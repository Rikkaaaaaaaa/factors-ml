import pandas as pd
import glob
import sys
sys.path.append('../')
sys.path.append('./')

from utils.publish import push_single_signal_sql, ensure_table_name
pd.options.display.width=500
pd.set_option('display.max_columns', None)


def concat_signals_from_folder(signal_path_list):
    signal = []
    for r in signal_path_list:
        signal.append(pd.read_csv(r))
    return pd.concat(signal)


def merge_main_signal(signal_folder_path, trading_hours=None):
    # read all files from path list
    signal_15s = concat_signals_from_folder(signal_folder_path['signal_15s']).rename(columns={'signal': 'signal_15s'})
    signal_60s = concat_signals_from_folder(signal_folder_path['signal_60s']).rename(columns={'signal': 'signal_60s'})
    signal_120s = concat_signals_from_folder(signal_folder_path['signal_120s']).rename(columns={'signal': 'signal_120s'})
    signal_300s = concat_signals_from_folder(signal_folder_path['signal_300s']).rename(columns={'signal': 'signal_300s'})

    merge_keys = ['ticker', 'date', 'time']
    signal_15s = signal_15s[['ticker', 'date', 'time', 'proba']]
    signal_60s = signal_60s[['ticker', 'date', 'time', 'signal_60s']]
    signal_120s = signal_120s[['ticker', 'date', 'time', 'signal_120s']]
    signal_300s = signal_300s[['ticker', 'date', 'time', 'signal_300s']]

    merge_signal = signal_15s.merge(signal_60s, on=merge_keys).merge(signal_120s, on=merge_keys).merge(signal_300s, on=merge_keys)

    # core merge format
    merge_signal['merge_signal'] = (merge_signal['proba'] - 0.5) * 2 + merge_signal['signal_60s'] * 2 + \
                              merge_signal['signal_120s'] * 2 + merge_signal['signal_300s'] * 2

    if isinstance(trading_hours, dict):
        if trading_hours['start_time'] <= trading_hours['end_time']:
            print(f"Trading hours:  [{trading_hours['start_time']}, {trading_hours['end_time']}]")

        start_time = trading_hours['start_time']
        end_time = trading_hours['end_time']
        merge_signal = merge_signal.query("time>= @start_time and time <= @end_time")
    print(f"merge data size is {len(merge_signal)}")
    return merge_signal


def merge_main_signal(signal_folder_path, trading_hours=None):
    # read all files from path list
    signal_15s = concat_signals_from_folder(signal_folder_path['signal_15s']).rename(columns={'signal': 'signal_15s'})
    signal_60s = concat_signals_from_folder(signal_folder_path['signal_60s']).rename(columns={'signal': 'signal_60s'})
    signal_120s = concat_signals_from_folder(signal_folder_path['signal_120s']).rename(columns={'signal': 'signal_120s'})
    signal_300s = concat_signals_from_folder(signal_folder_path['signal_300s']).rename(columns={'signal': 'signal_300s'})

    merge_keys = ['ticker', 'date', 'time']
    signal_15s = signal_15s[['ticker', 'date', 'time', 'proba']]
    signal_60s = signal_60s[['ticker', 'date', 'time', 'signal_60s']]
    signal_120s = signal_120s[['ticker', 'date', 'time', 'signal_120s']]
    signal_300s = signal_300s[['ticker', 'date', 'time', 'signal_300s']]

    merge_signal = signal_15s.merge(signal_60s, on=merge_keys).merge(signal_120s, on=merge_keys).merge(signal_300s, on=merge_keys)

    # core merge format
    merge_signal['merge_signal'] = (merge_signal['proba'] - 0.5) * 2 + merge_signal['signal_60s'] * 2 + \
                              merge_signal['signal_120s'] * 2 + merge_signal['signal_300s'] * 2

    if isinstance(trading_hours, dict):
        if trading_hours['start_time'] <= trading_hours['end_time']:
            print(f"Trading hours:  [{trading_hours['start_time']}, {trading_hours['end_time']}]")

        start_time = trading_hours['start_time']
        end_time = trading_hours['end_time']
        merge_signal = merge_signal.query("time>= @start_time and time <= @end_time")
    print(f"merge data size is {len(merge_signal)}")
    return merge_signal


