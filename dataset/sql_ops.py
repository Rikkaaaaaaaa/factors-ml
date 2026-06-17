import numpy as np
import pandas as pd
from utils.mysql import cx_read_sql
from utils.logger import get_root_logger
from utils import list2str
from utils.ddb import read_ddb_factor, read_ddb_return, read_ddb, read_ddb_hk, read_ddb_factor_low_price, read_ddb_factor_by_ticker, read_ddb_factor_by_ticker_filtered
import dolphindb as ddb


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
    if opt.get('dataset'):
        opt = opt['dataset']
    pool_name = opt['pool_name']
    indus_class = opt['indus_class']
    indus_table_suffix = opt['indus_table_suffix']
    if isinstance(indus_table_suffix, str) :
        if  len(indus_table_suffix) > 0:
            indus_table_suffix = '_' + indus_table_suffix
        else:
            indus_table_suffix =  ''
    else:
        raise ValueError(f"Param in opt['dataset']['indus_table_suffix'] must be string 'old' or '', but now it is {indus_table_suffix}")
    indus_list = []
    if opt['price_name'] == 'highprice':
        indus_table = cx_read_sql('select distinct {} from static_data_industry_{}_history{} where test_month={}'.format(
                                    indus_class, pool_name, indus_table_suffix, first_month))

        indus_list.extend(list(indus_table[indus_class]))

    # default class num of low price is zero
    else:
        indus_list = [0]

    return set(indus_list)

def check_price_group(opt, first_month):
    pool_name = opt['dataset']['pool_name']
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
    indus_table = cx_read_sql('select distinct {} from static_data_price_{}_history{} where test_month={} and avg_price <= 10'.format(
                                indus_class, pool_name, indus_table_suffix, first_month))
    indus_list.extend(list(indus_table[indus_class]))
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
            f"Params in opt['dataset']['indus_table_suffix'] must be string 'old' or '', but now it is {indus_table_suffix}")

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
        raise ValueError(f"{test_month}_indus_{indus_type}: The number of tickers(average price > {avg_price}) is 0")

    return tickers


def load_ticker_by_indus_hk(opt, pool, indus_type, test_month):
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
            f"Params in opt['dataset']['indus_table_suffix'] must be string 'old' or '', but now it is {indus_table_suffix}")

    if price_name == 'highprice':
        indus_table = cx_read_sql('select * from static_data_industry_{}_history{} where {}="{}" and test_month={}'.format(pool,
                                   indus_table_suffix, indus_class, indus_type, test_month))
        price_table = cx_read_sql('select * from static_data_{}_liquidity_history where avg_price > {} and test_month={}'.format(
                                   pool, avg_price, test_month))
    if price_name == 'lowprice':
        # Note that lowprice stocks have no indus_type, default is 0
        indus_table = cx_read_sql('select * from static_data_industry_{}_history{} where test_month={}'.format(pool, indus_table_suffix, test_month))
        price_table = cx_read_sql('select * from static_data_{}_liquidity_history where avg_price <= {} and test_month={}'.format(pool, avg_price, test_month))

    liquidity_table = cx_read_sql(
        'select * from static_data_hk_liquidity_history where test_month={} and liquidity_group=1'.format(test_month))

    tickers = set(indus_table['ticker']) & set(price_table['ticker']) & set(liquidity_table['ticker'])

    if len(tickers) == 0:
        raise ValueError(f"{test_month}_indus_{indus_type}: The number of tickers(average price > {avg_price}) is 0")

    return tickers

def load_ticker_by_price_group(opt, pool, indus_type, test_month):
    # fetch price and indus table from sql
    indus_class = opt['dataset']['indus_class']
    indus_table_suffix = opt['dataset']['indus_table_suffix']
    if isinstance(indus_table_suffix, str):
        if len(indus_table_suffix) > 0:
            indus_table_suffix = '_' + indus_table_suffix
        else:
            indus_table_suffix = ''
    else:
        raise ValueError(
            f"Params in opt['dataset']['indus_table_suffix'] must be string 'old' or '', but now it is {indus_table_suffix}")


    indus_table = cx_read_sql('select * from static_data_price_{}_history{} where {}="{}" and test_month={}'.format(pool,
                               indus_table_suffix, indus_class, indus_type, test_month))
    tickers = set(indus_table['ticker'])
    if len(tickers) == 0:
        raise FileExistsError(f"{test_month}_price_group_{indus_type}: The number of tickers is 0")

    return tickers


