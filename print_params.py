
import os

import utils

def print_ticker(indus_from, indus_type):

    data_hs = utils.cx_read_sql('select * from static_data_hs300_all where {}="{}" and avg_price > {} and test_month=202306'.format(indus_from, indus_type,
                                                                                      10, ))
    data_zz = utils.cx_read_sql('select * from static_data_zz500_all where {}="{}" and avg_price > {} and test_month=202306'.format(indus_from, indus_type,
                                                                                      10, ))
    tickers = tuple(data_hs['ticker']) + tuple(data_zz['ticker'])

    return len(tickers)

if __name__ == '__main__':
    indus_from = 'wind1'
    c = 0
    for i in range(12):
        c += print_ticker(indus_from, i)
    print(c)