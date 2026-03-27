TEST_MONTH=${1:-202601}
OUT_PUT_ROOT_PATH=${2:-data}
python -u pack_realtime_files_for_mix_model.py  --root_path experiments --test_month $TEST_MONTH  --output_root_path $OUT_PUT_ROOT_PATH --pool_name bond_etf  \
 --am_exp_name prod_pm_bond_etf_highprice_lgbm --pm_exp_name prod_pm_bond_etf_highprice_lgbm
