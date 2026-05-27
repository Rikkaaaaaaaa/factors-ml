import glob
from os import makedirs
import os.path as osp
import shutil
import numpy as np
import pandas as pd
import os

from utils.option import parse_options
from utils.mysql import read_table

def save_threshold_pct(train_proba_root_path, output_path):
    # read and merge all train proba
    train_signal = []
    for train_signal_path in sorted(os.listdir(train_proba_root_path)):
        train_signal.append(pd.read_csv((os.path.join(train_proba_root_path, train_signal_path))))
    train_proba = pd.concat(train_signal)
    train_proba = train_proba.sort_values(by=['ticker'])

    # define pct num list
    pct_num = [1, 3,5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 97, 99]
    threshold_df = pd.DataFrame()
    for pct in pct_num:
        pct_values = train_proba.groupby('ticker')['proba'].apply(lambda x: np.percentile(x, pct)).reset_index().rename(columns={'proba': f'pct_{pct}'})
        if threshold_df.empty:
            threshold_df = pct_values
        else:
            threshold_df = pd.merge(threshold_df, pct_values, on=['ticker'])

    # save to csv file
    threshold_df.to_csv(output_path)

    return


def push_realtime_files(config, model_period):
    if model_period == 'am':
        exp_name = config.am_exp_name
        output_root_path = osp.join(config.output_root_path, 'am')
    else:
        exp_name = config.pm_exp_name
        output_root_path = osp.join(config.output_root_path, 'pm')
    test_month = config.test_month
    root_path = config.root_path
    output_folder_name = config.output_folder_name
    pool_name = config.pool_name

    # deteck pool name
    if not pool_name in exp_name:
        raise ValueError(f"Pool name[{pool_name}] doesn't match exp_name[{exp_name}]!")

    highprice_folder = glob.glob(f'{root_path}/{exp_name}/{exp_name}*')
    folders = ['15s', '60s', '120s', '300s']
    saved_folders = ['ckpt', 'inference_params', 'preprocess_params', 'train_signal']
    print(f"Packaging all model files in {test_month} for {pool_name}...")
    for window in folders:
        window_path = osp.join(output_root_path, output_folder_name, pool_name, window)
        makedirs(window_path, exist_ok=True)
        for high_folder in highprice_folder:
            if window in high_folder and pool_name in high_folder:
                for folder in saved_folders:
                    src = osp.join(high_folder, str(test_month), folder)
                    dst = osp.join(window_path, folder)

                    if pool_name == "other" and len(os.listdir(src)) < 7:
                        raise ValueError(f"file nums less than 7 for stock pool: other in {src}")
                    elif pool_name == "zz2000_1" and len(os.listdir(src)) < 2:
                        raise ValueError(f"file nums less than 2 for stock zz2000_1: other in {src}")
                    elif pool_name == "zz2000_2" and len(os.listdir(src)) < 2:
                        raise ValueError(f"file nums less than 2 for stock zz2000_2: other in {src}")
                    elif pool_name == "zz2000_3" and len(os.listdir(src)) < 4:
                        raise ValueError(f"file nums less than 4 for stock zz2000_3: other in {src}")
                    elif pool_name in ['hs300', 'zz500', 'zz1000'] and len(os.listdir(src)) < 8:
                        raise ValueError(f"file nums less than 8 in {src}")

                    if not osp.exists(dst):
                        makedirs(dst)
                    # 处理preprocess_params文件夹中的文件，增加high/lowprice后缀
                    if folder == 'preprocess_params':
                        clip_params = []
                        std_params = []

                        for clip_csv in glob.glob(f'{src}/clip_*.csv'):
                            clip_params.append(pd.read_csv(clip_csv))
                        clip_params = pd.concat(clip_params, ignore_index=True)
                        clip_path = osp.join(dst, 'clip_params_highprice.csv')
                        clip_params.to_csv(clip_path, index=False)

                        for std_csv in glob.glob(f'{src}/std_*.csv'):
                            std_params.append(pd.read_csv(std_csv))
                        std_params = pd.concat(std_params, ignore_index=True)
                        std_path = osp.join(dst, 'std_params_highprice.csv')
                        std_params.to_csv(std_path, index=False)
                        print(f"[processing preprocessing params] Clip and std params have been saved at {clip_path} and {std_path}")

                    # compute and save threshold_pct to csv
                    elif folder == 'train_signal':
                        output_path = osp.join(dst, 'threshold_pct.csv')
                        save_threshold_pct(src, output_path)
                        print(f"[processing threshold pct] Threshold_pct has been computed and saved at {output_path}")

                    # others: copy all files to new folder
                    else:
                        [shutil.copy2(s, dst) for s in glob.glob(src.rstrip('/')+'/*')]
                        print(f"[processing {folder}] Files in {src} has been copied to {dst}")



