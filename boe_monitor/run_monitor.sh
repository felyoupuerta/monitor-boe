#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

ARGS="$@"
LOG_SUBDIR="default"
if [[ "$*" == *"--country"* ]]; then
    for word in $ARGS; do
        if [[ "$word" != --* ]]; then
            LOG_SUBDIR="$word"
            break
        fi
    done
fi

# Crear carpeta de logs 
LOG_DIR="logs/$LOG_SUBDIR"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/monitor_$(date +%Y%m%d).log"

if [ -f "$DIR/venv/bin/activate" ]; then
    source "$DIR/venv/bin/activate"
else
    
    if [ ! -f "venv/bin/activate" ]; then
         echo "Warning: No venv found" >> "$LOG_FILE"
    fi
fi

echo "=== Inicio de ejecución: $(date) Args: $ARGS ===" >> "$LOG_FILE"
python main.py $ARGS >> "$LOG_FILE" 2>&1
STATUS=$?
echo "=== Fin de ejecución: $(date), exit code: $STATUS ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
# Limpiar logs antiguos
find logs/ -name "*.log" -mtime +30 -delete

exit $STATUS
