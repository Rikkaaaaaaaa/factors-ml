import numpy as np
import os.path as osp
import pandas as pd
from tqdm import tqdm
import traceback

from utils.logger import get_root_logger
from utils import mysql_strategy
import sqlalchemy


class BackTesterLowPrice():
    """
    Backtester: include evaluation of models, metric of backtest and signal generation.

    Args:
        opt(dict): option for dataset, includes following keys:
            ...
        test_month(int): month needs to be eval
        indus_type(int): one of the indus_class

        """
    def __init__(self, opt, test_month, indus_type):
        self.opt = opt
        self.test_month = test_month
        self.indus_type = indus_type
        self.is_realtime = self.opt['is_realtime']
        # logging file
        logger_name = f"month{test_month}_price_group_{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)
        self.logger.info(f'{self.test_month}_price_group_{self.indus_type}: Backtester init successfully')

    @staticmethod
    def add_const_if_missing(df, factor_list):
        if 'const' not in df.columns:
            df['const'] = 1
        return df[factor_list]

    @staticmethod
    def pre_processing_ddb(merge_key_train, x_train, y_train):
        # train data drop na
        x_train = x_train.fillna(0)
        merged_train_data = pd.concat([merge_key_train, x_train, y_train], axis=1)
        merged_train_data = merged_train_data.dropna()
        merged_train_data = merged_train_data.reset_index(drop=True)

        merge_key = list(merge_key_train.columns)
        factor_list = [x for x in list(merged_train_data.columns) if x not in merge_key + ['fill_flag']]

        x_train = merged_train_data[factor_list]
        y_train = merged_train_data['fill_flag'].astype('int')
        new_merge_key_train = merged_train_data[merge_key]
        return x_train, y_train, new_merge_key_train

    def get_benchmark_dict(self, model, factor_data, benchmark):
        # calc y_pred for x_train
        x_train, y_train, merge_key_train = self.pre_processing_ddb(
            factor_data.merge_key_train, factor_data.x_train, factor_data.y_train)
        y_pred = model.predict(self.add_const_if_missing(x_train, factor_data.factor_list))

        # generate benchmark dict
        benchmark_dict = {}
        merge_key_train['y_train'] = y_train
        merge_key_train['y_pred'] = y_pred
        merge_key_train['count'] = 1
        ticker_list = list(merge_key_train['ticker'].unique())
        for ticker in ticker_list:
            y_pred_df = merge_key_train[merge_key_train['ticker'] == ticker]
            y_pred_df = y_pred_df.sort_values('y_pred', ascending=False)
            y_pred_df['cumu_fill_rate'] = y_pred_df['y_train'].cumsum() / y_pred_df['count'].cumsum()

            pred_in_benchmark = y_pred_df[y_pred_df['cumu_fill_rate'] >= benchmark]['y_pred']
            if len(pred_in_benchmark) > 0:
                threshold = pred_in_benchmark.tolist()[-1]
            else:
                threshold = 1.0
            benchmark_dict[ticker] = [threshold, y_pred_df['y_pred'].quantile(0.9), y_pred_df['y_pred'].quantile(0.8)]

        benchmark_df = pd.DataFrame.from_dict(benchmark_dict, orient='index',
                                              columns=['dynamic_threshold', 'quantile_90', 'quantile_80'])
        benchmark_df = benchmark_df.reset_index().rename(columns={'index': 'ticker'})
        self.benchmark_df = benchmark_df
        return benchmark_dict

    @staticmethod
    def calc_group_accuracy(y_pred, y_test, group_num):
        y_pred_df = pd.DataFrame()
        y_pred_df['y_pred'] = y_pred
        y_pred_df['y_test'] = y_test

        y_pred_group_accuracy = pd.DataFrame(index=range(group_num), columns=['accuracy'])
        y_pred_df['group'] = pd.qcut(y_pred_df['y_pred'].rank(method='first'), group_num, labels=False)
        y_pred_group_accuracy['accuracy'] = y_pred_df.groupby('group')['y_test'].mean()
        return y_pred_group_accuracy

    def calc_volume_signal(self, model, factor_data, benchmark_dict, bs_flag):
        """
        'top_10_fill_rate', 'bottom_10_fill_rate', 'top10_minus_bottom10_fill_rate',
        'dynamic_benchmark_fill_rate', 'dynamic_benchmark_pct', 'fixed_benchmark_fill_rate', 'fixed_benchmark_pct',
        'actual_fill_rate'
        """
        merge_key_test, x_test, y_test = factor_data.merge_key_test, factor_data.x_test, factor_data.y_test
        # y_pred = model.predict(self.add_const_if_missing(x_test.fillna(0), factor_data.factor_list))
        y_pred = predict_rt(x_test, self.opt, self.test_month, self.indus_type, bs_flag)

        merge_key_test['y_pred'] = y_pred
        merge_key_test['y_test'] = y_test
        ticker_list = list(merge_key_test['ticker'].unique())
        result_df_all = pd.DataFrame()
        final_prediction_label = pd.DataFrame()

        for ticker in ticker_list:
            temp_pred_data = merge_key_test[merge_key_test['ticker'] == ticker]
            temp_y_pred = temp_pred_data['y_pred']
            temp_y_test = temp_pred_data['y_test']

            # 'top_10_fill_rate', 'bottom_10_fill_rate', 'top10_minus_bottom10_fill_rate'
            y_pred_group_accuracy = self.calc_group_accuracy(temp_y_pred, temp_y_test, 10)
            top_10_fill_rate = y_pred_group_accuracy['accuracy'].tolist()[-1]
            bottom_10_fill_rate = y_pred_group_accuracy['accuracy'].tolist()[0]
            top10_minus_bottom10_fill_rate = top_10_fill_rate - bottom_10_fill_rate

            # 'dynamic_benchmark_fill_rate', 'dynamic_benchmark_pct'
            dynamic_benchmark_label = temp_y_pred > benchmark_dict[ticker][0]
            dynamic_benchmark_fill_rate = np.nanmean(temp_y_test[dynamic_benchmark_label].values)
            dynamic_benchmark_pct = sum(dynamic_benchmark_label) / len(dynamic_benchmark_label)

            # volume signal
            if bs_flag == 'b':
                vol_signal = np.where(temp_y_pred > benchmark_dict[ticker][2], 4.5,
                                      np.where(temp_y_pred > benchmark_dict[ticker][0], 0.5, 0))
            else:
                vol_signal = np.where(temp_y_pred > benchmark_dict[ticker][2], -4.5,
                                      np.where(temp_y_pred > benchmark_dict[ticker][0], -0.5, 0))
            temp_pred_data = temp_pred_data.copy()
            temp_pred_data.loc[:, 'vol_signal'] = list(vol_signal)
            temp_pred_data.loc[:, 'bs_flag'] = bs_flag
            final_prediction_label = pd.concat([final_prediction_label, temp_pred_data[
                ['date', 'time', 'ticker', 'bs_flag', 'y_pred', 'y_test', 'vol_signal']]])

            # 'actual_fill_rate'
            actual_fill_rate = np.nanmean(temp_y_test.values)

            # result df
            result_summary = [ticker, bs_flag, top_10_fill_rate, bottom_10_fill_rate, top10_minus_bottom10_fill_rate,
                              dynamic_benchmark_fill_rate, dynamic_benchmark_pct, actual_fill_rate,
                              self.indus_type, self.test_month]
            result_df = pd.DataFrame(result_summary).T
            result_df.columns = ['ticker', 'bs_flag', 'top_10_fill_rate', 'bottom_10_fill_rate',
                                 'top10_minus_bottom10_fill_rate',
                                 'dynamic_benchmark_fill_rate', 'dynamic_benchmark_pct', 'actual_fill_rate',
                                 'price_group', 'test_month']
            result_df_all = pd.concat([result_df_all, result_df])

        self.result_sumamry = result_df_all
        self.final_prediction = final_prediction_label

    def backtest(self, factor_data, model, bs_flag):
        '''
        backtest data and save results. bound values and signals
        '''
        benchmark_dict = self.get_benchmark_dict(model, factor_data, benchmark=0.7)
        self.calc_volume_signal(model, factor_data, benchmark_dict, bs_flag)

        self.save_benchmark(bs_flag)
        self.save_result_summary(bs_flag)
        if (not self.is_realtime) & (self.opt["save_signal"]["save_signal_to_sql"]):
            self.save_signal_to_sql()

        self.logger.info(f"{self.test_month}_price_group_{self.indus_type}_{bs_flag}: Backtest finish")

    def save_result_summary(self, bs_flag):
        '''
        save summary to backtesting results for all tickers
        '''
        results_folder =  self.opt['path']['results_path'][self.test_month]
        results_name = 'result_summary_{}_price_group_{}_{}.csv'.format(self.test_month, self.indus_type, bs_flag)
        results_path = osp.join(results_folder, results_name)
        self.result_sumamry.to_csv(results_path, index=False)

    def save_benchmark(self, bs_flag):
        '''
        save bound values for all toickers
        '''
        inference_folder = self.opt['path']['inference_path'][self.test_month]
        bound_name = 'benchmark_price_group_{}_{}.csv'.format(self.indus_type, bs_flag)
        bound_path = osp.join(inference_folder, bound_name)
        self.benchmark_df.to_csv(bound_path, index=False)

    def save_signal_to_sql(self):
        database = self.opt["save_signal"]["sql_database"]
        sql_table_name = self.opt["save_signal"]["sql_table_name"]
        pd_engine = mysql_strategy.create_pd_engine(database)
        result_to_sql(database, self.final_prediction, pd_engine, sql_table_name)


