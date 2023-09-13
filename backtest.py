import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression as LR
import statsmodels.api as sm
import lightgbm as lgb


def test_model(train_data, test_data, month=202306, indus_type=1, pct_num=[80, 80], class_num=3, num_epoch=300, model_name='lgbm', n_jobs=1, res_path='results'):
    label_col = 'class_label'
    save_name = '_'.join(["month", str(month), "indus_type", str(indus_type)])

    # training
    if model_name == 'lgbm':
        # save model file
        ckpt_path = os.path.join(res_path, 'ckpt')
        assert os.path.exists(ckpt_path)
        ckpt_path = os.path.join(ckpt_path, save_name + '.txt')
        model = lgb.Booster(model_file=ckpt_path)

    # evaluation
    signal = []
    res_keys = ['ticker', 'up_bound', 'down_bound', 'up_win_rate', 'down_win_rate', 'up_mean_ret', 'down_mean_ret', 'up_trade_num', \
                 'down_trade_num','total_sample','zero_pct']
    res = {k: [] for k in res_keys}
    tickers = test_data['ticker'].unique()
    for ticker in tickers:
        x_train = train_data.query('ticker==@ticker').drop([label_col, 'time', 'date', 'mid_price', 'ticker'],axis=1).values
        x_test = test_data.query('ticker==@ticker').drop([label_col, 'time', 'date', 'mid_price', 'ticker'], axis=1).values
        pre_prob, pre_prob_train = eval(model, x_train, x_test, num_epoch=num_epoch, model_name=model_name, class_num=class_num )
        y_test_value = test_data.query('ticker==@ticker')['mid_price'].values
        ticker_sig = gen_signal(pre_prob, pre_prob_train, test_data.query('ticker==@ticker'), pct_num=pct_num, class_num=class_num)
        ticker_sig['ticker'] = ticker
        signal.append(ticker_sig)

        # drop nan results
        # x_test = test_data.query('ticker==@ticker').dropna().drop([label_col, 'time', 'date', 'mid_price', 'ticker'], axis=1).values
        # y_test_value = test_data.query('ticker==@ticker').dropna()['mid_price'].values
        # pre_prob, pre_prob_train = eval(model, x_train, x_test, num_epoch=num_epoch, model_name=model_name, class_num=class_num)
        res_dict = compute_metric(pre_prob, pre_prob_train, y_test_value, x_test, pct_num=pct_num, class_num=class_num)
        res_dict['ticker'] = ticker
        for k in res_dict.keys():
            res[k].append(res_dict[k])

    res = pd.DataFrame(res)
    res['indus_type'] = indus_type
    res['month'] = month
    signal = pd.concat(signal, ignore_index=True)
    sig_path = os.path.join(res_path, 'signal')
    if not os.path.exists(sig_path):
        os.mkdir(sig_path)
    #res.to_csv(os.path.join(sig_path, save_name + '_sig_res.csv')) for debug result
    sig_path = os.path.join(sig_path, save_name + '_sig.csv')
    signal.to_csv(sig_path)
    print("file saved at {}".format(sig_path))


def eval(model, x_train, x_test, num_epoch=300, model_name='lgbm', class_num=3 ):
    '''
    evaluation for one ticker
    '''
    label_col = 'class_label'
    if model_name == 'LR':
        x_test = sm.add_constant(x_test)
        x_train = sm.add_constant(x_train)
        pre_prob = model.predict(x_test)
        pre_prob_train = model.predict(x_train)

        # pre_prob = model.predict_proba(x_test)[:, 1] # only need label 1
        # pre_prob_train = model.predict_proba(x_train)[:, 1]
    if model_name == 'lgbm':
        if class_num == 3:
            pre_prob = model.predict(x_test, num_iteration=num_epoch)
            pre_prob_train = model.predict(x_train, num_iteration=num_epoch)
            #pre_label = np.argmax(pre_prob, axis=1)
        if class_num == 2:
            pre_prob = model.predict(x_test, num_iteration=num_epoch)
            pre_prob_train = model.predict(x_train, num_iteration=num_epoch)

    return pre_prob, pre_prob_train

