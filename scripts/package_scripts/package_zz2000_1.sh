TEST_MONTH=${1:-202601}
OUT_PUT_ROOT_PATH=${2:-data}
python -u pack_realtime_files_for_mix_model.py  --root_path experiments --test_month $TEST_MONTH --output_root_path $OUT_PUT_ROOT_PATH --pool_name zz2000_1  \
 --am_exp_name prod_am_zz2000_1_highprice_lgbm --pm_exp_name prod_pm_zz2000_1_highprice_lgbm \
 --exp_name_low_price low_price_zz2000_1_rt
