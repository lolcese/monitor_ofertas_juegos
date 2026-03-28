import sys
import datetime
import re
import requests
import time
from bs4 import BeautifulSoup
from monitor_core import (
    get_db_connection, init_db, fetch_bgg_id, fetch_details, 
    HEADERS_GENERIC, save_deal, IGNORE_KEYWORDS
)

MM_IGNORE = ['replacement','binder','sleeves','mat','token','card holder','bag','box','case','paint','miniature','mini','model','kit', 'puzzle']

SOURCES = {
    'backdoor': "https://www.miniaturemarket.com/the-backrooms?order=name-asc&properties=019262c7e0db711a97a94030d6103aa9",
    'deals': "https://www.miniaturemarket.com/deals.html?order=name-asc&properties=019262c7e0db711a97a94030d6103aa9",
    'clearance': "https://www.miniaturemarket.com/deals/clearance.html?order=name-asc&properties=019262c7e0db711a97a94030d6103aa9"
}

def scrape_mm(source_key):
    if source_key not in SOURCES:
        print(f"Fuente MM desconocida: {source_key}")
        return
    
    init_db()
    today = datetime.date.today().isoformat()
    url_base = SOURCES[source_key]
    source_tag = f"mm_{source_key}"
    
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('DELETE FROM deals WHERE date_found=? AND deal_source=?', (today, source_tag))
    finally:
        conn.close()

    p = 1
    seen = set()
    print(f"--- [INICIO] Scraping Miniature Market {source_key.upper()} ---")
    
    while True:
        url = f"{url_base}&p={p}"
        print(f"Cargando página {p}: {url}")
        try:
            res = requests.get(url, headers=HEADERS_GENERIC, timeout=15)
            if res.status_code != 200: break
            
            soup = BeautifulSoup(res.content, 'html.parser')
            # Selector de contenedor corregido
            items = soup.select('.cms-listing-col')
            if not items: break
                
            found_new = False
            for item in items:
                # 1. Filtro estricto de STOCK
                if not item.select_one('.btn-buy'): continue

                # 2. Link y Nombre
                a_tag = item.select_one('a.product-name')
                if not a_tag: continue
                
                u = a_tag['href']
                name = a_tag.text.strip()
                
                if u in seen: continue
                seen.add(u)
                found_new = True
                
                print(f"   Procesando MM: {name}...")

                lower_name = name.lower()
                if any(k in lower_name for k in IGNORE_KEYWORDS) or any(k in lower_name for k in MM_IGNORE):
                    continue
                
                p_new_tag = item.select_one('.product-price')
                p_old_tag = item.select_one('.list-price-price')
                p_new = p_new_tag.text.strip() if p_new_tag else "0$"
                p_old = p_old_tag.text.strip() if p_old_tag else p_new 
                
                img_tag = item.select_one('img.product-image')
                img_url = img_tag['data-src'] if img_tag and img_tag.has_attr('data-src') else (img_tag['src'] if img_tag else "")

                search_name = re.sub(r'\(Clearance\)|\(Last Chance\)', '', name, flags=re.I).strip()

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
                    id_b, conf, real_n = cached[0], cached[1], search_name
                else:
                    id_b, conf, real_n = fetch_bgg_id(search_name, u, source=source_tag)
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
                            rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = fetch_details(id_b)
                            conn.execute('''
                                INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) 
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                            ''', (id_b, real_n, rat, rnk, gt, today, l_dep, o_name, wgt, minp, maxp, bestp))
                finally:
                    conn.close()
            
            if not found_new: break
            p += 1
            time.sleep(1)
        except Exception as e:
            print(f"Error scraping MM: {e}")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        scrape_mm(sys.argv[1])
    else:
        print("Uso: python scraper_miniature_market.py [backdoor|deals|clearance]")
