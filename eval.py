import multiprocessing as mp
import os.path as osp
import logging
import argparse

from dataset.sql_ops import check_indus
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

    # define task type
    task_type = opt['dataset'].setdefault('task_type', 'classification')
    if task_type == 'classification':
        label_col_name = 'class_label'
    else:
        label_col_name = 'ret'

    # get data set from test month
    dataset = build_dataset(opt, test_month=test_month, indus_type=indus_type)
    dataset.load_data()
    if dataset.is_empty:
        logger.info(f"{test_month}_indus_{indus_type}: Dataset is empty!")
        return

    # TODO: support factor selection
    training_factor_name = dataset.training_factor_name
    # if opt.get('feature_selector'):
    #     feature_selector = build_selector(opt, test_month=test_month, indus_type=indus_type)
    #     selected_factor_name = feature_selector.select_eval_factor(x_train, y_train) # feature_selector.select_factor(x_train, y_train)
    #     dataset.set_selected_factor(selected_factor_name)
    #     training_factor_name = dataset.selected_factor_name
    #     logger.info(f"{test_month}_indus_{indus_type}: Applying feature selection, total training factor num is: {len(training_factor_name)}")

    # train model
    model = build_model(opt, test_month=test_month, indus_type=indus_type)
    model.load_ckpt()

    # backtesting or record inference_bound
    backtester = BackTester(opt, test_month, indus_type)
    backtester.backtest_eval(dataset, model)


def init_args(opt):
    args = []
    for test_month in opt['dataset']['test_month']:
        industry = check_indus(opt, test_month)
        print(
            f"Loading indus by [{opt['dataset']['indus_class']}] from table [static_data_industry_{opt['dataset']['pool_name']}_history] + [{opt['dataset']['indus_table_suffix']}]]")
        print(f"Including industry id: {industry}")
        for indus_type in industry:
            if not exists_results(opt, test_month, indus_type):
                args.append((opt, test_month, indus_type))
    return args


def main(opt):
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
    if opt['mode']!= 'rt':
        save_report_disk(opt)


if __name__ == '__main__':
    print(get_env_info())
    parser = argparse.ArgumentParser()
    parser.add_argument('-root_path', type=str, default='./', help='Root path of project.')
    parser.add_argument('-option', type=str, default='option/eval/batch3_across_tickers_hs300_highprice_lgbm_15s.yaml', help='Path to option YAML file.')
    parser.add_argument('-is_realtime', action='store_true', help='Whether the phase is backtesting or realtime')
    parser.add_argument('-debug', action='store_true', help='Whether to use debug mode') # it'll contain ticker num <= 10
    args = parser.parse_args()
    opt = parse_options(args)
    main(opt)

