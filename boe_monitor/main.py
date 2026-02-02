#!/usr/bin/env python3
"""
Script principal para ejecutar el monitor del BOE con configuración desde archivo
"""

import json
import sys
from pathlib import Path
from boe_analyzer import BOEMonitor

def load_config(config_file='config.json'):
    """Carga la configuración desde archivo JSON"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        print(f"❌ Error: No se encuentra el archivo de configuración '{config_file}'")
        print("   Por favor, crea 'config.json' a partir de 'config.example.json'")
        print("\n   Pasos:")
        print("   1. cp config.example.json config.json")
        print("   2. Edita config.json con tus datos de correo")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validar campos requeridos
        required_fields = ['recipient_email', 'smtp_config']
        for field in required_fields:
            if field not in config:
                print(f"❌ Error: Falta el campo '{field}' en config.json")
                sys.exit(1)
        
        smtp_required = ['server', 'port', 'username', 'password']
        for field in smtp_required:
            if field not in config['smtp_config']:
                print(f"❌ Error: Falta el campo 'smtp_config.{field}' en config.json")
                sys.exit(1)
        
        return config
    
    except json.JSONDecodeError as e:
        print(f"❌ Error al leer config.json: {e}")
        sys.exit(1)

def main():
    """Función principal"""
    print("=" * 60)
    print("  📋 BOE MONITOR - Analizador del Boletín Oficial del Estado")
    print("=" * 60)
    print()
    
    config = load_config()
    
    data_dir = config.get('data_dir', './boe_data')
    
    db_config = config.get('db_config', {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "boe_monitor",
        "port": 3306
    })
    monitor = BOEMonitor(db_config=db_config, data_dir=data_dir)
    
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
