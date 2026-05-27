import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression as LR
from sklearn.metrics import roc_auc_score, accuracy_score
import statsmodels.api as sm
import lightgbm as lgb
from lightgbm import early_stopping, log_evaluation
import time
import optuna
import pickle



SEED = 42
N_TRIALS = 50


def objective_lgbm(trial, train_data, test_data, model_name, class_num, pct_num, n_jobs):
    label_col = 'class_label'
    x_train = train_data.drop([label_col, 'mid_price', 'ticker'], axis=1).values
    y_train = train_data[label_col].values
    x_test = test_data.drop([label_col, 'mid_price', 'ticker'], axis=1).values
    y_test = test_data[label_col].values

    dtrain = lgb.Dataset(x_train, label=y_train)
    dvalid = lgb.Dataset(x_test, label=y_test)
    # 
    # param = {
    #     "objective": "binary",
    #     "verbosity": -1,
    #     "n_jobs": n_jobs,
    #     "metric": "auc",#trial.suggest_categorical("metric",("binary_logloss","auc",)),
    #     "boosting_type": "gbdt",
    #     "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.4),
    #     "lambda_l1": trial.suggest_float("lambda_l1", 1e-8, 10.0, log=True),
    #     "lambda_l2": trial.suggest_float("lambda_l2", 1e-8, 10.0, log=True),
    #     "num_leaves": trial.suggest_int("num_leaves", 2, 1024),
    #     "feature_fraction": trial.suggest_float("feature_fraction", 0.4, 1.0),
    #     "bagging_fraction": trial.suggest_float("bagging_fraction", 0.4, 1.0),
    #     "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
    #     "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
    # }

    param = {
        "objective": "binary",
        "metric": "binary_logloss", #trial.suggest_categorical("metric",("binary_logloss","auc",)),
        "boosting_type": "gbdt",
        "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.5),
        "lambda_l1": trial.suggest_float("lambda_l1", 1e-8, 10, log=True),
        "lambda_l2": trial.suggest_float("lambda_l2", 1e-8, 10, log=True),
        "max_depth": 10,
        "num_leaves": trial.suggest_int("num_leaves", 10, 100),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.7, 1.0),
        "bagging_fraction": trial.suggest_float("bagging_fraction", 0.7, 1.0),
        "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
        #"min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 1, 50), # equal to min_child_samples
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
        "verbosity": -1,
        "n_jobs": n_jobs,
    }
    num_boost_round = trial.suggest_int("num_boost_round", 100, 300)
    #pct = trial.suggest_int("pct", 20, 45)

    # Add a callback for pruning.
    pruning_callback = optuna.integration.LightGBMPruningCallback(trial, "binary_logloss")
    model = lgb.train(
        param, dtrain, num_boost_round=num_boost_round, valid_sets=[dvalid], callbacks=[pruning_callback]
    )

    # evaluation
    res_keys = ['ticker', 'up_bound', 'down_bound', 'up_win_rate', 'down_win_rate', 'up_mean_ret', 'down_mean_ret',
                'up_trade_num', 'down_trade_num', 'total_sample', 'zero_pct']
    res = {k: [] for k in res_keys}
    tickers = test_data['ticker'].unique()
    for ticker in tickers:
        x_train_ticker = train_data[train_data['ticker'] == ticker].drop([label_col, 'mid_price', 'ticker'], axis=1).values
        x_test_ticker = test_data[test_data['ticker'] == ticker].drop([label_col, 'mid_price', 'ticker'], axis=1).values
        y_test_reg = test_data[test_data['ticker'] == ticker]['mid_price'].values
        y_test_ticker = test_data[test_data['ticker'] == ticker][label_col].values
        pre_prob, pre_prob_train = eval(model, x_train_ticker, x_test_ticker, num_boost_round,
                                        model_name=model_name, class_num=class_num)


        res_dict = compute_metric(pre_prob, pre_prob_train, y_test_reg, pct_num=pct_num, class_num=class_num)
        res_dict['ticker'] = ticker
        for k in res_dict.keys():
            res[k].append(res_dict[k])
    res['up_signal_rate'] = np.array(res['up_trade_num']) / np.array(res['total_sample'])
    res['down_signal_rate'] = np.array(res['down_trade_num']) / np.array(res['total_sample'])
    loss_value = np.mean(np.array(res['up_mean_ret'])*res['up_signal_rate']) - np.mean(np.array(res['down_mean_ret'])*res['down_signal_rate'])
    #loss_value = (np.mean(res['up_mean_ret']) - np.mean(res['down_mean_ret']))/2
    #loss_value = -1*(np.mean(res['up_mean_ret']) - np.mean(res['down_mean_ret']))/2
    #loss_value = np.mean(res['up_mean_ret'])
    #loss_value = np.mean(acc)
    return loss_value

def optimize_params(train_data, test_data, month, indus_type, pct_num=[80, 80], class_num=3,  model_name='lgbm', n_jobs=1, res_path='results'):
    # save study status
    study_name = '_'.join(["month", str(month+1), "indus_type", str(indus_type)])
    storage_name = "sqlite:///{}.sqlite3".format(os.path.join(res_path, 'study'))
    # optimization
    study = optuna.create_study(direction="minimize",
                                study_name=study_name,
                                storage=storage_name,
                                )
    func = lambda trial: objective_lgbm(trial, train_data, test_data, model_name, class_num, pct_num, n_jobs)
    study.optimize(func, n_trials=N_TRIALS)
    print('{} best_value is {}'.format(study_name, study.best_value))


def eval(model, x_train, x_test, num_epoch, model_name='lgbm', class_num=3 ):
    '''
    evaluation for one ticker
    '''
    if model_name == 'LR':
        x_test = sm.add_constant(x_test)
        x_train = sm.add_constant(x_train)
        pre_prob = model.predict(x_test)
        pre_prob_train = model.predict(x_train)

        # pre_prob = models.predict_proba(x_test)[:, 1] # only need label 1
        # pre_prob_train = models.predict_proba(x_train)[:, 1]
    if model_name == 'lgbm':
        if class_num == 3:
            pre_prob = model.predict(x_test, num_iteration=num_epoch)
            pre_prob_train = model.predict(x_train, num_iteration=num_epoch)
            #pre_label = np.argmax(pre_prob, axis=1)

            pre_prob_train = model.predict(x_train, num_iteration=num_epoch)
        if class_num == 2:
            pre_prob = model.predict(x_test, num_iteration=num_epoch)
            pre_prob_train = model.predict(x_train, num_iteration=num_epoch)

    return pre_prob, pre_prob_train

def compute_metric(pre_prob, pre_prob_train, y_test_reg, pct_num=[80, 80], class_num=3):
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
    res['up_bound'], res['down_bound'] = up_bound, down_bound
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

