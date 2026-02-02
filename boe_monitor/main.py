#!/usr/bin/env python3
"""
Script principal para ejecutar el monitor del BOE con soporte multi-país
"""

import json
import sys
import argparse
from pathlib import Path
from boe_analyzer import BOEMonitor

def load_config(config_file='config.json'):
    """Carga la configuración desde archivo JSON"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        print(f"❌ Error: No se encuentra el archivo de configuración '{config_file}'")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validar campos básicos
        if 'recipient_email' not in config:
             # Soporte legacy/migración
             pass 
             
        return config
    except json.JSONDecodeError as e:
        print(f"❌ Error al leer config.json: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Monitor de Boletines Oficiales")
    parser.add_argument('--country', '-c', help='Código del país a analizar (ej: es, fr)')
    parser.add_argument('--list', '-l', action='store_true', help='Listar fuentes disponibles')
    # Permitir flags dinámicos como --españa si se definen en config (opcional, pero mejor usar standard --country)
    # Sin embargo, el usuario pidió "--españa". Vamos a intentar mapear args sueltos.
    parser.add_argument('country_arg', nargs='?', help='Nombre o código del país (opcional)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  📋 MONITOR DE BOLETINES OFICIALES")
    print("=" * 60)
    print()
    
    config = load_config()
    
    # Normalizar estructura de config si es legacy
    if 'sources' not in config:
        # Crea una estructura default compatible con el código nuevo
        config['sources'] = {
            'es': {
                'name': 'España',
                'country_code': 'es',
                'url': 'https://www.boe.es',
                'api_url_template': 'https://www.boe.es/datosabiertos/api/boe/sumario/{date}',
                'parser': 'boe_xml'
            }
        }
    
    sources = config['sources']
    
    if args.list:
        print("Fuentes disponibles:")
        for code, data in sources.items():
            print(f" - {code}: {data.get('name', code)}")
        return

    # Determinar qué país ejecutar
    target_country = 'es' # Default
    
    if args.country:
        target_country = args.country
    elif args.country_arg:
        # Buscar si el argumento coincide con alguna key o name
        arg_lower = args.country_arg.lower().replace('--', '')
        found = False
        for code, data in sources.items():
            if code == arg_lower or data.get('name', '').lower() == arg_lower:
                target_country = code
                found = True
                break
        if not found:
            print(f"❌ No se encontró configuración para '{args.country_arg}'")
            print("Usa --list para ver disponibles.")
            sys.exit(1)
            
    # Verificar que existe en config
    if target_country not in sources:
        print(f"❌ No existe configuración para el código de país '{target_country}'")
        sys.exit(1)
        
    source_config = sources[target_country]
    source_config['country_code'] = target_country # Asegurar que esté set
    
    print(f"🚀 Iniciando análisis para: {source_config.get('name', target_country).upper()}")
    print(f"   Tipo de Parser: {source_config.get('parser', 'default')}")
    
    # Config DB default
    db_config = config.get('db_config', {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "boe_monitor",
        "port": 3306
    })
    
    data_dir = config.get('data_dir', './boe_data')
    
    monitor = BOEMonitor(db_config=db_config, source_config=source_config, data_dir=data_dir)
    
    success = monitor.run_daily_check(
        recipient_email=config['recipient_email'],
        smtp_config=config['smtp_config']
    )
    
    if success:
        print("\n✅ Proceso completado exitosamente")
    else:
        print("\n⚠️ El proceso finalizó con advertencias")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
