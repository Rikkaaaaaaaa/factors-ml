import argparse
import os
import sys
from types import SimpleNamespace

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dataset import build_dataset
from dataset.sql_ops import check_indus
from utils.option import parse_options, yaml_load


def apply_debug_connection_override(raw_opt):
    debug_connection = raw_opt.get("debug_connection", {})
    if not debug_connection:
        return

    ddb_conf = debug_connection.get("ddb")
    if ddb_conf:
        import utils.ddb as ddb_mod

        normalized_ddb_conf = dict(ddb_conf)
        if "host" in normalized_ddb_conf and "server" not in normalized_ddb_conf:
            normalized_ddb_conf["server"] = normalized_ddb_conf["host"]
        if "user" in normalized_ddb_conf and "userName" not in normalized_ddb_conf:
            normalized_ddb_conf["userName"] = normalized_ddb_conf["user"]
        if "password" in normalized_ddb_conf and "userKey" not in normalized_ddb_conf:
            normalized_ddb_conf["userKey"] = normalized_ddb_conf["password"]
        ddb_mod.DDB_config.update(normalized_ddb_conf)

    mysql_conf = debug_connection.get("mysql")
    if mysql_conf:
        import utils.mysql as mysql_mod

        mysql_mod.host = mysql_conf.get("host", mysql_mod.host)
        mysql_mod.port = mysql_conf.get("port", mysql_mod.port)
        mysql_mod.user = mysql_conf.get("user", mysql_mod.user)
        mysql_mod.password = mysql_conf.get("password", mysql_mod.password)


def parse_args():
    parser = argparse.ArgumentParser(description="Validate FactorLongTermDataset load_data pipeline.")
    parser.add_argument(
        "--option",
        type=str,
        default="option/long_term/hs300/long_term_hs300_202601_demo.yaml",
        help="Path to YAML option file.",
    )
    parser.add_argument("--root_path", type=str, default="./", help="Project root path.")
    parser.add_argument("--test-month", type=int, default=None, help="Override first test month from YAML.")
    parser.add_argument("--indus-type", type=str, default=None, help="Optional industry id to validate.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode from option parser.")
    return parser.parse_args()


def main():
    args = parse_args()
    raw_opt = yaml_load(args.option)
    apply_debug_connection_override(raw_opt)

    parse_args_ns = SimpleNamespace(
        option=args.option,
        root_path=args.root_path,
        is_realtime=False,
        debug=args.debug,
    )
    opt = parse_options(parse_args_ns, ensure=False)

    original_test_month = opt["dataset"]["test_month"][0]
    if args.test_month is not None:
        opt["dataset"]["test_month"] = [args.test_month]
        for path_key in [
            "model_path",
            "results_path",
            "preprocess_path",
            "inference_path",
            "signal_path",
            "train_signal_path",
            "selection_path",
        ]:
            path_map = opt["path"].get(path_key)
            if isinstance(path_map, dict) and original_test_month in path_map:
                path_map[args.test_month] = path_map.pop(original_test_month)

    test_month = opt["dataset"]["test_month"][0]
    indus_candidates = sorted(check_indus(opt, test_month))
    if not indus_candidates:
        raise ValueError(f"No industry candidates found for month [{test_month}]")

    indus_type = args.indus_type if args.indus_type is not None else indus_candidates[0]
    dataset = build_dataset(opt, test_month=test_month, indus_type=indus_type)
    dataset.load_data()

    if dataset.is_empty:
        raise ValueError("Dataset is empty after load_data().")

    raw_factor_num = len(getattr(dataset, "raw_factor_name", dataset.training_factor_name))
    derived_factor_num = len(dataset.training_factor_name)

    print(f"test_month={test_month}")
    print(f"indus_type={indus_type}")
    print(f"tickers={len(dataset.tickers)}")
    print(f"raw_factor_num={raw_factor_num}")
    print(f"derived_factor_num={derived_factor_num}")
    print(f"train_shape={dataset.train_data.shape}")
    print(f"test_shape={dataset.test_data.shape}")
    print(f"train_columns_sample={dataset.training_factor_name[:12]}")

    if "class_label" in dataset.train_data.columns:
        train_label_dist = dataset.train_data["class_label"].value_counts(dropna=False).sort_index().to_dict()
        test_label_dist = dataset.test_data["class_label"].value_counts(dropna=False).sort_index().to_dict()
        print(f"train_label_dist={train_label_dist}")
        print(f"test_label_dist={test_label_dist}")

    preview_cols = ["ticker", "date", "time"] + dataset.training_factor_name[:6]
    extra_cols = [col for col in ["ret", dataset.long_ret_name, dataset.short_ret_name, "class_label"] if col in dataset.train_data.columns]
    preview_cols.extend(extra_cols)
    preview_cols = list(dict.fromkeys(preview_cols))
    print(dataset.train_data[preview_cols].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
