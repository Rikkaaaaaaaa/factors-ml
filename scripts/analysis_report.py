import os
import pandas as pd
import numpy as np
import glob
import argparse
import os.path as osp
import sys
sys.path.append('../')
sys.path.append('./')

from dataset.sql_ops import get_ticker_list


def summarize_report(config, root='/root/PycharmProjects/factors-ml', svg_path='./summary'):
    '''
    summary all window_size(15s, 60s, 120s, 300s) report into a csv file
    '''
    prefix = config.prefix
    report_pool_name = config.report_pool_name
    ticker_pool_name = config.ticker_pool_name
    price_name = config.price_name
    model_name = config.model_name
    ret_windows = config.ret_windows
    experiment_path = config.experiment_path
    cols = [ 'month', 'up_bound', 'down_bound', 'up_win_rate', 'down_win_rate', 'up_mean_ret', 'down_mean_ret',
           'up_signal_rate', 'down_signal_rate', 'weighted_ret', 'total_sample', 'zero_rate']
    summary = []
    for ret_window in ret_windows:
        report_folder = f'{prefix}_{report_pool_name}_{price_name}_{model_name}_{ret_window}'
        report_name = f'report_{prefix}_{report_pool_name}_{price_name}_{model_name}_{ret_window}'

        report_path = osp.join(root, experiment_path, report_folder, report_name + '.csv')
        report = pd.read_csv(report_path)
        report['weighted_ret'] = report['up_mean_ret'] * report['up_signal_rate'] - report['down_mean_ret'] * report['down_signal_rate']
        test_month_list = sorted(report['month'].unique())
        for month in test_month_list:
            tickers = get_ticker_list(ticker_pool_name, price_name, month)
            month_report = report.query('ticker in @tickers and month==@month')
            _report = month_report[cols].groupby('month').mean()
            _report.insert(0, 'ret_window', ret_window)
            summary.append(_report)

    summary = pd.concat(summary)
    if not osp.exists(svg_path):
        os.makedirs(svg_path)
    svg_path = osp.join(svg_path, f"summary_{prefix}_{ticker_pool_name}_{price_name}_{model_name}_{test_month_list[0]}_{test_month_list[-1]}.csv")
    summary.to_csv(svg_path)
    print(f"Summary has been saved to {svg_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ddb_factor')
    parser.add_argument('-experiment_path', type=str, default='experiments', help='experiment folder name')
    parser.add_argument('-n_jobs', type=int, default=8, help="parallel num")
    parser.add_argument('-prefix', type=str, default='ddb_factor', )
    parser.add_argument('-price_name', type=str, default='highprice', help='highprice or lowprice')
    parser.add_argument('-report_pool_name', type=str, default='hs300', help='hs300, zz800 or zz1000')
    parser.add_argument('-ticker_pool_name', type=str, default='hs300', help='hs300, zz500 or zz1000')
    parser.add_argument('-model_name', type=str, default='lgbm', help='lgbm or lr')
    parser.add_argument('-ret_windows', nargs='+', type=str, default=['15s', '60s', '120s', '300s'], help='ret_windows in summary')
    config = parser.parse_args()

    summarize_report(config,)



