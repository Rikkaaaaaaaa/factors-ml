import numpy as np
import pandas as pd
import os.path as osp
import traceback

from utils.mysql import cx_read_sql
from utils.logger import get_root_logger
from dataset import factor_all

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
        self.is_backtest = self.opt['is_backtest']
        self.indus_class = self.opt['dataset']['indus_class']
        self.class_num = self.opt['dataset']['class_num']
        self.pool_name = self.opt['dataset']['pool_name']
        self.tickers = []
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


    def load_data(self):
        try:
            # read tickers from mysql
            self.load_ticker_list()
            if self.is_empty:
                return
            # read data from mysql
            data = dict() # restore data by month
            for month in self.training_month:
                data[month] = self.load_data_from_sql(month)
            if self.is_backtest:
                data[self.test_month] = self.load_data_from_sql(self.test_month)
                #self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Loading data in {self.test_month} ")
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish loading data")
            # split data
            train_data, test_data = self.split_data(data)
            # make labels according to return
            train_data, test_data = self.make_label(train_data, test_data)
            # delete nan in train data
            train_data = self.del_null_value(train_data)
            # down_sample balancing method
            if self.opt['dataset']['balance'] == 'down_sample':
                train_data = self.down_sample(train_data)
            # std, clip, save params by ticker,
            if self.is_backtest:
                self.transform(train_data, test_data)
            else:
                self.transform_RT(train_data)
            # training data balancing
            self.rebalance_training_data()

            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish transforming data")
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Train data num is {len(train_data)} and test data num is {len(test_data)}")

        except Exception as e:
            traceback.print_exc()
            self.logger.info(f'{self.test_month}_indus_{self.indus_type}: Error loading factor data', e)


    def load_ticker_list(self):
        # fetch ticker list from mysql table
        for pool in self.pool_name:
            if self.price_name == 'highprice':
                indus_table = cx_read_sql('select * from static_data_industry_{}_history where {}="{}" and test_month={}'.format(pool,
                                           self.indus_class, self.indus_type,self.test_month))
                price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price > {} and test_month={}'.format(
                                           pool, self.opt['dataset']['avg_price'], self.test_month))
            if self.price_name == 'lowprice':
                # note that lowprice stocks have no indus_type, default is 0
                indus_table = cx_read_sql('select * from static_data_industry_{}_history where test_month={}'.format(pool, self.test_month))
                price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price <= {} and test_month={}'.format(
                                           pool, self.opt['dataset']['avg_price'], self.test_month))
            ticker = set(indus_table['ticker']) & set(price_table['ticker'])
            self.tickers.extend(ticker)

        # ordered ticker list
        self.tickers = sorted(self.tickers)[:10]
        # check ticker list is null
        if len(self.tickers) == 0:
            self.is_empty = True
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: no ticker data in {self.test_month} ")
            return
        else:
            self.is_empty = False
        # delete some tickers
        if self.price_name == 'lowprice':
            if '000540.SZ' in self.tickers:
                self.tickers.remove('000540.SZ')
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Total ticker number is {len(self.tickers)}")


    def load_data_from_sql(self, month):
        if self.test_month % 100 in [1, 2, 3, 7, 8, 9]:
            is_rebalanced = True
        else:
            is_rebalanced = False
        self.tickers = tuple(self.tickers)
        if is_rebalanced and month % 100 in [4, 5, 6, 10, 11, 12]:
            factor = cx_read_sql('select * from factor_{}_index_rebalancing where ticker in {}'.format(month, self.tickers))
            labels = cx_read_sql('select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format(
                                        self.opt['dataset']['ret_name'], month, self.tickers))
        else:
            factor = cx_read_sql('select * from factor_{} where ticker in {}'.format(month, self.tickers))
            labels = cx_read_sql('select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format(
                                        self.opt['dataset']['ret_name'], month, self.tickers))

        # log factor
        log_factors = pd.read_csv('./log_factor_list.csv', header=None, names=['log_factor'])['log_factor']
        def get_log_factor_df(df_factors):
            df_factors[df_factors > 0] = np.log(df_factors[df_factors > 0] + 1)
            df_factors[df_factors < 0] = -np.log(-df_factors[df_factors < 0] + 1)
            return df_factors
        for log_factor in log_factors:
            factor.loc[:, log_factor] = get_log_factor_df(factor[log_factor].values)

        # merge factors and labels by ticker, date, time
        data = pd.merge(factor, labels, on=['ticker', 'date', 'time'])
        data.rename(columns={'ret_' + self.opt['dataset']['ret_name']: 'ret'}, inplace=True)
        # check missing tickers
        missing_tickers = set(self.tickers)-set(data['ticker'].unique())
        assert len(self.tickers) == len(data['ticker'].unique()), self.logger.info("SQL data missing ticker", missing_tickers)
        return data


    def split_data(self, data):
        # split month data to train/test
        train_data = pd.concat([data[m] for m in self.training_month])
        if self.is_backtest:
            test_data = data[self.test_month]
        else:
            test_data = pd.DataFrame()
        return train_data, test_data


    def make_label(self, train_data, test_data):
        '''
        classification of return, 0 for down, 1 for up and 2 for stable
        '''
        def label_mask(df):
            df['class_label'] = df['ret'].mask(df['ret'] <= -1 * alpha, 0).mask(df['ret'] >= alpha, 1) \
                .mask((-1 * alpha < df['ret']) & (df['ret'] < alpha), 2)

        alpha = self.opt['dataset']['alpha']
        label_mask(train_data)
        if self.is_backtest:
            label_mask(test_data)
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
        del_column = ['time', 'ticker', 'date', 'class_label', 'ret']          # deli columns in data
        factor_names = factor_all  # list(set(_train_data.columns) - set(del_column))
        self.train_data = train_data.reset_index()
        self.test_data = test_data.reset_index()
        self.transform_params = []

        for ticker in self.tickers:
            _train_data = self.train_data.query('ticker==@ticker')
            _test_data = self.test_data.query('ticker==@ticker')
            # split to x and y
            transform_param = pd.DataFrame(columns=['factor_name', 'min', 'max', 'mean', 'std'])
            train_x = _train_data[factor_names].values
            test_x = _test_data[factor_names].values
            # data std
            factor_mean = np.mean(train_x, axis=0)
            factor_std = np.std(train_x, axis=0)
            train_x = (train_x - factor_mean) / factor_std
            test_x = (test_x - factor_mean) / factor_std
            # data clip
            factor_min = np.percentile(train_x, 5, axis=0,)
            factor_max = np.percentile(train_x, 95, axis=0,)
            train_x = np.clip(train_x, factor_min, factor_max)
            test_x = np.clip(test_x, factor_min, factor_max)
            # save transform params
            transform_param['factor_name'] = factor_all
            transform_param['mean'] = factor_mean
            transform_param['std'] = factor_std
            transform_param['min'] = factor_min
            transform_param['max'] = factor_max
            transform_param.insert(0, 'ticker',ticker)
            self.transform_params.append(transform_param)
            # restore data at original position
            self.train_data.loc[_train_data.index, factor_all] = train_x
            self.test_data.loc[_test_data.index, factor_all] = test_x

        # save preprocess params
        save_folder = self.opt['path']['preprocess_path'][self.test_month]
        svg_path = osp.join(save_folder, f"preprocess_params_indus{self.indus_type}.csv")
        self.transform_params = pd.concat(self.transform_params)
        self.transform_params.to_csv(svg_path, index=False)

    def rebalance_training_data(self):
        # balance training data
        if self.class_num == 2 and self.opt['dataset']['balance'] == 'reverse':
            train_data_copy = self.train_data.copy()
            train_data_copy[factor_all] = -1 * train_data_copy[factor_all]
            train_y = train_data_copy['class_label']
            reversed_y = np.zeros_like(train_y)
            up_idx = (train_y==0)
            down_idx = (train_y==1)
            reversed_y[up_idx] = 1
            reversed_y[down_idx] = 0
            train_data_copy['class_label'] = reversed_y
            train_data_copy['augment'] = 1
            self.train_data['augment'] = 0
            self.train_data = pd.concat([self.train_data, train_data_copy], ignore_index=True)

        if self.class_num == 2 and self.opt['dataset']['balance'] == 'downsample':
            self.train_data = self.down_sample(self.train_data)


if __name__ == '__main__':
    from utils.option import parse_options

    opt, args = parse_options('./')
    indus_type = 1
    dataset = FactorDataset(opt, 202307, indus_type)
    dataset.load_data()
