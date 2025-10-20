import glob
from os import makedirs
import os.path as osp
import shutil
import numpy as np
import pandas as pd
import os

from utils.option import parse_options

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


def push_realtime_files(config):
    exp_name = config.exp_name
    test_month = config.test_month
    root_path = config.root_path
    output_root_path= config.output_root_path
    output_folder_name = config.output_folder_name
    pool_name = config.pool_name

    # deteck pool name
    if not pool_name in exp_name:
        raise ValueError(f"Pool name[{pool_name}] doesn't match exp_name[{exp_name}]!")

    highprice_folder = glob.glob(f'{root_path}/{exp_name}*')
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
                        print(f"[Processing preprocessing params] Clip and std params have been saved at {clip_path} and {std_path}")

                    # compute and save threshold_pct to csv
                    elif folder == 'train_signal':

                        output_path = osp.join(dst, 'threshold_pct.csv')
                        save_threshold_pct(src, output_path)
                        print(f"[Processing threshold pct] Threshold_pct has been computed and saved at {output_path}")

                    # others: copy all files to new folder
                    else:
                        [shutil.copy2(s, dst) for s in glob.glob(src.rstrip('/')+'/*')]
                        print(f"[Processing {folder}] Files in {src} has been copied to {dst}")

    # save factor names
    save_path = osp.join(output_root_path, "static_data")
    if not osp.exists(save_path):
        makedirs(save_path)
    factor_name_path = osp.join(save_path, "factor_name.csv")
    factor_names = get_factor_name_from_15s(exp_name)
    pd.Series(factor_names, name="factor_name").to_csv(factor_name_path)
    print(f"[Processing factor names] Factor names in 15s have been copied to {factor_name_path}")

    # save history static_data data from sql
    database = "strategy"
    for table in ["static_data_industry_hs300", "static_data_industry_zz500", "static_data_industry_zz1000", "static_data_price_hs300","static_data_price_zz500","static_data_price_zz1000"]:
        table = table + "_history"
        export_static_data(database, table, test_month, save_path)
    print(f"[Processing static data] Static data in MySQL have been saved at {save_path}")

    print(f"Suscessfully package all model files in {test_month} to {output_folder_name}")
def get_factor_name_from_15s(exp_name):
    # get factor list of 15s
    from utils.option import yaml_load
    from dataset import build_factor_name
    exp_path = osp.join("experiments", f"{exp_name}_15s/{exp_name}_15s.yaml")
    print(exp_path)
    opt = yaml_load(exp_path)
    training_factor_name = build_factor_name(opt['dataset']['training_factor_name'])
    return training_factor_name


def export_static_data(database, table, test_month, save_path):
    from utils.mysql import read_table
    df = read_table(database, f"select * from {table} where test_month={test_month}")
    df.to_csv(osp.join(save_path, f'{table.replace("_history", "")}.csv'), encoding='utf-8')


def push_realtime_files_low_price(config):
    exp_name = config.exp_name_low_price
    test_month = config.test_month
    root_path = config.root_path
    output_root_path = config.output_root_path
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
                    makedirs(dst_with_bs_flag, exist_ok=True)
                    [shutil.copy2(s, dst_with_bs_flag) for s in glob.glob(src_with_bs_flag.rstrip('/')+'/*')]

    # save factor names
    save_path = osp.join(output_root_path, "static_data")
    if not osp.exists(save_path):
        makedirs(save_path)
    factor_name_path = osp.join(save_path, "factor_name_low_price.csv")
    factor_name_src_path = osp.join(low_folder, str(test_month), "factor_name_low_price.csv")
    shutil.copy2(factor_name_src_path, factor_name_path)
    print(f"[Processing factor names low price] Factor names for low price have been copied to {factor_name_path}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='package model files for RT')
    parser.add_argument('--root_path', type=str, default='experiments', help="Root path of experiments")
    parser.add_argument('--test_month', type=int, default=202510, help="test_month")
    parser.add_argument('--pool_name', type=str, default="zz500", help="pool name")
    parser.add_argument('--exp_name', type=str, default="prod_202510_ddb_null_factor_no_reverse_zz500_highprice_lgbm", help="experiment name")
    parser.add_argument('--output_root_path', type=str, default='./data')
    parser.add_argument('--output_folder_name', type=str, default='lgbm_data')
    # low price
    parser.add_argument('--exp_name_low_price', type=str, default="low_price_zz500_rt", help="experiment name low price")
    parser.add_argument('--output_folder_name-low_price', type=str, default='logit_data')

    config = parser.parse_args()
    push_realtime_files(config)
    push_realtime_files_low_price(config)
