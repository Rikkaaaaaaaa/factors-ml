from backtester.backtester import BackTester
from backtester.backtester_long_term import BackTesterLongTerm
from backtester.search_backtester import SearchBackTester
from backtester.backtester_low_price import BackTesterLowPrice
from backtester.backtester_hk import BackTesterHK


def build_backtester(opt, test_month, indus_type, logger_name=None):
    dataset_type = opt['dataset']['type']
    if dataset_type == 'FactorLongTermDataset':
        return BackTesterLongTerm(opt, test_month, indus_type, logger_name)
    return BackTester(opt, test_month, indus_type, logger_name)
