import glob
import argparse
import pandas as pd
import os

from utils.option import parse_options


def push_report(opt):
    res_path = opt['path']['results_root']
    report = []
    for month in os.listdir(res_path):
        csv_folder = os.path.join(res_path, month)
        res_csv = glob.glob(csv_folder.rstrip('/') + '/*csv')
        for r in res_csv:
            report.append(pd.read_csv(r))
    report = pd.concat(report).reset_index(drop=True)
    report= report.reset_index(drop=True)
    report.to_csv(os.path.join(res_path, '{}_report.csv'.format(opt['name'])), index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-config', type=str, default='', help='Path to option YAML file.')
    parser.add_argument('-is_backtest', type=bool, default=True, help='Whether the phase is backtesting')
    args = parser.parse_args()

    config_path = '../config/wind1_lgbm_alpha5_15s.yaml'
    root_path = '../'

    push_report(parse_options(root_path, config_path))
