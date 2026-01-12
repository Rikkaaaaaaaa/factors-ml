# 机器学习价格预测任务训练框架

## 0 完整工作流程

1. **训练阶段**: 使用train.py或train_manager.py训练模型
2. **信号生成**: 模型生成交易信号文件
3. **信号评估**: 使用eval_signals.py评估信号月度和日度性能
4. **报告分析**: 如果是单个信号，也可使用scripts/analysis_report.py生成月度报告
5. **信号推送**: 使用merge_main_signal中的模块推送信号到数据库

## 1 项目概述

这是一个基于机器学习的金融价格预测训练框架，专门用于金融市场的高频交易信号生成和回测。框架支持多因子模型训练、特征选择、模型评估和实时信号生成等功能。

## 2 核心特性

- **多因子模型**: 支持基于技术因子、基本面因子等多种因子的价格预测
- **多任务支持**: 支持分类任务（涨跌预测）和回归任务（收益率预测）
- **特征选择**: 内置多种特征选择方法（LGBM、IV、PCA等）
- **多模型支持**: 支持LightGBM、Logistic Regression、Linear Regression等其他自定义模型
- **并行训练**: 支持多进程并行训练，提高训练效率
- **实时/回测模式**: 支持实时信号生成和历史回测两种模式
- **行业分类**: 支持按行业分类进行模型训练和评估
- **双训练方案**: 提供单次训练和循环训练两种模式
- **双评估方案**: 提供单次评估和循环评估两种模式

## 3 项目结构

```
factors-ml/
├── backtester/           # 回测模块
├── dataset/              # 数据集处理模块
├── ensemble/             # 模型集成模块
├── feature_selector/     # 特征选择器
├── models/               # 模型实现
├── option/               # 配置文件
│   ├── opt_manager/      # 循环训练配置文件
│   ├── eval/             # 评估配置文件
│   └── ...               # 其他配置文件
├── scripts/              # 工具脚本
├── signal_evaluation/    # 信号评估
├── utils/                # 工具函数
├── train.py              # 单次训练脚本
├── train_manager.py      # 循环训练脚本
├── eval.py               # 单次评估脚本
├── eval_manager.py       # 批量评估脚本
└── requirements.txt      # 依赖包
```

## 4 快速开始

### 4.1 环境配置

1. 安装依赖包：
```bash
pip install -r requirements.txt
```

2. 配置数据库连接（DolphinDB和mysql）：
   - 编辑 `utils/ddb.py` 中的数据库连接配置
   - 编辑 `utils/mysql.py` 中的数据库连接配置
   - 确保可以访问因子数据库和mysql中的股票静态数据

### 4.2 训练模式

#### 方案一：单次训练 (train.py)

- 适用于单个配置文件的训练任务
- 一个配置文件可以训练若干月份的全部行业，每个月份和每个行业会训练一个模型

**使用命令：**
```bash
# 基础训练，训练15s信号
python train.py -option option/hs300/20251105/20251105_hs300_highprice_lgbm_15s.yaml

# 实时模式训练，用于生产信号，此时不会进行test流程
python train.py -option option/prod/prod_train_202512/hs300/prod_202512_am、prod_202512_am_hs300_highprice_lgbm_300s.yaml -is_realtime

# 调试模式训练，debug模式会默认最多运行10个标的的数据（具体见dataset/factor_dataset.pydataset/factor_dataset.py）
python train.py -option option/hs300/20251105/20251105_hs300_highprice_lgbm_15s.yaml -debug

# 自定义根路径
python train.py -root_path /custom/path -option option/hs300/20251105/20251105_hs300_highprice_lgbm_15s.yaml
```

**参数说明：**
- `-root_path`: 项目根路径（默认：./）
- `-option`: 配置文件路径
- `-is_realtime`: 是否实时模式
- `-debug`: 调试模式（用于限制股票数量，加快pipeline验证进度）

#### 方案二：循环训练 (train_manager.py)

