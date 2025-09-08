import os
import numpy as np
import pandas as pd
from multiprocessing import Pool
import sys
sys.path.append('../')
sys.path.append('./')

from utils.ddb import read_ddb_return
from utils.publish import push_single_signal_sql, ensure_table_name


def read_signal_from_csv(signal_root_path):
    signal = []
    for signal_path in sorted(os.listdir(signal_root_path)):
        signal.append(pd.read_csv((os.path.join(signal_root_path, signal_path))))
    return pd.concat(signal)


def read_train_signal_from_csv(signal_root_path):
    train_signal = []
    for train_signal_path in sorted(os.listdir(signal_root_path)):
        train_signal.append(pd.read_csv((os.path.join(signal_root_path, train_signal_path))))
    return pd.concat(train_signal)


def merge_signal_by_pct(expr_name, ret_name, month):
    expr_path = f"../experiments/{expr_name}"
    signal_path = f"{expr_path}/{month}/signal"
    signal = read_signal_from_csv(signal_path) # keep data when return=0
    train_proba = read_train_signal_from_csv(f"{expr_path}/{month}/train_signal")
    train_proba = train_proba.sort_values(by=['ticker'])

    pct_num = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95]
    for pct in pct_num:
        threshold = train_proba.groupby('ticker')['proba'].apply(lambda x: np.percentile(x, pct)).reset_index().rename(columns={'proba': f'pct_{pct}'})
        signal = signal.merge(threshold, on=['ticker'])

    if ret_name in ['60s', '120s', '300s']:
        new_signal = np.zeros(len(signal['signal']))
        proba = signal['proba'].values
        # up signal
        new_signal[proba > signal['pct_80'].values] = 0.8
        new_signal[proba > signal['pct_90'].values] = 1.1
        new_signal[proba > signal['pct_95'].values] = 1.2
        # down signal
        new_signal[proba < signal['pct_20'].values] = -0.8
        new_signal[proba < signal['pct_10'].values] = -1.1
        new_signal[proba < signal['pct_5'].values] = -1.2
        signal['new_signal'] = new_signal

    if ret_name == '15s':
        new_signal = np.zeros(len(signal['signal']))
        proba = signal['proba'].values
        # up signal
        new_signal = proba - signal['pct_50'].values
        signal['new_signal'] = new_signal
    check_res = check_dist(signal, "new_signal")

    return signal[["ticker", "date", "time", "new_signal"]]

def merge_signal_by_pct2(expr_name, ret_name, month):
    expr_path = f"../experiments/{expr_name}"
    signal_path = f"{expr_path}/{month}/signal"
    signal = read_signal_from_csv(signal_path) # keep data when return=0
    train_proba = read_train_signal_from_csv(f"{expr_path}/{month}/train_signal")
    train_proba = train_proba.sort_values(by=['ticker'])

    pct_num = [1, 3,5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 97, 99]
    for pct in pct_num:
        threshold = train_proba.groupby('ticker')['proba'].apply(lambda x: np.percentile(x, pct)).reset_index().rename(columns={'proba': f'pct_{pct}'})
        signal = signal.merge(threshold, on=['ticker'])

    if ret_name in ['60s', '120s', '300s']:
        new_signal = np.zeros(len(signal['signal']))
        proba = signal['proba'].values
        # up signal
        new_signal[proba > signal['pct_80'].values] = 0.8
        new_signal[proba > signal['pct_90'].values] = 1.1
        new_signal[proba > signal['pct_95'].values] = 1.2
        new_signal[proba > signal['pct_97'].values] = 1.3
        new_signal[proba > signal['pct_99'].values] = 1.4
        # down signal
        new_signal[proba < signal['pct_20'].values] = -0.8
        new_signal[proba < signal['pct_10'].values] = -1.1
        new_signal[proba < signal['pct_5'].values] = -1.2
        new_signal[proba < signal['pct_3'].values] = -1.3
        new_signal[proba < signal['pct_1'].values] = -1.4
        signal['new_signal'] = new_signal

    if ret_name == '15s':
        new_signal = np.zeros(len(signal['signal']))
        proba = signal['proba'].values
        # up signal
        new_signal = proba - signal['pct_50'].values
        signal['new_signal'] = new_signal
    check_res = check_dist(signal, "new_signal")

    return signal[["ticker", "date", "time", "new_signal"]]