def get_factor_name_from_15s(exp_path):
    # get factor list of 15s
    from utils.option import yaml_load
    from dataset import build_factor_name
    print(exp_path)
    opt = yaml_load(exp_path)
    training_factor_name = build_factor_name(opt['dataset']['training_factor_name'])
    return training_factor_name


def push_static_data(config):
    output_root_path = config.output_root_path
    test_month = config.test_month
    save_path = osp.join(output_root_path, "static_data")

    # save history static_data data from sql
    database = "strategy"
    for table in ["static_data_industry_bond_etf", "static_data_industry_hs300", "static_data_industry_zz500", "static_data_industry_zz1000", "static_data_industry_zz2000_1",
                  "static_data_industry_zz2000_2", "static_data_industry_zz2000_3","static_data_industry_other",
                  "static_data_price_bond_etf", "static_data_price_hs300","static_data_price_zz500","static_data_price_zz1000", "static_data_price_zz2000_1",
                  "static_data_price_zz2000_2", "static_data_price_zz2000_3","static_data_price_other"]:
        table = table + "_history"
        df = read_table(database, f"select * from {table} where test_month={test_month}")
        df.to_csv(osp.join(save_path, f'{table.replace("_history", "")}.csv'), encoding='utf-8')

    print(f"[processing static data] Static data in MySQL have been saved at {save_path}")

def push_factor_name(config, factor_name_file_name):
    output_root_path = config.output_root_path
    exp_name = config.am_exp_name # fetch static data from am experiment
    root_path = config.root_path
    save_path = osp.join(output_root_path, "static_data")

    # save factor names
    if not osp.exists(save_path):
        makedirs(save_path)
    factor_name_path = osp.join(save_path, factor_name_file_name)
    exp_path = osp.join( root_path, exp_name, f"{exp_name}_15s/{exp_name}_15s.yaml")
    factor_names = get_factor_name_from_15s(exp_path)
    pd.Series(factor_names, name="factor_name").to_csv(factor_name_path)
    print(f"[processing factor names] Factor names in 15s have been copied to {factor_name_path}")


def push_static_data_low_price(config):
    root_path = config.root_path
    output_root_path = config.output_root_path
    exp_name = config.exp_name_low_price
    test_month = config.test_month
    low_folder = osp.join(root_path, exp_name)
    # save factor names
    save_path = osp.join(output_root_path, "static_data")
    if not osp.exists(save_path):
        makedirs(save_path)
    factor_name_path = osp.join(save_path, "factor_name_low_price.csv")
    factor_name_src_path = osp.join(low_folder, str(test_month), "factor_name_low_price.csv")
    shutil.copy2(factor_name_src_path, factor_name_path)
    print(f"[processing factor names low price] Factor names for low price have been copied to {factor_name_path}")




