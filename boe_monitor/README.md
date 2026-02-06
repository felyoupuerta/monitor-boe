# BOE Monitor

Monitor automático profesional de Boletines Oficiales con soporte multi-país.

## Características

- 🌍 **Multi-país**: España, Francia, República Checa, Kuwait
- 🔄 **Automático**: Ejecución diaria programada
- 📧 **Notificaciones**: Correos HTML profesionales
- 💾 **Persistencia**: Base de datos MySQL con deduplicación inteligente
- 📊 **Logging**: Sistema de logging estructurado
- 🚀 **Producción-ready**: Código limpio y documentado

## Requisitos

- Python 3.8+
- MySQL Server 5.7+
- Chrome/Chromium (opcional, para Francia y República Checa)

## Instalación Rápida

```bash
# 1. Descargar dependencias
pip install -r requirements.txt

# 2. Configurar base de datos
# Ver DOCUMENTATION.md para pasos detallados

# 3. Crear configuración
cp config.example.json config.json
# Editar config.json con tus datos

# 4. Probar email
python tests/test_email.py
```

## Uso

```bash
# Ejecución manual - España
python main.py

# Ejecución manual - Otros países
python main.py --country fr    # Francia
python main.py --country cz    # República Checa
python main.py --country kw    # Kuwait

# Ver países disponibles
python main.py --list

# Ejecución automática (cron)
0 8 * * * cd /ruta/al/proyecto && python main.py --country es
```

## Estructura

```
├── main.py              # Script principal
├── boe_analyzer.py      # Lógica de monitor
├── db_manager.py        # Gestor de BD
├── logger_config.py     # Sistema de logging
├── config.json          # Configuración (genera desde .example)
├── config.example.json  # Template de configuración
├── tests/               # Scripts de prueba
├── boe_data/            # Datos históricos
├── logs/                # Archivos de log
└── DOCUMENTATION.md     # Documentación completa
```

## Documentación

Ver [DOCUMENTATION.md](DOCUMENTATION.md) para:
- Instalación detallada
- Configuración completa
- Escalabilidad de países
- Troubleshooting
- Mantenimiento en producción

## Autenticación Gmail

Para usar Gmail como servidor SMTP:

1. Habilitar verificación en 2 pasos: https://myaccount.google.com/security
2. Generar "Contraseña de aplicación": https://myaccount.google.com/apppasswords
3. Usar esa contraseña en `config.json` (no tu contraseña personal)

## Quick Start - Producción

```bash
# Crear usuario BD
CREATE USER 'boe_monitor'@'localhost' IDENTIFIED BY 'password_segura';
GRANT ALL PRIVILEGES ON boe_monitor.* TO 'boe_monitor'@'localhost';

# Instalar
pip install -r requirements.txt

# Configurar
cp config.example.json config.json
nano config.json  # Editar con tus datos

# Probar
python tests/test_email.py

# Programar ejecución (cron)
crontab -e
# Agregar: 0 8 * * * cd /ruta/al/proyecto && python main.py --country es
```

## Troubleshooting

| Error | Solución |
|-------|----------|
| SMTPAuthenticationError | Ver sección Gmail - usar contraseña de aplicación |
| Conexión BD rechazada | Verificar credenciales MySQL en config.json |
| No descarga datos | Verificar URL en config, revisar logs |
| Chrome no encontrado | Instalar chromium/chrome (requerido para Selenium) |

Ver más en [DOCUMENTATION.md](DOCUMENTATION.md)

## Desarrollo

```bash
# Crear nuevo país
1. Agregar entrada en config.json
2. (Opcional) Crear método _fetch_XX() para descarga especial
3. (Opcional) Crear método _parse_XX() para parseo especial
4. Probar: python main.py --country xx
```

## Autor

**Felipe Angeriz** - Enero 2026

## Versión

1.0.0 - Production Ready
