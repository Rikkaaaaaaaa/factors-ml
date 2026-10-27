"""预处理完成后按 market state 训练；不改变原来的 X、y 和行业划分。"""
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score

from models import build_model
from utils.ddb import read_ddb


# 与交接文档一致；缺失或未知状态用 -1 表示，走统一模型。
STATE_GROUP = dict(enumerate([3, 1, 3, 1, 0, 1, 3, 2, 3, 3, 1, 3]))
KEYS = ['ticker', 'date', 'time']


def attach_market_state(dataset):
    """只读取实际用到的月份，按股票、日期、毫秒时间精确对齐。"""
    frames = [dataset.train_data, dataset.test_data]
    dates = pd.concat([frame['date'] for frame in frames])
    tickers = pd.concat([frame['ticker'] for frame in frames]).unique()
    symbols = '`' + '`'.join(tickers)
    states = []
    for month in sorted((dates.astype(int) // 100).unique()):
        month_str = f'{month // 100}.{month % 100:02d}M'
        states.append(read_ddb(f'''
            select securityCode as ticker, time, market_state
            from loadTable("dfs://DDB_MarketState", "MarketState_{dataset.pool_name}")
            where month(time)={month_str}, securityCode in {symbols}
        '''))
    states = pd.concat(states, ignore_index=True)
    timestamp = states['time'].dt
    states['date'] = timestamp.strftime('%Y%m%d').astype(int)
    states['time'] = (timestamp.hour * 10000000 + timestamp.minute * 100000
                      + timestamp.second * 1000 + timestamp.microsecond // 1000)
    # 仅在连接入口检查一次唯一键，避免重复标签使样本扩增。
    labels = states.set_index(KEYS, verify_integrity=True)['market_state']
    for frame in frames:
        frame['market_state'] = labels.reindex(pd.MultiIndex.from_frame(frame[KEYS])).to_numpy()
        frame['model_group'] = frame['market_state'].map(STATE_GROUP).fillna(-1).astype(int)


def prediction_bounds(opt, train, train_proba, test):
    """阈值只取训练集分位数，沿用 by_ticker / by_indus 和 threshold_pct。"""
    probabilities = pd.DataFrame({'ticker': train['ticker'].to_numpy(),
                                  'up': train_proba, 'down': 1 - train_proba})
    quantile = 1 - opt['test']['threshold_pct'] / 100
    pooled = probabilities[['up', 'down']].quantile(quantile)
    if opt['test']['bound_mode'] == 'by_ticker':
        bounds = probabilities.groupby('ticker')[['up', 'down']].quantile(quantile)
        # 某股票在该组没有训练样本时，使用本组全股票阈值。
        return bounds.reindex(test['ticker']).fillna(pooled).to_numpy()
    return np.tile(pooled.to_numpy(), (len(test), 1))


def state_metrics(opt, data, proba, bounds):
    """分类指标只评估 0/1；收益统计保留中性样本，预测不按收益筛选。"""
    labels = data['class_label'].to_numpy()
    binary = np.isin(labels, [0, 1])
    metrics = {'test_samples': len(data), 'classification_samples': int(binary.sum()),
               'accuracy': np.nan, 'auc': np.nan}
    if binary.any():
        metrics['accuracy'] = accuracy_score(labels[binary], proba[binary] >= 0.5)
        if np.unique(labels[binary]).size == 2:
            metrics['auc'] = roc_auc_score(labels[binary], proba[binary])

    long_name = opt['dataset'].get('long_ret_name', 'long_ret_10min')
    short_name = opt['dataset'].get('short_ret_name', 'short_ret_10min')
    if long_name in data and short_name in data:
        long_ret, short_ret = data[long_name].to_numpy(), data[short_name].to_numpy()
    else:
        long_ret, short_ret = data['ret'].to_numpy(), -data['ret'].to_numpy()
    valid = np.isfinite(long_ret) & np.isfinite(short_ret)
    metrics['return_samples'] = int(valid.sum())
    total_return = 0.0
    for side, returns, selected in [('up', long_ret, proba >= bounds[:, 0]),
                                     ('down', short_ret, 1 - proba >= bounds[:, 1])]:
        selected = selected & valid
        trades = returns[selected]
        nonzero = trades[trades != 0]
        metrics[f'{side}_trade_num'] = len(trades)
        metrics[f'{side}_mean_ret'] = trades.mean() * 1e4 if len(trades) else np.nan
        metrics[f'{side}_win_rate'] = (nonzero > 0).mean() if len(nonzero) else np.nan
        total_return += trades.sum()
    # 直接汇总所有样本，不能把四组的收益率或 AUC 简单平均。
    metrics['weighted_return'] = total_return / valid.sum() * 1e4 if valid.any() else np.nan
    return metrics


def train_market_states(opt, dataset, unified_model, features):
    """保留统一模型，额外训练四组模型并输出同样本对比。"""
    month, industry = dataset.test_month, dataset.indus_type
    output = Path(opt['path']['experiments_root']) / str(month) / 'market_state' / f'indus{industry}'
    output.mkdir(parents=True, exist_ok=True)
    attach_market_state(dataset)
    train, test = dataset.train_data, dataset.test_data
    counts = []
    for split, frame in [('train', train), ('test', test)]:
        for group in [0, 1, 2, 3, -1]:
            labels = frame.loc[frame['model_group'] == group, 'class_label']
            counts.append({'split': split, 'model_group': group, 'samples': len(labels),
                           'share': len(labels) / len(frame) if len(frame) else 0,
                           'negative': int((labels == 0).sum()),
                           'positive': int((labels == 1).sum()),
                           'neutral': int((labels == 2).sum())})
    counts = pd.DataFrame(counts)
    counts.to_csv(output / 'sample_counts.csv', index=False)
    # 控制台和日志输出同一份统计，占比分母为各自训练集/测试集的全部样本。
    summary = (
        f'[Market state][月份={month}, 行业={industry}] 预处理后样本统计\n'
        f'训练集总样本数：{len(train):,}；测试集总样本数：{len(test):,}\n'
        'samples=该组样本数，share=占所在 train/test 集的比例；model_group=-1 表示缺失或未知状态\n'
        + counts.to_string(index=False, formatters={'share': '{:.2%}'.format})
    )
    print(summary, flush=True)
    dataset.logger.info('%s', summary)
    low_share = counts.query("split == 'train' and model_group in [1, 2, 3] and share < 0.2")
    if not low_share.empty:
        dataset.logger.warning('以下组占比低于 20%%，保留原映射：%s', low_share['model_group'].tolist())

    # 先用统一模型填满预测；未知状态、样本不足的组自然保留这些预测。
    unified_train = unified_model.predict(train[features])
    unified_test = unified_model.predict(test[features]) if len(test) else np.empty(0)
    unified_bounds = prediction_bounds(opt, train, unified_train, test)
    routed_test, routed_bounds = unified_test.copy(), unified_bounds.copy()
    model_sources = {}
    for group in range(4):
        group_train = train.loc[train['model_group'] == group]
        test_mask = (test['model_group'] == group).to_numpy()
        # LGBM 默认每叶至少 20 条；不足两叶或缺少一个类别时复用统一模型。
        if len(group_train) < 40 or group_train['class_label'].nunique() < 2:
            model_sources[group] = 'unified'
            dataset.logger.warning('model_group_%s 样本不足或缺少类别，使用统一模型', group)
            continue
        group_opt = deepcopy(opt)
        model_dir = Path(opt['path']['model_path'][month]) / f'model_group_{group}'
        model_dir.mkdir(parents=True, exist_ok=True)
        group_opt['path']['model_path'][month] = str(model_dir)
        model = build_model(group_opt, test_month=month, indus_type=industry)
        model.train(group_train[features], group_train['class_label'])
        model.save()
        model_sources[group] = f'model_group_{group}'
        if test_mask.any():
            group_test = test.loc[test_mask]
            routed_test[test_mask] = model.predict(group_test[features])
            routed_bounds[test_mask] = prediction_bounds(
                opt, group_train, model.predict(group_train[features]), group_test)

    # 映射和因子顺序随模型保存，方便后续加载时按相同规则路由。
    metadata = {'version': 1, 'state_group': STATE_GROUP, 'features': list(features),
                'model_sources': model_sources, 'unknown_state_model': 'unified'}
    metadata_path = Path(opt['path']['model_path'][month]) / f'market_state_indus{industry}.json'
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')

    predictions = test[KEYS + ['market_state', 'model_group', 'class_label', 'ret']].copy()
    predictions['unified_proba'], predictions['routed_proba'] = unified_test, routed_test
    predictions[['unified_up_bound', 'unified_down_bound']] = unified_bounds
    predictions[['routed_up_bound', 'routed_down_bound']] = routed_bounds
    # 全部特征为空的行不参与评估，保留行和缺失预测以便排查。
    usable = ~test[features].isna().all(axis=1).to_numpy()
    predictions.loc[~usable, ['unified_proba', 'routed_proba']] = np.nan
    predictions.to_csv(output / 'test_predictions.csv', index=False)

    rows = []
    for group in [0, 1, 2, 3, -1, 'all']:
        mask = usable if group == 'all' else usable & (test['model_group'].to_numpy() == group)
        for name, proba, bounds in [('unified', unified_test, unified_bounds),
                                    ('routed', routed_test, routed_bounds)]:
            rows.append({'model_group': group, 'model': name,
                         **state_metrics(opt, test.loc[mask], proba[mask], bounds[mask])})
    pd.DataFrame(rows).to_csv(output / 'metrics.csv', index=False)
    dataset.logger.info('Market state 模型及分组结果已保存：%s', output)
