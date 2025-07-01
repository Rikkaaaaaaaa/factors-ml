import glob
import os
import numpy as np
import pandas as pd
import multiprocessing
from multiprocessing import Pool

from utils.ddb import read_ddb_return,get_limit_flag


def eval_result(y_test, y_pred_label):
    abs_ret = np.mean(np.abs(y_test))
    # win rate(drop y_test=0)
    up_winrate = np.sum(y_test[(y_test != 0) & (y_pred_label == 1)] > 0) / len(y_test[(y_test != 0) & (y_pred_label == 1)])
    down_winrate = np.sum(y_test[(y_test != 0) & (y_pred_label == -1)] < 0) / len(y_test[(y_test != 0) & (y_pred_label == -1)])
    # return
    up_ret = np.mean(y_test[y_pred_label == 1])
    down_ret = np.mean(y_test[y_pred_label == -1])
    # signal pct
    up_pct = len(y_test[y_pred_label == 1]) / len(y_test)
    down_pct = len(y_test[y_pred_label == -1]) / len(y_test)
    nonzero_pct = np.sum(y_test != 0) / len(y_test)
    # weighted return
    weighted_return = up_ret * up_pct - down_ret * down_pct
    # scale
    up_ret = up_ret * 1e4
    down_ret = down_ret * 1e4
    up_pct = up_pct * 100
    down_pct = down_pct * 100
    weighted_return = weighted_return * 1e4
    nonzero_pct = nonzero_pct * 100
    abs_ret = abs_ret * 1e4
    avg_ret = np.mean(y_test)*1e4
    return [weighted_return, up_winrate, down_winrate, up_ret, down_ret, up_pct, down_pct, len(y_test), nonzero_pct, abs_ret, avg_ret]


def read_signal_from_path(signal_root_path):
    '''
    read signal data from one csv file or folder
    '''
    if signal_root_path.lower().endswith('csv'):
        return pd.read_csv(signal_root_path)

    signal_path_list = glob.glob(f"{signal_root_path}/*.csv")
    if len(signal_path_list) == 0:
        raise FileExistsError(f"There is no signal csv file in {signal_root_path}")
    if len(signal_path_list) == 1:
        return pd.read_csv(signal_path_list[0])
    else:
        signal = []
        for signal_path in sorted(os.listdir(signal_root_path)):
            data = pd.read_csv((os.path.join(signal_root_path, signal_path)))
            signal.append(data)
        return pd.concat(signal)


def merge_signal(signal, ret_name, month):
    '''
    merge signal with ddb return monthly by tcicker,date,time
    '''
    # if exist ret column, return
    if f'ret_{ret_name}' in signal.columns:
        return signal
    # read return from ddb
    tickers = tuple(signal["ticker"].unique())
    labels = read_ddb_return(month, tickers)
    labels = labels[['ticker', 'date', "time", f'ret_{ret_name}']]
    # del null return data
    labels = labels.dropna()
    df_merge = labels.merge(signal, on=['ticker', 'date', 'time']).dropna()

    return df_merge

def compute_metrics(df_signal, ret_name, month):
    tickers = tuple(df_signal["ticker"].unique())
    # backtest by ticker
    report = []
    for ticker in tickers:
        # get data of per ticker
        df_ticker = df_signal.query("ticker==@ticker")
        y_test = df_ticker['ret_{}'.format(ret_name)].values
        # evaluate signal
        y_pred_label = df_ticker.signal
        results = eval_result(y_test, y_pred_label)
        # if  len(y_test[(y_test != 0) & (y_pred_label == 1)]) == 0:
        #     print(ticker, ret_name, month)
        up_bound = df_ticker.up_bound.values[0]
        down_bound = df_ticker.down_bound.values[0]
        date = df_ticker.date.values[0]
        # append to results
        results.insert(0, ticker)
        results.insert(1, month)
        results.insert(2, date)
        results.insert(3, up_bound)
        results.insert(4, down_bound)
        report.append(results)
    report = pd.DataFrame(report, columns=["ticker", "test_month", "test_date", "up_bound", "down_bound", "weighted_return", "up_winrate", "down_winrate", "up_ret", "down_ret", "up_pct", "down_pct",  "total_sample", "not_zero_rate", "abs_ret", "avg_ret"])

    return report


