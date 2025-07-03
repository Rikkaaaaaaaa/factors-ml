import numpy as np
import pandas as pd
import os.path as osp
import traceback
import time

from utils import list2str
from dataset import build_factor_name
from dataset.sql_ops import load_ticker_by_indus, load_labels, align_factor_ticker, load_factor_by_table, check_rebalanced
from utils.mysql import cx_read_sql
from utils.ddb import read_ddb_return
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
        self.ret_name = self.opt['dataset']['ret_name']
        self.price_name = self.opt['dataset']['price_name']
        self.avg_price = self.opt['dataset']['avg_price']
        self.is_realtime = self.opt['is_realtime']
        self.indus_class = self.opt['dataset']['indus_class']
        self.pool_name = self.opt['dataset']['pool_name']
        self.factor_table = self.opt['dataset']['factor_table']
        self.rebalancing_tables = self.opt['dataset']['rebalancing_tables']
        if self.opt['dataset'].get('eval_factor_table'):
            self.eval_factor_table = self.opt['dataset']['eval_factor_table']

        # build factor names
        self.training_factor_name =  build_factor_name(self.opt['dataset']['training_factor_name']) # list(set(_train_data.columns) - set(del_column))
        self.std_factor_name = build_factor_name(self.opt['dataset']['std_factor_name'])
        self.clip_factor_name = build_factor_name(self.opt['dataset']['clip_factor_name'])
        self.log_factor_name = build_factor_name(self.opt['dataset']['log_factor_name'])

        # bool params
        self.eval_rt = self.opt['eval_rt']
        self.debug_mode = self.opt['debug']
        self.is_empty = False

        # init logging
        if self.eval_rt:
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Running eval rt mode!")
        else:
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Running training mode!")
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Task type: {self.task_type}")
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Loading indus by [{self.indus_class}] from table [static_data_industry_pool_history] + [{self.opt['dataset']['indus_table_suffix']}]]")
        if isinstance(self.trading_hours, dict):
            if self.trading_hours['am_start_time'] <= self.trading_hours['am_end_time']:
                self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Trading hours: AM [{self.trading_hours['am_start_time']}, {self.trading_hours['am_end_time']}]")
            if self.trading_hours['pm_start_time'] <= self.trading_hours['pm_end_time']:
                self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Trading hours: PM [{self.trading_hours['pm_start_time']}, {self.trading_hours['pm_end_time']}]")

    def load_data(self):
        #-----Ingest Ticker List-----#

        # read tickers from mysql
        self.tickers = self.load_ticker_list()
        if self.debug_mode:
            self.tickers = self.tickers[: min(len(self.tickers), 10)]
        if len(self.tickers) == 0: # no ticker, return None
            self.is_empty = True
            return

        #-----Ingest Factor and Return-----#

        # read data from mysql
        need_rebalanced_month = check_rebalanced(self.training_month, self.test_month) # for debug
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Checking need_rebalanced_month: {need_rebalanced_month} ")

        # restore data by month
        data = dict()
        for month in self.training_month:
            data[month] = self.load_data_from_sql(month)
        if not self.is_realtime:
            data[self.test_month] = self.load_data_from_sql(self.test_month, eval_rt=self.eval_rt)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish loading factor and return ")

        #-----Data Preprocessing-----#

        # split data into train and test set
        train_data, test_data = self.split_data(data)
        if len(train_data) == 0:
            self.is_empty = True
            return

        # get alpha (i.e.return threshold)
        self.alpha = self.get_alhpa(train_data)

        if self.task_type == 'classification':
            # make classification labels according to returns
            train_data, test_data = self.make_label(train_data, test_data)

        # filter train_data with return
        train_data = self.filter_by_label(train_data)

        # delete nan in train data
        train_data = self.del_null_value(train_data)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Start transforming data and saving preprocess params")

        # transforming data, including std, clip, save params by ticker
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
                cur_ticker = load_ticker_by_indus(self.opt, pool, self.indus_type, self.test_month)
                ticker_list.extend(cur_ticker)

            # align training and testing ticker list
            all_ticker = cur_ticker.copy()
            check_ticker_month = self.get_check_ticker_month()
            ticker_list = align_factor_ticker(self.factor_table, all_ticker, check_ticker_month, self.test_month, self.rebalancing_tables, self.training_month_num, self.io_backend)

            # ordered ticker list
            ticker_list = sorted(ticker_list)
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Total ticker number is {len(ticker_list)}")

            # check whether ticker list is null
            if len(ticker_list) == 0:
                raise FileExistsError(f"{self.test_month}_indus_{self.indus_type}: No ticker list exists in SQL")

        except Exception as e:
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Error in fetching ticker list: {e}")
            self.logger.info(traceback.format_exc())
            ticker_list = []
            # exc_type, exc_values, exc_traceback = sys.exc_info()
            # traceback.print_tb(exc_traceback)

        return ticker_list


    def load_data_from_sql(self, month, eval_rt=False):
        try:
            self.tickers = tuple(self.tickers)
            data = [pd.DataFrame()]
            # training phase / eval phase
            if eval_rt:
                database_name = list(self.eval_factor_table.keys())
                factor_table_name = self.eval_factor_table
            else:
                database_name = list(self.factor_table.keys())
                factor_table_name = self.factor_table

            i = 0
            for database in database_name:
                for table in factor_table_name[database]:
                    # load factors from sql
                    factor = load_factor_by_table(database, table, self.tickers, month, self.test_month,
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

            # del null return data
            labels = labels.dropna()
            # merge factors and labels by ticker, date, time
            data = data[['ticker', 'date', "time"] + self.training_factor_name]
            data = pd.merge(data, labels, on=['ticker', 'date', 'time'])
            data.rename(columns={'ret_' + self.ret_name: 'ret'}, inplace=True)

            # check missing tickers between return and factors
            missing_tickers = set(self.tickers) - set(data['ticker'].unique())
            # assert len(self.tickers) == len(data['ticker'].unique()), self.logger.info("SQL data missing ticker", missing_tickers)
            if len(missing_tickers) > 0:
                # raise ValueError(f"{self.test_month}_indus_{self.indus_type}: There are missing tickers in Return: {list2str(missing_tickers)}")
                print(f"{self.test_month}_indus_{self.indus_type}: There are missing tickers in Return: {list2str(missing_tickers)}")

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
        if self.is_realtime:
            test_data = pd.DataFrame(columns=train_data.columns)
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

        # len(test_data) = 0
        add_label(test_data)
        test_num = {0: (test_data['class_label'] == 0).sum(),
                    1: (test_data['class_label'] == 1).sum(),
                    2: (test_data['class_label'] == 2).sum()}
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Test label number is {test_num}")

        return train_data, test_data


    def filter_by_label(self, train_data):
        total_train_num = len(train_data)
        if self.task_type == 'classification':
            if self.class_num == 2:
                train_data = train_data.query('class_label != 2')
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Select {len(train_data) / total_train_num * 100:.2f}% train data with return={self.alpha} and class num is {self.class_num}.")
        if self.task_type == 'regression':
            train_data = train_data.query('ret.notna()')
        return train_data


    def del_null_value(self, train_data):
        data = train_data.dropna()
        if self.opt['dataset'].get('drop_null_in_training') and self.opt['dataset']['drop_null_in_training']:
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Delete {(len(train_data)-len(data))/len(train_data)*100:.2f}% null samples in train data.")
            return data
        else:
            # keep nan by default
            # 20250319: training without dropna, will improve performance
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Keep nan in training data. There are {(len(train_data) - len(data)) / len(train_data)*100:.2f}% null samples in train data.")
            # null_idx = np.isnan(test_data[list(backtest_factor_name) + ['ret']].values).all(axis=1) # all nan index
            return train_data


    def transform(self, train_data, test_data=None):
        # time cost
        # transform_start_time = time.time()
        self.train_data_list = []
        self.test_data_list = []
        self.std_params = []
        self.clip_params = []

        for ticker in self.tickers:
            temp_ticker_start_time = time.time()
            _train_data = train_data[train_data['ticker'] == ticker]
            _test_data = test_data[test_data['ticker'] == ticker]
            # data clip
            if len(self.clip_factor_name) > 0:
                # split data to train_x and test_x
                train_x = _train_data[self.clip_factor_name]
                test_x = _test_data[self.clip_factor_name]
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
                    # fefault 5%~95%
                    factor_min = np.percentile(train_x.dropna(), 5, axis=0, )
                    factor_max = np.percentile(train_x.dropna(), 95, axis=0, )

                train_x = np.clip(train_x, factor_min, factor_max)
                test_x = np.clip(test_x, factor_min, factor_max)
                _train_data.loc[:, self.clip_factor_name] = train_x.values
                _test_data.loc[:, self.clip_factor_name] = test_x.values

                # save transform params
                clip_param = pd.DataFrame(columns=['factor_name', 'min', 'max', ])
                clip_param['factor_name'] = self.clip_factor_name
                clip_param['min'] = factor_min
                clip_param['max'] = factor_max
                clip_param.insert(0, 'ticker', ticker)
                self.clip_params.append(clip_param)

            # data std
            if len(self.std_factor_name) > 0:
                # split data to train_x and test_x
                train_x = _train_data[self.std_factor_name]
                test_x = _test_data[self.std_factor_name]

                std_param = pd.DataFrame(columns=['factor_name', 'mean', 'std'])
                factor_mean = np.mean(train_x, axis=0).values
                factor_std = np.std(train_x, axis=0).values
                train_x = (train_x - factor_mean) / factor_std
                test_x = (test_x - factor_mean) / factor_std
                _train_data.loc[:, self.std_factor_name] = train_x.values
                _test_data.loc[:, self.std_factor_name] = test_x.values

                # save transform params
                std_param['factor_name'] = self.std_factor_name
                std_param['mean'] = factor_mean
                std_param['std'] = factor_std
                std_param.insert(0, 'ticker', ticker)
                self.std_params.append(std_param)

            # return clip
            if self.task_type == 'regression':
                ret_lower_bound = np.percentile(_train_data['ret'].dropna(), 1)
                ret_upper_bound = np.percentile(_train_data['ret'].dropna(), 99)
                new_ret = np.clip(_train_data['ret'].values, ret_lower_bound, ret_upper_bound)
                _train_data.loc[:, 'ret'] = new_ret

            self.train_data_list.append(_train_data)
            self.test_data_list.append(_test_data)
            # print(f'transform time cost for ticker {ticker}: {time.time() - temp_ticker_start_time}')

        self.train_data = pd.concat(self.train_data_list)
        self.test_data = pd.concat(self.test_data_list)
        # print(f'transform time cost for all tickers: {time.time() - transform_start_time}')

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
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training set include month {training_month}")

        return training_month


    def get_check_ticker_month(self):
        if not self.is_realtime:
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
