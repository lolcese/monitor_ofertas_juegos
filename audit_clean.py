import sqlite3
import requests
import time
from bs4 import BeautifulSoup

DB_PATH = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
HEADERS = {"User-Agent": "Mozilla/5.0"}

def is_philibert_excluded(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, 'html.parser')
            body = soup.find('body')
            classes = " ".join(body.get('class', [])) if body else ""
            bread = soup.find('div', class_='breadcrumb')
            bread_text = bread.text.lower() if bread else ""
            
            reasons = []
            if 'category-1178' in classes or 'category-accessoires' in classes or 'accessoire' in bread_text:
                reasons.append("ACCESORIO (ID 1178)")
            if 'category-392' in classes or 'category-jeux-de-role' in classes or 'jeu de rôle' in bread_text:
                reasons.append("ROL (ID 392)")
            if 'category-8000' in classes or 'category-jeux-de-figurines' in classes or 'figurine' in bread_text:
                reasons.append("FIGURITAS (ID 8000+)")
            
            return reasons if reasons else None
    except: return None

def audit_clean():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Revisamos las ofertas encontradas hoy
    c.execute("SELECT philibert_name, url FROM deals WHERE date_found = (SELECT MAX(date_found) FROM deals)")
    deals = c.fetchall()
    
    print(f"Auditando {len(deals)} ofertas actuales...")
    to_clean = []
    for name, url in deals:
        reasons = is_philibert_excluded(url)
        if reasons:
            to_clean.append((name, reasons))
            print(f"[BLOQUEADO] {name} -> Razones: {', '.join(reasons)}")
        time.sleep(0.5)
        
    if not to_clean:
        print("\nNo se han encontrado accesorios, rol o figuritas infiltradas en las ofertas actuales. ¡Filtros funcionando!")
    else:
        print(f"\nSe han detectado {len(to_clean)} productos que serán eliminados en la próxima ejecución.")
    conn.close()

if __name__ == "__main__": audit_clean()
