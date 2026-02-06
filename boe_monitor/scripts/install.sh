#!/bin/bash
#
# Script de instalación inicial para BOE Monitor
# Ejecutar una sola vez al configurar el proyecto
#

set -e

echo "=========================================="
echo "Instalación Inicial - BOE Monitor"
echo "=========================================="
echo ""

# 1. Instalar dependencias Python
echo "1. Instalando dependencias Python..."
pip install -r requirements.txt
echo "   ✓ Dependencias instaladas"
echo ""

# 2. Crear directorio de datos si falta
echo "2. Creando estructura de directorios..."
mkdir -p boe_data logs tests
echo "   ✓ Directorios creados"
echo ""

# 3. Verificar configuración
echo "3. Verificando configuración..."
if [ ! -f "config.json" ]; then
    echo "   ATENCIÓN: config.json no encontrado"
    echo "   Copia config.example.json a config.json y edítalo:"
    echo "   $ cp config.example.json config.json"
    echo "   $ nano config.json"
else
    echo "   ✓ config.json encontrado"
fi
echo ""

# 4. Ejecutar validación
echo "4. Ejecutando validación pre-producción..."
if python validate.py; then
    echo ""
    echo "=========================================="
    echo "✓ Instalación completada exitosamente"
    echo "=========================================="
    echo ""
    echo "Próximos pasos:"
    echo "1. Configurar base de datos:"
    echo "   $ sudo bash scripts/setup_db.sh"
    echo ""
    echo "2. Probar email:"
    echo "   $ python tests/test_email.py"
    echo ""
    echo "3. Hacer primera ejecución:"
    echo "   $ python main.py --list"
    echo "   $ python main.py --country es"
else
    echo ""
    echo "✗ Validación fallida - Revisa los errores arriba"
    exit 1
fi