def load_labels(opt, tickers, month):
    # ret_name = opt['dataset']['ret_name']
    io_backend = opt['dataset']['io_backend']

    if io_backend == 'ddb':
        data_base = list(opt['dataset']['ret_table'].keys())[0]
        table_name =  opt['dataset']['ret_table'][data_base]
        labels = read_ddb_return(data_base, table_name, month, tickers, opt['dataset']['trading_hours'])

    # mix return by weights
    if opt['dataset'].get('mix_return'):
        data_base = list(opt['dataset']['ret_table'].keys())[0]
        table_name = opt['dataset']['ret_table'][data_base]
        labels = read_ddb_return(data_base, table_name, month, tickers, opt['dataset']['trading_hours'])

        ret_cols = opt['dataset']['mix_return']['ret_cols']
        weights = opt['dataset']['mix_return']['weights']
        mixed_ret = labels[ret_cols].values
        np_weights = np.array(weights)
        mixed_ret = np.sum(np_weights * mixed_ret, axis=1)/len(ret_cols)
        labels[f'ret_mix'] = mixed_ret

    ## filter all the other columns
    #labels = labels[['ticker', 'date', "time", f'ret_{ret_name}']]

    return labels


def load_labels_hk(opt, tickers, month):
    # ret_name = opt['dataset']['ret_name']
    io_backend = opt['dataset']['io_backend']

    if io_backend == 'ddb':
        data_base = list(opt['dataset']['ret_table'].keys())[0]
        table_name =  opt['dataset']['ret_table'][data_base]
        labels = read_ddb_return(data_base, table_name, month, tickers, opt['dataset']['trading_hours'], is_hk=True)

    # mix return by weights
    if opt['dataset'].get('mix_return'):
        data_base = list(opt['dataset']['ret_table'].keys())[0]
        table_name = opt['dataset']['ret_table'][data_base]
        labels = read_ddb_return(data_base, table_name, month, tickers, opt['dataset']['trading_hours'], is_hk=True)

        ret_cols = opt['dataset']['mix_return']['ret_cols']
        weights = opt['dataset']['mix_return']['weights']
        mixed_ret = labels[ret_cols].values
        np_weights = np.array(weights)
        mixed_ret = np.sum(np_weights * mixed_ret, axis=1)/len(ret_cols)
        labels[f'ret_mix'] = mixed_ret

    ## filter all the other columns
    #labels = labels[['ticker', 'date', "time", f'ret_{ret_name}']]

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


def align_factor_ticker(factor_table, all_ticker, pool_name, check_ticker_month, test_month, rebalancing_tables, training_month_num=3, io_backend="ddb", logger_name=None):
    logger = get_root_logger(logger_name=logger_name)
    cur_ticker = all_ticker.copy()
    train_tickers = []
    test_tickers = []
    for database in factor_table.keys():
        for table in factor_table[database]:
            for month in check_ticker_month:
                ddb_month = str(month)[0:4] + '.' + str(month)[4:] + 'M'

                if is_rebalanced(test_month, training_month_num) and need_rebalanced_factor(month, test_month) and table in rebalancing_tables:
                    if io_backend == "sql":
                        factor_ticker = cx_read_sql(f'select distinct ticker from {table}_{month}_index_rebalancing_{pool_name}', database=database)
                    if io_backend == "ddb":
                        factor_ticker = read_ddb(f'select distinct(securityCode) as ticker from loadTable("{database}", "{table}_index_rebalancing_{pool_name}") where month(time)={ddb_month}')

                else:
                    if io_backend == "sql":
                        factor_ticker = cx_read_sql(f'select distinct ticker from {table}_{month}', database=database)
                    if io_backend == "ddb":
                        factor_ticker = read_ddb(f'select distinct(securityCode) as ticker from loadTable("{database}", "{table}_{pool_name}") where month(time)={ddb_month}')
                # check missing tickers
                factor_ticker = factor_ticker['ticker']
                #cur_ticker = cur_ticker & set(factor_ticker)
                missing_tickers = set(all_ticker) - set(factor_ticker)

                if len(missing_tickers) > 0:
                    if is_rebalanced(test_month, training_month_num) and need_rebalanced_factor(month, test_month) and table in rebalancing_tables:
                    #raise ValueError(f"There are missing tickers in {database}.{table} in {month}:  {list2str(missing_tickers)}")
                        logger.warning(f"There are missing tickers in {database}.{table}_index_rebalancing_{pool_name} in {month}: {list2str(missing_tickers)}")
                    else:
                        logger.warning(f"There are missing tickers in {database}.{table} in {month}: {list2str(missing_tickers)}")

    return cur_ticker


