import glob
import argparse
import pandas as pd
import os
import os.path as osp
import sqlalchemy.types
import traceback

from utils.mysql import create_pd_engine, create_index
from utils import ensure_table_name, delete_by_month


def save_report_disk(opt):
    report = []
    res_path = opt['path']['results_path']
    root_path = opt['path']['experiments_root']
    # list all dirs and filter month folder like 202406
    all_items = os.listdir(root_path)
    month_folders = [item for item in all_items if osp.isdir(osp.join(root_path, item)) and item.isdigit() and len(item)==6]
    # concat all results.csv
    for month in month_folders:
        try:
            csv_folder = osp.join(root_path, month, "results")
            res_csv = glob.glob(csv_folder.rstrip('/') + '/*csv')
            if len(res_csv) == 0:
                raise FileNotFoundError(f"There are no result files in {csv_folder}")
            for r in res_csv:
                report.append(pd.read_csv(r))
        except Exception as e:
            print(traceback.format_exc())

    report = pd.concat(report).reset_index(drop=True)
    report= report.reset_index(drop=True)
    report_name = 'report_{}.csv'.format(opt['name'])
    report.to_csv(os.path.join(opt['path']['experiments_root'], report_name), index=False)
    print(f"Backtesting report has been saved at {report_name}")

def cat_signals(opt, upload_month=[], save_local=False):
    signal_path = opt['path']['signal_path']
    signal = []
    if len(upload_month) == 0:
        upload_month = list(signal_path.keys())
    for month in upload_month:
        csv_folder = signal_path[month]
        res_csv = glob.glob(csv_folder.rstrip('/') + '/*csv')
        for r in res_csv:
            signal.append(pd.read_csv(r))
    if len(signal) == 1:
        signal = signal[0]
    elif len(signal) > 1:
        signal = pd.concat(signal)
    else:
        raise ValueError("No signal exists, please check option path!")

    signal = signal.reset_index(drop=True)
    signal = signal[['ticker', 'date', 'time', 'signal', 'proba', 'up_bound', 'down_bound']]
    signal.rename(columns={'signal': 'signal_{}'.format(opt['dataset']['ret_name'])}, inplace=True)
    print(f"Concat signals in {upload_month}")

    # save all signals to csv
    if save_local:
        signal_name = '{}_signal.csv'.format(opt['name'])
        signal.to_csv(os.path.join(opt['path']['experiments_root'], signal_name), index=False)
        print(f"Signals have been saved at {signal_name}")

    return signal

def write_table_sql(signal, database, table_name, if_exists='replace'):
    print(f"Writing signals to '{database}.{table_name}' now...")
    engine = create_pd_engine(database)
    table_name = table_name
    signal.to_sql(table_name, con=engine, index=False, if_exists=if_exists, chunksize=10000,
                  dtype={'ticker': sqlalchemy.types.VARCHAR(length=10),
                         'date': sqlalchemy.types.BIGINT,
                         'time': sqlalchemy.types.BIGINT,
                         })
    create_index('strategy', table_name, ['ticker', 'date', 'time'])
    print(f"Write signals to sql tabel \'{table_name}\' successfully")


def push_signal_sql(opt, suffix='', upload_month=[], database='strategy', if_exists='append'):
    if 'hs300' in opt['dataset']['pool_name'] and 'zz500' in opt['dataset']['pool_name']:
        pool_name = 'zz800'
    else:
        pool_name = opt['dataset']['pool_name'][-1]
    if opt['dataset']['price_name'] == 'highprice':
        table_name = f"signal_{pool_name}_highprice_{opt['model']['type'].lower()}_{opt['dataset']['ret_name']}"
    else:
        table_name = f"signal_{pool_name}_lowprice_{opt['model']['type'].lower()}_{opt['dataset']['ret_name']}"
    if suffix != '':
        table_name += f"_{suffix}"

    ensure_table_name(database, table_name)
    # delete data by month first
    for month in upload_month:
        delete_by_month(database=database, table_name=table_name, month=month)
    signal = cat_signals(opt, upload_month=upload_month)
    write_table_sql(signal, database, table_name, if_exists=if_exists)

