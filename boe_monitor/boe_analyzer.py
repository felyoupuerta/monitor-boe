#!/usr/bin/env python3
"""
BOE Monitor - Analizador del Boletín Oficial del Estado
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
        
        date_str = date.strftime("%Y%m%d")
        
        url = f"{self.base_url}/datosabiertos/api/boe/sumario/{date_str}"
        
        headers = {
            'Accept': 'application/xml'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            if "text/xml" not in response.headers.get('content-type', '') and not response.text.strip().startswith('<?xml'):
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
        Retorna la lista de items nuevos guardados
        """
        new_items = []
        for item in items:
            if self.db.save_publication(item, date_obj):
                new_items.append(item)
        return new_items
    
    def load_day_data(self, date_obj):
        """
        Carga datos del BOE desde la Base de Datos
        """
        return self.db.get_publications_by_date(date_obj)
    
    def compare_items(self, today_items, yesterday_items):
        """
        Compara dos listas de items y detecta cambios
        """
        today_titles = {item['titulo'] or item['titulo'] for item in today_items}
        yesterday_titles = {item['titulo'] or item['titulo'] for item in yesterday_items}
        
        new_items = [item for item in today_items if item['titulo'] not in yesterday_titles]
        
        removed_items = [item for item in yesterday_items if item['titulo'] not in today_titles]
        
        return {
            'new_items': new_items,
            'removed_items': removed_items,
            'total_today': len(today_items),
            'total_yesterday': len(yesterday_items),
            'has_changes': len(new_items) > 0 or len(removed_items) > 0
        }
    
    def send_email_notification(self, items, recipient_email, smtp_config, has_changes=True):
        """
        Envía notificación por correo con los cambios detectados o mensaje de sin cambios.
        items: Lista de items nuevos (si has_changes=True) o vacía.
        """
        
        msg = MIMEMultipart('alternative')
        
        if has_changes:
            msg['Subject'] = f"🔔 Novedades en el BOE - {datetime.now().strftime('%d/%m/%Y')}"
        else:
            msg['Subject'] = f"📋 Estado del BOE - {datetime.now().strftime('%d/%m/%Y')}"
            
        msg['From'] = smtp_config['username']
        msg['To'] = recipient_email
        
        html_content = self.create_email_html(items, has_changes)
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        try:
            with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            
            print(f"✅ Notificación enviada a {recipient_email}")
            return True
        except Exception as e:
            print(f"❌ Error al enviar correo: {e}")
            return False
    
    def create_email_html(self, items, has_changes=True):
        """
        Crea el contenido HTML del correo
        """
        date_str = datetime.now().strftime('%d de %B de %Y')
        
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
                a {{ color: #003d6a; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📋 Monitor BOE</h1>
                <p>Fecha: {date_str}</p>
            </div>
        """
        
        if not has_changes:
            html += """
            <div class="summary" style="border-left: 4px solid #666;">
                <h3>ℹ️ Sin novedades</h3>
                <p>El dia de hoy no hemos detectado novedades en el BOE Español.</p>
            </div>
            """
        else:
            html += f"""
            <div class="summary">
                <h3>📊 Resumen de Novedades</h3>
                <p>Se han detectado <strong>{len(items)}</strong> nuevas publicaciones desde la última comprobación.</p>
            </div>
            
            <div class="section">
                <h2>✨ Nuevas Publicaciones</h2>
            """
            for item in items[:50]:  # Limitar a 50 items para no saturar el correo
                html += f"""
                <div class="item new">
                    <div class="item-title">{item['titulo']}</div>
                    <div class="item-meta">
                        <strong>Sección:</strong> {item['seccion']} | 
                        <strong>Departamento:</strong> {item['departamento']} | 
                        <strong>Rango:</strong> {item['rango']}
                    </div>
                    {f'<a href="{item["url"]}" target="_blank">📄 Ver PDF</a>' if item.get('url') else ''}
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
        Ejecuta el chequeo diario:
        1. Descarga datos del BOE
        2. Intenta guardar en BD
        3. Si hay nuevos items -> Envía correo con cambios
        4. Si no hay nuevos -> Envía correo indicando que no hay novedades
        """
        print(f"🔍 Iniciando monitoreo del BOE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        today = datetime.now()
        today_data = self.get_boe_summary(today)
        
        if not today_data:
            print("❌ No se pudo obtener el BOE de hoy")
            self.db.log_execution("error_download", 0, 0, 0, "Failed to download BOE")
            return False
            
        today_items = self.parse_boe_content(today_data['content'])
        
        new_items = self.save_day_data(today_items, today.date())
        
        print(f"✅ BOE procesado: {len(today_items)} items totales. {len(new_items)} nuevos detectados.")
        
        status = "success" if new_items else "no_changes"
        self.db.log_execution(status, len(today_items), len(new_items), 0, "Check completed")

        if new_items:
            print(f"📊 Novedades detectadas: {len(new_items)} items. Enviando correo...")
            self.send_email_notification(new_items, recipient_email, smtp_config, has_changes=True)
        else:
            print("ℹ️ No se detectaron novedades. Enviando correo de confirmación...")
            self.send_email_notification([], recipient_email, smtp_config, has_changes=False)
        
        return True
