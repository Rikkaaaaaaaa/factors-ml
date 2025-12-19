import numpy as np
import pandas as pd
import os.path as osp
import traceback
import time
import copy
from sklearn.preprocessing import StandardScaler

from utils import list2str
from dataset import build_factor_name
from dataset.sql_ops import load_ticker_by_indus, load_labels, align_factor_ticker, load_factor_by_table, check_rebalanced
from utils.logger import get_root_logger
from utils.registry import DATASET_REGISTRY


@DATASET_REGISTRY.register()
class FactorDataset():
    """
    fetch dataset in one indus_type for factor and return

    Args:
        opt(dict): option for dataset, includes following keys:
            ...
        test_month(int): month needs to be eval
        indus_type(int): one of the indus_class

    """
    def __init__(self, opt, test_month, indus_type, logger_name=None, *args, **kwargs):
        self.opt = opt
        self.test_month = test_month
        self.indus_type = indus_type
        self.mode = self.opt.get('mode')
        self.debug_mode = self.opt['debug']
        # logging file
        self.logger_name = logger_name
        if self.logger_name is None:
            self.logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=self.logger_name)

        # update option dict
        self.opt['dataset'].setdefault('indus_table_suffix', '')
        self.trading_hours = self.opt['dataset'].setdefault('trading_hours', 'None')
        self.task_type = self.opt['dataset'].setdefault('task_type', 'classification')
        if self.task_type == 'classification':
            self.class_num = self.opt['dataset'].setdefault('class_num', 2)
        self.training_month = self.get_training_month()
        self.training_month_num = len(self.training_month)

        # init params
        self.io_backend = self.opt['dataset']['io_backend']
        self.price_name = self.opt['dataset']['price_name']
        self.ret_name = self.opt['dataset']['ret_name']
        self.avg_price = self.opt['dataset']['avg_price']
        self.indus_class = self.opt['dataset']['indus_class']
        self.pool_name = self.opt['dataset']['pool_name']
        self.factor_table = self.opt['dataset']['factor_table']
        self.rebalancing_tables = self.opt['dataset']['rebalancing_tables']
        self.eval_factor_table = self.opt['dataset'].get('eval_factor_table')

        # build factor names
        self.training_factor_name =  build_factor_name(self.opt['dataset']['training_factor_name']) # list(set(_train_data.columns) - set(del_column))
        self.std_factor_name = build_factor_name(self.opt['dataset']['std_factor_name'])
        self.clip_factor_name = build_factor_name(self.opt['dataset']['clip_factor_name'])
        self.log_factor_name = build_factor_name(self.opt['dataset']['log_factor_name'])
        self.train_data_column_name = ['ticker', 'date', 'time'] + self.training_factor_name + ['ret']

        # bool params
        self.is_empty = False

        # init logging
        self.logger.info(f"[{self.logger_name}] Running {self.mode} mode!")
        self.logger.info(f"[{self.logger_name}] Task type: {self.task_type}")
        self.logger.info(f"[{self.logger_name}] Loading indus by [{self.indus_class}] from table [static_data_industry_{self.pool_name}_history] + [{self.opt['dataset']['indus_table_suffix']}]]")
        if isinstance(self.trading_hours, dict):
            if self.trading_hours['am_start_time'] <= self.trading_hours['am_end_time']:
                self.logger.info(f"[{self.logger_name}] Trading hours: AM [{self.trading_hours['am_start_time']}, {self.trading_hours['am_end_time']}]")
            if self.trading_hours['pm_start_time'] <= self.trading_hours['pm_end_time']:
                self.logger.info(f"[{self.logger_name}] Trading hours: PM [{self.trading_hours['pm_start_time']}, {self.trading_hours['pm_end_time']}]")


    def load_data(self, cache=False, data=None):

        try:
            #-----Ingest Ticker List-----#

            # read tickers from mysql
            self.tickers = self.load_ticker_list()
            if self.debug_mode:
                self.tickers = self.tickers[: min(len(self.tickers), 2)]
            if len(self.tickers) == 0: # no ticker, return None
                self.is_empty = True
                return

            #-----Ingest Factor and Return-----#

            # read data from mysql
            need_rebalanced_month = check_rebalanced(self.training_month, self.test_month) # for debug
            self.logger.info(f"[{self.logger_name}] need_rebalanced_month: {need_rebalanced_month} ")

            # restore data by month
            self.logger.info(f"[{self.logger_name}] Start loading factor and return")
            if data is None:
                data = dict()
                if self.mode != 'eval':
                    for month in self.training_month:
                        data[month] = self.load_data_from_sql(month)
                if self.mode != 'rt':
                    data[self.test_month] = self.load_data_from_sql(self.test_month)
            else:
                data = copy.deepcopy(data)
            self.logger.info(f"[{self.logger_name}] Finish loading factor and return")

            # cache data if 15s
            if cache:
                cache_data = copy.deepcopy(data)

            #---------Data Preprocessing-------#

            # split data into train and test set
            train_data, test_data = self.split_data(data)

            if self.mode == 'eval':
                if len(test_data) == 0:
                    self.is_empty = True
                    return
                # delete 1300 in test data
                test_data = self.del_test_value(test_data)
                # transforming data, including std, clip, save params by ticker
                self.logger.info(f"[{self.logger_name}] Start reading preprocess params and transforming test data")
                self.transform(train_data, test_data)
                self.logger.info(f"[{self.logger_name}] Finish transforming test data")
            else:
                # rt or train mode
                if len(train_data) == 0 :
                    self.is_empty = True
                    return
                # get alpha (i.e.return threshold)
                self.alpha = self.get_alhpa(train_data)
                # make classification labels according to returns
                if self.task_type == 'classification':
                    train_data, test_data = self.make_label(train_data, test_data)
                # filter train_data with return
                train_data = self.filter_by_label(train_data)
                # delete nan factor in train data
                train_data = self.del_train_value(train_data)
                # delete 1300 in test data
                test_data = self.del_test_value(test_data)

                # transforming data, including std, clip, save params by ticker
                self.logger.info(f"[{self.logger_name}] Start transforming data and saving preprocess params")
                self.transform(train_data, test_data)
                # rebalance training data
                self.rebalance_training_data()
                self.logger.info(f"[{self.logger_name}] Finish transforming data and saving preprocess params")

            # count data num
            self.logger.info(f"[{self.logger_name}] Training data num is {len(train_data)} and test data num is {len(test_data)}")

            if cache:
                return cache_data
            else:
                return

        except Exception as e:
            self.logger.error(f"[{self.logger_name}] Error in load_data function: {e}", exc_info=True)


    def load_ticker_list(self):
        # fetch ticker list from mysql table
        try:
            ticker_list = []
            # load ticker list
            cur_ticker = load_ticker_by_indus(self.opt, self.pool_name, self.indus_type, self.test_month)
            ticker_list.extend(cur_ticker)

            # align training and testing ticker list
            all_ticker = cur_ticker.copy()
            check_ticker_month = self.get_check_ticker_month()
            ticker_list = align_factor_ticker(self.factor_table, all_ticker, self.pool_name, check_ticker_month, self.test_month, self.rebalancing_tables, self.training_month_num, self.io_backend, self.logger_name)

            # ordered ticker list
            ticker_list = sorted(ticker_list)
            self.logger.info(f"[{self.logger_name}] Total ticker number is {len(ticker_list)}")

            # check whether ticker list is null
            if len(ticker_list) == 0:
                raise FileExistsError(f"[{self.logger_name}] No ticker list exists in SQL")

        except Exception as e:
            self.logger.error(f"[{self.logger_name}] Error in fetching ticker list: {e}", exc_info=True)
            ticker_list = []
            # self.logger.info(traceback.format_exc())
            # exc_type, exc_values, exc_traceback = sys.exc_info()
            # traceback.print_tb(exc_traceback)

        return ticker_list


    def load_data_from_sql(self, month):
        try:
            self.tickers = tuple(self.tickers)
            data = [pd.DataFrame()]
            # training phase / eval phase
            if self.mode == 'eval':
                database_name = list(self.eval_factor_table.keys())
                factor_table_name = self.eval_factor_table
            else:
                database_name = list(self.factor_table.keys())
                factor_table_name = self.factor_table

            i = 0
            for database in database_name:
                for table in factor_table_name[database]:
                    # load factors from sql
                    factor = load_factor_by_table(database, table, self.tickers, self.pool_name, month, self.test_month,
                                                  self.rebalancing_tables, self.trading_hours,
                                                  self.training_month_num, self.io_backend)
                    # preprocessing
                    self.preprocess(factor)
                    # merge factors from every table
                    if i == 0:
                        data = factor
                    else:
                        if 'limitFlag' in factor.columns:
                            del factor['limitFlag']
                        data = pd.merge(factor, data, on=['ticker', 'date', 'time'])
                    i += 1
            # load labels
            labels = load_labels(self.opt, self.tickers, month)

            # merge factors and labels by ticker, date, time
            data = data[['ticker', 'date', "time"] + self.training_factor_name]
            data = pd.merge(data, labels, on=['ticker', 'date', 'time'])
            # data.rename(columns={'ret_' + self.ret_name: 'ret'}, inplace=True)

            # check missing tickers between return and factors
            missing_tickers = set(self.tickers) - set(data['ticker'].unique())
            # assert len(self.tickers) == len(data['ticker'].unique()), self.logger.info("SQL data missing ticker", missing_tickers)
            if len(missing_tickers) > 0:
                # raise ValueError(f"[{self.logger_name}] There are missing tickers in {month} Return: {list2str(missing_tickers)}")
                self.logger.warning(f"[{self.logger_name}] There are missing tickers in {month} Return: {list2str(missing_tickers)}")

            # check Whether data is null
            if len(data) == 0:
                raise FileExistsError(f"[{self.logger_name}] No factor or return data exists in SQL")

        except Exception as e:
            self.logger.error(f"[{self.logger_name}] Error in fetching factor and return from SQL: {e}", exc_info=True)
            # self.logger.info(traceback.format_exc())
            raise

        return data


    def preprocess(self, factor):
        # preprocessing after fetcing from sql
        # log factor
        def get_log_factor_df(df_factors):
            df_factors[df_factors > 0] = np.log(df_factors[df_factors > 0] + 1)
            df_factors[df_factors < 0] = -np.log(-df_factors[df_factors < 0] + 1)
            return df_factors

        for log_factor in self.log_factor_name:
            if log_factor in factor.columns:
                factor.loc[:, log_factor] = get_log_factor_df(factor[log_factor].values)
        # other ops
        # ......
        return factor


    def split_data(self, data):
        # split month data to train/test
        if self.mode == 'eval':
            test_data = data[self.test_month]
            train_data = pd.DataFrame(columns=test_data.columns)
        elif self.mode == 'rt':
            train_data = pd.concat([data[m] for m in self.training_month])
            test_data = pd.DataFrame(columns=train_data.columns)
        else:
            # trainning mode
            train_data = pd.concat([data[m] for m in self.training_month])
            test_data = data[self.test_month]

        # rename y column name
        if self.opt['dataset'].get('mix_return'):
            train_data.rename(columns={'ret_mix': 'ret'}, inplace=True)
        else:
            train_data.rename(columns={'ret_' + self.ret_name: 'ret'}, inplace=True)
        test_data.rename(columns={'ret_' + self.ret_name: 'ret'}, inplace=True)

        # filter data
        train_data = train_data[self.train_data_column_name]
        test_data = test_data[self.train_data_column_name]

        return train_data, test_data

    def get_alhpa(self, train_data):
        if isinstance(self.opt['dataset']['alpha'], dict):
            if self.opt['dataset']['alpha'].get('type') == 'dynamic':
                if self.opt['dataset']['alpha'].get('quantile'):
                    quantile = self.opt['dataset']['alpha'].get('quantile')
                    alpha = np.quantile(train_data['ret'].dropna(), quantile)
                    self.logger.info(
                        f"[{self.logger_name}] Training with return threshold={alpha:.6f}, quantile={quantile}")

        else:
            alpha = self.opt['dataset']['alpha']
            self.logger.info(f"[{self.logger_name}] Training with return threshold={alpha:.6f}")
        return alpha


    def make_label(self, train_data, test_data):
        '''
        classification of return, 0 for down, 1 for up and 2 for stable
        '''
        def add_label(df):
            df['class_label'] = df['ret'].mask(df['ret'] <= -1 * self.alpha, 0).mask(df['ret'] >= self.alpha, 1) \
                .mask((-1 * self.alpha < df['ret']) & (df['ret'] < self.alpha), 2)

        add_label(train_data)
        train_num = {0: (train_data['class_label'] == 0).sum(),
                     1: (train_data['class_label'] == 1).sum(),
                     2: (train_data['class_label'] == 2).sum()}
        self.logger.info(f"[{self.logger_name}] Train label number is {train_num}")

        # len(test_data) = 0
        add_label(test_data)
        test_num = {0: (test_data['class_label'] == 0).sum(),
                    1: (test_data['class_label'] == 1).sum(),
                    2: (test_data['class_label'] == 2).sum()}
        self.logger.info(f"[{self.logger_name}] Test label number is {test_num}")

        return train_data, test_data


    def filter_by_label(self, train_data):
        total_train_num = len(train_data)
        if self.task_type == 'classification':
            if self.class_num == 2:
                filtered_train_data = train_data.query('class_label == 2')
                train_data = train_data.query('class_label != 2')
            self.logger.info(f"[{self.logger_name}] Select {len(train_data) / total_train_num * 100:.2f}% train data with return={self.alpha} and class num is {self.class_num}.")
        if self.task_type == 'regression':
            train_data = train_data.query('ret.notna()')
        return train_data


    def del_train_value(self, train_data):
        # delete retunr==nan from train_data
        train_data = train_data.query('ret.notna()')
        train_data = train_data.query('time!=130000000')

        # del nan in train_data
        data = train_data.dropna()
        if self.opt['dataset'].get('drop_null_in_training') :
            self.logger.info(f"[{self.logger_name}] Delete {(len(train_data)-len(data))/len(train_data)*100:.2f}% null samples in train data.")
            return data
        else:
            pass
            # keep nan by default
            # 20250319: training without dropna, will improve performance
            # null_idx = np.isnan(test_data[list(backtest_factor_name) + ['ret']].values).all(axis=1) # all nan index
            self.logger.info(f"[{self.logger_name}] Keep nan in training data. There are {(len(train_data) - len(data)) / len(train_data) * 100:.2f}% null samples in train data.")
        return train_data

    def del_test_value(self, test_data):
        # delete time==130000 from test_data
        test_data = test_data.query('time!=130000000')

        return test_data

    def transform(self, train_data, test_data=None):
        self.train_data_list = []
        self.test_data_list = []
        self.std_params = []
        self.clip_params = []

        # eval mode: read params from csv
        if self.mode == 'eval':
            # save and read path
            pretrain_folder = self.opt['path']['pretrain_preprocess_path'][self.test_month]
            std_path = osp.join(pretrain_folder, f"std_params_indus{self.indus_type}.csv")
            clip_path = osp.join(pretrain_folder, f"clip_params_indus{self.indus_type}.csv")
            self.std_params = pd.read_csv(std_path)
            self.clip_params = pd.read_csv(clip_path)

        try:
            for ticker in self.tickers:
                temp_ticker_start_time = time.time()
                _train_data = train_data[train_data['ticker'] == ticker]
                _test_data = test_data[test_data['ticker'] == ticker]
                # 1 data clip
                if len(self.clip_factor_name) > 0:
                    # split data to train_x and test_x
                    train_x = _train_data[self.clip_factor_name]
                    test_x = _test_data[self.clip_factor_name]

                    # eval mode: read std params
                    if self.mode == 'eval':
                        ticker_clip_params = self.clip_params.query('ticker==@ticker')
                        factor_min = ticker_clip_params.set_index('factor_name').loc[self.clip_factor_name].reset_index()['min'].values
                        factor_max = ticker_clip_params.set_index('factor_name').loc[self.clip_factor_name].reset_index()['max'].values
                    else:
                        # clip type
                        if isinstance(self.opt['dataset'].get('clip'), dict):
                            if self.opt['dataset']['clip'].get('type') == '3sigma':
                                factor_mean = np.mean(train_x.dropna(), axis=0).values
                                factor_std = np.std(train_x.dropna(), axis=0).values
                                factor_min = factor_mean - 3 * factor_std
                                factor_max = factor_mean + 3 * factor_std
                            elif self.opt['dataset']['clip'].get('type') == 'quantile':
                                min_quantile = self.opt['dataset']['clip'].get('min_quantile')
                                max_quantile = self.opt['dataset']['clip'].get('max_quantile')
                                factor_min = np.percentile(train_x.dropna(), min_quantile, axis=0, )
                                factor_max = np.percentile(train_x.dropna(), max_quantile, axis=0, )
                            else:
                                factor_min = np.percentile(train_x.dropna(), 5, axis=0, )
                                factor_max = np.percentile(train_x.dropna(), 95, axis=0, )
                        else:
                            # default 5%~95%
                            factor_min = np.percentile(train_x.dropna(), 5, axis=0, )
                            factor_max = np.percentile(train_x.dropna(), 95, axis=0, )

                        # save transform params
                        clip_param = pd.DataFrame(columns=['factor_name', 'min', 'max', ])
                        clip_param['factor_name'] = self.clip_factor_name
                        clip_param['min'] = factor_min
                        clip_param['max'] = factor_max
                        clip_param.insert(0, 'ticker', ticker)
                        self.clip_params.append(clip_param)

                    # update temp data
                    train_x = np.clip(train_x, factor_min, factor_max)
                    test_x = np.clip(test_x, factor_min, factor_max)
                    _train_data.loc[:, self.clip_factor_name] = train_x.values
                    _test_data.loc[:, self.clip_factor_name] = test_x.values

                # 2 data std
                if len(self.std_factor_name) > 0:
                    # split data to train_x and test_x
                    train_x = _train_data[self.std_factor_name]
                    test_x = _test_data[self.std_factor_name]

                    # eval mode: read std params
                    if self.mode == 'eval':
                        ticker_std_params = self.std_params.query('ticker==@ticker')
                        factor_std = ticker_std_params.set_index('factor_name').loc[self.std_factor_name].reset_index()['std'].values
                        factor_mean = ticker_std_params.set_index('factor_name').loc[self.std_factor_name].reset_index()['mean'].values
                    else:
                        factor_mean = np.mean(train_x, axis=0).values
                        factor_std = np.std(train_x, axis=0).values
                        # save transform params
                        std_param = pd.DataFrame(columns=['factor_name', 'mean', 'std'])
                        std_param['factor_name'] = self.std_factor_name
                        std_param['mean'] = factor_mean
                        std_param['std'] = factor_std
                        std_param.insert(0, 'ticker', ticker)
                        self.std_params.append(std_param)

                    # update temp data
                    train_x = (train_x - factor_mean) / factor_std
                    test_x = (test_x - factor_mean) / factor_std
                    _train_data.loc[:, self.std_factor_name] = train_x.values
                    _test_data.loc[:, self.std_factor_name] = test_x.values

                # 3 return clip
                if self.task_type == 'regression':
                    ret_lower_bound = np.percentile(_train_data['ret'].dropna(), 1)
                    ret_upper_bound = np.percentile(_train_data['ret'].dropna(), 99)
                    new_ret = np.clip(_train_data['ret'].values, ret_lower_bound, ret_upper_bound)
                    _train_data.loc[:, 'ret'] = new_ret

                # 4 append temp data
                self.train_data_list.append(_train_data)
                self.test_data_list.append(_test_data)

        except Exception as e:
            self.logger.error(f"[{self.logger_name}] Error in transforming ticker {ticker}: {e}", exc_info=True)
            raise

        self.train_data = pd.concat(self.train_data_list)
        self.test_data = pd.concat(self.test_data_list)

        if self.mode != 'eval':
            # save transforming params
            save_folder = self.opt['path']['preprocess_path'][self.test_month]
            std_path = osp.join(save_folder, f"std_params_indus{self.indus_type}.csv")
            clip_path = osp.join(save_folder, f"clip_params_indus{self.indus_type}.csv")
            if len(self.std_params) > 0:
                self.std_params = pd.concat(self.std_params)
                self.std_params.to_csv(std_path, index=False)
            if len(self.clip_params) > 0:
                self.clip_params = pd.concat(self.clip_params)
                self.clip_params.to_csv(clip_path, index=False)

            # # std across all tickers
            # scaler = StandardScaler()
            # self.train_data.loc[:, self.training_factor_name] = scaler.fit_transform(self.train_data[self.training_factor_name])
            # self.test_data.loc[:, self.training_factor_name] = scaler.transform(self.test_data[self.training_factor_name])
            # scaler_params = pd.DataFrame({
            #     'factor_name': self.training_factor_name,
            #     'mean': scaler.mean_,
            #     'std': scaler.scale_
            # })
            # std_across_tickers_path = osp.join(save_folder, f"std_params_across_tickers_indus{self.indus_type}.csv")
            # scaler_params.to_csv(std_across_tickers_path)

    def rebalance_training_data(self):
        # balance training data
        if self.opt['dataset'].get('balance') == 'reverse':
            train_data_copy = self.train_data.copy()
            train_data_copy[self.training_factor_name] = -1 * train_data_copy[self.training_factor_name]
            # reverse label values
            if self.task_type == 'classification':
                if self.class_num == 2:
                    train_y = train_data_copy['class_label'].values
                    reversed_y = np.zeros_like(train_y)
                    up_idx = (train_y==0)
                    down_idx = (train_y==1)
                    reversed_y[up_idx] = 1
                    reversed_y[down_idx] = 0
                    train_data_copy['class_label'] = reversed_y
            if self.task_type == 'regression':
                train_data_copy['ret'] = -1 * train_data_copy['ret'].values

            # add column augment to indicate train data
            train_data_copy['augment'] = 1
            self.train_data['augment'] = 0
            self.train_data = pd.concat([self.train_data, train_data_copy])

        # downsample
        def down_sample(self, data):
            up_num = len(data.query('class_label==0'))
            down_num = len(data.query('class_label==1'))
            sample_num = min(up_num, down_num)
            up_data = data.query('class_label==0').sample(n=sample_num)
            down_data = data.query('class_label==1').sample(n=sample_num)
            data = pd.concat([up_data, down_data], ignore_index=True)
            return data
        if self.task_type == 'classification' and self.opt['dataset'].get('balance') == 'downsample' :
            if self.class_num == 2:
                self.train_data = self.down_sample(self.train_data)


    def get_training_month(self):
        def get_pre_month(month, pre_num):
            int_year = month // 100
            int_month = month - int_year * 100
            if int_month <= pre_num:
                res_year = int_year - (pre_num - int_month) // 12 - 1
                res_month = 12 - (pre_num - int_month) % 12
                res = int(res_year * 100 + res_month)
            else:
                res = month - pre_num
            return res

        if isinstance(self.opt['dataset'].get('training_month_num'), int):
            training_month_num = self.opt['dataset'].get('training_month_num')
        else:
            training_month_num = 3
            self.opt['dataset']['training_month_num'] = 3
        training_month = [get_pre_month(self.test_month, training_month_num - i) for i in range(0, training_month_num)]
        if self.mode != 'eval':
            self.logger.info(f"[{self.logger_name}] Training set include month {training_month}")

        return training_month


    def get_check_ticker_month(self):
        if self.mode != 'rt':
            check_ticker_month = self.training_month + [self.test_month]
        else:
            check_ticker_month = self.training_month

        return check_ticker_month


    def set_selected_factor(self, selected_factor_name):
        self.selected_factor_name = list(set(selected_factor_name) & set(self.training_factor_name))


if __name__ == '__main__':
    from utils.option import parse_options

    opt, args = parse_options('./')
    indus_type = 1
    dataset = FactorDataset(opt, 202307, indus_type)
    dataset.load_data()
