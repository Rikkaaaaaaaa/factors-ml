import glob
from os import makedirs
import os.path as osp
import shutil
import pandas as pd

from utils.option import parse_options

def push_realtime_files(root_path='experiments', exp_name="ddb_factor_hs300_highprice_lgbm" ,res_name='lgbm_data', res_folder_path='./data', test_month=202307):
    pool_name = 'hs300'
    highprice_folder = glob.glob(f'{root_path}/{exp_name}*')
    lowprice_folder = glob.glob(f'{root_path}/{exp_name}*')
    folders = ['15s', '60s', '120s', '300s']
    saved_folders = ['ckpt', 'inference_params', 'preprocess_params']

    print(f"Packaging all model files in {test_month}...")
    for window in folders:
        window_path = osp.join(res_folder_path, res_name, window)
        makedirs(window_path)
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

                    # others: copy all files to new folder
                    else:
                        [shutil.copy2(s, dst) for s in glob.glob(src.rstrip('/')+'/*')]

        for low_folder in lowprice_folder:
            if window in low_folder and pool_name in low_folder:
                for f in saved_folders:
                    src = osp.join(low_folder, str(test_month), f)
                    dst = osp.join(window_path, f)
                    if not osp.exists(dst):
                        makedirs(dst)

                    # 处理preprocess_params文件夹中的文件，增加high/lowprice后缀
                    if f == 'preprocess_params':
                        clip_params = []
                        std_params = []
                        for clip_csv in glob.glob(f'{src}/clip*'):
                            clip_params.append(pd.read_csv(clip_csv))
                        clip_params = pd.concat(clip_params, ignore_index=True)
                        clip_path = osp.join(dst, 'clip_params_lowprice.csv')
                        clip_params.to_csv(clip_path, index=False)

                        for std_csv in glob.glob(f'{src}/std*'):
                            std_params.append(pd.read_csv(std_csv))
                        std_params = pd.concat(std_params, ignore_index=True)
                        std_path = osp.join(dst, 'std_params_lowprice.csv')
                        std_params.to_csv(std_path, index=False)

                    else:
                        [shutil.copy2(s, dst) for s in glob.glob(src.rstrip('/') + '/*')]

    # save factor names
    save_path = osp.join(res_folder_path, "static_data")
    if not osp.exists(save_path):
        makedirs(save_path)
    factor_name_path = osp.join(save_path, "factor_name.csv")
    factor_names = get_factor_name_from_15s(exp_name)
    pd.Series(factor_names, name="factor_name").to_csv(factor_name_path)

    # save history static_data data from sql
    database = "strategy"
    for table in ["static_data_industry_hs300", "static_data_industry_zz500", "static_data_industry_zz1000", "static_data_price_hs300","static_data_price_zz500","static_data_price_zz1000"]:
        table = table + "_history"
        export_static_data(database, table, test_month, save_path)

    print(f"Suscessfully package all model files in {test_month}...")
def get_factor_name_from_15s(exp_name):
    # get factor list of 15s
    from utils.option import yaml_load
    from dataset import build_factor_name
    exp_path = osp.join("experiments", f"{exp_name}_15s/{exp_name}_15s.yaml")
    opt = yaml_load(exp_path)
    training_factor_name = build_factor_name(opt['dataset']['training_factor_name'])
    return training_factor_name

def export_static_data(database, table, test_month, save_path):
    from utils.mysql import read_table
    df = read_table(database, f"select * from {table} where test_month={test_month}")
    df.to_csv(osp.join(save_path, f'{table.replace("_history", "")}.csv'), encoding='utf-8')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='package model files for RT')
    parser.add_argument('--test_month', type=int, default=202412, help="test_month")
    parser.add_argument('--exp_name', type=str, default="ddb_factor_hs300_highprice_lgbm", help="experiment name")
    config = parser.parse_args()
    push_realtime_files(exp_name=config.exp_name, test_month=config.test_month)
