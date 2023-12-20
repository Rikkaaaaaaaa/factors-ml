import pandas as pd
from utils.mysql import cx_read_sql
from utils import list2str



def check_indus(opt, first_month):
    pools = opt['dataset']['pool_name']
    indus_class = opt['dataset']['indus_class']
    indus_list = []
    if opt['dataset']['price_name'] == 'highprice':
        for pool in pools:
            indus_table = cx_read_sql('select distinct {} from static_data_industry_{}_history where test_month={}'.format(
                                        indus_class, pool, first_month))

            indus_list.extend(list(indus_table[indus_class]))
    # default class num of low price is zero
    else: indus_list = [0]

    return set(indus_list)


def get_ticker_list(pool_name, price_name, test_month):
    '''
    fetch ticker list from mysql table
    '''

    if price_name == 'highprice':
        indus_table = cx_read_sql('select * from static_data_industry_{}_history where test_month={}'.format(pool_name, test_month))
        price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price > {} and test_month={}'.format(
                                   pool_name, 10, test_month))
    if price_name == 'lowprice':
        # note that lowprice stocks have no indus_type, default is 0
        indus_table = cx_read_sql('select * from static_data_industry_{}_history where test_month={}'.format(pool_name, test_month))
        price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price <= {} and test_month={}'.format(
                                   pool_name, 10, test_month))
    tickers = set(indus_table['ticker']) & set(price_table['ticker'])
    # ordered ticker list
    tickers = sorted(tickers)

    return tickers

def load_ticker_by_indus(pool, price_name, indus_class, indus_type, test_month, avg_price=10):
    # fetch price he indus table from sql
    if price_name == 'highprice':
        indus_table = cx_read_sql('select * from static_data_industry_{}_history where {}="{}" and test_month={}'.format(pool,
                                   indus_class, indus_type, test_month))
        price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price > {} and test_month={}'.format(
                                   pool, avg_price, test_month))
    if price_name == 'lowprice':
        # Note that lowprice stocks have no indus_type, default is 0
        indus_table = cx_read_sql('select * from static_data_industry_{}_history where test_month={}'.format(pool, test_month))
        price_table = cx_read_sql('select * from static_data_price_{}_history where avg_price <= {} and test_month={}'.format(pool, avg_price, test_month))

    tickers = set(indus_table['ticker']) & set(price_table['ticker'])

    return tickers


def is_rebalanced(test_month):
    if test_month % 100 in [1, 2, 3, 7, 8, 9]:
        return True
    else:
        return False


def align_factor_ticker(factor_table, all_ticker, check_ticker_month, test_month):
    cur_ticker = all_ticker.copy()
    for database in factor_table.keys():
        for table in factor_table[database]:
            for month in check_ticker_month:
                if is_rebalanced(test_month) and month % 100 in [4, 5, 6, 10, 11, 12]:
                    factor_ticker = cx_read_sql(f'select distinct ticker from {table}_{month}_index_rebalancing',
                                                database=database)
                else:
                    factor_ticker = cx_read_sql(f'select distinct ticker from {table}_{month}', database=database)
                cur_ticker = cur_ticker & set(factor_ticker['ticker'])
                # check missing tickers
                missing_tickers = set(all_ticker) - set(factor_ticker['ticker'])

                if len(missing_tickers) > 0:
                    raise ValueError(f"There are missing tickers in {database}.{table} in {month}:  {list2str(missing_tickers)}")

    return cur_ticker


def load_factor_by_table(database, table, tickers, loading_month, test_month):
    if is_rebalanced(test_month) and loading_month % 100 in [4, 5, 6, 10, 11, 12] and table!='genetic_programming_factor_1':
        factor = cx_read_sql(f'select * from {table}_{loading_month}_index_rebalancing where ticker in {tickers}',
                             database=database)
    else:
        factor = cx_read_sql(f'select * from {table}_{loading_month} where ticker in {tickers}', database=database)

    return factor