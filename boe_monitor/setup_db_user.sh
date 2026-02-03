#!/bin/bash

echo "🔧 Configurando base de datos MariaDB para BOE Monitor..."

SQL_COMMANDS="
CREATE DATABASE IF NOT EXISTS boe_monitor;
CREATE USER IF NOT EXISTS 'boe_monitor'@'localhost' IDENTIFIED BY 'secure_boe_password';
GRANT ALL PRIVILEGES ON boe_monitor.* TO 'boe_monitor'@'localhost';
FLUSH PRIVILEGES;
"

echo "Ejecutando comandos SQL..."

#MODIFICO DEPENDE DE LA BASE DE DATOS INSTALADA MYSQL O MARIADB(FUNCIONA PA LAS 2)
sudo mariadb -e "$SQL_COMMANDS"

if [ $? -eq 0 ]; then
    echo "Configuración completada con éxito."
    echo "   - BD: boe_monitor"
    echo "   - Usuario: boe_monitor"
    echo "   - Password: secure_boe_password"
else
    echo "Falló la configuración automática."
    echo "   Por favor, ejecuta manualmente:"
    echo "   mariadb -u root -p -e \"$SQL_COMMANDS\""
fi
