import sqlite3
import requests
import time
from bs4 import BeautifulSoup

DB_PATH = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
HEADERS = {"User-Agent": "Mozilla/5.0"}

def is_philibert_excluded(url):
    """Verifica si el producto pertenece a categorías prohibidas de Philibert."""
    try:
        time.sleep(0.5)
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, 'html.parser')
            body = soup.find('body')
            if not body: return False
            classes = " ".join(body.get('class', []))
            # IDs: 392 (Rol), 8000+ (Figuritas), 1178 (Accesorios), 119 (Cartas/LCG)
            if any(k in classes for k in ['category-392', 'category-8000', 'category-1178', 'category-119', 'category-jeux-de-role', 'category-jeux-de-figurines', 'category-accessoires']):
                return True
            # Breadcrumbs como backup
            bread = soup.find('div', class_='breadcrumb')
            if bread:
                b_text = bread.text.lower()
                if any(k in b_text for k in ['jeu de rôle', 'jeux de rôle', 'figurine', 'accessoire', 'collectionner', 'évolutif']):
                    return True
    except: pass
    return False

def deep_purge():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Buscamos mapeos < 100% que tengan una URL en deals (para poder verificarlos)
    c.execute("""
        SELECT m.philibert_name, d.url, m.confidence 
        FROM bgg_mapping m
        JOIN deals d ON m.philibert_name = d.philibert_name
        WHERE m.confidence < 100
    """)
    candidates = c.fetchall()
    
    print(f"Iniciando purga profunda de categorías para {len(candidates)} candidatos...")
    purged_count = 0
    
    for name, url, conf in candidates:
        if is_philibert_excluded(url):
            print(f"[PURGADO] '{name}' ({conf:.1f}%) detectado como categoría excluida. Eliminando...")
            # Eliminamos de bgg_mapping y de deals (para que desaparezca del reporte actual)
            c.execute("DELETE FROM bgg_mapping WHERE philibert_name=?", (name,))
            c.execute("DELETE FROM deals WHERE philibert_name=?", (name,))
            conn.commit()
            purged_count += 1
        else:
            print(f"[MANTENIDO] '{name}' ({conf:.1f}%) parece ser un juego legítimo.")
            
    conn.close()
    print(f"\nPurga finalizada. Se han eliminado {purged_count} entradas no deseadas.")

if __name__ == "__main__":
    deep_purge()