def eval_signals_by_month(result_name, signal_path, month, ret_name, trading_hours=None):
    try:
        # read signal from csv or folder
        signal = read_signal_from_path(signal_path)
        bt_signal = merge_signal(signal, ret_name, month)
        # filter by trading hours
        if isinstance(trading_hours, dict):
            if trading_hours['am_start_time'] <= trading_hours['am_end_time']:
                print(f"Trading hours: AM-[{trading_hours['am_start_time']}, {trading_hours['am_end_time']}]")
            if trading_hours['pm_start_time'] <= trading_hours['pm_end_time']:
                print(f"Trading hours: PM-[{trading_hours['pm_start_time']}, {trading_hours['pm_end_time']}]")
            bt_signal = bt_signal[((bt_signal["time"] >= trading_hours['am_start_time'] * 1000) & (
                        bt_signal["time"] <= trading_hours['am_end_time'] * 1000))
                                  | ((bt_signal["time"] >= trading_hours['pm_start_time'] * 1000) & (
                        bt_signal["time"] <= trading_hours['pm_end_time'] * 1000))
                                  ]

        # compute metrics and save report
        report = compute_metrics(bt_signal, ret_name, month)

        # save report
        report_folder_path = os.path.join('./eval_monthly_reports', f'{result_name}')
        report_name = f"report_{result_name}_{month}_{ret_name}.csv"
        report_path = os.path.join(report_folder_path, report_name)
        if not os.path.exists(report_folder_path):
            os.makedirs(report_folder_path)
        print(f"Report has been saved at {report_path}")
        report.to_csv(report_path, index=False)
    except Exception as e:
        print(e)

def analysis_report_by_month(report_name, ret_windows = [ "15s", "60s", "120s", '300s'], report_root_path='./eval_monthly_reports'):
    '''
    summarize report by month
    '''
    cols = ["test_month", "weighted_return", "up_bound", "down_bound", "up_winrate", "down_winrate", "up_ret", "down_ret", "up_pct",
            "down_pct",  "total_sample", "not_zero_rate", "abs_ret", "avg_ret"]
    summary = []
    report_path_list = glob.glob(os.path.join(report_root_path, report_name) + '/*.csv')
    for ret_window in ret_windows:
        for report_path in sorted(report_path_list):
            if ret_window in os.path.basename(report_path) :
                report = pd.read_csv(report_path)
                new_report = report[cols].groupby('test_month').mean().round(4)
                new_report.insert(0, "test_month", report['test_month'].values[0])
                new_report.insert(1, "ret_window", ret_window)
                summary.append(new_report)

    summary = pd.concat(summary, ignore_index=True)
    summary_folder_path = os.path.join('./eval_summary', f'{result_name}')
    summary_name = f"summary_by_month_{report_name}.csv"
    summary_path = os.path.join(summary_folder_path, summary_name)
    if not os.path.exists(summary_folder_path):
        os.makedirs(summary_folder_path)
    summary.to_csv(summary_path, index=False)
    print(f"Summary by month has been saved at {summary_path}")


def eval_signals_by_date(result_name, signal_path, month, ret_name, trading_hours=None):
    # params
    # ret_name = '300s'
    # month=202503
    # result_name = 'bt_ensemble_signal'
    # #expr_name = f"ddb_factor_hs300_highprice_lgbm_{ret_name}"
    # #signal_folder_path = f"../experiments/{expr_name}/{month}/signal"
    # signal_path = f'../ensemble/ensemble_signals/ensemble_manual_selection_300s_weight_3_1_1_1_202503_300s.csv'

    try:
        # read signal
        signal = read_signal_from_path(signal_path)
        bt_signal = merge_signal(signal, ret_name, month)
        # filter by trading hours
        if isinstance(trading_hours, dict):
            if trading_hours['am_start_time'] <= trading_hours['am_end_time']:
                print(f"Trading hours: AM-[{trading_hours['am_start_time'] }, {trading_hours['am_end_time']}]")
            if trading_hours['pm_start_time'] <= trading_hours['pm_end_time']:
                print(f"Trading hours: PM-[{trading_hours['pm_start_time']}, {trading_hours['pm_end_time']}]")
            bt_signal = bt_signal[((bt_signal["time"] >= trading_hours['am_start_time'] * 1000) & (bt_signal["time"] <= trading_hours['am_end_time'] * 1000))
                      | ((bt_signal["time"] >= trading_hours['pm_start_time'] * 1000) & (bt_signal["time"] <= trading_hours['pm_end_time'] * 1000))
            ]

        report_all_month= []
        for test_date in bt_signal.date.unique():
            _bt_signal = bt_signal.query("date==@test_date")
            # compute metrics
            _report = compute_metrics(_bt_signal, ret_name, month)
            report_all_month.append(_report)

        # save report by date
        report_folder_path = os.path.join('./eval_daily_reports', f'{result_name}')
        report_name = f"report_by_date_{result_name}_{month}_{ret_name}.csv"
        report_path = os.path.join(report_folder_path, report_name)
        if not os.path.exists(report_folder_path):
            os.makedirs(report_folder_path)
        report_all_month = pd.concat(report_all_month)
        ticker_list = report_all_month['ticker'].unique()
        df_limit_flag = get_limit_flag(str(month), ticker_list)
        report_all_month = report_all_month.merge(df_limit_flag, left_on=['ticker', 'test_date'], right_on=['ticker', 'date'])
        report_all_month = report_all_month[report_all_month['limit_flag']==0]
        print(f"Daily report has been saved at {report_path}")
        report_all_month.to_csv(report_path, index=False)

        # analysis report to summary folder by date
        summary_name = f"summary_by_date_{result_name}_{month}_{ret_name}"
        analysis_report_by_date(report_all_month, result_name, summary_name)
    except Exception as e:
        print(e)


