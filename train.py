import multiprocessing as mp
import os.path as osp
import logging

from dataset.factor_dataset import FactorDataset
from dataset import check_indus
from model.lgbm_model import LgbmModel
from backtester import  BackTester
from utils.logger import get_root_logger, get_env_info
from utils.option import parse_options, dict2str
from utils.report import save_report_disk, write_signals_sql
from utils.misc import Timer, time_str, get_time_str, exists_results
from dataset import factor_all


def init(args):
    global lock
    lock = args[0]

def train_pipeline(train_args):
    opt, test_month, indus_type = train_args

    # logger init
    logger_name = f"month{test_month}_indus{indus_type}"
    log_file = osp.join(opt['path']['log'], f"{logger_name}_{get_time_str()}.log")
    logger = get_root_logger(logger_name=logger_name, log_level=logging.INFO, log_file=log_file)
    #logger.info(get_env_info())
    #logger.info(dict2str(opt))

    # get data set from test month
    dataset = FactorDataset(opt, test_month, indus_type)
    dataset.load_data()
    if dataset.is_empty:
        return

    # train lgbm model
    x_train, y_train = dataset.train_data[factor_all], dataset.train_data['class_label']
    model = LgbmModel(opt, test_month, indus_type)
    model.train(x_train, y_train)
    model.save_ckpt()

    # backtesting/realtime process
    backtester = BackTester(opt, test_month, indus_type)
    if opt['is_backtest']:
        backtester.backtest(dataset, model)


def gen_mp_args(opt):
    args = []
    for test_month in opt['dataset']['test_month']:
        industry = check_indus(opt, test_month)
        for indus_type in industry:
            if not exists_results(opt, test_month, indus_type):
                args.append((opt, test_month, indus_type))

    return args


def push_signal(opt, suffix=''):

    if 'hs300' in opt['dataset']['pool_name'] and 'zz500' in opt['dataset']['pool_name']:
        pool_name = 'zz800'
    else:
        pool_name = opt['dataset']['pool_name'][-1]
    if opt['dataset']['price_name'] == 'highprice':
        table_name = f"signal_{pool_name}_highprice_lgbm_{opt['dataset']['ret_name']}"
    else:
        table_name = f"signal_{pool_name}_lowpriceprice_lgbm_{opt['dataset']['ret_name']}"
    if len(suffix) > 0:
        table_name + f'_{suffix}'
    print(table_name)
    write_signals_sql(opt, table_name)


def main(opt):
    pool = mp.Pool(processes=opt['n_jobs'], )
    global_timer = Timer()
    args = gen_mp_args(opt)
    results = [pool.apply_async(train_pipeline, (arg,)) for arg in args]

    [result.get() for result in results]
    pool.close()
    pool.join()
    print("Task time is {}".format(time_str(global_timer.item())))


if __name__ == '__main__':

    root_path = './'
    opt = parse_options(root_path)
    main(opt)
    save_report_disk(opt)
    #push_signal(opt)
