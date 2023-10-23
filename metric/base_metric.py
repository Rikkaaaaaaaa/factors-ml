import numpy as np




def compute_metric(opt, pre_prob, pre_prob_train, y_test_reg):
    """
    Compute bound, win rate , mean return, total sample .etc as performance
    :param pre_prob: test probability
    :param pre_prob_train: train probability
    :param y_test_reg: return
    :return:summary: pd.DataFrame
    """

    pct_num = [100-opt['test']['threshold_pct'], 100-opt['test']['threshold_pct']]
    class_num = opt['dataset']['class_num']

    # compute up accuracy
    up_bound = compute_prob_bound(pre_prob_train, pct_num=pct_num[0], class_label=1, class_num=class_num)
    up_win, zero_sample = compute_win_rate(pre_prob, y_test_reg, up_bound, class_label=1, class_num=class_num)
    up_trade_num, up_mean_return = compute_return(pre_prob, up_bound, y_test_reg, class_label=1, class_num=class_num)

    # compute down accuracy
    down_bound = compute_prob_bound(pre_prob_train, pct_num=pct_num[1], class_label=0, class_num=class_num)
    down_win, _ = compute_win_rate(pre_prob, y_test_reg, down_bound, class_label=0, class_num=class_num)
    down_trade_num, down_mean_return = compute_return(pre_prob, down_bound, y_test_reg, class_label=0, class_num=class_num)

    summary = dict()
    summary['up_bound'], summary['down_bound']  = up_bound, down_bound
    summary['up_win_rate'], summary['down_win_rate'] = up_win, down_win
    summary['up_mean_ret'], summary['down_mean_ret'] = up_mean_return, down_mean_return
    summary['up_trade_num'], summary['down_trade_num'] = up_trade_num, down_trade_num
    summary['total_sample'] = len(y_test_reg)
    summary['zero_rate'] = zero_sample/len(y_test_reg)
    summary['up_signal_rate'] = up_trade_num/ summary['total_sample']
    summary['down_signal_rate'] = down_trade_num / summary['total_sample']

    return summary


def compute_metric_RT(opt, pre_prob_train):
    """
    Compute bound, win rate , mean return, total sample .etc as performance
    :param pre_prob_train: train probability

    """
    pct_num = [100-opt['test']['threshold_pct'], 100-opt['test']['threshold_pct']]
    class_num = opt['dataset']['class_num']

    # compute up accuracy
    up_bound = compute_prob_bound(pre_prob_train, pct_num=pct_num[0], class_label=1, class_num=class_num)

    # compute down accuracy
    down_bound = compute_prob_bound(pre_prob_train, pct_num=pct_num[1], class_label=0, class_num=class_num)

    summary = dict()
    summary['up_bound'], summary['down_bound'] = up_bound, down_bound

    return summary

def compute_prob_bound(pre_prob, pct_num, class_label, class_num):
    if class_num == 3:
        bound = np.percentile(pre_prob[:, class_label], pct_num)
    if class_num == 2:
        if class_label == 0:
            bound = np.percentile(1 - pre_prob, pct_num)
        else:
            bound = np.percentile(pre_prob, pct_num)

    return bound

def compute_win_rate(pre_prob, mid_price, bound, class_label, class_num):
    # delete prob under bound and zero return
    if class_num == 3:
        #pre_label = np.argmax(pre_prob, axis=1)
        selected_idx = (pre_prob[:, class_label] >= bound) & (mid_price != 0)
    if class_num == 2:
        if class_label == 0:
            pre_prob = 1 - pre_prob
        selected_idx = (pre_prob >= bound) & (mid_price != 0)
    zero_sample = len(mid_price[mid_price==0])

    # compute hit and sample number
    if class_label == 0:
        hit = np.sum(mid_price[selected_idx] < 0)
    if class_label == 1:
        hit = np.sum(mid_price[selected_idx] > 0)
    pre_num = len(mid_price[selected_idx])
    win_rate = hit / pre_num

    return win_rate, zero_sample

def compute_return(pre_prob, bound, mid_price, class_label=0, class_num=3):
    # delete prob under bound
    if class_num == 3:
        #pre_label = np.argmax(pre_prob, axis=1)
        selected_idx = (pre_prob[:, class_label] >= bound)

    if class_num == 2:
        if class_label == 0:
            pre_prob = 1 - pre_prob
        selected_idx = (pre_prob >= bound)

    return len(mid_price[selected_idx]), np.mean(mid_price[selected_idx])
