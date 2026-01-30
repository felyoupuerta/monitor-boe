#!/usr/bin/env python3
"""
BOE Monitor - Analizador del Boletín Oficial del Estado
Monitorea cambios diarios en el BOE y envía notificaciones por correo
Versión Mejorada con Base de Datos
"""

import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
import hashlib
from db_manager import DatabaseManager

class BOEMonitor:
    def __init__(self, db_config, data_dir="./boe_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.base_url = "https://www.boe.es"
        self.db = DatabaseManager(db_config)
        self.db.init_tables()
        
    def get_boe_summary(self, date=None):
        """
        Obtiene el sumario del BOE para una fecha específica
        date: datetime object o None para hoy
        """
        if date is None:
            date = datetime.now()
        
        # Formato de fecha para la URL del BOE: YYYYMMDD
        date_str = date.strftime("%Y%m%d")
        
        # URL del sumario en formato XML (API de datos abiertos)
        url = f"{self.base_url}/datosabiertos/api/boe/sumario/{date_str}"
        
        headers = {
            'Accept': 'application/xml'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Verificar que no sea una redirección a página de error (aunque raise_for_status debería pillar 4xx/5xx, a veces devuelven 200 con HTML)
            if "text/xml" not in response.headers.get('content-type', '') and not response.text.strip().startswith('<?xml'):
                # Intento de fallback o comprobación
                if "<!DOCTYPE html>" in response.text:
                     print(f"⚠️ Alerta: La respuesta para {date_str} parece ser HTML, no XML.")
                     return None

            return {
                'date': date_str,
                'content': response.text,
                'hash': hashlib.md5(response.text.encode()).hexdigest(),
                'date_obj': date
            }
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener BOE para {date_str}: {e}")
            return None
    
    def parse_boe_content(self, xml_content):
        """
        Parsea el contenido XML del BOE y extrae información relevante
        """
        soup = BeautifulSoup(xml_content, 'xml')
        
        items = []
        for item in soup.find_all('item'):
            try:
                items.append({
                    'titulo': item.find('titulo').text if item.find('titulo') else '',
                    'seccion': item.find('seccion').text if item.find('seccion') else '',
                    'departamento': item.find('departamento').text if item.find('departamento') else '',
                    'rango': item.find('rango').text if item.find('rango') else '',
                    'url': item.find('urlPdf').text if item.find('urlPdf') else '',
                })
            except Exception as e:
                continue
        
        return items
    
    def save_day_data(self, items, date_obj):
        """
        Guarda los items del día en la Base de Datos
        """
        count = 0
        for item in items:
            if self.db.save_publication(item, date_obj):
                count += 1
        return count
    
    def load_day_data(self, date_obj):
        """
        Carga datos del BOE desde la Base de Datos
        """
        return self.db.get_publications_by_date(date_obj)
    
    def compare_items(self, today_items, yesterday_items):
        """
        Compara dos listas de items y detecta cambios
        """
        # Crear sets de títulos para comparación
        today_titles = {item['titulo'] or item['titulo'] for item in today_items} # Handle case consistency? assuming raw strings match
        yesterday_titles = {item['titulo'] or item['titulo'] for item in yesterday_items}
        
        # Nuevas publicaciones
        new_items = [item for item in today_items if item['titulo'] not in yesterday_titles]
        
        # Publicaciones eliminadas
        removed_items = [item for item in yesterday_items if item['titulo'] not in today_titles]
        
        return {
            'new_items': new_items,
            'removed_items': removed_items,
            'total_today': len(today_items),
            'total_yesterday': len(yesterday_items),
            'has_changes': len(new_items) > 0 or len(removed_items) > 0
        }
    
    def send_email_notification(self, changes, recipient_email, smtp_config):
        """
        Envía notificación por correo con los cambios detectados
        smtp_config debe contener: server, port, username, password
        """
        if not changes or not changes['has_changes']:
            print("No hay cambios para notificar")
            return False
        
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🔔 Cambios en el BOE - {datetime.now().strftime('%d/%m/%Y')}"
        msg['From'] = smtp_config['username']
        msg['To'] = recipient_email
        
        # Crear contenido HTML
        html_content = self.create_email_html(changes)
        
        # Adjuntar HTML
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        try:
            # Conectar al servidor SMTP
            with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            
            print(f"✅ Notificación enviada a {recipient_email}")
            return True
        except Exception as e:
            print(f"❌ Error al enviar correo: {e}")
            return False
    
    def create_email_html(self, changes):
        """
        Crea el contenido HTML del correo con los cambios
        """
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #003d6a; color: white; padding: 20px; text-align: center; }}
                .summary {{ background-color: #f4f4f4; padding: 15px; margin: 20px 0; border-left: 4px solid #003d6a; }}
                .section {{ margin: 20px 0; }}
                .item {{ background-color: #fff; border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 4px; }}
                .item-title {{ font-weight: bold; color: #003d6a; }}
                .item-meta {{ font-size: 0.9em; color: #666; }}
                .new {{ border-left: 4px solid #28a745; }}
                .removed {{ border-left: 4px solid #dc3545; }}
                a {{ color: #003d6a; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📋 Monitor BOE</h1>
                <p>Cambios detectados el {datetime.now().strftime('%d de %B de %Y')}</p>
            </div>
            
            <div class="summary">
                <h3>📊 Resumen</h3>
                <ul>
                    <li><strong>Nuevas publicaciones:</strong> {len(changes['new_items'])}</li>
                    <li><strong>Publicaciones eliminadas:</strong> {len(changes['removed_items'])}</li>
                    <li><strong>Total hoy:</strong> {changes['total_today']}</li>
                    <li><strong>Total ayer:</strong> {changes['total_yesterday']}</li>
                </ul>
            </div>
        """
        
        # Nuevas publicaciones
        if changes['new_items']:
            html += """
            <div class="section">
                <h2>✨ Nuevas Publicaciones</h2>
            """
            for item in changes['new_items'][:20]:  # Limitar a 20 items
                html += f"""
                <div class="item new">
                    <div class="item-title">{item['titulo']}</div>
                    <div class="item-meta">
                        <strong>Sección:</strong> {item['seccion']} | 
                        <strong>Departamento:</strong> {item['departamento']} | 
                        <strong>Rango:</strong> {item['rango']}
                    </div>
                    {f'<a href="{item["url"]}" target="_blank">📄 Ver PDF</a>' if item['url'] else ''}
                </div>
                """
            html += "</div>"
        
        # Publicaciones eliminadas
        if changes['removed_items']:
            html += """
            <div class="section">
                <h2>🗑️ Publicaciones Eliminadas</h2>
            """
            for item in changes['removed_items'][:10]:  # Limitar a 10 items
                html += f"""
                <div class="item removed">
                    <div class="item-title">{item['titulo']}</div>
                    <div class="item-meta">
                        <strong>Sección:</strong> {item['seccion']} | 
                        <strong>Departamento:</strong> {item['departamento']}
                    </div>
                </div>
                """
            html += "</div>"
        
        html += """
            <div style="text-align: center; margin-top: 30px; padding: 20px; background-color: #f4f4f4;">
                <p>🔗 <a href="https://www.boe.es" target="_blank">Visitar BOE oficial</a></p>
                <p style="font-size: 0.8em; color: #666;">Este es un sistema automatizado de monitoreo del BOE</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def run_daily_check(self, recipient_email, smtp_config):
        """
        Ejecuta el chequeo diario completo
        """
        print(f"🔍 Iniciando monitoreo del BOE con Base de Datos - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Obtener BOE de hoy
        today = datetime.now()
        today_data = self.get_boe_summary(today)
        
        if not today_data:
            print("❌ No se pudo obtener el BOE de hoy")
            self.db.log_execution("error_download", 0, 0, 0, "Failed to download BOE")
            return False
            
        today_items = self.parse_boe_content(today_data['content'])
        
        # Guardar en BD (idempotente)
        saved_count = self.save_day_data(today_items, today)
        print(f"✅ BOE de hoy procesado: {len(today_items)} items ({saved_count} nuevos en BD)")
        
        # Obtener BOE de ayer
        yesterday = today - timedelta(days=1)
        
        # Intentar cargar de BD
        yesterday_items = self.load_day_data(yesterday)
        
        # Si no está en BD, y es la primera vez que corremos esto tras la migración,
        # podríamos intentar descargarlo y guardarlo para tener historial.
        if not yesterday_items:
            print("⏳ No hay datos de ayer en BD. Intentando descargar histórico...")
            yesterday_data = self.get_boe_summary(yesterday)
            if yesterday_data:
                yesterday_items = self.parse_boe_content(yesterday_data['content'])
                self.save_day_data(yesterday_items, yesterday)
                print(f"✅ Histórico recuperado: {len(yesterday_items)} items")
        
        changes = None
        if yesterday_items:
            changes = self.compare_items(today_items, yesterday_items)
            
            self.db.log_execution("success", 
                                  changes['total_today'], 
                                  len(changes['new_items']), 
                                  len(changes['removed_items']), 
                                  "Check completed")

            if changes and changes['has_changes']:
                print(f"📊 Cambios detectados: {len(changes['new_items'])} nuevos, {len(changes['removed_items'])} eliminados")
                # Enviar notificación
                self.send_email_notification(changes, recipient_email, smtp_config)
            else:
                print("ℹ️ No se detectaron cambios significativos")
        else:
            print("⚠️ No hay datos de ayer para comparar (primera ejecución o error en histórico)")
            self.db.log_execution("warning", len(today_items), 0, 0, "No yesterday data")
        
        return True
