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
from utils.option import parse_options, parse_opt_manager, dict2str
from utils.publish import save_report_disk, push_signal_sql
from utils.misc import Timer, time_str, get_time_str, exists_results, ensure_path


def init_lock(l):
    global dataset_lock
    dataset_lock = l

def train_pipeline(train_args):
    opt_manager, test_month, indus_type, train_sub_option_names = train_args
    cache_data = None
    for sub_opt_name in opt_manager['sub_options'].keys():
        # filter option to avoid overwrite experiment results
        if not sub_opt_name in train_sub_option_names:
            continue
        opt = opt_manager['sub_options'][sub_opt_name]
        # logger init
        logger_name = f"month{test_month}_indus{indus_type}_{sub_opt_name}"
        log_file = osp.join(opt['path']['log'], f"{logger_name}_{get_time_str()}.log")
        logger = get_root_logger(logger_name=logger_name, log_level=logging.INFO, log_file=log_file)
        logger.info(f"[{logger_name}] Traning data return name is {sub_opt_name}")

        # define task type
        task_type = opt['dataset'].setdefault('task_type', 'classification')
        if task_type == 'classification':
            label_col_name = 'class_label'
        else:
            label_col_name = 'ret'

        # get data set from test month
        dataset = build_dataset(opt, test_month=test_month, indus_type=indus_type, logger_name=logger_name)

        # load data
        load_timer = Timer()
        load_timer.start()
        if cache_data is None:
            logger.info(f"[{logger_name}] Loading factor and return from database")
            dataset_lock.acquire()
            cache_data = dataset.load_data(cache=True)
            dataset_lock.release()
            logger.info(f"[{logger_name}] Suscessfully Load data from [database] with cost={time_str(load_timer.item())}")
        else:
            logger.info(f"[{logger_name}] Loading factor and return from cache data")
            dataset.load_data(cache=False, data=cache_data)
            logger.info(f"[{logger_name}] Suscessfully load data from [cache data] with cost={time_str(load_timer.item())}")

        if dataset.is_empty:
            logger.info(f"[{logger_name}] Dataset is empty!")
            return
        x_train, y_train = dataset.train_data[dataset.training_factor_name], dataset.train_data[label_col_name]

        # factor selection
        training_factor_name = dataset.training_factor_name
        if opt.get('feature_selector'):
            feature_selector = build_selector(opt, test_month=test_month, indus_type=indus_type)
            selected_factor_name = feature_selector.select_factor(x_train, y_train)
            dataset.set_selected_factor(selected_factor_name)
            training_factor_name = dataset.selected_factor_name
            logger.info(f"[{logger_name}] Applying feature selection, total training factor num is: {len(training_factor_name)}")

        # train model
        model = build_model(opt, test_month=test_month, indus_type=indus_type, logger_name=logger_name)
        model.train(x_train[training_factor_name], y_train)
        model.save()

        # backtesting or record inference_bound
        backtester = BackTester(opt, test_month, indus_type, logger_name=logger_name)
        backtester.backtest(dataset, model)

def init_args(opt_manager):
    # ... (函数体保持不变) ...
    args = []

    for test_month in opt_manager['dataset']['test_month']:
        industry = check_indus(opt_manager, test_month)
        if opt_manager['dataset'].setdefault('selected_indus'):
            selected_industry = opt_manager['dataset']['selected_indus']
            industry = [indus for indus in industry if indus in selected_industry]
            print(f"[option manager] {test_month}: Selected indus is {selected_industry}")
        print(f"[option manager] {test_month}: Loading indus by [{opt_manager['dataset']['indus_class']}] from table [static_data_industry_{opt_manager['dataset']['pool_name']}_history] + [{opt_manager['dataset']['indus_table_suffix']}]]")
        print(f"[option manager] {test_month}: Running industry id: {industry}")
        for indus_type in industry:
            # check whether any result of sub options doesn't exist
            train_sub_option_names = []
            for sub_opt_name in opt_manager['sub_options'].keys():
                sub_opt = opt_manager['sub_options'][sub_opt_name]
                if not exists_results(sub_opt, test_month, indus_type) or opt_manager['mode']=='eval':
                    # if not exists one of sub options, append to args
                    train_sub_option_names.append(sub_opt_name)
            args.append((opt_manager, test_month, indus_type, train_sub_option_names))
    return args


