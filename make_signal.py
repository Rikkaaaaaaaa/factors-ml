import numpy as np
import pandas as pd
import utils
import sqlalchemy
import argparse
import multiprocessing as mp
import time
from tqdm import tqdm

def read_proba_LR(config, ticker, month):
    pro_15s = utils.cx_read_sql(
        'select * from prob_15s where ticker="{}"  and {}<date and date<{}'.format(ticker, month * 100, (month + 1) * 100))
    pro_60s = utils.cx_read_sql(
        'select * from prob_60s where ticker="{}" and {}<date and date<{}'.format(ticker,month * 100, (month + 1) * 100))

    return pro_15s, pro_60s

def read_signal_ML(config, month, ticker=None):
    if ticker:
        sig_15s = utils.cx_read_sql('select * from {} where ticker="{}" and {}<date and date<{}'.format(config.sig_15s, ticker, month*100, (month+1)*100))
        sig_60s = utils.cx_read_sql('select * from {} where ticker="{}" and {}<date and date<{}'.format(config.sig_60s, ticker, month * 100, (month + 1) * 100))
        sig_120s = utils.cx_read_sql('select * from {} where ticker="{}" and {}<date and date<{}'.format(config.sig_120s, ticker, month * 100,(month + 1) * 100))
        sig_300s = utils.cx_read_sql('select * from {} where ticker="{}" and {}<date and date<{}'.format(config.sig_300s, ticker, month * 100,(month + 1) * 100))
    else:
        sig_15s = utils.cx_read_sql(
            'select * from {} where  {}<date and date<{}'.format(config.sig_15s, month * 100,
                                                                                (month + 1) * 100))
        sig_60s = utils.cx_read_sql(
            'select * from {} where {}<date and date<{}'.format(config.sig_60s, month * 100,
                                                                                (month + 1) * 100))
        sig_120s = utils.cx_read_sql(
            'select * from {} where  {}<date and date<{}'.format(config.sig_120s, month * 100,
                                                                                (month + 1) * 100))
        sig_300s = utils.cx_read_sql(
            'select * from {} where {}<date and date<{}'.format(config.sig_300s, month * 100,
                                                                                (month + 1) * 100))
    return sig_15s, sig_60s, sig_120s, sig_300s


def save2sql(data_name, merge_signal):

    engine = utils.create_pd_engine('strategy')
    merge_signal.to_sql(data_name, con=engine, index=False, if_exists='append', chunksize=10000,
                        dtype={'ticker': sqlalchemy.types.VARCHAR(length=10),
                               'date': sqlalchemy.types.BIGINT,
                               'time': sqlalchemy.types.BIGINT,
                               })


def merge_signal_ensemble_zz800(args):
    # zz800 高价股
    config, month, table_name, signal_col_name = args[0], args[1], args[2], args[3]
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
    print(time.time() - s)

    # save
    lock.acquire()
    s = time.time()
    save2sql(table_name, merge_signal)
    print(time.time() - s)
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

    config = parser.parse_args()
    config.sig_15s = 'signal_zz800_' + config.price_name + '_15s_ml'
    config.sig_60s = 'signal_zz800_' + config.price_name + '_60s_ml'
    config.sig_120s = 'signal_zz800_' + config.price_name + '_120s_ml'
    config.sig_300s = 'signal_zz800_' + config.price_name + '_300s_ml'

    table_name = 'ensemble_zz800_' + config.price_name + '_ml_new'
    signal_col_name = 'ensemble_zz800_' + config.price_name +'_ml'
    func = merge_signal_ensemble_zz800
    args = [(config, month, table_name, signal_col_name) for month in [202307]]

    lock = mp.Lock()
    init_args = [lock, ]
    pool = mp.Pool(processes=config.n_jobs, initializer=init, initargs=(init_args,))
    pool.map(func, args)
    pool.close()
    pool.join()
    utils.create_index('strategy', table_name, ['ticker', 'date', 'time'])

    # merge_signal_ensemble_zz800((config, 202304, table_name, signal_col_name))
    # utils.create_index('strategy', table_name, ['ticker', 'date', 'time'])


