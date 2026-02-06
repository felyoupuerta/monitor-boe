#!/bin/bash
#
# Script para ejecutar BOE Monitor
# Puede ser usado por cron o ejecución manual
#
# Uso:
#   ./run.sh              # Ejecutar España (por defecto)
#   ./run.sh --country es # Ejecutar España
#   ./run.sh --country fr # Ejecutar Francia
#

set -e

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Crear directorio de logs si no existe
mkdir -p logs

# Obtener país a analizar
COUNTRY="${1:-es}"

# Extraer código de país
if [[ "$COUNTRY" == "--country" ]]; then
    COUNTRY="$2"
fi

# Validar formato
if [[ "$COUNTRY" != *"--"* ]]; then
    COUNTRY_CODE="$COUNTRY"
else
    COUNTRY_CODE="es"
fi

# Archivo de log
LOG_FILE="logs/monitor_${COUNTRY_CODE}_$(date +%Y%m%d).log"

echo "=========================================="
echo "BOE Monitor - Ejecución"
echo "=========================================="
echo "País: $COUNTRY_CODE"
echo "Log: $LOG_FILE"
echo "Inicio: $(date)"
echo "=========================================="
echo ""

# Activar venv si existe
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtual environment activado"
fi

# Ejecutar monitor
if python main.py --country "$COUNTRY_CODE" >> "$LOG_FILE" 2>&1; then
    echo "✓ Proceso completado exitosamente"
    exit 0
else
    echo "✗ Error en la ejecución (ver $LOG_FILE para detalles)"
    exit 1
fi
