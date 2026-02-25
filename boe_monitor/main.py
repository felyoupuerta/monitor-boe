#!/usr/bin/env python3
import json
import sys
import os
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
from boe_analyzer import BOEMonitor

# Cargar variables de entorno desde .env
load_dotenv()

def setup_logging(country_code):
    """Configura el sistema de logs con rotación y formato profesional"""
    log_dir = Path("logs") / country_code
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"monitor_{country_code}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def load_config(config_file='config.json'):
    config_path = Path(config_file)
    if not config_path.exists():
        logging.error(f"No se encuentra el archivo de configuración '{config_file}'")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        logging.error(f"Error al leer config.json: {e}")
        sys.exit(1)

def get_secure_config():
    """Construye la configuración segura combinando JSON y variables de entorno"""
    
    db_pass = os.getenv("DB_PASSWORD")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    # Si faltan las contraseñas, avisamos pero no matamos el proceso inmediatamente 
    # si el usuario solo quiere ver la ayuda o listar fuentes.
    # Pero para la ejecución normal, las necesitaremos.
    missing = []
    if not db_pass: missing.append("DB_PASSWORD")
    if not smtp_pass: missing.append("SMTP_PASSWORD")

    if missing:
        print(f"⚠️  ADVERTENCIA: Faltan variables de entorno: {', '.join(missing)}")
        print("Asegúrate de configurar el archivo .env con las credenciales necesarias.")
        # No salimos aquí, dejamos que falle al intentar conectar a la DB o SMTP 
        # para dar más flexibilidad en pruebas locales sin persistencia.

    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": db_pass or "",
        "database": os.getenv("DB_NAME", "boe_monitor"),
        "port": int(os.getenv("DB_PORT", 3306))
    }

    smtp_config = {
        "server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", 587)),
        "username": os.getenv("SMTP_USER", ""),
        "password": smtp_pass or ""
    }

    return db_config, smtp_config

def main():
    parser = argparse.ArgumentParser(description="Monitor de Boletines Oficiales")
    parser.add_argument('--country', '-c', help='Código del país a analizar (ej: es, fr)')
    parser.add_argument('--date', '-d', help='Fecha a analizar (YYYY-MM-DD), por defecto hoy')
    parser.add_argument('--list', '-l', action='store_true', help='Listar fuentes disponibles')
    parser.add_argument('country_arg', nargs='?', help='Nombre o código del país (opcional)')
    
    args = parser.parse_args()
    
    config = load_config()
    sources = config.get('sources', {})
    
    if args.list:
        print("Fuentes disponibles:")
        for code, data in sources.items():
            print(f" - {code}: {data.get('name', code)}")
        return

    # Determinar país objetivo
    target_country = 'es' 
    if args.country:
        target_country = args.country
    elif args.country_arg:
        arg_lower = args.country_arg.lower().replace('--', '')
        for code, data in sources.items():
            if code == arg_lower or data.get('name', '').lower() == arg_lower:
                target_country = code
                break
    
    if target_country not in sources:
        print(f"❌ No existe configuración para el país '{target_country}'")
        sys.exit(1)

    # Configurar Logging
    logger = setup_logging(target_country)
    logger.info("=" * 60)
    logger.info(f"INICIANDO MONITOR: {target_country.upper()}")
    
    # Obtener configuración segura
    db_config, smtp_config = get_secure_config()
    source_config = sources[target_country]
    source_config['country_code'] = target_country
    data_dir = config.get('data_dir', './boe_data')
    
    # Iniciar Monitor
    monitor = BOEMonitor(db_config=db_config, source_config=source_config, data_dir=data_dir)
    
    recipient_email = config.get('recipient_email', [])
    
    # Ejecutar análisis (el método run ahora es genérico para manual/cron)
    success = monitor.run(
        recipient_email=recipient_email,
        smtp_config=smtp_config,
        check_date=args.date
    )
    
    if success:
        logger.info("Proceso finalizado correctamente")
    else:
        logger.error("El proceso encontró errores durante la ejecución")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()