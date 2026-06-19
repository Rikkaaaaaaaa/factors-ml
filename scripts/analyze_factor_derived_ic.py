import argparse
import multiprocessing as mp
import os
import os.path as osp
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

import dolphindb as ddb
import dolphindb.settings as ddb_keys
import numpy as np
import pandas as pd
import pymysql
import yaml
from scipy.stats import rankdata

from dataset.factor_name_long_term import build_factor_name_long_term, build_factor_table_long_term


DEFAULT_FACTORS = [
    "ma_close_ret_10",
    "bulk_buy_sell_diff_15s",
    "order_diff_10_15s",
    "ma_close_ret_5",
    "ma_mid_ret_2_10",
    "active_buy_sell_diff_15s",
    "mid_ret_15s",
    "mkt_bulk_active_buy_sell_diff_15s",
    "net_bid_amt_delta_15s",
    "indus_order_diff_1_15s",
    "book_pressure_15s",
    "ma_close_ret_1",
    "mkt_book_pressure_15s",
    "ma_close_ret_2_10",
    "mkt_net_bid_amt_delta_15s",
    "indus_bulk_active_buy_sell_diff_15s",
    "close_ret_15s",
    "book_pressure_delta_15s",
    "indus_close_ret_15s",
    "ma_mid_ret_2_5",
    "indus_mid_ret_15s",
    "indus_order_diff_10_15s",
    "mkt_lower_ask_amt_15s",
    "indus_active_buy_sell_diff_15s",
    "lower_ask_amt_15s",
    "bulk_active_buy_sell_diff_15s",
    "ma_close_ret_2",
    "indus_cancel_diff_10_15s",
    "mkt_close_ret_15s",
    "indus_book_pressure_15s",
    "mkt_active_buy_sell_diff_15s",
    "ma_mid_ret_2",
    "mid_mmt_route_5_5",
    "ma_mid_ret_5",
    "mkt_higher_bid_amt_15s",
    "indus_net_bid_amt_delta_15s",
    "order_diff_1_15s",
    "mid_mmt_route_10_10",
    "indus_book_pressure_delta_15s",
    "ma_close_ret_2_5",
    "ma_mid_ret_10",
    "mid_ret_skew_10",
    "mkt_order_diff_10_15s",
    "indus_lower_ask_amt_15s",
    "higher_bid_amt_15s",
    "indus_higher_bid_amt_15s",
    "ma_mid_ret_1",
    "cancel_diff_10_15s",
]

DEFAULT_RETURN_COLS = [
    "long_ret_10min",
    "long_ret_20min",
    "long_ret_30min",
]

WINDOW_CONFIG = {
    "1m": 4,
    "5m": 20,
    "10m": 40,
    "30m": 120,
}

TIME_KEYS = ["ticker", "date", "time"]
WORKER_RETURN_DF = None
WORKER_RETURN_COLS = None
WORKER_MIN_CS = None
WORKER_SAVE_DETAIL = None


class DDBConnector:
    def __init__(self, config):
        self.config = config
        self.session = ddb.session(
            protocol=ddb_keys.PROTOCOL_DDB,
            compress=True,
            keepAliveTime=12000,
        )
        self.session.connect(
            host=config["server"],
            port=config["port"],
            userid=config["userName"],
            password=config["userKey"],
            reconnect=True,
        )
        self.session.setTimeout(config.get("timeout", 3600))

    def run(self, query, priority=9):
        return self.session.run(query, priority=priority)

    def close(self):
        self.session.close()


def parse_args():
    from pathlib import Path

    root_path = str(Path(__file__).resolve().parents[1])
    parser = argparse.ArgumentParser(description="Analyze derived factor IC / rankIC on long-short returns.")
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(root_path, "scripts/configs/derived_factor_ic_demo.yaml"),
        help="Path to YAML config.",
    )
    parser.add_argument("--month", type=int, default=None, help="Override month in YYYYMM format.")
    parser.add_argument("--date", type=int, default=None, help="Optional single-date filter in YYYYMMDD format.")
    parser.add_argument("--pool", type=str, default=None, help="Override stock pool, such as hs300 / zz500.")
    parser.add_argument("--save-detail", action="store_true", help="Whether to save per-ticker IC / rankIC details.")
    return parser.parse_args()


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as file_obj:
        return yaml.safe_load(file_obj)


