import lightgbm as lgb
import numpy as np
import os.path as osp

import pandas as pd

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
        # save model file
        ckpt_folder = self.opt['path']['model_path'][self.test_month]
        ckpt_name = 'lgbm_indus{}.txt'.format(self.indus_type)
        ckpt_path = osp.join(ckpt_folder, ckpt_name)
        self.model.save_model(ckpt_path)
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Saving model at {ckpt_path}")


    def predict(self, data):
        return self.model.predict(data)




