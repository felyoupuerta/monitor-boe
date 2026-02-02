#!/bin/bash
DIR="$( cd "/home/felipe/Documents/monitor-boe/boe_monitor" && pwd )"
cd "$DIR"

mkdir -p logs

LOG_FILE="logs/boe_monitor_$(date +%Y%m%d).log"

if [ -f "$DIR/venv/bin/activate" ]; then
    source "$DIR/venv/bin/activate"
else
    echo "ERROR: no se encontró el venv en $DIR/venv" >> "$LOG_FILE"
    exit 1
fi

echo "=== Inicio de ejecución: $(date) ===" >> "$LOG_FILE"
python main.py >> "$LOG_FILE" 2>&1
STATUS=$?
echo "=== Fin de ejecución: $(date), exit code: $STATUS ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

find logs/ -name "boe_monitor_*.log" -mtime +30 -delete

exit $STATUS