def analysis_report_by_date(report, result_name, summary_name):
    cols = ["test_month", "test_date",  "weighted_return", "up_bound", "down_bound", "up_winrate", "down_winrate", "up_ret", "down_ret", "up_pct",
            "down_pct", "total_sample", "not_zero_rate", "abs_ret", "avg_ret"]

    summary_folder_path = os.path.join('./eval_daily_summary', f'{result_name}')
    summary_path = os.path.join(summary_folder_path, f'{summary_name}.csv')
    if not os.path.exists(summary_folder_path):
        os.makedirs(summary_folder_path)

    summary = report[cols].groupby('test_date').mean()
    summary.to_csv(summary_path, index=True)
    print(f"Summary by date has been saved at {summary_path}")


def analysis_summary_by_date(report_name, ret_windows = [ "15s", "60s", "120s", '300s'], daily_summary_root_path='./eval_daily_summary'):
    keep_cols = ["test_month"]
    calc_cols = ["weighted_return", "up_bound", "down_bound", "up_winrate", "down_winrate", "up_ret", "down_ret", "up_pct",
                    "down_pct","abs_ret", "avg_ret"]
    monthly_summary_mean = []
    monthly_summary_std = []
    report_path_list = glob.glob(os.path.join(daily_summary_root_path, report_name) + '/*.csv')
    for ret_window in ret_windows:
        for report_path in sorted(report_path_list):
            if ret_window in report_path:
                daily_summary = pd.read_csv(report_path)
                mean_values = daily_summary[calc_cols].mean().round(4)
                std_values = daily_summary[calc_cols].std().round(4)

                mean_row = pd.Series(index=keep_cols + ['ret_window'] +[f'mean_{col}' for col in calc_cols], name=ret_window)
                mean_row[keep_cols] = daily_summary[keep_cols].iloc[0]
                mean_row["ret_window"] = ret_window
                for col in calc_cols:
                    mean_row[f'mean_{col}'] = mean_values[col]
                std_row = pd.Series(index=keep_cols + ['ret_window'] + [f'std_{col}' for col in calc_cols], name=ret_window)
                std_row[keep_cols] = daily_summary[keep_cols].iloc[0]
                std_row["ret_window"] = ret_window
                for col in calc_cols:
                    std_row[f'std_{col}'] = std_values[col]

                monthly_summary_mean.append(mean_row.to_frame().T)
                monthly_summary_std.append((std_row.to_frame().T))
    monthly_summary_mean = pd.concat(monthly_summary_mean, ignore_index=True)
    monthly_summary_std = pd.concat(monthly_summary_std, ignore_index=True)
    save_path = os.path.join('./eval_summary', report_name, f'summary_agg_by_date_{report_name}.xlsx')

    with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
        monthly_summary_mean.to_excel(writer, sheet_name='mean', index=False)
        monthly_summary_std.to_excel(writer, sheet_name='std', index=False)
    print(f"Summary agg by date has been saved at {save_path}")


