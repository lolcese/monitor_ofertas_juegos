import sys
import requests
import re
from bs4 import BeautifulSoup
from philibert_core import get_db_connection, fetch_details, HEADERS, save_deal
import datetime

def manual_fix(phili_url, bgg_input):
    # 0. Headers de navegador para evitar el 503
    PHILI_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    # 1. Extraer ID de BGG
    bgg_id = re.search(r'boardgame/(\d+)', bgg_input)
    bgg_id = bgg_id.group(1) if bgg_id else bgg_input
    
    print(f"🔍 Identificando producto en Philibert...")
    res = requests.get(phili_url, headers=PHILI_HEADERS, timeout=10)
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # Intentar pillar el nombre del H1 (que es el nombre oficial en la ficha)
    title_tag = soup.find('h1', class_='item-title') or soup.find('h1')
    if not title_tag:
        print("❌ Error: No se pudo encontrar el título en la página de Philibert.")
        return
    
    p_name = title_tag.text.strip()
    print(f"🎯 Producto detectado: '{p_name}'")
    
    # 2. Obtener detalles de BGG
    print(f"🌐 Consultando BGG para el ID {bgg_id}...")
    rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = fetch_details(bgg_id)
    
    # 3. Guardar en la base de datos
    today = datetime.date.today().isoformat()
    with get_db_connection() as conn:
        # Forzar el mapeo
        conn.execute('''
            INSERT OR REPLACE INTO bgg_mapping (philibert_name, bgg_id, confidence, last_search)
            VALUES (?, ?, ?, ?)
        ''', (p_name, bgg_id, 100.0, today))
        
        # Actualizar metadatos del juego
        conn.execute('''
            INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (bgg_id, o_name, rat, rnk, gt, today, l_dep, o_name, wgt, minp, maxp, bestp))
        
        conn.commit()
    
    print(f"✅ ¡ÉXITO! '{p_name}' ahora está vinculado a '{o_name}' (#{rnk})")
    print(f"Recuerda ejecutar 'python generate_report.py' para ver los cambios.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python manual_fix.py \"URL_PHILIBERT\" \"URL_BGG_O_ID\"")
    else:
        manual_fix(sys.argv[1], sys.argv[2])
