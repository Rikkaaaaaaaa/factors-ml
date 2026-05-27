import dolphindb as ddb
import numpy as np
import pandas as pd

# config = {
#     "ddb_host": "10.95.145.91",
#     "ddb_port": 8994,
#     "ddb_username": "quantStrat",
#     "ddb_password": "eqalgo_2024"
# }
class Config():
    def __init__(self):
        self.ddb_host = "10.95.145.91"
        self.ddb_port = 8994
        self.ddb_username = "quantStrat"
        self.ddb_password = "eqalgo_2024"

config = Config()

def read_table(query):
    s = ddb.session()
    s.connect(config.ddb_host, config.ddb_port, config.ddb_username, config.ddb_password)
    df = s.run(query)
    s.close()
    return df


def get_tick_data(date, ticker):
    tick_data = read_table(f'select date, time, price, volume, turnover, accVolume, accTurnover, askPrice, bidPrice from loadTable("dfs://hdb", "tick") where date={date}, ticker=`{ticker}')
    tick_data['date'] = tick_data['date'].apply(lambda x: int(x.strftime('%Y%m%d')))
    tick_data['time'] = tick_data['time'].apply(lambda x: int(x.second * 1000 + x.minute * 100000 + x.hour * 10000000 + x.microsecond/1000))
    tick_data = tick_data.drop_duplicates('time', keep='last')
    tick_data = tick_data[(tick_data['time']<=113000000)|(tick_data['time']>=130000000)]
    # cast to int price
    tick_data['askPrice2'] = tick_data['askPrice'].apply(lambda x: np.nan_to_num(x[1], 0) * 10000 + 0.1).astype(int)
    tick_data['askPrice1'] = tick_data['askPrice'].apply(lambda x: np.nan_to_num(x[0], 0) * 10000 + 0.1).astype(int)
    tick_data['bidPrice1'] = tick_data['bidPrice'].apply(lambda x: np.nan_to_num(x[0], 0) * 10000 + 0.1).astype(int)
    tick_data['bidPrice2'] = tick_data['bidPrice'].apply(lambda x: np.nan_to_num(x[1], 0) * 10000 + 0.1).astype(int)
    tick_data['price'] = (tick_data['price'] * 10000 + 0.1).astype(int)
    return tick_data


def get_tick_data_hk(date, ticker):
    query = f'select * from loadTable("dfs://HKmd","quotation_lv1") where iTrdDate={date},strCode=`{ticker[:5]}'
    temp_data = read_table(query)
    tick_data = temp_data[['iTradingDay', 'iTime', 'strCode','lVolume','fTurnover', 'fLast','fPreClose', 'fOpen','fTdClose','fHigh','fLow','fAskPrice','iAskVol',
                           'fBidPrice','iBidVol']]
    tick_data = tick_data.rename(columns={'iTradingDay': 'date', 'iTime':'time', 'lVolume': 'accVolume', 'fTurnover':'accTurnover',
                                          'fLast': 'price', 'fPreClose':'pre_close', 'fOpen': 'open','fTdClose': 'close', 'fHigh': 'high', 'fLow': 'low',
                                           'fAskPrice': 'ask_price', 'iAskVol':'ask_volume', 'fBidPrice': 'bid_price',
                                           'iBidVol': 'bid_volume'})
    tick_data['datetime'] = pd.to_datetime(tick_data['date'].astype('str') + ' ' + tick_data['time'].dt.strftime('%H:%M:%S.%f'))
    tick_data.set_index('datetime', inplace=True)
    resampled = tick_data.resample('3S', closed='right', label='right').last()
    resampled = resampled.sort_index()
    resampled.reset_index(inplace=True)
    resampled[resampled.columns[4:]] = resampled[resampled.columns[4:]].fillna(method='ffill')
    resampled = resampled[~((resampled['datetime'].dt.time > pd.to_datetime('12:00:00').time()) &
                          (resampled['datetime'].dt.time < pd.to_datetime('13:00:00').time()))]
    resampled['date'] = resampled['datetime'].apply(lambda x: int(x.strftime('%Y%m%d')))
    resampled['time'] = resampled['datetime'].apply(
        lambda x: int(x.second * 1000 + x.minute * 100000 + x.hour * 10000000 + x.microsecond / 1000))

    tick_data['date'] = tick_data['date'].apply(lambda x: int(x.strftime('%Y%m%d')))
    tick_data['time'] = tick_data['time'].apply(lambda x: int(x.second * 1000 + x.minute * 100000 + x.hour * 10000000 + x.microsecond/1000))
    return tick_data, resampled


