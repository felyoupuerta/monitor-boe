# BOE Monitor - Documentación Técnica

## Descripción General

BOE Monitor es una aplicación Python profesional para monitorear automáticamente Boletines Oficiales de diferentes países. Detecta nuevas publicaciones, las almacena en una base de datos, y envía notificaciones por correo electrónico.

**Características:**
- ✅ Soporte multi-país escalable (España, Francia, República Checa, Kuwait)
- ✅ Múltiples métodos de obtención de datos (HTTP, Selenium, APIs especializadas)
- ✅ Base de datos MySQL con detección de cambios basada en hash
- ✅ Notificaciones por correo HTML profesionales
- ✅ Logging estructurado y comprensivo
- ✅ Apto para producción

## Requisitos del Sistema

- **Python 3.8+**
- **MySQL Server 5.7+**
- **Chrome/Chromium** (solo si se usa Selenium para Francia o República Checa)

## Instalación

### 1. Clonar o descargar el repositorio

```bash
cd monitor-boe
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar base de datos

#### Opción A: Crear usuario y BD manualmente

```sql
CREATE DATABASE boe_monitor;
CREATE USER 'boe_monitor'@'localhost' IDENTIFIED BY 'secure_boe_password';
GRANT ALL PRIVILEGES ON boe_monitor.* TO 'boe_monitor'@'localhost';
FLUSH PRIVILEGES;
```

#### Opción B: Usar script de configuración (Linux/Unix)

```bash
chmod +x setup_db_user.sh
sudo ./setup_db_user.sh
```

### 4. Configurar aplicación

#### Crear archivo de configuración

Copiar y editar:

```bash
cp config.example.json config.json
```

Editar `config.json` con:
- **Email destinatarios**: Dónde enviar notificaciones
- **Credenciales SMTP**: Para enviar emails (ver sección Gmail)
- **Credenciales BD**: Usuario y contraseña MySQL
- **Países a monitorear**: Editar sección `sources`

#### Configuración de Gmail

Para usar Gmail como servidor SMTP:

1. Abrir: https://myaccount.google.com/security
2. Habilitar "Verificación en 2 pasos"
3. Generar "Contraseña de aplicación" en: https://myaccount.google.com/apppasswords
4. Usar esa contraseña en `config.json` (no tu contraseña normal)

### 5. Probar configuración

```bash
python tests/test_email.py
```

Este script verifica:
- Conexión SMTP
- Autenticación
- Envío de email de prueba

## Uso

### Ejecución Manual

```bash
# Analizar España (por defecto)
python main.py

# Analizar un país específico
python main.py --country es
python main.py --country fr
python main.py --country cz
python main.py --country kw

# Listar países disponibles
python main.py --list
```

### Ejecución Automática (Cron)

#### Linux/Unix - Ejecutar a las 8 AM cada día

```bash
# Editar crontab
crontab -e

# Agregar estas líneas
0 8 * * * cd /ruta/a/monitor-boe && python main.py --country es
0 8 * * * cd /ruta/a/monitor-boe && python main.py --country fr
```

#### Windows - Usar Programador de Tareas

1. Abrir "Programador de Tareas"
2. Crear "Tarea básica"
3. Desencadenador: Hora específica (8 AM)
4. Acción: `python main.py --country es`
5. Directorio: Ruta del proyecto

## Estructura del Proyecto

```
monitor-boe/
├── main.py                    # Script principal y punto de entrada
├── boe_analyzer.py            # Lógica de monitor (descarga, parseo, notificaciones)
├── db_manager.py              # Gestor de base de datos
├── logger_config.py           # Configuración centralizada de logging
├── config.json                # Configuración (NO INCLUIR EN GIT)
├── config.example.json        # Ejemplo de configuración
├── requirements.txt           # Dependencias Python
├── README.md                  # Este archivo
├── tests/
│   └── test_email.py          # Script de prueba de correo
├── boe_data/
│   ├── es/                    # Datos históricos España
│   ├── fr/                    # Datos históricos Francia
│   └── ...
└── logs/                      # Archivos de log
    └── boe_monitor_*.log
```

## Arquitectura

### Flujo de Ejecución

1. **main.py** → Punto de entrada, carga configuración, valida parámetros
2. **BOEMonitor** → Clase principal que orquesta:
   - **fetch_data()** → Descarga contenido según país
   - **parse()** → Extrae publicaciones según formato
   - **run_daily_check()** → Orquesta descarga→parseo→guardado→notificación
3. **DatabaseManager** → Gestiona BD (deduplicación, almacenamiento)
4. **Email** → Envía notificaciones formateadas en HTML

### Escalabilidad de Países

Agregar un nuevo país es sencillo:

#### 1. Agregar configuración en `config.json`

```json
{
  "country_code": "pt",
  "name": "Portugal",
  "url": "https://example.com",
  "api_url_template": "https://example.com/api/{date}",
  "fetch_method": "requests",
  "parser_rules": { ... }
}
```

#### 2. (Opcional) Crear parser específico

Si el sitio requiere parseo especial, agregar método en `BOEMonitor`:

```python
def _fetch_pt(self, url, headers, date):
    # Implementación específica
    ...

def _parse_pt(self, content):
    # Parseo específico
    ...