def build_output_dir(config):
    output_dir = config.get("output_dir")
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_tag = str(config["date"]) if config.get("date") else str(config["month"])
    output_dir = osp.join("experiments", "derived_factor_ic", f'{config["pool"]}_{date_tag}_{timestamp}')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def to_ddb_month_literal(month):
    month_str = str(month)
    return f"{month_str[:4]}.{month_str[4:]}M"


def to_ddb_date_literal(date_int):
    date_str = str(date_int)
    return f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:8]}"


def to_mysql_conn_str(mysql_config, database=None):
    db_name = database or mysql_config.get("database", "strategy")
    return (
        f'mysql://{mysql_config["user"]}:{mysql_config["password"]}'
        f'@{mysql_config["host"]}:{mysql_config["port"]}/{db_name}'
    )


def read_mysql(query, mysql_config, database=None):
    db_name = database or mysql_config.get("database", "strategy")
    conn = pymysql.connect(
        host=mysql_config["host"],
        port=mysql_config["port"],
        user=mysql_config["user"],
        password=mysql_config["password"],
        database=db_name,
        charset="utf8",
    )
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()


def get_pool_tickers_from_mysql(config):
    mysql_config = config["mysql"]
    pool = config["pool"]
    month = config["month"]
    indus_suffix = config.get("indus_table_suffix", "")
    avg_price = config.get("avg_price", 10)
    price_name = config.get("price_name", "highprice")

    if indus_suffix:
        indus_suffix = f"_{indus_suffix}"

    indus_query = f"select ticker from static_data_industry_{pool}_history{indus_suffix} where test_month={month}"
    if price_name == "highprice":
        price_query = f"select ticker from static_data_price_{pool}_history where avg_price > {avg_price} and test_month={month}"
    else:
        price_query = f"select ticker from static_data_price_{pool}_history where avg_price <= {avg_price} and test_month={month}"

    indus_table = read_mysql(indus_query, mysql_config)
    price_table = read_mysql(price_query, mysql_config)
    tickers = sorted(set(indus_table["ticker"]) & set(price_table["ticker"]))
    if len(tickers) == 0:
        raise ValueError(f"No tickers found from MySQL for pool [{pool}] in month [{month}]")
    return tickers


def get_tickers_from_return_table(config, connector):
    month_literal = to_ddb_month_literal(config["month"])
    return_table_name = config["return_table_name"]
    query = (
        f'select distinct(securityCode) as ticker from loadTable("dfs://DDB_Returns", "{return_table_name}") '
        f"where month(time)={month_literal}"
    )
    if config.get("date") is not None:
        query += f", date(time)={to_ddb_date_literal(config['date'])}"
    tickers = connector.run(query)["ticker"].tolist()
    tickers = sorted(set(tickers))
    if len(tickers) == 0:
        raise ValueError(f"No tickers found in return table [{return_table_name}]")
    return tickers


def get_tickers(config, connector):
    ticker_source = config.get("ticker_source", "mysql")
    if ticker_source == "mysql":
        return get_pool_tickers_from_mysql(config)
    if ticker_source == "return_table":
        return get_tickers_from_return_table(config, connector)
    raise ValueError(f"Unsupported ticker_source: [{ticker_source}]")


def standardize_time_keys(df):
    df = df.copy()
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str)
    if "date" in df.columns:
        df["date"] = pd.to_numeric(df["date"], errors="coerce").astype("Int64").astype(np.int64)
    if "time" in df.columns:
        df["time"] = pd.to_numeric(df["time"], errors="coerce").astype("Int64").astype(np.int64)
    return df


def normalize_time_columns(df, source_time_col="time", ticker_col="securityCode"):
    df = df.copy()
    if ticker_col in df.columns:
        df = df.rename(columns={ticker_col: "ticker"})
    df.insert(0, "date", df[source_time_col].dt.strftime("%Y%m%d").astype("int64"))
    df["time"] = (
        df[source_time_col].dt.hour * 10000000
        + df[source_time_col].dt.minute * 100000
        + df[source_time_col].dt.second * 1000
        + df[source_time_col].dt.microsecond // 1000
    ).astype("int64")
    return standardize_time_keys(df)


