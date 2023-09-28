import numpy as np
import pandas as pd
import os.path as osp
import traceback

from utils.mysql import cx_read_sql
from utils.misc import mkdir
from utils.logger import get_root_logger

class FactorDataset():
    """
    fetch dataset in one indus_type for factor and return

    Args:
        opt(dict): config for dataset, includes following keys:
            ...
        test_month(int): month needs to be eval
        indus_type(int): one of the indus_class

    Attrs:
        train_idx, test_idx: sample index, including date and time
        test_ret: test return values
        x_train, y_train: train data
        x_test, y_test: test data
    """
    def __init__(self, opt, test_month, indus_type, cache=None, *args, **kwargs):
        self.opt = opt
        self.test_month = test_month
        self.indus_type = indus_type
        self.is_backtest = self.opt['is_backtest']
        self.indus_class = self.opt['dataset']['indus_class']
        self.class_num = self.opt['dataset']['class_num']
        self.tickers = []
        self.pool_name = self.opt['dataset']['pool_name']
        self.training_month = self.get_training_month()
        # self.lock = kwargs['lock']
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
            # fetch ticker list from mysql table
            for pool in self.pool_name:

                # lowprice stocks have no indus_type
                if self.opt['dataset']['is_highprice']:
                    indus_table = cx_read_sql('select * from static_data_industry_{}_history where {}="{}" and test_month={}'.format(pool,
                                              self.indus_class, self.indus_type, self.test_month ))
                    price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price > {} and test_month={}'.format(
                                              pool, self.opt['dataset']['avg_price'], self.test_month))
                else:
                    indus_table = cx_read_sql('select * from static_data_industry_{}_history where test_month={}'.format(pool, self.test_month))
                    price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price <= {} and test_month={}'.format(
                                               pool, self.opt['dataset']['avg_price'], self.test_month))
                ticker = set(indus_table['ticker']) & set(price_table['ticker'])
                self.tickers.extend(ticker)

            # ordered ticker list
            self.tickers = sorted(self.tickers)#[:10]
            assert len(self.tickers) > 0
            if not self.opt['dataset']['is_highprice']:
                if '000540.SZ' in self.tickers:
                    self.tickers.remove('000540.SZ')
            self.logger.info(f"Loading {len(self.tickers)} tickers in indus {self.indus_type} test_month {self.test_month}")


            # read data from mysql
            data = dict() # restore data by month
            for month in self.training_month:
                data[month] = self.load_data_from_sql(month)
                self.logger.info(f"Loading data in {month}")
            if self.is_backtest:
                data[self.test_month] = self.load_data_from_sql(self.test_month)
                self.logger.info(f"Loading data in {self.test_month} ")
            self.logger.info(f"Finish loading data with indus {self.indus_type}")

            # split data
            train_data, test_data = self.split_data(data)

            # make labels according to return
            train_data, test_data = self.make_label(train_data, test_data)

            # delete nan in train data (the nan of test data will be treated in backtest)
            train_data = self.del_null_value(train_data)

            # down_sample balancing method
            if self.opt['dataset']['balance'] == 'down_sample':
                train_data = self.down_sample(train_data)

            # std, clip, save params by ticker, reverse balancing
            if self.is_backtest:
                # returned data is in self.x_train/y_train/x_test/y_test
                self.transform(train_data, test_data)
            else:
                # returned data is in self.x_train/y_train
                self.transform_RT(train_data)
            self.logger.info(f"Finish transforming data with indus {self.indus_type}")
        except Exception as e:
            traceback.print_exc()
            self.logger.info('Error loading factor data in indus {}: '.format(self.indus_type), e)


    def load_data_from_sql(self, month):
        if self.test_month % 100 in [1, 2, 3, 7, 8, 9]:
            is_rebalanced = True
        else:
            is_rebalanced = False
        self.tickers = tuple(self.tickers)
        if is_rebalanced and month % 100 in [4, 5, 6, 10, 11, 12]:
            factor = cx_read_sql('select * from factor_{}_index_rebalancing where ticker in {}'.format(month, self.tickers))
            labels = cx_read_sql('select ticker, date, time, ret_{}  from ret_{}_index_rebalancing where ticker in {}'.format(
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
        # classification of return, 0 for down, 1 for up and 2 for stable
        def label_mask(df):
            df['class_label'] = df['ret'].mask(df['ret'] <= -1 * alpha, 0).mask(df['ret'] >= alpha, 1) \
                .mask((-1 * alpha < df['ret']) & (df['ret'] < alpha), 2)

        alpha = self.opt['dataset']['alpha']
        label_mask(train_data)
        if self.is_backtest:
            label_mask(test_data)

        # 顺序未定
        if self.class_num == 2:
            train_data =  train_data.query('class_label < 2')

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
        self.x_train, self.y_train, self.x_test, self.y_test = [], [], [], []  # np.array for training
        self.train_position = dict()  # record idx for backtest
        self.test_position = dict()
        self.test_idx = dict()         # record time date in test data
        self.test_ret = dict()         # record return in test data
        train_cur, test_cur = 0, 0     # record data cursor for backtest

        for ticker in self.tickers:
            _train_data = train_data.query('ticker==@ticker')
            _test_data = test_data.query('ticker==@ticker')
            self.test_idx[ticker] = dict()
            self.test_ret[ticker] = _test_data['ret']

            # record time date index and test return
            self.train_position[ticker] = [train_cur, train_cur + len(_train_data)]
            self.test_position[ticker] = [test_cur, test_cur + len(_test_data)]
            self.test_idx[ticker]['date'], self.test_idx[ticker]['time'] = _test_data['date'], _test_data['time']

            train_cur += len(_train_data)
            test_cur += len(_test_data)

            # split to x and y
            factor_names = list(set(_train_data.columns) - set(del_column))
            transform_params = pd.DataFrame(index=factor_names, columns=['min', 'max', 'mean', 'std'])
            train_x = _train_data.drop(del_column, axis=1).values
            train_y = _train_data['class_label'].values
            test_x = _test_data.drop(del_column, axis=1).values
            test_y = _test_data['class_label'].values  # test 应该再bt模式下设置为0

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
            transform_params['mean'] = factor_mean
            transform_params['std'] = factor_std
            transform_params['min'] = factor_min
            transform_params['max'] = factor_max
            save_folder = osp.join(self.opt['path']['preprocess_root'], str(self.test_month))
            mkdir(save_folder)
            svg_path = osp.join(save_folder,'{}.csv'.format(ticker))
            transform_params.to_csv(svg_path)

            self.x_train.append(train_x)
            self.y_train.append(train_y)
            self.x_test.append(test_x)
            self.y_test.append(test_y)

        self.x_train = np.concatenate(self.x_train, axis=0)
        self.y_train = np.concatenate(self.y_train, axis=0)
        self.x_test = np.concatenate(self.x_test, axis=0)
        self.y_test = np.concatenate(self.y_test, axis=0)

        # balance data by reversing
        if self.class_num==2 and self.opt['dataset']['balance']=='reverse':
            self.x_train = np.concatenate([self.x_train, -1*self.x_train], axis=0)
            reversed_y = np.zeros_like(self.y_train)
            reversed_y[self.y_train==0] = 1
            self.y_train = np.concatenate([self.y_train, reversed_y], axis=0)

    def transform_RT(self, train_data):
        del_column = ['time', 'ticker', 'date', 'class_label', 'ret']          # deli columns in data
        self.x_train, self.y_train = [], []  # np.array for training
        self.train_position = dict()  # record idx for backtest
        train_cur = 0
        for ticker in self.tickers:
            _train_data = train_data.query('ticker==@ticker')

            # record train data pos by ticker
            self.train_position[ticker] = [train_cur, train_cur + len(_train_data)]
            train_cur += len(_train_data)

            # split to x and y
            factor_names = list(set(_train_data.columns) - set(del_column))
            transform_params = pd.DataFrame(index=factor_names, columns=['min', 'max', 'mean', 'std'])
            train_x = _train_data.drop(del_column, axis=1).values
            train_y = _train_data['class_label'].values

            # data std
            factor_mean = np.mean(train_x, axis=0)
            factor_std = np.std(train_x, axis=0)
            train_x = (train_x - factor_mean) / factor_std

            # data clip
            factor_min = np.percentile(train_x, 5, axis=0,)
            factor_max = np.percentile(train_x, 95, axis=0,)
            train_x = np.clip(train_x, factor_min, factor_max)

            # save transform params
            transform_params['mean'] = factor_mean
            transform_params['std'] = factor_std
            transform_params['min'] = factor_min
            transform_params['max'] = factor_max
            save_folder = osp.join(self.opt['path']['preprocess_root'], str(self.test_month))
            mkdir(save_folder)
            svg_path = osp.join(save_folder,'{}.csv'.format(ticker))
            transform_params.to_csv(svg_path)

            self.x_train.append(train_x)
            self.y_train.append(train_y)

        self.x_train = np.concatenate(self.x_train, axis=0)
        self.y_train = np.concatenate(self.y_train, axis=0)

        # balance data by reversing
        if self.class_num==2 and self.opt['dataset']['balance']=='reverse':
            self.x_train = np.concatenate([self.x_train, -1*self.x_train], axis=0)
            reversed_y = np.zeros_like(self.y_train)
            reversed_y[self.y_train==0] = 1
            self.y_train = np.concatenate([self.y_train, reversed_y], axis=0)



if __name__ == '__main__':
    from utils.option import parse_options

    opt, args = parse_options('./')
    indus_type = 1
    dataset = FactorDataset(opt, 202307, indus_type)
    dataset.load_data()
