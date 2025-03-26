import os
import numpy as np
import pandas as pd
import sys
import multiprocessing
from multiprocessing import Pool
sys.path.append('./')
sys.path.append('../')

import utils
from utils.ddb import read_ddb_return


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
    return [up_winrate, down_winrate, up_ret, down_ret, up_pct, down_pct, weighted_return, len(y_test), nonzero_pct, abs_ret]


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


def merge_signal(expr_name, ret_name, month):
    # read signal files
    signal_path = f"../experiments/{expr_name}/{month}/signal"
    signal = read_signal_from_csv(signal_path)
    # read return from ddb
    tickers = tuple(signal["ticker"].unique())
    labels = read_ddb_return(month, tickers)
    labels = labels[['ticker', 'date', "time", f'ret_{ret_name}']]
    # del null return data
    labels = labels.dropna()
    df_merge = labels.merge(signal, on=['ticker', 'date', 'time']).dropna()

    return df_merge

def compute_metrics(df_signal, df_train_proba, expr_name, ret_name, month):
    report_folder, report_name = "./reports", f"report_{expr_name}_{month}_{ret_name}.csv"
    pct_num = {'15s': 40, '60s':20, '120s':20, '300s':20}

    tickers = tuple(df_signal["ticker"].unique())
    # labels = read_ddb_return(month, tickers)
    # labels = labels[['ticker', 'date', "time", f'ret_{ret_name}']]
    # # del null return data
    # labels = labels.dropna()
    # df_signal = labels.merge(df_signal, on=['ticker', 'date', 'time']).dropna()

    # backtest by ticker
    report = []
    for ticker in tickers:
        # get data of per ticker
        train_proba_ticker = df_train_proba.query("ticker==@ticker")["proba"].values
        df_ticker = df_signal.query("ticker==@ticker")
        y_test = df_ticker['ret_{}'.format(ret_name)].values
        proba = df_ticker["proba"].values
        # compute bound
        up_bound = np.percentile(train_proba_ticker, 100 - pct_num[ret_name])
        down_bound = np.percentile(1-train_proba_ticker, 100 - pct_num[ret_name])
        # compute signal
        signal = np.zeros(len(df_ticker))
        signal[proba >= up_bound] = 1
        signal[1-proba >= down_bound] = -1
        # evaluate signal
        y_pred_label = signal
        results = eval_result(y_test, y_pred_label)
        # append to results
        results.insert(0, ticker)
        results.insert(1, month)
        results.insert(2, up_bound)
        results.insert(3, down_bound)
        report.append(results)
    # save to ./reports
    report = pd.DataFrame(report, columns=["ticker", "test_month", "up_bound", "down_bound", "up_winrate", "down_winrate", "up_ret", "down_ret", "up_pct", "down_pct", "weighted_return", "total_sample", "zero_rate", "abs_ret"])
    save_path = os.path.join(report_folder, report_name)
    print(f"Report has been saved to {save_path}")
    report.to_csv(save_path, index=False)

def ensemble_avg_weight(ret_name, month, ensemble_name):
    # read test signal
    expr_name = f"ddb_factor_all_new_batch1_hs300_highprice_lgbm_{ret_name}"
    batch1_signal = merge_signal(expr_name, ret_name, month)
    expr_name = f"ddb_factor_all_new_batch2_hs300_highprice_lgbm_{ret_name}"
    batch2_signal = merge_signal(expr_name, ret_name, month)
    expr_name = f"ddb_factor_all_new_batch3_hs300_highprice_lgbm_{ret_name}"
    batch3_signal = merge_signal(expr_name, ret_name, month)

    # read train proba
    expr_name = f"ddb_factor_all_new_batch1_hs300_highprice_lgbm_{ret_name}"
    batch1_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    expr_name = f"ddb_factor_all_new_batch2_hs300_highprice_lgbm_{ret_name}"
    batch2_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    expr_name = f"ddb_factor_all_new_batch3_hs300_highprice_lgbm_{ret_name}"
    batch3_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")

    train_proba = (batch1_train_proba["proba"].values + batch2_train_proba["proba"].values + batch3_train_proba["proba"].values) / 3
    df_train_proba = pd.DataFrame({"ticker": batch1_train_proba.ticker.values, "proba": train_proba})

    # create signal dataframe
    proba = (batch1_signal["proba"].values + batch2_signal["proba"].values + batch3_signal["proba"].values) / 3
    ticker = batch1_signal.ticker
    date = batch1_signal.date
    time = batch1_signal.time
    df_signal = pd.DataFrame({"ticker": ticker, "date": date, "time": time, "proba":proba, f"ret_{ret_name}": batch1_signal[f"ret_{ret_name}"]})
    # compute metrics and save report
    compute_metrics(df_signal, df_train_proba, ensemble_name, ret_name, month)