def apply_trading_hours_filter(df, trading_hours):
    if trading_hours is None:
        return df[(df["time"] >= 94000000) & (df["time"] <= 145700000)].copy()

    am_mask = (df["time"] >= trading_hours["am_start_time"] * 1000) & (df["time"] <= trading_hours["am_end_time"] * 1000)
    pm_mask = (df["time"] >= trading_hours["pm_start_time"] * 1000) & (df["time"] <= trading_hours["pm_end_time"] * 1000)
    return df[am_mask | pm_mask].copy()


def sort_factor_frame(df):
    return df.sort_values(TIME_KEYS).reset_index(drop=True)


def read_ddb_factor_table(connector, data_base, table_name, month, tickers, trading_hours=None):
    month_literal = to_ddb_month_literal(month)
    if isinstance(trading_hours, dict):
        am_start_time = str(trading_hours["am_start_time"]).zfill(6)
        am_end_time = str(trading_hours["am_end_time"]).zfill(6)
        pm_start_time = str(trading_hours["pm_start_time"]).zfill(6)
        pm_end_time = str(trading_hours["pm_end_time"]).zfill(6)
        am_start_time = f'{am_start_time[:2]}:{am_start_time[2:4]}:{am_start_time[4:]}'
        am_end_time = f'{am_end_time[:2]}:{am_end_time[2:4]}:{am_end_time[4:]}'
        pm_start_time = f'{pm_start_time[:2]}:{pm_start_time[2:4]}:{pm_start_time[4:]}'
        pm_end_time = f'{pm_end_time[:2]}:{pm_end_time[2:4]}:{pm_end_time[4:]}'
    else:
        am_start_time, am_end_time = "09:40:00", "11:30:00"
        pm_start_time, pm_end_time = "13:00:00", "14:57:00"

    query = f"""
    factorTable = loadTable("{data_base}", "{table_name}")
    retTable = select * from factorTable where month(time)={month_literal}, securityCode in {tickers},
        {am_start_time}<=second(time)<={am_end_time} or {pm_start_time}<=second(time)<={pm_end_time}
    select factorValue from retTable pivot by time, securityCode, factorName
    """
    factor = connector.run(query)
    if factor.empty:
        return factor
    factor = normalize_time_columns(factor, source_time_col="time", ticker_col="securityCode")
    return factor


def load_factor_tables(config, connector, tickers):
    factor_tables = config["factor_tables"]
    factor_frames = []
    seen_columns = set(TIME_KEYS)
    ignored_non_factor_cols = {"limitFlag"}

    for factor_db, table_defs in factor_tables.items():
        for table_def in table_defs:
            if isinstance(table_def, dict):
                table_name = table_def.get("table_name")
                table_base = table_def.get("table")
            else:
                table_name = None
                table_base = table_def

            resolved_table_name = table_name or f"{table_base}_{config['pool']}"
            print(f"Loading factor table [{factor_db}.{resolved_table_name}]")
            factor = read_ddb_factor_table(
                connector=connector,
                data_base=factor_db,
                table_name=resolved_table_name,
                month=config["month"],
                tickers=tickers,
                trading_hours=config.get("trading_hours"),
            )
            if factor.empty:
                print(f"Warning: factor table [{resolved_table_name}] is empty, skip it.")
                continue
            factor = standardize_time_keys(factor)

            duplicate_cols = [
                col for col in factor.columns if col in seen_columns and col not in TIME_KEYS and col not in ignored_non_factor_cols
            ]
            if duplicate_cols:
                raise ValueError(f"Duplicate factor columns found across tables: {duplicate_cols}")
            seen_columns.update(
                [col for col in factor.columns if col not in TIME_KEYS and col not in ignored_non_factor_cols]
            )
            factor_frames.append(factor)

    if len(factor_frames) == 0:
        raise ValueError("No factor data loaded from any configured factor table.")

    merged_factor = standardize_time_keys(factor_frames[0])
    for factor in factor_frames[1:]:
        if "limitFlag" in factor.columns:
            factor = factor.drop(columns=["limitFlag"])
        factor = standardize_time_keys(factor)
        merged_factor = merged_factor.merge(factor, on=TIME_KEYS, how="inner")

    factor_cols = config["factors"]
    missing_factor_cols = [col for col in factor_cols if col not in merged_factor.columns]
    if missing_factor_cols:
        raise ValueError(f"Missing factor columns after table merge: {missing_factor_cols}")

    merged_factor = merged_factor[TIME_KEYS + factor_cols].copy()
    if config.get("date") is not None:
        merged_factor = merged_factor[merged_factor["date"] == config["date"]].copy()
    return merged_factor


