PROJECT_DIR="$(dirname "$(realpath "$0")")"
LOG_DIR="$PROJECT_DIR/logs"
MAIN_FILE="$PROJECT_DIR/main.py"
PYTHON_EXEC="python3"  

mkdir -p "$LOG_DIR"

NOW=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/cron_$NOW.log"

echo "[$NOW] Running BBC Crawler..." >> "$LOG_FILE"
$PYTHON_EXEC "$MAIN_FILE" >> "$LOG_FILE" 2>&1
echo "[$NOW] Done." >> "$LOG_FILE"