def result_to_sql(database, order_prediction, pd_engine, result_table_name):
    order_prediction.to_sql(result_table_name, con=pd_engine, index=False, if_exists='append', chunksize=10000,
                            dtype={'ticker': sqlalchemy.types.VARCHAR(length=10),
                                   'date': sqlalchemy.types.BIGINT, 'time': sqlalchemy.types.BIGINT,
                                   'bs_flag': sqlalchemy.types.VARCHAR(length=1),
                                   'y_pred': sqlalchemy.types.DOUBLE,
                                   'y_test': sqlalchemy.types.DOUBLE,
                                   'vol_signal': sqlalchemy.types.DOUBLE
                                   })
    # create index
    mysql_strategy.create_index(database, result_table_name, ['ticker', 'date', 'time', 'bs_flag'])


def predict_proba(theta, X):
    z = np.sum(np.array(theta.T * X), axis=1)
    # sigmoid
    s = 1 / (1 + np.exp(-z))
    return s


def predict_rt(x_test, opt, test_month, indus_type, bs_flag):
    x_test['const'] = 1

    # load factor name
    factor_name_folder = osp.join(opt['path']['experiments_root'], str(test_month))
    factor_name_df = pd.read_csv(osp.join(factor_name_folder, 'factor_name_low_price.csv'))
    factor_list = list(factor_name_df['factor_name'])

    factor_array = x_test[factor_list].values
    factor_array = np.nan_to_num(factor_array, nan=0)

    # load params
    ckpt_folder = opt['path']['model_path'][test_month]
    ckpt_name = 'logit_price_group_{}_{}.csv'.format(indus_type, bs_flag)
    ckpt_path = osp.join(ckpt_folder, ckpt_name)
    params_df = pd.read_csv(ckpt_path, index_col=0)

    params = params_df.values[0]
    y_pred = predict_proba(params, factor_array)
    return y_pred

