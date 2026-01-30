#!/usr/bin/env python3
"""
Script de migración de datos JSON a MariaDB
"""

import json
import glob
from pathlib import Path
from datetime import datetime
from db_manager import DatabaseManager
from boe_analyzer import BOEMonitor

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def migrate():
    print("🚀 Iniciando migración de JSON a Base de Datos...")
    
    config = load_config()
    db_config = config.get('db_config')
    
    if not db_config:
        print("❌ Configuración de BD no encontrada en config.json")
        return

    db = DatabaseManager(db_config)
    if not db.init_tables():
        print("❌ Error al inicializar tablas")
        return

    # Buscar archivos JSON
    data_dir = Path(config.get('data_dir', './boe_data'))
    json_files = sorted(list(data_dir.glob('boe_*.json')))
    
    print(f"📂 Encontrados {len(json_files)} archivos JSON para migrar.")
    
    total_imported = 0
    
    # Instanciamos BOEMonitor solo para usar parse_boe_content si fuera necesario, 
    # pero los JSON ya tienen la estructura parseada?
    # Espera, save_boe_data guardaba el objeto COMPLETO devuelto por get_boe_summary
    # que incluía 'content' (XML) y 'date'.
    # Entonces los JSONs contienen XML en brudo.
    
    monitor = BOEMonitor(db_config, data_dir=data_dir)
    
    for json_file in json_files:
        try:
            print(f"📄 Procesando {json_file.name}...")
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            date_str = data.get('date')
            if not date_str:
                print(f"⚠️  Saltando {json_file.name}: Sin fecha")
                continue
                
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            xml_content = data.get('content')
            
            if not xml_content:
                print(f"⚠️  Saltando {json_file.name}: Sin contenido XML")
                continue
                
            # Parsear contenido
            items = monitor.parse_boe_content(xml_content)
            
            # Guardar en BD
            count = monitor.save_day_data(items, date_obj)
            print(f"   ✅ Importados {count} registros del {date_str}")
            total_imported += count
            
        except Exception as e:
            print(f"❌ Error al procesar {json_file.name}: {e}")
            
    print(f"\n✨ Migración completada! Total registros importados: {total_imported}")

if __name__ == "__main__":
    migrate()
