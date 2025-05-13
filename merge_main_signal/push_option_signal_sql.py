import sys
sys.path.append('./')
sys.path.append('../')
from utils.publish import push_signal_sql
from utils.option import parse_options




if __name__ == '__main__':
    root_path = '/root/PycharmProjects/factors-ml'
    opt, args = parse_options(root_path, ensure=False)
    # note that upload_month must equals to yaml
    upload_month = [202501, 202502, 202503]
    signal_file_name_suffix = "ddb_with_nan"
    push_signal_sql(opt, suffix=signal_file_name_suffix, upload_month=upload_month, if_exists='append')