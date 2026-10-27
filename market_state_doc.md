# 按 Market State 分组训练

在原 YAML 的 `train` 下添加 `by_market_state: true`，使用 `train.py` 运行。
此功能当前用于二分类训练（`class_num: 2`）；不开启时原流程不变。
不修改行业划分，使用你已配置好的全股票池行业。

zz500 示例（先确认数据库连接、月份、收益表符合你的环境）：

```powershell
python train.py --option examples/long_term_zz500_market_state.yaml
```

示例用 2026 年 1 月训练、2 月测试；改 `dataset.test_month` 和
`dataset.training_month_num` 可调整窗口。连接沿用项目默认配置，也可以把原
YAML 的 `debug_connection` 段复制到示例中。建议首次使用新的 `base_name`，
避免与旧实验混在一起。也可以直接复制你当前可运行的配置，只加这个开关。

处理顺序：原有数据提取 → 月份切分、标签筛选及预处理 → 原有因子选择 →
训练统一模型 → 精确连接 state → 分组训练。预处理与因子选择共用训练集，
不在每组重新拟合；不读取测试集来拟合预处理或选择参数。沿用原有按月训练/测试
切分，本次不增加验证集、调参或额外的收益窗口边界剔除。

从 `dfs://DDB_MarketState/MarketState_<pool_name>` 读取状态，保留毫秒，
按 `ticker + date + time` 匹配。仅在连接入口检查状态键唯一性。
固定映射如下；state 只决定选哪个模型，不加入 X，也不替换 y：

| model_group | 原 market_state |
|---|---|
| 0 | 4 |
| 1 | 1、3、5、10 |
| 2 | 7 |
| 3 | 0、2、6、8、9、11 |

缺失或未知 state 记作 `-1`，使用统一模型。某组训练样本少于 40 条
（LGBM 默认两个叶子的最低样本量），或只有一个类别，也使用统一模型。
组 1～3 的训练占比低于 20% 时仅记录日志，不修改分组或补样本。

原模型、原回测报告和信号保持原路径。新增文件在实验目录的对应测试月份下：

- `ckpt/model_group_0/` 至 `ckpt/model_group_3/`：各组模型，兜底组不另训模型。
- `ckpt/market_state_indus<行业>.json`：映射版本、因子顺序及各组实际模型来源。
- `market_state/indus<行业>/sample_counts.csv`：预处理后各组训练/测试样本数、占比、正负及中性类别数。
- `market_state/indus<行业>/metrics.csv`：`unified` 与 `routed` 在相同测试样本上的分类和收益指标。
- `market_state/indus<行业>/test_predictions.csv`：原 state、组别、统一/路由预测概率及上下阈值。

使用 `LgbmModel` 时，每个 `market_state/indus<行业>/model_group_<组号>/` 自动增加以下输出，无需新增参数：

- `feature_importance.csv`：全部因子的 gain（分裂收益）和 split（分裂次数），按 gain 排序。
- `shap_importance.csv`：因子的平均绝对 SHAP、平均有符号 SHAP，按平均绝对值排序。
- `feature_importance.png`、`shap_importance.png`：对应排名的前 20 个因子。
- `shap_values.csv`：抽样数据逐行的因子 SHAP 和 `base_value`，保留股票、日期、毫秒时间。
- `shap_samples.csv`：上述同批样本的预处理后因子值，行序与 SHAP 明细一致。
- `explanation.json`：实际模型来源、抽样来自训练集还是测试集、抽样数量和随机种子。

SHAP 优先解释该组测试样本，不按未来收益筛选；该组无测试样本时使用本组训练样本。
全因子缺失行不解释，每组最多抽取 2,000 条，使用已有 `manual_seed` 保证抽样可复现。
这部分仅解释已训练模型，不用于重新选因子或调参。使用 LightGBM 自带的
`pred_contrib=True`，无需安装 `shap` 包；二分类 SHAP 是 log-odds 的贡献，
各因子贡献加上 `base_value` 等于模型的原始分数，不是预测概率。
兜底组（含 `-1`）输出的是统一模型的 feature importance，SHAP 仍在该组样本上计算；
无可用样本时 SHAP 排名为空值，明细为空。其他模型类型保持原流程，不输出这组解释文件。
若旧实验已经训练完成，会沿用原逻辑跳过；要生成新增文件，请换一个 `base_name` 重新运行。

`metrics.csv` 中 `model_group=all` 直接汇总所有测试样本（含 `-1`），不是四组指标
的简单平均。分类 accuracy/AUC 仅统计标签 0/1；收益指标包含中性样本，预测阶段
不按未来收益筛选。全特征缺失行不评估；收益缺失行不计入收益指标。
收益单位为 bp，`weighted_return` 是多空入选收益之和除以有效收益样本数。
上下阈值继续使用 `threshold_pct` 与 `bound_mode`，分组模型的阈值取本组训练预测；
若某股票在该组无训练样本，阈值退回本组全股票分位数。

本次接入的是 `train.py` 离线训练与分组统计；原报告仍是统一模型的结果。
`eval.py`、`train_manager.py` 和实时打包/部署入口未增加 state 路由。
上线时需根据保存的映射与模型来源选择模型，不能直接把原统一模型文件替换成某个分组模型。
