import argparse
import glob
import os
import os.path as osp
import sys

import numpy as np
import pandas as pd

ROOT_DIR = osp.dirname(osp.dirname(osp.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.ddb import read_ddb_return


TIME_KEYS = ["ticker", "date", "time"]


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate long-term signals with long/short returns.")
    parser.add_argument("--signal-path", type=str, required=True, help="Signal csv file or folder containing signal csv files.")
    parser.add_argument("--month", type=int, required=True, help="Month in YYYYMM format.")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for evaluation reports.")
    parser.add_argument("--pool", type=str, default="hs300", help="Stock pool suffix used by return table.")
    parser.add_argument("--ret-db", type=str, default="dfs://DDB_Returns", help="DolphinDB return database name.")
    parser.add_argument("--ret-table", type=str, default=None, help="Override return table name. Defaults to Returns_long_short_{pool}.")
    parser.add_argument("--long-ret-col", type=str, default="long_ret", help="Signal long return column name.")
    parser.add_argument("--short-ret-col", type=str, default="short_ret", help="Signal short return column name.")
    parser.add_argument("--ddb-long-ret-col", type=str, default="long_ret_10min", help="Return-table long return column name when merge is needed.")
    parser.add_argument("--ddb-short-ret-col", type=str, default="short_ret_10min", help="Return-table short return column name when merge is needed.")
    parser.add_argument("--save-daily", action="store_true", help="Whether to save daily aggregated summary.")
    return parser.parse_args()


def read_signal_from_path(signal_path):
    if signal_path.lower().endswith(".csv"):
        signal = pd.read_csv(signal_path)
        if signal.empty:
            raise ValueError(f"Signal file is empty: {signal_path}")
        return signal

    if not osp.isdir(signal_path):
        raise FileNotFoundError(f"Signal path does not exist: {signal_path}")

    csv_files = sorted(glob.glob(osp.join(signal_path, "*.csv")))
    if len(csv_files) == 0:
        raise FileNotFoundError(f"There are no signal csv files in {signal_path}")

    signals = [pd.read_csv(path) for path in csv_files]
    signals = [df for df in signals if not df.empty]
    if len(signals) == 0:
        raise ValueError(f"All signal csv files are empty in {signal_path}")
    return pd.concat(signals, ignore_index=True)


def ensure_return_columns(signal, args):
    if args.long_ret_col in signal.columns and args.short_ret_col in signal.columns:
        return signal

    ret_table_name = args.ret_table or f"Returns_long_short_{args.pool}"
    tickers = tuple(sorted(signal["ticker"].astype(str).unique()))
    returns = read_ddb_return(args.ret_db, ret_table_name, args.month, tickers)
    keep_cols = TIME_KEYS + [args.ddb_long_ret_col, args.ddb_short_ret_col]
    missing_cols = [col for col in keep_cols if col not in returns.columns]
    if missing_cols:
        raise KeyError(f"Missing return columns in [{ret_table_name}]: {missing_cols}")

    returns = returns[keep_cols].copy()
    returns = returns.rename(
        columns={
            args.ddb_long_ret_col: args.long_ret_col,
            args.ddb_short_ret_col: args.short_ret_col,
        }
    )
    merged = signal.merge(returns, on=TIME_KEYS, how="inner")
    return merged


def safe_mean(arr):
    if len(arr) == 0:
        return np.nan
    return float(np.mean(arr))


def compute_long_term_metrics(df):
    signal_values = df["signal"].to_numpy()
    long_ret = df["long_ret"].to_numpy()
    short_ret = df["short_ret"].to_numpy()

    up_idx = signal_values == 1
    down_idx = signal_values == -1
    up_non_zero_idx = up_idx & (long_ret != 0)
    down_non_zero_idx = down_idx & (short_ret != 0)

    up_trade_num = int(np.sum(up_idx))
    down_trade_num = int(np.sum(down_idx))
    total_sample = len(df)

    up_mean_ret = safe_mean(long_ret[up_idx])
    down_mean_ret = safe_mean(short_ret[down_idx])
    up_win_rate = safe_mean(long_ret[up_non_zero_idx] > 0)
    down_win_rate = safe_mean(short_ret[down_non_zero_idx] > 0)

    combined_selected_returns = np.concatenate([long_ret[up_idx], short_ret[down_idx]])
    weighted_return = 0.0
    if total_sample > 0:
        weighted_return = (
            safe_mean(long_ret[up_idx]) * (up_trade_num / total_sample)
            + safe_mean(short_ret[down_idx]) * (down_trade_num / total_sample)
        )

    metrics = {
        "up_win_rate": up_win_rate,
        "down_win_rate": down_win_rate,
        "up_mean_ret": up_mean_ret * 1e4 if not np.isnan(up_mean_ret) else np.nan,
        "down_mean_ret": down_mean_ret * 1e4 if not np.isnan(down_mean_ret) else np.nan,
        "up_signal_rate": up_trade_num / total_sample if total_sample > 0 else np.nan,
        "down_signal_rate": down_trade_num / total_sample if total_sample > 0 else np.nan,
        "up_trade_num": up_trade_num,
        "down_trade_num": down_trade_num,
        "weighted_return": weighted_return * 1e4 if not np.isnan(weighted_return) else np.nan,
        "total_sample": total_sample,
        "zero_signal_rate": float(np.mean(signal_values == 0)) if total_sample > 0 else np.nan,
        "selected_abs_ret": safe_mean(np.abs(combined_selected_returns)) * 1e4 if len(combined_selected_returns) > 0 else np.nan,
        "selected_avg_ret": safe_mean(combined_selected_returns) * 1e4 if len(combined_selected_returns) > 0 else np.nan,
    }
    return metrics


def build_ticker_report(signal):
    report_rows = []
    for ticker, df_ticker in signal.groupby("ticker", sort=True):
        metrics = compute_long_term_metrics(df_ticker)
        first_row = df_ticker.iloc[0]
        report_rows.append(
            {
                "ticker": ticker,
                "month": int(str(first_row["date"])[:6]),
                "first_date": int(first_row["date"]),
                "up_bound": first_row.get("up_bound", np.nan),
                "down_bound": first_row.get("down_bound", np.nan),
                **metrics,
            }
        )
    return pd.DataFrame(report_rows)


def build_daily_summary(signal):
    rows = []
    for test_date, df_date in signal.groupby("date", sort=True):
        metrics = compute_long_term_metrics(df_date)
        rows.append({"date": int(test_date), **metrics})
    return pd.DataFrame(rows)


def build_overall_summary(signal):
    metrics = compute_long_term_metrics(signal)
    unique_tickers = signal["ticker"].nunique()
    unique_dates = signal["date"].nunique()
    return pd.DataFrame(
        [
            {
                "month": int(str(signal["date"].iloc[0])[:6]),
                "ticker_num": unique_tickers,
                "date_num": unique_dates,
                **metrics,
            }
        ]
    )


def save_outputs(signal, ticker_report, overall_summary, daily_summary, output_dir, result_name, save_daily):
    os.makedirs(output_dir, exist_ok=True)
    signal_output_path = osp.join(output_dir, f"{result_name}_merged_signals.csv")
    ticker_report_path = osp.join(output_dir, f"{result_name}_ticker_report.csv")
    overall_summary_path = osp.join(output_dir, f"{result_name}_overall_summary.csv")

    signal.to_csv(signal_output_path, index=False)
    ticker_report.to_csv(ticker_report_path, index=False)
    overall_summary.to_csv(overall_summary_path, index=False)

    print(f"Merged signals saved at {signal_output_path}")
    print(f"Ticker report saved at {ticker_report_path}")
    print(f"Overall summary saved at {overall_summary_path}")

    if save_daily and daily_summary is not None:
        daily_summary_path = osp.join(output_dir, f"{result_name}_daily_summary.csv")
        daily_summary.to_csv(daily_summary_path, index=False)
        print(f"Daily summary saved at {daily_summary_path}")


def main():
    args = parse_args()
    signal = read_signal_from_path(args.signal_path)
    signal = ensure_return_columns(signal, args)
    signal["ticker"] = signal["ticker"].astype(str)
    signal["date"] = signal["date"].astype(int)
    signal["time"] = signal["time"].astype(int)
    signal = signal.dropna(subset=["signal", args.long_ret_col, args.short_ret_col]).copy()
    signal = signal.rename(columns={args.long_ret_col: "long_ret", args.short_ret_col: "short_ret"})

    ticker_report = build_ticker_report(signal)
    overall_summary = build_overall_summary(signal)
    daily_summary = build_daily_summary(signal) if args.save_daily else None

    result_name = osp.basename(osp.normpath(args.signal_path))
    output_dir = args.output_dir or osp.join("signal_evaluation", "outputs", result_name)
    save_outputs(signal, ticker_report, overall_summary, daily_summary, output_dir, result_name, args.save_daily)


if __name__ == "__main__":
    main()
