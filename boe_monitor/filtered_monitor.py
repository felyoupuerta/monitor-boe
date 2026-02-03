#!/usr/bin/env python3
from boe_analyzer import BOEMonitor
import json

class FilteredBOEMonitor(BOEMonitor):
    def __init__(self, data_dir="./boe_data", keywords=None):
        super().__init__(data_dir)
        self.keywords = [k.lower() for k in (keywords or [])]
    
    def filter_items_by_keywords(self, items):
        if not self.keywords:
            return items
        
        filtered = []
        for item in items:
            text = " ".join([
                item.get('titulo', ''),
                item.get('seccion', ''),
                item.get('departamento', ''),
                item.get('rango', '')
            ]).lower()
            
            if any(keyword in text for keyword in self.keywords):
                filtered.append(item)
        
        return filtered
    
    def compare_boe_days(self, today_data, yesterday_data):
        changes = super().compare_boe_days(today_data, yesterday_data)
        
        if not changes or not self.keywords:
            return changes
        
        changes['new_items'] = self.filter_items_by_keywords(changes['new_items'])
        changes['removed_items'] = self.filter_items_by_keywords(changes['removed_items'])
        
        changes['has_changes'] = len(changes['new_items']) > 0 or len(changes['removed_items']) > 0
        changes['filtered'] = True
        changes['keywords'] = self.keywords
        
        return changes
    
    def create_email_html(self, changes):
        html = super().create_email_html(changes)
        
        if changes.get('filtered'):
            filter_info = f"""
            <div style="background-color: #fff3cd; padding: 15px; margin: 20px 0; border-left: 4px solid #ffc107; border-radius: 4px;">
                <h3> Filtros activos</h3>
                <p>Solo se muestran publicaciones que contengan estas palabras clave:</p>
                <p><strong>{', '.join(changes['keywords'])}</strong></p>
            </div>
            """
            html = html.replace('<div class="summary">', filter_info + '<div class="summary">')
        
        return html



if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    
    config_path = Path('config.json')
    if not config_path.exists():
        print("❌ Error: No se encuentra config.json")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    #CONFIG DE PALABRAS CLAVE
    keywords = [
        'inteligencia artificial',
        'tecnología',
        'subvención',
        'ayuda',
        'convocatoria',
    ]
    
    print("=" * 60)
    print("BOE MONITOR FILTRADO")
    print("=" * 60)
    print(f"\nFiltrando por palabras clave: {', '.join(keywords)}\n")
    
    monitor = FilteredBOEMonitor(
        data_dir=config.get('data_dir', './boe_data'),
        keywords=keywords
    )
    
    # Ejecutar
    monitor.run_daily_check(
        recipient_email=config['recipient_email'],
        smtp_config=config['smtp_config']
    )