def merge_mix6_main_signal(signal_folder_path, trading_hours=None):
    # read all files from path list
    signal_15s = concat_signals_from_folder(signal_folder_path['signal_15s']).rename(columns={'signal': 'signal_15s'})
    signal_60s = concat_signals_from_folder(signal_folder_path['signal_60s']).rename(columns={'signal': 'signal_60s'})
    signal_120s = concat_signals_from_folder(signal_folder_path['signal_120s']).rename(columns={'signal': 'signal_120s'})
    signal_300s = concat_signals_from_folder(signal_folder_path['signal_300s']).rename(columns={'signal': 'signal_300s'})
    signal_mix_120s = concat_signals_from_folder(signal_folder_path['signal_mix_120s']).rename(columns={'signal': 'signal_mix_120s'})
    signal_mix_300s = concat_signals_from_folder(signal_folder_path['signal_mix_300s']).rename(columns={'signal': 'signal_mix_300s'})

    merge_keys = ['ticker', 'date', 'time']
    signal_15s = signal_15s[['ticker', 'date', 'time', 'proba']]
    signal_60s = signal_60s[['ticker', 'date', 'time', 'signal_60s']]
    signal_120s = signal_120s[['ticker', 'date', 'time', 'signal_120s']]
    signal_300s = signal_300s[['ticker', 'date', 'time', 'signal_300s']]
    signal_mix_120s = signal_mix_120s[['ticker', 'date', 'time', 'signal_mix_120s']]
    signal_mix_300s = signal_mix_300s[['ticker', 'date', 'time', 'signal_mix_300s']]

    merge_signal = signal_15s.merge(signal_60s, on=merge_keys).merge(signal_120s, on=merge_keys).merge(signal_300s, on=merge_keys).merge(signal_mix_120s, on=merge_keys).merge(signal_mix_300s, on=merge_keys)

    # core merge format
    merge_signal['merge_signal'] = (merge_signal['proba'] - 0.5) * 2 + merge_signal['signal_60s'] * 2 + \
                              merge_signal['signal_120s'] * 1 + merge_signal['signal_300s'] * 1 + merge_signal['signal_mix_120s'] + merge_signal['signal_mix_300s']

    if isinstance(trading_hours, dict):
        if trading_hours['start_time'] <= trading_hours['end_time']:
            print(f"Trading hours:  [{trading_hours['start_time']}, {trading_hours['end_time']}]")

        start_time = trading_hours['start_time']
        end_time = trading_hours['end_time']
        merge_signal = merge_signal.query("time>= @start_time and time <= @end_time")
    print(f"merge data size is {len(merge_signal)}")
    return merge_signal


