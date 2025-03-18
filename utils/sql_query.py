from utils.mysql import cx_read_sql


def get_ticker_list(pool_name, price_name, test_month, price_threshold=10):
    '''
    fetch ticker list from mysql table
    '''
    if price_name == 'highprice':
        indus_table = cx_read_sql(
            'select * from static_data_industry_{}_history where test_month={}'.format(pool_name, test_month))
        price_table = cx_read_sql(
            'select * from static_data_price_{}_history where avg_price > {} and test_month={}'.format(
                pool_name, price_threshold, test_month))
    if price_name == 'lowprice':
        indus_table = cx_read_sql(
            'select * from static_data_industry_{}_history where test_month={}'.format(pool_name, test_month))
        price_table = cx_read_sql(
            'select * from static_data_price_{}_history where avg_price <= {} and test_month={}'.format(
                pool_name, price_threshold, test_month))
    tickers = set(indus_table['ticker']) & set(price_table['ticker'])
    # ordered ticker list
    tickers = sorted(tickers)

    indus_table.query('indus_class==@indus_type')

    return tickers

def get_ticker_list(pool_name, price_name, test_month, indus_class, indus_type, price_threshold=10):
    '''
    fetch ticker list from mysql table
    '''

    if price_name == 'highprice':
        indus_table = cx_read_sql(
            f'select * from static_data_industry_{pool_name}_history where {indus_class}="{indus_type}" and test_month={test_month}')
        price_table = cx_read_sql(
            f'select * from static_data_price_{pool_name}_history where avg_price > {price_threshold} and test_month={test_month}')
    if price_name == 'lowprice':
        indus_table = cx_read_sql(
            f'select * from static_data_industry_{pool_name}_history where {indus_class}="{indus_type}" and test_month={test_month}')
        price_table = cx_read_sql(
            'select * from static_data_price_{}_history where avg_price <= {} and test_month={}'.format(
                pool_name, price_threshold, test_month))
    tickers = set(indus_table['ticker']) & set(price_table['ticker'])
    # ordered ticker list
    tickers = sorted(tickers)

    return tickers

def get_return(ret_name, test_month, tickers):
    tickers = tuple(tickers)
    labels = cx_read_sql( 'select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format(ret_name, test_month, tickers))

    return labels

def get_indus_list(pool_name, test_month, indus_class):
    indus_table = cx_read_sql('select distinct {} from static_data_industry_{}_history where test_month={}'.format(
        indus_class, pool_name, test_month))

    return list(indus_table[indus_class])

if __name__ == '__main__':
    pool_name = 'hs300'
    price_name = 'highprice'
    test_month = 202301
    indus_class = 'wind1'
    indus_list = get_indus_list(pool_name, test_month, indus_class)
    ret_name = '15s'
    for indus_type in indus_list:
        tickers = get_ticker_list(pool_name, price_name, test_month, indus_class, indus_type)
        ret = get_return(ret_name, test_month, tickers)
        print(len(tickers), len(ret))

