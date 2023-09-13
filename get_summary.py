import glob
import argparse
import pandas as pd
import os

def compute_rate(df):
    df['up_signal_rate'] = df['up_trade_num'] / df['total_sample']
    df['down_signal_rate'] = df['down_trade_num'] / df['total_sample']
    return df


def get_summary(config):
    csv_folder = os.path.join(config.res_path, 'results')
    res_csv = glob.glob(csv_folder.rstrip('/') + '/*csv')
    res = []
    for r in res_csv:
        res.append(pd.read_csv(r))
    res = pd.concat(res).reset_index(drop=True)
    res = compute_rate(res)
    basename = os.path.basename(config.res_path)
    res.to_csv(os.path.join(config.res_path, basename + '_res.csv'), index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='concat hs300 result')
    parser.add_argument('--res_path', type=str, help="the path of csv results")
    parser.add_argument('--csv_name', type=str, default='summary', help="the path of final csv results")
    config = parser.parse_args()

    get_summary(config)
