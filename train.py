import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression as LR
import statsmodels.api as sm
import lightgbm as lgb
import xgboost as xgb
import time
import pickle
import optuna

import utils
from data_prepare import get_data


def train_model(train_data, test_data, month=202306, indus_type=1, pct_num=[80, 80], class_num=3, num_epoch=300, model_name='lgbm', n_jobs=1, res_path='results'):
    label_col = 'class_label'
    save_name = '_'.join(["month", str(month), "indus_type", str(indus_type)])
    x_train = train_data.drop([label_col, 'mid_price', 'ticker'], axis=1).values
    y_train = train_data[label_col].values
    y_train_reg = train_data['mid_price'].values

    # training
    if model_name == 'xgb':
        params = {'booster': 'gbtree',
                  'objective': 'binary:logistic',
                  'eval_metric': 'auc',
                  'gamma': 1,
                  'min_child_weight': 1.5,
                  'max_depth': 5,
                  'lambda': 10,
                  'subsample': 0.7,
                  'colsample_bytree': 0.7,
                  'colsample_bylevel': 0.7,
                  'eta': 0.04,
                  'tree_method': 'exact',
                  'seed': 2020,
                  'n_jobs': n_jobs,
                  'verbosity': 0,

                  }
        # loading study status
        study_name = '_'.join(["month", str(month), "indus_type", str(indus_type)])
        storage_name = "sqlite:///{}.sqlite3".format(os.path.join(res_path, 'study'))
        study_path = os.path.join(res_path, 'study.sqlite3')
        if os.path.exists(study_path):
            study = optuna.create_study(study_name=study_name, storage=storage_name, load_if_exists=True)
            params.update(study.best_params)
            num_epoch = study.best_params["num_boost_round"]
            if study.best_params.get("pct"):
                pct = study.best_params.get("pct")
                pct_num = [pct, pct]

        train_matrix = xgb.DMatrix(x_train, label=y_train)
        model = xgb.train(params, train_matrix, num_boost_round=num_epoch)

        # save model file
        ckpt_path = os.path.join(res_path, 'ckpt')
        if not os.path.exists(ckpt_path):
            os.mkdir(ckpt_path)
        ckpt_path = os.path.join(ckpt_path, save_name + '.json')
        model.save_model(ckpt_path)

    if model_name == 'lgbm':
        train_matrix = lgb.Dataset(x_train, label=y_train)
        #valid_matrix = lgb.Dataset(x_test, label=y_test)
        if class_num == 3:
            params = {
                'boosting_type': 'gbdt',
                'objective': 'multiclass',
                'metric': 'multi_logloss',
                'learning_rate': 0.1,
                'num_class': 3,
                'min_child_weight': 1e-3,
                'num_leaves': 30,
                'max_depth': -1,
                'lambda_l1': 0.4,
                'lambda_l2': 0.5,
                'feature_fraction': 1,
                'bagging_fraction': 1,
                'bagging_freq': 0,
                'seed': 2020,
                'nthread': n_jobs,
                #'silent': True,
                'verbose': -1,
            }
        if class_num == 2:
            # params = {
            #     'boosting_type': 'gbdt',
            #     'objective': 'binary',
            #     'metric': 'auc',
            #     'max_bin': 255,
            #     'learning_rate': 0.1,
            #     'num_leaves': 30,
            #     'max_depth': -1,
            #     'feature_fraction': 0.8,
            #     'bagging_freq': 5,
            #     'bagging_fraction': 0.8,
            #     #'min_data_in_leaf': 21,
            #     #'min_sum_hessian_in_leaf': 3.0,
            #     'n_jobs': n_jobs,
            #     'verbosity': -1,
            # }
            # for params read from study
            params = {
                    "objective": "binary",
                    "metric": "auc",  # trial.suggest_categorical("metric",("binary_logloss","auc",)),
                    "boosting_type": "gbdt",
                    'max_bin': 255,
                    "learning_rate": 0.1,
                    "max_depth": -1,
                    "num_leaves": 30,
                    "feature_fraction": 0.8,
                    "bagging_fraction": 0.8,
                    "bagging_freq": 5,
                    #'min_sum_hessian_in_leaf': 3.0,
                    "verbosity": -1,
                    'n_jobs': n_jobs,
                    #'verbose': -1,
                }


        # loading study status
        study_name = '_'.join(["month", str(month), "indus_type", str(indus_type)])
        storage_name = "sqlite:///{}.sqlite3".format(os.path.join(res_path, 'study'))
        study_path = os.path.join(res_path, 'study.sqlite3')
        if os.path.exists(study_path):
            study = optuna.create_study(study_name=study_name, storage=storage_name, load_if_exists=True)
            params.update(study.best_params)
            del params['num_boost_round']
            #num_epoch = study.best_params["num_boost_round"]
            if study.best_params.get("pct"):
                pct = study.best_params.get("pct")
                pct_num = [pct, pct]

        num_epoch = 200
        model = lgb.train(params, train_set=train_matrix, num_boost_round=num_epoch)

        # save model file
        ckpt_path = os.path.join(res_path, 'ckpt')
        if not os.path.exists(ckpt_path):
            os.mkdir(ckpt_path)
        ckpt_path = os.path.join(ckpt_path, save_name + '.txt')
        model.save_model(ckpt_path)


    if model_name == 'LR':
        x_train = sm.add_constant(x_train)
        model = sm.Logit(y_train, x_train).fit()# LR()
        # model = LR(solver='liblinear', n_jobs=n_jobs) # 初始化LogisticRegression
        # model.fit(x_train, y_train)  # 使用训练集对测试集进行训练

    # evaluation
    res_keys = ['ticker', 'up_bound', 'down_bound', 'up_win_rate', 'down_win_rate', 'up_mean_ret', 'down_mean_ret'
                ,'up_trade_num',  'down_trade_num','total_sample','zero_pct']
    res = {k: [] for k in res_keys}
    tickers = test_data['ticker'].unique()
    for ticker in tickers:
        x_train_ticker = train_data[train_data['ticker']==ticker].drop([label_col, 'mid_price', 'ticker'], axis=1).values
        y_train_ticker = train_data[train_data['ticker']==ticker][label_col].values
        x_test_ticker = test_data[test_data['ticker']==ticker].drop([label_col, 'mid_price', 'ticker'], axis=1).values
        y_test_ticker = test_data[test_data['ticker']==ticker][label_col].values
        y_test_reg = test_data[test_data['ticker']==ticker]['mid_price'].values
        pre_prob, pre_prob_train = eval(model, x_train_ticker, x_test_ticker, num_epoch=num_epoch, model_name=model_name, class_num=class_num )
        res_dict = compute_metric(pre_prob, pre_prob_train, y_test_reg, pct_num=pct_num, class_num=class_num)
        res_dict['ticker'] = ticker
        for k in res_dict.keys():
            res[k].append(res_dict[k])

    res = pd.DataFrame(res)
    res['indus_type'] = indus_type
    res['month'] = month
    save_path = os.path.join(res_path, 'results')
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    save_path = os.path.join(save_path, save_name + '_res.csv')
    res.to_csv(save_path)
    print("file saved at {}".format(save_path))


