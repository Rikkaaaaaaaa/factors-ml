#!/bin/bash
SCRIPT_DIR="./scripts/package_scripts"
LOG_DIR="./log/package_log"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 并行启动所有脚本，并将输出重定向到各自日志文件
nohup sh "$SCRIPT_DIR/package_hs300.sh" > "$LOG_DIR/package_hs300.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_zz500.sh" > "$LOG_DIR/package_zz500.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_zz1000.sh" > "$LOG_DIR/package_zz1000.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_zz2000_1.sh" > "$LOG_DIR/package_zz2000_1.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_zz2000_2.sh" > "$LOG_DIR/package_zz2000_2.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_zz2000_3.sh" > "$LOG_DIR/package_zz2000_3.log" 2>&1 &
nohup sh "$SCRIPT_DIR/package_other.sh" > "$LOG_DIR/package_other.log" 2>&1 &

# 等待所有后台进程完成
wait