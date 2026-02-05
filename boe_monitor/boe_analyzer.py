#!/usr/bin/env python3
"""

PROGRAMA PRINCIPAL PARA EL ANALISIZS Y MONITORIZACIÓN DE BOLETINES OFICIALES

FELIPE ANGERIZ 29-01-2026

"""

import requests
import urllib3
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
import hashlib
from db_manager import DatabaseManager
import unicodedata
import re

class BOEMonitor:
    def __init__(self, db_config, source_config, data_dir="./boe_data"):
        self.source_config = source_config
        self.country_code = source_config.get('country_code', 'es').lower()
        
        # Directorio por país
        self.data_dir = Path(data_dir) / self.country_code
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_url = source_config.get('url', "https://www.boe.es")
        self.db = DatabaseManager(db_config, country_code=self.country_code)
        self.db.init_tables()
        self.session = requests.Session()
        
        #cookie para la sesión
        self.session.cookies.update({'JSESSIONID': 'dummy'})

    def get_boe_summary(self, date=None, retry_count=0, max_retries=3):
        """
        Obtiene el sumario de la fuente configurada.
        """
        if date is None:
            date = datetime.now()
        
        # Diccionario de fechas para el template string
        date_formats = {
            "date_ymd": date.strftime("%Y%m%d"),
            "date": date.strftime("%Y%m%d"), # Alias común
            "date_dmy": date.strftime("%d/%m/%Y"),
            "date_dmy_encoded": date.strftime("%d/%m/%Y").replace("/", "%2F"),
            "date_dmy_dot": date.strftime("%d.%m.%Y"),
            "date_iso": date.strftime("%Y-%m-%d"),
            "day": date.day,
            "month": date.month,
            "year": date.year
        }
        
        # Construir URL
        url_template = self.source_config.get('api_url_template')
        if not url_template:
            # Fallback legacy para BOE España si no está definido
            url = f"{self.base_url}/datosabiertos/api/boe/sumario/{date_formats['date_ymd']}"
        else:
            try:
                url = url_template.format(**date_formats)
            except KeyError as e:
                print(f"Error en template de URL: Falta el placeholder {e}")
                return None
        
        headers = self.source_config.get('headers', {})
        fetch_method = self.source_config.get('fetch_method', 'requests')
        
        print(f"🌍 Consultando ({self.country_code.upper()}) via {fetch_method}: {url}")
        
        try:
            content = None
            
            # Método 1: Selenium
            if fetch_method == 'selenium':
                 try:
                    from selenium import webdriver
                    from selenium.webdriver.chrome.options import Options
                    
                    options = Options()
                    options.add_argument('--headless')
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    if 'User-Agent' in headers:
                        options.add_argument(f'user-agent={headers["User-Agent"]}')
                    
                    driver = webdriver.Chrome(options=options)
                    driver.get(url)
                    time.sleep(self.source_config.get('delay', 3)) # Delay configurable
                    
                    content = driver.page_source
                    driver.quit()
                 except ImportError:
                    print("Selenium no instalado. Instala: pip install selenium")
                    return None
                 except Exception as e:
                    print(f"Error Selenium: {e}")
                    return None
            
            # Método 2: Requests (default)
            else:
                verify_ssl = self.source_config.get('verify_ssl', True)
                if not verify_ssl:
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                # Special Case for Kuwait (requests)
                if self.country_code == 'kw':
                    response = self.session.get(url, headers=headers, timeout=30, verify=verify_ssl)
                    if response.status_code == 200:
                        # Extract ID
                        match = re.search(r"data\.EditionID_FK\s*=\s*'(\d+)'", response.text)
                        if match:
                            edition_id = match.group(1)
                            print(f"   Kuwait Edition ID: {edition_id}")
                            
                            api_url = "https://kuwaitalyawm.media.gov.kw/online/AdsMainEditionJson"
                            payload = {
                                "draw": "1",
                                "start": "0", # Fetch all (first page large enough)
                                "length": "500",
                                "EditionID_FK": edition_id,
                                "AdsTitle": "", "Agents": "", "AdsCategories": "",
                                "search[value]": "", "search[regex]": "false",
                                "order[0][column]": "1", "order[0][dir]": "desc",
                                # Required columns defs to avoid 500 error
                                "columns[0][data]": "AdsTitle", "columns[0][name]": "", "columns[0][searchable]": "true", "columns[0][orderable]": "true", "columns[0][search][value]": "", "columns[0][search][regex]": "false",
                                "columns[1][data]": "ID", "columns[1][name]": "", "columns[1][searchable]": "true", "columns[1][orderable]": "true", "columns[1][search][value]": "", "columns[1][search][regex]": "false",
                                "columns[2][data]": "AgentTitle", "columns[2][name]": "", "columns[2][searchable]": "true", "columns[2][orderable]": "true", "columns[2][search][value]": "", "columns[2][search][regex]": "false",
                                "columns[3][data]": "AdsCategoryTitle", "columns[3][name]": "", "columns[3][searchable]": "true", "columns[3][orderable]": "true", "columns[3][search][value]": "", "columns[3][search][regex]": "false"
                            }
                            
                            headers_api = headers.copy()
                            headers_api['X-Requested-With'] = 'XMLHttpRequest'
                            
                            api_resp = self.session.post(api_url, data=payload, headers=headers_api, verify=verify_ssl)
                            if api_resp.status_code == 200:
                                try:
                                    json_data = api_resp.json()
                                    items = json_data.get('data', [])
                                    
                                    html_parts = []
                                    for item in items:
                                        item_url = f"/flip?id={item.get('EditionID_FK')}&no={item.get('FromPage')}"
                                        title = item.get('AdsTitle', 'No Title')
                                        agent = item.get('AgentTitle', '')
                                        cat = item.get('AdsCategoryTitle', '')
                                        
                                        html_parts.append(f'''
                                        <div class="breifdiv">
                                            <a data-load-url="{item_url}">{title}</a>
                                            <span class="category">{cat}</span>
                                            <span class="agent">{agent}</span>
                                        </div>
                                        ''')
                                    content = "<html><body>" + "".join(html_parts) + "</body></html>"
                                except ValueError:
                                    print("Error parsing Kuwait API JSON")
                                    content = None
                            else:
                                print(f"Error calling Kuwait API: {api_resp.status_code}")
                                content = None
                        else:
                            print("Could not find EditionID_FK in Kuwait page")
                            content = None
                    else:
                        print(f"Error fetching Kuwait main page: {response.status_code}")
                        content = None
                
                else:
                    # Generic requests
                    response = self.session.get(url, headers=headers, timeout=30, verify=verify_ssl)
                    if response.status_code == 200:
                        content = response.text
                    elif response.status_code == 403:
                         # Reintento simple
                         time.sleep(2)
                         response = self.session.get(url, headers=headers, timeout=30, verify=verify_ssl)
                         if response.status_code == 200:
                             content = response.text
                
                if not content:
                    # If we fell through or failed
                    if not (self.country_code == 'kw' and response.status_code == 200): # Avoid double printing if handled above
                         print(f"Error HTTP {response.status_code}")
                    return None

            if content:
                 return {
                    'date': date_formats['date_ymd'],
                    'content': content,
                    'hash': hashlib.md5(content.encode('utf-8')).hexdigest(),
                    'date_obj': date
                }
            return None

        except Exception as e:
            print(f"Error general obteniendo datos: {e}")
            return None

    def parse_boe_content(self, content):
        """
        Parser genérico basado en reglas del config.json
        """
        rules = self.source_config.get('parser_rules')
        if not rules:
            print("No se encontraron reglas de parsers en config.json")
            return []
            
        items = []
        try:
            engine = rules.get('engine', 'html.parser')
            # Fix para lxml vs html.parser si es xml
            if engine == 'xml' and 'xml' not in content[:50].lower():
                 # A veces se define xml pero llega html, manejo básico
                 pass

            soup = BeautifulSoup(content, engine)
            
            container_selector = rules.get('container')
            if not container_selector:
                return []
            
            # Seleccionar contenedores (items)
            containers = soup.select(container_selector)
            print(f"   Encontrados {len(containers)} elementos.")
            
            fields = rules.get('fields', {})
            
            for container in containers:
                item = {}
                try:
                    for field_name, field_rule in fields.items():
                        value = field_rule.get('default', '')
                        
                        selector = field_rule.get('selector')
                        if selector:
                            # Buscar elemento
                            element = container.select_one(selector)
                            if element:
                                extract_type = field_rule.get('type', 'text')
                                if extract_type == 'text':
                                    value = element.get_text(" ", strip=True)
                                elif extract_type == 'attr':
                                    attr_name = field_rule.get('attr')
                                    value = element.get(attr_name, '')
                        
                        # Post-procesado especifico para URL relative
                        if field_name == 'url' and value and not value.startswith('http'):
                            base_url = self.source_config.get('url', '')
                            # Limpieza de slash duplicado
                            if base_url.endswith('/') and value.startswith('/'):
                                value = base_url + value[1:]
                            elif not base_url.endswith('/') and not value.startswith('/'):
                                value = base_url + '/' + value
                            else:
                                value = base_url + value
                                
                        item[field_name] = value
                    
                    # Validar integridad mínima:
                    if item.get('titulo'):
                        items.append(item)
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error en parser genérico: {e}")
        
        return items

    
    def save_day_data(self, items, date_obj):

        new_items = []
        for item in items:
            if self.db.save_publication(item, date_obj):
                new_items.append(item)
        return new_items
    
    def load_day_data(self, date_obj):
        return self.db.get_publications_by_date(date_obj)
    
    def compare_items(self, today_items, yesterday_items):
        def _normalize_title(t):
            if not t:
                return ''
            try:
                s = unicodedata.normalize('NFKC', str(t))
                s = ' '.join(s.split())
                return s.strip().lower()
            except Exception:
                return str(t).strip().lower()

        today_titles = {_normalize_title(item.get('titulo', '')) for item in today_items}
        yesterday_titles = {_normalize_title(item.get('titulo', '')) for item in yesterday_items}

        new_items = [item for item in today_items if _normalize_title(item.get('titulo', '')) not in yesterday_titles]

        removed_items = [item for item in yesterday_items if _normalize_title(item.get('titulo', '')) not in today_titles]
        
        return {
            'new_items': new_items,
            'removed_items': removed_items,
            'total_today': len(today_items),
            'total_yesterday': len(yesterday_items),
            'has_changes': len(new_items) > 0 or len(removed_items) > 0
        }
    
    def send_email_notification(self, items, recipient_email, smtp_config, has_changes=True):
        msg = MIMEMultipart('alternative')
        country_name = self.source_config.get('name', self.country_code.upper())
        
        if has_changes:
            msg['Subject'] = f"🔔 Novedades en {country_name} - {datetime.now().strftime('%d/%m/%Y')}"
        else:
            msg['Subject'] = f"📋 Estado de {country_name} - {datetime.now().strftime('%d/%m/%Y')}"
            
        msg['From'] = smtp_config['username']
        if isinstance(recipient_email, list):
            recipients_str = ", ".join(recipient_email)
        else:
            recipients_str = recipient_email
            
        msg['To'] = recipients_str
        
        html_content = self.create_email_html(items, has_changes)
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        try:
            with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            
            print(f"Notificación enviada a {recipients_str}")
            return True
        except Exception as e:
            print(f"Error al enviar correo: {e}")
            return False
    
    def create_email_html(self, items, has_changes=True):
        """
        HTML pal correo
        """
        date_str = datetime.now().strftime('%d de %B de %Y')
        country_name = self.source_config.get('name', self.country_code.upper())
        
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
                <h1>📋 Monitor {country_name}</h1>
                <p>Fecha: {date_str}</p>
            </div>
        """
        
        if not has_changes:
            html += f"""
            <div class="summary" style="border-left: 4px solid #666;">
                <h3>ℹ️ Sin novedades</h3>
                <p>El dia de hoy no hemos detectado novedades en {country_name}.</p>
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
            for item in items[:50]:
                html += f"""
                <div class="item new">
                    <div class="item-title">{item['titulo']}</div>
                    <div class="item-meta">
                        <strong>Sección:</strong> {item.get('seccion', '-')} | 
                        <strong>Departamento:</strong> {item.get('departamento', '-')} | 
                        <strong>Rango:</strong> {item.get('rango', '-')}
                    </div>
                    {f'<a href="{item["url"]}" target="_blank">📄 Ver PDF</a>' if item.get('url') else ''}
                </div>
                """
            html += "</div>"
        
        html += """
            <div style="text-align: center; margin-top: 30px; padding: 20px; background-color: #f4f4f4;">
                <p style="font-size: 0.8em; color: #666;">Sistema automatizado de monitoreo</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def run_daily_check(self, recipient_email, smtp_config):

        country_name = self.source_config.get('name', self.country_code)
        print(f"🔍 Iniciando monitoreo de {country_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        today = datetime.now()
        today_data = self.get_boe_summary(today)
        
        if not today_data:
            print("No se pudieron obtener datos hoy")
            self.db.log_execution("error_download", 0, 0, 0, "Failed to download data")
            return False
        
        today_items = self.parse_boe_content(today_data['content'])
        print(f"Total de items obtenidos: {len(today_items)}")
        
        if not today_items:
            print("No se encontraron items para procesar")
            self.db.log_execution("no_items", 0, 0, 0, "No items found in content")
            return False
        
        # Cargar datos previos de la BD
        yesterday = today - timedelta(days=1)
        yesterday_items = self.load_day_data(yesterday.date())
        print(f"Items del día anterior en BD: {len(yesterday_items)}")

        
        used_baseline = 'yesterday'
        if not yesterday_items:
            today_saved = self.load_day_data(today.date())
            if today_saved:
                yesterday_items = today_saved
                used_baseline = 'today_saved'

        print(f"📚 Usando baseline para comparación: {used_baseline} (items={len(yesterday_items)})")

        # Comparar items
        comparison = self.compare_items(today_items, yesterday_items)
        new_items = comparison['new_items']
        removed_items = comparison['removed_items']
        
        print(f"Procesado: {len(today_items)} items totales.")
        print(f"   Nuevos: {len(new_items)}")
        print(f"   Eliminados: {len(removed_items)}")
        
        #Guardar itemas nuevos en BD
        saved_items = []
        for item in today_items:
            if self.db.save_publication(item, today.date()):
                saved_items.append(item)

        print(f"💾 Guardados en BD: {len(saved_items)} items nuevos")

        
        status = "success" if saved_items else "no_changes"
        self.db.log_execution(status, len(today_items), len(saved_items), len(removed_items), "Check completed")

        # Enviar correo nada nuevo o cosas nuevas
        if saved_items:
            print(f"📊 Novedades detectadas: {len(saved_items)} items. Enviando correo...")
            self.send_email_notification(saved_items, recipient_email, smtp_config, has_changes=True)
        else:
            print("ℹ️ Sin novedades (no se guardaron items nuevos). Enviando confirmación...")
            self.send_email_notification([], recipient_email, smtp_config, has_changes=False)
        
        return True
