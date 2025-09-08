import dolphindb as ddb
import pandas as pd
import numpy as np
import time
import dolphindb.settings as keys

log_factor_name = ['book_pressure_15s', 'book_pressure_30s', 'book_pressure_delta_15s', 'higher_bid_amt_15s',
                  'higher_bid_amt_30s', 'higher_bid_amt_60s', 'lower_ask_amt_15s', 'lower_ask_amt_30s',
                  'lower_ask_amt_60s',
                  'net_bid_amt_delta_15s', 'net_bid_amt_delta_30s', 'net_bid_amt_delta_60s', 'indus_book_pressure_15s',
                  'indus_book_pressure_delta_15s', 'indus_higher_bid_amt_15s', 'indus_higher_bid_amt_30s',
                  'indus_higher_bid_amt_60s',
                  'indus_lower_ask_amt_15s', 'indus_lower_ask_amt_30s', 'indus_lower_ask_amt_60s',
                  'indus_net_bid_amt_delta_15s',
                  'indus_net_bid_amt_delta_30s', 'indus_net_bid_amt_delta_60s', 'mkt_book_pressure_15s',
                  'mkt_higher_bid_amt_15s',
                  'mkt_lower_ask_amt_15s', 'mkt_net_bid_amt_delta_15s']


def preprocess(factor):
    # preprocessing after fetcing from sql
    # log factor
    def get_log_factor_df(df_factors):
        df_factors[df_factors > 0] = np.log(df_factors[df_factors > 0] + 1)
        df_factors[df_factors < 0] = -np.log(-df_factors[df_factors < 0] + 1)
        return df_factors

    for log_factor in log_factor_name:
        if log_factor in factor.columns:
            factor.loc[:, log_factor] = get_log_factor_df(factor[log_factor].values)
    # other ops
    # ......
    return factor

DDB_config = { "server": "10.95.145.91",
               "port": 8992,
               "userName": "quantStrat",
               "userKey": "eqalgo_2024"
            }

class DDB_connector():
    def __init__(self, DDB_config):
        self.ddb_session = ddb.session(
            DDB_config["server"],
            DDB_config["port"],
            DDB_config["userName"],
            DDB_config["userKey"],
            keepAliveTime=12000,
            protocol=keys.PROTOCOL_DDB,
        )
        self.ddb_session.setTimeout(3600)

    def query_data(self, query):
        res = self.ddb_session.run(query)

        return res

    def close(self):
        self.ddb_session.close()

def read_ddb(query):
    ddb = DDB_connector(DDB_config)
    res = ddb.query_data(query)
    ddb.close()

    return res

def read_ddb_factor(data_base, table_name, test_month, tickers, trading_hours=None):
    test_month = str(test_month)
    test_month = test_month[0:4] + '.' + test_month[4:] + 'M'

    # select wide table
    start_time = time.time()
    #print(f"[{table_name}][{test_month}][{len(tickers)}] Connecting DDB")
    ddb_reader = DDB_connector(DDB_config)
    scripts = "factorTable = loadTable(\"{}\", \"{}\")".format(data_base, table_name)
    ddb_reader.ddb_session.run(scripts)
    scripts =  "retTable = select * from factorTable where month(time)={} and securityCode in {}".format(test_month, tickers)
    ddb_reader.ddb_session.run(scripts)
    scripts = "select factorValue from retTable pivot by time, securityCode, factorName"
    factor = ddb_reader.ddb_session.run(scripts)
    ddb_reader.close()
    #print(f"[{table_name}][{test_month}][{len(tickers)}] load data time: {time.time() - start_time}")

    # transfer to ticker date time format like sql
    start_time = time.time()
    factor.rename(columns={"securityCode": "ticker"}, inplace=True)
    factor.insert(0, 'date', factor["time"].dt.strftime('%Y%m%d').astype(int))
    factor["time"] = (factor["time"].dt.hour * 10000000 + factor["time"].dt.minute * 100000 +
                      factor["time"].dt.second * 1000)
    # filter by select_period dict
    if isinstance(trading_hours, dict):
        factor = factor[ ((factor["time"] >= trading_hours['am_start_time']*1000) & (factor["time"] <= trading_hours['am_end_time']*1000))
                         | ((factor["time"] >= trading_hours['pm_start_time'] * 1000) & (factor["time"] <= trading_hours['pm_end_time'] * 1000))
                         ]
    else:
        # else time between [94000, 145700]
        factor = factor[(factor["time"] >= 94000000) & (factor["time"] <= 145700000)]
    #print(f"[{table_name}][{test_month}][{len(tickers)}] filter data time: {time.time() - start_time}")

    # print(f'load date time: {time.time() - start_time}')
    return factor


