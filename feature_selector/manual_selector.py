import numpy as np
import pandas as pd
from dataset import build_factor_name
from utils.logger import get_root_logger
from utils.registry import SELECTOR_REGISTRY

@SELECTOR_REGISTRY.register()
class ManualSelector():
    def __init__(self, opt, test_month, indus_type, *args, **kwargs):
        self.opt = opt
        self.test_month = test_month
        self.indus_type = indus_type
        self.training_factor_name =  build_factor_name(self.opt['dataset']['training_factor_name']) # list(set(_train_data.columns) - set(del_column))

        # logging file
        logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)



    def select_factor(self, train, target_train):
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Start training for factor selection...")
        self.max_features = min(train.shape[1], self.opt['feature_selector']['selected_feature_num'])
        if self.max_features in [150, 200, 250]:
            selected_factor = pd.read_csv('feature_selector/selected_factors_{}_corr85.csv'.format(self.max_features))['factor_name'].tolist()
        else:
            selected_factor = self.training_factor_name
            self.logger.info(f"{self.test_month}_indus_{self.indus_type}: !!! no manual factor file")

        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish factor selection with feature num={self.max_features}")

        return selected_factor