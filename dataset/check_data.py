from utils import cx_read_sql


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