def get_adv_hk(date ,ticker_list):
    ticker_list_str = '`' + '`'.join(ticker_list)
    query = f'select last(lVolume) as ADV from loadTable("dfs://HKmd", "quotation_lv1") where iTrdDate={date}, in(strCode, {ticker_list_str}) group by StrCode'
    quant_params_hk = read_table(query)
    quant_params_hk = quant_params_hk.rename(columns={'StrCode': 'ticker'})
    return quant_params_hk


def get_vwap_curve_hk(date, ticker):
    if ticker.endswith(".HK"):
        ticker = ticker.split(".")[0]
    query = f'hk_utils::loadVolumeCurve({date}, [`{ticker}])'
    s = ddb.session()
    s.connect(config.ddb_host, config.ddb_port, config.ddb_username, config.ddb_password)
    s.run("use hk_utils")
    data = s.run(query)
    data['time'] = data['time'].apply(
        lambda x: int(x.second * 1000 + x.minute * 100000 + x.hour * 10000000 + x.microsecond / 1000))
    data = data.rename(columns={ticker[:5]: 'pred20'})
    return data


def time_format_convert(time_series):
    seconds = time_series.dt.second * 1000
    minutes = time_series.dt.minute * 100000
    hours = time_series.dt.hour * 10000000
    milliseconds = time_series.dt.microsecond / 1000
    return (seconds + minutes + hours + milliseconds).astype(int)


def get_vwap_curve_ashare(date, ticker):
    s = ddb.session()
    s.connect(config.ddb_host, config.ddb_port, config.ddb_username, config.ddb_password)
    date_query = f'exec distinct date from loadTable("dfs://algo_params_new","volumePredAshare") where date<{date}, ticker="{ticker}" order by date desc limit 1'
    last_date = s.run(date_query)
    if len(last_date) == 0:
        print(f'{ticker} no volume curve before {date}')
        date_query = f'exec distinct date from loadTable("dfs://algo_params_new","volumePredAshare") where date<{date}, ticker="000300.SH" order by date desc limit 1'
        last_date = s.run(date_query)

    last_date_str = last_date[0].astype(str).replace('-', '.')
    volume_pred_query = f'select time, ticker, pred20 from loadTable("dfs://algo_params_new","volumePredAshare") where date={last_date_str}, ticker="{ticker}"'
    volume_pred = s.run(volume_pred_query)

    if len(volume_pred) == 0:
        volume_pred_query = f'select time, ticker, pred20 from loadTable("dfs://algo_params_new","volumePredAshare") where date={last_date_str}, ticker="000300.SH"'
        volume_pred = s.run(volume_pred_query)
    s.close()
    volume_pred['time'] = time_format_convert(volume_pred['time'])
    return volume_pred


def get_quant_params(date, ticker_list):
    ticker_list_str = "`".join(ticker_list)
    query = f'select * from loadTable("dfs://quantParameters","quantParameters") where date={date}, ticker in `{ticker_list_str}'
    quant_params = read_table(query)
    return quant_params


def get_adv_ashare(date, ticker_list):
    ticker_list_str = "`".join(ticker_list)
    query = f'select sum(volume) as ADV from loadTable("dfs://hdb","tick") where date={date}, ticker in `{ticker_list_str} group by ticker'
    quant_params = read_table(query)
    return quant_params


def get_period_mkt_volume(date, ticker_list, start_time, end_time):
    ticker_list_str = "`".join(ticker_list)
    query = f'select sum(volume) as ADV from loadTable("dfs://hdb","tick") where date={date}, ticker in `{ticker_list_str}, time>={start_time}, time<={end_time} group by ticker'
    quant_params = read_table(query)
    return quant_params


