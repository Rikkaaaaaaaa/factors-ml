import numpy as np
import os.path as osp
import pandas as pd

from backtester.backtester import BackTester
from metric.base_metric import compute_realtime_metric
from metric.base_metric_long_term import compute_metric_long_term


class BackTesterLongTerm(BackTester):
    def __init__(self, opt, test_month, indus_type, logger_name=None):
        super().__init__(opt, test_month, indus_type, logger_name)
        self.long_ret_name = self.opt['dataset'].get('long_ret_name', 'long_ret_10min')
        self.short_ret_name = self.opt['dataset'].get('short_ret_name', 'short_ret_10min')
        self.logger.info(
            f'[{self.logger_name}] BackTesterLongTerm enabled with '
            f'long_ret=[{self.long_ret_name}] short_ret=[{self.short_ret_name}]'
        )

    def attach_test_returns(self, test_data):
        self._test_ret = test_data['ret']
        self._test_long_ret = test_data[self.long_ret_name]
        self._test_short_ret = test_data[self.short_ret_name]
        self._test_time = test_data['time']
        self._test_date = test_data['date']

    def compute_null_idx(self, test_data, backtest_factor_name):
        self.factor_null_idx = np.isnan(test_data[list(backtest_factor_name)].values).all(axis=1)
        self.long_ret_null_idx = np.isnan(test_data[self.long_ret_name].values)
        self.short_ret_null_idx = np.isnan(test_data[self.short_ret_name].values)
        self.ret_null_idx = self.long_ret_null_idx | self.short_ret_null_idx
        self._null_idx = self.factor_null_idx | self.ret_null_idx

    def backtest_eval(self, factor_data, model):
        if hasattr(factor_data, 'selected_factor_name'):
            backtest_factor_name = factor_data.selected_factor_name
        else:
            backtest_factor_name = factor_data.training_factor_name

        test_tickers = set(factor_data.test_data["ticker"].unique())
        train_tickers = set(factor_data.tickers)
        if self.mode == 'eval':
            self.tickers = list(test_tickers & train_tickers)
        elif self.mode == 'rt':
            self.tickers = train_tickers
        else:
            self.tickers = train_tickers

        inference_folder = self.opt['path']['pretrain_inference_path'][self.test_month]
        bound_name = 'bound_indus{}.csv'.format(self.indus_type)
        bound_path = osp.join(inference_folder, bound_name)
        self.threshold = pd.read_csv(bound_path)

        for ticker in self.tickers:
            try:
                self._ticker = ticker
                test_data = factor_data.test_data.query('ticker==@ticker')
                x_test = test_data[backtest_factor_name]
                self.attach_test_returns(test_data)
                self._pre_proba = model.predict(x_test)
                self.compute_null_idx(test_data, backtest_factor_name)
                self.compute_metrics()
                if len(self._pre_proba) != 0:
                    self.compute_signal()
            except Exception as e:
                self.logger.info(f'[{self.logger_name}] Error backtesting evaluation in {ticker}', e, exc_info=True)

        self.save_results()
        self.save_signals()
        self.logger.info(f"[{self.logger_name}] Backtesting evaluation finish with {len(self.tickers)} tickers")

    def compute_metrics(self):
        if not hasattr(self, 'results'):
            self.results = []

        if self.mode == 'rt':
            self._metric = compute_realtime_metric(self.opt, self.train_proba)
        elif self.mode == 'eval':
            self._metric = compute_metric_long_term(
                self.opt,
                self._pre_proba[~self._null_idx],
                np.zeros_like(self._pre_proba),
                self._test_long_ret[~self._null_idx],
                self._test_short_ret[~self._null_idx],
                self.threshold.query("ticker==@self._ticker")
            )
        elif self.mode == 'train' and self.compute_bound_only:
            self._metric = compute_realtime_metric(self.opt, self.train_proba)
        else:
            self._metric = compute_metric_long_term(
                self.opt,
                self._pre_proba[~self._null_idx],
                self.train_proba,
                self._test_long_ret[~self._null_idx],
                self._test_short_ret[~self._null_idx]
            )
        self.results.append(list(self._metric.values()))

        if not hasattr(self, 'metric_keys'):
            self.metric_keys = list(self._metric.keys())

    def backtest(self, factor_data, model):
        if hasattr(factor_data, 'selected_factor_name'):
            backtest_factor_name = factor_data.selected_factor_name
        else:
            backtest_factor_name = factor_data.training_factor_name

        test_tickers = set(factor_data.test_data["ticker"].unique())
        train_tickers = set(factor_data.tickers)
        if self.mode == 'eval':
            self.tickers = list(test_tickers & train_tickers)
        elif self.mode == 'rt':
            self.tickers = train_tickers
        else:
            self.tickers = train_tickers

        self.tickers = list(self.tickers)
        self.logger.info(f'[{self.logger_name}] Backtesting ticker num is {len(self.tickers)}')

        if self.opt['test']['bound_mode'] == 'by_indus':
            self.train_proba = model.predict(factor_data.train_data[backtest_factor_name])

        for ticker in self.tickers:
            try:
                self._ticker = ticker
                if self.opt['dataset'].get('balance') == 'reverse':
                    ticker_data_query = 'ticker==@ticker and augment==0'
                else:
                    ticker_data_query = 'ticker==@ticker'

                train_data = factor_data.train_data.query(ticker_data_query)
                x_train = train_data[backtest_factor_name]

                if self.opt['test']['bound_mode'] == 'by_ticker':
                    self.train_proba = model.predict(x_train)

                test_data = factor_data.test_data.query('ticker==@ticker')
                if len(test_data) == 0 or self.mode == 'rt':
                    self.compute_bound_only = True
                else:
                    self.compute_bound_only = False
                    x_test = test_data[backtest_factor_name]
                    self.attach_test_returns(test_data)
                    self._pre_proba = model.predict(x_test)
                    self.compute_null_idx(test_data, backtest_factor_name)

                self.compute_metrics()
                self.compute_train_signal()
                if (self.mode != 'rt') and len(getattr(self, '_pre_proba', [])) != 0 and not self.compute_bound_only:
                    self.compute_signal()

            except Exception as e:
                self.logger.error(f'[{self.logger_name}] Error backtesting in {ticker}', e, exc_info=True)

        self.save_results()
        self.save_bound()
        self.save_train_proba()
        if self.mode != 'rt':
            self.save_signals()
        self.logger.info(f"[{self.logger_name}] Backtesting finish with {len(self.tickers)} tickers")

    def compute_signal(self):
        if not hasattr(self, 'signals'):
            self.signals = []
        signal = pd.DataFrame(columns=[
            'ticker', 'time', 'date', 'signal', 'proba', 'up_bound', 'down_bound',
            'long_ret', 'short_ret'
        ])
        signal['date'] = self._test_date
        signal['time'] = self._test_time
        signal['ticker'] = self._ticker
        signal['up_bound'] = self._metric['up_bound']
        signal['down_bound'] = self._metric['down_bound']
        signal['proba'] = self._pre_proba
        signal['long_ret'] = self._test_long_ret.values
        signal['short_ret'] = self._test_short_ret.values
        signal_array = np.zeros(len(self._pre_proba))
        signal_array[signal['proba'] > self._metric['up_bound']] = 1
        signal_array[1 - signal['proba'] > self._metric['down_bound']] = -1
        signal_array[self.factor_null_idx] = 0
        signal['signal'] = signal_array
        self.signals.append(signal)

    def save_signals(self):
        signal_folder = self.opt['path']['signal_path'][self.test_month]
        signal_name = 'signal_{}_indus{}.csv'.format(self.test_month, self.indus_type)
        signal_path = osp.join(signal_folder, signal_name)
        self.signals = pd.concat(self.signals, ignore_index=True)
        self.signals = self.signals[
            ['ticker', 'time', 'date', 'signal', 'proba', 'up_bound', 'down_bound', 'long_ret', 'short_ret']
        ]
        self.signals.to_csv(signal_path, index=False)
