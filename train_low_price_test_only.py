import multiprocessing
import multiprocessing as mp
import os.path as osp
import logging
import argparse

from dataset.sql_ops import check_price_group
from dataset import build_dataset
from models import build_model
from feature_selector import build_selector
from backtester import BackTesterLowPrice
from utils.logger import get_root_logger, get_env_info
from utils.option import parse_options, dict2str
from utils.publish import save_report_disk, push_signal_sql
from utils.misc import Timer, time_str, get_time_str, exists_results_low_price, ensure_path
from pathlib import Path
import os
import pandas as pd
import statsmodels.api as sm
from utils import mysql_strategy


class DatasetTrainTest:
    def __init__(self, x_train, y_train, merge_key_train, x_test, y_test, merge_key_test):
        self.x_train = x_train
        self.y_train = y_train
        self.merge_key_train = merge_key_train
        self.x_test = x_test
        self.y_test = y_test
        self.merge_key_test = merge_key_test
        self.factor_list = list(sm.add_constant(x_train, has_constant='skip').columns)


def merge_data(factor_data, fill_flag_data):
    # first round of pre-processing: factor filter, time_filter, merge, drop_duplicates
    # (dropna: move to pre-processing)
    # factor filter
    merge_key = ['date', 'time', 'ticker']
    factor_data = factor_data.drop_duplicates()
    fill_flag_data = fill_flag_data[fill_flag_data['time'] <= 145000000]
    fill_flag_data = fill_flag_data[['date', 'time', 'ticker', 'fill_flag']]

    # merge, drop_duplicates
    merged_data = factor_data.merge(fill_flag_data, how='left', on=merge_key)
    # merged_data = merged_data[~pd.isna(merged_data['fill_flag'])]     # keep na for further process
    # merged_data = merged_data.dropna()
    merged_data = merged_data.drop_duplicates()
    factor_list = [x for x in list(merged_data.columns) if x not in merge_key + ['fill_flag']]
    x_data = merged_data[factor_list]
    y_data = merged_data['fill_flag']
    merge_key_data = merged_data[merge_key]
    return x_data, y_data, merge_key_data


def drop_signal_table(signal_table, test_month):
    query = f'delete from {signal_table} where date>={test_month}01 and date<={test_month}31'
    mysql_strategy.delete_query('strategy', query)
    print(query)


if __name__ == '__main__':
    root_path = str(Path(__file__).resolve().parents[0])
    parser = argparse.ArgumentParser()
    parser.add_argument('-root_path', type=str, default=root_path, help='Root path of project.')
    parser.add_argument('-option', type=str, default='option/hs300/20251105/20251105_hs300_highprice_lgbm_15s.yaml', help='Path to option YAML file.')
    parser.add_argument('-is_realtime', action='store_true', help='Whether the phase is backtesting or realtime')
    parser.add_argument('-debug', action='store_true', help='Whether to use debug mode') # it'll contain ticker num <= 10
    args = parser.parse_args()
    opt = parse_options(args, ensure=False, yaml_path='option/low_price/low_price_other_pct_eval.yaml')

    for test_month in opt['dataset']['test_month']:
        # delete current data in signal table
        if (not opt["is_realtime"]) & (opt["save_signal"]["save_signal_to_sql"]):
            signal_table = opt["save_signal"]["sql_table_name"]
            print(signal_table)
            drop_signal_table(signal_table, test_month)

        # build model
        industry = check_price_group(opt, test_month)
        print(
            f"Loading price_group by [{opt['dataset']['indus_class']}] from table [static_data_price_{opt['dataset']['pool_name']}_history] + [{opt['dataset']['indus_table_suffix']}]]")
        print(f"Including group id: {industry}")
        for indus_type in industry:
            dataset = build_dataset(opt, test_month, indus_type)
            factor_test_data = dataset.load_factor_data_test_only()
            for bs_flag in ["b", "s"]:
                print(test_month, indus_type, bs_flag)
                fill_flag_test = dataset.load_fill_flag_data_test_only("1", bs_flag)
                x_test, y_test, merge_key_test = merge_data(factor_test_data, fill_flag_test)

                dataset_train_test = DatasetTrainTest(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), x_test, y_test, merge_key_test)
                backtester = BackTesterLowPrice(opt, test_month, indus_type)
                model = None
                backtester.backtest_test_only(dataset_train_test, model, bs_flag)









