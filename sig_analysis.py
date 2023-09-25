import numpy as np
import pandas as pd
import argparse
from joblib import Parallel, delayed
import sqlalchemy.types

import utils
from utils import create_pd_engine, create_index



def merge_signal(month, config):
    data_LR = utils.cx_read_sql('select * from signal_{} where {}<date and date<{}'.format(config.label_name, month*100, (month+1)*100))
    data_ML = utils.cx_read_sql('select * from signal_{}_ml where {}<date and date<{}'.format(config.label_name, month*100, (month+1)*100))
    tickers = data_ML['ticker'].unique()
    df_signals = []
    for ticker in tickers:
        signal_LR = data_LR.query('ticker==@ticker').copy()
        signal_LR['signal_{}'.format(config.label_name)].fillna(0, inplace=True)
        ticker_ML = data_ML.query('ticker==@ticker').copy()
        ticker_ML.rename(columns={'signal_{}'.format(config.label_name):'signal_{}_ml'.format(config.label_name)}, inplace=True)
        ticker_ML['signal_{}_ml'.format(config.label_name)].fillna(0, inplace=True)

        ret = utils.cx_read_sql('select ticker, date, time, ret_{} from ret_{} where ticker="{}"'.format(config.label_name, str(month), ticker))
        assert len(signal_LR) == len(ticker_ML)

        df_signal = pd.merge(ticker_ML, signal_LR, on=['ticker', 'date', 'time'])
        df_signal = pd.merge(df_signal, ret, on=['ticker', 'date','time'])
        signal_ML = df_signal['signal_{}_ml'.format(config.label_name)].values.astype(np.int32)

        signal_LR = df_signal['signal_{}'.format(config.label_name)].values.astype(np.int32)

        # sig0: and
        new_signal = np.zeros(len(signal_ML))
        selected_idx = signal_LR==signal_ML
        new_signal[selected_idx] = signal_ML[selected_idx]
        no_zero_rate = np.sum(new_signal!=0)/len(new_signal)
        # sig1: or + LR
        new_signal1 = signal_LR.copy()
        selected_idx = signal_LR*signal_ML < 0 # -1
        new_signal1[selected_idx] = 0
        # sig2: or + ML
        new_signal2 = signal_ML.copy()
        selected_idx = signal_LR * signal_ML < 0  # -1
        new_signal2[selected_idx] = 0

        # save merged signal
        df_signal = ticker_ML.copy()
        df_signal['merged_signal_0'] = new_signal
        df_signal['merged_signal_1'] = new_signal1
        df_signal['merged_signal_2'] = new_signal2
        df_signals.append(df_signal)

    return pd.concat(df_signals)


def main(config):
    months = [202304, 202305, 202306]
    signal = Parallel(config.n_jobs)([delayed(merge_signal)(month, config) for month in months])
    #signal = merge_signal(202304)
    signal = pd.concat(signal)
    signal.to_csv('merged_signal.csv')
    # write to sql
    engine = create_pd_engine('strategy')
    data_name = 'merge_signal_{}'.format(config.label_name)
    signal.to_sql(data_name, con=engine, index=False, if_exists='replace', chunksize=10000,
                  dtype={'ticker': sqlalchemy.types.VARCHAR(length=10),
                         'date': sqlalchemy.types.BIGINT,
                         'time': sqlalchemy.types.BIGINT,
                         })
    create_index('strategy', data_name, ['ticker', 'date', 'time'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='concat hs300 signal')
    parser.add_argument('--n_jobs', type=int, default=3, help="parallel num")
    parser.add_argument('--label_name', type=str, default='60s', help="future return")
    config = parser.parse_args()
    main(config)

