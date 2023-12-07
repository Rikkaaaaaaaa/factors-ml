import numpy as np
import pandas as pd
import os.path as osp
import traceback
import sys

from utils import list2str
from dataset import build_factor_name
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
        self.price_name = self.opt['dataset']['price_name']
        self.is_runtime = self.opt['is_runtime']
        self.indus_class = self.opt['dataset']['indus_class']
        self.class_num = self.opt['dataset']['class_num']
        self.pool_name = self.opt['dataset']['pool_name']
        self.factor_db = self.opt['dataset']['factor_db']
        self.factor_table = self.opt['dataset']['factor_table']
        self.training_factor_name =  build_factor_name(self.opt['dataset']['training_factor_name']) # list(set(_train_data.columns) - set(del_column))
        self.std_factor_name = build_factor_name(self.opt['dataset']['std_factor_name'])
        self.clip_factor_name = build_factor_name(self.opt['dataset']['clip_factor_name'])
        self.log_factor_name = build_factor_name(self.opt['dataset']['log_factor_name'])
        self.reversed_factor_name = build_factor_name(self.opt['dataset']['reversed_factor_name'])
        self.training_month = self.get_training_month()
        self.debug_mode = self.opt['debug']
        self.is_empty = False
        # logging file
        logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)


    def get_training_month(self):
        if self.test_month % 100 == 1:
            training_month = [(self.test_month)-100+9, (self.test_month)-100+10, (self.test_month)-100+11]
        elif self.test_month % 100 == 2:
            training_month = [(self.test_month)-100+9, (self.test_month) - 100 + 10, self.test_month-1]
        elif self.test_month % 100 == 3:
            training_month = [(self.test_month) - 100 + 9, self.test_month - 2, self.test_month - 1]
        else:
            training_month = [ self.test_month - 3, self.test_month - 2, self.test_month - 1]
        return training_month


    def set_selected_factor(self, selected_factor):
        self.selected_factor = selected_factor


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
        data = dict() # restore data by month
        for month in self.training_month:
            data[month] = self.load_data_from_sql(month)
        if not self.is_runtime:
            data[self.test_month] = self.load_data_from_sql(self.test_month)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish loading data")


        # Data Preprocessing
        # split data into train and test set
        train_data, test_data = self.split_data(data)
        if len(train_data) == 0:
            self.is_empty = True
            return

        # make labels according to returns
        train_data, test_data = self.make_label(train_data, test_data)
        # delete nan in train data
        train_data = self.del_null_value(train_data)
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
                if self.price_name == 'highprice':
                    indus_table = cx_read_sql('select * from static_data_industry_{}_history where {}="{}" and test_month={}'.format(pool,
                                               self.indus_class, self.indus_type,self.test_month))
                    price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price > {} and test_month={}'.format(
                                               pool, self.opt['dataset']['avg_price'], self.test_month))
                if self.price_name == 'lowprice':
                    # Note that lowprice stocks have no indus_type, default is 0
                    indus_table = cx_read_sql('select * from static_data_industry_{}_history where test_month={}'.format(pool, self.test_month))
                    price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price <= {} and test_month={}'.format(pool, self.opt['dataset']['avg_price'], self.test_month))

                cur_ticker = set(indus_table['ticker']) & set(price_table['ticker'])

                # Align training and testing ticker list
                if not self.is_runtime:
                    check_ticker_month = self.training_month + [self.test_month]
                else:
                    check_ticker_month = self.training_month
                for month in check_ticker_month:
                    if self.test_month % 100 in [1, 2, 3, 7, 8, 9]:
                        is_rebalanced = True
                    else:
                        is_rebalanced = False
                    if is_rebalanced and month % 100 in [4, 5, 6, 10, 11, 12]:
                        factor_ticker = cx_read_sql(f'select distinct ticker from {self.factor_table}_{month}_index_rebalancing', database=self.factor_db)
                    else:
                        factor_ticker = cx_read_sql(f'select distinct ticker from {self.factor_table}_{month}', database=self.factor_db)
                    cur_ticker = cur_ticker & set(factor_ticker['ticker'])


                ticker_list.extend(cur_ticker)

            # ordered ticker list
            ticker_list = sorted(ticker_list)
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Total ticker number is {len(ticker_list)}")
            # delete some tickers
            if self.price_name == 'lowprice':
                if '000540.SZ' in ticker_list:
                    ticker_list.remove('000540.SZ')

            # check whether ticker list is null
            if len(ticker_list) == 0:
                raise ValueError(f"{self.test_month}_indus_{self.indus_type}: No ticker list exists in SQL")

        except Exception as e:
            # exc_type, exc_values, exc_traceback = sys.exc_info()
            # traceback.print_tb(exc_traceback)
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Error in fetching ticker list!")
            self.logger.info(traceback.format_exc())

        return ticker_list


    def load_data_from_sql(self, month):
        try:
            if self.test_month % 100 in [1, 2, 3, 7, 8, 9]:
                is_rebalanced = True
            else:
                is_rebalanced = False

            self.tickers = tuple(self.tickers)
            if is_rebalanced and month % 100 in [4, 5, 6, 10, 11, 12]:
                factor = cx_read_sql('select * from factor_{}_index_rebalancing where ticker in {}'.format(month, self.tickers))
                labels = cx_read_sql('select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format(self.opt['dataset']['ret_name'], month, self.tickers))
            else:
                factor = cx_read_sql('select * from {}_{} where ticker in {}'.format(self.factor_table, month, self.tickers), database=self.factor_db)
                labels = cx_read_sql('select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format(self.opt['dataset']['ret_name'], month, self.tickers))

            # log factor
            def get_log_factor_df(df_factors):
                df_factors[df_factors > 0] = np.log(df_factors[df_factors > 0] + 1)
                df_factors[df_factors < 0] = -np.log(-df_factors[df_factors < 0] + 1)
                return df_factors
            for log_factor in self.log_factor_name:
                factor.loc[:, log_factor] = get_log_factor_df(factor[log_factor].values)

            # merge factors and labels by ticker, date, time
            data = pd.DataFrame()
            data = pd.merge(factor, labels, on=['ticker', 'date', 'time'])
            data.rename(columns={'ret_' + self.opt['dataset']['ret_name']: 'ret'}, inplace=True)

            # check missing tickers between return and factors
            missing_tickers = set(self.tickers)-set(data['ticker'].unique())
            #assert len(self.tickers) == len(data['ticker'].unique()), self.logger.info("SQL data missing ticker", missing_tickers)
            if len(missing_tickers) > 0:
                self.logger.warning(f'{self.test_month}_indus_{self.indus_type}: There are missing tickers in SQL!')
                self.logger.warning(f'{self.test_month}_indus_{self.indus_type}: {list2str(missing_tickers)}')

            # check Whether data is None
            if len(data) == 0:
                raise ValueError(f"{self.test_month}_indus_{self.indus_type}: No factor or return data exists in SQL")

        except Exception as e:
            self.logger.info(f'{self.test_month}_indus_{self.indus_type}: Error in fetching factor and return from SQL')
            self.logger.info(traceback.format_exc())

        return data


    def split_data(self, data):
        # split month data to train/test
        train_data = pd.concat([data[m] for m in self.training_month])
        if self.is_runtime:
            test_data = pd.DataFrame()
        else:
            test_data = data[self.test_month]
        return train_data, test_data


    def make_label(self, train_data, test_data):
        '''
        classification of return, 0 for down, 1 for up and 2 for stable
        '''
        def add_label(df):
            df['class_label'] = df['ret'].mask(df['ret'] <= -1 * alpha, 0).mask(df['ret'] >= alpha, 1) \
                .mask((-1 * alpha < df['ret']) & (df['ret'] < alpha), 2)

        total_train_num = len(train_data)
        alpha = self.opt['dataset']['alpha']
        add_label(train_data)
        # filter
        if self.class_num == 2:
            train_data =  train_data.query('class_label != 2')
        self.logger.info(f"Select {len(train_data)/total_train_num * 100:.2f}% train data with return={alpha}.")

        return train_data, test_data


    def del_null_value(self, train_data):
        data = train_data.dropna()
        self.logger.info(f"Delete {(len(train_data)-len(data))/len(data):.2f} null samples in train data.")
        return data


    def down_sample(self, data):
        up_num = len(data.query('class_label==0'))
        down_num = len(data.query('class_label==1'))
        sample_num = min(up_num, down_num)
        up_data = data.query('class_label==0').sample(n=sample_num)
        down_data = data.query('class_label==1').sample(n=sample_num)
        data = pd.concat([up_data, down_data], ignore_index=True)
        return data


    def transform(self, train_data, test_data=None):
        del_column = ['time', 'ticker', 'date', 'class_label', 'ret']  # del columns in data
        self.train_data = train_data.reset_index()
        self.test_data = test_data.reset_index()
        self.std_params = []
        self.clip_params = []

        for ticker in self.tickers:
            _train_data = self.train_data.query('ticker==@ticker')
            _test_data = self.test_data.query('ticker==@ticker')

            # split data to train_x and test_x
            train_x = _train_data[self.std_factor_name]
            test_x = _test_data[self.std_factor_name]

            # data std
            std_param = pd.DataFrame(columns=['factor_name', 'mean', 'std'])
            factor_mean = np.mean(train_x, axis=0).values
            factor_std = np.std(train_x, axis=0).values
            train_x = (train_x - factor_mean) / factor_std
            test_x = (test_x - factor_mean) / factor_std
            self.train_data.loc[_train_data.index, self.std_factor_name] = train_x.values
            self.test_data.loc[_test_data.index, self.std_factor_name] = test_x.values

            # data clip
            clip_param = pd.DataFrame(columns=['factor_name', 'min', 'max', ])
            train_x = _train_data[self.clip_factor_name]
            test_x = _test_data[self.clip_factor_name]
            factor_min = np.percentile(train_x, 5, axis=0,)
            factor_max = np.percentile(train_x, 95, axis=0,)
            train_x = np.clip(train_x, factor_min, factor_max)
            test_x = np.clip(test_x, factor_min, factor_max)
            self.train_data.loc[_train_data.index, self.clip_factor_name] = train_x
            self.test_data.loc[_test_data.index, self.clip_factor_name] = test_x

            # save transform params
            std_param['factor_name'] = self.std_factor_name
            std_param['mean'] = factor_mean
            std_param['std'] = factor_std
            clip_param['factor_name'] = self.clip_factor_name
            clip_param['min'] = factor_min
            clip_param['max'] = factor_max
            std_param.insert(0, 'ticker',ticker)
            clip_param.insert(0, 'ticker', ticker)
            self.std_params.append(std_param)
            self.clip_params.append(clip_param)

        # save preprocess params
        save_folder = self.opt['path']['preprocess_path'][self.test_month]
        # std
        std_path = osp.join(save_folder, f"std_params_indus{self.indus_type}.csv")
        self.std_params = pd.concat(self.std_params)
        self.std_params.to_csv(std_path, index=False)
        # clip
        clip_path = osp.join(save_folder, f"clip_params_indus{self.indus_type}.csv")
        self.clip_params = pd.concat(self.clip_params)
        self.clip_params.to_csv(clip_path, index=False)


    def transform_runtime(self, train_data):
        del_column = ['time', 'ticker', 'date', 'class_label', 'ret']  # del columns in data
        self.train_data = train_data.reset_index()

        self.std_params = []
        self.clip_params = []

        for ticker in self.tickers:
            _train_data = self.train_data.query('ticker==@ticker')

            # split data to train_x and test_x
            train_x = _train_data[self.std_factor_name]

            # data std
            std_param = pd.DataFrame(columns=['factor_name', 'mean', 'std'])
            factor_mean = np.mean(train_x, axis=0).values
            factor_std = np.std(train_x, axis=0).values
            train_x = (train_x - factor_mean) / factor_std
            self.train_data.loc[_train_data.index, self.std_factor_name] = train_x.values

            # data clip
            clip_param = pd.DataFrame(columns=['factor_name', 'min', 'max', ])
            train_x = _train_data[self.clip_factor_name]
            factor_min = np.percentile(train_x, 5, axis=0, )
            factor_max = np.percentile(train_x, 95, axis=0, )
            train_x = np.clip(train_x, factor_min, factor_max)
            self.train_data.loc[_train_data.index, self.clip_factor_name] = train_x


            # save transform params
            std_param['factor_name'] = self.std_factor_name
            std_param['mean'] = factor_mean
            std_param['std'] = factor_std
            clip_param['factor_name'] = self.clip_factor_name
            clip_param['min'] = factor_min
            clip_param['max'] = factor_max
            std_param.insert(0, 'ticker', ticker)
            clip_param.insert(0, 'ticker', ticker)
            self.std_params.append(std_param)
            self.clip_params.append(clip_param)

        # save preprocess params
        save_folder = self.opt['path']['preprocess_path'][self.test_month]
        # std
        std_path = osp.join(save_folder, f"std_params_indus{self.indus_type}.csv")
        self.std_params = pd.concat(self.std_params)
        self.std_params.to_csv(std_path, index=False)
        # clip
        clip_path = osp.join(save_folder, f"clip_params_indus{self.indus_type}.csv")
        self.clip_params = pd.concat(self.clip_params)
        self.clip_params.to_csv(clip_path, index=False)

    def rebalance_training_data(self):
        # balance training data
        if self.class_num == 2 and self.opt['dataset']['balance'] == 'reverse':
            train_data_copy = self.train_data.copy()
            train_data_copy[self.reversed_factor_name] = -1 * train_data_copy[self.reversed_factor_name]
            train_y = train_data_copy['class_label'].values
            reversed_y = np.zeros_like(train_y)
            up_idx = (train_y==0)
            down_idx = (train_y==1)
            reversed_y[up_idx] = 1
            reversed_y[down_idx] = 0
            #reversed_y = pd.DataFrame(reversed_y, columns='class_label')
            train_data_copy['class_label'] = reversed_y
            #train_data_copy['augment'] = 1
            augment = pd.DataFrame(columns=['augment'], data=np.ones(len(reversed_y)))
            train_data_copy = pd.concat([train_data_copy,augment], axis=1)
            #self.train_data['augment'] = 0
            augment = pd.DataFrame(columns=['augment'], data=np.zeros(len(reversed_y)))
            self.train_data = pd.concat([self.train_data, augment], axis=1)
            self.train_data = pd.concat([self.train_data, train_data_copy], ignore_index=True)

        if self.class_num == 2 and self.opt['dataset']['balance'] == 'downsample':
            self.train_data = self.down_sample(self.train_data)


if __name__ == '__main__':
    from utils.option import parse_options

    opt = parse_options('./')
    indus_type = 1
    dataset = FactorDataset(opt, 202307, indus_type)
    dataset.load_data()
