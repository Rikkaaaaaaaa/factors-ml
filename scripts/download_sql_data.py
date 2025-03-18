import utils
import multiprocessing as mp
import time
import pandas as pd
import os
from tqdm import tqdm

factor_table = { 'strategy': ['factor'],
                'factor_test': ['ofl_factor', 'fok_factor', 'slope_factor', 'genetic_programming_factor_2_div_open']
                }



def sql2csv(month=202202, indus_from='wind1', ):
    if indus_from == 'wind1':
        indus_num = range(11)  # 0 - 10 type
        res_path = 'local_data/wind1'
    if indus_from == 'sw1':
        indus_num = range(0, 30)  # 0 - 29 type
        res_path = 'local_data/sw1'
    res_path = os.path.join(res_path, str(month))
    if not os.path.exists(res_path):
        os.makedirs(res_path)

    # get ticker list
    month_tickers = utils.cx_read_sql(f'select distinct ticker from ofl_factor_{month} ', database='factor_test').ticker
    month_tickers = tuple(month_tickers)
    print(len(month_tickers))
    for db in factor_table.keys():
        for table in factor_table[db]:
            print(table, db)
            # save factors
            factor = utils.cx_read_sql(f'select * from {table}_{month} where ticker in {month_tickers}', database=db)
            factor_name = f'{table}_{month}.csv'
            file_path = res_path + '/' + factor_name
            if not os.path.exists(file_path):
                print('save to {}'.format(file_path))
                factor.to_csv(res_path + '/' +factor_name)

    if month in [202304, 202305, 202306]:
        table = f"factor_{month}_index_rebalancing"
        factor = utils.cx_read_sql(f'select * from factor_{month}_index_rebalancing where ticker in {month_tickers}')
        factor_name = f'{table}.csv'
        file_path = res_path + '/' + factor_name
        if not os.path.exists(file_path):
            print('save to {}'.format(file_path))
            factor.to_csv(res_path + '/' + factor_name)


    # save labels
    labels = utils.cx_read_sql(
        f'select *  from ret_{month} where ticker in {month_tickers}')
    label_name = f'ret_{month}.csv'
    labels.to_csv(res_path + '/' +label_name)

def sql2csv_mp():
    pool = mp.Pool(processes=8)
    args = [ 202308, 202309, 202310, 202311 ] # 202202, 202203, 202204, 202205, 202206, 202207, 202208, 202209, 202210,
    #args = [202306]
    results = [ pool.apply_async(sql2csv, (arg,)) for arg in args]
    [res.get() for res in results]

if __name__ == '__main__':
    data_path = 'data'
    if not os.path.exists(data_path):
        os.mkdir(data_path)
    sql2csv_mp()

