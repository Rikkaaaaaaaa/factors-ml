import numpy as np
import pandas as pd
import os.path as osp
import traceback

from utils import list2str
from dataset import build_factor_name
from utils.mysql import cx_read_sql
from utils.logger import get_root_logger
from utils.registry import DATASET_REGISTRY


@DATASET_REGISTRY.register()
class SQLDataset():
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
        # logging file
        logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)


    def get_training_month(self):
        if self.test_month % 100 == 1:
            training_month = [(self.test_month)-100+9, (self.test_month)-100+10, (self.test_month)-100+11]
        elif self.test_month % 100 == 2:
            training_month = [(self.test_month)-100+9, (self.test_month) - 100 + 10, self.test_month-1]
        elif self.test_month % 100 == 3:
            training_month = [(self.test_month) - 100 + 10, self.test_month - 2, self.test_month - 1]
        else:
            training_month = [ self.test_month - 3, self.test_month - 2, self.test_month - 1]
        return training_month


    def set_selected_factor(self, selected_factor):
        self.selected_factor = selected_factor


    def load_data(self):
        # ingest ticker list
        # read tickers from mysql
        self.tickers = self.load_ticker_list()
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Total ticker number is {len(self.tickers)}")

        # check ticker list is null
        self.is_empty = False
        if len(self.tickers) == 0:
            self.is_empty = True
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: No ticker data in {self.test_month} ")
            return

        # ingest factor and return
        # read data from mysql
        data = dict() # restore data by month
        for month in self.training_month:
            data[month] = self.load_data_from_sql(month)
            data[self.test_month] = self.load_data_from_sql(self.test_month)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish loading data")

        # data preprocessing
        # split data into train and test set
        train_data, test_data = self.split_data(data)
        # # make labels according to returns
        # train_data, test_data = self.make_label(train_data, test_data)
        # # delete nan in train data
        # train_data = self.del_null_value(train_data)
        # transforming data, including std, clip, save params by ticker
        self.transform(train_data, test_data)
        # rebalance training data
        #self.rebalance_training_data()
        # logging
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish transforming data")
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training data num is {len(train_data)} and test data num is {len(test_data)}")


    def load_ticker_list(self):
        # Fetch ticker list from mysql table
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

            ticker = set(indus_table['ticker']) & set(price_table['ticker'])
            # Align ticker list
            for month in self.training_month + [self.test_month]:
                factor_ticker = cx_read_sql('select distinct ticker from {}_{}'.format(self.factor_table, month), database=self.factor_db)
                ticker = ticker & set(factor_ticker['ticker'])
            ticker_list.extend(ticker)

        # ordered ticker list
        ticker_list = sorted(ticker_list)
        # delete some tickers
        if self.price_name == 'lowprice':
            if '000540.SZ' in ticker_list:
                ticker_list.remove('000540.SZ')

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

            else:
                factor = cx_read_sql('select * from {}_{} where ticker in {}'.format(self.factor_table, month, self.tickers), database=self.factor_db)

            labels = pd.DataFrame()
            for r in ['15s', '60s', '120s', '300s']:
                tmp_label = cx_read_sql(
                    'select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format(r, month, self.tickers))

                self.ret_15s = cx_read_sql('select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format('15s', month, self.tickers))
                self.ret_60s = cx_read_sql('select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format('60s', month, self.tickers))
                self.ret_120s = cx_read_sql('select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format('120s', month, self.tickers))
                self.ret_300s = cx_read_sql('select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format('300s', month, self.tickers))

            # log factor
            def get_log_factor_df(df_factors):
                df_factors[df_factors > 0] = np.log(df_factors[df_factors > 0] + 1)
                df_factors[df_factors < 0] = -np.log(-df_factors[df_factors < 0] + 1)
                return df_factors
            for log_factor in self.log_factor_name:
                factor.loc[:, log_factor] = get_log_factor_df(factor[log_factor].values)

            # Merge factors and labels by ticker, date, time
            data = factor
            # Check missing tickers
            missing_tickers = set(self.tickers)-set(data['ticker'].unique())
            #assert len(self.tickers) == len(data['ticker'].unique()), self.logger.info("SQL data missing ticker", missing_tickers)
            if len(missing_tickers) > 0:
                self.logger.info(f'{self.test_month}_indus_{self.indus_type}: There are missing tickers in SQL!')
                self.logger.info(f'{self.test_month}_indus_{self.indus_type}: {list2str(missing_tickers)}')


        except Exception as e:
            traceback.print_exc()
            self.logger.info(f'{self.test_month}_indus_{self.indus_type}: Error fetching factor and ret fro SQL', e)

        return data


    def split_data(self, data):
        # split month data to train/test
        train_data = pd.concat([data[m] for m in self.training_month])
        test_data = data[self.test_month]
        return train_data, test_data


    def make_label(self, train_data, test_data):
        '''
        classification of return, 0 for down, 1 for up and 2 for stable
        '''
        def add_label(df):
            df['class_label'] = df['ret'].mask(df['ret'] <= -1 * alpha, 0).mask(df['ret'] >= alpha, 1) \
                .mask((-1 * alpha < df['ret']) & (df['ret'] < alpha), 2)

        alpha = self.opt['dataset']['alpha']
        add_label(train_data)
        add_label(test_data)
        # filter
        if self.class_num == 2:
            train_data =  train_data.query('class_label != 2')
        return train_data, test_data


    def del_null_value(self, train_data):
        return train_data.dropna()


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
        self.transform_params = []

        for ticker in self.tickers:
            _train_data = self.train_data.query('ticker==@ticker')
            _test_data = self.test_data.query('ticker==@ticker')
            # split data to train_x and test_x
            transform_param = pd.DataFrame(columns=['factor_name', 'min', 'max', 'mean', 'std'])
            train_x = _train_data[self.std_factor_name]
            test_x = _test_data[self.std_factor_name]
            # Data std
            factor_mean = np.mean(train_x, axis=0)
            factor_std = np.std(train_x, axis=0)
            train_x = (train_x - factor_mean) / factor_std
            test_x = (test_x - factor_mean) / factor_std
            self.train_data.loc[_train_data.index, self.std_factor_name] = train_x.values
            self.test_data.loc[_test_data.index, self.std_factor_name] = test_x.values

            # Data clip
            train_x = _train_data[self.clip_factor_name]
            test_x = _test_data[self.clip_factor_name]
            factor_min = np.percentile(train_x, 5, axis=0,)
            factor_max = np.percentile(train_x, 95, axis=0,)
            train_x = np.clip(train_x, factor_min, factor_max)
            test_x = np.clip(test_x, factor_min, factor_max)
            self.train_data.loc[_train_data.index, self.clip_factor_name] = train_x
            self.test_data.loc[_test_data.index, self.clip_factor_name] = test_x