def get_limit_flag(date, ticker_list):
    ticker_list_str = "`".join(ticker_list)
    query = f'select ticker, any(iif(bidPrice[0] == 0 OR askPrice[0] == 0, 1, 0))$INT as limit_flag from loadTable("dfs://hdb","tick")' \
            f'where ticker in `{ticker_list_str}, date={date}, second(time)>=09:30:00, second(time)<14:57:00 group by ticker'
    df_limit_flag = read_table(query)
    # df_limit_flag = df_limit_flag.rename(columns={'securityCode': 'ticker'})
    return df_limit_flag


def get_date_list(start_date, end_date):
    query = f'select distinct(date) as date from loadTable("dfs://instrument","instrument") where date>={start_date}, date<={end_date} order by date'
    date_list = read_table(query)['date'].tolist()
    date_list = [x.strftime("%Y%m%d") for x in date_list]
    return date_list


def get_adv(date, ticker, table_name):
    if ticker.endswith(".HK"):
        ticker = ticker.split(".")[0]
    date = '.'.join([date[:4], date[4:6], date[6:8]])
    query = f'hk_utils::calcADV({date}, `{ticker}, "{table_name}")'
    s = ddb.session()
    s.connect(config.ddb_host, config.ddb_port, config.ddb_username, config.ddb_password)
    s.run("use hk_utils")
    result = s.run(query)
    s.close()
    return result


def get_mkt_volume(date, ticker, table_name):
    date = date[:4] + "." + date[4:6] + "." + date[6:8]
    if ticker.endswith(".HK"):
        ticker = ticker.split(".")[0]
    query = f'exec last(lVolume) - first(lVolume) from loadTable("dfs://HKmd","{table_name}") where iTrdDate={date}, strCode=`{ticker}, iTime>=09:30:00, iTime<=16:00:00'
    s = ddb.session()
    s.connect(config.ddb_host, config.ddb_port, config.ddb_username, config.ddb_password)
    s.run("use hk_utils")
    result = s.run(query)
    s.close()
    return result


def get_adv_ratio_to_hist(date, ticker):
    mkt_volume = get_mkt_volume(date, ticker, 'quotation_lv1')
    hist_adv = get_adv(date, ticker, 'quotation_lv1')
    return mkt_volume / hist_adv


def get_cas_hk(date, ticker):
    data = read_table(f'select * from loadTable("dfs://HKmd_extra","cas") where date={date},ticker=`{ticker[:5]}')
    data['date'] = data['date'].apply(lambda x: int(x.strftime('%Y%m%d')))
    data['time'] = data['time'].apply(
        lambda x: int(x.second * 1000 + x.minute * 100000 + x.hour * 10000000 + x.microsecond / 1000))
    return data


def get_returns(date, ticker):
    data = read_table(f'select * from loadTable("dfs://DDB_Returns","Returns") where date(time)={date}, securityCode=`{ticker}')
    data['date'] = data['time'].dt.strftime('%Y%m%d')
    data['time'] = time_format_convert(data['time'])
    return data


def get_ret_data_by_month(ticker_list, ret_table_name, month):
    ticker_list_str = '`' + '`'.join(ticker_list)
    month_str = str(month)[:4] + '.' + str(month)[4:] + 'M'
    df = read_table(f'select * from loadTable("dfs://DDB_Returns", "{ret_table_name}") where month(time)={month_str}, securityCode in {ticker_list_str}')
    df['date'] = df['time'].apply(lambda x: int(x.strftime('%Y%m%d')))
    df['time'] = df['time'].apply(lambda x: x.second * 1000 + x.minute * 100000 + x.hour * 10000000)
    df = df.rename(columns={'securityCode': 'ticker'})
    return df[['ticker', 'date', 'time', 'ret_15s', 'ret_60s','ret_120s','ret_300s']]


def get_single_stock_signal(date, ticker):
    query = f"""
    select * from loadTable("dfs://smart_order_position_signal", "signals_bt") where date(time)={date}, securityCode=`{ticker}
    """
    data = read_table(query)
    data['date'] = data['time'].dt.strftime('%Y%m%d')
    data['time'] = time_format_convert(data['time'])
    return data


if __name__ == '__main__':
    # data = get_vwap_curve_ashare('2025.03.04', '002896.SZ')
    data = get_limit_flag('2025.09.23', ['688373.SH', '300750.SZ'])
    print(data)