def load_return_data(config, connector, tickers):
    month_literal = to_ddb_month_literal(config["month"])
    return_table_name = config["return_table_name"]
    query = f"""
    retTable = loadTable("dfs://DDB_Returns", "{return_table_name}")
    select * from retTable where month(time)={month_literal} and securityCode in {tickers}
    """
    ret = connector.run(query)
    if ret.empty:
        raise ValueError(f"No return data found in [{return_table_name}] for month [{config['month']}]")
    ret = normalize_time_columns(ret, source_time_col="time", ticker_col="securityCode")
    ret = standardize_time_keys(ret)
    ret = apply_trading_hours_filter(ret, config.get("trading_hours"))
    if config.get("date") is not None:
        ret = ret[ret["date"] == config["date"]].copy()
        if ret.empty:
            raise ValueError(f"No return data found on date [{config['date']}] in [{return_table_name}]")

    missing_return_cols = [col for col in config["return_cols"] if col not in ret.columns]
    if missing_return_cols:
        raise ValueError(f"Missing return columns in return table: {missing_return_cols}")
    return ret[TIME_KEYS + config["return_cols"]].copy()


def build_single_factor_features(factor_df, factor_col):
    factor_df = factor_df[TIME_KEYS + [factor_col]].copy()
    features = pd.DataFrame(index=factor_df.index)

    features[f"{factor_col}__current"] = factor_df[factor_col]

    result = pd.concat([factor_df[TIME_KEYS], features], axis=1)
    return result


def compute_feature_stats(derived_df, feature_cols):
    rows = []
    for feature_col in feature_cols:
        raw_factor, derived_tag = split_feature_name(feature_col)
        series = derived_df[feature_col]
        finite_series = series[np.isfinite(series.to_numpy(dtype=float, na_value=np.nan))]
        if len(finite_series) == 0:
            rows.append(
                {
                    "raw_factor": raw_factor,
                    "derived_tag": derived_tag,
                    "feature_name": feature_col,
                    "non_null_count": 0,
                    "mean": np.nan,
                    "std": np.nan,
                    "skew": np.nan,
                    "kurtosis": np.nan,
                    "min": np.nan,
                    "max": np.nan,
                }
            )
            continue
        rows.append(
            {
                "raw_factor": raw_factor,
                "derived_tag": derived_tag,
                "feature_name": feature_col,
                "non_null_count": int(finite_series.shape[0]),
                "mean": float(finite_series.mean()),
                "std": float(finite_series.std(ddof=1)) if finite_series.shape[0] > 1 else np.nan,
                "skew": float(finite_series.skew()),
                "kurtosis": float(finite_series.kurt()),
                "min": float(finite_series.min()),
                "max": float(finite_series.max()),
            }
        )
    return pd.DataFrame(rows)


def split_feature_name(feature_name):
    raw_factor, derived_tag = feature_name.split("__", 1)
    return raw_factor, derived_tag


def fast_pearson_corr(x, y):
    x_mean = x.mean()
    y_mean = y.mean()
    x_centered = x - x_mean
    y_centered = y - y_mean
    denominator = np.sqrt(np.sum(x_centered * x_centered) * np.sum(y_centered * y_centered))
    if denominator == 0:
        return np.nan
    return float(np.sum(x_centered * y_centered) / denominator)


