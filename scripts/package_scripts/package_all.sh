SCRIPT_DIR="./scripts/package_scripts"
( sh "$SCRIPT_DIR/echo1.sh" ) &
( sh "$SCRIPT_DIR/echo2.sh" ) &
wait