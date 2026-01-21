import dolphindb as ddb
import pandas as pd
import numpy as np
import time
import dolphindb.settings as keys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime



DDB_config = { "server": "10.95.145.91",
               "port": 8993,
               "userName": "quantStrat",
               "userKey": "eqalgo_2024"
            }

class DDB_connector():
    def __init__(self, DDB_config):
        self.ddb_session = ddb.session(
            protocol=keys.PROTOCOL_DDB, 
            compress=True,
            keepAliveTime=12000
        )
        # 创建连接；开启重连
        self.ddb_session.connect(
            host=DDB_config["server"], 
            port=DDB_config["port"], 
            userid=DDB_config["userName"],
            password=DDB_config["userKey"],
            reconnect=True
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
    # filter by select_period dict
    if isinstance(trading_hours, dict):
        am_start_time = str(trading_hours['am_start_time']).zfill(6)
        am_start_time = datetime.strptime(am_start_time, "%H%M%S").strftime("%H:%M:%S")
        am_end_time = str(trading_hours['am_end_time']).zfill(6)
        am_end_time = datetime.strptime(am_end_time, "%H%M%S").strftime("%H:%M:%S")

        pm_start_time = str(trading_hours['pm_start_time']).zfill(6)
        pm_start_time = datetime.strptime(pm_start_time, "%H%M%S").strftime("%H:%M:%S")
        pm_end_time = str(trading_hours['pm_end_time']).zfill(6)
        pm_end_time = datetime.strptime(pm_end_time, "%H%M%S").strftime("%H:%M:%S")

    else:
        # default time period
        am_start_time, am_end_time = "09:40:00", "11:30:00"
        pm_start_time, pm_end_time = "13:00:00", "14:57:00"

    # select wide table
    start_time = time.time()
    #print(f"[{table_name}][{test_month}][{len(tickers)}] Connecting DDB")
    ddb_reader = DDB_connector(DDB_config)
    scripts = "factorTable = loadTable(\"{}\", \"{}\")".format(data_base, table_name)
    ddb_reader.ddb_session.run(scripts, priority=9)
    scripts =  f"retTable = select * from factorTable where month(time)={test_month}, securityCode in {tickers}, {am_start_time}<=second(time)<={am_end_time} or {pm_start_time}<=second(time)<={pm_end_time}"
    ddb_reader.ddb_session.run(scripts, priority=9)
    scripts = "select factorValue from retTable pivot by time, securityCode, factorName"
    factor = ddb_reader.ddb_session.run(scripts, priority=9)
    ddb_reader.close()
    #print(f"[{table_name}][{test_month}][{len(tickers)}] load data time: {time.time() - start_time}")

    # transfer to ticker date time format like sql
    start_time = time.time()
    factor.rename(columns={"securityCode": "ticker"}, inplace=True)
    factor.insert(0, 'date', factor["time"].dt.strftime('%Y%m%d').astype(int))
    factor["time"] = (factor["time"].dt.hour * 10000000 + factor["time"].dt.minute * 100000 +
                      factor["time"].dt.second * 1000 + factor["time"].dt.microsecond // 1000)
    #print(f"[{table_name}][{test_month}][{len(tickers)}] filter data time: {time.time() - start_time}")

    #print(f'load date time: {time.time() - start_time}')
    return factor

# def read_ddb_factor_by_ticker(data_base, table_name, test_month, tickers, trading_hours=None, n_threads=8):
#     with ThreadPoolExecutor(max_workers=min(len(tickers), n_threads)) as executor:
#         results = list(
#             executor.map(
#                 lambda ticker: read_ddb_factor(data_base, table_name, test_month, [ticker], trading_hours), tickers
#             )
#         )
#     factors = pd.concat([r for r in results])
#     return factors



def read_ddb_factor_by_ticker(data_base, table_name, test_month, tickers, trading_hours=None, 
                            batch_size=4, n_threads=8):
    """
    批量读取因子数据，每批最多batch_size个ticker
    
    参数:
        data_base: 数据库名称
        table_name: 表名称
        test_month: 测试月份
        tickers: ticker列表
        trading_hours: 交易时段配置
        batch_size: 每批处理的ticker数量，默认4
        n_threads: 线程数，默认8
    """
    #print(f"[{table_name}][{test_month}][{len(tickers)}] Connecting DDB")
    start_time = time.time()
    # 将ticker列表分批
    ticker_batches = []
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        ticker_batches.append(batch)
    
    #print(f"总共{len(tickers)}个ticker，分为{len(ticker_batches)}批，每批最多{batch_size}个")
    
    total_start_time = time.time()
    
    # 使用线程池并行处理各批次
    with ThreadPoolExecutor(max_workers=min(len(ticker_batches), n_threads)) as executor:
        # 提交所有批次任务
        future_to_batch = {}
        for batch_idx, batch in enumerate(ticker_batches):
            future = executor.submit(
                read_ddb_factor, 
                data_base, table_name, test_month, batch, trading_hours
            )
            future_to_batch[future] = (batch_idx, batch)
        
        # 收集结果
        results = []
        for future in as_completed(future_to_batch):
            batch_idx, batch = future_to_batch[future]
            try:
                batch_result = future.result()
                if not batch_result.empty:
                    results.append(batch_result)
                    #print(f"批次{batch_idx+1}完成，包含{len(batch)}个ticker，获取{len(batch_result)}行数据")
                else:
                    pass
                    #print(f"批次{batch_idx+1}完成，但未获取到数据")
            except Exception as e:
                print(f"批次{batch_idx+1}处理失败: {e}")
    
    # 合并所有批次结果
    if results:
        factors = pd.concat(results, ignore_index=True)
        #print(f"[{table_name}][{test_month}][{len(tickers)}] 所有批次处理完成，总耗时: {time.time() - total_start_time:.2f}s, 合并后总数据量: {len(factors)}行")
        return factors
    else:
        print("未获取到任何数据")
        return pd.DataFrame()



def read_ddb_factor_low_price(data_base, table_name, test_month, tickers, trading_hours=None):
    test_month = str(test_month)
    test_month = test_month[0:4] + '.' + test_month[4:] + 'M'

    # select wide table
    start_time = time.time()
    #print(f"[{table_name}][{test_month}][{len(tickers)}] Connecting DDB")
    ddb_reader = DDB_connector(DDB_config)
    scripts = "factorTable = loadTable(\"{}\", \"{}\")".format(data_base, table_name)
    ddb_reader.ddb_session.run(scripts, priority=9)
    scripts =  "retTable = select * from factorTable where month(time)={} and securityCode in {}".format(test_month, tickers)
    ddb_reader.ddb_session.run(scripts, priority=9)
    scripts = "select factorValue from retTable pivot by time, securityCode, factorName"
    factor = ddb_reader.ddb_session.run(scripts, priority=9)
    ddb_reader.close()
    #print(f"[{table_name}][{test_month}][{len(tickers)}] load data time: {time.time() - start_time}")

    # transfer to ticker date time format like sql
    start_time = time.time()
    factor.rename(columns={"securityCode": "ticker"}, inplace=True)
    factor.insert(0, 'date', factor["time"].dt.strftime('%Y%m%d').astype(int))
    factor["time"] = (factor["time"].dt.hour * 10000000 + factor["time"].dt.minute * 100000 +
                      factor["time"].dt.second * 1000 + factor["time"].dt.microsecond // 1000)
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
    ddb_reader.ddb_session.run(scripts, priority=9)
    scripts =  "select * from retTable where month(time)={} and securityCode in {}".format(test_month, tickers)
    ret = ddb_reader.ddb_session.run(scripts, priority=9)
    ddb_reader.close()

    # transfer to ticker date time format like sql
    ret.rename(columns={"securityCode": "ticker"}, inplace=True)
    ret.insert(0, 'date', ret["time"].dt.strftime('%Y%m%d').astype(int))
    ret["time"] = (ret["time"].dt.hour * 10000000 + ret["time"].dt.minute * 100000 +
                   ret["time"].dt.second * 1000 + ret["time"].dt.microsecond // 1000)

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

#
# if __name__ == "__main__":
#     df_limit_flag = get_limit_flag('202505', ["600519.SH", "300750.SZ"])
#
#     ddb_reader = DDB_connector(DDB_config)
#     res = ddb_reader.query_data("license()")
#     tickers = tuple(["600519.SH", "300750.SZ"])
#
#     factor_tables = ['BaseFokFactor', 'SlopeOflFactor', 'GPFactor']
#     factor_database = { "dfs://DDB_Factor_15s":factor_tables}
#     test_month = 202401
#     ret_name = "15s"
#
#     data = [pd.DataFrame()]
#     i = 0
#     for database in factor_database:
#         for table in factor_database[database]:
#             # load factors
#             factor = read_ddb_factor(database, table, test_month, tickers)
#             # preprocess(log...)
#             preprocess(factor)
#             # merge factors from every table
#             if i == 0:
#                 data = factor
#             else:
#                 data = pd.merge(factor, data, on=['ticker', 'date', 'time'])
#             i += 1
#
#     ret_db_name = "dfs://DDB_Returns"
#     ret_table_name = 'Returns'
#     labels = read_ddb_return(ret_db_name,ret_table_name, test_month, tickers)
#     labels = labels[['ticker', 'date', "time", f'ret_{ret_name}']]
#     # merge factors and labels by ticker, date, time
#     data = pd.merge(data, labels, on=['ticker', 'date', 'time'])
#     data.rename(columns={'ret_' + ret_name: 'ret'}, inplace=True)
#     print(len(data))