def gen_signal(pre_prob, pre_prob_train, x_test, pct_num=[80, 80], class_num=3):
    def compute_signal(pre_prob, bound, class_label=0, class_num=3):
        # delete prob under bound and zero return
        if class_num == 3:
            # pre_label = np.argmax(pre_prob, axis=1)
            selected_idx = (pre_prob[:, class_label] >= bound)
        if class_num == 2:
            if class_label == 0: # up
                pre_prob_ = 1 - pre_prob
                selected_idx = (pre_prob_ >= bound)
            else:
                selected_idx = (pre_prob >= bound)
        return selected_idx

    na_idx = x_test.isnull().T.any()
    up_bound = compute_prob_bound(pre_prob_train, pct_num=100 - pct_num[0], class_label=0, class_num=class_num)
    up_idx = compute_signal(pre_prob, up_bound, class_label=0, class_num=class_num)
    down_bound = compute_prob_bound(pre_prob_train, pct_num=100 - pct_num[1], class_label=1, class_num=class_num)
    down_idx = compute_signal(pre_prob, down_bound, class_label=1, class_num=class_num)

    signal = np.zeros(len(up_idx)) # nan factors generate zero signal
    signal[up_idx] = 1
    signal[down_idx] = -1
    signal[na_idx] = 0
    x_test_sig = pd.DataFrame()
    x_test_sig['time'] = x_test['time']
    x_test_sig['date'] = x_test['date']
    x_test_sig['signal'] = signal
    x_test_sig['proba'] = 1 - pre_prob
    x_test_sig['up_bound'] = up_bound
    x_test_sig['down_bound'] = down_bound
    #x_test_sig['ret'] = x_test['mid_price']


    return x_test_sig[['time', 'date', 'signal', 'proba', 'up_bound', 'down_bound',]]


def compute_metric(pre_prob, pre_prob_train, y_test_reg, x_test, pct_num=[80, 80], class_num=3):
    # up accuracy
    up_bound = compute_prob_bound(pre_prob_train, pct_num=100-pct_num[0], class_label=0, class_num=class_num)
    up_win, zero_sample = compute_win_rate(pre_prob, y_test_reg, up_bound, class_label=0, class_num=class_num)
    up_trade_num, up_mean_return = compute_return(pre_prob, up_bound, y_test_reg, class_label=0, class_num=class_num)

    # down accuracy
    down_bound = compute_prob_bound(pre_prob_train, pct_num=100-pct_num[1], class_label=1, class_num=class_num)
    down_win, _ = compute_win_rate(pre_prob, y_test_reg, down_bound, class_label=1, class_num=class_num)
    down_trade_num, down_mean_return = compute_return(pre_prob, down_bound, y_test_reg, class_label=1, class_num=class_num)

    # save result dict
    res = dict()
    res['up_bound'], res['down_bound']  = up_bound, down_bound
    res['up_win_rate'], res['down_win_rate'] = up_win, down_win
    res['up_mean_ret'], res['down_mean_ret'] = up_mean_return, down_mean_return
    res['up_trade_num'], res['down_trade_num'] = up_trade_num, down_trade_num
    res['total_sample'] = len(y_test_reg)
    res['zero_pct'] = zero_sample/len(y_test_reg)
    return res

def compute_prob_bound(pre_prob, pct_num=80, class_label=0, class_num=3):
    if class_num == 3:
        bound = np.percentile(pre_prob[:, class_label], pct_num)
    if class_num == 2:
        if class_label == 0:
            pre_prob = 1 - pre_prob
        bound = np.percentile(pre_prob, pct_num)
        #bound = np.percentile(pre_prob[:, class_label], pct_num)

    return bound

def compute_win_rate(pre_prob, mid_price, bound, class_label=0, class_num=3):
    # delete prob under bound and zero return
    if class_num == 3:
        #pre_label = np.argmax(pre_prob, axis=1)
        selected_idx = (pre_prob[:, class_label] >= bound) & (mid_price != 0)
    if class_num == 2:
        if class_label == 0:
            pre_prob = 1 - pre_prob
        selected_idx = (pre_prob >= bound) & (mid_price != 0)
        #selected_idx = (pre_prob[:, class_label] >= bound) & (mid_price != 0)

    zero_sample = len(mid_price[mid_price==0])

    # compute hit and sample number
    if class_label == 0:
        hit = np.sum(mid_price[selected_idx] >= 0)
    if class_label == 1:
        hit = np.sum(mid_price[selected_idx] <= 0)
    pre_num = len(mid_price[selected_idx])
    win_rate = hit / pre_num
    # print(hit, pre_num, win_rate)
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
        #selected_idx = (pre_prob[:, class_label] >= bound)

    return len(mid_price[selected_idx]), np.mean(mid_price[selected_idx])

