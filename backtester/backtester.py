import numpy as np
import os.path as osp
import pandas as pd
from tqdm import tqdm
import traceback
from sklearn.decomposition import PCA

from dataset import build_factor_name
from utils.logger import get_root_logger
from metric.base_metric import compute_metric, compute_runtime_metric

class BackTester():
    """
    Backtester: include evaluation of models, metric of backtest and signal generation.

    Args:
        opt(dict): option for dataset, includes following keys:
            ...
        test_month(int): month needs to be eval
        indus_type(int): one of the indus_class

        """
    def __init__(self, opt, test_month, indus_type):
        self.opt = opt
        self.test_month = test_month
        self.indus_type = indus_type
        self.class_num = self.opt['dataset']['class_num']
        self.is_runtime = self.opt['is_runtime']
        self.training_factor_name = build_factor_name(self.opt['dataset']['training_factor_name'])
        # logging file
        logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)
        self.logger.info(f'{self.test_month}_indus_{self.indus_type}: Backtester init successfully')


    def backtest(self, factor_data, model):
        '''
        backtest data and save results. bound values and signals
         '''
        if hasattr(factor_data, 'selected_factor') and self.opt['feature_selector']['type'] != 'PCASelector':
            self.training_factor_name = factor_data.selected_factor

        try:
            self.tickers = factor_data.tickers
            if self.opt['test']['bound_mode'] == 'by_indus':
                self._train_proba = model.predict(factor_data.train_data[self.training_factor_name])

            tbar = tqdm(self.tickers, leave=False)
            for ticker in tbar:
                tbar.set_description(f"{self.test_month}_indus_{self.indus_type}: Backtesing ticker {ticker}")
                # load train and test array from dataframe
                if self.opt['dataset'].get('balance') == 'reverse':
                    ticker_data_query = 'ticker==@ticker and augment==0'
                else:
                    ticker_data_query = 'ticker==@ticker'
                train_data = factor_data.train_data.query(ticker_data_query) # bound proba come from original data
                test_data = factor_data.test_data.query('ticker==@ticker')
                # PCA by indus
                if hasattr(factor_data, 'selected_factor') and self.opt['feature_selector']['type'] == 'PCASelector':
                    x_train = train_data[self.training_factor_name].copy()
                    train_null_idx = np.isnan(x_train)
                    x_train = x_train.fillna(0)
                    x_train = factor_data.selected_factor.inverse_transform(factor_data.selected_factor.transform(x_train))
                    x_train[train_null_idx] = np.nan

                    x_test = test_data[self.training_factor_name].copy()
                    test_null_idx = np.isnan(x_test)
                    x_test = x_test.fillna(0)
                    x_test = factor_data.selected_factor.inverse_transform(factor_data.selected_factor.transform(x_test))
                    x_test[test_null_idx] = np.nan
                else:
                    x_train = train_data[self.training_factor_name]
                    x_test = test_data[self.training_factor_name]

                # test ret time date ticker used for signal record
                self._ticker = ticker
                self._test_ret = test_data['ret']
                self._test_time = test_data['time']
                self._test_date = test_data['date']

                # get proba from prediction
                if self.opt['test']['bound_mode'] == 'by_ticker':
                    self._train_proba = model.predict(x_train)
                self._pre_proba = model.predict(x_test)

                # compute null idx in test data
                #self._null_idx = np.isnan(test_data[self.training_factor_name + ['ret']].values).any(axis=1)
                training_factor_name = test_data.drop(['ticker', 'date', 'time', 'class_label', 'ret'], axis=1).columns
                self._null_idx = np.isnan(test_data[list(training_factor_name) + ['ret']].values).any(axis=1)
                #self._null_idx = np.isnan(test_data[self.training_factor_name].values).any(axis=1) # factor nan

                # compute metric with not null data
                self.compute_results()

                # push signal dataframe into self.signals
                self.compute_signal()

            # save all files
            self.save_results()
            self.save_bound()
            self.save_signals()
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Backtesting finish with {len(self.tickers)} tickers")

        except Exception as e:
            traceback.print_exc()
            self.logger.info(f'{self.test_month}_indus_{self.indus_type}: Error backtesting in {ticker}', e)


    def compute_results(self):
        '''
        compute metric to summary for every ticker
        '''
        # init results dataframe list
        if not hasattr(self, 'results'):
            self.results = []  # results summary

        # compute performance dict
        if self.is_runtime:
            self._metric = compute_runtime_metric(self.opt, self._train_proba)
        else:
            # filter null data
            self._metric = compute_metric(self.opt, self._pre_proba[~self._null_idx], self._train_proba, self._test_ret[~self._null_idx])
            # self._metric = compute_metric(self.opt, self._pre_proba, self._train_proba, self._test_ret)
        self.results.append(list(self._metric.values()))

        # get metric keys in summary
        if not hasattr(self, 'metric_keys'):
            self.metric_keys = list(self._metric.keys())


    def save_results(self):
        '''
        save summary to backtesting results for all tickers
        '''
        self.results = pd.DataFrame(self.results, columns=self.metric_keys)
        self.results.insert(0, 'ticker', self.tickers)
        self.results.insert(1, 'month', self.test_month)
        self.results.insert(2, 'indus_type', self.indus_type)

        # save results file
        if not self.is_runtime:
            results_folder =  self.opt['path']['results_path'][self.test_month]
            results_name = 'results_{}_indus{}.csv'.format(self.test_month, self.indus_type)
            results_path = osp.join(results_folder, results_name)
            self.results.reset_index(drop=True, inplace=True)
            self.results.to_csv(results_path, index=False)


    def save_bound(self):
        '''
        save bound values for all toickers
        '''
        if not hasattr(self, 'results'):
            print('Please run compute_results before saving boundary values!')
        # save bound file
        inference_folder = self.opt['path']['inference_path'][self.test_month]
        bound_name = 'bound_indus{}.csv'.format(self.indus_type)
        bound_path = osp.join(inference_folder, bound_name)
        inference_cols = ['ticker', 'up_bound', 'down_bound']
        self.results[inference_cols].to_csv(bound_path, index=False)


    def compute_signal(self):
        '''
        compute signals for one tickers
        '''
        # init signals df list
        if not hasattr(self, 'signals'):
            self.signals = []
        signal = pd.DataFrame(columns=['ticker', 'time', 'date', 'signal', 'proba', 'up_bound', 'down_bound', ])
        # insert test data index
        signal['date'] = self._test_date
        signal['time'] = self._test_time
        signal['ticker'] = self._ticker
        signal['up_bound'] = self._metric['up_bound']
        signal['down_bound'] = self._metric['down_bound']
        # compute up/down signal according to proba and bound
        signal['proba'] = self._pre_proba
        signal_array = np.zeros(len(self._pre_proba))
        signal_array[signal['proba'] > self._metric['up_bound']] = 1
        signal_array[1 - signal['proba'] > self._metric['down_bound']] = -1
        signal_array[self._null_idx] = np.nan
        signal['signal'] = signal_array
        self.signals.append(signal)


    def save_signals(self):
        '''
        save signal file for all tickers
        '''
        signal_folder = self.opt['path']['signal_path'][self.test_month]
        signal_name = 'signal_{}_indus{}.csv'.format(self.test_month, self.indus_type)
        signal_path = osp.join(signal_folder, signal_name)
        self.signals = pd.concat(self.signals, ignore_index=True)
        self.signals = self.signals[['ticker', 'time', 'date', 'signal', 'proba', 'up_bound', 'down_bound', ]]
        self.signals.to_csv(signal_path, index=False)


    def runtime(self, factor_data, model):
        '''
        backtest data and save results. bound values and signals
         '''
        try:
            self.tickers = factor_data.tickers
            if self.opt['test']['bound_mode'] == 'by_indus':
                self._train_proba = model.predict(factor_data.train_data[self.training_factor_name])

            tbar = tqdm(self.tickers, leave=False)
            for ticker in tbar:
                tbar.set_description(f"{self.test_month}_indus_{self.indus_type}: Backtesing ticker {ticker}")

                # load train and test array from df
                if self.opt['dataset'].get('balance') == 'reverse':
                    ticker_data_query = 'ticker==@ticker and augment==0'
                else:
                    ticker_data_query = 'ticker==@ticker'
                train_data = factor_data.train_data.query(ticker_data_query)
                x_train = train_data[self.training_factor_name]
                self._ticker = ticker

                # get proba from prediction
                if self.opt['test']['bound_mode'] == 'by_ticker':
                    self._train_proba = model.predict(x_train)

                # compute runtime metric with train data
                self.compute_results()

            # save bound values
            self.save_results()
            self.save_bound()
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Runtime params saving finish with {len(self.tickers)} tickers")

        except Exception as e:
            traceback.print_exc()
            self.logger.info(f'{self.test_month}_indus_{self.indus_type}: Error backtesting in {ticker}', e)

