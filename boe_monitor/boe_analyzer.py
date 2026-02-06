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
    
    def _get_date_formats(self, date: datetime) -> Dict[str, str]:
        """
        Genera múltiples formatos de fecha para usar en templates de URL.
        
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
            "day": f"{date.day:02d}",
            "month": f"{date.month:02d}",
            "year": str(date.year)
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
        Descarga contenido dinámico usando Selenium.
        Útil para sitios con JavaScript.
        
        Args:
            url: URL a descargar
            headers: Headers HTTP
        
        Returns:
            Contenido descargado o None
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            driver = webdriver.Chrome(options=options)
            delay = self.source_config.get('delay', 5)
            
            driver.get(url)
            time.sleep(delay)
            
            html = driver.page_source
            driver.quit()
            
            logger.debug(f"Contenido Selenium obtenido: {len(html)} bytes")
            return html
            
        except Exception as e:
            logger.error(f"Error en Selenium: {e}")
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
        """Parser especializado para Francia (HTML)."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            items = []
            
            for container in soup.select('.notice, .result, article'):
                title_elem = container.select_one('h3, h2')
                link_elem = container.select_one('h3 a, h2 a')
                
                if title_elem and link_elem:
                    item = {
                        'titulo': title_elem.get_text(strip=True),
                        'url': link_elem.get('href', ''),
                        'seccion': 'JORF',
                        'departamento': 'Texte',
                    }
                    items.append(item)
            
            logger.info(f"Parseadas {len(items)} publicaciones de Francia")
            return items
            
        except Exception as e:
            logger.error(f"Error parseando Francia: {e}")
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
            
            # Enviar notificaciones si hay nuevas publicaciones
            if new_items:
                self.send_email_notification(new_items, recipient, smtp)
                logger.info("Notificación de email enviada")
            else:
                logger.info("No hay nuevas publicaciones, email no enviado")
            
            return True
            
        except Exception as e:
            logger.error(f"Error en chequeo diario: {e}", exc_info=True)
            return False
        finally:
            self.db.close()
    
    def send_email_notification(self, items: List[Dict], recipient: List[str], smtp: Dict) -> None:
        """
        Envía notificación por email con las nuevas publicaciones.
        
        Args:
            items: Lista de publicaciones nuevas
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
            
            html_content = self._build_email_html(items)
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(smtp['server'], smtp['port']) as server:
                server.starttls()
                server.login(smtp['username'], smtp['password'])
                server.send_message(msg)
            
            logger.info(f"Email enviado a {recipient_str}")
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
    
    def _build_email_html(self, items: List[Dict]) -> str:
        """
        Construye el contenido HTML del email.
        
        Args:
            items: Lista de publicaciones
        
        Returns:
            HTML del email
        """
        date_str = datetime.now().strftime('%d de %B de %Y')
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }}
                .container {{ max-width: 800px; margin: 20px auto; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: #2c3e50; color: #ffffff; padding: 20px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; }}
                .date {{ font-size: 14px; opacity: 0.8; margin-top: 5px; }}
                .content {{ padding: 20px; }}
                .item {{ background: #ffffff; border-left: 4px solid #3498db; padding: 15px; margin-bottom: 15px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
                .item-title {{ font-size: 16px; font-weight: 600; color: #2c3e50; margin-bottom: 8px; display: block; text-decoration: none; }}
                .item-title:hover {{ color: #3498db; }}
                .meta {{ font-size: 13px; color: #7f8c8d; display: flex; flex-wrap: wrap; gap: 10px; }}
                .tag {{ background: #ecf0f1; padding: 2px 8px; border-radius: 12px; font-weight: 500; }}
                .footer {{ background: #ecf0f1; padding: 15px; text-align: center; color: #7f8c8d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Monitor BOE - {self.country_name.upper()}</h1>
                    <div class="date">{date_str}</div>
                </div>
                <div class="content">
                    <p style="color: #666; font-size: 15px;">Se han encontrado <strong>{len(items)}</strong> nuevas publicaciones.</p>
        """
        
        for item in items[:20]:  # Máximo 20 items por email
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
        
        if len(items) > 20:
            html += f"""
            <p style="color: #e74c3c; font-weight: bold;">
                ... y {len(items) - 20} publicaciones más
            </p>
            """
        
        html += """
                </div>
                <div class="footer">
                    Generado automáticamente por BOE Monitor
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
