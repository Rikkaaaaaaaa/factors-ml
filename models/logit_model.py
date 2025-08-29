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
import statsmodels.api as sm
import warnings
warnings.filterwarnings('ignore')
pd.options.display.width = 500
pd.set_option('display.max_columns', None)


@MODEL_REGISTRY.register()
class LogitModel():
    """
    Logit models for training

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
        # logging file
        logger_name = f"month{test_month}_price_group_{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)
        self.logger.info(f"{self.test_month}_price_group_{self.indus_type}: Logit model init successfully")

    @staticmethod
    def pre_processing_train(x_train, y_train):
        # train data drop na
        x_train = x_train.fillna(0)
        merged_train_data = pd.concat([x_train, y_train], axis=1)
        merged_train_data = merged_train_data.dropna()
        merged_train_data = merged_train_data.reset_index(drop=True)
        factor_list = [x for x in list(merged_train_data.columns) if x not in ['fill_flag']]

        x_train = merged_train_data[factor_list]
        y_train = merged_train_data['fill_flag'].astype('int')
        return x_train, y_train

    def train(self, x_train, y_train):
        self.logger.info(f"{self.test_month}_price_group_{self.indus_type}: Training Logit model...")
        # pre_processing
        x_train, y_train = self.pre_processing_train(x_train, y_train)
        self.model = sm.Logit(y_train.astype(int), sm.add_constant(x_train, has_constant='skip')).fit(disp=False)
        self.factor_list = list(sm.add_constant(x_train, has_constant='skip').columns)
        self.logger.info(f"{self.test_month}_price_group_{self.indus_type}: Training finish")


    def save(self, bs_flag):
        ckpt_folder = osp.join(self.opt['path']['model_path'][self.test_month], bs_flag)
        if not osp.exists(ckpt_folder):
            os.mkdir(ckpt_folder)
        ckpt_name = 'logit_price_group_{}.csv'.format(self.indus_type)
        ckpt_path = osp.join(ckpt_folder, ckpt_name)
        self.logger.info(f"{self.test_month}_price_group_{self.indus_type}_{bs_flag}: Saving model at {ckpt_path}")

        pre_params = pd.DataFrame(self.model.params, index=self.factor_list)
        params = pd.DataFrame()
        params = pd.concat([params, pd.DataFrame(pre_params.values.T, columns=pre_params.index)], axis=1)
        params = params.set_index([['coef']])
        params.to_csv(ckpt_path)


    def predict(self, data):
        factor_data = sm.add_constant(data, has_constant='skip')
        factor_data = factor_data[self.factor_list]
        return self.model.predict(factor_data)




