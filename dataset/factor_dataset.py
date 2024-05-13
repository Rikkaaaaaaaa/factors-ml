import numpy as np
import pandas as pd
import os.path as osp
import traceback

from utils import list2str
from dataset import build_factor_name
from dataset.sql_data import load_ticker_by_indus, align_factor_ticker, load_factor_by_table, check_rebalanced
from utils.mysql import cx_read_sql
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
    def __init__(self, opt, test_month, indus_type, cache=None, *args, **kwargs):
        self.opt = opt
        self.test_month = test_month
        self.indus_type = indus_type
        # logging file
        logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)
        # init params
        self.ret_name = self.opt['dataset']['ret_name']
        self.price_name = self.opt['dataset']['price_name']
        self.avg_price = self.opt['dataset']['avg_price']
        self.is_runtime = self.opt['is_runtime']
        self.training_month = self.get_training_month()
        self.training_month_num = len(self.training_month)
        self.indus_class = self.opt['dataset']['indus_class']
        self.class_num = self.opt['dataset']['class_num']
        self.pool_name = self.opt['dataset']['pool_name']
        self.factor_table = self.opt['dataset']['factor_table']
        self.database_name = list(self.factor_table.keys())
        self.training_factor_name =  build_factor_name(self.opt['dataset']['training_factor_name']) # list(set(_train_data.columns) - set(del_column))
        self.std_factor_name = build_factor_name(self.opt['dataset']['std_factor_name'])
        self.clip_factor_name = build_factor_name(self.opt['dataset']['clip_factor_name'])
        self.log_factor_name = build_factor_name(self.opt['dataset']['log_factor_name'])

        # bool params
        self.debug_mode = self.opt['debug']
        self.is_empty = False


    def load_data(self):
        # Ingest Ticker List

        # read tickers from mysql
        self.tickers = self.load_ticker_list()
        if self.debug_mode:
            self.tickers = self.tickers[: min(len(self.tickers), 10)]
        if len(self.tickers) == 0: # no ticker, return None
            self.is_empty = True
            return

        # Ingest Factor and Return

        # read data from mysql
        need_rebalanced_month = check_rebalanced(self.training_month, self.test_month)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Checking need_rebalanced_month: {need_rebalanced_month} ")
        data = dict() # restore data by month
        for month in self.training_month:
            data[month] = self.load_data_from_sql(month)
        if not self.is_runtime:
            data[self.test_month] = self.load_data_from_sql(self.test_month)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish loading factor and return ")

        # Data Preprocessing

        # split data into train and test set
        train_data, test_data = self.split_data(data)
        if len(train_data) == 0:
            self.is_empty = True
            return

        # get alpha
        self.alpha = self.get_alhpa(train_data)
        # make labels according to returns
        train_data, test_data = self.make_label(train_data, test_data)
        # filter train_data with return
        train_data = self.filter_by_label(train_data)
        # delete nan in train data
        train_data = self.del_null_value(train_data)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Start transforming data and saving preprocess params")
        # transforming data, including std, clip, save params by ticker
        if self.is_runtime:
            # cancel backtesting in test_data
            self.transform_runtime(train_data)
        else:
            self.transform(train_data, test_data)
        # rebalance training data
        self.rebalance_training_data()

        # logging
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish transforming data and saving preprocess params")
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training data num is {len(train_data)} and test data num is {len(test_data)}")

    def load_ticker_list(self):
        # fetch ticker list from mysql table
        try:
            ticker_list = []
            for pool in self.pool_name:
                # load ticker list
                cur_ticker = load_ticker_by_indus(pool, self.price_name, self.indus_class, self.indus_type, self.test_month, self.avg_price)
                ticker_list.extend(cur_ticker)

            # align training and testing ticker list
            all_ticker = cur_ticker.copy()
            check_ticker_month = self.get_check_ticker_month()
            align_factor_ticker(self.factor_table, all_ticker, check_ticker_month, self.test_month, self.training_month_num)

            # check whether ticker list is null
            if len(ticker_list) == 0:
                raise FileExistsError(f"{self.test_month}_indus_{self.indus_type}: No ticker list exists in SQL")

            # ordered ticker list
            ticker_list = sorted(ticker_list)
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Total ticker number is {len(ticker_list)}")

        except Exception as e:
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Error in fetching ticker list: {e}")
            self.logger.info(traceback.format_exc())
            ticker_list = []
            # exc_type, exc_values, exc_traceback = sys.exc_info()
            # traceback.print_tb(exc_traceback)

        return ticker_list


    def load_data_from_sql(self, month):
        try:
            self.tickers = tuple(self.tickers)
            data = [pd.DataFrame()]
            for i, database in enumerate(self.database_name):
                for table in self.factor_table[database]:
                    # load factors from sql
                    factor = load_factor_by_table(database, table, self.tickers, month, self.test_month, self.training_month_num)
                    # preprocess(log...)
                    self.preprocess(factor)
                    # merge factors from every table
                    if i == 0:
                        data = factor
                    else:
                        data = pd.merge(factor, data, on=['ticker', 'date', 'time'])
            # load labels
            labels = cx_read_sql(f'select ticker, date, time, ret_{self.ret_name}  from ret_{month} where ticker in {self.tickers}')

            # merge factors and labels by ticker, date, time
            data = pd.merge(data, labels, on=['ticker', 'date', 'time'])
            data.rename(columns={'ret_' + self.ret_name: 'ret'}, inplace=True)

            # check missing tickers between return and factors
            missing_tickers = set(self.tickers) - set(data['ticker'].unique())
            # assert len(self.tickers) == len(data['ticker'].unique()), self.logger.info("SQL data missing ticker", missing_tickers)
            if len(missing_tickers) > 0:
                raise ValueError(f"{self.test_month}_indus_{self.indus_type}: There are missing tickers in Return: {list2str(missing_tickers)}")

            # check Whether data is null
            if len(data) == 0:
                raise FileExistsError(f"{self.test_month}_indus_{self.indus_type}: No factor or return data exists in SQL")

        except Exception as e:
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Error in fetching factor and return from SQL: {e}")
            self.logger.info(traceback.format_exc())

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
        train_data = pd.concat([data[m] for m in self.training_month])
        if self.is_runtime:
            test_data = pd.DataFrame()
        else:
            test_data = data[self.test_month]
        return train_data, test_data

    def get_alhpa(self, train_data):
        if isinstance(self.opt['dataset']['alpha'], dict):
            if self.opt['dataset']['alpha'].get('type') == 'dynamic':
                if self.opt['dataset']['alpha'].get('quantile'):
                    quantile = self.opt['dataset']['alpha'].get('quantile')
                    alpha = np.quantile(train_data['ret'].dropna(), quantile)

        else:
            alpha = self.opt['dataset']['alpha']
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training with return threshold={alpha:.6f}")
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
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Train label number is {train_num}")

        if not self.is_runtime:
            add_label(test_data)
            test_num = {0: (test_data['class_label'] == 0).sum(),
                        1: (test_data['class_label'] == 1).sum(),
                        2: (test_data['class_label'] == 2).sum()}
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Test label number is {test_num}")

        return train_data, test_data


    def filter_by_label(self, train_data):
        # filter
        total_train_num = len(train_data)
        if self.class_num == 2:
            train_data = train_data.query('class_label != 2')
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Select {len(train_data) / total_train_num * 100:.2f}% train data with return={self.alpha} and class num is {self.class_num}.")

        return train_data


    def del_null_value(self, train_data):
        data = train_data.dropna()
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Delete {(len(train_data)-len(data))/len(data):.2f}% null samples in train data.")
        return data


    def transform(self, train_data, test_data=None):
        self.train_data = train_data.reset_index()
        self.test_data = test_data.reset_index()
        self.std_params = []
        self.clip_params = []

        for ticker in self.tickers:
            # data std
            if len(self.std_factor_name) > 0:
                _train_data = self.train_data.query('ticker==@ticker')
                _test_data = self.test_data.query('ticker==@ticker')
                # split data to train_x and test_x
                train_x = _train_data[self.std_factor_name]
                test_x = _test_data[self.std_factor_name]

                std_param = pd.DataFrame(columns=['factor_name', 'mean', 'std'])
                factor_mean = np.mean(train_x, axis=0).values
                factor_std = np.std(train_x, axis=0).values
                train_x = (train_x - factor_mean) / factor_std
                test_x = (test_x - factor_mean) / factor_std
                self.train_data.loc[_train_data.index, self.std_factor_name] = train_x.values
                self.test_data.loc[_test_data.index, self.std_factor_name] = test_x.values
                # save transform params
                std_param['factor_name'] = self.std_factor_name
                std_param['mean'] = factor_mean
                std_param['std'] = factor_std
                std_param.insert(0, 'ticker', ticker)
                self.std_params.append(std_param)

            # data clip
            if len(self.clip_factor_name) > 0:
                # split data to train_x and test_x
                _train_data = self.train_data.query('ticker==@ticker')
                _test_data = self.test_data.query('ticker==@ticker')
                train_x = _train_data[self.clip_factor_name]
                test_x = _test_data[self.clip_factor_name]
                # clip type
                if isinstance(self.opt['dataset'].get('clip'), dict):
                    if self.opt['dataset']['clip'].get('type') == '3sigma':
                        factor_mean = np.mean(train_x, axis=0).values
                        factor_std = np.std(train_x, axis=0).values
                        factor_min = factor_mean - 3 * factor_std
                        factor_max = factor_mean + 3 * factor_std
                    elif self.opt['dataset']['clip'].get('type') == 'quantile':
                        min_quantile = self.opt['dataset']['clip'].get('min_quantile')
                        max_quantile = self.opt['dataset']['clip'].get('max_quantile')
                        factor_min = np.percentile(train_x, min_quantile, axis=0, )
                        factor_max = np.percentile(train_x, max_quantile, axis=0, )
                    else:
                        factor_min = np.percentile(train_x, 5, axis=0, )
                        factor_max = np.percentile(train_x, 95, axis=0, )
                else:
                    # fefault 5%~95%
                    factor_min = np.percentile(train_x, 5, axis=0, )
                    factor_max = np.percentile(train_x, 95, axis=0, )
                train_x = np.clip(train_x, factor_min, factor_max)
                test_x = np.clip(test_x, factor_min, factor_max)
                self.train_data.loc[_train_data.index, self.clip_factor_name] = train_x
                self.test_data.loc[_test_data.index, self.clip_factor_name] = test_x
                # save transform params
                clip_param = pd.DataFrame(columns=['factor_name', 'min', 'max', ])
                clip_param['factor_name'] = self.clip_factor_name
                clip_param['min'] = factor_min
                clip_param['max'] = factor_max
                clip_param.insert(0, 'ticker', ticker)
                self.clip_params.append(clip_param)

        # save preprocess params
        save_folder = self.opt['path']['preprocess_path'][self.test_month]
        # std
        if len(self.std_params) > 0:
            std_path = osp.join(save_folder, f"std_params_indus{self.indus_type}.csv")
            self.std_params = pd.concat(self.std_params)
            self.std_params.to_csv(std_path, index=False)
        # clip
        if len(self.clip_params) > 0:
            clip_path = osp.join(save_folder, f"clip_params_indus{self.indus_type}.csv")
            self.clip_params = pd.concat(self.clip_params)
            self.clip_params.to_csv(clip_path, index=False)


    def transform_runtime(self, train_data):
        del_column = ['time', 'ticker', 'date', 'class_label', 'ret']  # del columns in data
        self.train_data = train_data.reset_index()
        self.std_params = []
        self.clip_params = []
        for ticker in self.tickers:

            # data std
            if len(self.std_factor_name) > 0:
                _train_data = self.train_data.query('ticker==@ticker')
                # split data to train_x and test_x
                train_x = _train_data[self.std_factor_name]

                std_param = pd.DataFrame(columns=['factor_name', 'mean', 'std'])
                factor_mean = np.mean(train_x, axis=0).values
                factor_std = np.std(train_x, axis=0).values
                train_x = (train_x - factor_mean) / factor_std
                self.train_data.loc[_train_data.index, self.std_factor_name] = train_x.values
                # save transform params
                std_param['factor_name'] = self.std_factor_name
                std_param['mean'] = factor_mean
                std_param['std'] = factor_std
                std_param.insert(0, 'ticker', ticker)
                self.std_params.append(std_param)

            # data clip
            if len(self.clip_factor_name) > 0:
                _train_data = self.train_data.query('ticker==@ticker')
                train_x = _train_data[self.clip_factor_name]

                clip_param = pd.DataFrame(columns=['factor_name', 'min', 'max', ])
                factor_min = np.percentile(train_x, 5, axis=0, )
                factor_max = np.percentile(train_x, 95, axis=0, )
                train_x = np.clip(train_x, factor_min, factor_max)
                self.train_data.loc[_train_data.index, self.clip_factor_name] = train_x
                # save transform params
                clip_param['factor_name'] = self.clip_factor_name
                clip_param['min'] = factor_min
                clip_param['max'] = factor_max
                clip_param.insert(0, 'ticker', ticker)
                self.clip_params.append(clip_param)

        # save preprocess params
        save_folder = self.opt['path']['preprocess_path'][self.test_month]
        # std
        if len(self.std_params) > 0:
            std_path = osp.join(save_folder, f"std_params_indus{self.indus_type}.csv")
            self.std_params = pd.concat(self.std_params)
            self.std_params.to_csv(std_path, index=False)
        # clip
        if len(self.clip_params) > 0:
            clip_path = osp.join(save_folder, f"clip_params_indus{self.indus_type}.csv")
            self.clip_params = pd.concat(self.clip_params)
            self.clip_params.to_csv(clip_path, index=False)

    def rebalance_training_data(self):
        # balance training data
        if self.class_num == 2 and self.opt['dataset'].get('balance') == 'reverse':
            train_data_copy = self.train_data.copy()
            train_data_copy[self.training_factor_name] = -1 * train_data_copy[self.training_factor_name]
            train_y = train_data_copy['class_label'].values
            reversed_y = np.zeros_like(train_y)
            up_idx = (train_y==0)
            down_idx = (train_y==1)
            reversed_y[up_idx] = 1
            reversed_y[down_idx] = 0
            train_data_copy['class_label'] = reversed_y
            # add column augment to indicate train data
            augment = pd.DataFrame(columns=['augment'], data=np.ones(len(reversed_y)))
            train_data_copy = pd.concat([train_data_copy,augment], axis=1)
            augment = pd.DataFrame(columns=['augment'], data=np.zeros(len(reversed_y)))
            self.train_data = pd.concat([self.train_data, augment], axis=1)
            self.train_data = pd.concat([self.train_data, train_data_copy], ignore_index=True)

        # downsample
        def down_sample(self, data):
            up_num = len(data.query('class_label==0'))
            down_num = len(data.query('class_label==1'))
            sample_num = min(up_num, down_num)
            up_data = data.query('class_label==0').sample(n=sample_num)
            down_data = data.query('class_label==1').sample(n=sample_num)
            data = pd.concat([up_data, down_data], ignore_index=True)
            return data
        if self.class_num == 2 and self.opt['dataset'].get('balance') == 'downsample':
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
        training_month = [get_pre_month(self.test_month, training_month_num - i) for i in range(0, training_month_num)]
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training set include {training_month}")

        return training_month


    def get_check_ticker_month(self):
        if not self.is_runtime:
            check_ticker_month = self.training_month + [self.test_month]
        else:
            check_ticker_month = self.training_month

        return check_ticker_month


    def set_selected_factor(self, selected_factor):
        self.selected_factor = selected_factor





if __name__ == '__main__':
    from utils.option import parse_options

    opt, args = parse_options('./')
    indus_type = 1
    dataset = FactorDataset(opt, 202307, indus_type)
    dataset.load_data()
