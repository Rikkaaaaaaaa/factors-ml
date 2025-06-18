import pandas as pd
import glob
import sys
sys.path.append('../')
sys.path.append('./')

from utils.publish import push_single_signal_sql, ensure_table_name


def concat_signals_from_folder(signal_path_list):
    signal = []
    for r in signal_path_list:
        signal.append(pd.read_csv(r))
    return pd.concat(signal)


def merge_main_signal(signal_folder_path, upload_month, table_name, database='strategy'):
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
    print(f"merge data size is {len(merge_signal)}")
    # core merge format
    merge_signal['merge_signal'] = (merge_signal['proba'] - 0.5) * 2 + merge_signal['signal_60s'] * 2 + \
                              merge_signal['signal_120s'] * 2 + merge_signal['signal_300s'] * 2
    # filter by upload month
    if isinstance(upload_month, list):
        merge_signal = merge_signal[(merge_signal.date<(upload_month[-1]+1)*100) & (merge_signal.date>upload_month[0]*100) ]
        print(f"Uploading month: {upload_month}")
        push_single_signal_sql(merge_signal, upload_month=upload_month, table_name=table_name, database=database)
    else:
        merge_signal = merge_signal[(merge_signal.date < (upload_month + 1) * 100) & (merge_signal.date > upload_month * 100)]
        print(f"Uploading month: {upload_month}")
        push_single_signal_sql(merge_signal, upload_month=[upload_month], table_name=table_name, database=database)


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
    merge_main_signal(signal_folder_path, upload_month, table_name, database)


def upload_signal_from_experiments():
    upload_month = [202501,202502,202503, 202504,202505]
    # upload_month = [202404]
    # table name
    expr_name = 'ddb_null_factor_hs'
    table_suffix = 'ddb_null_factor_hs'
    pool_name = 'hs300'
    price_level = 'highprice'
    model_type = 'lgbm'
    database = 'strategy'
    table_name = f"ensemble_signal_{pool_name}_{price_level}_{model_type}_{table_suffix}"

    # check table name
    if len(table_name) > len("ensemble_signal_hs300_highprice_lgbm_ddb_null_factor_hs"):
        raise RuntimeError("Table_name may be too long!")
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
        merge_main_signal(signal_folder_path, month, table_name, database) # use single month, not upload_month

if __name__ == '__main__':
    upload_signal_from_experiments()
