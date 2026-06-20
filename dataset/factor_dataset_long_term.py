import numpy as np
import pandas as pd

from dataset import build_factor_name
from dataset.factor_name_long_term import build_factor_name_long_term, build_factor_table_long_term
from dataset.factor_dataset import FactorDataset
from dataset.sql_ops import load_factor_by_table_filtered, load_labels
from utils import list2str
from utils.registry import DATASET_REGISTRY


@DATASET_REGISTRY.register()
class FactorLongTermDataset(FactorDataset):
    DERIVED_SUFFIXES = [
        'ewm_10m',
        'ewm_30m',
        'z_5m',
        'z_10m',
        'z_30m',
        'trend_mean_1m_5m',
        'trend_mean_5m_30m',
    ]
    PREPROCESS_DERIVED_SUFFIXES = [
        'ewm_10m',
        'ewm_30m',
        'trend_mean_1m_5m',
        'trend_mean_5m_30m',
    ]

    def __init__(self, opt, test_month, indus_type, logger_name=None, *args, **kwargs):
        dataset_opt = opt['dataset']
        if dataset_opt.get('factor_table_groups') and not dataset_opt.get('factor_table'):
            dataset_opt['factor_table'] = build_factor_table_long_term(dataset_opt['factor_table_groups'])
        if dataset_opt.get('eval_factor_table_groups') and not dataset_opt.get('eval_factor_table'):
            dataset_opt['eval_factor_table'] = build_factor_table_long_term(dataset_opt['eval_factor_table_groups'])

        super().__init__(opt, test_month, indus_type, logger_name, *args, **kwargs)

        self.long_ret_name = self.opt['dataset'].get('long_ret_name', 'long_ret_10min')
        self.short_ret_name = self.opt['dataset'].get('short_ret_name', 'short_ret_10min')
        self.window_config = self.opt['dataset'].get(
            'long_term_window_config',
            {'1m': 4, '5m': 20, '10m': 40, '30m': 120}
        )

        self.raw_factor_name = build_factor_name_long_term(self.opt['dataset']['training_factor_name'])
        requested_derived_factor_name = build_factor_name_long_term(
            self.opt['dataset'].get('derived_factor_name', 'long_term_derived_factor_15s')
        )
        requested_derived_factor_set = set(requested_derived_factor_name)
        self.derived_raw_factor_name = [
            factor_name for factor_name in self.raw_factor_name
            if factor_name in requested_derived_factor_set
        ]
        self.raw_log_factor_name = list(
            set(self.raw_factor_name) & set(build_factor_name_long_term(self.opt['dataset']['log_factor_name']))
        )
        self.training_factor_name = self.build_long_term_feature_names(self.raw_factor_name)
        self.std_factor_name = self.expand_feature_names(
            build_factor_name_long_term(self.opt['dataset']['std_factor_name']),
            include_zscore=False
        )
        self.clip_factor_name = self.expand_feature_names(
            build_factor_name_long_term(self.opt['dataset']['clip_factor_name']),
            include_zscore=False
        )
        self.log_factor_name = self.raw_log_factor_name

        label_columns = ['ret', self.long_ret_name, self.short_ret_name]
        self.train_data_column_name = ['ticker', 'date', 'time'] + self.training_factor_name + label_columns
        self.train_data_column_name = list(dict.fromkeys(self.train_data_column_name))

        self.logger.info(f"[{self.logger_name}] Long-term factor mode enabled.")
        self.logger.info(f"[{self.logger_name}] Long return column: {self.long_ret_name}, short return column: {self.short_ret_name}")
        self.logger.info(f"[{self.logger_name}] Derived raw factor number: {len(self.derived_raw_factor_name)}")

    def build_feature_names_for_factor(self, factor_name, include_zscore=True):
        feature_names = [f'{factor_name}__current']
        if factor_name not in self.derived_raw_factor_name:
            return feature_names

        suffixes = self.DERIVED_SUFFIXES if include_zscore else self.PREPROCESS_DERIVED_SUFFIXES
        feature_names.extend([f'{factor_name}__{suffix}' for suffix in suffixes])
        return feature_names

    def build_long_term_feature_names(self, raw_factor_names):
        feature_names = []
        for factor_name in raw_factor_names:
            feature_names.extend(self.build_feature_names_for_factor(factor_name, include_zscore=True))
        return feature_names

    def expand_feature_names(self, factor_names, include_zscore=True):
        expanded = []
        for factor_name in factor_names:
            if factor_name in self.raw_factor_name:
                expanded.extend(self.build_feature_names_for_factor(factor_name, include_zscore=include_zscore))
            elif factor_name in self.training_factor_name:
                expanded.append(factor_name)
        return list(dict.fromkeys(expanded))

    def preprocess(self, factor):
        if len(self.log_factor_name) > 0:
            data = factor[self.log_factor_name].values
            factor.loc[:, self.log_factor_name] = np.sign(data) * np.log(np.abs(data) + 1)
        return factor

    def sort_factor_frame(self, factor_df):
        return factor_df.sort_values(['ticker', 'date', 'time']).reset_index(drop=True)

    def rename_feature_columns(self, feature_df, suffix):
        return feature_df.rename(columns={col: f'{col}__{suffix}' for col in feature_df.columns})

    def generate_long_term_features(self, factor):
        factor = self.sort_factor_frame(factor)
        feature_frames = [factor[['ticker', 'date', 'time']].copy()]

        current_features = factor[self.raw_factor_name].copy()
        feature_frames.append(self.rename_feature_columns(current_features, 'current'))

        derived_factor_name = [factor_name for factor_name in self.derived_raw_factor_name if factor_name in factor.columns]
        if len(derived_factor_name) > 0:
            derived_data = factor[derived_factor_name]
            grouped = factor.groupby(['ticker', 'date'], sort=False)[derived_factor_name]
            rolling_means = {}

            for label in ['1m', '5m', '10m', '30m']:
                window = self.window_config[label]
                rolling_means[label] = grouped.transform(
                    lambda x: x.rolling(window=window, min_periods=window).mean()
                )

            for label in ['10m', '30m']:
                window = self.window_config[label]
                ewm_features = grouped.transform(
                    lambda x: x.ewm(span=window, adjust=False, min_periods=window).mean()
                )
                feature_frames.append(self.rename_feature_columns(ewm_features, f'ewm_{label}'))

            for label in ['5m', '10m', '30m']:
                window = self.window_config[label]
                rolling_std = grouped.transform(
                    lambda x: x.rolling(window=window, min_periods=window).std(ddof=0)
                ).replace(0, np.nan)
                z_features = (derived_data - rolling_means[label]) / rolling_std
                feature_frames.append(self.rename_feature_columns(z_features, f'z_{label}'))

            trend_1m_5m = rolling_means['1m'] - rolling_means['5m']
            trend_5m_30m = rolling_means['5m'] - rolling_means['30m']
            feature_frames.append(self.rename_feature_columns(trend_1m_5m, 'trend_mean_1m_5m'))
            feature_frames.append(self.rename_feature_columns(trend_5m_30m, 'trend_mean_5m_30m'))

        res = pd.concat(feature_frames, axis=1)
        res = res.loc[:, ~res.columns.duplicated()].copy()
        return res

    def load_data_from_sql(self, month):
        try:
            self.tickers = tuple(self.tickers)
            data = [pd.DataFrame()]
            if self.mode == 'eval':
                database_name = list(self.eval_factor_table.keys())
                factor_table_name = self.eval_factor_table
            else:
                database_name = list(self.factor_table.keys())
                factor_table_name = self.factor_table

            i = 0
            for database in database_name:
                for table in factor_table_name[database]:
                    factor = load_factor_by_table_filtered(
                        database, table, self.tickers, self.pool_name, month, self.test_month,
                        self.rebalancing_tables, self.trading_hours, self.training_month_num,
                        self.io_backend, self.raw_factor_name
                    )
                    if len(factor) == 0:
                        raise FileExistsError(f"[{self.logger_name}] No factor exists in [{database}.{table}] !")

                    if i == 0:
                        data = factor
                    else:
                        if 'limitFlag' in factor.columns:
                            del factor['limitFlag']
                        data = pd.merge(factor, data, on=['ticker', 'date', 'time'])
                    i += 1

            self.preprocess(data)
            data = self.generate_long_term_features(data)
            labels = load_labels(self.opt, self.tickers, month)
            data = data[['ticker', 'date', 'time'] + self.training_factor_name]
            data = pd.merge(data, labels, on=['ticker', 'date', 'time'])

            missing_tickers = set(self.tickers) - set(data['ticker'].unique())
            if len(missing_tickers) > 0:
                self.logger.warning(f"[{self.logger_name}] There are missing tickers in {month} Return: {list2str(missing_tickers)}")

            if len(data) == 0:
                raise FileExistsError(f"[{self.logger_name}] No factor or return data exists in SQL")

        except Exception as e:
            self.logger.error(f"[{self.logger_name}] Error in fetching factor and return from SQL: {e}", exc_info=True)
            raise

        return data

    def split_data(self, data):
        if self.mode == 'eval':
            test_data = data[self.test_month]
            train_data = pd.DataFrame(columns=test_data.columns)
        elif self.mode == 'rt':
            train_data = pd.concat([data[m] for m in self.training_month])
            test_data = pd.DataFrame(columns=train_data.columns)
        else:
            train_data = pd.concat([data[m] for m in self.training_month])
            test_data = data[self.test_month]

        if self.long_ret_name not in train_data.columns or self.short_ret_name not in train_data.columns:
            raise KeyError(
                f"[{self.logger_name}] Missing long/short return columns: [{self.long_ret_name}], [{self.short_ret_name}]"
            )

        train_data = train_data.copy()
        test_data = test_data.copy()
        train_data.loc[:, 'ret'] = train_data[self.long_ret_name]
        if len(test_data) > 0:
            test_data.loc[:, 'ret'] = test_data[self.long_ret_name]

        train_data = train_data[self.train_data_column_name]
        test_data = test_data[self.train_data_column_name]
        return train_data, test_data

    def make_label(self, train_data, test_data):
        def add_label(df):
            up_mask = df[self.long_ret_name] >= self.alpha
            down_mask = df[self.short_ret_name] >= self.alpha
            both_mask = up_mask & down_mask
            if both_mask.any():
                self.logger.warning(
                    f"[{self.logger_name}] There are {both_mask.sum()} samples matching both long-up and short-down labels."
                )
            df['class_label'] = 2
            df.loc[down_mask & (~both_mask), 'class_label'] = 0
            df.loc[up_mask & (~both_mask), 'class_label'] = 1

        add_label(train_data)
        train_num = {0: (train_data['class_label'] == 0).sum(),
                     1: (train_data['class_label'] == 1).sum(),
                     2: (train_data['class_label'] == 2).sum()}
        self.logger.info(f"[{self.logger_name}] Train label number is {train_num}")

        add_label(test_data)
        test_num = {0: (test_data['class_label'] == 0).sum(),
                    1: (test_data['class_label'] == 1).sum(),
                    2: (test_data['class_label'] == 2).sum()}
        self.logger.info(f"[{self.logger_name}] Test label number is {test_num}")
        return train_data, test_data