def align_factor_ticker_hk(factor_table, all_ticker, pool_name, check_ticker_month, test_month, rebalancing_tables, training_month_num=3, io_backend="ddb", logger_name=None):
    logger = get_root_logger(logger_name=logger_name)
    cur_ticker = all_ticker.copy()
    train_tickers = []
    test_tickers = []
    for database in factor_table.keys():
        for table in factor_table[database]:
            for month in check_ticker_month:
                ddb_month = str(month)[0:4] + '.' + str(month)[4:] + 'M'

                if is_rebalanced(test_month, training_month_num) and need_rebalanced_factor(month, test_month) and table in rebalancing_tables:
                    if io_backend == "sql":
                        factor_ticker = cx_read_sql(f'select distinct ticker from {table}_{month}_index_rebalancing_{pool_name}', database=database)
                    if io_backend == "ddb":
                        factor_ticker = read_ddb_hk(f'select distinct(securityCode) as ticker from loadTable("{database}", "{table}_index_rebalancing_{pool_name}") where month(time)={ddb_month}')

                else:
                    if io_backend == "sql":
                        factor_ticker = cx_read_sql(f'select distinct ticker from {table}_{month}', database=database)
                    if io_backend == "ddb":
                        factor_ticker = read_ddb_hk(f'select distinct(securityCode) as ticker from loadTable("{database}", "{table}") where month(time)={ddb_month}')
                # check missing tickers
                factor_ticker = factor_ticker['ticker']
                #cur_ticker = cur_ticker & set(factor_ticker)
                missing_tickers = set(all_ticker) - set(factor_ticker)

                if len(missing_tickers) > 0:
                    if is_rebalanced(test_month, training_month_num) and need_rebalanced_factor(month, test_month) and table in rebalancing_tables:
                    #raise ValueError(f"There are missing tickers in {database}.{table} in {month}:  {list2str(missing_tickers)}")
                        logger.warning(f"There are missing tickers in {database}.{table}_index_rebalancing_{pool_name} in {month}: {list2str(missing_tickers)}")
                    else:
                        logger.warning(f"There are missing tickers in {database}.{table} in {month}: {list2str(missing_tickers)}")

    return cur_ticker


def load_factor_by_table(database, table, tickers, pool_name, loading_month, test_month, rebalancing_tables, trading_hours=None, training_month_num=3, io_backend='sql'):
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
            #factor = read_ddb_factor(database, f'{table}_index_rebalancing_{pool_name}', loading_month, tickers, trading_hours)
            factor = read_ddb_factor_by_ticker(database, f'{table}_index_rebalancing_{pool_name}', loading_month, tickers, trading_hours)

    else:
        if io_backend == "sql":
            factor = cx_read_sql(f'select * from {table}_{loading_month} where {ticker_condition}', database=database)
        if io_backend == "ddb":
            tickers = list(tickers)
            #factor = read_ddb_factor(database, f'{table}_{pool_name}', loading_month, tickers, trading_hours)
            factor = read_ddb_factor_by_ticker(database, f'{table}_{pool_name}', loading_month, tickers, trading_hours)

    return factor


def load_factor_by_table_filtered(database, table, tickers, pool_name, loading_month, test_month, rebalancing_tables,
                                  trading_hours=None, training_month_num=3, io_backend='sql', factor_names=None):
    if len(tickers) == 1:
        ticker_condition = f'ticker="{tickers[0]}"'
    else:
        ticker_condition = f'ticker in {tickers}'

    if is_rebalanced(test_month, training_month_num) and need_rebalanced_factor(loading_month, test_month) and  table in rebalancing_tables:
        if io_backend == "sql":
            factor = cx_read_sql(f'select * from {table}_{loading_month}_index_rebalancing where {ticker_condition}',
                                 database=database)
        if io_backend == "ddb":
            tickers = list(tickers)
            factor = read_ddb_factor_by_ticker_filtered(
                database, f'{table}_index_rebalancing_{pool_name}', loading_month, tickers, trading_hours, factor_names
            )
    else:
        if io_backend == "sql":
            factor = cx_read_sql(f'select * from {table}_{loading_month} where {ticker_condition}', database=database)
        if io_backend == "ddb":
            tickers = list(tickers)
            factor = read_ddb_factor_by_ticker_filtered(
                database, f'{table}_{pool_name}', loading_month, tickers, trading_hours, factor_names
            )

    return factor


