# 🚀 BOE Monitor 2.0 - Edición "Enterprise"

Esta versión ha sido mejorada para ser más robusta y escalable, utilizando **MariaDB/MySQL** en lugar de archivos JSON planos.

## 🌟 Nuevas Características
- **Persistencia en Base de Datos**: Almacenamiento eficiente y consultable en MariaDB.
- **Logs de Ejecución**: Registro detallado de cada ejecución en la tabla `execution_logs`.
- **Deduplicación**: Evita duplicidad de registros automáticamente.
- **Escalabilidad**: Preparado para manejar años de historial sin problemas de rendimiento.

## 🛠️ Instrucciones de Actualización

### 1. Requisitos Previos
Asegúrate de tener instalado MariaDB o MySQL:
```bash
sudo pacman -S mariadb  # Arch Linux
# O tu gestor de paquetes correspondiente
sudo systemctl start mariadb
```

### 2. Configuración
Tu archivo `config.json` ha sido actualizado automáticamente con la sección `db_config`:
```json
"db_config": {
    "host": "localhost",
    "user": "root",
    "password": "",  <-- Pon tu contraseña de root si tienes
    "database": "boe_monitor",
    "port": 3306
}
```

### 3. Migración de Datos (Opcional)
Si ya tienes datos históricos en JSON, puedes importarlos a la base de datos:
```bash
python migrate_json_to_db.py
```

### 4. Ejecución
Sigue ejecutando como siempre:
```bash
python main.py
```
El sistema creará automáticamente la base de datos y las tablas necesarias en la primera ejecución.

## 📊 Estructura de la Base de Datos
- **Table `publications`**: Almacena cada disposición del BOE (Título, Sección, Departamento, URL).
- **Table `execution_logs`**: Auditoría de ejecuciones del monitor.
