#!/bin/bash
# Instalador de cron job para BOE Monitor

echo "================================"
echo "  BOE Monitor - Instalador Cron"
echo "================================"
echo ""

# Obtener el directorio actual (absoluto)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN=$(which python3)

echo "Directorio del proyecto: $SCRIPT_DIR"
echo "Python encontrado en: $PYTHON_BIN"
echo ""

# Preguntar la hora de ejecución
echo "¿A qué hora quieres ejecutar el monitor diariamente?"
read -p "Hora (0-23, por defecto 9): " HOUR
HOUR=${HOUR:-9}

read -p "Minutos (0-59, por defecto 0): " MINUTE
MINUTE=${MINUTE:-0}

echo ""
echo "El monitor se ejecutará todos los días a las $HOUR:$MINUTE"
echo ""

# Crear la entrada de cron
CRON_CMD="$MINUTE $HOUR * * * cd $SCRIPT_DIR && $PYTHON_BIN $SCRIPT_DIR/main.py >> $SCRIPT_DIR/logs/boe_monitor.log 2>&1"

echo "Entrada de cron que se añadirá:"
echo "$CRON_CMD"
echo ""

read -p "¿Continuar con la instalación? (s/n): " CONFIRM

if [ "$CONFIRM" != "s" ] && [ "$CONFIRM" != "S" ]; then
    echo "Instalación cancelada"
    exit 0
fi

# Crear directorio de logs
mkdir -p "$SCRIPT_DIR/logs"

# Añadir al crontab
(crontab -l 2>/dev/null | grep -v "boe_monitor/main.py"; echo "$CRON_CMD") | crontab -

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Cron job instalado correctamente"
    echo ""
    echo "El BOE Monitor se ejecutará automáticamente a las $HOUR:$MINUTE todos los días"
    echo ""
    echo "Para ver tus cron jobs:"
    echo "  crontab -l"
    echo ""
    echo "Para ver los logs:"
    echo "  tail -f $SCRIPT_DIR/logs/boe_monitor.log"
    echo ""
    echo "Para eliminar el cron job:"
    echo "  crontab -e"
    echo "  (y elimina la línea que contiene 'boe_monitor/main.py')"
else
    echo ""
    echo "❌ Error al instalar el cron job"
    echo "Puedes hacerlo manualmente con: crontab -e"
    exit 1
fi