```

### Validación de Publicaciones

El sistema usa **hash SHA256** del contenido para detectar:

- ✅ Publicaciones duplicadas (misma fecha + mismo contenido)
- ✅ Cambios en contenido (título, sección, departamento)
- ❌ Evita falsos positivos por pequeñas diferencias de formato

```python
hash = SHA256(titulo + seccion + departamento)
UNIQUE KEY(boe_date, content_hash)
```

## Logging

Los logs se guardan en `logs/boe_monitor_YYYYMMDD_HHMMSS.log`

### Niveles de Log

- **DEBUG** → Información detallada (solo archivo)
- **INFO** → Eventos importantes (archivo + consola)
- **WARNING** → Problemas potenciales
- **ERROR** → Errores que requieren atención

### Supervisar Logs

```bash
# Ver últimas líneas
tail -f logs/boe_monitor_*.log

# Buscar errores
grep ERROR logs/boe_monitor_*.log
```

## Base de Datos

### Esquema

```sql
CREATE TABLE publications_XX (
    id INT AUTO_INCREMENT PRIMARY KEY,
    boe_date DATE NOT NULL,
    title TEXT NOT NULL,
    section VARCHAR(255),
    department VARCHAR(255),
    url_pdf VARCHAR(512),
    content_hash VARCHAR(64),              -- SHA256 para deduplicación
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_publication (boe_date, content_hash),
    INDEX idx_date (boe_date),
    INDEX idx_hash (content_hash)
);
```

### Mantenimiento

```sql
-- Ver tamaño de tablas
SELECT table_name, ROUND(((data_length + index_length) / 1024 / 1024), 2) 
FROM information_schema.tables 
WHERE table_schema = 'boe_monitor';

-- Limpiar publicaciones antiguas (mantener 1 año)
DELETE FROM publications_es 
WHERE boe_date < DATE_SUB(NOW(), INTERVAL 1 YEAR);
```

## Troubleshooting

### Error: "Se rechazó la conexión"

**Causa**: Base de datos no accesible

**Solución**:
```bash
mysql -h localhost -u boe_monitor -p
# Probar conexión
```

### Error: "SMTPAuthenticationError"

**Causa**: Credenciales SMTP incorrectas

**Solución**:
- Para Gmail: Usar "Contraseña de aplicación" (ver sección instalación)
- Verificar usuario y contraseña en config.json
- Correr: `python tests/test_email.py`

### Error: "Por favor, permita el acceso a las aplicaciones menos seguras"

**Solución**: Gmail requiere "Contraseña de aplicación", no contraseña de cuenta

### No se descargan datos (Selenium)

**Causa**: Chrome no instalado o Chromedriver incompatible

**Solución**:
```bash
# Linux
sudo apt-get install chromium-browser

# macOS
brew install chromium

# Windows
# Descargar: https://chromedriver.chromium.org/
```

### Logs vacíos o no se crean

**Solución**: Verificar permisos de carpeta `logs/`:
```bash
chmod 755 logs/
```

## Seguridad

### Recomendaciones para Producción

1. **Base de datos**
   - No usar contraseña por defecto
   - Limitar acceso por IP
   - Hacer backups regulares

2. **SMTP**
   - Usar "Contraseña de aplicación" (Gmail)
   - No versionar `config.json` (contiene credenciales)
   - Usar `.gitignore`:
     ```
     config.json
     logs/
     boe_data/
     ```

3. **Archivos**
   - Cambiar permisos: `chmod 600 config.json`
   - Ejecutar como usuario sin privilegios

4. **Servidor**
   - Usar HTTPS si se expone en red
   - Limitar acceso a BD (firewall)
   - Monitorear logs regularmente

## Mantenimiento

### Actualizar Dependencias

```bash
pip install --upgrade -r requirements.txt
```

### Monitoreo

Crear script de verificación diaria:

```bash
#!/bin/bash
# check_monitor.sh
if [ ! -f logs/boe_monitor_*.log ]; then
    echo "WARNING: No logs found" | mail -s "BOE Monitor" admin@example.com
fi

# Buscar errores
if grep -q "ERROR" logs/boe_monitor_*.log; then
    echo "ALERT: Errors found" | mail -s "BOE Monitor Alert" admin@example.com
fi
```

### Rotación de Logs

Usar `logrotate` (Linux):

```bash
# /etc/logrotate.d/boe-monitor
/ruta/a/monitor-boe/logs/boe_monitor_*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
}
```

## Desarrollo

### Ejecutar Tests

```bash
python tests/test_email.py
```

### Estructura de Código

- **main.py**: Interfaz CLI, punto de entrada
- **boe_analyzer.py**: Lógica central (descarga, parseo, notificación)
- **db_manager.py**: Abstracción de BD
- **logger_config.py**: Logging centralizado

### Agregar Nuevo País

1. Agregar entrada en `config.json`
2. Crear método `_fetch_XX()` si descarga especial es necesaria
3. Crear método `_parse_XX()` si parseo especial es necesario
4. Probar: `python main.py --country xx`

## Licencia y Autoría

**Autor**: Felipe Angeriz
**Creado**: Enero 2026
**Versión**: 1.0.0

## Soporte

Para reportar issues o solicitar features, contactar al desarrollador.

---

**Última actualización**: Febrero 2026