def push_realtime_files_low_price(config, model_period):
    if model_period == 'am':
        output_root_path = osp.join(config.output_root_path, 'am')
    else:
        output_root_path = osp.join(config.output_root_path, 'pm')

    exp_name = config.exp_name_low_price
    test_month = config.test_month
    root_path = config.root_path
    output_folder_name = config.output_folder_name_low_price
    pool_name = config.pool_name

    # deteck pool name
    if not pool_name in exp_name:
        raise ValueError(f"Pool name[{pool_name}] doesn't match exp_name[{exp_name}]!")

    low_folder = osp.join(root_path, exp_name)
    saved_folders = ['ckpt', 'inference_params', 'preprocess_params']
    print(f"Packaging all low price model files in {test_month} for {pool_name}...")

    # target_path = osp.join(res_folder_path, pool_name, res_name)  # TODO
    target_path = osp.join(output_root_path, output_folder_name, pool_name)
    makedirs(target_path, exist_ok=True)

    if pool_name in low_folder:
        for folder in saved_folders:
            src = osp.join(low_folder, str(test_month), folder)
            dst = osp.join(target_path, folder)

            if not osp.exists(dst):
                makedirs(dst)
            # 处理preprocess_params文件夹中的文件，增加high/lowprice后缀
            if folder == 'preprocess_params':
                clip_params = []
                std_params = []

                if len(os.listdir(src)) < 4:
                    raise ValueError(f"file nums less than 4 for low price in {src}")

                for clip_csv in glob.glob(f'{src}/clip_*.csv'):
                    clip_params.append(pd.read_csv(clip_csv))
                clip_params = pd.concat(clip_params, ignore_index=True)
                clip_path = osp.join(dst, 'clip_params_lowprice.csv')
                clip_params.to_csv(clip_path, index=False)

                for std_csv in glob.glob(f'{src}/std_*.csv'):
                    std_params.append(pd.read_csv(std_csv))
                std_params = pd.concat(std_params, ignore_index=True)
                std_path = osp.join(dst, 'std_params_lowprice.csv')
                std_params.to_csv(std_path, index=False)

            # others: copy all files to new folder
            else:
                for bs_flag in ['b', 's']:
                    dst_with_bs_flag = osp.join(dst, bs_flag)
                    src_with_bs_flag = osp.join(src, bs_flag)

                    if len(os.listdir(src_with_bs_flag)) < 4:
                        raise ValueError(f"file nums less than 4 for low price in {src}")

                    makedirs(dst_with_bs_flag, exist_ok=True)
                    [shutil.copy2(s, dst_with_bs_flag) for s in glob.glob(src_with_bs_flag.rstrip('/')+'/*')]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='package model files for RT')
    parser.add_argument('--root_path', type=str, default='experiments', help="Root path of experiments")
    parser.add_argument('--test_month', type=int, default=202602, help="test_month")
    parser.add_argument('--pool_name', type=str, default="zz2000_2", help="pool name")
    parser.add_argument('--am_exp_name', type=str, default="prod_am_zz2000_2_highprice_lgbm", help="am experiment name")
    parser.add_argument('--pm_exp_name', type=str, default="prod_pm_zz2000_2_highprice_lgbm", help="pm experiment name")
    parser.add_argument('--output_root_path', type=str, default='./data_debug')
    parser.add_argument('--output_folder_name', type=str, default='lgbm')
    # low price
    parser.add_argument('--exp_name_low_price', type=str, default="low_price_zz2000_2_rt", help="experiment name low price")
    parser.add_argument('--output_folder_name_low_price', type=str, default='logit')
    config = parser.parse_args()

    # save highprice am and pm model
    if config.am_exp_name:
        push_realtime_files(config, model_period='am')
    else:
        print(f"[Error] There is no [am_exp_name] for {config.pool_name}!")
    if config.pm_exp_name:
        push_realtime_files(config, model_period='pm')
    else:
        print(f"[Error] There is no [pm_exp_name] for {config.pool_name}!")
    # save factor name
    if config.am_exp_name or config.pm_exp_name:
        push_factor_name(config, factor_name_file_name=f'batch3_{config.pool_name}_highprice_factor_name.csv')
    else:
        print(f"[Error] There is no [am_exp_name] or [pm_exp_name] for {config.pool_name}!")

    # package lowprice files
    if config.exp_name_low_price:
        push_realtime_files_low_price(config, model_period='am')
        push_realtime_files_low_price(config, model_period='pm')
        push_static_data_low_price(config)
    else:
        print(f"[Error] There is no [exp_name_low_price] for {config.pool_name}!")

    # save static data csv
    push_static_data(config)