def ensemble_with_all_avg_weight(ret_name, month, ensemble_name):
    # read signal
    expr_name = f"ddb_factor_all_new_hs300_highprice_lgbm_{ret_name}"
    all_new_signal = merge_signal(expr_name, ret_name, month)
    expr_name = f"ddb_factor_all_new_batch1_hs300_highprice_lgbm_{ret_name}"
    batch1_signal = merge_signal(expr_name, ret_name, month)
    expr_name = f"ddb_factor_all_new_batch2_hs300_highprice_lgbm_{ret_name}"
    batch2_signal = merge_signal(expr_name, ret_name, month)
    expr_name = f"ddb_factor_all_new_batch3_hs300_highprice_lgbm_{ret_name}"
    batch3_signal = merge_signal(expr_name, ret_name, month)
    assert  len(batch3_signal)==len(batch2_signal) and len(batch1_signal)==len(batch3_signal) and len(batch1_signal)==len(all_new_signal)

    # read train proba
    expr_name = f"ddb_factor_all_new_batch1_hs300_highprice_lgbm_{ret_name}"
    batch1_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    expr_name = f"ddb_factor_all_new_batch2_hs300_highprice_lgbm_{ret_name}"
    batch2_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    expr_name = f"ddb_factor_all_new_batch3_hs300_highprice_lgbm_{ret_name}"
    batch3_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    expr_name = f"ddb_factor_all_new_hs300_highprice_lgbm_{ret_name}"
    all_new_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    assert len(batch1_train_proba)==len(batch2_train_proba) and len(batch1_train_proba)==len(batch3_train_proba) and len(batch1_train_proba)==len(all_new_train_proba)


    # ensemble signal
    train_proba = (batch1_train_proba["proba"].values + batch2_train_proba["proba"].values +
                   batch3_train_proba["proba"].values) / 4 + 1/4 * all_new_train_proba["proba"].values
    df_train_proba = pd.DataFrame({"ticker": batch1_train_proba.ticker.values, "proba": train_proba})

    # create signal dataframe
    proba = 1 / 4 * all_new_signal["proba"].values + (batch1_signal["proba"].values + batch2_signal["proba"].values + batch3_signal["proba"].values) / 4
    ticker = batch1_signal.ticker
    date = batch1_signal.date
    time = batch1_signal.time
    df_signal = pd.DataFrame({"ticker": ticker, "date": date, "time": time, "proba": proba,
                              f"ret_{ret_name}": batch1_signal[f"ret_{ret_name}"]})
    # compute metrics and save report
    compute_metrics(df_signal, df_train_proba, ensemble_name, ret_name, month)


def ensemble_with_all_weight_3_1_1_1(ret_name, month, ensemble_name):
    # read signal
    expr_name = f"ddb_factor_all_new_hs300_highprice_lgbm_{ret_name}"
    all_new_signal = merge_signal(expr_name, ret_name, month)
    expr_name = f"ddb_factor_all_new_batch1_hs300_highprice_lgbm_{ret_name}"
    batch1_signal = merge_signal(expr_name, ret_name, month)
    expr_name = f"ddb_factor_all_new_batch2_hs300_highprice_lgbm_{ret_name}"
    batch2_signal = merge_signal(expr_name, ret_name, month)
    expr_name = f"ddb_factor_all_new_batch3_hs300_highprice_lgbm_{ret_name}"
    batch3_signal = merge_signal(expr_name, ret_name, month)
    assert  len(batch3_signal)==len(batch2_signal) and len(batch1_signal)==len(batch3_signal)

    # read train proba
    expr_name = f"ddb_factor_all_new_batch1_hs300_highprice_lgbm_{ret_name}"
    batch1_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    expr_name = f"ddb_factor_all_new_batch2_hs300_highprice_lgbm_{ret_name}"
    batch2_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    expr_name = f"ddb_factor_all_new_batch3_hs300_highprice_lgbm_{ret_name}"
    batch3_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    expr_name = f"ddb_factor_all_new_hs300_highprice_lgbm_{ret_name}"
    all_new_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    assert len(batch1_train_proba)==len(batch2_train_proba) and len(batch1_train_proba)==len(batch3_train_proba) and len(batch1_train_proba)==len(all_new_train_proba)


    # ensemble signal
    train_proba = (batch1_train_proba["proba"].values + batch2_train_proba["proba"].values +
                   batch3_train_proba["proba"].values) / 6 + 1/2 * all_new_train_proba["proba"].values
    df_train_proba = pd.DataFrame({"ticker": batch1_train_proba.ticker.values, "proba": train_proba})

    # create signal dataframe
    proba = 1 / 2 * all_new_signal["proba"].values + (batch1_signal["proba"].values + batch2_signal["proba"].values + batch3_signal["proba"].values) / 6
    ticker = batch1_signal.ticker
    date = batch1_signal.date
    time = batch1_signal.time
    df_signal = pd.DataFrame({"ticker": ticker, "date": date, "time": time, "proba": proba,
                              f"ret_{ret_name}": batch1_signal[f"ret_{ret_name}"]})
    # compute metrics and save report
    compute_metrics(df_signal, df_train_proba, ensemble_name, ret_name, month)


