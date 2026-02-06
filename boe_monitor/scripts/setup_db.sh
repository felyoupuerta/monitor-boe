#!/bin/bash
#
# Script de configuración de base de datos para BOE Monitor
# Crea la BD y usuario necesarios en MySQL/MariaDB
#

set -e

echo "=========================================="
echo "Configuración de BD para BOE Monitor"
echo "=========================================="
echo ""

# Validar que se ejecuta con permisos de root
if [ "$EUID" -ne 0 ]; then 
    echo "Este script debe ejecutarse con sudo"
    exit 1
fi

# Solicitar credenciales si no se proporcionan
if [ -z "$DB_USER" ]; then
    DB_USER="boe_monitor"
fi

if [ -z "$DB_PASS" ]; then
    read -sp "Contraseña para usuario BD [secure_boe_password]: " DB_PASS
    DB_PASS="${DB_PASS:-secure_boe_password}"
    echo ""
fi

# Comandos SQL a ejecutar
SQL_COMMANDS="
DROP USER IF EXISTS '${DB_USER}'@localhost;
CREATE DATABASE IF NOT EXISTS boe_monitor;
CREATE USER '${DB_USER}'@localhost IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON boe_monitor.* TO '${DB_USER}'@localhost;
FLUSH PRIVILEGES;
"

echo "Ejecutando comandos SQL..."
echo ""

# Detectar motor disponible (MySQL o MariaDB)
if command -v mariadb &> /dev/null; then
    DB_CLI="mariadb"
elif command -v mysql &> /dev/null; then
    DB_CLI="mysql"
else
    echo "Error: MySQL o MariaDB no encontrado"
    exit 1
fi

echo "Usando: $DB_CLI"
echo ""

# Ejecutar comandos
if $DB_CLI -u root -e "$SQL_COMMANDS"; then
    echo ""
    echo "✓ Configuración exitosa"
    echo ""
    echo "Detalles:"
    echo "  Base de datos: boe_monitor"
    echo "  Usuario: ${DB_USER}"
    echo "  Host: localhost"
    echo ""
    echo "Actualiza config.json con estas credenciales"
else
    echo ""
    echo "Error: Fallo en la configuración"
    exit 1
fi
