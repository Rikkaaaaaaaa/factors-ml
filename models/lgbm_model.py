import lightgbm as lgb
import numpy as np
import os.path as osp
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from utils.misc import mkdir
from utils.logger import get_root_logger
from utils.registry import MODEL_REGISTRY

@MODEL_REGISTRY.register()
class LgbmModel():
    """
    LGBM models for training

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
        self.num_epoch = self.opt['train']['num_epoch']
        # logging file
        logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: LGBM model init successfully")

    def train(self, x_train, y_train):
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training LGBM model...")
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

        self.model = lgb.train(params, train_set=train_matrix, num_boost_round=self.num_epoch)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training finish")


    def save(self):
        ckpt_folder = self.opt['path']['model_path'][self.test_month]
        ckpt_name = 'lgbm_indus{}.txt'.format(self.indus_type)
        ckpt_path = osp.join(ckpt_folder, ckpt_name)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Saving model at {ckpt_path}")
        self.model.save_model(ckpt_path)


    def predict(self, data):
        return self.model.predict(data)


    def select_factor(self, x_train, y_train):
        # train first
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Start training for factor selection...")
        self.train(x_train, y_train)

        selection_path = osp.join(self.opt['path']['experiments_root'], str(self.test_month), 'factor_selection')
        selection_name = f"{self.opt['name']}_{self.test_month}_indus{self.indus_type}"
        if not os.path.exists(selection_path):
            os.makedirs(selection_path)

        # save rank csv file
        feature_importance = pd.DataFrame(data={'factor_name': self.model.feature_name(),
                                                'score': self.model.feature_importance()})
        feature_importance.to_csv(f"{selection_path}/{selection_name}.csv", index=False)
        max_num_features = min(self.model.num_feature(), self.opt['factor_selection']['selected_factor_num'])
        feature_importance = feature_importance.sort_values('score', ascending=False).iloc[:max_num_features, :]

        # plot bar rank
        fig, ax = plt.subplots(figsize=(16, 12))
        sns.barplot(data=feature_importance, x='score', y='factor_name', orient='h', ax=ax)
        plt.title(f"{self.opt['name']}_{self.test_month}_indus{self.indus_type}")
        # plot data label
        offset = 2  # for visual quality
        for p in ax.patches:
            ax.text(p.get_width() + offset, p.get_y() + p.get_height() / 2,
                    '{:.1f}'.format(p.get_width()),
                    va='center')  # center text
        plt.savefig(f"{selection_path}/{selection_name}.jpg")

        # restart training
        self.selected_factor = list(feature_importance['factor_name'])
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish factor selection, restart training...")
        return self.selected_factor


    def search_params(self, x_train, y_train, x_test, y_test, callbacks=[]):
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training LGBM model...")
        train_matrix = lgb.Dataset(x_train, label=y_train)
        valid_matrix = lgb.Dataset(x_test, label=y_test)
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

        self.model = lgb.train(params, train_set=train_matrix, valid_sets=[valid_matrix], callbacks=callbacks,num_boost_round=self.num_epoch)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Training finish")