if __name__ == "__main__":
    months = [202501,202502,202503,202504, 202505, 202506]
    ret_windows = ['15s', '60s', '120s', '300s']
    # use eval function to treat signal files in experiments folder

    #signal_path = 'f"../87_experiments/manual_factor_select_results/ddb_factor_select_hs300_highprice_lgbm_{ret_window}/{month}/signal"'
    #result_name = 'manual_factor_selection'

    #signal_path = 'f"../experiments/ddb_factor_all_new_hs300_highprice_lgbm_{ret_window}/{month}/signal"'
    #result_name = 'ddb_factor_all_new'


    signal_path = 'f"../experiments/ddb_null_factor_hs300_highprice_lgbm_{ret_window}/{month}/signal"'
    result_name = 'ddb_null_factor'

    signal_path = 'f"../experiments/ddb_factor_all_new_alpha001_hs300_highprice_lgbm_{ret_window}/{month}/signal"'
    result_name = 'ddb_factor_all_new_alpha001'

    signal_path = 'f"../experiments/ddb_factor_all_new_alpha0005_hs300_highprice_lgbm_{ret_window}/{month}/signal"'
    result_name = 'ddb_factor_all_new_alpha0005'

    signal_path = 'f"../ensemble/ensemble_signals/ensemble_mix2_300s_weight_3_1_1_1/ensemble_mix2_300s_weight_3_1_1_1_{month}_{ret_window}.csv"'
    result_name = 'ensemble_mix2_300s_weight_3_1_1_1'

    signal_path =  'f"../ensemble/ensemble_signals/create_mix2s_ret_signal/create_mix2s_ret_signal_{month}_{ret_window}.csv"'
    result_name = 'mix2s_ret_signal'

    # signal_path = 'f"../ensemble/ensemble_signals/create_mix2_ret_signal/create_mix2_ret_signal_{month}_{ret_window}.csv"'
    # result_name = 'mix2_ret_signal'

    #signal_path = 'f"../experiments/ddb_factor_all_new_manual_selection_hs300_highprice_lgbm_{ret_window}/{month}/signal"'
    #result_name = 'ddb_factor_all_new_manual_selection'

    #result_name = 'ensemble_manual_selection_300s_weight_3_1_1_1'
    #signal_path = 'f"../ensemble/ensemble_signals/ensemble_manual_selection_300s_weight_3_1_1_1/ensemble_manual_selection_300s_weight_3_1_1_1_{month}_{ret_window}.csv"'

    #result_name = 'ensemble_with_all_weight_3_1_1_1'
    #signal_path = 'f"../ensemble/ensemble_signals/ensemble_with_all_weight_3_1_1_1/ensemble_with_all_weight_3_1_1_1_{month}_{ret_window}.csv"'

    result_name = 'ddb_null_factor_new_indus_in_open_hs300_highprice_lgbm'
    expr_name = 'ddb_null_factor_new_indus_hs300_highprice_lgbm'
    signal_path = 'f"../experiments/{expr_name}_{ret_window}/{month}/signal"'
    #
    # result_name = 'ddb_null_factor_in_open_hs300_highprice_lgbm'
    # expr_name = 'ddb_null_factor_hs300_highprice_lgbm'
    # signal_path = 'f"../experiments/{expr_name}_{ret_window}/{month}/signal"'

    # result_name = 'ddb_null_factor_new_open_hs300_highprice_lgbm'
    # expr_name = 'ddb_null_factor_new_open_hs300_highprice_lgbm'
    # signal_path = 'f"../experiments/{expr_name}_{ret_window}/{month}/signal"'

    #
    # result_name = 'ddb_null_factor_open_hs300_highprice_lgbm'
    # expr_name = 'ddb_null_factor_open_hs300_highprice_lgbm'
    # signal_path = 'f"../experiments/{expr_name}_{ret_window}/{month}/signal"'

    result_name = 'ddb_null_factor_hs300_highprice_lgbm'
    expr_name = 'ddb_null_factor_hs300_highprice_lgbm'
    signal_path = 'f"../experiments/{expr_name}_{ret_window}/{month}/signal"'

    #
    # trading_hours = {
    #     "am_start_time": 113015,
    #     "am_end_time": 113000,
    #     "pm_start_time": 130000,
    #     "pm_end_time": 145700
    # }
    trading_hours = None

    n_jobs = 16
    params = [(result_name,
               eval(signal_path),
               month, ret_window, trading_hours)
              for month in months
              for ret_window in ret_windows]
    # eval by month
    with Pool(processes=n_jobs) as pool:
        pool.starmap(eval_signals_by_month, params)
    analysis_report_by_month(result_name)

    # eval by date
    with Pool(processes=n_jobs) as pool:
        pool.starmap(eval_signals_by_date, params)
    analysis_summary_by_date(result_name)






