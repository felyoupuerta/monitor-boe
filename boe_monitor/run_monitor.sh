#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Argumentos para el script python (ej: --country es)
ARGS="$@"

# Determinar subcarpeta de logs basada en el argumento si existe
# Si se pasa "--country es" o "es", intentamos usar eso. Simple: usar "default" si no hay args
LOG_SUBDIR="default"
if [[ "$*" == *"--country"* ]]; then
    # Extraer el codigo de pais seria complejo en bash puro de forma robusta rapida,
    # asumiendo que el usuario usará wrapper scripts o cron distintos.
    # Vamos a usar una carpeta única global si no se complica.
    # Pero el usuario pidió carpetas distintas.
    # Estrategia: Si hay argumentos, los hasheamos o usamos el primero sanitizado.
    # Simplificación: logs/global por ahora, y dejamos que main.py maneje su salida.
    # REVISIÓN: El usuario quiere carpetas distintas.
    # Si ejecutamos ./run_monitor.sh --country es
    # Log: logs/es/monitor_DATE.log
    
    # Intento simple: buscar 'es', 'fr' en los args
    for word in $ARGS; do
        if [[ "$word" != --* ]]; then
            LOG_SUBDIR="$word"
            break
        fi
    done
fi

# Crear carpeta de logs específica
LOG_DIR="logs/$LOG_SUBDIR"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/monitor_$(date +%Y%m%d).log"

if [ -f "$DIR/venv/bin/activate" ]; then
    source "$DIR/venv/bin/activate"
else
    # Fallback si no está en venv/
    if [ ! -f "venv/bin/activate" ]; then
         echo "Warning: No venv found" >> "$LOG_FILE"
    fi
fi

echo "=== Inicio de ejecución: $(date) Args: $ARGS ===" >> "$LOG_FILE"
python main.py $ARGS >> "$LOG_FILE" 2>&1
STATUS=$?
echo "=== Fin de ejecución: $(date), exit code: $STATUS ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Limpiar logs antiguos (más de 30 días)
find logs/ -name "*.log" -mtime +30 -delete

exit $STATUS
