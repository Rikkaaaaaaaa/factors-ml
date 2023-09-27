import numpy as np
import os.path as osp
import pandas as pd
from tqdm import tqdm
import traceback

from utils.misc import mkdir
from utils.logger import get_root_logger
from metric.base_metric import compute_metric, compute_metric_RT

class BackTester():
    """
    Backtester: include evaluation of model, metric of backtest and signal generation.

    Args:
        opt(dict): config for dataset, includes following keys:
            ...
        test_month(int): month needs to be eval
        indus_type(int): one of the indus_class

    Attrs:
        train_idx, test_idx: sample index, including date and time
        test_ret: test return values
        x_train, y_train: train data
        x_test, y_test: test data
        """
    def __init__(self, opt, test_month, indus_type):
        self.opt = opt
        self.test_month = test_month
        self.indus_type = indus_type
        self.class_num = self.opt['dataset']['class_num']
        self.is_backtest = self.opt['is_backtest']
        # logging file
        logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)
        self.logger.info(f'Backtester init successfully in {test_month} with indus {indus_type}')


    def backtest(self, factor_data, model):
        try:
            self.tickers = factor_data.tickers
            x_train = factor_data.x_train
            x_test = factor_data.x_test

            if self.opt['test']['bound_mode'] == 'by_indus':
                self.train_proba = model.predict(x_train)

            tbar = tqdm(self.tickers, leave=False)
            for ticker in tbar:
                tbar.set_description("Backtesting indus: {}, test month: {}".format(ticker, self.indus_type, self.test_month))
                self._ticker_ret = factor_data.test_ret[ticker]
                self._ticker_time = factor_data.test_idx[ticker]
                self._ticker = ticker

                # load test and train data in one ticker
                train_position = factor_data.train_position[ticker]
                test_position = factor_data.test_position[ticker]
                _x_train = x_train[train_position[0]: train_position[1]]
                _x_test = x_test[test_position[0]: test_position[1]]

                # get proba from prediction
                if self.opt['test']['bound_mode'] == 'by_ticker':
                    self.train_proba = model.predict(_x_train)
                self.pre_proba = model.predict(_x_test)

                # compute null idx in test data
                self.null_idx = np.isnan(_x_test).any(axis=1)

                # compute metric with not null data
                self.compute_results()

                # push signal dataframe into self.signals
                self.push_signal()

                #tbar.set_postfix({'loading_time': '{}'.format(self.summary),})

            # save all files
            self.save_results()
            self.save_bound()
            self.save_signals()
            self.logger.info(f"Backtesting finish with ticker num {len(self.tickers)}")

        except Exception as e:
            traceback.print_exc()
            print('Error backtesting {} in indus {}: '.format(ticker, self.indus_type), e)

    def runtime(self, factor_data, model):
        try:
            self.tickers = factor_data.tickers
            x_train = factor_data.x_train

            if self.opt['test']['bound_mode'] == 'by_indus':
                self.train_proba = model.predict(x_train)

            tbar = tqdm(self.tickers)
            for ticker in tbar:
                tbar.set_description("Backtesting {}, indus: {}, test month: {}".format(ticker, self.indus_type, self.test_month))
                self._ticker = ticker
                # load test and train data in one ticker
                train_position = factor_data.train_position[ticker]
                _x_train = x_train[train_position[0]: train_position[1]]

                # get proba from prediction
                if self.opt['test']['bound_mode'] == 'by_ticker':
                    self.train_proba = model.predict(_x_train)

                # compute metric with not null data
                self.compute_results()

                #tbar.set_postfix({'loading_time': '{}'.format(self.summary),})

            # save testing bounds
            self.save_results()
            self.save_bound()


        except Exception as e:
            traceback.print_exc()
            print('Error runtime: {} in indus {}: '.format(ticker, self.indus_type), e)

    def compute_results(self):
        # init summaries list
        if not hasattr(self, 'summaries'):
            self.summaries = []  # results summary
        # compute performance dict
        if self.is_backtest:
            self._summary = compute_metric(self.opt, self.pre_proba[~self.null_idx], self.train_proba, self._ticker_ret[~self.null_idx])
        else:
            self._summary = compute_metric_RT(self.opt, self.train_proba)
        self.summaries.append(list(self._summary.values()))
        # get metric keys in summary
        if not hasattr(self, 'metric_keys'):
            self.metric_keys = list(self._summary.keys())


    def save_results(self):
        self.results = pd.DataFrame(self.summaries, columns=self.metric_keys)
        self.results.insert(0, 'ticker', self.tickers)
        self.results.insert(1, 'month', self.indus_type)
        self.results.insert(2, 'indus_type', self.test_month)

        # save results file
        results_folder = osp.join(self.opt['path']['results_root'], str(self.test_month))
        mkdir(results_folder)
        results_name = 'results_month{}_indus{}.csv'.format(self.test_month, self.indus_type)
        results_path = osp.join(results_folder, results_name)
        self.results.reset_index(drop=True, inplace=True)
        self.results.to_csv(results_path, index=False)


    def save_bound(self):
        if not hasattr(self, 'results'):
            print('Please run compute_results before saving boundary values!')

        # save bound file
        inference_folder = osp.join(self.opt['path']['inference_root'], str(self.test_month))
        mkdir(inference_folder)
        bound_name = 'bound_month{}_indus{}.csv'.format(self.test_month, self.indus_type)
        bound_path = osp.join(inference_folder, bound_name)
        inference_cols = ['ticker', 'up_bound', 'down_bound']
        self.results[inference_cols].to_csv(bound_path, index=False)


    def push_signal(self):
        # init signals df list
        if not hasattr(self, 'signals'):
            self.signals = []
        signal = pd.DataFrame(columns=['ticker', 'time', 'date', 'signal', 'proba', 'up_bound', 'down_bound', ])
        signal['date'] = self._ticker_time['date']
        signal['time'] = self._ticker_time['time']
        signal['ticker'] = self._ticker
        signal['up_bound'] = self._summary['up_bound']
        signal['down_bound'] = self._summary['down_bound']

        # compute up/down signal according to proba and bound
        signal['proba'] = self.pre_proba
        signal_array = np.zeros(len(self.pre_proba))
        signal_array[signal_array > self._summary['up_bound']] = 1
        signal_array[1 - signal_array > self._summary['down_bound']] = -1
        signal_array[self.null_idx] = 0
        signal['signal'] = signal_array
        self.signals.append(signal)


    def save_signals(self):
        # save signal file
        signal_folder = osp.join(self.opt['path']['signal_root'], str(self.test_month))
        mkdir(signal_folder)
        signal_name = 'signal_month{}_indus{}.csv'.format(self.test_month, self.indus_type)
        signal_path = osp.join(signal_folder, signal_name)
        self.signals = pd.concat(self.signals, ignore_index=True)
        self.signals = self.signals[['ticker', 'time', 'date', 'signal', 'proba', 'up_bound', 'down_bound', ]]
        self.signals.to_csv(signal_path)




