import pandas as pd
import os.path as osp






def analyse_report(experiment_name, test_month):
    report_path = osp.join('experiments', experiment_name, experiment_name+'_report.csv')
    data = pd.read_csv(report_path)
    #tickers =
    report = data.query('month==@test_month')
    weighted_ret = rep


if __name__ == '__main__':
    test_month = 202305
    ret_names = ['15s', ]  # '60s', '120s', '300s']
    for ret_name in ret_names:
        experiment_name = f'zz800_highprice_lgbm_{ret_name}'
        pre_prob, label = plot_ticker_curve(experiment_name, test_month, ret_name)
