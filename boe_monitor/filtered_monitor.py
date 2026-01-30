#!/usr/bin/env python3
"""
Extensión del BOE Monitor con filtrado por palabras clave
Útil si solo te interesan ciertos temas específicos
"""

from boe_analyzer import BOEMonitor
import json

class FilteredBOEMonitor(BOEMonitor):
    """
    Monitor del BOE con capacidad de filtrar por palabras clave
    """
    
    def __init__(self, data_dir="./boe_data", keywords=None):
        super().__init__(data_dir)
        # Lista de palabras clave para filtrar (minúsculas)
        self.keywords = [k.lower() for k in (keywords or [])]
    
    def filter_items_by_keywords(self, items):
        """
        Filtra publicaciones que contengan alguna de las palabras clave
        """
        if not self.keywords:
            return items  # Si no hay keywords, devolver todo
        
        filtered = []
        for item in items:
            # Combinar todos los campos de texto
            text = " ".join([
                item.get('titulo', ''),
                item.get('seccion', ''),
                item.get('departamento', ''),
                item.get('rango', '')
            ]).lower()
            
            # Verificar si contiene alguna palabra clave
            if any(keyword in text for keyword in self.keywords):
                filtered.append(item)
        
        return filtered
    
    def compare_boe_days(self, today_data, yesterday_data):
        """
        Sobrescribe el método de comparación para incluir filtrado
        """
        changes = super().compare_boe_days(today_data, yesterday_data)
        
        if not changes or not self.keywords:
            return changes
        
        # Aplicar filtro a los items nuevos
        changes['new_items'] = self.filter_items_by_keywords(changes['new_items'])
        changes['removed_items'] = self.filter_items_by_keywords(changes['removed_items'])
        
        # Actualizar flag de cambios
        changes['has_changes'] = len(changes['new_items']) > 0 or len(changes['removed_items']) > 0
        changes['filtered'] = True
        changes['keywords'] = self.keywords
        
        return changes
    
    def create_email_html(self, changes):
        """
        Sobrescribe el método de creación de email para incluir info de filtros
        """
        html = super().create_email_html(changes)
        
        # Si hay filtros activos, añadir información
        if changes.get('filtered'):
            filter_info = f"""
            <div style="background-color: #fff3cd; padding: 15px; margin: 20px 0; border-left: 4px solid #ffc107; border-radius: 4px;">
                <h3>🔍 Filtros activos</h3>
                <p>Solo se muestran publicaciones que contengan estas palabras clave:</p>
                <p><strong>{', '.join(changes['keywords'])}</strong></p>
            </div>
            """
            # Insertar después del header
            html = html.replace('<div class="summary">', filter_info + '<div class="summary">')
        
        return html


# Ejemplo de uso con filtros
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Cargar configuración
    config_path = Path('config.json')
    if not config_path.exists():
        print("❌ Error: No se encuentra config.json")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # CONFIGURACIÓN DE PALABRAS CLAVE
    # Añade aquí las palabras o temas que te interesan
    keywords = [
        'inteligencia artificial',
        'tecnología',
        'subvención',
        'ayuda',
        'convocatoria',
        # Añade más palabras clave aquí
    ]
    
    print("=" * 60)
    print("  📋 BOE MONITOR FILTRADO")
    print("=" * 60)
    print(f"\n🔍 Filtrando por palabras clave: {', '.join(keywords)}\n")
    
    # Crear monitor con filtros
    monitor = FilteredBOEMonitor(
        data_dir=config.get('data_dir', './boe_data'),
        keywords=keywords
    )
    
    # Ejecutar
    monitor.run_daily_check(
        recipient_email=config['recipient_email'],
        smtp_config=config['smtp_config']
    )
