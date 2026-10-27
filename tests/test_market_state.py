"""离线验证分组逻辑；数据库和模型用替身，不连接生产库。"""
import importlib.util
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd


# 独立加载新模块，让本测试无需安装数据库客户端或 LightGBM。
spec = importlib.util.spec_from_file_location('market_state_under_test',
                                            Path(__file__).resolve().parents[1] / 'market_state.py')
state = importlib.util.module_from_spec(spec)
with patch.dict('sys.modules', {'models': SimpleNamespace(build_model=Mock()),
                                'utils.ddb': SimpleNamespace(read_ddb=Mock())}):
    spec.loader.exec_module(state)


class MarketStateTest(unittest.TestCase):
    def test_exact_keys_and_all_groups(self):
        timestamps = pd.date_range('2026-01-05 09:30:01', periods=14, freq='15s')
        raw = pd.DataFrame({'ticker': ['A.SZ'] * 14, 'time': timestamps,
                            'market_state': list(range(12)) + [99, np.nan]})
        times = timestamps.hour * 10000000 + timestamps.minute * 100000 + timestamps.second * 1000
        train = pd.DataFrame({'ticker': ['A.SZ'] * 14, 'date': [20260105] * 14, 'time': times})
        # 故意重复原始索引、打乱行序：不应按 DataFrame index 错配。
        train = train.iloc[::-1].copy()
        train.index = [0] * len(train)
        test = train.iloc[:2].copy()
        test.iloc[0, test.columns.get_loc('time')] += 1  # 相差 1ms 必须匹配失败。
        dataset = SimpleNamespace(train_data=train, test_data=test, pool_name='zz500')
        with patch.object(state, 'read_ddb', return_value=raw) as reader:
            state.attach_market_state(dataset)
        self.assertEqual(train['model_group'].tolist(), [-1, -1] + list(state.STATE_GROUP.values())[::-1])
        self.assertTrue(pd.isna(test['market_state'].iloc[0]))
        self.assertEqual(test['model_group'].tolist(), [-1, -1])
        self.assertIn('MarketState_zz500', reader.call_args.args[0])

    def test_duplicate_state_keys_fail(self):
        raw = pd.DataFrame({'ticker': ['A.SZ'] * 2,
                            'time': pd.to_datetime(['2026-01-05 09:30:01'] * 2),
                            'market_state': [4, 7]})
        frame = pd.DataFrame({'ticker': ['A.SZ'], 'date': [20260105], 'time': [93001000]})
        dataset = SimpleNamespace(train_data=frame, test_data=frame.copy(), pool_name='zz500')
        with patch.object(state, 'read_ddb', return_value=raw):
            with self.assertRaises(ValueError):
                state.attach_market_state(dataset)

    def test_bounds_use_training_only(self):
        opt = {'test': {'threshold_pct': 50, 'bound_mode': 'by_ticker'}}
        bounds = state.prediction_bounds(opt, pd.DataFrame({'ticker': ['A', 'A', 'B', 'B']}),
                                        np.array([0.1, 0.3, 0.7, 0.9]),
                                        pd.DataFrame({'ticker': ['B', 'A', 'C']}))
        np.testing.assert_allclose(bounds, [[0.8, 0.2], [0.2, 0.8], [0.5, 0.5]])

    def test_pooled_returns_include_neutral_samples(self):
        data = pd.DataFrame({'class_label': [1, 0, 2], 'ret': [0.01, -0.02, 0.03]})
        result = state.state_metrics({'dataset': {}}, data, np.array([0.9, 0.1, 0.9]),
                                     np.array([[0.8, 0.8]] * 3))
        self.assertEqual(result['classification_samples'], 2)
        self.assertEqual(result['accuracy'], 1)
        self.assertEqual(result['auc'], 1)
        self.assertEqual(result['up_trade_num'], 2)
        self.assertAlmostEqual(result['weighted_return'], 200)

    def test_training_routing_fallback_and_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            train = pd.DataFrame({'ticker': ['A.SZ'] * 170, 'date': [20260105] * 170,
                                  'time': np.arange(170), 'x': np.arange(170),
                                  'model_group': [0] * 60 + [1] * 60 + [2] * 40 + [3] * 10,
                                  'class_label': [0, 1] * 60 + [1] * 40 + [0, 1] * 5,
                                  'ret': [0.01] * 170})
            test = pd.DataFrame({'ticker': ['A.SZ'] * 6, 'date': [20260205] * 6,
                                 'time': np.arange(6), 'x': [0., 1., 2., 3., 4., np.nan],
                                 'model_group': [0, 1, 2, 3, -1, 0],
                                 'class_label': [1, 0, 2, 1, 0, 1], 'ret': [0.01] * 6})
            train['market_state'], test['market_state'] = 4, [4, 1, 7, 0, np.nan, 4]
            opt = {'path': {'experiments_root': folder, 'model_path': {202602: folder}},
                   'dataset': {}, 'test': {'bound_mode': 'by_ticker', 'threshold_pct': 10}}
            dataset = SimpleNamespace(train_data=train, test_data=test, test_month=202602,
                                      indus_type=0, logger=logging.getLogger('test'))
            unified = SimpleNamespace(predict=lambda frame: np.full(len(frame), 0.5))
            trained = []

            def build_model(group_opt, **kwargs):
                group = int(Path(group_opt['path']['model_path'][202602]).name[-1])
                def train_model(x, y):
                    trained.append((group, x.copy(), y.copy()))
                return SimpleNamespace(train=train_model, save=Mock(),
                                       predict=lambda frame: np.full(len(frame), 0.9 - group * 0.8))

            with patch.object(state, 'attach_market_state'), patch.object(state, 'build_model', side_effect=build_model):
                state.train_market_states(opt, dataset, unified, ['x'])
            self.assertEqual([item[0] for item in trained], [0, 1])
            self.assertEqual(trained[0][1]['x'].tolist(), list(range(60)))
            self.assertEqual(trained[1][1]['x'].tolist(), list(range(60, 120)))
            self.assertEqual(opt['path']['model_path'][202602], folder)
            output = Path(folder) / '202602' / 'market_state' / 'indus0'
            predictions = pd.read_csv(output / 'test_predictions.csv')
            np.testing.assert_allclose(predictions['routed_proba'][:5], [0.9, 0.1, 0.5, 0.5, 0.5])
            self.assertTrue(pd.isna(predictions['routed_proba'].iloc[5]))
            metrics = pd.read_csv(output / 'metrics.csv')
            overall = metrics.query("model_group == 'all'")
            self.assertEqual(overall['test_samples'].tolist(), [5, 5])
            self.assertEqual(overall['classification_samples'].tolist(), [4, 4])
            self.assertTrue((Path(folder) / 'market_state_indus0.json').exists())


if __name__ == '__main__':
    unittest.main()