- 适用于需要批量处理多个配置文件的训练任务，支持数据缓存优化
- 相比单词训练，每次可以将数据缓存，并循环执行15s、60s、120s以及300s时间窗口的模型训练

**使用命令：**
```bash
# 基础循环训练
python train_manager.py -option option/opt_manager/hs300/am_model/am_model_hs300_highprice_lgbm_opt_manager.yaml

# 实时模式循环训练
python train_manager.py -option option/opt_manager/hs300/am_model/am_model_hs300_highprice_lgbm_opt_manager.yaml -is_realtime

# 调试模式循环训练
python train_manager.py -option option/opt_manager/hs300/am_model/am_model_hs300_highprice_lgbm_opt_manager.yaml -debug
```

**参数说明：**
- `-root_path`: 项目根路径（默认：./）
- `-option`: 循环训练配置文件路径
- `-is_realtime`: 是否实时模式
- `-debug`: 调试模式（限制股票数量）

### 4.3 评估模式

#### 方案一：单次评估 (eval.py)

适用于单个配置文件的模型评估任务。
注意eval模式下用到的yaml文件略有不同，详见[**5 配置文件说明**]

**使用命令：**
```bash
# 基础评估
python eval.py -option option/eval/batch3_across_tickers_hs300_highprice_lgbm_15s.yaml
```

#### 方案二：批量评估 (eval_manager.py)

适用于需要批量处理多个配置文件的评估任务。

**使用命令：**
```bash
# 基础批量评估
python eval_manager.py -option option/eval/opt_manager/hs300_test/am_model/am_model_hs300_highprice_lgbm_opt_manager.yaml
```

### 4.4 输出结果

训练完成后，框架会生成以下结果：

- **模型文件**: 保存在 `experiments/{test_month}/ckpt/`
- **特征重要性**: 保存在 `experiments/{test_month}/factor_selection/`
- **回测结果**: 保存在 `experiments/{test_month}/results/`
- **信号文件**: 保存在 `experiments/{test_month}/signals/`


### 5 配置文件说明
```
文件夹说明
option/
├── eval/              # 评估（eval）配置文件（包含单次和循环）
├── opt_manager/       # 循环训练（train）配置文件
├── prod/              # 生产rt模式配置文件
```

框架使用YAML格式的配置文件，存放在option文件夹，分为两种类型：

#### 5.1 单次配置文件
- **用于单次训练和评估，包含完整的训练参数**
- **训练和评估模式**：主要参数区别为
**mode**字段和增加了dataset中的**eval_factor_table字典**
- **rt模式**：可以指定mode为rt，或者在train模式中终端命令加上 -is_realtime表示rt
```yaml
    # 评估yaml主要区别
    mode: eval             # 用于模式指定[eval, train, rt],不指定默认为train，
    dataset:       
        eval_factor_table: # 用于指定评估的DDB数据库和表名
        dfs://DDB_Factor_15s: [ 'BaseFokFactor', 'SlopeOflFactor', 'GPFactor' ]
```