def load_factor_by_table_hk(database, table, tickers, pool_name, loading_month, test_month, rebalancing_tables, trading_hours=None, training_month_num=3, io_backend='sql'):
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
            #factor = read_ddb_factor(database, f'{table}_index_rebalancing_{pool_name}', loading_month, tickers, trading_hours)
            factor = read_ddb_factor_by_ticker(database, f'{table}_index_rebalancing', loading_month, tickers,trading_hours, is_hk=True)

    else:
        if io_backend == "sql":
            factor = cx_read_sql(f'select * from {table}_{loading_month} where {ticker_condition}', database=database)
        if io_backend == "ddb":
            tickers = list(tickers)
            #factor = read_ddb_factor(database, f'{table}_{pool_name}', loading_month, tickers, trading_hours)
            factor = read_ddb_factor_by_ticker(database, f'{table}', loading_month, tickers, trading_hours, is_hk=True)

    return factor


def load_factor_by_table_low_price(database, table, tickers, pool_name, loading_month, test_month, rebalancing_tables, trading_hours=None, training_month_num=3, io_backend='sql'):
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
            factor = read_ddb_factor_low_price(database, f'{table}_index_rebalancing_{pool_name}', loading_month, tickers, trading_hours)
    else:
        if io_backend == "sql":
            factor = cx_read_sql(f'select * from {table}_{loading_month} where {ticker_condition}', database=database)
        if io_backend == "ddb":
            tickers = list(tickers)
            factor = read_ddb_factor_low_price(database, f'{table}_{pool_name}', loading_month, tickers, trading_hours)

    return factor



# =============================== SOP DDB functions =============================
def read_table(ddb_info, query):
    host, port, username, password = ddb_info[0], ddb_info[1], ddb_info[2], ddb_info[3]
    s = ddb.session()
    s.connect(host, port, username, password)
    df = s.run(query)
    s.close()
    return df


def get_sop_fill_flag_ddb(tickers, pool_name, start_month, end_month, tick_ahead, bs_flag):
    ddb_info = ['10.95.145.91', 8993, "quantStrat", "eqalgo_2024"]
    start_month_str = str(start_month)[:4] + '.' + str(start_month)[-2:]
    end_month_str = str(end_month)[:4] + '.' + str(end_month)[-2:]

    if len(tickers) == 1:
        ticker_condition = f'securityCode="{tickers[0]}"'
    else:
        ticker_condition = f'securityCode in {tickers}'

    table_name = f'fill_flag_{pool_name}_{tick_ahead}_{bs_flag}'
    # TODO temp version for selected stock pool, can be deleted after 202510
    if 'selected' in pool_name:
        table_name = f'fill_flag_{pool_name.split("_")[0]}_{tick_ahead}_{bs_flag}'
    if 'zz2000_' in pool_name:
        table_name = f'fill_flag_{pool_name.split("_")[0]}_{tick_ahead}_{bs_flag}'

    # fill_flag_query = f'select factorValue from loadTable("dfs://smart_order_position", "{table_name}") where month(tradeTime)>={start_month_str}M, month(tradeTime)<={end_month_str}M, securityCode=`{ticker} pivot by tradeTime, securityCode, factorName'
    fill_flag_query = f"""
    tb=select * from loadTable("dfs://smart_order_position", "{table_name}") where month(tradeTime)>={start_month_str}M, month(tradeTime)<={end_month_str}M, {ticker_condition}
    select factorValue from tb pivot by tradeTime, securityCode, factorName
    """
    fill_flag_data = read_table(ddb_info, fill_flag_query)

    fill_flag_data.rename(columns={"securityCode": "ticker"}, inplace=True)
    fill_flag_data.insert(0, 'date', fill_flag_data["tradeTime"].dt.strftime('%Y%m%d').astype(int))
    fill_flag_data["time"] = (fill_flag_data["tradeTime"].dt.hour * 10000000 + fill_flag_data["tradeTime"].dt.minute * 100000 +
                      fill_flag_data["tradeTime"].dt.second * 1000 + fill_flag_data["tradeTime"].dt.microsecond // 1000)
    return fill_flag_data
