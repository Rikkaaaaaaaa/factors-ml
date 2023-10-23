import utils
import multiprocessing as mp
import time
import pandas as pd
import os
from tqdm import tqdm


def is_null_indus(indus_type, indus_from):
    data = utils.cx_read_sql(
        'select * from static_data_hs300_old where {}="{}" and avg_price > {}'. \
            format(indus_from, indus_type, 10))
    tickers = tuple(data['ticker'])
    # delete industry_num <=1
    if len(tickers) <= 1:
        return 1
    else:
        return 0

def sql2csv(month=202202, indus_from='wind1', label='15s'):
    if indus_from == 'wind1':
        indus_num = range(11)  # 0 - 10 type
        res_path = 'data/wind1'
    if indus_from == 'sw1':
        indus_num = range(0, 30)  # 0 - 29 type
        res_path = 'data/sw1'

    if not os.path.exists(res_path):
        os.makedirs(res_path)

    for indus_type in indus_num:
        if is_null_indus(indus_type, indus_from):
            continue

        # data = utils.cx_read_sql(
        #     'select * from static_data_hs300 where {}="{}" and avg_price > {}'.format(indus_from, indus_type, 10))
        # tickers = tuple(data['ticker'])
        data = pd.read_csv('static_data_hs300.csv')
        tickers = tuple(data.query('avg_price>10 &  wind1==@indus_type')['ticker'])

        # save factors
        factor = utils.cx_read_sql(
            'select * from factor_{} where ticker in {} '.format(str(month), tickers))
        factor_name = 'factor_{}_indus_{}.csv'.format(str(month), str(indus_type))
        file_path = res_path + '/' +factor_name
        if not os.path.exists(file_path):
            print('save to {}'.format(file_path))
            factor.to_csv(res_path + '/' +factor_name)

        # # save labels
        # labels = utils.cx_read_sql(
        #     'select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format(label, str(month), tickers))
        # label_name = 'ret_{}_indus_{}_label{}.csv'.format(str(month),str(indus_type), label)
        # labels.to_csv(res_path + '/' +label_name)

def sql2csv_mp():
    pool = mp.Pool(processes=8)
    args = [ 202210, 202211, 202212, 202301, 202302, 202303, 202304, 202305, 202306 ] # 202202, 202203, 202204, 202205, 202206, 202207, 202208, 202209, 202210,
    #args = [202306]
    results = [ pool.apply_async(sql2csv, (arg,)) for arg in args]
    [res.get() for res in results]

if __name__ == '__main__':
    data_path = 'data'
    if not os.path.exists(data_path):
        os.mkdir(data_path)
    sql2csv_mp()