**数据集配置示例：**
```yaml
# 基础配置
base_name: am_model_hs300_highprice_lgbm  # 实验基础名称，同时也是上层文件夹名称。命名方式为前缀_股票池_price_模型名称
manual_seed: 2023                         # 随机种子，确保结果可复现
n_jobs: 1                                 # 并行进程数，每个月份每个行业为一个模型（进程）

# 数据集配置
dataset:
  # 因子表配置
  factor_table:
    dfs://DDB_Factor_15s: ['BaseFokFactor', 'SlopeOflFactor', 'GPFactor']  # DolphinDB因子表
  ret_table:
    dfs://DDB_Returns: 'Returns_hs300'  # 收益率表，注意跟随股票池修改
  
  # 因子名称配置，获取因子具体名称在dataset/factor_name.py中指定
  training_factor_name: [ 'ddb_base_factor', 'ddb_fok_factor', 'ddb_ofl_factor', 'ddb_slope_factor', 'ddb_gp_factor']  # 训练因子
  std_factor_name: [ 'ddb_base_factor', 'ddb_slope_std_factor', 'ddb_gp_factor']  # 标准化因子
  clip_factor_name: [ 'ddb_base_factor', 'ddb_ofl_factor', 'ddb_slope_factor', 'ddb_gp_factor']  # 截断因子
  log_factor_name: [ 'log_factor' ]  # 对数变换因子
  rebalancing_tables: ['BaseFokFactor', 'SlopeOflFactor', 'GPFactor']  # 再平衡表

  # 数据预处理选项
  type: 'FactorDataset'           # 数据集类型
  test_month: [202512]            # 测试月份
  training_month_num: 6           # 训练月份数量
  io_backend: ddb                 # 数据源：ddb(DolphinDB) 或 disk(本地磁盘)
  pool_name: 'hs300'              # 股票池名称
  indus_table_suffix: ''          # 行业表后缀
  indus_class: group_id           # 行业分类字段
  avg_price: 10                   # 平均价格阈值
  price_name: highprice           # 价格类型：highprice(高价) 或 lowprice(低价)
  ret_name: 15s                   # 收益率时间窗口：15s/60s/120s/300s
  std_type: default               # 标准化类型：default(训练集标准化)
  drop_null_in_training: false    # 训练集是否删除空值
  alpha: 0.0005                   # 标签生成阈值
  class_num: 2                    # 分类数：2(二分类) 或 3(三分类)
  balance: default                # 样本平衡方式
  trading_hours:                  # 交易时间段，用于筛选数据包含的时段
    am_start_time: 93000
    am_end_time: 113000
    pm_start_time: 145715
    pm_end_time: 145700

# 模型配置
model:
  type: 'LgbmModel'  # 模型类型：LgbmModel/LogitModel/LrModel
  n_cpus: 8          # 模型训练使用的线程数

# 训练配置
train:
  num_epoch: 200     # 训练轮数
  save_proba: true   # 是否保存预测概率，用于后续阈值的优化选取

# 测试配置
test:
  bound_mode: by_ticker  # 边界模式：by_ticker(按股票) 或 indus(按行业)
  threshold_pct: 40      # 阈值百分比
```

**参数详细说明：**

1. **基础配置参数**
   - `base_name`: 实验标识，用于生成输出目录和文件名
   - `manual_seed`: 随机种子，确保实验可复现性
   - `n_jobs`: 并行处理进程数，影响数据处理速度

2. **数据集参数**
   - `factor_table`: DolphinDB因子表配置，指定数据源和因子表名
   - `ret_table`: 收益率表配置
   - `training_factor_name`: 用于训练的因子列表
   - `std_factor_name`: 需要标准化的因子列表
   - `clip_factor_name`: 需要截断的因子列表
   - `log_factor_name`: 需要对数变换的因子列表
   - `rebalancing_tables`: 再平衡因子表
   - `test_month`: 测试月份列表，支持多个月份测试
   - `training_month_num`: 训练月份数量，决定训练数据的时间跨度
   - `io_backend`: 数据读取后端，`ddb`为DolphinDB，`disk`为本地磁盘
   - `pool_name`: 股票池名称，如`hs300`、`zz500`等
   - `price_name`: 价格类型，`highprice`为高价策略，`lowprice`为低价策略
   - `ret_name`: 收益率时间窗口，决定预测的时间尺度
   - `class_num`: 分类任务类型，2为涨跌二分类，3为涨平跌三分类
   - `trading_hours`: 交易时间段配置，支持上午和下午分段

3. **模型参数**
   - `type`: 模型类型，支持LightGBM、Logistic回归、线性回归等
   - `n_cpus`: 模型训练时的CPU核数，影响训练速度

4. **训练参数**
   - `num_epoch`: 训练轮数，影响模型拟合程度
   - `save_proba`: 是否保存预测概率，用于后续信号生成

