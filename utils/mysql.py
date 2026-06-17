import pandas as pd
try:
    from sqlalchemy import create_engine
    import sqlalchemy
except ImportError:
    create_engine = None
    sqlalchemy = None
import pymysql
try:
    import connectorx as cx
except ImportError:
    cx = None

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
    if cx is not None:
        conn = 'mysql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)
        return cx.read_sql(conn, query)

    conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset='utf8')
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()

def create_pd_engine(database):
    if create_engine is None:
        raise ImportError("sqlalchemy is required for create_pd_engine but is not installed.")
    return create_engine('mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8'.format(user, password, host, port, database))

def read_table(database, query):
    try:
        if cx is not None:
            conn = 'mysql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)
            return cx.read_sql(conn, query)
        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset='utf8')
        try:
            return pd.read_sql(query, conn)
        finally:
            conn.close()
    except Exception as e:
        print('run query"{}" error: {}'.format(query, e))


def read_table_by_ticker(database, table_name, ticker):
    query = 'select * from {} where ticker="{}"'.format(table_name, ticker)
    try:
        if cx is not None:
            conn = 'mysql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)
            return cx.read_sql(conn, query)
        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset='utf8')
        try:
            return pd.read_sql(query, conn)
        finally:
            conn.close()
    except Exception as e:
        print('run query"{}" error: {}'.format(query, e))


def read_table_by_date(database, table_name, date):
    query = 'select * from {} where date={}'.format(table_name, date)
    try:
        if cx is not None:
            conn = 'mysql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)
            return cx.read_sql(conn, query)
        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset='utf8')
        try:
            return pd.read_sql(query, conn)
        finally:
            conn.close()
    except Exception as e:
        print('run query"{}" error: {}'.format(query, e))


def read_table_by_ticker_and_period(database, table_name, ticker, start_date, end_date):
    query = 'select * from {} where ticker="{}" and date>={} and date<={}'.format(
        table_name, ticker, start_date, end_date)
    try:
        if cx is not None:
            conn = 'mysql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)
            return cx.read_sql(conn, query)
        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset='utf8')
        try:
            return pd.read_sql(query, conn)
        finally:
            conn.close()
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
        # to avoid index name exceed 64
        if len(table_name) > 59:
            print("IDX name is too long, clip to size 60!")
            index_name = table_name[:59]
        else:
            index_name = table_name
        cur.execute(
            'CREATE INDEX {}_IDX USING BTREE ON {}.{}({});'.format(index_name, database, table_name, index_str))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print('create index in table "{}" error: {}'.format(table_name, e))



def delete_by_test_month_and_ticker_list(database, table_name, test_month, ticker_list):
    ticker_list_str = list(map(lambda x: '"' + x + '"', ticker_list))
    ticker_list_str = ','.join(ticker_list_str)
    ticker_list_str = '(' + ticker_list_str + ')'
    conn = pymysql.connect(host=host, port=port, user=user, passwd=password, db=database)
    cursor = conn.cursor()
    sql = 'delete from {}.{} where test_month={} and ticker in {}'.format(database, table_name, test_month, ticker_list_str)
    try:
        cursor.execute(sql)
        conn.commit()
        print(sql)
    except Exception as e:
        print('run query"{}" error: {}'.format(sql, e))
    conn.close()


def delete_by_date_and_ticker_list(database, table_name, date, ticker_list):
    ticker_list_str = list(map(lambda x: '"' + x + '"', ticker_list))
    ticker_list_str = ','.join(ticker_list_str)
    ticker_list_str = '(' + ticker_list_str + ')'
    conn = pymysql.connect(host=host, port=port, user=user, passwd=password, db=database)
    cursor = conn.cursor()
    sql = 'delete from {}.{} where date={} and ticker in {}'.format(database, table_name, date, ticker_list_str)
    try:
        cursor.execute(sql)
        conn.commit()
        print(sql)
    except Exception as e:
        print('run query"{}" error: {}'.format(sql, e))
    conn.close()


def delete_by_ticker_list(database, table_name, ticker_list):
    ticker_list_str = list(map(lambda x: '"' + x + '"', ticker_list))
    ticker_list_str = ','.join(ticker_list_str)
    ticker_list_str = '(' + ticker_list_str + ')'
    conn = pymysql.connect(host=host, port=port, user=user, passwd=password, db=database)
    cursor = conn.cursor()
    sql = 'delete from {}.{} where ticker in {}'.format(database, table_name, ticker_list_str)
    try:
        cursor.execute(sql)
        conn.commit()
        print(sql)
    except Exception as e:
        print('run query"{}" error: {}'.format(sql, e))
    conn.close()


def delete_by_month(database, table_name, month):

    conn = pymysql.connect(host=host, port=port, user=user, passwd=password, db=database)
    cursor = conn.cursor()
    sql = 'delete from {}.{} where date>{} and date<{}'.format(database, table_name, month*100, (month+1)*100 )
    try:
        cursor.execute(sql)
        conn.commit()
        print(sql)
    except Exception as e:
        print('run query"{}" error: {}'.format(sql, e))
    conn.close()

