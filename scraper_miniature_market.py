import sys
import datetime
import requests
import time
import re
from bs4 import BeautifulSoup
from monitor_core import (
    get_db_connection, init_db, fetch_bgg_id, fetch_details, 
    save_deal, NOISE_RE, IGNORE_KEYWORDS, HEADERS_GENERIC
)

SITE_NAME = 'Miniature Market'
# Filtrando por Board Games usando el property ID: 019262c7e0db711a97a94030d6103aa9
BG_FILTER = "properties=019262c7e0db711a97a94030d6103aa9"

SOURCES = {
    'daily': f"https://www.miniaturemarket.com/dailydeal?{BG_FILTER}",
    'sales': f"https://www.miniaturemarket.com/deals.html?{BG_FILTER}",
    'backrooms': f"https://www.miniaturemarket.com/the-backrooms?{BG_FILTER}",
    'clearance': f"https://www.miniaturemarket.com/deals/clearance.html?{BG_FILTER}",
    'gameon': f"https://www.miniaturemarket.com/deals/game-on-weekend?{BG_FILTER}",
    'lastchance': f"https://www.miniaturemarket.com/search?search=Last+Chance&{BG_FILTER}",
    'markdown': f"https://www.miniaturemarket.com/search?search=Markdown&{BG_FILTER}",
    'preorder': f"https://www.miniaturemarket.com/search?search=Pre-order&{BG_FILTER}"
}

def scrape_mm(source_key):
    if source_key not in SOURCES:
        print(f"Fuente desconocida: {source_key}")
        return

    url_base = SOURCES[source_key]
    today = datetime.date.today().isoformat()
    source_tag = f"mm_{source_key}"
    
    print(f"--- [INICIO] Scraping {SITE_NAME} {source_key.upper()} (Filtro Board Games) ---")
    
    init_db()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('DELETE FROM deals WHERE date_found=? AND deal_source=?', (today, source_tag))
    finally:
        conn.close()

    p = 1
    # Aumentado el límite de páginas ya que 'sales' tiene miles de productos
    max_pages = 300 if source_key == 'sales' else 50
    
    while p < max_pages:
        # Ajustar paginación según si ya hay parámetros
        if p == 1:
            url = url_base
        else:
            sep = "&" if "?" in url_base else "?"
            url = f"{url_base}{sep}p={p}"
            
        print(f"Cargando página {p}: {url}")
        try:
            res = requests.get(url, headers=HEADERS_GENERIC, timeout=15)
            if res.status_code != 200: 
                print(f"Página no disponible (Status {res.status_code})")
                break
            
            soup = BeautifulSoup(res.content, 'html.parser')
            
            # Intentar detectar el layout automático
            items = soup.select('.product-box')
            layout = "box"
            if not items:
                items = soup.select('.product-item')
                layout = "standard"
            
            if not items: 
                print("No se encontraron productos con ningún layout conocido.")
                break
                
            found_new = False
            for item in items:
                if layout == "box":
                    a_tag = item.select_one('.product-name')
                    if not a_tag: continue
                    u = a_tag['href']
                    name = a_tag.get('title', a_tag.text.strip())
                    p_new_tag = item.select_one('.product-price')
                    p_old_tag = item.select_one('.list-price-price')
                    img_tag = item.select_one('img.product-image')
                    img_url = img_tag['src'] if img_tag else ""
                else: # Layout Standard (Legacy)
                    a_tag = item.select_one('.product-item-link')
                    if not a_tag: continue
                    u = a_tag['href']
                    name = a_tag.text.strip()
                    p_new_tag = item.select_one('.price-wrapper .price')
                    p_old_tag = item.select_one('.old-price .price')
                    img_tag = item.select_one('img.product-image')
                    img_url = img_tag['data-src'] if img_tag and img_tag.has_attr('data-src') else (img_tag['src'] if img_tag else "")
                
                # LIMPIEZA DE RUIDO EN EL NOMBRE
                name = re.sub(r'\(Clearance\)|\(Last Chance\)|\(New Arrival\)|\(Preorder\)|\s*CASE\s*\(\d+\)', '', name, flags=re.I).strip()
                
                # FILTRO DE PALABRAS IGNORADAS (Antes de imprimir progreso)
                if any(k.lower() in name.lower() for k in IGNORE_KEYWORDS):
                    continue

                print(f"   - Procesando: {name}")
                search_name = name 
                found_new = True
                
                p_new = p_new_tag.text.strip() if p_new_tag else "0$"
                p_old = p_old_tag.text.strip() if p_old_tag else p_new

                # Cache check
                conn = get_db_connection()
                cached = None
                try:
                    cached = conn.execute('''
                        SELECT bgg_id, confidence FROM bgg_mapping 
                        WHERE item_name=? AND (confidence >= 95 OR bgg_id = 'IGNORED' OR last_search >= ?)
                    ''', (name, (datetime.date.today() - datetime.timedelta(days=7)).isoformat())).fetchone()
                finally:
                    conn.close()

                if cached:
                    id_b, conf = cached
                else:
                    id_b, conf = fetch_bgg_id(search_name, u, source=source_tag)
                    conn = get_db_connection()
                    try:
                        with conn:
                            conn.execute('INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)', (name, id_b, conf, today))
                    finally:
                        conn.close()

                if id_b == "IGNORED": continue

                # Save
                conn = get_db_connection()
                try:
                    with conn:
                        is_exp = any(k in name.lower() for k in ['expansion','expansion','pack'])
                        save_deal(conn, name, p_new, p_old, u, False, is_exp, source_tag, "", img_url)
                        
                        if id_b and not conn.execute('SELECT bgg_id FROM games WHERE bgg_id=?', (id_b,)).fetchone():
                            details = fetch_details(id_b)
                            if details:
                                rat, rnk, gt, l_dep, o_name, wgt, min_p, max_p, best_p = details
                                conn.execute('''
                                    INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) 
                                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                                ''', (id_b, name, rat, rnk, gt, today, l_dep, o_name, wgt, min_p, max_p, best_p))
                finally:
                    conn.close()
            
            if not found_new and p > 10: # Para 'sales' no paramos tan pronto si solo hay basura en una pág, pero dudo que pases 10 págs de solo basura
                 pass # Seguir si es necesario
            
            # Si no hay productos en absoluto (items vacíos), ya paró arriba.
            p += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"Error scraping MM: {e}")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        scrape_mm(sys.argv[1])
    else:
        print("Uso: python scraper_miniature_market.py [backrooms|daily|sales|clearance|gameon]")
