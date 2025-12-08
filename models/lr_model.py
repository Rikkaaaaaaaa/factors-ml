import lightgbm as lgb
import numpy as np
import os.path as osp

import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from utils.misc import mkdir
from utils.logger import get_root_logger
from utils.registry import MODEL_REGISTRY

@MODEL_REGISTRY.register()
class LRModel():

    def __init__(self, opt, test_month, indus_type, logger_name=None):
        self.opt = opt
        self.test_month = test_month
        self.indus_type = indus_type
        self.class_num = self.opt['dataset']['class_num']

        # logging file
        # logging file
        self.logger_name = logger_name
        if self.logger_name is None:
            self.logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=self.logger_name)
        self.logger.info(f"[{self.logger_name}] LR model init successfully")

    def train(self, x_train, y_train):
        self.logger.info(f"[{self.logger_name}] Training LR model...")
        # self.model = sm.Logit(y_train, sm.add_constant(x_train, has_constant='add')).fit(disp=False)
        self.model = LogisticRegression(fit_intercept=False, n_jobs=self.opt['model']['n_cpus'], random_state=self.opt['manual_seed'],)
        self.model.fit(sm.add_constant(x_train, has_constant='add'), y_train)
        self.logger.info(f"[{self.logger_name}] Training finish")


    def save(self, ):
        # save model file
        # ckpt_folder = self.opt['path']['model_path'][self.test_month]
        # ckpt_name = 'lr_indus{}.csv'.format(self.indus_type)
        # ckpt_path = osp.join(ckpt_folder, ckpt_name)
        # params = pd.DataFrame(self.model.coef_, columns=['coef'])
        # params.to_csv(ckpt_path, index=False)
        # self.logger.info(f"[{self.logger_name}] Saving model at {ckpt_path}")
        pass

    def predict(self, data):
        null_idx = np.isnan(data).any(axis=1)
        y_pred = np.zeros(shape=(data.shape[0]))
        y_pred[~null_idx] = self.model.predict_proba(sm.add_constant(data[~null_idx], has_constant='add'))[:,1]
        return y_pred





