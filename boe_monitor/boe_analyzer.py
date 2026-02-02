#!/usr/bin/env python3
"""
BOE Monitor - Analizador del Boletín Oficial del Estado
"""

import requests
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

class BOEMonitor:
    def __init__(self, db_config, source_config, data_dir="./boe_data"):
        self.source_config = source_config
        self.country_code = source_config.get('country_code', 'es').lower()
        
        # Directorio específico por país
        self.data_dir = Path(data_dir) / self.country_code
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_url = source_config.get('url', "https://www.boe.es")
        self.db = DatabaseManager(db_config, country_code=self.country_code)
        self.db.init_tables()
        self.session = requests.Session()
        
        # Agregar cookie jar para mantener sesión
        self.session.cookies.update({'JSESSIONID': 'dummy'})

    def get_boe_summary(self, date=None, retry_count=0, max_retries=3):
        """
        Obtiene el sumario del BOE (o equivalente) para una fecha específica
        date: datetime object o None para hoy
        retry_count: contador interno de reintentos
        """
        if date is None:
            date = datetime.now()
        
        # Formatos de fecha extra para templates flexibles
        date_ymd = date.strftime("%Y%m%d")
        date_dmy = date.strftime("%d/%m/%Y")
        date_dmy_encoded = date_dmy.replace("/", "%2F") # DD%2FMM%2FYYYY
        
        # Construir URL usando template si existe, sino lógica default BOE
        url_template = self.source_config.get('api_url_template')
        if url_template:
            # Reemplazar placeholders
            url = url_template.format(
                date=date_ymd, # Legacy/Default
                date_ymd=date_ymd,
                date_dmy=date_dmy,
                date_dmy_encoded=date_dmy_encoded
            )
        else:
            # Fallback a la antigua lógica hardcoded si no hay template
            url = f"{self.base_url}/datosabiertos/api/boe/sumario/{date_ymd}"
        
        headers = self.source_config.get('headers', {'Accept': 'application/xml'})
        
        try:
            print(f"🌍 Consultando URL ({self.country_code}): {url}")
            
            # Agregar delays para Francia para evitar bloqueos
            if self.country_code == 'fr' and retry_count > 0:
                delay = 3 + (retry_count * 2)  # 3s, 5s, 7s
                print(f"⏳ Esperando {delay}s antes de reintentar...")
                time.sleep(delay)
            
            # Para Francia, usar Selenium directamente
            if self.country_code == 'fr':
                print("   Usando Selenium para acceso directo...")
                html_content = self._try_selenium_scrape(url)
                if html_content:
                    return {
                        'date': date_ymd,
                        'content': html_content,
                        'hash': hashlib.md5(html_content.encode()).hexdigest(),
                        'date_obj': date
                    }
                else:
                    print("❌ Selenium no pudo obtener datos")
                    return None
            else:
                response = self.session.get(url, headers=headers, timeout=30)
            
            # Si da error 403, reintentar
            if response and response.status_code == 403:
                print(f"❌ Error 403 Forbidden. Reintentando ({retry_count + 1}/{max_retries})...")
                if retry_count < max_retries:
                    return self.get_boe_summary(date, retry_count + 1, max_retries)
                else:
                    print(f"❌ Se agotaron los reintentos para {date_ymd}")
                    return None

            if response:
                try:
                    response.raise_for_status()
                except:
                    if response.status_code == 403 and retry_count < max_retries:
                        return self.get_boe_summary(date, retry_count + 1, max_retries)
                    return None
                
                return {
                    'date': date_ymd,
                    'content': response.text,
                    'hash': hashlib.md5(response.text.encode()).hexdigest(),
                    'date_obj': date
                }
            else:
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener datos para {date_ymd}: {e}")
            if retry_count < max_retries and '403' not in str(e):
                return self.get_boe_summary(date, retry_count + 1, max_retries)
            return None
    
    def _get_response_with_bypass(self, url, headers):
        """
        Intenta obtener respuesta con múltiples estrategias para evitar bloqueos
        """
        strategies = [
            {'headers': headers},
            {'headers': {**headers, 'Accept': 'application/json'}},
            {'headers': {**headers, 'X-Requested-With': 'XMLHttpRequest'}},
            {'headers': {**headers, 'Accept': 'text/html'}},
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                print(f"   Intento {i+1}: Headers alternativos...")
                response = self.session.get(url, timeout=10, **strategy)
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    time.sleep(2)
                    continue
            except Exception as e:
                print(f"   Error en intento {i+1}: {e}")
                continue
        
        # Último intento sin custom headers
        try:
            print("   Intento final: Sin headers custom...")
            response = self.session.get(url, timeout=10)
            return response
        except Exception as e:
            print(f"   Error final: {e}")
            return None
    
    def _try_selenium_scrape(self, url):
        """
        Intenta usar Selenium para obtener contenido de Francia (requiere chromedriver)
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            print("   Intentando con Selenium (navegador real)...")
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            
            # Esperar a que se cargue contenido
            time.sleep(3)
            html = driver.page_source
            driver.quit()
            
            return html if html and len(html) > 500 else None
        except ImportError:
            print("   ⚠️ Selenium no instalado. Instala con: pip install selenium")
            return None
        except Exception as e:
            print(f"   Error con Selenium: {e}")
            return None
    
    def parse_boe_content(self, xml_content):
        """
        Parsea el contenido XML y extrae información relevante.
        Por defecto usa la lógica del BOE Español. 
        Para otros países se debería implementar un parser específico.
        """
        parser_type = self.source_config.get('parser', 'boe_xml')
        
        items = []
        
        # Parser default (BOE España)
        if parser_type == 'boe_xml':
            try:
                soup = BeautifulSoup(xml_content, 'xml')
                for item in soup.find_all('item'):
                    try:
                        items.append({
                            'titulo': item.find('titulo').text if item.find('titulo') else '',
                            'seccion': item.find('seccion').text if item.find('seccion') else '',
                            'departamento': item.find('departamento').text if item.find('departamento') else '',
                            'rango': item.find('rango').text if item.find('rango') else '',
                            'url': item.find('urlPdf').text if item.find('urlPdf') else '',
                        })
                    except Exception:
                        continue
            except Exception as e:
                print(f"Error parseando XML: {e}")
                
        # Parser para Francia (Legifrance)
        elif parser_type == 'fr_jo_demo':
            try:
                soup = BeautifulSoup(xml_content, 'html.parser')
                # Buscar artículos en la estructura de Legifrance
                articles = soup.find_all('article', class_='notice')
                
                if not articles:
                    # Intenta estructura alternativa
                    articles = soup.find_all('div', class_=lambda x: x and 'notice' in x)
                
                for article in articles:
                    try:
                        # Extraer título
                        title_elem = article.find('h3') or article.find('h2') or article.find('a')
                        titulo = title_elem.get_text(strip=True) if title_elem else ''
                        
                        # Extraer URL
                        url_elem = article.find('a', href=True)
                        url = url_elem['href'] if url_elem else ''
                        if url and not url.startswith('http'):
                            url = 'https://www.legifrance.gouv.fr' + url
                        
                        # Extraer sección/tipo (puede estar en clase o texto)
                        section_elem = article.find('span', class_=lambda x: x and 'section' in x.lower())
                        seccion = section_elem.get_text(strip=True) if section_elem else 'JORF'
                        
                        # Extraer departamento/tipo de norma
                        dept_elem = article.find('span', class_=lambda x: x and 'type' in x.lower())
                        departamento = dept_elem.get_text(strip=True) if dept_elem else 'Loi ou Décret'
                        
                        if titulo:  # Solo agregar si hay título
                            items.append({
                                'titulo': titulo,
                                'seccion': seccion,
                                'departamento': departamento,
                                'rango': 'Legifrance',
                                'url': url,
                            })
                    except Exception as e:
                        print(f"Error parseando artículo francés: {e}")
                        continue
                
                if not items:
                    print("⚠️ No se encontraron artículos en la respuesta de Legifrance")
                    
            except Exception as e:
                print(f"Error parseando HTML francés: {e}")
        
        # Parser para Francia - API Legifrance JSON
        elif parser_type == 'fr_legifrance_api':
            try:
                # Primero intenta parsear como JSON
                try:
                    data = json.loads(xml_content)
                    results = data.get('results', [])
                except (json.JSONDecodeError, ValueError):
                    # Si no es JSON, es HTML
                    results = []
                
                # Si no hay resultados en JSON, parsear como HTML
                if not results:
                    print("   Parseando como HTML...")
                    items = self._parse_legifrance_html_fallback(xml_content)
                    if items:
                        return items
                
                # Procesar resultados JSON
                for item in results:
                    try:
                        titulo = item.get('title') or item.get('titrage', '')
                        url = item.get('url', '')
                        
                        if url and not url.startswith('http'):
                            url = 'https://www.legifrance.gouv.fr' + url
                        
                        seccion = item.get('nature', 'JORF')
                        if isinstance(seccion, dict):
                            seccion = seccion.get('label', 'JORF')
                        
                        departamento = item.get('text_type') or item.get('type_acte', 'Texte')
                        
                        if titulo:
                            items.append({
                                'titulo': str(titulo)[:500],
                                'seccion': str(seccion)[:255],
                                'departamento': str(departamento)[:255],
                                'rango': item.get('rank', 'Legifrance')[:255],
                                'url': url,
                            })
                    except Exception as e:
                        continue
                
                if items:
                    print(f"✅ Parseados {len(items)} items")
                else:
                    print("⚠️ Sin items encontrados")
                    
            except Exception as e:
                print(f"Error parseando: {e}")
                items = self._parse_legifrance_html_fallback(xml_content)
        
        return items
    
    def _parse_legifrance_html_fallback(self, html_content):
        """
        Fallback para parsear Legifrance como HTML si la API falla
        Busca en estructura actual de Legifrance (2024+)
        """
        items = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Estrategia 1: Buscar divs con clase 'notice' o similares
            containers = soup.find_all(['article', 'div', 'li'], class_=lambda x: x and any(c in str(x).lower() for c in ['notice', 'result', 'item', 'publication']))
            
            if not containers:
                # Estrategia 2: Buscar todos los enlaces que contengan 'jorf'
                containers = soup.find_all('a', href=lambda x: x and 'jorf' in x.lower())
            
            if not containers:
                # Estrategia 3: Buscar por estructura de tabla
                containers = soup.find_all(['tr', 'div'], class_=lambda x: x and 'row' in str(x).lower())
            
            print(f"   Encontrados {len(containers)} contenedores potenciales")
            
            for container in containers[:100]:  # Limitar a 100 items por seguridad
                try:
                    # Extraer título
                    title_elem = container.find(['h2', 'h3', 'h4', 'a', 'strong', 'span'])
                    if not title_elem:
                        title_elem = container
                    
                    titulo = title_elem.get_text(strip=True) if title_elem else ''
                    
                    # Limpiar título
                    titulo = ' '.join(titulo.split())[:500]
                    
                    if not titulo or len(titulo) < 5:
                        continue
                    
                    # Extraer URL
                    link_elem = container.find('a', href=True)
                    if not link_elem:
                        link_elem = container.find('a')
                    
                    url = ''
                    if link_elem and link_elem.get('href'):
                        url = link_elem['href']
                        if url and not url.startswith('http'):
                            url = 'https://www.legifrance.gouv.fr' + url
                    
                    # Extraer metadatos
                    seccion = 'JORF'
                    departamento = 'Texte'
                    
                    # Buscar sección en texto cercano
                    text_content = container.get_text()
                    if 'décret' in text_content.lower():
                        departamento = 'Décret'
                    elif 'loi' in text_content.lower():
                        departamento = 'Loi'
                    elif 'arrêté' in text_content.lower():
                        departamento = 'Arrêté'
                    
                    if titulo:
                        items.append({
                            'titulo': titulo,
                            'seccion': seccion,
                            'departamento': departamento,
                            'rango': 'Legifrance',
                            'url': url,
                        })
                except Exception as e:
                    continue
            
            print(f"   ✅ Extraídos {len(items)} items del HTML")
            return items
        except Exception as e:
            print(f"Error en fallback HTML: {e}")
            return []
    
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
        Carga datos desde la Base de Datos
        """
        return self.db.get_publications_by_date(date_obj)
    
    def compare_items(self, today_items, yesterday_items):
        """
        Compara dos listas de items y detecta cambios
        """
        today_titles = {item.get('titulo', '') for item in today_items}
        yesterday_titles = {item.get('titulo', '') for item in yesterday_items}
        
        new_items = [item for item in today_items if item.get('titulo', '') not in yesterday_titles]
        
        removed_items = [item for item in yesterday_items if item.get('titulo', '') not in today_titles]
        
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
        """
        msg = MIMEMultipart('alternative')
        country_name = self.source_config.get('name', self.country_code.upper())
        
        if has_changes:
            msg['Subject'] = f"🔔 Novedades en {country_name} - {datetime.now().strftime('%d/%m/%Y')}"
        else:
            msg['Subject'] = f"📋 Estado de {country_name} - {datetime.now().strftime('%d/%m/%Y')}"
            
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
        """
        Ejecuta el chequeo diario
        """
        country_name = self.source_config.get('name', self.country_code)
        print(f"🔍 Iniciando monitoreo de {country_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        today = datetime.now()
        today_data = self.get_boe_summary(today)
        
        if not today_data:
            print("❌ No se pudieron obtener datos hoy")
            self.db.log_execution("error_download", 0, 0, 0, "Failed to download data")
            return False
        
        today_items = self.parse_boe_content(today_data['content'])
        print(f"📥 Total de items obtenidos: {len(today_items)}")
        
        if not today_items:
            print("⚠️ No se encontraron items para procesar")
            self.db.log_execution("no_items", 0, 0, 0, "No items found in content")
            return False
        
        # Cargar datos previos de la BD
        yesterday = today - timedelta(days=1)
        yesterday_items = self.load_day_data(yesterday.date())
        print(f"📚 Items del día anterior en BD: {len(yesterday_items)}")
        
        # Comparar items
        comparison = self.compare_items(today_items, yesterday_items)
        new_items = comparison['new_items']
        removed_items = comparison['removed_items']
        
        print(f"✅ Procesado: {len(today_items)} items totales.")
        print(f"   ➕ Nuevos: {len(new_items)}")
        print(f"   ➖ Eliminados: {len(removed_items)}")
        
        # Guardar TODOS los items de hoy en la BD (para comparación futura)
        saved_count = 0
        for item in today_items:
            if self.db.save_publication(item, today.date()):
                saved_count += 1
        
        print(f"💾 Guardados en BD: {saved_count} items nuevos")
        
        status = "success" if new_items else "no_changes"
        self.db.log_execution(status, len(today_items), len(new_items), len(removed_items), "Check completed")

        if new_items:
            print(f"📊 Novedades detectadas: {len(new_items)} items. Enviando correo...")
            self.send_email_notification(new_items, recipient_email, smtp_config, has_changes=True)
        else:
            print("ℹ️ Sin cambios respecto al día anterior. Enviando confirmación...")
            self.send_email_notification([], recipient_email, smtp_config, has_changes=False)
        
        return True
