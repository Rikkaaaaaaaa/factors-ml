import numpy as np
import pandas as pd
import sqlalchemy
import argparse
import multiprocessing as mp
import time
import sys
sys.path.append('scripts/')
from utils import cx_read_sql, create_index, create_pd_engine, delete_by_month, ensure_table_name

def read_proba_LR(config, ticker, month):
    pro_15s = cx_read_sql(
        'select * from prob_15s where ticker="{}"  and {}<date and date<{}'.format(ticker, month * 100, (month + 1) * 100))
    pro_60s = cx_read_sql(
        'select * from prob_60s where ticker="{}" and {}<date and date<{}'.format(ticker,month * 100, (month + 1) * 100))

    return pro_15s, pro_60s

def read_signal_ML(config, month, ticker=None):
    try:
        if ticker:
            sig_15s = cx_read_sql('select * from {} where ticker="{}" and {}<date and date<{}'.format(config.sig_15s, ticker, month*100, (month+1)*100))
            sig_60s = cx_read_sql('select * from {} where ticker="{}" and {}<date and date<{}'.format(config.sig_60s, ticker, month * 100, (month + 1) * 100))
            sig_120s = cx_read_sql('select * from {} where ticker="{}" and {}<date and date<{}'.format(config.sig_120s, ticker, month * 100,(month + 1) * 100))
            sig_300s = cx_read_sql('select * from {} where ticker="{}" and {}<date and date<{}'.format(config.sig_300s, ticker, month * 100,(month + 1) * 100))
        else:
            sig_15s = cx_read_sql(
                'select * from {} where  {}<date and date<{}'.format(config.sig_15s, month * 100,
                                                                                    (month + 1) * 100))
            sig_60s = cx_read_sql(
                'select * from {} where {}<date and date<{}'.format(config.sig_60s, month * 100,
                                                                                    (month + 1) * 100))
            sig_120s = cx_read_sql(
                'select * from {} where  {}<date and date<{}'.format(config.sig_120s, month * 100,
                                                                                    (month + 1) * 100))
            sig_300s = cx_read_sql(
                'select * from {} where {}<date and date<{}'.format(config.sig_300s, month * 100,
                                                                                    (month + 1) * 100))
        if len(sig_15s) == len(sig_60s) == len(sig_120s) == len(sig_300s):
            pass
        else:
            raise ValueError("Unequal number of signal!")
    except Exception as e:
        print('Read signal ML error: {}'.format(e))

    return sig_15s, sig_60s, sig_120s, sig_300s


def save_signal_sql(database, table_name, merge_signal):
    engine = create_pd_engine(database)
    merge_signal.to_sql(table_name, con=engine, index=False, if_exists='append', chunksize=10000,
                        dtype={'ticker': sqlalchemy.types.VARCHAR(length=10),
                               'date': sqlalchemy.types.BIGINT,
                               'time': sqlalchemy.types.BIGINT,
                               })

def merge_signal_ensemble(args):
    # zz800 高价股
    config, month, table_name, signal_col_name = args[0], args[1], args[2], args[3]
    print(f'Merging {month} signals to {table_name}...')
    s = time.time()
    sig_15s, sig_60s, sig_120s, sig_300s = read_signal_ML(config, month)
    sig_15s = sig_15s[['ticker', 'date', 'time', 'proba']]
    sig_60s = sig_60s[['ticker', 'date', 'time', 'signal_60s']]
    sig_120s = sig_120s[['ticker', 'date', 'time', 'signal_120s']]
    sig_300s = sig_300s[['ticker', 'date', 'time', 'signal_300s']]

    merge_keys = ['ticker', 'date', 'time']
    signal = sig_15s.merge(sig_60s, on=merge_keys).merge(sig_120s, on=merge_keys).merge(sig_300s, on=merge_keys)

    # core merge format
    signal[signal_col_name] = (signal['proba'] - 0.5) * 4 + signal['signal_60s']*2 + \
                               signal['signal_120s'] * 2 + signal['signal_300s'] * 2
    merge_signal = signal[['ticker', 'date', 'time', signal_col_name]]

    lock.acquire()
    s = time.time()
    # delete data by month first
    delete_by_month(database=config.database, table_name=table_name, month=month)
    # write to sql
    print(f'Writing data in {month} to {table_name}...')
    save_signal_sql(database=config.database, table_name=table_name, merge_signal=merge_signal,)
    print(f'Finishing writing data in {month}, cost {time.time() - s}s')
    lock.release()

def init(args):
    # transfer global variant to every processing
    # 所有线程使用同一个lock作为初始化
    global lock
    lock = args[0]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='merge bt signal')
    parser.add_argument('-n_jobs', type=int, default=8, help="parallel num")
    parser.add_argument('-price_name', type=str, default='highprice', help='highprice or lowprice')
    parser.add_argument('-pool_name', type=str, default='zz800', help='hs300, zz500 or zz1000')
    parser.add_argument('-signal_table_suffix', type=str, default='')
    parser.add_argument('-merge_table_suffix', type=str, default='ml')
    parser.add_argument('-database', type=str, default='strategy')
    test_month = [202304, 202305,202306,202307,202308, 202309, 202310, 202311]

    config = parser.parse_args()
    config.sig_15s = f'signal_{config.pool_name}_{config.price_name}_lgbm_15s'
    config.sig_60s = f'signal_{config.pool_name}_{config.price_name}_lgbm_60s'
    config.sig_120s = f'signal_{config.pool_name}_{config.price_name}_lgbm_120s'
    config.sig_300s = f'signal_{config.pool_name}_{config.price_name}_lgbm_300s'
    if config.signal_table_suffix != '':
        config.sig_15s += f"_{config.signal_table_suffix}"
        config.sig_60s += f"_{config.signal_table_suffix}"
        config.sig_120s += f"_{config.signal_table_suffix}"
        config.sig_300s += f"_{config.signal_table_suffix}"

    table_name = f"ensemble_{config.pool_name}_{config.price_name}_{config.merge_table_suffix}"
    ensure_table_name(database=config.database, table_name=table_name)
    signal_col_name = f"ensemble_{config.pool_name}_{config.price_name}_{config.merge_table_suffix}"
    func = merge_signal_ensemble
    args = [(config, month, table_name, signal_col_name) for month in test_month]

    lock = mp.Lock()
    init_args = [lock, ]
    pool = mp.Pool(processes=config.n_jobs, initializer=init, initargs=(init_args,))
    pool.map(func, args)
    pool.close()
    pool.join()
    create_index('strategy', table_name, ['ticker', 'date', 'time'])