def ensemble_with_batch1_all_avg_weight(ret_name, month, ensemble_name):
    # read signal
    expr_name = f"ddb_factor_all_new_hs300_highprice_lgbm_{ret_name}"
    all_new_signal = merge_signal(expr_name, ret_name, month)
    expr_name = f"ddb_factor_all_new_batch1_hs300_highprice_lgbm_{ret_name}"
    batch1_signal = merge_signal(expr_name, ret_name, month)
    assert  len(batch1_signal)==len(all_new_signal)

    # read train proba
    expr_name = f"ddb_factor_all_new_batch1_hs300_highprice_lgbm_{ret_name}"
    batch1_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    expr_name = f"ddb_factor_all_new_hs300_highprice_lgbm_{ret_name}"
    all_new_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    assert len(batch1_train_proba)==len(all_new_train_proba)


    # ensemble signal
    train_proba = 1/2 *batch1_train_proba["proba"].values + 1/2 * all_new_train_proba["proba"].values
    df_train_proba = pd.DataFrame({"ticker": batch1_train_proba.ticker.values, "proba": train_proba})

    # create signal dataframe
    proba = 1 / 2 * all_new_signal["proba"].values + 1 / 2 * batch1_signal["proba"].values
    ticker = batch1_signal.ticker
    date = batch1_signal.date
    time = batch1_signal.time
    df_signal = pd.DataFrame({"ticker": ticker, "date": date, "time": time, "proba": proba,
                              f"ret_{ret_name}": batch1_signal[f"ret_{ret_name}"]})
    # compute metrics and save report
    compute_metrics(df_signal, df_train_proba, ensemble_name, ret_name, month)


def ensemble_with_batch2_all_avg_weight(ret_name, month, ensemble_name):
    # read signal
    expr_name = f"ddb_factor_all_new_hs300_highprice_lgbm_{ret_name}"
    all_new_signal = merge_signal(expr_name, ret_name, month)
    expr_name = f"ddb_factor_all_new_batch2_hs300_highprice_lgbm_{ret_name}"
    batch2_signal = merge_signal(expr_name, ret_name, month)
    assert  len(batch2_signal)==len(all_new_signal)

    # read train proba
    expr_name = f"ddb_factor_all_new_batch2_hs300_highprice_lgbm_{ret_name}"
    batch2_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    expr_name = f"ddb_factor_all_new_hs300_highprice_lgbm_{ret_name}"
    all_new_train_proba = read_train_signal_from_csv(f"../experiments/{expr_name}/{month}/train_signal")
    assert len(batch2_train_proba)==len(all_new_train_proba)


    # ensemble signal
    train_proba = 1/2 *batch2_train_proba["proba"].values + 1/2 * all_new_train_proba["proba"].values
    df_train_proba = pd.DataFrame({"ticker": batch2_train_proba.ticker.values, "proba": train_proba})

    # create signal dataframe
    proba = 1 / 2 * all_new_signal["proba"].values + 1 / 2 * batch2_signal["proba"].values
    ticker = batch2_signal.ticker
    date = batch2_signal.date
    time = batch2_signal.time
    df_signal = pd.DataFrame({"ticker": ticker, "date": date, "time": time, "proba": proba,
                              f"ret_{ret_name}": batch2_signal[f"ret_{ret_name}"]})
    # compute metrics and save report
    compute_metrics(df_signal, df_train_proba, ensemble_name, ret_name, month)


def analysis_report(ensemble_name, month_list, ret_windows, svg_folder="./ensemble_summary"):
    summary = []
    ret_windows = ["15s", "60s", "120s", "300s"]
    cols = ["test_month", "up_bound", "down_bound", "up_winrate", "down_winrate", "up_ret", "down_ret", "up_pct", "down_pct", "weighted_return", "total_sample", "zero_rate", "abs_ret"]
    for ret_window in ret_windows:
        for month in month_list:
            report_folder, report_name = "./reports", f"report_{ensemble_name}_{month}_{ret_window}.csv"
            report = pd.read_csv(os.path.join(report_folder, report_name))
            mean_report = report[cols].mean().to_frame().T
            mean_report.insert(0, 'ret_window', ret_window)
            summary.append(mean_report)
    summary = pd.concat(summary)
    if not os.path.exists(svg_folder):
        os.makedirs(svg_folder)
    svg_path = os.path.join(svg_folder, f"summary_{ensemble_name}_{month_list[0]}_{month_list[-1]}.csv")
    summary.to_csv(svg_path, index=False)
    print(f"Summary has been saved to {os.getcwd()}/{svg_path}")

if __name__ == "__main__":
    ensemble_func_name = "ensemble_with_all_avg_weight"
    ensemble_name = ensemble_func_name
    months = [202404, 202405, 202406, 202407, 202408, 202409, 202410, 202411, 202412]
    ret_windows = ["15s", "60s", "120s", "300s"]
    n_jobs = multiprocessing.cpu_count()

    # run evaluation by multiprocessing
    params = [(ret_name, month, ensemble_name)
              for month in months
              for ret_name in ret_windows]
    with Pool(processes=n_jobs) as pool:
        pool.starmap(globals()[ensemble_func_name], params)

    analysis_report(ensemble_func_name, ret_windows=ret_windows, month_list=months)











