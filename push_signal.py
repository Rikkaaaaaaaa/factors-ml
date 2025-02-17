from utils.publish import save_report_disk, push_signal_sql
from utils.option import parse_options



if __name__ == '__main__':
    root_path = './'
    opt, args = parse_options(root_path, ensure=False)
    # note that upload_month must equals to yaml
    upload_month = [202403, 202404, 202405, 202406, 202407, 202408, 202409, 202410, 202411, 202412]
    signal_file_name_suffix = "ddb_with_nan"
    push_signal_sql(opt, suffix=signal_file_name_suffix, upload_month=upload_month, if_exists='append')