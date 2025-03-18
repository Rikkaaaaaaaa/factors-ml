
import optuna
import multiprocessing as mp
import os.path as osp
import logging
import numpy as np

from dataset.sql_data import check_indus
from dataset import build_dataset
from models import build_model
from backtester import SearchBackTester
from utils.logger import get_root_logger, get_env_info
from utils.option import parse_options, dict2str
from utils.misc import Timer, time_str, get_time_str, exists_results



SEED = 2023
N_TRIALS = 50


def objective_lgbm(trial, search_args, dataset):
    opt, test_month, indus_type = search_args
    logger_name = f"month{test_month}_indus{indus_type}"
    logger = get_root_logger(logger_name=logger_name)

    # searching params
    pct = trial.suggest_int("pct", 5, 25)
    opt['test']['threshold_pct'] = pct

    # train lgbm models
    model = build_model(opt, test_month=test_month, indus_type=indus_type)
    x_train, y_train = dataset.train_data[dataset.training_factor_name], dataset.train_data.class_label
    x_test, y_test = dataset.test_data[dataset.training_factor_name], dataset.test_data.class_label
    # prune
    pruning_callback = optuna.integration.LightGBMPruningCallback(trial, "auc") # binary_logloss
    if opt.get('factor_selection'):
        selected_factor = model.select_factor(x_train, y_train)
        dataset.set_selected_factor(selected_factor)
        model.search_params(x_train[selected_factor], y_train, x_test, y_test, callback=pruning_callback)
    else:
        model.search_params(x_train, y_train, x_test, y_test, callbacks=[pruning_callback])
    model.save()

    # backtest and compute loss
    search_backtester = SearchBackTester(opt, test_month, indus_type)
    search_backtester.search_params(dataset, model)
    loss_value = float(search_backtester.loss)

    return loss_value
#
def optimize_params(search_args):
    opt, test_month, indus_type = search_args
    # logger init
    logger_name = f"month{test_month}_indus{indus_type}"
    log_file = osp.join(opt['path']['log'], f"{logger_name}_{get_time_str()}.log")
    logger = get_root_logger(logger_name=logger_name, log_level=logging.INFO, log_file=log_file)

    optuna_log_file = osp.join(opt['path']['log'], f"optuna/{logger_name}_{get_time_str()}.log")
    optuna_logger = get_root_logger(log_level=logging.INFO, log_file=optuna_log_file)
    optuna.logging.enable_propagation()
    optuna.logging.set_verbosity(optuna.logging.INFO)

    # get data set from test month
    dataset = build_dataset(opt, test_month=test_month, indus_type=indus_type)
    dataset.load_data()
    if dataset.is_empty:
        logger.info("Dataset is empty!")
        return

    # save study status
    study_name = '_'.join(["month", str(test_month), "indus_type", str(indus_type)])
    storage_name = "sqlite:///{}.sqlite3".format(osp.join(opt['path']['experiments_root'], 'study'))
    # optimization
    sampler = optuna.samplers.GridSampler({'pct':list(range(5,21))})
    study = optuna.create_study(direction="maximize",
                                sampler=sampler,
                                study_name=study_name,
                                storage=storage_name,
                                )
    func = lambda trial: objective_lgbm(trial, search_args, dataset)
    study.optimize(func, n_trials=N_TRIALS)

    logger.info('{} best value is {}'.format(study_name, study.best_value))
    logger.info('{} best params are {}'.format(study_name, dict2str(study.best_params)))

    result = {study_name: study.best_params}
    return result

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
    results = [pool.apply_async(optimize_params, (arg,)) for arg in args]
    best_params = [result.get() for result in results]
    best_param_log = open (osp.join(opt['path']['experiments_root'], 'best_param.txt'), 'w')
    print(best_params, file=best_param_log)

    pool.close()
    pool.join()
    print("Task time is {}".format(time_str(global_timer.item())))


if __name__ == '__main__':
    root_path = './'
    opt, args = parse_options(root_path)
    main(opt)

