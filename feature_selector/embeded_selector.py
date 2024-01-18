import numpy as np
from sklearn.feature_selection import SelectFromModel
from sklearn.linear_model import LogisticRegression
import pandas as pd

from dataset import build_factor_name
from utils.logger import get_root_logger
from utils.registry import SELECTOR_REGISTRY

@SELECTOR_REGISTRY.register()
class EmbeddedSelector():
    def __init__(self, opt, test_month, indus_type, *args, **kwargs):
        self.opt = opt
        self.test_month = test_month
        self.indus_type = indus_type
        self.training_factor_name =  build_factor_name(self.opt['dataset']['training_factor_name']) # list(set(_train_data.columns) - set(del_column))

        # logging file
        logger_name = f"month{test_month}_indus{indus_type}"
        self.logger = get_root_logger(logger_name=logger_name)

    def get_selected_factor_names(self):
        return self.selector.get_feature_names_out()

    def select_factor(self, train, target_train):
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Start training for factor selection...")

        self.max_features = min(train.shape[1], self.opt['feature_selector']['selected_feature_num'])
        self.selector = SelectFromModel(LogisticRegression(penalty="l2", C=0.1), max_features=self.max_features)
        self.selector.fit_transform(train, target_train)
        # save features to excel
        selection_path = self.opt['path']['selection_path'][self.test_month]
        selection_name = f"{self.opt['name']}_{self.test_month}_indus{self.indus_type}"
        all_factor_names = pd.DataFrame(data={'factor_name': list(train.columns)})
        selected_factor_names = pd.DataFrame(data={'factor_name': list(self.get_selected_factor_names())})
        with pd.ExcelWriter(f"{selection_path}/{selection_name}.xlsx") as writer:
            all_factor_names.to_excel(writer, sheet_name='all_factor_name', index=False)
            selected_factor_names.to_excel(writer, sheet_name='selected_factor_name',index=False)

        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish factor selection with feature num={self.max_features}")

        return list(self.selector.get_feature_names_out())