5. **测试参数**
   - `bound_mode`: 边界处理模式，按股票或行业进行边界调整
   - `threshold_pct`: 阈值百分比，用于信号生成

#### 5.2 循环训练配置文件 (opt_manager)
- **用于批量处理多个配置文件的训练任务**
- 相比于单次训练，增加了ret_names来进行控制训练的窗口数
- 此外，opt_manager中的所有配置会覆盖写入所有子配置

**opt_manager配置文件结构：**
```yaml
base_name: am_model_hs300_highprice_lgbm
manual_seed: 2023
n_jobs: 4 # 并行的数量
ret_names: [15s, 60s, 120s, 300s]  # 多收益率窗口配置
dataset:
  test_month: [202512]
  training_month_num: 6
  io_backend: ddb # disk
  pool_name: 'hs300'
  indus_table_suffix: ''
  indus_class: group_id
  avg_price: 10
  price_name: highprice
```

**循环训练配置特点：**

1. **分层配置**：主配置文件定义通用参数，子配置文件针对不同收益率窗口进行详细配置
2. **批量处理**：通过`ret_names`参数指定多个收益率窗口，实现批量训练
3. **资源优化**：主配置中的`n_jobs`控制整体并行度，子配置中的`n_jobs`控制单个任务的并行度
4. **统一管理**：便于管理多个相关实验配置，**覆盖写入所有子配置**，保持参数一致性


#### 5.3 评估模式配置

评估模式配置文件与训练模式类似，主要区别在于：

```yaml
# 评估yaml主要区别
mode: eval     # 用于评估模式指定，不指定默认为train
dataset:       # 评估模式因子表配置
    eval_factor_table:
    dfs://DDB_Factor_15s: [ 'BaseFokFactor', 'SlopeOflFactor', 'GPFactor' ]
```

#### 5.4 生产模式配置

实时模式（rt模式）可以通过两种方式指定：
1. 在配置文件中设置 `mode: rt`
2. 在训练命令中加上 `-is_realtime` 参数

实时模式主要用于生产环境信号生成，此时不会进行测试流程。



### 6 其他核心模块

#### 6.1 数据集模块 (`dataset`)

- `factor_dataset.py`: 因子数据集加载和预处理
- `sql_ops.py`: 数据库操作工具
- 支持数据标准化、缺失值处理、标签生成等功能

#### 6.2 模型模块 (`models`)

- `lgbm_model.py`: LightGBM模型实现
- `logit_model.py`: 逻辑回归模型
- `lr_model.py`: 线性回归模型
- 支持模型训练、预测、保存和加载

#### 6.3 特征选择器 (`feature_selector`)

- `lgbm_selector.py`: 基于LightGBM的特征选择
- `iv_selector.py`: 基于IV值的特征选择
- `pca_selector.py`: PCA降维特征选择

### 6.4 回测模块 (`backtester`)

- `backtester.py`: 主要回测逻辑
- 支持信号生成、绩效评估、结果保存

### 6.5 信号评估模块 (`signal_evaluation`)

#### eval_signals.py - 信号评估工具

用于评估生成的交易信号性能，支持月度评估和日度评估。

**主要功能：**
- 信号数据读取和合并
- 收益率数据合并（连接DolphinDB数据库）
- 多维度绩效指标计算
- 月度/日度评估报告生成

**主要函数：**
```python
# 月度信号评估
eval_signals_by_month(
    result_name="test_evaluation",
    signal_path="./experiments/test_model/202501/signal",
    month=202501,
    ret_name="15s",
    stock_pool="hs300",
    time_ranges=[(93000, 113000), (130000, 145700)]
)

# 日度信号评估
eval_signals_by_date(
    result_name="daily_evaluation",
    signal_path="./experiments/test_model/202501/signal",
    month=202501,
    ret_name="15s",
    stock_pool="hs300",
    time_ranges=[(93000, 113000), (130000, 145700)]
)
```