def merge_mix7_main_signal(signal_folder_path, trading_hours=None):
    # read all files from path list
    signal_15s = concat_signals_from_folder(signal_folder_path['signal_15s']).rename(columns={'signal': 'signal_15s'})
    signal_60s = concat_signals_from_folder(signal_folder_path['signal_60s']).rename(columns={'signal': 'signal_60s'})
    signal_120s = concat_signals_from_folder(signal_folder_path['signal_120s']).rename(columns={'signal': 'signal_120s'})
    signal_300s = concat_signals_from_folder(signal_folder_path['signal_300s']).rename(columns={'signal': 'signal_300s'})
    signal_mix_60s = concat_signals_from_folder(signal_folder_path['signal_mix_60s']).rename(columns={'signal': 'signal_mix_60s'})
    signal_mix_120s = concat_signals_from_folder(signal_folder_path['signal_mix_120s']).rename(columns={'signal': 'signal_mix_120s'})
    signal_mix_300s = concat_signals_from_folder(signal_folder_path['signal_mix_300s']).rename(columns={'signal': 'signal_mix_300s'})

    merge_keys = ['ticker', 'date', 'time']
    signal_15s = signal_15s[['ticker', 'date', 'time', 'proba']]
    signal_60s = signal_60s[['ticker', 'date', 'time', 'signal_60s']]
    signal_120s = signal_120s[['ticker', 'date', 'time', 'signal_120s']]
    signal_300s = signal_300s[['ticker', 'date', 'time', 'signal_300s']]
    signal_mix_60s = signal_mix_60s[['ticker', 'date', 'time', 'signal_mix_60s']]
    signal_mix_120s = signal_mix_120s[['ticker', 'date', 'time', 'signal_mix_120s']]
    signal_mix_300s = signal_mix_300s[['ticker', 'date', 'time', 'signal_mix_300s']]

    merge_signal = signal_15s.merge(signal_60s, on=merge_keys).merge(signal_120s, on=merge_keys).merge(signal_300s, on=merge_keys).merge(signal_mix_60s, on=merge_keys).merge(signal_mix_120s, on=merge_keys).merge(signal_mix_300s, on=merge_keys)

    # core merge format
    merge_signal['merge_signal'] = (merge_signal['proba'] - 0.5) * 2 + merge_signal['signal_60s'] + merge_signal['signal_mix_60s'] + \
                              merge_signal['signal_120s'] + merge_signal['signal_300s'] + merge_signal['signal_mix_120s'] + merge_signal['signal_mix_300s']

    if isinstance(trading_hours, dict):
        if trading_hours['start_time'] <= trading_hours['end_time']:
            print(f"Trading hours:  [{trading_hours['start_time']}, {trading_hours['end_time']}]")

        start_time = trading_hours['start_time']
        end_time = trading_hours['end_time']
        merge_signal = merge_signal.query("time>= @start_time and time <= @end_time")
    print(f"merge data size is {len(merge_signal)}")
    return merge_signal

def merge_single_signal(signal_folder_path, trading_hours=None):
    # read all files from path list
    signal_15s = concat_signals_from_folder(signal_folder_path['signal_15s']).rename(columns={'signal': 'signal_15s'})
    signal_15s = signal_15s[['ticker', 'date', 'time', 'proba']]
    merge_signal = signal_15s

    # core merge format
    bins = [i / 10 for i in range(0, 10)]
    prob_dist = (merge_signal['proba']-0.5).values_counts(bin=bins, sort=False)
    print('prob_dist', prob_dist)
    merge_signal['merge_signal'] = (merge_signal['proba'] - 0.5) * 30

    if isinstance(trading_hours, dict):
        if trading_hours['start_time'] <= trading_hours['end_time']:
            print(f"Trading hours:  [{trading_hours['start_time']}, {trading_hours['end_time']}]")

        start_time = trading_hours['start_time']
        end_time = trading_hours['end_time']
        merge_signal = merge_signal.query("time>= @start_time and time <= @end_time")
    print(f"merge data size is {len(merge_signal)}")
    return merge_signal

def upload_signal_from_ensemble():
    upload_month = [202404,202405,202406,202407,20208,202409,202410,202411,202412,202501,202502,202503]
    signal_folder_path = dict()
    signal_folder_path['signal_15s'] = glob.glob('../ensemble/ensemble_signals/ensemble_with_all_weight_3_1_1_1/*15s.csv')
    signal_folder_path['signal_60s'] = glob.glob('../ensemble/ensemble_signals/ensemble_with_all_weight_3_1_1_1/*60s.csv')
    signal_folder_path['signal_120s'] = glob.glob('../ensemble/ensemble_signals/ensemble_with_all_weight_3_1_1_1/*120s.csv')
    signal_folder_path['signal_300s'] = glob.glob('../ensemble/ensemble_signals/ensemble_manual_selection_300s_weight_3_1_1_1/*300s.csv')

    # table name
    suffix = 'avg'
    pool_name = 'hs300'
    price_level = 'highprice'
    model_type = 'lgbm'
    database = 'strategy'
    table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{suffix}"
    ensure_table_name(database, table_name)
    # append to sql table
    merge_signal = merge_main_signal(signal_folder_path)  # use single month, not upload_month

    # filter by upload month
    merge_signal = merge_signal[
        (merge_signal.date < (upload_month[-1] + 1) * 100) & (merge_signal.date > upload_month[0] * 100)]
    print(f"Uploading month: {upload_month}")
    push_single_signal_sql(merge_signal, upload_month=upload_month, table_name=table_name, database=database)


