import os.path
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
        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Start manual factor selection...")
        if self.opt["feature_selector"].get("selected_factor_file_name"):
            selected_factor_file_name = self.opt["feature_selector"].get("selected_factor_file_name")
            file_path = f'feature_selector/selected_factor_names/{selected_factor_file_name}'
            if os.path.exists(file_path):
                selected_factor = pd.read_csv(file_path)['factor_name'].tolist()
                self.logger.info(f"{self.test_month}_indus_{self.indus_type}: There are {len(selected_factor)} selected factors in {file_path}")
            else:
                error_info = f"{self.test_month}_indus_{self.indus_type}: There is no selected factor name file in {file_path}!"
                self.logger.info(error_info)
                raise FileNotFoundError(error_info)
        else:
            error_info = f"{self.test_month}_indus_{self.indus_type}: There is no key named 'selected_factor_file_name' in option.feature_selector"
            self.logger.info(error_info)
            raise AttributeError(error_info)

        self.logger.info(f"{self.test_month}_indus_{self.indus_type}: Finish factor selection with feature num={len(selected_factor)}")

        return selected_factor