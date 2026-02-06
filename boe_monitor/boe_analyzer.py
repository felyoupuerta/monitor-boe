#!/usr/bin/env python3
"""
Monitor principal para Boletines Oficiales de diferentes países.
Descarga, analiza y notifica cambios en publicaciones oficiales.
"""

import requests
import urllib3
import json
import time
import re
import smtplib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup

from db_manager import DatabaseManager
from logger_config import setup_logger

logger = setup_logger(__name__)


class BOEMonitor:
    """
    Monitor de Boletines Oficiales con soporte multi-país.
    Soporta múltiples métodos de obtención de datos (HTTP, Selenium, APIs).
    """
    
    # Parsers específicos por país
    COUNTRY_PARSERS = {
        'es': '_parse_es',
        'fr': '_parse_fr',
        'cz': '_parse_cz',
        'kw': '_parse_kw'
    }
    
    # Fetchers específicos por país
    COUNTRY_FETCHERS = {
        'kw': '_fetch_kw'
    }
    
    def __init__(self, db_config: Dict, source_config: Dict, data_dir: str = "./boe_data"):
        """
        Inicializa el monitor.
        
        Args:
            db_config: Configuración de base de datos
            source_config: Configuración de la fuente del país
            data_dir: Directorio para almacenar datos históricos
        """
        self.source_config = source_config
        self.country_code = source_config.get('country_code', 'es').lower()
        self.country_name = source_config.get('name', self.country_code)
        
        self.data_dir = Path(data_dir) / self.country_code
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db = DatabaseManager(db_config, country_code=self.country_code)
        self.db.init_tables()
        
        self.session = requests.Session()
        
        if not source_config.get('verify_ssl', True):
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        logger.info(f"Monitor inicializado para {self.country_name} ({self.country_code})")
    
    def _get_date_formats(self, date: datetime) -> Dict:
        """
        Genera múltiples formatos de fecha para templates de URL.
        Incluye strings y valores numéricos para máxima compatibilidad.
        
        Args:
            date: Objeto datetime
        
        Returns:
            Diccionario con diferentes formatos de fecha
        """
        return {
            "date_ymd": date.strftime("%Y%m%d"),
            "date": date.strftime("%Y%m%d"),
            "date_iso": date.strftime("%Y-%m-%d"),
            "date_dmy": date.strftime("%d/%m/%Y"),
            "date_dmy_dot": date.strftime("%d.%m.%Y"),
            "day": date.day,
            "month": date.month,
            "year": date.year
        }
    
    def fetch_data(self, date: datetime) -> Optional[str]:
        """
        Obtiene datos del boletín para la fecha especificada.
        Utiliza fetcher específico del país si existe.
        
        Args:
            date: Fecha a descargar
        
        Returns:
            Contenido descargado o None si falla
        """
        formats = self._get_date_formats(date)
        url_template = self.source_config.get('api_url_template')
        
        try:
            url = url_template.format(**formats)
            logger.debug(f"URL generada: {url}")
        except KeyError as e:
            logger.error(f"Error en template de URL: {e}")
            return None
        
        headers = self.source_config.get('headers', {})
        
        # Usar fetcher específico del país si existe
        if self.country_code in self.COUNTRY_FETCHERS:
            fetcher_method = getattr(self, self.COUNTRY_FETCHERS[self.country_code], None)
            if fetcher_method:
                return fetcher_method(url, headers, date)
        
        # Usar método configurado
        fetch_method = self.source_config.get('fetch_method', 'requests')
        if fetch_method == 'selenium':
            return self._fetch_selenium(url, headers)
        
        return self._fetch_requests(url, headers)
    
    def _fetch_requests(self, url: str, headers: Dict) -> Optional[str]:
        """
        Descarga contenido usando librería requests.
        
        Args:
            url: URL a descargar
            headers: Headers HTTP
        
        Returns:
            Contenido descargado o None
        """
        try:
            verify_ssl = self.source_config.get('verify_ssl', True)
            timeout = self.source_config.get('timeout', 30)
            
            response = self.session.get(url, headers=headers, timeout=timeout, verify=verify_ssl)
            
            if response.status_code == 200:
                logger.debug(f"Descarga exitosa de {self.country_code}: {len(response.text)} bytes")
                return response.text
            else:
                logger.warning(f"Error HTTP {response.status_code} para {url}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error en descarga: {e}")
            return None
    
    def _fetch_selenium(self, url: str, headers: Dict) -> Optional[str]:
        """
        Descarga contenido dinámico usando Selenium con técnicas anti-Cloudflare.
        
        Args:
            url: URL a descargar
            headers: Headers HTTP
        
        Returns:
            Contenido descargado o None
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Técnicas anti-bot para Cloudflare
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Desabilitar WebDriver detection
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-logging')
            
            driver = webdriver.Chrome(options=options)
            
            # Ejecutar script para ocultar webdriver
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
            
            delay = self.source_config.get('delay', 10)
            
            logger.debug(f"Selenium obteniendo: {url}")
            driver.get(url)
            
            # Esperar a que cargue o a que desaparezca challenge
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
                )
            except:
                time.sleep(delay)
            
            time.sleep(delay)
            
            html = driver.page_source
            driver.quit()
            
            logger.debug(f"Contenido Selenium obtenido: {len(html)} bytes")
            
            # Validar que no sea página de error Cloudflare
            if "Un momento" in html or "one moment" in html.lower() or "cloudflare" in html.lower():
                logger.warning("Cloudflare bloqueó Selenium, intentando con requests")
                return self._fetch_requests_with_headers(url)
            
            return html
            
        except Exception as e:
            logger.error(f"Error en Selenium: {e}")
            logger.debug("Reintentando con requests")
            return self._fetch_requests_with_headers(url)
    
    def _fetch_requests_with_headers(self, url: str) -> Optional[str]:
        """Fetch con headers realistas para evitar bloqueos."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,es;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = self.session.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code == 200:
                logger.debug(f"Descarga exitosa con requests: {len(response.text)} bytes")
                return response.text
            else:
                logger.warning(f"Error HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error en requests: {e}")
            return None
    
    def _fetch_kw(self, url: str, headers: Dict, date: datetime) -> Optional[str]:
        """
        Fetcher especializado para Kuwait (uso de API POST).
        
        Args:
            url: URL inicial
            headers: Headers HTTP
            date: Fecha (no usado en este caso)
        
        Returns:
            JSON con datos
        """
        try:
            # Primera petición para obtener EditionID
            response = self.session.get(url, headers=headers, 
                                       verify=self.source_config.get('verify_ssl', False), 
                                       timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Error en descarga inicial Kuwait: {response.status_code}")
                return None
            
            # Buscar EditionID en respuesta
            match = re.search(r"EditionID_FK\s*=\s*['\"](\d+)['\"]", response.text)
            if not match:
                logger.warning("EditionID_FK no encontrado en respuesta de Kuwait")
                return None
            
            edition_id = match.group(1)
            logger.debug(f"EditionID obtenido: {edition_id}")
            
            # Segunda petición para obtener datos
            api_url = "https://kuwaitalyawm.media.gov.kw/online/AdsMainEditionJson"
            payload = {
                "draw": "1",
                "start": "0",
                "length": "1000",
                "search[value]": "",
                "search[regex]": "false",
                "order[0][column]": "1",
                "order[0][dir]": "desc",
                "EditionID_FK": edition_id,
                "columns[0][data]": "AdsTitle",
                "columns[0][name]": "",
                "columns[0][searchable]": "true",
                "columns[0][orderable]": "true",
            }
            
            api_response = self.session.post(api_url, data=payload,
                                            headers={"X-Requested-With": "XMLHttpRequest"},
                                            verify=self.source_config.get('verify_ssl', False))
            
            if api_response.status_code == 200:
                logger.debug(f"Datos Kuwait obtenidos: {len(api_response.text)} bytes")
                return api_response.text
            else:
                logger.warning(f"Error en API Kuwait: {api_response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error en _fetch_kw: {e}")
            return None
    
    def parse(self, content: Optional[str]) -> List[Dict]:
        """
        Parsea el contenido descargado según el país.
        
        Args:
            content: Contenido a parsear
        
        Returns:
            Lista de publicaciones extraídas
        """
        if not content:
            logger.warning(f"Contenido vacío para {self.country_code}")
            return []
        
        # Usar parser específico del país si existe
        if self.country_code in self.COUNTRY_PARSERS:
            parser_method = getattr(self, self.COUNTRY_PARSERS[self.country_code], None)
            if parser_method:
                return parser_method(content)
        
        # Usar parser genérico
        return self._parse_generic(content)
    
    def _parse_es(self, content: str) -> List[Dict]:
        """Parser especializado para España (XML)."""
        try:
            soup = BeautifulSoup(content, 'xml')
            items = []
            
            for item_elem in soup.find_all('item'):
                item = {
                    'titulo': item_elem.find('titulo').get_text(strip=True) if item_elem.find('titulo') else '',
                    'url': item_elem.find('urlPdf').get_text(strip=True) if item_elem.find('urlPdf') else '',
                    'seccion': item_elem.find('seccion').get_text(strip=True) if item_elem.find('seccion') else '',
                    'departamento': item_elem.find('departamento').get_text(strip=True) if item_elem.find('departamento') else '',
                }
                if item.get('titulo'):
                    items.append(item)
            
            logger.info(f"Parseadas {len(items)} publicaciones de España")
            return items
            
        except Exception as e:
            logger.error(f"Error parseando España: {e}")
            return []
    
    def _parse_fr(self, content: str) -> List[Dict]:
        """Parser especializado para Francia (HTML) - legifrance.gouv.fr"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            items = []
            
            # Estructura: article[class*="result-item"] > h2 > a
            for article in soup.select('article[class*="result-item"]'):
                # Buscar el título y link
                title_elem = article.select_one('h2.title-result-item, h2')
                if not title_elem:
                    continue
                
                # El link está dentro del h2
                link_elem = title_elem.select_one('a')
                if not link_elem:
                    continue
                
                href = link_elem.get('href', '').strip()
                title = link_elem.get_text(strip=True)
                
                if href and title and len(title) > 8:
                    # Construir URL completa si es relativa
                    if href.startswith('/'):
                        full_url = 'https://www.legifrance.gouv.fr' + href
                    else:
                        full_url = href
                    
                    # Extraer sección/departamento del atributo data o del contenedor
                    section = 'JORF'
                    department = 'Texte'
                    
                    # Buscar información adicional en el article
                    meta_elem = article.select_one('[class*="nature"], [class*="type"], .type-result-item')
                    if meta_elem:
                        meta_text = meta_elem.get_text(strip=True)
                        if meta_text:
                            department = meta_text[:50]
                    
                    item = {
                        'titulo': title[:300],
                        'url': full_url,
                        'seccion': section,
                        'departamento': department,
                    }
                    
                    # Evitar duplicados
                    if not any(i['url'] == full_url for i in items):
                        items.append(item)
            
            logger.info(f"Parseadas {len(items)} publicaciones de Francia")
            
            if not items:
                logger.debug(f"HTML recibido tiene {len(content)} caracteres")
                # Log algunos detalles para debugging
                articles = soup.select('article')
                logger.debug(f"Encontrados {len(articles)} articles totales")
            
            return items
            
        except Exception as e:
            logger.error(f"Error parseando Francia: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _parse_cz(self, content: str) -> List[Dict]:
        """Parser especializado para República Checa (HTML)."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            items = []
            
            for row in soup.select('tr.pravni-akt-row'):
                link = row.select_one('td.cell-nazev a')
                if link:
                    item = {
                        'titulo': link.get_text(strip=True),
                        'url': link.get('href', ''),
                        'rango': row.select_one('td.cell-cislo').get_text(strip=True) if row.select_one('td.cell-cislo') else '',
                        'seccion': 'Sbírka zákonů',
                        'departamento': 'Nová legislativa',
                    }
                    items.append(item)
            
            logger.info(f"Parseadas {len(items)} publicaciones de República Checa")
            return items
            
        except Exception as e:
            logger.error(f"Error parseando República Checa: {e}")
            return []
    
    def _parse_kw(self, content: str) -> List[Dict]:
        """Parser especializado para Kuwait (JSON)."""
        try:
            data = json.loads(content)
            items = []
            
            for record in data.get('data', []):
                item = {
                    'titulo': record.get('AdsTitle', '').strip(),
                    'url': f"https://kuwaitalyawm.media.gov.kw/flip?id={record.get('ID')}",
                    'seccion': record.get('AdsCategoryTitle', 'Official Gazette'),
                    'departamento': record.get('AgentTitle', ''),
                }
                if item.get('titulo'):
                    items.append(item)
            
            logger.info(f"Parseadas {len(items)} publicaciones de Kuwait")
            return items
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de Kuwait: {e}")
            return []
    
    def _parse_generic(self, content: str) -> List[Dict]:
        """
        Parser genérico basado en reglas configuradas.
        Funciona para HTML/XML con selectores CSS.
        """
        try:
            rules = self.source_config.get('parser_rules', {})
            soup = BeautifulSoup(content, rules.get('engine', 'html.parser'))
            items = []
            
            containers = soup.select(rules.get('container', 'body'))
            logger.debug(f"Contenedores encontrados: {len(containers)}")
            
            for container in containers:
                item = {}
                
                for field, rule in rules.get('fields', {}).items():
                    if 'default' in rule:
                        item[field] = rule['default']
                        continue
                    
                    selector = rule.get('selector')
                    if not selector:
                        continue
                    
                    element = container.select_one(selector)
                    
                    if rule.get('type') == 'attr' and element:
                        item[field] = element.get(rule.get('attr'), '')
                    elif element:
                        item[field] = element.get_text(strip=True)
                    else:
                        item[field] = ''
                
                if item.get('titulo'):
                    items.append(item)
            
            logger.info(f"Parseadas {len(items)} publicaciones (parser genérico)")
            return items
            
        except Exception as e:
            logger.error(f"Error en parser genérico: {e}")
            return []
    
    def run_daily_check(self, recipient: List[str], smtp: Dict) -> bool:
        """
        Ejecuta el chequeo diario completo.
        
        Args:
            recipient: Lista de emails destinatarios
            smtp: Configuración SMTP
        
        Returns:
            True si completó exitosamente
        """
        try:
            logger.info(f"Iniciando chequeo diario para {self.country_name}")
            
            today = datetime.now()
            content = self.fetch_data(today)
            
            if not content:
                logger.error("No se pudo descargar contenido")
                return False
            
            items = self.parse(content)
            
            if not items:
                logger.warning("No se encontraron publicaciones")
                return False
            
            # Guardando publicaciones y filtrando nuevas
            new_items = []
            for item in items:
                if self.db.save_publication(item, today.date()):
                    new_items.append(item)
            
            duplicates = len(items) - len(new_items)
            logger.info(f"Publicaciones: {len(items)} totales, {len(new_items)} nuevas, {duplicates} duplicadas")
            
            # Enviar resumen con TODAS las publicaciones encontradas
            self.send_email_summary(items, new_items, recipient, smtp)
            logger.info("Resumen enviado por email")
            
            return True
            
        except Exception as e:
            logger.error(f"Error en chequeo diario: {e}", exc_info=True)
            return False
        finally:
            self.db.close()
    
    def send_email_notification(self, items: List[Dict], recipient: List[str], smtp: Dict) -> None:
        """
        Envía notificación por email con publicaciones nuevas.
        
        Args:
            items: Lista de publicaciones nuevas
            recipient: Lista de emails destinatarios
            smtp: Configuración SMTP
        """
        self.send_email_summary(items, items, recipient, smtp)
    
    def send_email_summary(self, all_items: List[Dict], new_items: List[Dict], recipient: List[str], smtp: Dict) -> None:
        """
        Envía resumen detallado por email con todas las publicaciones y estadísticas.
        
        Args:
            all_items: Lista de todas las publicaciones encontradas
            new_items: Lista de publicaciones nuevas
            recipient: Lista de emails destinatarios
            smtp: Configuración SMTP
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"BOE {self.country_name.upper()} {datetime.now().strftime('%d/%m/%Y')}"
            
            if isinstance(recipient, list):
                recipient_str = ", ".join(recipient)
            else:
                recipient_str = str(recipient)
            
            msg['To'] = recipient_str
            msg['From'] = smtp['username']
            
            html_content = self._build_email_html_summary(all_items, new_items)
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(smtp['server'], smtp['port']) as server:
                server.starttls()
                server.login(smtp['username'], smtp['password'])
                server.send_message(msg)
            
            logger.info(f"Email enviado a {recipient_str}")
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
    
    def _build_email_html(self, items: List[Dict]) -> str:
        """Construcción simple de HTML."""
        return self._build_email_html_summary(items, items)
    
    def _build_email_html_summary(self, all_items: List[Dict], new_items: List[Dict]) -> str:
        """
        Construye HTML con todas las publicaciones y estadísticas de cambios.
        Muestra cuáles son nuevas y cuáles ya existían.
        
        Args:
            all_items: Todas las publicaciones encontradas
            new_items: Solo las nuevas publicaciones
        
        Returns:
            HTML del email
        """
        date_str = datetime.now().strftime('%d de %B de %Y')
        new_count = len(new_items)
        total_count = len(all_items)
        duplicate_count = total_count - new_count
        
        # Determinar estado
        if new_count > 0:
            status_color = "#27ae60"
            status_text = f"✨ {new_count} NUEVA(S) publicación(es)"
        else:
            status_color = "#3498db"
            status_text = f"📋 Sin cambios - {total_count} publicaciones encontradas"
        
        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }}
                .container {{ max-width: 800px; margin: 20px auto; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: #2c3e50; color: #ffffff; padding: 20px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; }}
                .date {{ font-size: 14px; opacity: 0.8; margin-top: 5px; }}
                .status {{ background: {status_color}; color: #ffffff; padding: 15px; text-align: center; font-weight: bold; font-size: 16px; }}
                .stats {{ display: flex; justify-content: space-around; background: #ecf0f1; padding: 15px; text-align: center; }}
                .stat {{ flex: 1; }}
                .stat-number {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
                .stat-label {{ font-size: 12px; color: #7f8c8d; }}
                .content {{ padding: 20px; }}
                .section {{ margin-bottom: 20px; }}
                .section-title {{ font-size: 13px; font-weight: bold; color: #ffffff; background: #3498db; padding: 8px 12px; border-radius: 4px; margin-bottom: 10px; }}
                .item {{ background: #ffffff; border-left: 4px solid #3498db; padding: 12px; margin-bottom: 10px; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
                .item-new {{ border-left-color: #27ae60; background-color: #f0fdf4; }}
                .item-new .section-title {{ background: #27ae60; }}
                .item-title {{ font-size: 14px; font-weight: 600; color: #2c3e50; margin-bottom: 6px; display: block; text-decoration: none; }}
                .item-new .item-title {{ color: #27ae60; }}
                .item-title:hover {{ color: #3498db; }}
                .meta {{ font-size: 11px; color: #7f8c8d; display: flex; flex-wrap: wrap; gap: 6px; }}
                .tag {{ background: #ecf0f1; padding: 2px 6px; border-radius: 10px; font-weight: 500; }}
                .badge-new {{ background: #27ae60; color: #ffffff; padding: 2px 5px; border-radius: 3px; font-size: 10px; font-weight: bold; }}
                .footer {{ background: #ecf0f1; padding: 15px; text-align: center; color: #7f8c8d; font-size: 11px; }}
                .more-text {{ color: #7f8c8d; text-align: center; font-size: 12px; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Monitor BOE - {self.country_name.upper()}</h1>
                    <div class="date">{date_str}</div>
                </div>
                <div class="status">{status_text}</div>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-number">{total_count}</div>
                        <div class="stat-label">Publicaciones encontradas</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number" style="color: #27ae60;">{new_count}</div>
                        <div class="stat-label">Nuevas hoy</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{duplicate_count}</div>
                        <div class="stat-label">Ya en BD</div>
                    </div>
                </div>
                <div class="content">
        """
        
        # Mostrar nuevas publicaciones primero
        if new_items:
            html += f'<div class="section"><div class="section-title">✨ NUEVAS PUBLICACIONES ({new_count})</div>'
            for item in new_items[:25]:
                dept = item.get('departamento', 'General')
                sect = item.get('seccion', 'Boletín')
                
                html += f"""
                <div class="item item-new">
                    <div style="margin-bottom: 5px;"><span class="badge-new">NUEVO</span></div>
                    <a href="{item.get('url', '#')}" class="item-title">{item.get('titulo', 'Sin título')}</a>
                    <div class="meta">
                        <span class="tag">{dept}</span>
                        <span class="tag">{sect}</span>
                    </div>
                </div>
                """
            html += '</div>'
        
        # Mostrar otras publicaciones
        other_items = [i for i in all_items if i not in new_items]
        if other_items:
            html += f'<div class="section"><div class="section-title">📋 OTRAS PUBLICACIONES ({len(other_items)})</div>'
            for item in other_items[:20]:
                dept = item.get('departamento', 'General')
                sect = item.get('seccion', 'Boletín')
                
                html += f"""
                <div class="item">
                    <a href="{item.get('url', '#')}" class="item-title">{item.get('titulo', 'Sin título')}</a>
                    <div class="meta">
                        <span class="tag">{dept}</span>
                        <span class="tag">{sect}</span>
                    </div>
                </div>
                """
            
            if len(other_items) > 20:
                html += f'<div class="more-text">... y {len(other_items) - 20} publicaciones más</div>'
            html += '</div>'
        
        html += """
                </div>
                <div class="footer">
                    BOE Monitor - Sistema de monitorización automática de boletines oficiales
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