def eval(model, x_train, x_test, num_epoch=300, model_name='lgbm', class_num=3 ):
    '''
    evaluation for one ticker
    '''
    if model_name == 'LR':
        x_test = sm.add_constant(x_test)
        x_train = sm.add_constant(x_train)
        pre_prob = model.predict(x_test)
        pre_prob_train = model.predict(x_train)
        # pre_prob = model.predict_proba(x_test)[:, 1] # only need label 1
        # pre_prob_train = model.predict_proba(x_train)[:, 1]

    if model_name == 'lgbm' :
        if class_num == 3:
            pre_prob = model.predict(x_test, num_iteration=num_epoch)
            pre_prob_train = model.predict(x_train, num_iteration=num_epoch)
            #pre_label = np.argmax(pre_prob, axis=1)

        if class_num == 2:
            pre_prob = model.predict(x_test, num_iteration=num_epoch)
            pre_prob_train = model.predict(x_train, num_iteration=num_epoch)
    if model_name == 'xgb' :
        if class_num == 3:
            pre_prob = model.predict(x_test, )
            pre_prob_train = model.predict(x_train, )
            #pre_label = np.argmax(pre_prob, axis=1)

        if class_num == 2:
            pre_prob = model.predict(x_test, )
            pre_prob_train = model.predict(x_train, )

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

    # compute pct return
    up_ret, down_ret = compute_weighted_return(pre_prob, up_bound, down_bound, y_test_reg)

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

    return len(mid_price[selected_idx]), np.mean(mid_price[selected_idx])

def compute_weighted_return(pre_prob, up_bound, down_bound, ret):
    up_idx = 1 - pre_prob > up_bound
    down_idx = pre_prob > down_bound
    up_ret = np.mean(ret[up_idx])
    down_ret = np.mean(ret[down_idx])

    return up_ret, down_ret