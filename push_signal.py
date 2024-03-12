from utils.publish import save_report_disk, push_signal_sql
from utils.option import parse_options



if __name__ == '__main__':
    root_path = './'
    opt, args = parse_options(root_path, ensure=False)
    upload_month = [202304,202305,202306,202307,202308, 202309, 202310,202311,202312, 202401]
    push_signal_sql(opt, suffix=args.suffix, upload_month=upload_month, if_exists='append')