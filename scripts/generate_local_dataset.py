import multiprocessing as mp
import os.path as osp
import logging
import random
import os.path as osp
import shutil

import pandas as pd

from utils.misc import set_random_seed, ensure_path, mkdir
from dataset.sql_data import check_indus
from dataset import build_dataset
from utils.option import yaml_load
from utils.logger import get_root_logger, get_env_info
from utils.misc import Timer, time_str, get_time_str, exists_results
import lightgbm as lgbm



def init(args):
    global lock
    lock = args[0]

def train_pipeline(train_args):
    folder_name = './folder'
    opt, test_month, indus_type = train_args
    # logger init
    logger_name = f"month{test_month}_indus{indus_type}"
    log_file = osp.join(opt['path']['log'], f"{logger_name}_{get_time_str()}.log")
    logger = get_root_logger(logger_name=logger_name, log_level=logging.INFO, log_file=log_file)


    # get data set from test month
    dataset = build_dataset(opt, test_month=test_month, indus_type=indus_type)
    dataset.load_data()
    if dataset.is_empty:
        return

    # train_data_pred, test_data_pred = gen_lgbm_regression_pred_result(dataset)
    # train_data_pred.to_csv(
    #     f"{opt['path']['experiments_root']}/{test_month}/train_pred_result_{test_month}_indus_{indus_type}.csv")
    # test_data_pred.to_csv(
    #     f"{opt['path']['experiments_root']}/{test_month}/test_pred_result_{test_month}_indus_{indus_type}.csv")

    # dataset.train_data.to_csv(f"{opt['path']['experiments_root']}/{test_month}/train_data_{test_month}_indus_{indus_type}.csv", index=False)
    # dataset.test_data.to_csv(f"{opt['path']['experiments_root']}/{test_month}/test_data_{test_month}_indus_{indus_type}.csv",index=False)
    dataset.labels.to_csv(f"{opt['path']['experiments_root']}/{test_month}/ret_{test_month}_indus_{indus_type}.csv", index=False)


def gen_lgbm_regression_pred_result(dataset):
    train_data = dataset.train_data.merge(dataset.labels, on=['ticker', 'date', 'time'], how='inner')
    test_data = dataset.test_data.merge(dataset.labels, on=['ticker', 'date', 'time'], how='inner')
    train_data = train_data.dropna(axis=0)
    test_data = test_data.dropna(axis=0)
    train_data_pred = train_data[['ticker', 'date', 'time']]
    test_data_pred = test_data[['ticker', 'date', 'time']]

    for pred_period in [15, 60, 120, 300]:
        # train LGBM regression model
        temp_train_data = train_data[train_data['ret_{}s'.format(pred_period)] != 0]
        train_x = temp_train_data[dataset.training_factor_name]
        train_y = temp_train_data['ret_{}s'.format(pred_period)]
        model = lgbm.LGBMRegressor(n_jobs=8)
        model.fit(train_x, train_y)

        # use LGBM model to predict
        train_x_orig = train_data[dataset.training_factor_name]
        train_pred_y = model.predict(train_x_orig)
        train_data_pred['pred_ret_{}s'.format(pred_period)] = train_pred_y

        test_x = test_data[dataset.training_factor_name]
        test_pred_y = model.predict(test_x)
        test_data_pred['pred_ret_{}s'.format(pred_period)] = test_pred_y
    return train_data_pred, test_data_pred


def gen_mp_args(opt):
    args = []
    for test_month in opt['dataset']['test_month']:
        industry = check_indus(opt, test_month)
        for indus_type in industry:
            if not exists_results(opt, test_month, indus_type):
                args.append((opt, test_month, indus_type))
    return args




def main(opt):
    print(get_env_info())
    pool = mp.Pool(processes=opt['n_jobs'], )
    global_timer = Timer()
    args = gen_mp_args(opt)
    results = [pool.apply_async(train_pipeline, (arg,)) for arg in args]
    [result.get() for result in results]
    pool.close()
    pool.join()
    print("Task time is {}".format(time_str(global_timer.item())))


def gen_factor():
    root_path = '../'
    option_path = '../option/gen_factor/gen_factor_hs300_highprice.yaml'
    opt = yaml_load(option_path)
    # random seed
    seed = opt.get('manual_seed')
    if seed is None:
        seed = random.randint(1, 10000)
        opt['manual_seed'] = seed
    set_random_seed(seed)

    # save path init
    if not opt.get('path'):
        opt['path'] = dict()
    # experiment path
    experiments_root = opt['path'].get('experiments_root')
    if experiments_root is None:
        experiments_root = osp.join(root_path, 'experiments')
    experiments_root = osp.join(experiments_root, opt['name'])
    opt['path']['experiments_root'] = experiments_root
    ensure_path(experiments_root)

    # month path
    for test_month in opt['dataset']['test_month']:
        test_month_path = osp.join(experiments_root, str(test_month))
        mkdir(test_month_path)


    # log path
    log_root = opt['path'].get('log_root')
    if log_root is None:
        log_root = osp.join(experiments_root, 'log')
    opt['path']['log'] = log_root
    mkdir(log_root)

    # copy option
    shutil.copy2(option_path, opt['path']['experiments_root'])

    # main
    main(opt)

def check_data():
    train = '/root/PycharmProjects/factors-ml/experiments/generate_factor/train_data_202304_indus_1.csv'
    train_data = pd.read_csv(train)
    test = '/root/PycharmProjects/factors-ml/experiments/generate_factor/test_data_202304_indus_1.csv'
    test_data = pd.read_csv(test)

    print(len(train))

if __name__ == '__main__':
    gen_factor()
