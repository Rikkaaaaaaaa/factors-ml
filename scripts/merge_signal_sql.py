import numpy as np
import pandas as pd
import sqlalchemy
import argparse
import multiprocessing as mp
import time
import sys
sys.path.append('./')
from utils import cx_read_sql, create_index, create_pd_engine

def read_proba_LR(config, ticker, month):
    pro_15s = cx_read_sql(
        'select * from prob_15s where ticker="{}"  and {}<date and date<{}'.format(ticker, month * 100, (month + 1) * 100))
    pro_60s = cx_read_sql(
        'select * from prob_60s where ticker="{}" and {}<date and date<{}'.format(ticker,month * 100, (month + 1) * 100))

    return pro_15s, pro_60s

def read_signal_ML(config, month, ticker=None):
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
    return sig_15s, sig_60s, sig_120s, sig_300s


def save2sql(data_name, merge_signal):

    engine = create_pd_engine('strategy')
    merge_signal.to_sql(data_name, con=engine, index=False, if_exists='append', chunksize=10000,
                        dtype={'ticker': sqlalchemy.types.VARCHAR(length=10),
                               'date': sqlalchemy.types.BIGINT,
                               'time': sqlalchemy.types.BIGINT,
                               })


def merge_signal_ensemble(args):
    # zz800 高价股
    config, month, table_name, signal_col_name = args[0], args[1], args[2], args[3]
    print(f'Merging {month} table {table_name}...')
    s = time.time()
    sig_15s, sig_60s, sig_120s, sig_300s = read_signal_ML(config, month)
    sig_15s = sig_15s[['ticker', 'date', 'time', 'proba']]
    sig_60s = sig_60s[['ticker', 'date', 'time', 'signal_60s']]
    sig_120s = sig_120s[['ticker', 'date', 'time', 'signal_120s']]
    sig_300s = sig_300s[['ticker', 'date', 'time', 'signal_300s']]

    merge_keys = ['ticker', 'date', 'time']
    signal = sig_15s.merge(sig_60s, on=merge_keys).merge(sig_120s, on=merge_keys).merge(sig_300s, on=merge_keys)
    signal[signal_col_name] = (signal['proba'] - 0.5) * 4 + signal['signal_60s']*2 + \
                               signal['signal_120s'] * 2 + signal['signal_300s'] * 2
    merge_signal = signal[['ticker', 'date', 'time', signal_col_name]]

    # write to sql
    lock.acquire()
    s = time.time()
    print(f'Writing data in {month} to SQL...')
    save2sql(table_name, merge_signal)
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
    test_month = [202304,202305,202306,202307]

    config = parser.parse_args()
    config.sig_15s = f'signal_{config.pool_name}_{config.price_name}_lgbm_15s'
    config.sig_60s = f'signal_{config.pool_name}_{config.price_name}_lgbm_60s'
    config.sig_120s = f'signal_{config.pool_name}_{config.price_name}_lgbm_120s'
    config.sig_300s = f'signal_{config.pool_name}_{config.price_name}_lgbm_300s'

    table_name = f'ensemble_{config.pool_name}_{config.price_name}_ml'
    signal_col_name = f'ensemble_{config.pool_name}_{config.price_name}_ml'
    func = merge_signal_ensemble
    args = [(config, month, table_name, signal_col_name) for month in test_month]

    lock = mp.Lock()
    init_args = [lock, ]
    pool = mp.Pool(processes=config.n_jobs, initializer=init, initargs=(init_args,))
    pool.map(func, args)
    pool.close()
    pool.join()
    create_index('strategy', table_name, ['ticker', 'date', 'time'])



