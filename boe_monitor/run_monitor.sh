#!/bin/bash
# Script para ejecutar el monitor del BOE con logging

# Directorio del script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Crear directorio de logs si no existe
mkdir -p logs

# Nombre del archivo de log con fecha
LOG_FILE="logs/boe_monitor_$(date +%Y%m%d).log"

# Ejecutar el monitor y guardar salida
echo "=== Inicio de ejecución: $(date) ===" >> "$LOG_FILE"
python3 boe_analyzer.py >> "$LOG_FILE" 2>&1
echo "=== Fin de ejecución: $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Limpiar logs antiguos (más de 30 días)
find logs/ -name "boe_monitor_*.log" -mtime +30 -delete
