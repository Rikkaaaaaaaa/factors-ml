import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy
import pymysql
import connectorx as cx

host = '10.95.145.83'
user = 'junxiang.ruan'
password = 'Et20230209'
port = 3306

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


def cx_read_sql(query, database='strategy'):
    conn = 'mysql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)
    data = cx.read_sql(conn, query)
    return data

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
        index_str = ''
        for index in index_cols:
            index_str += index + ', '
        index_str = index_str[:-2]

        conn = pymysql.connect(host=host, port=port, user=user, password=password,
                               db=database, charset='utf8', cursorclass=pymysql.cursors.DictCursor)
        cur = conn.cursor()
        cur.execute(
            'CREATE INDEX {}_IDX USING BTREE ON {}.{}({});'.format(table_name, database, table_name, index_str))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print('create index in table "{}" error: {}'.format(table_name, e))


if __name__ == '__main__':
    strategy_engine = create_pd_engine('strategy')
    smart_order_position_engine = create_pd_engine('strategy')
    # path = 'D:\\wuyi\\EQ Algo Trading\\backtest_result_analysis\\'
    # main_statistics = pd.read_csv(os.path.join(path, "analysis", 'main_statistics.csv'))

    # read_sql
    temp_date_data = pd.read_sql('select * from static_data where ticker="000001.SZ"', strategy_engine)
    print(temp_date_data)