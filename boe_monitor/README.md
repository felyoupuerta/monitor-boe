# 📋 BOE Monitor - Analizador del Boletín Oficial del Estado

Sistema automatizado para monitorear cambios diarios en el BOE y recibir notificaciones por correo electrónico.

## 🚀 Características

- ✅ Descarga automática del BOE diario
- 🔍 Detección de cambios respecto al día anterior
- 📧 Notificaciones por correo con resumen detallado
- 💾 Almacenamiento histórico de datos
- 🎨 Correos HTML con formato profesional
- ⚙️ Fácil configuración y automatización

## 📦 Instalación

### 1. Requisitos previos

- Python 3.7 o superior
- pip (gestor de paquetes de Python)

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

## ⚙️ Configuración

### 1. Configurar el correo electrónico

El sistema soporta cualquier servidor SMTP. Aquí tienes ejemplos para los más comunes:

#### Gmail

1. Activa la verificación en 2 pasos en tu cuenta de Google
2. Genera una contraseña de aplicación: https://myaccount.google.com/apppasswords
3. Usa estos valores en la configuración:
   - Server: `smtp.gmail.com`
   - Port: `587`
   - Username: tu correo de Gmail
   - Password: la contraseña de aplicación generada

#### Outlook/Hotmail

- Server: `smtp-mail.outlook.com`
- Port: `587`

#### Yahoo

- Server: `smtp.mail.yahoo.com`
- Port: `587`

### 2. Crear archivo de configuración

Copia el archivo de ejemplo y edítalo con tus datos:

```bash
cp config.example.json config.json
nano config.json  # o usa tu editor preferido
```

Edita los campos:
```json
{
  "recipient_email": "tu_email@ejemplo.com",
  "smtp_config": {
    "server": "smtp.gmail.com",
    "port": 587,
    "username": "tu_email@gmail.com",
    "password": "tu_contraseña_de_aplicacion"
  }
}
```

## 🏃 Uso

### Ejecución manual

```bash
python boe_analyzer.py
```

### Automatización con Cron (Linux/Mac)

Para ejecutar el script automáticamente todos los días a las 9:00 AM:

```bash
# Editar crontab
crontab -e

# Añadir esta línea (ajusta la ruta al script)
0 9 * * * cd /ruta/a/boe_monitor && /usr/bin/python3 boe_analyzer.py >> logs/boe_monitor.log 2>&1
```

### Automatización con Task Scheduler (Windows)

1. Abre el "Programador de tareas"
2. Crear tarea básica
3. Nombre: "Monitor BOE"
4. Desencadenador: Diariamente a las 9:00 AM
5. Acción: Iniciar programa
   - Programa: `python.exe`
   - Argumentos: `ruta\completa\a\boe_analyzer.py`
   - Iniciar en: `ruta\completa\a\boe_monitor\`

## 📊 Qué detecta el sistema

El monitor compara el BOE de hoy con el de ayer y detecta:

- **Nuevas publicaciones**: Documentos que aparecen hoy y no estaban ayer
- **Publicaciones eliminadas**: Documentos que estaban ayer pero no aparecen hoy
- **Total de publicaciones**: Cantidad de documentos en cada día

## 📧 Formato del correo

El correo incluye:

- 📊 Resumen con estadísticas
- ✨ Lista de nuevas publicaciones con:
  - Título completo
  - Sección del BOE
  - Departamento emisor
  - Rango (Ley, Real Decreto, Orden, etc.)
  - Enlace directo al PDF
- 🗑️ Lista de publicaciones eliminadas

## 📁 Estructura de archivos

```
boe_monitor/
├── boe_analyzer.py          # Script principal
├── config.json              # Tu configuración (crear desde example)
├── config.example.json      # Plantilla de configuración
├── requirements.txt         # Dependencias Python
├── README.md               # Esta documentación
├── boe_data/               # Datos históricos del BOE (se crea automáticamente)
│   ├── boe_20240101.json
│   ├── boe_20240102.json
│   └── ...
└── logs/                   # Logs de ejecución (opcional)
```

## 🔒 Seguridad

**IMPORTANTE**: 
- Nunca compartas tu archivo `config.json` (contiene tu contraseña)
- Usa contraseñas de aplicación, no tu contraseña principal
- El archivo `config.json` está en `.gitignore` por defecto

## 🛠️ Solución de problemas

### Error al enviar correo

- Verifica que estés usando una contraseña de aplicación (no tu contraseña normal)
- Comprueba que la verificación en 2 pasos esté activa
- Revisa que el servidor SMTP y el puerto sean correctos

### No se detectan cambios

- El BOE se publica normalmente entre las 8:00 y 9:00 AM
- Los fines de semana y festivos puede que no haya publicaciones
- En la primera ejecución no habrá comparación (es normal)

### Error al descargar el BOE

- Verifica tu conexión a internet
- El sitio del BOE podría estar temporalmente no disponible
- Intenta de nuevo en unos minutos

## 📝 Personalización

Puedes modificar el script para:

- Filtrar por secciones específicas del BOE
- Añadir palabras clave de interés
- Cambiar el formato del correo
- Ajustar la hora de ejecución
- Añadir múltiples destinatarios

## 📄 Licencia

Este proyecto es de código abierto y está disponible para uso personal y comercial.

## 🤝 Contribuciones

¡Las mejoras y sugerencias son bienvenidas!

## 📞 Soporte

Para problemas o preguntas, consulta la documentación oficial del BOE: https://www.boe.es
