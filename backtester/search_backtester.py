import numpy as np
import os.path as osp
import pandas as pd
from tqdm import tqdm
import traceback

from dataset import build_factor_name
from utils.logger import get_root_logger
from metric.base_metric import compute_metric, compute_runtime_metric

class SearchBackTester():
    """
    Backtester: include evaluation and searching method of models

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


    def search_params(self, factor_data, model):
        '''
        backtest data and save results. bound values and signals
         '''
        if hasattr(factor_data, 'selected_factor'):
            self.training_factor_name = factor_data.selected_factor

        try:
            self.tickers = factor_data.tickers
            if self.opt['test']['bound_mode'] == 'by_indus':
                self._train_proba = model.predict(factor_data.train_data[self.training_factor_name])

            tbar = tqdm(self.tickers, leave=False)
            for ticker in tbar:
                tbar.set_description(f"{self.test_month}_indus_{self.indus_type}: Backtesing ticker {ticker}")
                # load train and test array from dataframe
                train_data = factor_data.train_data.query('ticker==@ticker and augment==0') # bound proba come from original data
                test_data = factor_data.test_data.query('ticker==@ticker')
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
                self._null_idx = np.isnan(test_data[self.training_factor_name + ['ret']].values).any(axis=1)
                #self._null_idx = np.isnan(test_data[self.training_factor_name].values).any(axis=1) # factor nan

                # compute metric with not null data
                self.compute_results()

            # save all files
            self.compute_loss()
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: loss values is {self.loss*1e4:.2f} bps")

        except Exception as e:
            traceback.print_exc()
            self.logger.info(f'{self.test_month}_indus_{self.indus_type}: Error searching params in {ticker}', e)


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


    def compute_loss(self):
        '''
        save summary to backtesting results for all tickers
        '''
        self.results = pd.DataFrame(self.results, columns=self.metric_keys)
        self.results.insert(0, 'ticker', self.tickers)
        self.results.insert(1, 'month', self.test_month)
        self.results.insert(2, 'indus_type', self.indus_type)

        self.loss = np.mean(self.results['up_signal_rate']*self.results['up_mean_ret'] - \
                    self.results['down_signal_rate']*self.results['down_mean_ret'])