**评估指标：**
- 加权收益率 (weighted_return)
- 上涨/下跌胜率 (up_winrate/down_winrate)
- 上涨/下跌平均收益率 (up_ret/down_ret)
- 信号比例 (up_pct/down_pct)
- 非零收益率比例 (not_zero_rate)

### 6.6 分析报告模块 (`scripts/analysis_report.py`)

#### analysis_report.py - 分析报告生成工具

用于汇总多个时间窗口的评估报告，生成综合信号性能分析。

**使用命令：**
```bash
# 生成分析报告
python scripts/analysis_report.py \
    -prefix ddb_factor \
    -price_name highprice \
    -report_pool_name hs300 \
    -ticker_pool_name hs300 \
    -model_name lgbm \
    -ret_windows 15s 60s 120s 300s \
    -experiment_path experiments
```

**参数说明：**
- `-prefix`: 实验前缀名称
- `-price_name`: 价格类型 (highprice/lowprice)
- `-report_pool_name`: 报告股票池
- `-ticker_pool_name`: 股票池名称
- `-model_name`: 模型名称
- `-ret_windows`: 收益率时间窗口列表
- `-experiment_path`: 实验文件夹路径

**输出结果：**
- 汇总报告保存在 `./summary/` 目录
- 包含各时间窗口的综合绩效指标

### 6.7 信号推送模块 (merge_main_signal)

#### 信号合并与推送流程
该模块负责将训练生成的信号合并并推送到MySQL数据库，供回测交易使用。

#### 1. create_main_signal.py - 主信号生成与推送（可用于多个实验文件夹提取不同时间段信号）

**功能：**
- 读取训练信号文件
- 基于百分位数调整信号强度
- 生成主交易信号

**使用示例：**
```python
# 生成主信号
signal = merge_signal_by_pct(
    expr_name="test_experiment",
    ret_name="15s",
    month=202501
)
```

#### 2. merge_sql_signal_sql.py - 单一主信号生成与推送（仅可用于单个实验文件夹的信号）

**功能：**
- 从MySQL数据库读取多个时间窗口的信号
- 合并生成综合信号
- 推送到目标数据库表

**使用命令：**
```bash
# 合并信号并推送到数据库
python merge_main_signal/merge_sql_signal_sql.py \
    -n_jobs 8 \
    -price_name highprice \
    -pool_name hs300 \
    -model_name lgbmmodel \
    -database strategy
```

**参数说明：**
- `-n_jobs`: 并行进程数
- `-price_name`: 价格类型
- `-pool_name`: 股票池
- `-model_name`: 模型名称
- `-database`: 目标数据库

#### 3. push_option_signal_sql.py - 基于yaml配置文件的信号推送脚本

**功能：**
- 批量推送信号到MySQL数据库
- 支持追加或替换模式
- 自动处理数据库连接

**使用示例：**
```python
# 推送信号到数据库
from utils.publish import push_signal_sql
from utils.option import parse_options

root_path = '/root/PycharmProjects/factors-ml'
opt, args = parse_options(root_path, ensure=False)
upload_month = [202501, 202502, 202503, 202504, 202505]
signal_file_name_suffix = "ddb_null_factor_new_indus"
push_signal_sql(opt, suffix=signal_file_name_suffix, upload_month=upload_month, if_exists='append')
```





## 7 扩展开发

### 添加数据处理类
1. 在 `dataset/` 目录下创建新模型类
2. 在 `dataset/__init__.py` 中注册数据类

### 添加新模型
1. 在 `models/` 目录下创建新模型类
2. 继承 `BaseModel` 类
3. 在 `models/__init__.py` 中注册模型

### 添加新特征选择器
1. 在 `feature_selector/` 目录下创建新选择器
2. 实现 `select_factor` 方法
3. 在 `feature_selector/__init__.py` 中注册选择器

## 常见问题

## TODO
1. 更新低价股运行方式
2. 更新return表格为自动拼接股票池

## 技术支持

如有问题或建议，请联系EQ Algo团队。

---

*最后更新: 2025年12月25日*