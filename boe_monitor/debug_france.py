#!/usr/bin/env python3
"""Script de debug para Francia - ver qué HTML devuelve Selenium"""

import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

def debug_france_fetch():
    """Debug de la descarga de Francia"""
    
    # Leer config
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    fr_config = config['sources']['fr']
    
    # Construir URL con fecha de hoy
    today = datetime.now()
    url_template = fr_config['api_url_template']
    
    date_formats = {
        'day': today.day,
        'month': today.month,
        'year': today.year
    }
    
    url = url_template.format(**date_formats)
    print(f"URL final: {url}\n")
    
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Técnicas anti-bot
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        
        print("Iniciando Selenium con opciones anti-bot...")
        driver = webdriver.Chrome(options=options)
        
        # Ocultar webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
        
        print(f"Navegando a: {url}")
        driver.get(url)
        
        # Esperar a que se resuelva Cloudflare
        print("Esperando a que cargue...")
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
            )
            print("✓ Página cargó elementos")
        except:
            print("⚠ Timeout esperando elementos, continuando igual")
            time.sleep(10)
        
        time.sleep(5)  # Espera adicional
        
        html = driver.page_source
        driver.quit()
        
        print(f"\n✓ HTML obtenido: {len(html)} caracteres")
        print(f"\nPrimeros 2000 caracteres:\n{html[:2000]}\n")
        
        # Buscar patrones
        print("✓ Búsquedas de patrones:")
        print(f"  - Contiene 'Un momento': {'Un momento' in html}")
        print(f"  - Contiene 'cloudflare': {'cloudflare' in html.lower()}")
        print(f"  - Contiene 'jorf': {'jorf' in html.lower()}")
        print(f"  - Contiene 'legifrance': {'legifrance' in html}")
        print(f"  - Contiene '<a ': {'<a ' in html}")
        print(f"  - Contiene 'href=': {'href=' in html}")
        
        # Guardar a archivo
        with open('debug_france_html.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("\n✓ HTML guardado en debug_france_html.html")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_france_fetch()
