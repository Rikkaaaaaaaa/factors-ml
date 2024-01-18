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



def align_factor_ticker(factor_table, all_ticker, check_ticker_month, test_month, training_month_num=3):
    cur_ticker = all_ticker.copy()
    for database in factor_table.keys():
        for table in factor_table[database]:
            for month in check_ticker_month:
                if is_rebalanced(test_month, training_month_num) and need_rebalanced_factor(month, test_month) and table == 'factor':
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


def load_factor_by_table(database, table, tickers, loading_month, test_month, training_month_num=3):
    if is_rebalanced(test_month, training_month_num) and need_rebalanced_factor(loading_month, test_month) and table == 'factor':
        factor = cx_read_sql(f'select * from {table}_{loading_month}_index_rebalancing where ticker in {tickers}',
                             database=database)
    else:
        factor = cx_read_sql(f'select * from {table}_{loading_month} where ticker in {tickers}', database=database)

    return factor