def compute_factor_metric_rows(merged_df, feature_cols, return_cols, min_time_series_size, save_detail):
    metric_rows = []
    aggregations = {}
    grouped = merged_df.groupby(["ticker"], sort=True)

    for ticker_value, frame in grouped:
        feature_matrix = frame[feature_cols].to_numpy(dtype=float, copy=False)
        return_matrix = frame[return_cols].to_numpy(dtype=float, copy=False)

        for feature_idx, feature_col in enumerate(feature_cols):
            x_raw = feature_matrix[:, feature_idx]
            raw_factor, derived_tag = split_feature_name(feature_col)

            for return_idx, ret_col in enumerate(return_cols):
                y_raw = return_matrix[:, return_idx]
                valid_mask = np.isfinite(x_raw) & np.isfinite(y_raw)
                sample_size = int(valid_mask.sum())
                if sample_size < min_time_series_size:
                    continue

                x_valid = x_raw[valid_mask]
                y_valid = y_raw[valid_mask]

                ic_value = fast_pearson_corr(x_valid, y_valid)
                if not np.isnan(ic_value):
                    key = (raw_factor, derived_tag, feature_col, ret_col, "ic")
                    aggregations.setdefault(key, []).append((ic_value, sample_size))
                    if save_detail:
                        metric_rows.append(
                            {
                                "raw_factor": raw_factor,
                                "derived_tag": derived_tag,
                                "feature_name": feature_col,
                                "ret_col": ret_col,
                                "metric": "ic",
                                "ticker": ticker_value,
                                "value": ic_value,
                                "n": sample_size,
                            }
                        )

                rank_ic_value = fast_pearson_corr(rankdata(x_valid), rankdata(y_valid))
                if not np.isnan(rank_ic_value):
                    key = (raw_factor, derived_tag, feature_col, ret_col, "rank_ic")
                    aggregations.setdefault(key, []).append((rank_ic_value, sample_size))
                    if save_detail:
                        metric_rows.append(
                            {
                                "raw_factor": raw_factor,
                                "derived_tag": derived_tag,
                                "feature_name": feature_col,
                                "ret_col": ret_col,
                                "metric": "rank_ic",
                                "ticker": ticker_value,
                                "value": rank_ic_value,
                                "n": sample_size,
                            }
                        )

    summary_rows = []
    for key, values in aggregations.items():
        raw_factor, derived_tag, feature_name, ret_col, metric = key
        corr_values = np.array([item[0] for item in values], dtype=float)
        sample_sizes = np.array([item[1] for item in values], dtype=float)
        std_value = corr_values.std(ddof=1) if len(corr_values) > 1 else np.nan
        mean_value = corr_values.mean()
        summary_rows.append(
            {
                "raw_factor": raw_factor,
                "derived_tag": derived_tag,
                "feature_name": feature_name,
                "ret_col": ret_col,
                "metric": metric,
                "mean_value": mean_value,
                "std_value": std_value,
                "metric_ir": mean_value / std_value if std_value not in [0, np.nan] and not np.isnan(std_value) else np.nan,
                "abs_mean_value": np.abs(corr_values).mean(),
                "n_tickers": len(corr_values),
                "avg_time_series_size": sample_sizes.mean(),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    detail_df = pd.DataFrame(metric_rows) if save_detail and len(metric_rows) > 0 else pd.DataFrame()
    return summary_df, detail_df


def init_worker(return_df, return_cols, min_time_series_size, save_detail):
    global WORKER_RETURN_DF, WORKER_RETURN_COLS, WORKER_MIN_CS, WORKER_SAVE_DETAIL
    WORKER_RETURN_DF = return_df
    WORKER_RETURN_COLS = return_cols
    WORKER_MIN_CS = min_time_series_size
    WORKER_SAVE_DETAIL = save_detail


def analyze_single_factor_task(task):
    factor_slice_df, factor_col = task
    derived_df = build_single_factor_features(factor_slice_df, factor_col)
    merged = derived_df.merge(WORKER_RETURN_DF, on=TIME_KEYS, how="inner")
    feature_cols = [col for col in derived_df.columns if col not in TIME_KEYS]
    stats_df = compute_feature_stats(derived_df, feature_cols)
    if merged.empty:
        return factor_col, pd.DataFrame(), pd.DataFrame(), stats_df

    summary_df, detail_df = compute_factor_metric_rows(
        merged_df=merged,
        feature_cols=feature_cols,
        return_cols=WORKER_RETURN_COLS,
        min_time_series_size=WORKER_MIN_CS,
        save_detail=WORKER_SAVE_DETAIL,
    )
    return factor_col, summary_df, detail_df, stats_df


def summarize_metric_rows(metric_rows):
    if len(metric_rows) == 0:
        return pd.DataFrame(
            columns=[
                "raw_factor",
                "derived_tag",
                "feature_name",
                "ret_col",
                "metric",
                "mean_value",
                "std_value",
                "metric_ir",
                "abs_mean_value",
                "n_tickers",
                "avg_time_series_size",
            ]
        )

    detail_df = pd.DataFrame(metric_rows)
    summary = (
        detail_df.groupby(["raw_factor", "derived_tag", "feature_name", "ret_col", "metric"], as_index=False)
        .agg(
            mean_value=("value", "mean"),
            std_value=("value", "std"),
            abs_mean_value=("value", lambda x: np.abs(x).mean()),
            n_tickers=("value", "size"),
            avg_time_series_size=("n", "mean"),
        )
    )
    summary["metric_ir"] = summary["mean_value"] / summary["std_value"].replace(0, np.nan)
    return summary


def build_pivot_tables(summary_df):
    if summary_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    value_pivot = summary_df.pivot_table(
        index=["raw_factor", "derived_tag", "feature_name"],
        columns=["ret_col", "metric"],
        values="mean_value",
        aggfunc="first",
    )
    ir_pivot = summary_df.pivot_table(
        index=["raw_factor", "derived_tag", "feature_name"],
        columns=["ret_col", "metric"],
        values="metric_ir",
        aggfunc="first",
    )

    value_pivot.columns = [f"{ret_col}__{metric}__mean" for ret_col, metric in value_pivot.columns]
    ir_pivot.columns = [f"{ret_col}__{metric}__ir" for ret_col, metric in ir_pivot.columns]
    pivot_df = value_pivot.join(ir_pivot, how="outer").reset_index()
    pivot_abs_df = summary_df.pivot_table(
        index=["raw_factor", "derived_tag", "feature_name"],
        columns=["ret_col", "metric"],
        values="abs_mean_value",
        aggfunc="first",
    )
    pivot_abs_df.columns = [f"{ret_col}__{metric}__abs_mean" for ret_col, metric in pivot_abs_df.columns]
    pivot_df = pivot_df.merge(pivot_abs_df.reset_index(), on=["raw_factor", "derived_tag", "feature_name"], how="left")
    return pivot_df, pivot_abs_df.reset_index()


def analyze_factor_ic(factor_df, return_df, factor_cols, return_cols, min_time_series_size, save_detail, n_jobs=1):
    summary_frames = []
    detail_frames = []
    stats_frames = []
    factor_df = sort_factor_frame(factor_df)
    tasks = [(factor_df[TIME_KEYS + [factor_col]].copy(), factor_col) for factor_col in factor_cols]

    if n_jobs <= 1:
        init_worker(return_df, return_cols, min_time_series_size, save_detail)
        for idx, task in enumerate(tasks, start=1):
            factor_col = task[1]
            print(f"[{idx}/{len(factor_cols)}] Building derived features for [{factor_col}]")
            _, factor_summary, factor_detail, factor_stats = analyze_single_factor_task(task)
            if not factor_summary.empty:
                summary_frames.append(factor_summary)
            if save_detail and not factor_detail.empty:
                detail_frames.append(factor_detail)
            if not factor_stats.empty:
                stats_frames.append(factor_stats)
    else:
        max_workers = min(n_jobs, len(tasks))
        print(f"Running factor analysis with [{max_workers}] worker processes")
        with ProcessPoolExecutor(
            max_workers=max_workers,
            initializer=init_worker,
            initargs=(return_df, return_cols, min_time_series_size, save_detail),
        ) as executor:
            future_map = {executor.submit(analyze_single_factor_task, task): task[1] for task in tasks}
            completed = 0
            for future in as_completed(future_map):
                factor_col = future_map[future]
                completed += 1
                print(f"[{completed}/{len(factor_cols)}] Finished [{factor_col}]")
                _, factor_summary, factor_detail, factor_stats = future.result()
                if not factor_summary.empty:
                    summary_frames.append(factor_summary)
                if save_detail and not factor_detail.empty:
                    detail_frames.append(factor_detail)
                if not factor_stats.empty:
                    stats_frames.append(factor_stats)

    summary_df = pd.concat(summary_frames, ignore_index=True) if summary_frames else pd.DataFrame()
    detail_df = pd.concat(detail_frames, ignore_index=True) if detail_frames else pd.DataFrame()
    stats_df = pd.concat(stats_frames, ignore_index=True) if stats_frames else pd.DataFrame()
    pivot_df, pivot_abs_df = build_pivot_tables(summary_df)
    return summary_df, detail_df, pivot_df, pivot_abs_df, stats_df


def save_outputs(output_dir, config, summary_df, detail_df, pivot_df, stats_df):
    month_tag = str(config["date"]) if config.get("date") else str(config["month"])
    summary_path = osp.join(output_dir, f"derived_factor_ic_summary_{month_tag}.csv")
    pivot_path = osp.join(output_dir, f"derived_factor_ic_pivot_{month_tag}.csv")
    stats_path = osp.join(output_dir, f"derived_factor_feature_stats_{month_tag}.csv")
    metadata_path = osp.join(output_dir, "run_metadata.yaml")

    with open(metadata_path, "w", encoding="utf-8") as file_obj:
        yaml.safe_dump(config, file_obj, sort_keys=False, allow_unicode=True)

    summary_df.to_csv(summary_path, index=False)
    pivot_df.to_csv(pivot_path, index=False)
    stats_df.to_csv(stats_path, index=False)
    print(f"Saved summary to [{summary_path}]")
    print(f"Saved pivot to [{pivot_path}]")
    print(f"Saved feature stats to [{stats_path}]")

    if not detail_df.empty:
        detail_path = osp.join(output_dir, f"derived_factor_ic_detail_{month_tag}.csv")
        detail_df.to_csv(detail_path, index=False)
        print(f"Saved detail to [{detail_path}]")


def build_runtime_config(args):
    raw_config = load_yaml(args.config)
    runtime = raw_config.copy()
    runtime["month"] = args.month if args.month is not None else raw_config["month"]
    runtime["date"] = args.date if args.date is not None else raw_config.get("date")
    runtime["pool"] = args.pool if args.pool is not None else raw_config["pool"]
    runtime["save_detail"] = args.save_detail or raw_config.get("save_detail", False)
    factor_groups = raw_config.get("factor_groups")
    if factor_groups is not None:
        runtime["factors"] = build_factor_name_long_term(factor_groups)
    else:
        runtime["factors"] = raw_config.get("factors", DEFAULT_FACTORS)
    factor_table_groups = raw_config.get("factor_table_groups")
    if factor_table_groups is not None:
        runtime["factor_tables"] = build_factor_table_long_term(factor_table_groups)
    else:
        runtime["factor_tables"] = raw_config["factor_tables"]
    runtime["return_cols"] = raw_config.get("return_cols", DEFAULT_RETURN_COLS)
    runtime["return_table_name"] = raw_config.get("return_table_name", f'Returns_long_short_{runtime["pool"]}')
    runtime["min_time_series_size"] = raw_config.get(
        "min_time_series_size",
        raw_config.get("min_cross_section_size", 30),
    )
    runtime["ticker_source"] = raw_config.get("ticker_source", "mysql")
    runtime["trading_hours"] = raw_config.get("trading_hours")
    runtime["n_jobs"] = raw_config.get("n_jobs", max(1, min(8, (os.cpu_count() or 2) - 1)))
    return runtime


def main():
    args = parse_args()
    config = build_runtime_config(args)
    output_dir = build_output_dir(config)

    connector = DDBConnector(config["ddb"])
    try:
        tickers = get_tickers(config, connector)
        print(f"Loaded [{len(tickers)}] tickers for pool [{config['pool']}]")

        factor_df = load_factor_tables(config, connector, tickers)
        return_df = load_return_data(config, connector, tickers)
    finally:
        connector.close()

    if factor_df.empty:
        raise ValueError("Factor dataframe is empty after loading.")
    if return_df.empty:
        raise ValueError("Return dataframe is empty after loading.")

    print(f"Factor rows: [{len(factor_df)}], Return rows: [{len(return_df)}]")
    summary_df, detail_df, pivot_df, _, stats_df = analyze_factor_ic(
        factor_df=factor_df,
        return_df=return_df,
        factor_cols=config["factors"],
        return_cols=config["return_cols"],
        min_time_series_size=config["min_time_series_size"],
        save_detail=config["save_detail"],
        n_jobs=config["n_jobs"],
    )

    if not summary_df.empty:
        summary_df = summary_df.sort_values(
            ["ret_col", "metric", "abs_mean_value", "raw_factor", "derived_tag"],
            ascending=[True, True, False, True, True],
        ).reset_index(drop=True)
        pivot_df = pivot_df.sort_values(["raw_factor", "derived_tag", "feature_name"]).reset_index(drop=True)
    else:
        print("No valid IC / rankIC rows were produced.")

    if not stats_df.empty:
        stats_df = stats_df.sort_values(["raw_factor", "derived_tag", "feature_name"]).reset_index(drop=True)

    save_outputs(output_dir, config, summary_df, detail_df, pivot_df, stats_df)


if __name__ == "__main__":
    main()
