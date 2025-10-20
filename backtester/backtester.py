import numpy as np
import os.path as osp
import pandas as pd
from tqdm import tqdm
import traceback

from utils.logger import get_root_logger
from metric.base_metric import compute_metric, compute_realtime_metric

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
        self.task_type = self.opt['dataset'].setdefault('task_type', 'classification')
        self.is_realtime = self.opt['is_realtime']
        # logging file
        logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)
        self.logger.info(f'{self.test_month}_indus_{self.indus_type}: Backtester init successfully')


    def backtest(self, factor_data, model):
        '''
        backtest data and save results. bound values and signals
         '''
        if hasattr(factor_data, 'selected_factor_name'):
            backtest_factor_name = factor_data.selected_factor_name
        else:
            backtest_factor_name = factor_data.training_factor_name

        # get ticker list
        if self.is_realtime:
            self.tickers = factor_data.tickers
        else:
            # Some tickers may be not consistent with static data, such as realtime data whose tickers are not incomplete
            self.tickers = factor_data.test_data["ticker"].unique()

        # bound_mode = 'by_indus'
        if self.opt['test']['bound_mode'] == 'by_indus':
            self.train_proba = model.predict(factor_data.train_data[backtest_factor_name])
            # filtered_train_proba = model.predict(factor_data.filtered_train_data[backtest_factor_name])
            # self.train_proba = np.concatenate((self.train_proba, filtered_train_proba), axis=0)

        # bound_mode = 'by_ticker'
        tbar = tqdm(self.tickers, leave=False)
        for ticker in tbar:
            try:
                self._ticker = ticker
                tbar.set_description(f"{self.test_month}_indus_{self.indus_type}: Backtesing ticker {ticker}")
                # load train data
                if self.opt['dataset'].get('balance') == 'reverse':
                    ticker_data_query = 'ticker==@ticker and augment==0'
                else:
                    ticker_data_query = 'ticker==@ticker'

                # select factor from train_data
                train_data = factor_data.train_data.query(ticker_data_query) # bound proba come from original data
                x_train = train_data[backtest_factor_name]

                #filtered_train_data = factor_data.filtered_train_data.query(ticker_data_query)  # bound proba come from original data
                #filtered_x_train = filtered_train_data[backtest_factor_name]


                # get train proba for bound computation
                if self.opt['test']['bound_mode'] == 'by_ticker':
                    self.train_proba = model.predict(x_train)
                    # ori_x_train = np.concatenate((x_train, filtered_x_train), axis=0)
                    # filtered_train_proba = model.predict(filtered_x_train)
                    # self.train_proba = np.concatenate((self.train_proba, filtered_train_proba)

                # BT mode: run inference
                if not self.is_realtime:
                    test_data = factor_data.test_data.query('ticker==@ticker')
                    x_test = test_data[backtest_factor_name]
                    # test ret time date ticker used for signal record
                    self._test_ret = test_data['ret']
                    self._test_time = test_data['time']
                    self._test_date = test_data['date']
                    self._pre_proba = model.predict(x_test)

                    # compute null idx in test data
                    # self._null_idx = np.isnan(test_data[list(backtest_factor_name) + ['ret']].values).any(axis=1)
                    #self._null_idx = np.isnan(test_data[list(backtest_factor_name) + ['ret']].values).all(axis=1) # del all nan
                    factor_null_idx = np.isnan(test_data[list(backtest_factor_name)].values).all(axis=1) # facor is all nan
                    ret_null_idx = np.isnan(test_data['ret'].values) # del return nan
                    # self._null_idx = factor_null_idx + ret_null_idx
                    self._null_idx = ret_null_idx
                    #self._null_idx = np.isnan(test_data[backtest_factor_name].values).any(axis=1) # factor nan

                # compute metric
                self.compute_metrics()

                # compute signal and proba
                # RT mode: append train proba into self.train_proba
                # BT mode: append train proba into self.train_proba and signal dataframe into self.signals
                self.compute_train_signal()
                if not self.is_realtime:
                    self.compute_signal()

            except Exception as e:
                traceback.print_exc()
                self.logger.info(f'{self.test_month}_indus_{self.indus_type}: Error backtesting in {ticker}', e)

        # save result and bound both in RT and BT
        self.save_results()
        self.save_bound()
        self.save_train_proba()
        # BT mode: save train and test signals
        if not self.is_realtime:
            self.save_signals()
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Backtesting finish with {len(self.tickers)} tickers")




    def compute_metrics(self):
        '''
        compute metric to summary for every ticker
        '''
        # init results dataframe list
        if not hasattr(self, 'results'):
            self.results = []  # results summary

        # compute bound and performance metrics
        if self.is_realtime:
            self._metric = compute_realtime_metric(self.opt, self.train_proba)
        else:
            # filter null data
            self._metric = compute_metric(self.opt, self._pre_proba[~self._null_idx], self.train_proba, self._test_ret[~self._null_idx])
            # self._metric = compute_metric(self.opt, self._pre_proba, self.train_proba, self._test_ret)
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
            print('Please run compute_metrics before saving boundary values!')
        # save bound file
        inference_folder = self.opt['path']['inference_path'][self.test_month]
        bound_name = 'bound_indus{}.csv'.format(self.indus_type)
        bound_path = osp.join(inference_folder, bound_name)
        inference_cols = ['ticker', 'up_bound', 'down_bound']
        self.results[inference_cols].to_csv(bound_path, index=False)


    def compute_signal(self):
        '''
        compute signals for one ticker
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
        # set signal to nan when null factor
        # signal_array[self._null_idx] = 0
        signal['signal'] = signal_array
        #signal['ret'] = self._test_ret.values

        self.signals.append(signal)

    def compute_train_signal(self):
        # if we need to save training proba
        if self.opt['train'].get('save_proba'):
            if not hasattr(self, 'train_signals'):
                self.train_signals = []
            train_signal = pd.DataFrame({'ticker': [self._ticker]*len(self.train_proba), 'proba': self.train_proba})
            self.train_signals.append(train_signal)


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

    def save_train_proba(self):
        # save training proba to train_signal_path
        if self.opt['train'].get('save_proba'):
            train_signal_folder = self.opt['path']['train_signal_path'][self.test_month]
            train_signal_name = 'train_signal_{}_indus{}.csv'.format(self.test_month, self.indus_type)
            train_signal_path = osp.join(train_signal_folder, train_signal_name)
            self.train_signals = pd.concat(self.train_signals, ignore_index=True)
            self.train_signals.to_csv(train_signal_path, index=False)


