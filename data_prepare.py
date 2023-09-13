import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
import os

import utils


def get_data_1min(month=202107, indus_from='sw1', indus_type=1, avg_price=10, std_type='zscore', label_name='60s', csv_path='data'):


    # use batch data
    data_hs = utils.cx_read_sql('select * from static_data_hs300_all where {}="{}" and avg_price > {} and test_month=202306'.format(indus_from, indus_type,
                                                                                      avg_price, ))
    data_zz = utils.cx_read_sql('select * from static_data_zz500_all where {}="{}" and avg_price > {} and test_month=202306'.format(indus_from, indus_type,
                                                                                      avg_price, ))
    tickers = tuple(data_hs['ticker']) + tuple(data_zz['ticker'])
    print(len(data_hs['ticker']))
    if indus_from == 'sw1':
        csv_path = 'data/sw1/'
        factor_path = csv_path + 'factor_{}_indus_{}.csv'.format(str(month), str(indus_type))
        if os.path.exists(factor_path):
            factor = pd.read_csv(factor_path, index_col=0)
        else:
            factor = utils.cx_read_sql('select * from factor_{} where ticker in {}'.format(month, tickers))

    if indus_from == 'wind1':
        csv_path = 'data/wind1/'
        factor_path = csv_path + 'factor_{}_indus_{}.csv'.format(str(month), str(indus_type))
        if os.path.exists(factor_path):
            factor = pd.read_csv(factor_path, index_col=0)
        else:
            factor = utils.cx_read_sql('select * from factor_{} where ticker in {}'.format(month, tickers))


    # fetch factors from sql
    # else:
    #     factor = utils.cx_read_sql(
    #         'select * from factor_{} where ticker in {} '.format(str(month), tickers))
    labels = utils.cx_read_sql(
        'select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format(label_name, str(month), tickers))

    if std_type == 'cross_section':
        pass
        # need to delete mkt factors

    # treat log factor
    log_factors = pd.read_csv('log_factor_list.csv', header=None, names=['log_factor'])['log_factor']
    def get_log_factor_df(df_factors):
        df_factors[df_factors > 0] = np.log(df_factors[df_factors > 0] + 1)
        df_factors[df_factors < 0] = -np.log(-df_factors[df_factors < 0] + 1)
        return df_factors
    for log_factor in log_factors:
        factor.loc[:, log_factor] = get_log_factor_df(factor[log_factor].values)

    new_data = pd.merge(factor, labels, on=['ticker', 'date', 'time'])
    new_data.rename(columns={'ret_'+label_name: 'mid_price'}, inplace=True)

    #all_data = new_data.dropna() # delete nan midprice
    # all_data.append(new_data)
    # all_data = pd.concat(all_data)
    # all_data.rename(columns={'ret_60s':'mid_price'}, inplace=True)
    # all_data = all_data.dropna() # delete nan midprice
    return new_data


def filter_ticker(data):
    new_data = []
    tickers = set(data[0]['ticker'].unique())
    for df in data:
        tickers.intersection(set(df['ticker'].unique()))

    for df in data:
        df = df[df['ticker'].isin(tickers)]
        new_data.append(df.reset_index(drop=True))
    return new_data, tickers

def split_data(data, phase='optimization'):
    if phase == 'optimization':
        # treat last training month-data
        # last_data = data[-2]
        # dates = sorted(last_data.date.unique())
        # split_num = int(0.5 * len(dates))
        # split_train = last_data[last_data['date'].isin(dates[:split_num])]
        # train_dfs = data[:-2]
        # train_dfs.append(split_train)
        # test_df = last_data[last_data['date'].isin(dates[split_num:])]

        # use more 1 month
        train_dfs = data[:-2]
        test_df = data[-1]
    else:
        train_dfs = data[:-1]
        test_df = data[-1]
    new_train_df = []
    for df in train_dfs:
        new_train_df.append(df.dropna())
    if phase != 'eval': # preserve NA sig
        test_df.dropna(inplace=True)

    return new_train_df, test_df

def standardizate(train_dfs, test_df, std_type='zscore'):
    dfs = train_dfs
    dfs.append(test_df)
    # to be fixed!!!
    if std_type == 'cross_section':
        def cross_std(df):
            new_data = []
            align_cols = ['ticker', 'date', 'time']
            avg = df.groupby(['date', 'time']).mean()
            std = df.groupby(['date', 'time']).std()
            for ticker in df.ticker.unique():
                data = df[df['ticker']==ticker]
                mid_price = data['mid_price'].values
                data_avg = pd.merge(data[align_cols], avg, on=['date', 'time'])
                data_std = pd.merge(data[align_cols], std, on=['date', 'time'])
                data_matrix = (data.drop(align_cols, axis=1).values - data_avg.drop(align_cols, axis=1).values) /  data_std.drop(align_cols, axis=1).values
                tmp_data = pd.DataFrame(data_matrix, columns=data.drop(align_cols, axis=1).columns)
                tmp_data['mid_price'] = mid_price
                tmp_data['ticker'] = ticker
                new_data.append(tmp_data.dropna())
            return pd.concat(new_data)

        train_df = pd.concat(dfs[:-1])
        train_df = cross_std(train_df)
        test_df = dfs[-1]
        test_df = cross_std(test_df)
        return train_df, test_df

    # time-series Z-Score
    elif std_type == 'zscore':
        del_cols = ['ticker', 'date', 'time',  'mid_price']
        new_data = []
        for i in range(1, len(dfs)):
            df = dfs[i]
            stat_data = dfs[i-1]
            ticker_data = []
            for ticker in df.ticker.unique():
                time = df.query('ticker==@ticker')['time']
                mid_price = df[df['ticker']==ticker]['mid_price']
                date = df.query('ticker==@ticker')['date']
                data = df[df['ticker']==ticker].drop(del_cols, axis=1)
                avg = stat_data[stat_data['ticker']==ticker].drop(del_cols, axis=1).mean()
                std = stat_data[stat_data['ticker']==ticker].drop(del_cols, axis=1).std()
                tmp_data = (data - avg) / std
                tmp_data['mid_price'] = mid_price
                tmp_data['ticker'] = ticker # keep ticker and mid price
                tmp_data['time'] = time
                tmp_data['date'] = date

                ticker_data.append(tmp_data)
            new_data.append(pd.concat(ticker_data))

        train_df = pd.concat(new_data[:-1])
        test_df = new_data[-1]
        return train_df, test_df # return last month
    # zscore with pre 3 month data
    elif std_type == 'zscore1':
        del_cols = ['ticker', 'date', 'time', 'mid_price']
        new_data = []
        for i in range(3, len(dfs)): # 3 + 3 + 1 = 7 month
            df = dfs[i]
            stat_data = pd.concat(dfs[i-3:i])
            ticker_data = []
            for ticker in df.ticker.unique():
                time = df.query('ticker==@ticker')['time']
                mid_price = df[df['ticker'] == ticker]['mid_price']
                date = df.query('ticker==@ticker')['date']
                data = df[df['ticker'] == ticker].drop(del_cols, axis=1)
                avg = stat_data[stat_data['ticker'] == ticker].drop(del_cols, axis=1).mean()
                std = stat_data[stat_data['ticker'] == ticker].drop(del_cols, axis=1).std()
                tmp_data = (data - avg) / std
                tmp_data['mid_price'] = mid_price
                tmp_data['ticker'] = ticker  # keep ticker and mid price
                tmp_data['time'] = time
                tmp_data['date'] = date

                ticker_data.append(tmp_data)
            new_data.append(pd.concat(ticker_data))

        train_df = pd.concat(new_data[:-1])
        test_df = new_data[-1]
        return train_df, test_df  # return last month

    # zscore with 3 month data
    elif std_type == 'zscore2':
        del_cols = ['ticker', 'date', 'time',  'mid_price']
        # compute mean & std in training set and testing set std
        train_df = pd.concat(dfs[:-1]) # 3 month
        test_data = dfs[-1]
        ticker_data = []
        for ticker in test_data.ticker.unique():
            time = test_data.query('ticker==@ticker')['time']
            date = test_data.query('ticker==@ticker')['date']
            mid_price = test_data[test_data['ticker'] == ticker]['mid_price']
            data = test_data[test_data['ticker'] == ticker].drop(del_cols, axis=1)
            avg = train_df[train_df['ticker'] == ticker].drop(del_cols, axis=1).mean()
            std = train_df[train_df['ticker'] == ticker].drop(del_cols, axis=1).std()
            tmp_data = (data - avg) / std
            tmp_data['mid_price'] = mid_price
            tmp_data['ticker'] = ticker  # keep ticker and mid price
            tmp_data['time'] = time
            tmp_data['date'] = date
            ticker_data.append(tmp_data)
        new_test_data = pd.concat(ticker_data)
        # training set std
        new_train_data = []
        for i in range(len(dfs) - 1):
            df = dfs[i]
            ticker_data = []
            for ticker in test_data.ticker.unique():
                time = df.query('ticker==@ticker')['time']
                date = df.query('ticker==@ticker')['date']
                mid_price = df[df['ticker']==ticker]['mid_price']
                data = df[df['ticker']==ticker].drop(del_cols, axis=1)
                avg = train_df[train_df['ticker']==ticker].drop(del_cols, axis=1).mean()
                std = train_df[train_df['ticker']==ticker].drop(del_cols, axis=1).std()
                tmp_data = (data - avg) / std
                tmp_data['mid_price'] = mid_price
                tmp_data['ticker'] = ticker # keep ticker and mid price
                tmp_data['time'] = time
                tmp_data['date'] = date
                ticker_data.append(tmp_data)
            new_train_data.append(pd.concat(ticker_data))
        new_train_data = pd.concat(new_train_data)

        train_df = new_train_data
        test_df = new_test_data
        return train_df, test_df
    else:
        # no standardization
        del_cols = ['date', 'time']
        return pd.concat(dfs[:-1]).drop(del_cols, axis=1),  dfs[-1].drop(del_cols, axis=1)

def make_label(df, alpha=5e-4):
    # 根据交易费率划分方向：涨、跌、平
    df['class_label'] = df['mid_price'].mask(df['mid_price'] > alpha, 0).mask(df['mid_price'] < -1 * alpha, 1) \
        .mask((-1 * alpha <= df['mid_price']) & (df['mid_price'] <= alpha), 2)
    return df

def transform_data(train_data, test_data, class_num=3, clip_pct=(5, 95), balance=0 ):
    # clip data values
    def clip_data(x):
        return np.clip(x, np.percentile(x, clip_pct[0]), np.percentile(x, clip_pct[1]))

    def clip_dataset(train_data, test_data, clip_test=True):
        not_clip_cols = ['mid_price', 'class_label', 'time', 'date']
        new_train = train_data.drop(not_clip_cols, axis=1)
        low = new_train.groupby('ticker').agg(lambda x: np.percentile(x, 5))
        high = new_train.groupby('ticker').agg(lambda x: np.percentile(x, 95))
        new_train = new_train.groupby('ticker').transform(lambda x: clip_data(x, ))
        new_train['ticker'] = train_data['ticker']
        new_train['mid_price'] = train_data['mid_price']
        new_train['class_label'] = train_data['class_label']
        new_train['time'] = train_data['time']
        new_train['date'] = train_data['date']

        if clip_test:
            low = low.reset_index()
            high = high.reset_index()
            new_test = []
            for ticker in test_data['ticker'].unique():
                data = test_data[test_data['ticker']==ticker]
                tmp_data = data.drop(['ticker','mid_price', 'class_label', 'time', 'date'], axis=1)
                clip_low = low[low['ticker']==ticker].drop(['ticker'], axis=1).values
                clip_high = high[high['ticker']==ticker].drop(['ticker'], axis=1).values
                tmp_data = tmp_data.clip(clip_low, clip_high, axis=1) # column clip
                tmp_data['ticker'] = ticker
                tmp_data['mid_price'] = data['mid_price']
                tmp_data['class_label'] = data['class_label']
                tmp_data['time'] = data['time']
                tmp_data['date'] = data['date']
                new_test.append(tmp_data)
            new_test = pd.concat(new_test)
        else:
            new_test = test_data

        return new_train, new_test

    train_data, test_data = clip_dataset(train_data, test_data)
    # change class num
    if class_num == 2:
        train_data = train_data[train_data['class_label']!=2]

        #balance data
        if balance == 1:
            up_num = len(train_data.query('class_label==0'))
            down_num = len(train_data.query('class_label==1'))
            sample_num = min(up_num, down_num)
            up_data = train_data.query('class_label==0').sample(n=sample_num)
            down_data = train_data.query('class_label==1').sample(n=sample_num)
            train_data = pd.concat([up_data, down_data], ignore_index=True)
            print('updata is {}, down data is {}, test data is {}'.format(up_num, down_num, len(test_data)))

        # balance label
        if balance == 2:
            up_num = len(train_data.query('class_label==0'))
            down_num = len(train_data.query('class_label==1'))
            up_data = train_data.query('class_label==0')
            re_updata = -1 * up_data.drop(['class_label'], axis=1)
            re_updata['class_label'] = 1
            down_data = train_data.query('class_label==1')
            re_downdata = -1 * down_data.drop(['class_label'], axis=1)
            re_downdata['class_label'] = 0
            train_data = pd.concat([up_data, down_data, re_updata, re_downdata], ignore_index=True)
            print('updata is {}, down data is {}, test data is {}'.format(up_num, down_num, len(test_data)))

    return train_data, test_data


def get_data(month=[], indus_from='sw1', indus_type=1, avg_price=10, label_name='ret_60s', std_type='zscore', alpha=5, class_num=3, phase='optimization', balance=0,lock=None):
    data = []
    lock.acquire()
    for i in range(len(month)):
        data.append(get_data_1min(month=month[i], indus_from=indus_from, indus_type=indus_type, avg_price=avg_price, std_type=std_type, label_name=label_name, ))
    lock.release()

    # # detect insertsection of data
    # data, tickers = filter_ticker(data)
    # if len(tickers) == 0 :
    #     return pd.DataFrame(), pd.DataFrame()

    train_dfs, test_df = split_data(data, phase=phase)
    train_data, test_data = standardizate(train_dfs, test_df, std_type=std_type)
    make_label(train_data, alpha=alpha)
    make_label(test_data, alpha=alpha)
    train_data, test_data = transform_data(train_data, test_data, class_num=class_num, balance=balance)

    if phase=='eval':
        return train_data.reset_index(drop=True), test_data.reset_index(drop=True)
    else:
        del_col = ['time', 'date']
        return train_data.reset_index(drop=True).drop(del_col, axis=1), test_data.reset_index(drop=True).drop(del_col, axis=1)

if __name__ == '__main__':
    pass
    # show label dist
    # alpha = 5e-4
    # # 根据交易费率划分方向：涨、跌、平
    # data = total_data
    # data['class_label'] = data['mid_price'].mask(data['mid_price'] > alpha, 0).mask(data['mid_price'] < -1 * alpha, 1) \
    #     .mask((-1 * alpha <= data['mid_price']) & (data['mid_price'] <= alpha), 2)
    # class_label_counts = data['class_label'].value_counts()
    # plt.bar(['up', 'down', 'stable'], [class_label_counts[0], class_label_counts[1], class_label_counts[2]])
    # plt.savefig('label_dis.png')
