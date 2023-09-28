import glob
import argparse
import pandas as pd
import os
import sqlalchemy.types

from utils.option import parse_options
from utils.mysql import create_pd_engine, create_index


def push_report(opt):
    res_path = opt['path']['results_root']
    report = []
    for month in os.listdir(res_path):
        csv_folder = os.path.join(res_path, month)
        res_csv = glob.glob(csv_folder.rstrip('/') + '/*csv')
        for r in res_csv:
            report.append(pd.read_csv(r))
    report = pd.concat(report).reset_index(drop=True)
    report= report.reset_index(drop=True)
    report_name = '{}_report.csv'.format(opt['name'])
    report.to_csv(os.path.join(res_path, report_name), index=False)
    print(f"backtesting report has been saved at {report_name}")

def cat_signals(opt):
    signal_path = opt['path']['signal_root']
    signal = []
    for month in os.listdir(signal_path):
        csv_folder = os.path.join(signal_path, month)
        res_csv = glob.glob(csv_folder.rstrip('/') + '/*csv')
        for r in res_csv:
            signal.append(pd.read_csv(r))

    signal = pd.concat(signal).reset_index(drop=True)
    signal = signal.reset_index(drop=True)
    signal = signal[['ticker', 'date', 'time', 'signal', 'proba', 'up_bound', 'down_bound']]
    signal.rename(columns={'signal': 'signal_{}'.format(opt['dataset']['ret_name'])}, inplace=True)
    signal_name = '{}_signal.csv'.format(opt['name'])
    signal.to_csv(os.path.join(signal_path, signal_name), index=False)
    print(f"signals have been saved at {signal_name}")

    return signal

def push_signals_sql(signal, table_name ):
    engine = create_pd_engine('strategy')
    table_name = table_name
    signal.to_sql(table_name, con=engine, index=False, if_exists='replace', chunksize=10000,
                  dtype={'ticker': sqlalchemy.types.VARCHAR(length=10),
                         'date': sqlalchemy.types.BIGINT,
                         'time': sqlalchemy.types.BIGINT,
                         })
    create_index('strategy', table_name, ['ticker', 'date', 'time'])
    print(f"write signals to sql tabel:{table_name} successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-config', type=str, default='', help='Path to option YAML file.')
    parser.add_argument('-is_backtest', type=bool, default=True, help='Whether the phase is backtesting')
    args = parser.parse_args()

    config_path = '../config/train_lgbm_15s_highprice.yaml'
    root_path = '../'

    push_report(parse_options(root_path, config_path))