def main(opt_manager):
    # mp training
    manager = mp.Manager()
    dataset_lock = manager.Lock()
    pool = mp.Pool(processes=opt_manager['n_jobs'], initializer=init_lock, initargs=(dataset_lock,), maxtasksperchild=1)
    global_timer = Timer()
    args = init_args(opt_manager)
    
    # 提交所有任务到进程池
    async_results = [pool.apply_async(train_pipeline, (arg,)) for arg in args]
    failed_tasks = []  # 用于记录失败的任务信息
    for task_arg, async_result in zip(args, async_results):
        try:
            # 等待任务完成，如果子进程有未捕获的异常，会在这里抛出
            async_result.get()
        except Exception as e:
            # 从任务参数中提取标识信息
            _, test_month, indus_type, train_sub_option_names = task_arg
            # 记录失败任务的关键信息
            error_info = {
                'test_month': test_month,
                'indus_type': indus_type,
                'sub_options_to_train': train_sub_option_names,
                'exception_type': type(e).__name__,
                'exception_msg': str(e),
                'traceback': traceback.format_exc()  # 获取完整的错误堆栈
            }
            failed_tasks.append(error_info)
            # 立即打印错误，方便实时查看
            print(f"\n[ERROR] 任务执行失败: {error_info['sub_options_to_train']}")
            print(f"        异常类型: {error_info['exception_type']}")
            print(f"        异常信息: {error_info['exception_msg']}")
            # 立即打印详细堆栈
            print(f"        错误堆栈:\n{error_info['traceback']}")
    
    pool.close()
    pool.join()
    
    # --- 所有任务执行完毕后，汇总报告 ---
    print(f"\n{'='*60}")
    print(f"[option manager] 任务 [{opt_manager['base_name']}] 总耗时 {time_str(global_timer.item())}")
    if failed_tasks:
        print(f"[警告] 共有 {len(failed_tasks)} 个任务执行失败:")
        for i, err in enumerate(failed_tasks, 1):
            print(f"  失败任务 {i}: test_month={err['test_month']}, indus_type={err['indus_type']}, "
                  f"sub_options={err['sub_options_to_train']}")
            print(f"      原因: {err['exception_type']}: {err['exception_msg']}")
        # 可以选择将详细的错误堆栈记录到文件，避免输出过长
        error_log_file = f"task_errors_{opt_manager['base_name']}_{get_time_str()}.log"
        with open(error_log_file, 'w') as f:
            for err in failed_tasks:
                f.write(f"Failed task: {err['test_month']}, {err['indus_type']}\n")
                f.write(f"Exception: {err['traceback']}\n")
                f.write("-"*50 + "\n")
        print(f"  详细错误堆栈已保存至: {error_log_file}")
    else:
        print(f"[完成] 所有任务执行成功。")
    print('='*60)
    
    # save report 
    if not opt_manager['is_realtime'] and not failed_tasks: 
        for sub_opt_name in opt_manager['sub_options'].keys():
            opt = opt_manager['sub_options'][sub_opt_name]
            save_report_disk(opt)


if __name__ == '__main__':
    print(get_env_info())
    parser = argparse.ArgumentParser()
    parser.add_argument('-root_path', type=str, default='./', help='Root path of project.')
    parser.add_argument('-option', type=str, default='./option/opt_manager/other/am_model/am_model_other_highprice_lgbm_opt_manager.yaml', help='Path to option YAML file.')
    parser.add_argument('-is_realtime', action='store_true', help='Whether the phase is backtesting or realtime')
    parser.add_argument('-debug', action='store_true', help='Whether to use debug mode') # it'll contain ticker num <= 10
    args = parser.parse_args()
    opt_manager = parse_opt_manager(args)
    main(opt_manager)