def upload_signal_from_experiments_by_period():

    upload_month = [202501, 202502, 202503, 202504, 202505, 202506, 202507]
    # upload_month = [202404]
    # table name
    am_expr_name = 'ddb_null_factor_new_allam_6month'
    pm_expr_name = 'ddb_null_factor_no_re_all_new_6m'
    table_suffix = 'am_newmodel_pm_allday'
    pool_name = 'hs300'
    price_level = 'highprice'
    model_type = 'lgbm'
    database = 'strategy'
    table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{table_suffix}"

    am_signal_folder_path = dict()
    pm_signal_folder_path = dict()
    ensure_table_name(database, table_name)

    for month in upload_month:
        am_signal_folder_path['signal_15s'] = glob.glob(
            f'experiments/{am_expr_name}_{pool_name}_{price_level}_{model_type}_15s/{month}/signal/*.csv')
        am_signal_folder_path['signal_60s'] = glob.glob(
             f'experiments/{am_expr_name}_{pool_name}_{price_level}_{model_type}_60s/{month}/signal/*.csv')
        am_signal_folder_path['signal_120s'] = glob.glob(
             f'experiments/{am_expr_name}_{pool_name}_{price_level}_{model_type}_120s/{month}/signal/*.csv')
        am_signal_folder_path['signal_300s'] = glob.glob(
             f'experiments/{am_expr_name}_{pool_name}_{price_level}_{model_type}_300s/{month}/signal/*.csv')

        pm_signal_folder_path['signal_15s'] = glob.glob(
            f'experiments/{pm_expr_name}_{pool_name}_{price_level}_{model_type}_15s/{month}/signal/*.csv')
        pm_signal_folder_path['signal_60s'] = glob.glob(
            f'experiments/{pm_expr_name}_{pool_name}_{price_level}_{model_type}_60s/{month}/signal/*.csv')
        pm_signal_folder_path['signal_120s'] = glob.glob(
            f'experiments/{pm_expr_name}_{pool_name}_{price_level}_{model_type}_120s/{month}/signal/*.csv')
        pm_signal_folder_path['signal_300s'] = glob.glob(
            f'experiments/{pm_expr_name}_{pool_name}_{price_level}_{model_type}_300s/{month}/signal/*.csv')

        # append to sql table
        am_hours = {'start_time': int(94000*1000), 'end_time': int(113000*1000)}
        merge_signal_am = merge_main_signal(am_signal_folder_path, trading_hours=am_hours)
        pm_hours = {'start_time':int(130000*1000), 'end_time':int(145700*1000)}
        merge_signal_pm = merge_main_signal(pm_signal_folder_path, trading_hours=pm_hours)

        merge_signal = pd.concat([merge_signal_am, merge_signal_pm])

        # filter by upload month
        merge_signal = merge_signal[
            (merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
        print(f"Uploading month: {month}")
        push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)

def upload_signal_from_experiments():
    upload_month = [202507]
    print("Uploading signal month is ", upload_month)
    # upload_month = [202404]
    # table name
    # expr_name = 'ddb_null_factor_no_reverse'#'ddb_null_factor_no_re_all_new_6m'
    # table_suffix = 'ddb_null_factor_no_re'
    expr_name = 'bond_etf_null_factor_no_reverse_with_930_940'
    table_suffix = 'bond_etf_6m_930_new'
    pool_name = 'bond_etf'
    price_level = 'highprice'
    model_type = 'lgbm'
    database = 'strategy'
    table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{table_suffix}"

    signal_folder_path = dict()
    ensure_table_name(database, table_name)

    for month in upload_month:
        signal_folder_path['signal_15s'] = glob.glob(
            f'experiments/{expr_name}_{pool_name}_{price_level}_{model_type}_15s/{month}/signal/*.csv')
        signal_folder_path['signal_60s'] = glob.glob(
             f'experiments/{expr_name}_{pool_name}_{price_level}_{model_type}_60s/{month}/signal/*.csv')
        signal_folder_path['signal_120s'] = glob.glob(
             f'experiments/{expr_name}_{pool_name}_{price_level}_{model_type}_120s/{month}/signal/*.csv')
        signal_folder_path['signal_300s'] = glob.glob(
             f'experiments/{expr_name}_{pool_name}_{price_level}_{model_type}_300s/{month}/signal/*.csv')

        # append to sql table
        merge_signal = merge_main_signal(signal_folder_path,) # use single month, not upload_month

        # filter by upload month
        merge_signal = merge_signal[
            (merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
        print(f"Uploading month: {month}")
        push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)


def upload_mix1_signal_from_experiments():
    upload_month = [202501, 202502, 202503, 202504, 202505, 202506, 202507]
    # upload_month = [202404]
    # table name
    expr_name_15s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_60s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_120s = 'mix3_1_1_1_pct20'
    expr_name_300s = 'mix4_1_1_1_1_pct20'
    table_suffix = 'mix_120s_300s_pct20'
    pool_name = 'hs300'
    price_level = 'highprice'
    model_type = 'lgbm'
    database = 'strategy'
    table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{table_suffix}"

    signal_folder_path = dict()
    ensure_table_name(database, table_name)

    for month in upload_month:
        signal_folder_path['signal_15s'] = glob.glob(
            f'experiments/{expr_name_15s}_{pool_name}_{price_level}_{model_type}_15s/{month}/signal/*.csv')
        signal_folder_path['signal_60s'] = glob.glob(
             f'experiments/{expr_name_60s}_{pool_name}_{price_level}_{model_type}_60s/{month}/signal/*.csv')
        signal_folder_path['signal_120s'] = glob.glob(
             f'experiments/{expr_name_120s}_{pool_name}_{price_level}_{model_type}_120s/{month}/signal/*.csv')
        signal_folder_path['signal_300s'] = glob.glob(
             f'experiments/{expr_name_300s}_{pool_name}_{price_level}_{model_type}_300s/{month}/signal/*.csv')

        # append to sql table
        merge_signal = merge_main_signal(signal_folder_path) # use single month, not upload_month

        # filter by upload month
        merge_signal = merge_signal[
            (merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
        print(f"Uploading month: {month}")
        push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)

def upload_mix2_signal_from_experiments():
    upload_month = [202501, 202502, 202503, 202504, 202505, 202506, 202507]
    # upload_month = [202404]
    # table name
    expr_name_15s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_60s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_120s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_300s = 'mix4_1_1_1_1_pct20'
    table_suffix = 'mix_300s_pct20'
    pool_name = 'hs300'
    price_level = 'highprice'
    model_type = 'lgbm'
    database = 'strategy'
    table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{table_suffix}"

    signal_folder_path = dict()
    ensure_table_name(database, table_name)

    for month in upload_month:
        signal_folder_path['signal_15s'] = glob.glob(
            f'experiments/{expr_name_15s}_{pool_name}_{price_level}_{model_type}_15s/{month}/signal/*.csv')
        signal_folder_path['signal_60s'] = glob.glob(
             f'experiments/{expr_name_60s}_{pool_name}_{price_level}_{model_type}_60s/{month}/signal/*.csv')
        signal_folder_path['signal_120s'] = glob.glob(
             f'experiments/{expr_name_120s}_{pool_name}_{price_level}_{model_type}_120s/{month}/signal/*.csv')
        signal_folder_path['signal_300s'] = glob.glob(
             f'experiments/{expr_name_300s}_{pool_name}_{price_level}_{model_type}_300s/{month}/signal/*.csv')

        # append to sql table
        merge_signal = merge_main_signal(signal_folder_path) # use single month, not upload_month

        # filter by upload month
        merge_signal = merge_signal[
            (merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
        print(f"Uploading month: {month}")
        push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)

def upload_mix6_signal():
    upload_month = [202501, 202502, 202503, 202504, 202505, 202506]
    # upload_month = [202404]
    # table name
    expr_name_15s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_60s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_120s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_300s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_mix_120s = 'mix3_1_1_1'
    expr_name_mix_300s = 'mix4_1_1_1_1'
    table_suffix = 'mix6_2'
    pool_name = 'hs300'
    price_level = 'highprice'
    model_type = 'lgbm'
    database = 'strategy'
    table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{table_suffix}"

    signal_folder_path = dict()
    ensure_table_name(database, table_name)

    for month in upload_month:
        signal_folder_path['signal_15s'] = glob.glob(
            f'experiments/{expr_name_15s}_{pool_name}_{price_level}_{model_type}_15s/{month}/signal/*.csv')
        signal_folder_path['signal_60s'] = glob.glob(
             f'experiments/{expr_name_60s}_{pool_name}_{price_level}_{model_type}_60s/{month}/signal/*.csv')
        signal_folder_path['signal_120s'] = glob.glob(
             f'experiments/{expr_name_120s}_{pool_name}_{price_level}_{model_type}_120s/{month}/signal/*.csv')
        signal_folder_path['signal_300s'] = glob.glob(
             f'experiments/{expr_name_300s}_{pool_name}_{price_level}_{model_type}_300s/{month}/signal/*.csv')
        signal_folder_path['signal_mix_120s'] = glob.glob(
            f'experiments/{expr_name_mix_120s}_{pool_name}_{price_level}_{model_type}_120s/{month}/signal/*.csv')
        signal_folder_path['signal_mix_300s'] = glob.glob(
            f'experiments/{expr_name_mix_300s}_{pool_name}_{price_level}_{model_type}_300s/{month}/signal/*.csv')

        # append to sql table
        merge_signal = merge_mix6_main_signal(signal_folder_path) # use single month, not upload_month

        # filter by upload month
        merge_signal = merge_signal[
            (merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
        print(f"Uploading month: {month}")
        push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)

def upload_mix7_signal():
    upload_month = [202501, 202502, 202503, 202504, 202505, 202506]
    # upload_month = [202404]
    # table name
    expr_name_15s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_60s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_120s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_300s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_mix_60s = 'mix2_1_1_pct20'
    expr_name_mix_120s = 'mix3_1_1_1_pct20'
    expr_name_mix_300s = 'mix4_1_1_1_1_pct20'
    table_suffix = 'mix7_pct20'
    pool_name = 'hs300'
    price_level = 'highprice'
    model_type = 'lgbm'
    database = 'strategy'
    table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{table_suffix}"

    signal_folder_path = dict()
    ensure_table_name(database, table_name)

    for month in upload_month:
        signal_folder_path['signal_15s'] = glob.glob(
            f'experiments/{expr_name_15s}_{pool_name}_{price_level}_{model_type}_15s/{month}/signal/*.csv')
        signal_folder_path['signal_60s'] = glob.glob(
             f'experiments/{expr_name_60s}_{pool_name}_{price_level}_{model_type}_60s/{month}/signal/*.csv')
        signal_folder_path['signal_120s'] = glob.glob(
             f'experiments/{expr_name_120s}_{pool_name}_{price_level}_{model_type}_120s/{month}/signal/*.csv')
        signal_folder_path['signal_300s'] = glob.glob(
             f'experiments/{expr_name_300s}_{pool_name}_{price_level}_{model_type}_300s/{month}/signal/*.csv')
        signal_folder_path['signal_mix_60s'] = glob.glob(
            f'experiments/{expr_name_mix_60s}_{pool_name}_{price_level}_{model_type}_60s/{month}/signal/*.csv')
        signal_folder_path['signal_mix_120s'] = glob.glob(
            f'experiments/{expr_name_mix_120s}_{pool_name}_{price_level}_{model_type}_120s/{month}/signal/*.csv')
        signal_folder_path['signal_mix_300s'] = glob.glob(
            f'experiments/{expr_name_mix_300s}_{pool_name}_{price_level}_{model_type}_300s/{month}/signal/*.csv')

        # append to sql table
        merge_signal = merge_mix7_main_signal(signal_folder_path) # use single month, not upload_month

        # filter by upload month
        merge_signal = merge_signal[
            (merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
        print(f"Uploading month: {month}")
        push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)

def upload_mix3_signal():
    upload_month = [202501, 202502, 202503, 202504, 202505, 202506]
    # upload_month = [202404]
    # table name
    expr_name_15s = 'ddb_null_factor_no_re_all_new_6m'
    expr_name_60s = 'mix2_1_1'
    expr_name_120s = 'mix3_1_1_1'
    expr_name_300s = 'mix4_1_1_1_1'

    table_suffix = 'mix3'
    pool_name = 'hs300'
    price_level = 'highprice'
    model_type = 'lgbm'
    database = 'strategy'
    table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{table_suffix}"

    signal_folder_path = dict()
    ensure_table_name(database, table_name)

    for month in upload_month:
        signal_folder_path['signal_15s'] = glob.glob(
            f'experiments/{expr_name_15s}_{pool_name}_{price_level}_{model_type}_15s/{month}/signal/*.csv')
        signal_folder_path['signal_60s'] = glob.glob(
             f'experiments/{expr_name_60s}_{pool_name}_{price_level}_{model_type}_60s/{month}/signal/*.csv')
        signal_folder_path['signal_120s'] = glob.glob(
             f'experiments/{expr_name_120s}_{pool_name}_{price_level}_{model_type}_120s/{month}/signal/*.csv')
        signal_folder_path['signal_300s'] = glob.glob(
             f'experiments/{expr_name_300s}_{pool_name}_{price_level}_{model_type}_300s/{month}/signal/*.csv')


        # append to sql table
        merge_signal = merge_main_signal(signal_folder_path) # use single month, not upload_month

        # filter by upload month
        merge_signal = merge_signal[
            (merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
        print(f"Uploading month: {month}")
        push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)


def upload_single_signal_from_experiments():
    upload_month = [202501, 202502, 202503, 202504, 202505]
    # upload_month = [202404]
    # table name
    expr_name = 'mix4_1_1_1_1'
    table_suffix = 'mix4_1111'
    pool_name = 'hs300'
    price_level = 'highprice'
    model_type = 'lgbm'
    database = 'strategy'
    table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{table_suffix}"

    signal_folder_path = dict()
    ensure_table_name(database, table_name)

    for month in upload_month:
        signal_folder_path['signal_15s'] = glob.glob(
            f'experiments/{expr_name}_{pool_name}_{price_level}_{model_type}/{month}/signal/*.csv')
        # append to sql table
        merge_signal = merge_single_signal(signal_folder_path) # use single month, not upload_month

        # filter by upload month
        merge_signal = merge_signal[
            (merge_signal.date < (month + 1) * 100) & (merge_signal.date > month * 100)]
        print(f"Uploading month: {month}")
        push_single_signal_sql(merge_signal, upload_month=[month], table_name=table_name, database=database)

if __name__ == '__main__':
    upload_signal_from_experiments()
    # upload_signal_from_experiments_by_period()
    # upload_single_signal_from_experiments()
    # upload_mix2_signal_from_experiments()
    # upload_mix2_signal_from_experiments()
    # upload_mix7_signal()
    # upload_mix3_signal()
    # upload_signal_from_experiments()

