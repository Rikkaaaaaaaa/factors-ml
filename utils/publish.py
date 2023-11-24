import glob
import argparse
import pandas as pd
import os
import sqlalchemy.types

from utils.option import parse_options
from utils.mysql import create_pd_engine, create_index


def save_report_disk(opt):
    res_path = opt['path']['results_path']
    report = []
    for month in res_path.keys():
        csv_folder = res_path[month]
        res_csv = glob.glob(csv_folder.rstrip('/') + '/*csv')
        for r in res_csv:
            report.append(pd.read_csv(r))
    report = pd.concat(report).reset_index(drop=True)
    report= report.reset_index(drop=True)
    report_name = 'report_{}.csv'.format(opt['name'])
    report.to_csv(os.path.join(opt['path']['experiments_root'], report_name), index=False)
    print(f"Backtesting report has been saved at {report_name}")

def cat_signals(opt, save_local=False):
    signal_path = opt['path']['signal_path']
    signal = []
    for month in signal_path.keys():
        csv_folder = signal_path[month]
        res_csv = glob.glob(csv_folder.rstrip('/') + '/*csv')
        for r in res_csv:
            signal.append(pd.read_csv(r))

    signal = pd.concat(signal).reset_index(drop=True)
    signal = signal.reset_index(drop=True)
    signal = signal[['ticker', 'date', 'time', 'signal', 'proba', 'up_bound', 'down_bound']]
    signal.rename(columns={'signal': 'signal_{}'.format(opt['dataset']['ret_name'])}, inplace=True)
    # save all signals to csv
    if save_local:
        signal_name = '{}_signal.csv'.format(opt['name'])
        signal.to_csv(os.path.join(opt['path']['experiments_root'], signal_name), index=False)
        print(f"Signals have been saved at {signal_name}")

    return signal

def write_table_sql(opt, table_name, if_exists='replace'):
    print(f"Writing signals to sql tabel '{table_name}' now...")
    signal = cat_signals(opt)
    engine = create_pd_engine('strategy')
    table_name = table_name
    signal.to_sql(table_name, con=engine, index=False, if_exists=if_exists, chunksize=10000,
                  dtype={'ticker': sqlalchemy.types.VARCHAR(length=10),
                         'date': sqlalchemy.types.BIGINT,
                         'time': sqlalchemy.types.BIGINT,
                         })
    create_index('strategy', table_name, ['ticker', 'date', 'time'])
    print(f"Write signals to sql tabel \'{table_name}\' successfully")


def push_signal_sql(opt, suffix=''):
    if 'hs300' in opt['dataset']['pool_name'] and 'zz500' in opt['dataset']['pool_name']:
        pool_name = 'zz800'
    else:
        pool_name = opt['dataset']['pool_name'][-1]
    if opt['dataset']['price_name'] == 'highprice':
        table_name = f"signal_{pool_name}_highprice_lgbm_{opt['dataset']['ret_name']}"
    else:
        table_name = f"signal_{pool_name}_lowprice_lgbm_{opt['dataset']['ret_name']}"
    if len(suffix) > 0:
        table_name + f'_{suffix}'
    write_table_sql(opt, table_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-option', type=str, default='', help='Path to option YAML file.')
    parser.add_argument('-is_backtest', type=bool, default=True, help='Whether the phase is backtesting')
    args = parser.parse_args()

    config_path = '../option/backtest_zz800_highprice_lgbm_15s.yaml'
    root_path = '../'

    save_report_disk(parse_options(root_path, config_path))
