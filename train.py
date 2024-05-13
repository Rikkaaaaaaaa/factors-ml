import multiprocessing as mp
import os.path as osp
import logging

from dataset.sql_data import check_indus
from dataset import build_dataset
from models import build_model
from feature_selector import build_selector
from backtester import BackTester
from utils.logger import get_root_logger, get_env_info
from utils.option import parse_options, dict2str
from utils.publish import save_report_disk, push_signal_sql
from utils.misc import Timer, time_str, get_time_str, exists_results, ensure_path



def init(args):
    global lock
    lock = args[0]

def train_pipeline(train_args):
    opt, test_month, indus_type = train_args
    # logger init
    logger_name = f"month{test_month}_indus{indus_type}"
    log_file = osp.join(opt['path']['log'], f"{logger_name}_{get_time_str()}.log")
    logger = get_root_logger(logger_name=logger_name, log_level=logging.INFO, log_file=log_file)

    # get data set from test month
    dataset = build_dataset(opt, test_month=test_month, indus_type=indus_type)
    dataset.load_data()
    if dataset.is_empty:
        logger.info(f"{test_month}_indus_{indus_type}: Dataset is empty!")
        return
    x_train, y_train = dataset.train_data[dataset.training_factor_name], dataset.train_data.class_label

    # factor selection
    training_factor_name = dataset.training_factor_name
    if opt.get('feature_selector'):
        feature_selector = build_selector(opt, test_month=test_month, indus_type=indus_type)
        selected_factor = feature_selector.select_factor(x_train, y_train)
        dataset.set_selected_factor(selected_factor)
        training_factor_name = selected_factor

    # train model
    model = build_model(opt, test_month=test_month, indus_type=indus_type)
    model.train(x_train[training_factor_name], y_train)
    model.save()

    # backtesting or reactive process: it will record bound proba and report summay of models performance
    backtester = BackTester(opt, test_month, indus_type)
    if opt['is_runtime']:
        backtester.runtime(dataset, model)
    else:
        backtester.backtest(dataset, model)


def init_args(opt):
    args = []
    for test_month in opt['dataset']['test_month']:
        industry = check_indus(opt, test_month)
        industry = [9]
        for indus_type in industry:
            if not exists_results(opt, test_month, indus_type):
                args.append((opt, test_month, indus_type))
    return args


def main(opt):
    print(get_env_info())
    # mp training
    pool = mp.Pool(processes=opt['n_jobs'], )
    global_timer = Timer()
    args = init_args(opt)
    results = [pool.apply_async(train_pipeline, (arg,)) for arg in args]
    [result.get() for result in results]
    pool.close()
    pool.join()
    print("Task time is {}".format(time_str(global_timer.item())))
    # save report
    if not opt['is_runtime']:
        save_report_disk(opt)


if __name__ == '__main__':
    root_path = './'
    opt, args = parse_options(root_path)
    main(opt)



