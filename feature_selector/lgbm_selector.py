import lightgbm as lgb
import os.path as osp
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from dataset import build_factor_name
from utils.logger import get_root_logger
from utils.registry import SELECTOR_REGISTRY

@SELECTOR_REGISTRY.register()
class LGBMSelector():
    def __init__(self, opt, test_month, indus_type,  *args, **kwargs):
        self.opt = opt
        self.test_month = test_month
        self.indus_type = indus_type
        self.training_factor_name =  build_factor_name(self.opt['dataset']['training_factor_name']) # list(set(_train_data.columns) - set(del_column))
        self.class_num = self.opt['dataset']['class_num']

        # logging file
        logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)

    def get_selected_factor_names(self):
        return self.selector.get_feature_names_out()

    def train(self, x_train, y_train):
        num_epoch = 200
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training LGBM model, num_epoch is {num_epoch}.")
        train_matrix = lgb.Dataset(x_train, label=y_train)
        if self.class_num == 3:
            params = {
                'boosting_type': 'gbdt',
                'objective': 'multiclass',
                'metric': 'multi_logloss',
                'learning_rate': 0.1,
                'num_class': 3,
                'min_child_weight': 1e-3,
                'num_leaves': 30,
                'max_depth': -1,
                'lambda_l1': 0.4,
                'lambda_l2': 0.5,
                'feature_fraction': 1,
                'bagging_fraction': 1,
                'bagging_freq': 0,
                'seed':  self.opt['manual_seed'],
                'nthread': self.opt['model']['n_cpus'],
                'verbose': -1,
            }
        if self.class_num == 2:
            params = {
                'seed': self.opt['manual_seed'],
                "objective": "binary",
                "metric": "auc",
                "boosting_type": "gbdt",
                'max_bin': 255,
                "learning_rate": 0.1,
                "max_depth": -1,
                "num_leaves": 30,
                "feature_fraction": 0.8,
                "bagging_fraction": 0.8,
                "bagging_freq": 5,
                # 'min_sum_hessian_in_leaf': 3.0,

                "verbosity": -1,
                'n_jobs': self.opt['model']['n_cpus'],
            }

        self.model = lgb.train(params, train_set=train_matrix, num_boost_round=num_epoch)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training finish")

    def select_factor(self, x_train, y_train):
        # train first
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Start training for factor selection...")
        self.train(x_train, y_train)

        selection_path = self.opt['path']['selection_path'][self.test_month]
        selection_name = f"{self.opt['name']}_{self.test_month}_indus{self.indus_type}"


        # save importance file
        feature_importance = pd.DataFrame(data={'factor_name': self.model.feature_name(),
                                                'score': self.model.feature_importance()})
        feature_importance = feature_importance.sort_values('score', ascending=False)

        # save selected importance score and factor name
        self.max_features = min(self.model.num_feature(), self.opt['feature_selector']['selected_feature_num'])
        selected_feature_importance = feature_importance.sort_values('score', ascending=False).iloc[:self.max_features, :]
        with pd.ExcelWriter(f"{selection_path}/{selection_name}.xlsx") as writer:
            feature_importance.to_excel(writer, sheet_name='all_factor_name', index=False)
            selected_feature_importance.to_excel(writer, sheet_name='selected_factor_name', index=False)
        self.selected_factor = self.selected_factor = list(selected_feature_importance['factor_name'])

        # plot bar rank
        max_plot_num = min(self.model.num_feature(), 30) # plt feature num <=30
        fig, ax = plt.subplots(figsize=(16, 12))
        sns.barplot(data=feature_importance.iloc[:max_plot_num, :], x='score', y='factor_name', orient='h', ax=ax)
        plt.title(f"{self.opt['name']}_{self.test_month}_indus{self.indus_type}")
        # plot data label
        offset = 2  # for visual quality
        for p in ax.patches:
            ax.text(p.get_width() + offset, p.get_y() + p.get_height() / 2,
                    '{:.1f}'.format(p.get_width()),
                    va='center')  # center text
        plt.savefig(f"{selection_path}/{selection_name}.jpg")

        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish factor selection with feature num={self.max_features}")

        return self.selected_factor
