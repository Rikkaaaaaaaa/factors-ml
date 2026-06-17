import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy
import pymysql
import connectorx as cx


DEFAULT_MYSQL_STRATEGY_CONFIG = {
    'host': '10.95.145.83',
    'user': 'taorui',
    'password': 'Et20231207',
    'port': 3306,
}

host = DEFAULT_MYSQL_STRATEGY_CONFIG['host']
user = DEFAULT_MYSQL_STRATEGY_CONFIG['user']
password = DEFAULT_MYSQL_STRATEGY_CONFIG['password']
port = DEFAULT_MYSQL_STRATEGY_CONFIG['port']


def set_mysql_strategy_config(config=None):
    global host, user, password, port
    config = config or {}
    host = config.get('host', DEFAULT_MYSQL_STRATEGY_CONFIG['host'])
    user = config.get('user', DEFAULT_MYSQL_STRATEGY_CONFIG['user'])
    password = config.get('password', DEFAULT_MYSQL_STRATEGY_CONFIG['password'])
    port = config.get('port', DEFAULT_MYSQL_STRATEGY_CONFIG['port'])


def create_pd_engine(database):
    return create_engine('mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8'.format(user, password, host, port, database))


def read_table(database, query):
    try:
        conn = 'mysql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)
        df = cx.read_sql(conn, query)
        return df
    except Exception as e:
        print('run query"{}" error: {}'.format(query, e))


def read_table_by_ticker(database, table_name, ticker):
    conn = 'mysql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)
    query = 'select * from {} where ticker="{}"'.format(table_name, ticker)
    try:
        df = cx.read_sql(conn, query)
        return df
    except Exception as e:
        print('run query"{}" error: {}'.format(query, e))


def read_table_by_date(database, table_name, date):
    conn = 'mysql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)
    query = 'select * from {} where date={}'.format(table_name, date)
    try:
        df = cx.read_sql(conn, query)
        return df
    except Exception as e:
        print('run query"{}" error: {}'.format(query, e))


def read_table_by_ticker_and_period(database, table_name, ticker, start_date, end_date):
    conn = 'mysql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)
    query = 'select * from {} where ticker="{}" and date>={} and date<={}'.format(
        table_name, ticker, start_date, end_date)
    try:
        df = cx.read_sql(conn, query)
        return df
    except Exception as e:
        print('run query"{}" error: {}'.format(query, e))


def delete_table(database, table_name):
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password,
                               db=database, charset='utf8', cursorclass=pymysql.cursors.DictCursor)
        cur = conn.cursor()
        cur.execute(
            'DROP TABLE {}'.format(table_name))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print('no table "{}" in database "{}", error: {}'.format(table_name, database, e))


def delete_query(database, query):
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password,
                               db=database, charset='utf8', cursorclass=pymysql.cursors.DictCursor)
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print('delete query "{}" error, error: {}'.format(query, e))


def create_index(database, table_name, index_cols):
    try:
        index_str = ','.join(index_cols)

        conn = pymysql.connect(host=host, port=port, user=user, password=password,
                               db=database, charset='utf8', cursorclass=pymysql.cursors.DictCursor)
        cur = conn.cursor()
        index_flag = cur.execute('SHOW INDEX from {}'.format(table_name))
        if index_flag == 0:
            cur.execute(
                'CREATE INDEX {}_IDX USING BTREE ON {}.{}({});'.format(table_name, database, table_name, index_str))
            conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print('create index in table "{}" error: {}'.format(table_name, e))


if __name__ == '__main__':
    strategy_engine = create_pd_engine('strategy')
    smart_order_position_engine = create_pd_engine('smart_order_position')
    # path = 'D:\\wuyi\\EQ Algo Trading\\backtest_result_analysis\\'
    # main_statistics = pd.read_csv(os.path.join(path, "analysis", 'main_statistics.csv'))

    # read_sql
    sql = 'select * from test where ticker="000001.SZ"'
    # sql = "select distinct date from fill_flag_1_b_202305"
    temp_data = read_table('smart_order_position', sql)
    print(temp_data)

    # # to_sql
    # import datetime
    # print('start time:{}'.format(datetime.datetime.now()))
    # temp_data.to_sql('test', con=smart_order_position_engine, index=False, if_exists='append',
    #                       chunksize=10000)
    # print('end time:{}'.format(datetime.datetime.now()))

    # delete table
    # delete_table(database, table_name)

    # create index
    # create_index(database, table_name, ['ticker', 'date', 'time'])

    # import os
    # data = pd.read_csv(
    #     os.path.join(os.path.abspath(os.getcwd()), 'output/data/', '000300.csv'))['ts_code'].tolist()
    #
    # path = os.path.join(os.path.abspath(os.getcwd()), 'output/multi_factor_analysis/')
    # tick_ahead_list = ['0mid', '1', '1mid', '2']
    # for ticker in data:
    #     for tick_ahead in tick_ahead_list:
    #         pre_processing = pd.read_csv(os.path.join(path, 'pre_processing/',
    #                                                   'ticker_600519.SH_test_month_202202_model_factors_1_b.csv'))
    #         benchmark = pd.read_csv(os.path.join(path, 'benchmark/',
    #                                                   'ticker_600519.SH_test_month_202202_model_factors_1_b.csv'))
    #         params = pd.read_csv(os.path.join(path, 'model_params/Logit/',
    #                                                   'ticker_600519.SH_test_month_202202_model_factors_1_b.csv'))
    #
    #         pre_processing.columns = ['factor_name', 'min', 'max', 'mean', 'std']
    #         pre_processing['ticker'] = ticker
    #         pre_processing = pre_processing[['ticker'] + pre_processing.columns.to_list()[:-1]]
    #         pre_processing.to_sql('pre_processing_{}'.format(tick_ahead), con=smart_order_position_engine, index=False,
    #                               if_exists='append', chunksize=10000,
    #                               dtype={'ticker': sqlalchemy.types.VARCHAR(length=10)})
    #
    #         benchmark.columns = ['ticker', 'dynamic_benchmark', 'fixed_benchmark']
    #         benchmark['ticker'] = ticker
    #         benchmark.to_sql('benchmark_{}'.format(tick_ahead), con=smart_order_position_engine, index=False,
    #                          if_exists='append', chunksize=10000,
    #                          dtype={'ticker': sqlalchemy.types.VARCHAR(length=10)})
    #
    #         params.columns = ['factor_name', 'coef']
    #         params = params.set_index('factor_name').T
    #         params['ticker'] = ticker
    #         params = params[['ticker'] + params.columns.to_list()[:-1]]
    #         params.to_sql('params_{}'.format(tick_ahead), con=smart_order_position_engine, index=False,
    #                          if_exists='append', chunksize=10000,
    #                          dtype={'ticker': sqlalchemy.types.VARCHAR(length=10)})
    #
    # for tick_ahead in tick_ahead_list:
    #     create_index('smart_order_position', 'pre_processing_{}'.format(tick_ahead), ['ticker'])
    #     create_index('smart_order_position', 'benchmark_{}'.format(tick_ahead), ['ticker'])
    #     create_index('smart_order_position', 'params_{}'.format(tick_ahead), ['ticker'])
