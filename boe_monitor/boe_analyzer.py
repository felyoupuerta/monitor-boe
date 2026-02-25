#!/usr/bin/env python3
import requests
import json
import os
import time
import logging
import hashlib
import smtplib
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup

# Manejo de imports opcionales
try:
    from fake_useragent import UserAgent
    HAS_USERAGENT = True
except ImportError:
    HAS_USERAGENT = False

from db_manager import DatabaseManager

class BOEMonitor:
    def __init__(self, db_config, source_config, data_dir="./boe_data"):
        self.logger = logging.getLogger(__name__)
        self.source_config = source_config
        self.country_code = source_config.get('country_code', 'es').lower()
        
        # Configuración de directorios
        self.data_dir = Path(data_dir) / self.country_code
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_url = source_config.get('url', "https://www.boe.es")
        
        # Inicializar BD
        self.db = DatabaseManager(db_config, country_code=self.country_code)
        self.db.init_tables()
        
        # Sesión HTTP persistente
        self.session = requests.Session()
        self.session.cookies.update({'JSESSIONID': 'dummy'})
        
        # User Agent Rotator
        self.ua = UserAgent() if HAS_USERAGENT else None

    def _get_headers(self):
        """Genera headers dinámicos para evitar bloqueos"""
        headers = self.source_config.get('headers', {}).copy()
        if self.ua and 'User-Agent' not in headers:
            headers['User-Agent'] = self.ua.random
        return headers

    def get_boe_summary(self, date=None):
        """Obtiene el sumario de la fuente configurada"""
        if date is None:
            date = datetime.now()
        
        # Formatos de fecha disponibles para las URLs
        date_formats = {
            "date_ymd": date.strftime("%Y%m%d"),
            "date": date.strftime("%Y%m%d"),
            "date_dmy": date.strftime("%d/%m/%Y"),
            "date_dmy_encoded": date.strftime("%d/%m/%Y").replace("/", "%2F"),
            "date_dmy_dot": date.strftime("%d.%m.%Y"),
            "date_iso": date.strftime("%Y-%m-%d"),
            "day": date.day,
            "month": date.month,
            "year": date.year
        }
        
        # Construcción de URL
        url_template = self.source_config.get('api_url_template')
        if not url_template:
            url = f"{self.base_url}/datosabiertos/api/boe/sumario/{date_formats['date_ymd']}"
        else:
            try:
                url = url_template.format(**date_formats)
            except KeyError as e:
                self.logger.error(f"Error en template URL: Falta placeholder {e}")
                return None
        
        fetch_method = self.source_config.get('fetch_method', 'requests')
        self.logger.info(f"🌍 Consultando ({self.country_code.upper()}) via {fetch_method}: {url}")
        
        try:
            content = None
            headers = self._get_headers()
            
            # --- MÉTODO SELENIUM ---
            if fetch_method == 'selenium':
                 try:
                    from selenium import webdriver
                    from selenium.webdriver.chrome.options import Options
                    from selenium.webdriver.chrome.service import Service
                    
                    options = Options()
                    options.add_argument('--headless')
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    options.add_argument(f"user-agent={headers.get('User-Agent', 'Mozilla/5.0')}")
                    
                    # Usar context manager para asegurar el cierre del driver
                    driver = webdriver.Chrome(options=options)
                    try:
                        driver.get(url)
                        delay = self.source_config.get('delay', 3)
                        time.sleep(delay)
                        content = driver.page_source
                    finally:
                        driver.quit()
                        
                 except ImportError:
                    self.logger.error("Selenium no instalado. Instala: pip install selenium")
                    return None
                 except Exception as e:
                    self.logger.error(f"Error crítico Selenium: {e}")
                    return None
            
            # --- MÉTODO REQUESTS (DEFAULT) ---
            else:
                response = self.session.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    content = response.text
                elif response.status_code in [403, 429, 500]:
                     self.logger.warning(f"Status {response.status_code}. Reintentando...")
                     time.sleep(5)
                     response = self.session.get(url, headers=headers, timeout=30)
                     if response.status_code == 200:
                         content = response.text
                
                if not content:
                    self.logger.error(f"Error HTTP {response.status_code} al obtener datos")
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
            self.logger.exception(f"Excepción general obteniendo datos: {e}")
            return None

    def parse_boe_content(self, content):
        """Parser genérico basado en reglas"""
        rules = self.source_config.get('parser_rules')
        if not rules:
            self.logger.warning("No se encontraron reglas de parser en config.json")
            return []
            
        items = []
        try:
            engine = rules.get('engine', 'html.parser')
            # Fallback seguro para xml
            if engine == 'xml' and 'xml' not in content[:100].lower() and '<html' in content[:100].lower():
                 engine = 'html.parser'

            soup = BeautifulSoup(content, engine)
            container_selector = rules.get('container')
            
            if not container_selector:
                return []
            
            containers = soup.select(container_selector)
            self.logger.info(f"Encontrados {len(containers)} elementos crudos.")
            
            fields = rules.get('fields', {})
            
            for container in containers:
                item = {}
                try:
                    for field_name, field_rule in fields.items():
                        value = field_rule.get('default', '')
                        selector = field_rule.get('selector')
                        
                        if selector:
                            element = container.select_one(selector)
                            if element:
                                extract_type = field_rule.get('type', 'text')
                                if extract_type == 'text':
                                    value = element.get_text(" ", strip=True)
                                elif extract_type == 'attr':
                                    attr_name = field_rule.get('attr')
                                    value = element.get(attr_name, '')
                        
                        # Normalización de URL relativa
                        if field_name == 'url' and value and not value.startswith(('http', 'https')):
                            base_url_clean = self.source_config.get('url', '').rstrip('/')
                            if value.startswith('/'):
                                value = f"{base_url_clean}{value}"
                            else:
                                value = f"{base_url_clean}/{value}"
                                
                        item[field_name] = value
                    
                    if item.get('titulo'):
                        items.append(item)
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error en parser: {e}")
        
        return items

    def load_day_data(self, date_obj):
        return self.db.get_publications_by_date(date_obj)
    
    def compare_items(self, today_items, yesterday_items):
        """Compara items normalizando títulos para evitar falsos positivos por tildes/espacios"""
        def _normalize_title(t):
            if not t: return ''
            try:
                # Normalización Unicode estricta (NFKC) y lowercase
                s = unicodedata.normalize('NFKC', str(t))
                return " ".join(s.split()).strip().lower()
            except Exception:
                return str(t).strip().lower()

        # Crear sets de hashes/títulos normalizados para comparación rápida
        today_titles = {_normalize_title(item.get('titulo', '')) for item in today_items}
        yesterday_titles = {_normalize_title(item.get('titulo', '')) for item in yesterday_items}

        new_items = [item for item in today_items if _normalize_title(item.get('titulo', '')) not in yesterday_titles]
        removed_items = [item for item in yesterday_items if _normalize_title(item.get('titulo', '')) not in today_titles]
        
        return {
            'new_items': new_items,
            'removed_items': removed_items,
            'total_today': len(today_items),
            'total_yesterday': len(yesterday_items),
            'has_changes': bool(new_items or removed_items)
        }
    
    def send_email_notification(self, items, recipient_email, smtp_config, has_changes=True):
        msg = MIMEMultipart('alternative')
        country_name = self.source_config.get('name', self.country_code.upper())
        
        date_str = datetime.now().strftime('%d/%m/%Y')
        if has_changes:
            msg['Subject'] = f"🔔 Novedades en {country_name} - {date_str}"
        else:
            msg['Subject'] = f"📋 Estado de {country_name} - {date_str}"
            
        msg['From'] = smtp_config['username']
        
        if isinstance(recipient_email, list):
            msg['To'] = ", ".join(recipient_email)
        else:
            msg['To'] = recipient_email
            
        html_content = self.create_email_html(items, has_changes)
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        try:
            with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            
            self.logger.info(f"✉️ Notificación enviada a {msg['To']}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error enviando correo: {e}")
            return False
    
    def create_email_html(self, items, has_changes=True):
        date_str = datetime.now().strftime('%d de %B de %Y')
        country_name = self.source_config.get('name', self.country_code.upper())
        country_url = self.source_config.get('url', '#')
        # Estilos inline para compatibilidad con clientes de correo
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; }}
                .header {{ background-color: #004d99; color: white; padding: 20px; text-align: center; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-left: 5px solid #004d99; margin: 20px 0; }}
                .item {{ background-color: #fff; border: 1px solid #e1e4e8; padding: 15px; margin-bottom: 10px; border-radius: 4px; }}
                .new {{ border-left: 5px solid #28a745; }}
                .title {{ color: #004d99; font-weight: bold; font-size: 1.1em; }}
                .meta {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
                a.button {{ background-color: #004d99; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 0.8em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Monitor {country_name}</h1>
                <h2>{country_url}, {date_str}</h2>
                <p>{date_str}</p>
            </div>
        """
        
        if not has_changes:
            html += f"""
            <div class="summary" style="border-left-color: #6c757d;">
                <h3>✅ Sin novedades</h3>
                <p>No se han detectado nuevas publicaciones hoy.</p>
            </div>"""
        else:
            html += f"""
            <div class="summary">
                <h3>📊 Resumen</h3>
                <p>Se han detectado <strong>{len(items)}</strong> nuevas publicaciones.</p>
            </div>
            <h3>✨ Nuevas Publicaciones</h3>
            """
            # Limitar a 50 items para no saturar el correo
            for item in items[:50]:
                url_html = f'<br><br><a href="{item["url"]}" class="button">📄 Ver Documento</a>' if item.get('url') else ''
                html += f"""
                <div class="item new">
                    <div class="title">{item['titulo']}</div>
                    <div class="meta">
                        📂 {item.get('seccion', 'General')} | 
                        🏢 {item.get('departamento', '-')}
                        {url_html}
                    </div>
                </div>
                """
                
        html += """
            <div style="text-align: center; margin-top: 30px; font-size: 0.8em; color: #999;">
                Monitor BOES - {country_name} | {date_str} | Fuente: <a href="{country_url}">{country_url}</a> | Desarrollado por Felipe Angeriz para Anook
            </div>
        </body></html>
        """
        return html
    
    def run(self, recipient_email, smtp_config, check_date=None):
        """
        Ejecuta el análisis para una fecha específica o el día actual.
        Diseñado para ejecución manual o automatizada vía crontab.
        """
        country_name = self.source_config.get('name', self.country_code)
        
        # Determinar fecha de ejecución
        run_date = check_date if check_date else datetime.now()
        if isinstance(run_date, str):
            try:
                run_date = datetime.strptime(run_date, "%Y-%m-%d")
            except ValueError:
                self.logger.error(f"Formato de fecha inválido: {run_date}. Use YYYY-MM-DD")
                return False

        self.logger.info(f"Iniciando análisis para {country_name} - Fecha: {run_date.strftime('%Y-%m-%d')}")
        
        # 1. Obtener sumario
        today_data = self.get_boe_summary(run_date)
        
        if not today_data:
            self.logger.error(f"No se pudieron obtener datos para la fecha {run_date.strftime('%Y-%m-%d')}")
            self.db.log_execution("error_download", 0, 0, 0, f"Failed to download data for {run_date.date()}")
            return False
        
        # 2. Parsear contenido
        today_items = self.parse_boe_content(today_data['content'])
        self.logger.info(f"Items detectados en la fuente: {len(today_items)}")
        
        if not today_items:
            self.logger.warning("No se encontraron items para procesar")
            self.db.log_execution("no_items", 0, 0, 0, "No items found in content")
            return False
        
        # 3. Guardar en Base de Datos (solo los que no existan)
        # La función save_publication ya maneja la verificación de duplicados
        saved_count = 0
        new_items = []
        
        for item in today_items:
            if self.db.save_publication(item, run_date.date()):
                saved_count += 1
                new_items.append(item)
        
        self.logger.info(f"Registros nuevos guardados en BD: {saved_count}")
        
        # 4. Registrar ejecución
        status = "success" if saved_count > 0 else "no_changes"
        message = f"Check completed for {run_date.date()}. Found {len(today_items)}, saved {saved_count} new."
        self.db.log_execution(status, len(today_items), saved_count, 0, message)
        
        # 5. Notificar si hay novedades
        if saved_count > 0:
            self.logger.info(f"Enviando notificación por {saved_count} nuevos items...")
            self.send_email_notification(new_items, recipient_email, smtp_config, has_changes=True)
        else:
            # Opcional: Notificar aunque no haya cambios (según config)
            should_notify = self.source_config.get('notify_no_changes', False)
            if should_notify:
                self.send_email_notification([], recipient_email, smtp_config, has_changes=False)
            else:
                self.logger.info("Sin novedades detectadas. No se envía correo.")
        
        return True