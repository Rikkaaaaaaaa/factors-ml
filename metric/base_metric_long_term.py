import numpy as np
import pandas as pd

from metric.base_metric import compute_prob_bound


def compute_metric_long_term(opt, pre_prob, pre_prob_train, long_ret, short_ret, threshold=pd.DataFrame()):
    """
    Compute long-term backtest metrics where:
    - up signal performance is evaluated on long_ret
    - down signal performance is evaluated on short_ret
    """

    pct_num = [100 - opt['test']['threshold_pct'], 100 - opt['test']['threshold_pct']]
    class_num = opt['test'].setdefault('direction_num', 2)

    if len(pre_prob) == 0:
        summary = {
            "weighted_return": np.nan,
            "base_weighted_return": np.nan,
            "excess_weighted_return": np.nan,
            "up_win_rate": np.nan,
            "down_win_rate": np.nan,
            "up_base_win_rate": np.nan,
            "down_base_win_rate": np.nan,
            "up_win_rate_lift": np.nan,
            "down_win_rate_lift": np.nan,
            "up_beat_base_mean_rate": np.nan,
            "down_beat_base_mean_rate": np.nan,
            "up_mean_ret": np.nan,
            "down_mean_ret": np.nan,
            "up_base_mean_ret": np.nan,
            "down_base_mean_ret": np.nan,
            "up_excess_mean_ret": np.nan,
            "down_excess_mean_ret": np.nan,
            "up_lift_ratio": np.nan,
            "down_lift_ratio": np.nan,
            "up_signal_rate": np.nan,
            "down_signal_rate": np.nan,
            'up_bound': np.nan,
            "down_bound": np.nan,
            "up_trade_num": np.nan,
            "down_trade_num": np.nan,
            "zero_rate": np.nan,
            "total_sample": np.nan,
            "abs_ret": np.nan,
            "avg_ret": np.nan,
        }
        up_bound = compute_prob_bound(pre_prob_train, pct_num=pct_num[0], class_label=1, class_num=class_num)
        down_bound = compute_prob_bound(pre_prob_train, pct_num=pct_num[1], class_label=0, class_num=class_num)
        summary['up_bound'], summary['down_bound'] = up_bound, down_bound
        summary['total_sample'] = 0
        return summary

    if opt['mode'] == 'eval':
        up_bound = threshold['up_bound'].values[0]
        down_bound = threshold['down_bound'].values[0]
    else:
        up_bound = compute_prob_bound(pre_prob_train, pct_num=pct_num[0], class_label=1, class_num=class_num)
        down_bound = compute_prob_bound(pre_prob_train, pct_num=pct_num[1], class_label=0, class_num=class_num)

    up_selected_idx = get_selected_idx(pre_prob, up_bound, class_label=1, class_num=class_num)
    down_selected_idx = get_selected_idx(pre_prob, down_bound, class_label=0, class_num=class_num)

    up_non_zero_idx = up_selected_idx & (long_ret != 0)
    down_non_zero_idx = down_selected_idx & (short_ret != 0)

    up_trade_num = int(np.sum(up_selected_idx))
    down_trade_num = int(np.sum(down_selected_idx))
    total_sample = len(long_ret)
    up_signal_rate = up_trade_num / total_sample
    down_signal_rate = down_trade_num / total_sample

    up_win = safe_mean(long_ret[up_non_zero_idx] > 0)
    down_win = safe_mean(short_ret[down_non_zero_idx] > 0)
    up_mean_return = safe_mean(long_ret[up_selected_idx])
    down_mean_return = safe_mean(short_ret[down_selected_idx])
    up_base_mean_return = safe_mean(long_ret)
    down_base_mean_return = safe_mean(short_ret)
    up_base_win = safe_mean(long_ret[long_ret != 0] > 0)
    down_base_win = safe_mean(short_ret[short_ret != 0] > 0)

    zero_sample = np.sum((long_ret == 0) & (short_ret == 0))

    combined_selected_returns = np.concatenate([
        long_ret[up_selected_idx],
        short_ret[down_selected_idx],
    ])

    summary = dict()
    summary['up_win_rate'], summary['down_win_rate'] = up_win, down_win
    summary['up_base_win_rate'], summary['down_base_win_rate'] = up_base_win, down_base_win
    summary['up_win_rate_lift'] = up_win - up_base_win
    summary['down_win_rate_lift'] = down_win - down_base_win
    summary['up_beat_base_mean_rate'] = safe_mean(long_ret[up_selected_idx] > up_base_mean_return)
    summary['down_beat_base_mean_rate'] = safe_mean(short_ret[down_selected_idx] > down_base_mean_return)
    summary['up_mean_ret'], summary['down_mean_ret'] = up_mean_return * 1e4, down_mean_return * 1e4
    summary['up_base_mean_ret'], summary['down_base_mean_ret'] = up_base_mean_return * 1e4, down_base_mean_return * 1e4
    summary['up_excess_mean_ret'] = (up_mean_return - up_base_mean_return) * 1e4
    summary['down_excess_mean_ret'] = (down_mean_return - down_base_mean_return) * 1e4
    summary['up_lift_ratio'] = safe_divide(up_mean_return, abs(up_base_mean_return))
    summary['down_lift_ratio'] = safe_divide(down_mean_return, abs(down_base_mean_return))
    summary['up_signal_rate'] = up_signal_rate
    summary['down_signal_rate'] = down_signal_rate
    summary['up_bound'], summary['down_bound'] = up_bound, down_bound
    summary['up_trade_num'], summary['down_trade_num'] = up_trade_num, down_trade_num
    summary['weighted_return'] = (
        safe_contribution(up_signal_rate, summary['up_mean_ret'])
        + safe_contribution(down_signal_rate, summary['down_mean_ret'])
    )
    summary['base_weighted_return'] = (
        safe_contribution(up_signal_rate, summary['up_base_mean_ret'])
        + safe_contribution(down_signal_rate, summary['down_base_mean_ret'])
    )
    summary['excess_weighted_return'] = summary['weighted_return'] - summary['base_weighted_return']
    summary['zero_rate'] = zero_sample / total_sample
    summary['total_sample'] = total_sample
    summary['abs_ret'] = safe_mean(np.abs(combined_selected_returns)) * 1e4
    summary['avg_ret'] = safe_mean(combined_selected_returns) * 1e4

    return summary


def get_selected_idx(pre_prob, bound, class_label, class_num):
    if class_num == 3:
        return pre_prob[:, class_label] >= bound

    if class_num == 2:
        if class_label == 0:
            pre_prob = 1 - pre_prob
        return pre_prob >= bound

    raise ValueError(f"Unsupported class_num: {class_num}")


def safe_mean(arr):
    if len(arr) == 0:
        return np.nan
    return np.mean(arr)


def safe_divide(numerator, denominator):
    if np.isnan(numerator) or np.isnan(denominator) or denominator == 0:
        return np.nan
    return numerator / denominator


def safe_contribution(rate, value):
    if np.isnan(rate) or rate == 0:
        return 0.0
    if np.isnan(value):
        return np.nan
    return rate * value
