import argparse
from tqdm import tqdm
import os
import multiprocessing as mp
import time

import utils
from data_prepare import get_data
from train import train_model
from backtest import test_model
from search_params import optimize_params

def init(args):
    global lock
    lock = args[0]


def is_null_indus(indus_type, config):
    if config.indus_from == 'sw1':
        data = utils.cx_read_sql(
            'select * from static_data_hs300_all where {}="{}" and avg_price > {} and test_month=202306'.format(config.indus_from, indus_type, config.avg_price))
        tickers = tuple(data['ticker'])
        # delete industry_num <=1
        if len(tickers) <= 1:
            return 1
        else:
            return 0
    else:
        return 0


def get_hs300_args(config):
    args = []
    # month = [202202, 202203, 202204, 202205, 202206, 202207, 202208, 202209, 202210, 202211, 202212, 202301 ,202302, 202303, 202304, 202305]
    #month = [202202, 202203, 202204, 202205, 202206, 202207, 202208]
    month = [202210, 202211, 202212, 202301, 202302, 202303, 202304, 202305, 202306]
    if config.indus_from == 'wind1':
        # wind1 = utils.cx_read_sql(
        #     'select wind1 from static_data_hs300_all avg_price > {} and test_month=202306'.format(config.avg_price))
        # wind1 = list(wind1.unique())
        indus_num = range(12) # 0 - 10 type
    if config.indus_from == 'sw1':
        indus_num = range(30)  # 0 - 29 type

    if config.std_type == 'zscore':
        std_month_num = 4
        month = [202212, 202301, 202302, 202303, 202304, 202305, 202306]
    elif config.std_type == 'zscore1':
        std_month_num = 6
        month = [202210, 202211, 202212, 202301, 202302, 202303, 202304, 202305, 202306]
        if config.phase == 'optimization':
            month = [202209, 202210, 202211, 202212, 202301, 202302, 202303, 202304, 202305]
    elif config.std_type == 'zscore2':
        std_month_num = 3
        month = [202301, 202302, 202303, 202304, 202305, 202306]
        if config.phase == 'optimization':
            month = [202212, 202301, 202302, 202303, 202304, 202305]
    else:
        std_month_num = 3
        month = [202301, 202302, 202303, 202304, 202305, 202306]

    for indus_type in indus_num:
        if is_null_indus(indus_type, config):
            continue
        for i in range(len(month) - std_month_num):
            file_name = os.path.join(config.res_path, 'results',
                                     '_'.join(["month", str(month[i + std_month_num]), "indus_type", str(indus_type)]))
            file_path = file_name + '_res.csv'
            if not os.path.exists(file_path) or config.phase!='train':
                args.append({"month": month[i:i + std_month_num + 1], # std + train(3) + test month(1)
                             "month_bt": month[i + std_month_num],
                             "indus_from": config.indus_from,
                             "indus_type": indus_type,
                             "avg_price": config.avg_price,
                             "label_name": config.label_name,
                             "pct_num": config.pct_num,
                             "std_type": config.std_type,
                             "alpha": config.alpha,
                             "class_num": config.class_num,
                             "num_epoch": config.num_epoch,
                             "res_path": config.res_path,
                             "model_name": config.model_name,
                             "n_jobs": config.process_num,
                             "phase": config.phase,
                             "balance": config.balance,
                             })

    return args


def train_hs300_mp(args):
    train_data, test_data = get_data(month=args["month"], indus_from=args["indus_from"], indus_type=args["indus_type"],
                                     avg_price=args["avg_price"], label_name=args["label_name"], std_type=args["std_type"], alpha=args["alpha"],
                                     class_num=args["class_num"], phase=args["phase"], balance=args["balance"] , lock=lock)
    if not train_data.empty:
        if args["phase"] == 'train':
            train_model(train_data, test_data, month=args["month_bt"], indus_type=args["indus_type"],
                       pct_num=args["pct_num"],class_num=args["class_num"], num_epoch=args["num_epoch"],
                       model_name=args["model_name"], n_jobs=args["n_jobs"], res_path=args["res_path"], )
        if args["phase"] == 'optimization':
            optimize_params(train_data, test_data, month=args["month_bt"], indus_type=args["indus_type"],
                            pct_num=args["pct_num"], class_num=args["class_num"],
                            model_name=args["model_name"], n_jobs=args["n_jobs"], res_path=args["res_path"])
        if args["phase"] == 'eval':
            test_model(train_data, test_data, month=args["month_bt"], indus_type=args["indus_type"],
                       pct_num=args["pct_num"],class_num=args["class_num"], num_epoch=args["num_epoch"],
                       model_name=args["model_name"], n_jobs=args["n_jobs"], res_path=args["res_path"], )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train hs300 data')
    parser.add_argument('--std_type', type=str, default='zscore2', help="standardization type")
    parser.add_argument('--res_path', type=str, default='experiments/results', help="the path of results")
    parser.add_argument('--label_name', type=str, default='15s', help="label column: 15s, 60s, 120s, 300s")
    parser.add_argument('--indus_from', type=str, default='wind1', help="wind1 or sw1")
    parser.add_argument('--phase', type=str, default='train', help="training status, train or optimization")
    parser.add_argument('--class_num', type=int, default=2, help="classification objective")
    parser.add_argument('--avg_price', type=int, default=10, help="ticker filter by price ")
    parser.add_argument('--num_epoch', type=int, default=200, help="training and testing epoch number")
    parser.add_argument('--alpha', type=float, default=5.0, help="threshold of return, whose base is 1e-4")
    parser.add_argument('--model_name', type=str, default='lgbm', help="selection of moyydel type: LR, xgb or lgbm")
    parser.add_argument('--pct_num', type=str, default="40,40", help="trading top prob pct of up and down directions, range=(1,100)")
    parser.add_argument('--process_num', type=int, default=10, help="processor number")
    parser.add_argument('--balance', type=int, default=2, help="balance type number")
    config = parser.parse_args()

    config.pct_num = [int(config.pct_num.split(',')[0]), int(config.pct_num.split(',')[1])]
    # rename result folder_name, eg.experiments/wind1_lgbm_alpha5_pct40_40_class2_epoch150_15s
    if config.res_path == 'auto' or config.res_path == 'experiments/results':
        dirname = os.path.dirname(config.res_path)
        basename = config.indus_from + '_' + config.model_name + '_alpha' + str(config.alpha) + '_' + config.std_type + '_pct' + \
                   str(config.pct_num[0]) + '_' + str(config.pct_num[1]) + '_class' + str(config.class_num) + '_epoch' + \
                   str(config.num_epoch) + '_balance' +  str(config.balance)  +'_'+ config.label_name
        config.res_path = os.path.join(dirname, basename)

    # make result path
    utils.ensure_path(config.res_path, remove=False)

    # correct alpha value
    config.alpha = config.alpha * 1e-4

    # Logit Regression must be binary classification
    if config.model_name == 'LR':
        assert config.class_num == 2, "ValueError: For logistic regression class_num must be 2 ! "

    # multiprocessing training
    lock = mp.Lock()
    init_args = [lock,]
    global_timer = utils.Timer()
    pool = mp.Pool(processes=config.process_num, initializer=init, initargs=(init_args,))
    args = get_hs300_args(config)
    results = [pool.apply_async(train_hs300_mp, (arg,)) for arg in args]
    [result.get() for result in results]
    print("Task time is {}".format(utils.time_str(global_timer.t())))
