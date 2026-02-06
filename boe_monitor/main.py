#!/usr/bin/env python3
"""
Script principal de BOE Monitor.
Gestiona la ejecución del monitor para diferentes países.
"""

import json
import sys
import argparse
from pathlib import Path

from boe_analyzer import BOEMonitor
from logger_config import setup_logger

logger = setup_logger(__name__)


def load_config(config_file: str = 'config.json') -> dict:
    """
    Carga la configuración desde archivo JSON.
    
    Args:
        config_file: Ruta del archivo de configuración
    
    Returns:
        Diccionario con configuración
    """
    config_path = Path(config_file)
    
    if not config_path.exists():
        logger.error(f"Archivo de configuración no encontrado: {config_file}")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validaciones básicas
        required_keys = ['recipient_email', 'smtp_config', 'sources', 'db_config']
        for key in required_keys:
            if key not in config:
                logger.error(f"Falta clave requerida en configuración: {key}")
                sys.exit(1)
        
        logger.debug("Configuración cargada exitosamente")
        return config
        
    except json.JSONDecodeError as e:
        logger.error(f"Error al leer JSON: {e}")
        sys.exit(1)


def get_available_countries(config: dict) -> dict:
    """
    Obtiene los países disponibles desde la configuración.
    
    Args:
        config: Configuración cargada
    
    Returns:
        Diccionario de países disponibles
    """
    sources = config.get('sources', {})
    return {code: data.get('name', code) for code, data in sources.items()}


def validate_source_config(source_config: dict, country_code: str) -> bool:
    """
    Valida que la configuración de fuente sea válida.
    
    Args:
        source_config: Configuración de la fuente
        country_code: Código del país
    
    Returns:
        True si válida
    """
    required_fields = ['api_url_template', 'fetch_method']
    
    for field in required_fields:
        if field not in source_config:
            logger.error(f"Falta campo requerido en fuente {country_code}: {field}")
            return False
    
    return True


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Monitor de Boletines Oficiales (BOE)",
        epilog="Ejemplo: python main.py --country es"
    )
    
    parser.add_argument(
        '--country', '-c',
        help='Código del país a analizar (ej: es, fr, cz, kw)',
        default=None
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='Listar países disponibles'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("MONITOR DE BOLETINES OFICIALES".center(70))
    print("=" * 70)
    print()
    
    # Cargar configuración
    config = load_config()
    available_countries = get_available_countries(config)
    
    # Si se pide listar países
    if args.list:
        print("Países disponibles:")
        print()
        for code, name in available_countries.items():
            print(f"  {code:4s} - {name}")
        print()
        return
    
    # Determinar país a analizar
    if args.country:
        country_code = args.country.lower()
    else:
        country_code = 'es'
    
    # Validar que el país exista
    if country_code not in available_countries:
        logger.error(f"País no configurado: {country_code}")
        print()
        print("Usa --list para ver países disponibles")
        sys.exit(1)
    
    # Obtener configuración del país
    source_config = config['sources'][country_code].copy()
    source_config['country_code'] = country_code
    
    # Validar configuración
    if not validate_source_config(source_config, country_code):
        sys.exit(1)
    
    country_name = source_config.get('name', country_code)
    print(f"Analizando: {country_name} ({country_code})")
    print(f"Método de obtención: {source_config.get('fetch_method')}")
    print()
    
    # Crear y ejecutar monitor
    try:
        db_config = config.get('db_config')
        data_dir = config.get('data_dir', './boe_data')
        
        monitor = BOEMonitor(
            db_config=db_config,
            source_config=source_config,
            data_dir=data_dir
        )
        
        success = monitor.run_daily_check(
            recipient=config['recipient_email'],
            smtp=config['smtp_config']
        )
        
        print()
        if success:
            logger.info("Proceso completado exitosamente")
            print("✓ Proceso completado exitosamente")
        else:
            logger.warning("Proceso completado con advertencias")
            print("⚠ Proceso completado con advertencias")
        
        print("=" * 70)
        
    except KeyboardInterrupt:
        logger.info("Proceso interrumpido por usuario")
        print("\n\nProceso interrumpido")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        print()
        print("ERROR FATAL")
        print(f"Detalles: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
