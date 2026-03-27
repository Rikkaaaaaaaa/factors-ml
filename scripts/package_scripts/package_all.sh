#!/bin/bash
SCRIPT_DIR="./scripts/package_scripts"
LOG_DIR="./log/package_log"
TEST_MONTH="202603"
OUT_PUT_ROOT_PATH="data"
# 确保日志目录存在
mkdir -p "$LOG_DIR"
echo "test_month=$TEST_MONTH"

# 并行启动所有脚本，并将输出重定向到各自日志文件
nohup sh "$SCRIPT_DIR/package_bond_etf.sh" "$TEST_MONTH" "$OUT_PUT_ROOT_PATH" > "$LOG_DIR/package_bond_etf.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_hs300.sh" "$TEST_MONTH"  "$OUT_PUT_ROOT_PATH" > "$LOG_DIR/package_hs300.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_zz500.sh" "$TEST_MONTH"  "$OUT_PUT_ROOT_PATH" > "$LOG_DIR/package_zz500.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_zz1000.sh" "$TEST_MONTH"  "$OUT_PUT_ROOT_PATH" > "$LOG_DIR/package_zz1000.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_zz2000_1.sh" "$TEST_MONTH"  "$OUT_PUT_ROOT_PATH" > "$LOG_DIR/package_zz2000_1.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_zz2000_2.sh" "$TEST_MONTH"  "$OUT_PUT_ROOT_PATH" > "$LOG_DIR/package_zz2000_2.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_zz2000_3.sh"  "$TEST_MONTH"  "$OUT_PUT_ROOT_PATH" > "$LOG_DIR/package_zz2000_3.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_other.sh" "$TEST_MONTH"  "$OUT_PUT_ROOT_PATH" > "$LOG_DIR/package_other.log" 2>&1 &

# 等待所有后台进程完成
wait