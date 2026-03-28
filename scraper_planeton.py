import requests
from bs4 import BeautifulSoup
import datetime
import re
import time
from monitor_core import (
    get_db_connection, fetch_bgg_id, fetch_details, 
    save_deal, NOISE_RE, IGNORE_KEYWORDS, HEADERS_GENERIC
)

# URLs de Planeton Games
URLS = {
    'planeton': "https://www.planetongames.com/es/ofertas-195",
    'planeton_preorder': "https://www.planetongames.com/es/proximamente-192"
}

def scrape_planeton(target='planeton'):
    base_url = URLS.get(target, URLS['planeton'])
    source_tag = target
    
    print(f"\n>>> Iniciando scraper de PLANETON GAMES ({target}): {base_url}")
    today = datetime.date.today().isoformat()
    
    page = 1
    total_new = 0
    seen_urls = set()
    
    while page <= 15: # Límite de páginas
        url = f"{base_url}?page={page}"
        print(f"   Cargando página {page}...")
        
        try:
            res = requests.get(url, headers=HEADERS_GENERIC, timeout=15)
            if res.status_code != 200: break
            
            soup = BeautifulSoup(res.content, 'html.parser')
            items = soup.select('.product-miniature')
            if not items: break
            
            for item in items:
                # Requisito de stock según el tipo de página
                stock_tag = item.select_one('.availability .available-now')
                stock_text = stock_tag.text if stock_tag else ""
                
                if target == 'planeton':
                    if "Producto en stock" not in stock_text: continue
                else: # proximamente
                    if "Preventa" not in stock_text and "Resérvalo" not in stock_text: continue
                
                title_tag = item.select_one('.product-title a')
                if not title_tag: continue
                
                u = title_tag['href']
                if u in seen_urls: continue
                seen_urls.add(u)
                
                raw_name = title_tag.text.strip()
                # Limpiar "Preventa", "Resérvalo", "Ver fecha", etc.
                name = re.sub(r'\(New Arrival\)|\(Preorder\)|PREVENTA|RESERVALO|ver fecha', '', raw_name, flags=re.I).strip()
                name = re.sub(NOISE_RE, '', name, flags=re.I).strip()
                
                if any(k.lower() in name.lower() for k in IGNORE_KEYWORDS): continue

                p_new_tag = item.select_one('.price')
                p_old_tag = item.select_one('.regular-price')
                p_new = p_new_tag.text.strip() if p_new_tag else "0€"
                p_old = p_old_tag.text.strip() if p_old_tag else p_new
                
                img_meta = item.select_one('meta[itemprop="image"]')
                img_url = img_meta['content'] if img_meta else ""

                print(f"      - Procesando: {name}")
                
                # BGG Mapping
                conn = get_db_connection()
                cached = conn.execute('SELECT bgg_id, confidence FROM bgg_mapping WHERE item_name=?', (name,)).fetchone()
                conn.close()

                if cached:
                    id_b, conf = cached
                else:
                    id_b, conf = fetch_bgg_id(name, u, source=source_tag)
                    conn = get_db_connection()
                    with conn:
                        conn.execute('INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)', (name, id_b, conf, today))
                    conn.close()

                if id_b == "IGNORED": continue

                # Save Deal
                conn = get_db_connection()
                with conn:
                    is_exp = any(k in name.lower() for k in ['expansion','expansion','pack','ampliacion'])
                    save_deal(conn, name, p_new, p_old, u, False, is_exp, source_tag, "", img_url)
                    
                    if id_b and id_b != 'N/A' and not conn.execute('SELECT bgg_id FROM games WHERE bgg_id=?', (id_b,)).fetchone():
                        details = fetch_details(id_b)
                        if details:
                            rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = details
                            conn.execute('INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (id_b, name, rat, rnk, gt, today, l_dep, o_name, wgt, minp, maxp, bestp))
                conn.close()
                total_new += 1
                
        except Exception as e:
            print(f"   [!] Error: {e}")
            break
        page += 1
        time.sleep(1)

    print(f"\n>>> Scraper Planeton ({target}) finalizado. Total: {total_new}")

if __name__ == "__main__":
    import sys
    mode = 'planeton'
    if len(sys.argv) > 1 and sys.argv[1] == 'preorder':
        mode = 'planeton_preorder'
    scrape_planeton(mode)