def read_signal_and_adjust_main_signal_enhance(expr_name, ret_name, month):
    expr_path = f"../experiments/{expr_name}"
    signal_path = f"{expr_path}/{month}/signal"
    signal = read_signal_from_csv(signal_path)  # keep data when return=0
    train_proba = read_train_signal_from_csv(f"{expr_path}/{month}/train_signal")
    train_proba = train_proba.sort_values(by=['ticker'])

    pct_num = [3, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 97]
    for pct in pct_num:
        threshold = train_proba.groupby('ticker')['proba'].apply(lambda x: np.percentile(x, pct)).reset_index().rename(columns={'proba': f'pct_{pct}'})
        signal = signal.merge(threshold, on=['ticker'])

    if ret_name in ['60s', '120s', '300s']:
        new_signal = np.zeros(len(signal['signal']))
        proba = signal['proba'].values
        # up signal
        new_signal[proba > signal['pct_80'].values] = 1
        new_signal[proba > signal['pct_90'].values] = 1.05
        new_signal[proba > signal['pct_95'].values] =1.1
        new_signal[proba > signal['pct_97'].values] =1.2
        # down signal
        new_signal[proba < signal['pct_20'].values] = -1
        new_signal[proba < signal['pct_10'].values] = -1.05
        new_signal[proba < signal['pct_5'].values] = -1.1
        new_signal[proba < signal['pct_3'].values] = -1.2
        signal['new_signal'] = new_signal

    if ret_name == '15s':
        new_signal = np.zeros(len(signal['signal']))
        proba = signal['proba'].values
        # up signal
        new_signal = proba - 0.5
        signal['new_signal'] = new_signal
    check_res = check_dist(signal, "new_signal")

    return signal[["ticker", "date", "time", "new_signal"]]


def merge_bond_signal(expr_name, ret_name, month):
    expr_path = f"../experiments/{expr_name}"
    signal_path = f"{expr_path}/{month}/signal"
    signal = read_signal_from_csv(signal_path) # keep data when return=0
    train_proba = read_train_signal_from_csv(f"{expr_path}/{month}/train_signal")
    train_proba = train_proba.sort_values(by=['ticker'])

    pct_num = [1,3, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 97,99]
    for pct in pct_num:
        threshold = train_proba.groupby('ticker')['proba'].apply(lambda x: np.percentile(x, pct)).reset_index().rename(columns={'proba': f'pct_{pct}'})
        signal = signal.merge(threshold, on=['ticker'])

    if ret_name in ['60s', '120s', '300s']:
        new_signal = np.zeros(len(signal['signal']))
        proba = signal['proba'].values
        # up signal
        new_signal[proba > signal['pct_80'].values] = 0.9
        new_signal[proba > signal['pct_90'].values] = 1.05
        new_signal[proba > signal['pct_95'].values] =1.1
        new_signal[proba > signal['pct_97'].values] =1.2
        new_signal[proba > signal['pct_99'].values] = 1.3
        # down signal
        new_signal[proba < signal['pct_20'].values] = -0.9
        new_signal[proba < signal['pct_10'].values] = -1.05
        new_signal[proba < signal['pct_5'].values] = -1.1
        new_signal[proba < signal['pct_3'].values] = -1.2
        new_signal[proba < signal['pct_1'].values] = -1.3
        signal['new_signal'] = new_signal

    if ret_name == '15s':
        new_signal = np.zeros(len(signal['signal']))
        proba = signal['proba'].values
        # up signal
        new_signal = proba - signal['pct_50'].values
        signal['new_signal'] = new_signal

    return signal[["ticker", "date", "time", "new_signal"]]

