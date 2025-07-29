import numpy as np
import pandas as pd
from utils.mysql import cx_read_sql
from utils import list2str
from utils.ddb import read_ddb_factor, read_ddb_return, read_ddb

def get_ticker_list(pool_name, price_name, test_month, indus_table_suffix=''):
    '''
    fetch ticker list from mysql table
    '''
    if isinstance(indus_table_suffix, str):
        if len(indus_table_suffix) > 0:
            indus_table_suffix = '_' + indus_table_suffix
        else:
            indus_table_suffix = ''
    else:
        raise ValueError(
            f"'indus_table_suffix' must be string 'old' or '', but now it is {indus_table_suffix}")

    print(f'Fetching ticker list from table [static_data_industry_{pool_name}_history{indus_table_suffix}]')
    if price_name == 'highprice':
        indus_table = cx_read_sql('select * from static_data_industry_{}_history{} where test_month={}'.format(pool_name, indus_table_suffix, test_month))
        price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price > {} and test_month={}'.format(
                                   pool_name, 10, test_month))
    if price_name == 'lowprice':
        # note that lowprice stocks have no indus_type, default is 0
        indus_table = cx_read_sql('select * from static_data_industry_{}_history{} where test_month={}'.format(pool_name, indus_table_suffix, test_month))
        price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price <= {} and test_month={}'.format(
                                   pool_name, 10, test_month))
    tickers = set(indus_table['ticker']) & set(price_table['ticker'])
    # ordered ticker list
    tickers = sorted(tickers)

    return tickers

def check_indus(opt, first_month):
    pools = opt['dataset']['pool_name']
    indus_class = opt['dataset']['indus_class']
    indus_table_suffix = opt['dataset']['indus_table_suffix']
    if isinstance(indus_table_suffix, str) :
        if  len(indus_table_suffix) > 0:
            indus_table_suffix = '_' + indus_table_suffix
        else:
            indus_table_suffix =  ''
    else:
        raise ValueError(f"Param in opt['dataset']['indus_table_suffix'] must be string 'old' or '', but now it is {indus_table_suffix}")
    indus_list = []
    if opt['dataset']['price_name'] == 'highprice':
        for pool in pools:
            indus_table = cx_read_sql('select distinct {} from static_data_industry_{}_history{} where test_month={}'.format(
                                        indus_class, pool, indus_table_suffix, first_month))

            indus_list.extend(list(indus_table[indus_class]))
    # default class num of low price is zero
    else: indus_list = [0]

    return set(indus_list)

def load_ticker_by_indus(opt, pool, indus_type, test_month):
    # fetch price and indus table from sql
    indus_class = opt['dataset']['indus_class']
    price_name = opt['dataset']['price_name']
    avg_price = opt['dataset']['avg_price']
    indus_table_suffix = opt['dataset']['indus_table_suffix']
    if isinstance(indus_table_suffix, str):
        if len(indus_table_suffix) > 0:
            indus_table_suffix = '_' + indus_table_suffix
        else:
            indus_table_suffix = ''
    else:
        raise ValueError(
            f"Param in opt['dataset']['indus_table_suffix'] must be string 'old' or '', but now it is {indus_table_suffix}")

    if price_name == 'highprice':
        indus_table = cx_read_sql('select * from static_data_industry_{}_history{} where {}="{}" and test_month={}'.format(pool,
                                   indus_table_suffix, indus_class, indus_type, test_month))
        price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price > {} and test_month={}'.format(
                                   pool, avg_price, test_month))
    if price_name == 'lowprice':
        # Note that lowprice stocks have no indus_type, default is 0
        indus_table = cx_read_sql('select * from static_data_industry_{}_history{} where test_month={}'.format(pool, indus_table_suffix, test_month))
        price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price <= {} and test_month={}'.format(pool, avg_price, test_month))

    tickers = set(indus_table['ticker']) & set(price_table['ticker'])
    if len(tickers) == 0:
        raise FileExistsError(f"{test_month}_indus_{indus_type}: The number of tickers(average price > 10) is 0")

    return tickers