def read_ddb_factor_low_price(data_base, table_name, test_month, tickers, trading_hours=None):
    test_month = str(test_month)
    test_month = test_month[0:4] + '.' + test_month[4:] + 'M'

    # select wide table
    start_time = time.time()
    #print(f"[{table_name}][{test_month}][{len(tickers)}] Connecting DDB")
    ddb_reader = DDB_connector(DDB_config)
    scripts = "factorTable = loadTable(\"{}\", \"{}\")".format(data_base, table_name)
    ddb_reader.ddb_session.run(scripts)
    scripts =  "retTable = select * from factorTable where month(time)={} and securityCode in {}".format(test_month, tickers)
    ddb_reader.ddb_session.run(scripts)
    scripts = "select factorValue from retTable pivot by time, securityCode, factorName"
    factor = ddb_reader.ddb_session.run(scripts)
    ddb_reader.close()
    #print(f"[{table_name}][{test_month}][{len(tickers)}] load data time: {time.time() - start_time}")

    # transfer to ticker date time format like sql
    start_time = time.time()
    factor.rename(columns={"securityCode": "ticker"}, inplace=True)
    factor.insert(0, 'date', factor["time"].dt.strftime('%Y%m%d').astype(int))
    factor["time"] = (factor["time"].dt.hour * 10000000 + factor["time"].dt.minute * 100000 +
                      factor["time"].dt.second * 1000)
    # filter by select_period dict
    if isinstance(trading_hours, dict):
        factor = factor[ ((factor["time"] >= trading_hours['am_start_time']*1000) & (factor["time"] <= trading_hours['am_end_time']*1000))
                         | ((factor["time"] >= trading_hours['pm_start_time'] * 1000) & (factor["time"] <= trading_hours['pm_end_time'] * 1000))
                         ]
    else:
        # else time between [94000, 145700]
        factor = factor[(factor["time"] >= 93000000) & (factor["time"] <= 145700000)]
    #print(f"[{table_name}][{test_month}][{len(tickers)}] filter data time: {time.time() - start_time}")

    # print(f'load date time: {time.time() - start_time}')
    return factor


def read_ddb_return(data_base, table_name, test_month, tickers, trading_hours=None):
    test_month = str(test_month)
    test_month = test_month[0:4] + '.' + test_month[4:] + 'M'
    ddb_reader = DDB_connector(DDB_config)

    # select wide table
    scripts = "retTable = loadTable(\"{}\", \"{}\")".format(data_base, table_name)
    ddb_reader.ddb_session.run(scripts)
    scripts =  "select * from retTable where month(time)={} and securityCode in {}".format(test_month, tickers)
    ret = ddb_reader.ddb_session.run(scripts)
    ddb_reader.close()

    # transfer to ticker date time format like sql
    ret.rename(columns={"securityCode": "ticker"}, inplace=True)
    ret.insert(0, 'date', ret["time"].dt.strftime('%Y%m%d').astype(int))
    ret["time"] = (ret["time"].dt.hour * 10000000 + ret["time"].dt.minute * 100000 +
                   ret["time"].dt.second * 1000)

    # filter by select_period dict
    if isinstance(trading_hours, dict):
        ret = ret[((ret["time"] >= trading_hours['am_start_time'] * 1000) & (ret["time"] <= trading_hours['am_end_time'] * 1000))
                | ((ret["time"] >= trading_hours['pm_start_time'] * 1000) & (ret["time"] <= trading_hours['pm_end_time'] * 1000))
        ]
    else:
        # else time between [94000, 145700]
        ret = ret[(ret["time"] >= 94000000) & (ret["time"] <= 145700000)]
    return ret

def get_limit_flag(month, ticker_list):
    month_str = '.'.join([month[:4],month[4:6]]) + 'M'
    ddb_reader = DDB_connector(DDB_config)
    ticker_list_str = "`".join(ticker_list)
    query = f'select securityCode, date, any(iif(bidPriceList[0].isNull()||askPriceList[0].isNull(), 1, 0))$INT as limit_flag from loadTable("dfs://amd","newOrderBookSnapshot")' \
            f'where securityCode in `{ticker_list_str}, month(time)={month_str}, second(time)>=09:30:00, second(time)<14:57:00 group by securityCode, date(time) as date'
    df_limit_flag = ddb_reader.query_data(query)
    df_limit_flag['date'] = df_limit_flag['date'].apply(lambda  x: int(x.strftime("%Y%m%d")))
    df_limit_flag = df_limit_flag.rename(columns={'securityCode': 'ticker'})
    return df_limit_flag


if __name__ == "__main__":
    df_limit_flag = get_limit_flag('202505', ["600519.SH", "300750.SZ"])

    ddb_reader = DDB_connector(DDB_config)
    res = ddb_reader.query_data("license()")
    tickers = tuple(["600519.SH", "300750.SZ"])

    factor_tables = ['BaseFokFactor', 'SlopeOflFactor', 'GPFactor']
    factor_database = { "dfs://DDB_Factor_15s":factor_tables}
    test_month = 202401
    ret_name = "15s"

    data = [pd.DataFrame()]
    i = 0
    for database in factor_database:
        for table in factor_database[database]:
            # load factors
            factor = read_ddb_factor(database, table, test_month, tickers)
            # preprocess(log...)
            preprocess(factor)
            # merge factors from every table
            if i == 0:
                data = factor
            else:
                data = pd.merge(factor, data, on=['ticker', 'date', 'time'])
            i += 1

    ret_db_name = "dfs://DDB_Returns"
    ret_table_name = 'Returns'
    labels = read_ddb_return(ret_db_name,ret_table_name, test_month, tickers)
    labels = labels[['ticker', 'date', "time", f'ret_{ret_name}']]
    # merge factors and labels by ticker, date, time
    data = pd.merge(data, labels, on=['ticker', 'date', 'time'])
    data.rename(columns={'ret_' + ret_name: 'ret'}, inplace=True)
    print(len(data))