def ensemble_all_new_6m(months, trading_hours=None):
    try:
        # table name
        suffix = 'all_new_pct2'
        pool_name = 'hs300'
        price_level = 'highprice'
        model_type = 'lgbm'
        database = 'strategy'
        table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{suffix}"
        ensure_table_name(database, table_name)

        for month in months:
            # read signal and train proba
            expr_name_15s = 'ddb_null_factor_no_re_all_new_6m_hs300_highprice_lgbm_15s'
            expr_name_60s = 'ddb_null_factor_no_re_all_new_6m_hs300_highprice_lgbm_60s'
            expr_name_120s = 'ddb_null_factor_no_re_all_new_6m_hs300_highprice_lgbm_120s'
            expr_name_300s = 'ddb_null_factor_no_re_all_new_6m_hs300_highprice_lgbm_300s'
            # expr_name_mix_60s = 'mix2_1_1_pct20_hs300_highprice_lgbm_60s'
            # expr_name_mix_120s = 'mix3_1_1_1_pct20_hs300_highprice_lgbm_120s'
            # expr_name_mix_300s = 'mix4_1_1_1_1_pct20_hs300_highprice_lgbm_300s'

            signal_15s = merge_signal_by_pct2(expr_name_15s, '15s', month).rename(columns={'new_signal':'new_signal_15s'})
            signal_60s = merge_signal_by_pct2(expr_name_60s, '60s', month).rename(columns={'new_signal':'new_signal_60s'})
            signal_120s = merge_signal_by_pct2(expr_name_120s, '120s',month).rename(columns={'new_signal':'new_signal_120s'})
            signal_300s = merge_signal_by_pct2(expr_name_300s, '300s', month).rename(columns={'new_signal':'new_signal_300s'})

            merge_keys = ['ticker', 'date', 'time']
            merge_signal = signal_15s.merge(signal_60s, on=merge_keys).merge(signal_120s, on=merge_keys).merge(signal_300s, on=merge_keys)
            merge_signal['merge_signal'] = merge_signal['new_signal_15s'] * 2 + merge_signal['new_signal_60s']*2 + merge_signal['new_signal_120s']*2 + merge_signal['new_signal_300s']*2

            if isinstance(trading_hours, dict):
                if trading_hours['start_time'] <= trading_hours['end_time']:
                    print(f"Trading hours:  [{trading_hours['start_time']}, {trading_hours['end_time']}]")
                start_time = trading_hours['start_time']
                end_time = trading_hours['end_time']
                merge_signal = merge_signal.query("time>= @start_time and time <= @end_time")
            print(f"merge data size is {len(merge_signal)}")

            # filter by upload month
            merge_signal = merge_signal[(merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
            print(f"Uploading month: {month}")
            push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)

    except Exception as e:
        print(e)

def ensemble_all_new_6m_enhance(months, trading_hours=None):

    try:
        # table name
        suffix = 'all_new_pct_enhance'
        pool_name = 'hs300'
        price_level = 'highprice'
        model_type = 'lgbm'
        database = 'strategy'
        table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{suffix}"
        ensure_table_name(database, table_name)

        for month in months:
            # read signal and train proba
            expr_name_15s = 'ddb_null_factor_no_re_all_new_6m_hs300_highprice_lgbm_15s'
            expr_name_60s = 'ddb_null_factor_no_re_all_new_6m_hs300_highprice_lgbm_60s'
            expr_name_120s = 'ddb_null_factor_no_re_all_new_6m_hs300_highprice_lgbm_120s'
            expr_name_300s = 'ddb_null_factor_no_re_all_new_6m_hs300_highprice_lgbm_300s'
            # expr_name_mix_60s = 'mix2_1_1_pct20_hs300_highprice_lgbm_60s'
            # expr_name_mix_120s = 'mix3_1_1_1_pct20_hs300_highprice_lgbm_120s'
            # expr_name_mix_300s = 'mix4_1_1_1_1_pct20_hs300_highprice_lgbm_300s'

            signal_15s = read_signal_and_adjust_main_signal_enhance(expr_name_15s, '15s', month).rename(columns={'new_signal':'new_signal_15s'})
            signal_60s = read_signal_and_adjust_main_signal_enhance(expr_name_60s, '60s', month).rename(columns={'new_signal':'new_signal_60s'})
            signal_120s = read_signal_and_adjust_main_signal_enhance(expr_name_120s, '120s',month).rename(columns={'new_signal':'new_signal_120s'})
            signal_300s = read_signal_and_adjust_main_signal_enhance(expr_name_300s, '300s', month).rename(columns={'new_signal':'new_signal_300s'})

            merge_keys = ['ticker', 'date', 'time']
            merge_signal = signal_15s.merge(signal_60s, on=merge_keys).merge(signal_120s, on=merge_keys).merge(signal_300s, on=merge_keys)
            merge_signal['merge_signal'] = merge_signal['new_signal_15s'] * 2 + merge_signal['new_signal_60s']*2 + merge_signal['new_signal_120s']*2 + merge_signal['new_signal_300s']*2

            if isinstance(trading_hours, dict):
                if trading_hours['start_time'] <= trading_hours['end_time']:
                    print(f"Trading hours:  [{trading_hours['start_time']}, {trading_hours['end_time']}]")
                start_time = trading_hours['start_time']
                end_time = trading_hours['end_time']
                merge_signal = merge_signal.query("time>= @start_time and time <= @end_time")
            print(f"merge data size is {len(merge_signal)}")

            # filter by upload month
            merge_signal = merge_signal[(merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
            print(f"Uploading month: {month}")
            push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)

    except Exception as e:
        print(e)

def ensemble_batch3_pct(months, del_month=True, trading_hours=None):
    trading_hours = {
        "start_time": 130000,
        "end_time": 145700,
    }
    try:
        # table name
        suffix = 'batch3_pct2_mix_am_pm'
        pool_name = 'hs300'
        price_level = 'highprice'
        model_type = 'lgbm'
        database = 'strategy'
        table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{suffix}"
        ensure_table_name(database, table_name)

        for month in months:
            # read signal and train proba
            expr_name_15s = f'ddb_null_factor_no_reverse_with_930_940_{pool_name}_highprice_lgbm_15s'
            expr_name_60s = f'ddb_null_factor_no_reverse_with_930_940_{pool_name}_highprice_lgbm_60s'
            expr_name_120s = f'ddb_null_factor_no_reverse_with_930_940_{pool_name}_highprice_lgbm_120s'
            expr_name_300s = f'ddb_null_factor_no_reverse_with_930_940_{pool_name}_highprice_lgbm_300s'
            # expr_name_mix_60s = 'mix2_1_1_pct20_hs300_highprice_lgbm_60s'
            # expr_name_mix_120s = 'mix3_1_1_1_pct20_hs300_highprice_lgbm_120s'
            # expr_name_mix_300s = 'mix4_1_1_1_1_pct20_hs300_highprice_lgbm_300s'

            signal_15s = merge_signal_by_pct2(expr_name_15s, '15s', month).rename(columns={'new_signal':'new_signal_15s'})
            signal_60s = merge_signal_by_pct2(expr_name_60s, '60s', month).rename(columns={'new_signal':'new_signal_60s'})
            signal_120s = merge_signal_by_pct2(expr_name_120s, '120s',month).rename(columns={'new_signal':'new_signal_120s'})
            signal_300s = merge_signal_by_pct2(expr_name_300s, '300s', month).rename(columns={'new_signal':'new_signal_300s'})

            merge_keys = ['ticker', 'date', 'time']
            merge_signal = signal_15s.merge(signal_60s, on=merge_keys).merge(signal_120s, on=merge_keys).merge(signal_300s, on=merge_keys)
            merge_signal['merge_signal'] = merge_signal['new_signal_15s'] * 2 + merge_signal['new_signal_60s']*2 + merge_signal['new_signal_120s']*2 + merge_signal['new_signal_300s']*2

            if isinstance(trading_hours, dict):
                if trading_hours['start_time'] <= trading_hours['end_time']:
                    print(f"Trading hours:  [{trading_hours['start_time']}, {trading_hours['end_time']}]")
                start_time = trading_hours['start_time'] * 1000
                end_time = trading_hours['end_time'] *1000
                merge_signal = merge_signal.query("time>= @start_time and time <= @end_time")
            print(f"merge data size is {len(merge_signal)}")

            # filter by upload month
            merge_signal = merge_signal[(merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
            print(f"Uploading month: {month}")
            push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database, del_month=del_month)

    except Exception as e:
        print(e)


def ensemble_bond_etf_6m(months, trading_hours=None):

    try:
        # table name
        suffix = 'bond_etf_w1'
        pool_name = 'hs300'
        price_level = 'highprice'
        model_type = 'lgbm'
        database = 'strategy'
        table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{suffix}"
        ensure_table_name(database, table_name)

        for month in months:
            # read signal and train proba
            expr_name_15s = 'bond_null_factor_no_reverse_bond_etf_highprice_lgbm_15s'
            expr_name_60s = 'bond_null_factor_no_reverse_bond_etf_highprice_lgbm_60s'
            expr_name_120s = 'bond_null_factor_no_reverse_bond_etf_highprice_lgbm_120s'
            expr_name_300s = 'bond_null_factor_no_reverse_bond_etf_highprice_lgbm_300s'
            # expr_name_mix_60s = 'mix2_1_1_pct20_hs300_highprice_lgbm_60s'
            # expr_name_mix_120s = 'mix3_1_1_1_pct20_hs300_highprice_lgbm_120s'
            # expr_name_mix_300s = 'mix4_1_1_1_1_pct20_hs300_highprice_lgbm_300s'

            signal_15s = merge_bond_signal(expr_name_15s, '15s', month).rename(columns={'new_signal':'new_signal_15s'})
            signal_60s = merge_bond_signal(expr_name_60s, '60s', month).rename(columns={'new_signal':'new_signal_60s'})
            signal_120s = merge_bond_signal(expr_name_120s, '120s',month).rename(columns={'new_signal':'new_signal_120s'})
            signal_300s = merge_bond_signal(expr_name_300s, '300s', month).rename(columns={'new_signal':'new_signal_300s'})

            merge_keys = ['ticker', 'date', 'time']
            merge_signal = signal_15s.merge(signal_60s, on=merge_keys).merge(signal_120s, on=merge_keys).merge(signal_300s, on=merge_keys)
            merge_signal['merge_signal'] = merge_signal['new_signal_15s'] * 2 + merge_signal['new_signal_60s']*2 + merge_signal['new_signal_120s']*2 + merge_signal['new_signal_300s']*2

            if isinstance(trading_hours, dict):
                if trading_hours['start_time'] <= trading_hours['end_time']:
                    print(f"Trading hours:  [{trading_hours['start_time']}, {trading_hours['end_time']}]")
                start_time = trading_hours['start_time']
                end_time = trading_hours['end_time']
                merge_signal = merge_signal.query("time>= @start_time and time <= @end_time")
            print(f"merge data size is {len(merge_signal)}")

            # filter by upload month
            merge_signal = merge_signal[(merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
            print(f"Uploading month: {month}")
            push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)

    except Exception as e:
        print(e)


def check_dist(signal_data, column,  time_bin=[940, 1000, 1030, 1130, 1400, 1500]):
    signal_data['time_hhmm'] = signal_data['time'] // 100000
    signal_data['time_group'] = pd.cut(signal_data['time_hhmm'], bins=time_bin,
                                       labels=['abs_signal_' + str(x) for x in time_bin[1:]], right=False)
    signal_data['abs_signal'] = signal_data[column].abs()
    abs_signal = signal_data.groupby('time_group')['abs_signal'].mean()

    return  abs_signal

if __name__ == "__main__":
    months = [202501, 202502,202503,202504, 202505,202506, 202507]
    # ensemble_bond_etf_6m(months)
    # signal = read_signal_and_adjust_main_signal_enhance('ddb_null_factor_no_re_all_new_6m_hs300_highprice_lgbm_300s', '300s', 202506)
    # ensemble_all_new_6m_enhance(months)
    #ensemble_all_new_6m(months)
    ensemble_batch3_pct(months, del_month=False) # zz500














