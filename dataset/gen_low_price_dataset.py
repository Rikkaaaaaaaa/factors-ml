import numpy as np
import pandas as pd
import os.path as osp
import traceback
import sys

from utils import list2str
from dataset import build_factor_name_low_price
from dataset.sql_ops import load_ticker_by_price_group, align_factor_ticker, load_factor_by_table_low_price, get_sop_fill_flag_ddb
from utils.mysql import cx_read_sql
from utils.logger import get_root_logger
from utils.registry import DATASET_REGISTRY
import multiprocessing
import time
from concurrent.futures import ThreadPoolExecutor


@DATASET_REGISTRY.register()
class GenDatasetLowPrice:
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
        self.is_empty = False
        self.indus_type = indus_type
        # logging file
        logger_name = f"month{test_month}_price_group_{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)

        # training_month
        self.training_month_num = 3
        self.training_month = self.get_training_month(self.training_month_num)
        self.pool_name = self.opt['dataset']['pool_name']

        # factor table
        self.factor_table = self.opt['dataset']['factor_table']
        self.rebalancing_tables = self.opt['dataset']['rebalancing_tables']
        self.database_name = list(self.factor_table.keys())

        # build factor names
        self.training_factor_name =  build_factor_name_low_price(self.opt['dataset']['training_factor_name']) # list(set(_train_data.columns) - set(del_column))
        self.std_factor_name = build_factor_name_low_price(self.opt['dataset']['std_factor_name'])
        self.clip_factor_name = build_factor_name_low_price(self.opt['dataset']['clip_factor_name'])
        self.log_factor_name = build_factor_name_low_price(self.opt['dataset']['log_factor_name'])

        # other settings from opt
        self.io_backend = self.opt['dataset']['io_backend']
        self.is_realtime = self.opt['is_realtime']
        self.test_month_new = test_month if not self.is_realtime else self.training_month[-1]   # if is_realtime: use latest month as new test month

        # ticker list
        self.ticker_list = self.load_ticker_list()
        self.logger.info(f"{self.test_month}_price_group_{self.indus_type}: ticker number={len(self.ticker_list)}")

    def get_training_month(self, training_month_num=3):
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

        training_month = [get_pre_month(self.test_month, training_month_num - i) for i in range(0, training_month_num)]
        self.logger.info(f"{self.test_month}_price_group_{self.indus_type}: Training set include month {training_month}")
        return training_month

    def load_factor_data_by_ticker(self, ticker):
        data = dict() # restore data by month
        for month in self.training_month:
            data[month] = self.load_data_from_sql([ticker], month, self.pool_name)
        train_data = pd.concat([data[m] for m in self.training_month])
        test_data = self.load_data_from_sql([ticker], self.test_month_new, self.pool_name)
        return train_data, test_data

    def load_factor_data(self):
        print(f'start loading factor data for price_group {self.indus_type}...')
        start_time = time.time()

        # Ingest Ticker List
        # read tickers from mysql
        if self.ticker_list == 0: # no ticker, return None
            self.is_empty = True
            return

        # load factor data (multiprocessing)
        n_jobs = self.opt['n_jobs_read_data']
        # with multiprocessing.Pool(processes=min(len(self.ticker_list), n_jobs)) as pool:
        #     results = pool.starmap(self.load_factor_data_by_ticker,
        #                            [(ticker,) for ticker in self.ticker_list])
        with ThreadPoolExecutor(max_workers=min(len(self.ticker_list), n_jobs)) as executor:
            results = list(executor.map(
                lambda ticker: self.load_factor_data_by_ticker(ticker),
                self.ticker_list
            ))

        train_data = pd.concat([r[0] for r in results])
        test_data = pd.concat([r[1] for r in results])

        # # load factor data (single process)
        # data = dict() # restore data by month
        # for month in self.training_month:
        #     data[month] = self.load_data_from_sql(self.ticker_list, month, self.pool_name)
        # train_data = pd.concat([data[m] for m in self.training_month])
        # test_data = self.load_data_from_sql(self.ticker_list, self.test_month_new, self.pool_name)

        self.logger.info(f"{self.test_month}_price_group_{self.indus_type}: Finish loading factor")

        if len(train_data) == 0:
            self.is_empty = True
            return

        # transforming data, including std, clip, save params by ticker
        self.transform(self.ticker_list, train_data, test_data)
        print(f'load factor data time for price_group {self.indus_type}: {time.time() - start_time}')
        return self.train_data, self.test_data

    @staticmethod
    def load_fill_flag_by_ticker(ticker, stock_pool, start_month, end_month, tick_ahead, bs_flag):
        fill_flag_data = get_sop_fill_flag_ddb([ticker], stock_pool, start_month, end_month, tick_ahead, bs_flag)
        return fill_flag_data

    def load_fill_flag_data(self, tick_ahead, bs_flag):
        print(f'start loading fill_flag for price_group {self.indus_type}, bs_flag {bs_flag}...')
        start_time = time.time()
        # with multiprocessing.Pool(processes=min(len(self.ticker_list), 10)) as pool:
        #     results = pool.starmap(self.load_fill_flag_by_ticker,
        #                            [(ticker, self.pool_name, self.training_month[0],
        #                              self.training_month[-1], tick_ahead, bs_flag) for ticker in self.ticker_list])
        # fill_flag_data_train = pd.concat(results)
        #
        # with multiprocessing.Pool(processes=min(len(self.ticker_list), 10)) as pool:
        #     results = pool.starmap(self.load_fill_flag_by_ticker,
        #                            [(ticker, self.pool_name, self.test_month_new,
        #                              self.test_month_new, tick_ahead, bs_flag) for ticker in self.ticker_list])
        # fill_flag_data_test = pd.concat(results)

        n_jobs = self.opt['n_jobs_read_data']
        args_list_train = [(ticker, self.pool_name, self.training_month[0],
                            self.training_month[-1], tick_ahead, bs_flag) for ticker in self.ticker_list]
        with ThreadPoolExecutor(max_workers=min(len(self.ticker_list), n_jobs)) as executor:
            results = list(executor.map(
                lambda args: self.load_fill_flag_by_ticker(*args),
                args_list_train
            ))
        fill_flag_data_train = pd.concat(results)

        args_list_test = [(ticker, self.pool_name, self.test_month_new,
                           self.test_month_new, tick_ahead, bs_flag) for ticker in self.ticker_list]
        with ThreadPoolExecutor(max_workers=min(len(self.ticker_list), n_jobs)) as executor:
            results = list(executor.map(
                lambda args: self.load_fill_flag_by_ticker(*args),
                args_list_test
            ))
        fill_flag_data_test = pd.concat(results)

        print(f'load fill_flag time for price group {self.indus_type}, bs_flag {bs_flag}: {time.time() - start_time}')
        return fill_flag_data_train, fill_flag_data_test

    def load_ticker_list(self):
        # fetch ticker list from mysql table
        try:
            ticker_list = []
            # load ticker list
            cur_ticker = load_ticker_by_price_group(self.opt, self.pool_name, self.indus_type, self.test_month)
            ticker_list.extend(cur_ticker)

            # align training and testing ticker list
            all_ticker = cur_ticker.copy()
            check_ticker_month = self.get_check_ticker_month()
            ticker_list = align_factor_ticker(self.factor_table, all_ticker, self.pool_name, check_ticker_month, self.test_month, self.rebalancing_tables, self.training_month_num, self.io_backend)

            # ordered ticker list
            ticker_list = sorted(ticker_list)
            self.logger.info(f"{self.test_month}_price_group_{self.indus_type}: Total ticker number is {len(ticker_list)}")

            # check whether ticker list is null
            if len(ticker_list) == 0:
                raise FileExistsError(f"{self.test_month}_price_group_{self.indus_type}: No ticker list exists in SQL")

        except Exception as e:
            self.logger.info(f"{self.test_month}_price_group_{self.indus_type}: Error in fetching ticker list: {e}")
            self.logger.info(traceback.format_exc())
            ticker_list = []
            # exc_type, exc_values, exc_traceback = sys.exc_info()
            # traceback.print_tb(exc_traceback)

        return ticker_list

    def load_data_from_sql(self, ticker_list, month, stock_pool):
        try:
            data = [pd.DataFrame()]
            database_name = list(self.factor_table.keys())
            factor_table_name = self.factor_table

            i = 0
            for database in database_name:
                for table in factor_table_name[database]:
                    # load factors from sql
                    factor = load_factor_by_table_low_price(
                        database, table, ticker_list, stock_pool, month, self.test_month,
                        self.rebalancing_tables, None, self.training_month_num, self.io_backend)
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

            # merge factors and labels by ticker, date, time
            data = data[['ticker', 'date', "time"] + self.training_factor_name]

            # check missing tickers between return and factors
            missing_tickers = set(ticker_list) - set(data['ticker'].unique())
            # assert len(ticker_list) == len(data['ticker'].unique()), self.logger.info("SQL data missing ticker", missing_tickers)
            if len(missing_tickers) > 0:
                # raise ValueError(f"{self.test_month}_indus_{self.indus_type}: There are missing tickers in Return: {list2str(missing_tickers)}")
                print(f"{self.test_month}: There are missing tickers in Return: {list2str(missing_tickers)}")

            # check Whether data is null
            if len(data) == 0:
                raise FileExistsError(f"{self.test_month}: No factor or return data exists in SQL")
        except Exception as e:
            traceback.print_exc()
            data = pd.DataFrame()
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


    def transform(self, ticker_list, train_data, test_data=None):
        self.train_data = train_data.reset_index(drop=True)
        self.test_data = test_data.reset_index(drop=True)
        self.std_params = []
        self.clip_params = []

        for ticker in ticker_list:

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
                self.train_data.loc[_train_data.index, self.clip_factor_name] = train_x
                self.test_data.loc[_test_data.index, self.clip_factor_name] = test_x
                # save transform params
                clip_param = pd.DataFrame(columns=['factor_name', 'min', 'max', ])
                clip_param['factor_name'] = self.clip_factor_name
                clip_param['min'] = factor_min
                clip_param['max'] = factor_max
                clip_param.insert(0, 'ticker', ticker)
                self.clip_params.append(clip_param)

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


        # save preprocess params
        save_folder = self.opt['path']['preprocess_path'][self.test_month]
        # std
        if len(self.std_params) > 0:
            std_path = osp.join(save_folder, f"std_params_price_group_{self.indus_type}.csv")
            self.std_params = pd.concat(self.std_params)
            self.std_params.to_csv(std_path, index=False)
        # clip
        if len(self.clip_params) > 0:
            clip_path = osp.join(save_folder, f"clip_params_price_group_{self.indus_type}.csv")
            self.clip_params = pd.concat(self.clip_params)
            self.clip_params.to_csv(clip_path, index=False)

    def get_check_ticker_month(self):
        check_ticker_month = self.training_month + [self.test_month]
        return check_ticker_month



if __name__ == '__main__':
    from utils.option import parse_options
    from pathlib import Path

    root_path = str(Path(__file__).resolve().parents[1])
    opt, args = parse_options(root_path, ensure=True, yaml_path='option/low_price/low_price.yaml')
    dataset = GenDatasetLowPrice(opt, 202507, 1)
    factor_train_data, factor_test_data = dataset.load_factor_data()
    fill_flag_train, fill_flag_test = dataset.load_fill_flag_data("1", "b")
