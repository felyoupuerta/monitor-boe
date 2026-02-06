#!/usr/bin/env python3
"""Analizar estructura HTML de Francia"""

from bs4 import BeautifulSoup

with open('debug_france_html.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# Buscar patrones de resultados
print("=" * 60)
print("BUSCANDO ESTRUCTURA DE RESULTADOS")
print("=" * 60)

# Buscar divs con class 'result', 'item', etc
for selector in ['[class*="result"]', '[class*="item"]', '[class*="document"]', '[data-result]', 'article']:
    elements = soup.select(selector)
    if elements:
        print(f"\n✓ Encontrados {len(elements)} elementos con selector: {selector}")
        if elements:
            print(f"  Primer elemento: {str(elements[0])[:300]}...\n")

# Buscar todos los links
print("\n" + "=" * 60)
print("BUSCANDO LINKS")
print("=" * 60)

links = soup.find_all('a', href=True)
print(f"\n✓ Total de <a> tags: {len(links)}")

# Buscar links con patrones específicos
jorf_links = [l for l in links if 'jorf' in l.get('href', '').lower() or 'legifrance' in l.get('href', '')]
print(f"✓ Links con 'jorf' o 'legifrance': {len(jorf_links)}")

if jorf_links:
    print("\nPrimeros 5 links:")
    for i, link in enumerate(jorf_links[:5], 1):
        title = link.get_text(strip=True)[:80]
        href = link.get('href', '')[:80]
        print(f"  {i}. Título: {title}")
        print(f"     URL: {href}\n")

# Buscar por clases específicas comunes en JORF
print("\n" + "=" * 60)
print("CLASES CSS ENCONTRADAS")
print("=" * 60)

classes = set()
for elem in soup.find_all(class_=True):
    for cls in elem.get('class', []):
        classes.add(cls)

# Filtrar por relevancia
relevant = [c for c in classes if any(x in c.lower() for x in ['result', 'item', 'doc', 'search', 'article', 'publication', 'row', 'list'])]
print(f"\nClases relevantes encontradas: {sorted(relevant)[:20]}")