def load_labels(opt, tickers, month):
    ret_name = opt['dataset']['ret_name']
    io_backend = opt['dataset']['io_backend']

    if io_backend == 'ddb':
        data_base = list(opt['dataset']['ret_table'].keys())[0]
        table_name =  opt['dataset']['ret_table'][data_base]
        labels = read_ddb_return(data_base, table_name, month, tickers, opt['dataset']['trading_hours'])

    # mix return by weights
    if opt['dataset'].get('mix_return'):
        data_base = list(opt['dataset']['ret_table'].keys())[0]
        table_name =  opt['dataset']['ret_table'][data_base]
        labels = read_ddb_return(data_base, table_name, month, tickers, opt['dataset']['trading_hours'])

        ret_cols = opt['dataset']['mix_return']['ret_cols']
        weights = opt['dataset']['mix_return']['weights']
        mixed_ret = labels[ret_cols].values
        np_weights = np.array(weights)
        mixed_ret = np.sum(np_weights * mixed_ret, axis=1)/len(ret_cols)
        labels[f'ret_{ret_name}'] = mixed_ret

    # filter all the other columns
    labels = labels[['ticker', 'date', "time", f'ret_{ret_name}']]

    return labels

def is_rebalanced(test_month, training_month_num):
    # whether training months spread 01/07 month
    training_month_num = training_month_num
    int_month = test_month % 100
    if int_month >= 7:
        if (int_month - training_month_num) < 7:
            return True
        else:
            return False
    else:
        if (int_month - training_month_num) < 1:
            return True

        else:
            return False
def need_rebalanced_factor(check_month, test_month):
    '''
    whether to use relanced factor
    '''
    status = False
    test_year = test_month // 100
    # test month in [7,12]
    if test_month % 100 >= 7:
        if check_month < test_year*100 + 7:
            status = True
    # test month in [1,6]
    else:
        if check_month < test_year*100 + 1:
            status = True

    return status


def check_rebalanced(training_month, test_month):
    is_rebalanced_flag = is_rebalanced(test_month, len(training_month))
    need_rebalanced_month = []
    for check_month in training_month:
        status = need_rebalanced_factor(check_month, test_month)
        if status and is_rebalanced_flag:
            need_rebalanced_month.append(check_month)

    return need_rebalanced_month


def align_factor_ticker(factor_table, all_ticker, check_ticker_month, test_month, rebalancing_tables, training_month_num=3, io_backend="ddb"):

    cur_ticker = all_ticker.copy()
    for database in factor_table.keys():
        for table in factor_table[database]:
            for month in check_ticker_month:
                ddb_month = str(month)[0:4] + '.' + str(month)[4:] + 'M'

                if is_rebalanced(test_month, training_month_num) and need_rebalanced_factor(month, test_month) and table in rebalancing_tables:
                    if io_backend == "sql":
                        factor_ticker = cx_read_sql(f'select distinct ticker from {table}_{month}_index_rebalancing', database=database)
                    if io_backend == "ddb":
                        factor_ticker = read_ddb(f'select distinct(securityCode) as ticker from loadTable("{database}", "{table}_index_rebalancing") where month(time)={ddb_month}')

                else:
                    if io_backend == "sql":
                        factor_ticker = cx_read_sql(f'select distinct ticker from {table}_{month}', database=database)
                    if io_backend == "ddb":
                        factor_ticker = read_ddb(f'select distinct(securityCode) as ticker from loadTable("{database}", "{table}") where month(time)={ddb_month}')
                # check missing tickers
                factor_ticker = factor_ticker['ticker']
                # cur_ticker = cur_ticker & set(factor_ticker)
                missing_tickers = set(all_ticker) - set(factor_ticker)

                if len(missing_tickers) > 0:
                    #raise ValueError(f"There are missing tickers in {database}.{table} in {month}:  {list2str(missing_tickers)}")
                    print(f"There are missing tickers in {database}.{table} in {month}:  {list2str(missing_tickers)}")

    return cur_ticker


def load_factor_by_table(database, table, tickers, loading_month, test_month, rebalancing_tables, trading_hours=None, training_month_num=3, io_backend='sql'):
    if len(tickers) == 1:
        ticker_condition = f'ticker="{tickers[0]}"'
    else:
        ticker_condition = f'ticker in {tickers}'

    if is_rebalanced(test_month, training_month_num) and need_rebalanced_factor(loading_month, test_month) and  table in rebalancing_tables :
        if io_backend == "sql":
            factor = cx_read_sql(f'select * from {table}_{loading_month}_index_rebalancing where {ticker_condition}',
                                 database=database)
        if io_backend == "ddb":
            tickers = list(tickers)
            factor = read_ddb_factor(database, f'{table}_index_rebalancing', loading_month, tickers, trading_hours)
    else:
        if io_backend == "sql":
            factor = cx_read_sql(f'select * from {table}_{loading_month} where {ticker_condition}', database=database)
        if io_backend == "ddb":
            tickers = list(tickers)
            factor = read_ddb_factor(database, table, loading_month, tickers, trading_hours)

    return factor