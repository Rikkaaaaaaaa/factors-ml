from sklearn import metrics
from sklearn.metrics import precision_recall_curve, average_precision_score, PrecisionRecallDisplay
import pandas as pd
import os
import os.path as osp
import glob
import numpy as np
import matplotlib.pyplot as plt

from utils.mysql import cx_read_sql


def label_mask(df, ret_name, alpha=5e-4):
    if ret_name == '300s':
        alpha = 1e-3
    ret_series = df[ret_name]
    df['class_label'] = ret_series.mask(ret_series <= -1 * alpha, 0).mask(ret_series >= alpha, 1) \
        .mask((-1 * alpha < ret_series) & (ret_series < alpha), 2)


def plot_ticker_curve(experiment_name, month, ret_name):
    pre_prob = []
    label = []
    pre_results_folder = osp.join('../experiments', experiment_name, str(month), 'signal')
    for pre_file in glob.glob(pre_results_folder.rstrip('/') + '/*'):
        signal = pd.read_csv(pre_file)
        tickers = tuple(signal['ticker'].unique())
        labels = cx_read_sql('select ticker, date, time, ret_{}  from ret_{} where ticker in {}'.format(ret_name, month, tickers))
        label_mask(labels, f'ret_{ret_name}')
        labels =  labels.query('class_label < 2')
        data = pd.merge(signal, labels, on=['ticker', 'date', 'time'])
        pre_prob.extend(data['proba'].values)
        label.extend(data['class_label'].values)

        for ticker in tickers:
            data_ = data.query('ticker==@ticker')
            precision, recall, threshold = precision_recall_curve(data_['class_label'], data_['proba'], pos_label=1, )
            fig, ax = plt.subplots(figsize=(8,8))
            disp = PrecisionRecallDisplay( precision=precision, recall=recall, pos_label=1, average_precision=average_precision_score(data_['class_label'], data_['proba']))
            ax.set_title(f"{test_month} PR-Curve")
            disp.plot(ax=ax,)
            root = f'pr-curve/{experiment_name}'
            if not osp.exists(root):
                os.makedirs(root)
            plt.savefig(f'pr-curve/{experiment_name}/{ticker}_{month}.jpg')
            plt.close()

            fpr, tpr, threshold = metrics.roc_curve(data_['class_label'], data_['proba'])
            roc_auc = metrics.auc(fpr, tpr)
            plt.figure(figsize=(8, 8))
            plt.title(f"{test_month} ROC-Curve")
            plt.plot(fpr, tpr, 'b', label='Pred AUC = %0.4f' % roc_auc)
            plt.legend(loc='best')
            plt.ylim(0, 1)
            plt.xlim(0, 1)
            plt.ylabel('True Positive Rate')
            plt.xlabel('False Positive Rate')
            # corner
            plt.plot([0, 1], [0, 1], 'r--')
            root = f'roc-curve/{experiment_name}'
            if not osp.exists(root):
                os.makedirs(root)
            plt.savefig(f"roc-curve/{experiment_name}/{ticker}_{month}.jpg")
            plt.close()

    return np.array(pre_prob), np.array(label)



def plot_roc(experiment_name, test_month, label, pre_prob):
    fpr, tpr, threshold = metrics.roc_curve(label, pre_prob)
    roc_auc = metrics.auc(fpr, tpr)
    plt.figure(figsize=(8, 8))
    plt.title(f"{test_month} ROC-Curve")
    plt.plot(fpr, tpr, 'b', label='PRED AUC = %0.4f' % roc_auc)
    plt.legend(loc='best')
    plt.ylim(0, 1)
    plt.xlim(0, 1)
    plt.ylabel('True Positive Rate')
    plt.xlabel('False Positive Rate')
    # corner
    plt.plot([0, 1], [0, 1], 'r--')
    plt.savefig(f"roc-curve/{experiment_name}_{month}.jpg")


def plot_pr_curve(experiment_name, test_month, label, pre_prob, ticker=None):

    precision, recall, threshold = precision_recall_curve(label, pre_prob, pos_label=1, )
    fig, ax = plt.subplots(figsize=(8, 8))
    disp = PrecisionRecallDisplay(precision=precision, recall=recall, pos_label=1,
                                  average_precision=average_precision_score(data_['class_label'], data_['proba']))
    ax.set_title(f"{test_month} PR-Curve")
    disp.plot(ax=ax, )
    plt.savefig(f'pr-curve/{experiment_name}_{month}.jpg')
    plt.close()


if __name__ == '__main__':
    test_month = 202305
    ret_names = ['15s', ]#'60s', '120s', '300s']
    for ret_name in ret_names:
        experiment_name = f'zz800_highprice_lgbm_{ret_name}'
        pre_prob, label = plot_ticker_curve(experiment_name, test_month, ret_name)

