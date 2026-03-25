import sys
import datetime
import requests
import time
from bs4 import BeautifulSoup
from monitor_core import (
    get_db_connection, init_db, fetch_bgg_id, fetch_details, 
    HEADERS_PHILI, save_deal, NOISE_RE
)

# Configuración específica de Philibert
SITE_NAME = 'Philibert'
SOURCES = {
    'flash': "https://www.philibertnet.com/fr/flash-sales",
    'occasion': "https://www.philibertnet.com/fr/214-occasions",
    'private': "https://www.philibertnet.com/fr/15007-ventes-privees"
}

def scrape_philibert(source_key):
    if source_key not in SOURCES:
        print(f"Fuente desconocida: {source_key}")
        return
    
    init_db()
    today = datetime.date.today().isoformat()
    url_base = SOURCES[source_key]
    
    with get_db_connection() as conn:
        conn.execute('DELETE FROM deals WHERE date_found=? AND deal_source=?', (today, source_key))
        conn.commit()

    p = 1
    seen = set()
    print(f"--- [INICIO] Scraping Philibert {source_key.upper()} ---")
    
    while True:
        if p == 1:
            url = url_base
        else:
            url = f"{url_base}?p={p}"
        
        print(f"Cargando página {p}: {url}")
        try:
            res = requests.get(url, headers=HEADERS_PHILI, timeout=15)
            if res.status_code != 200: break
            
            soup = BeautifulSoup(res.content, 'html.parser')
            items = soup.select('.ajax_block_product')
            if not items: break
                
            found_new = False
            for item in items:
                a_tag = item.select_one('.product-name a')
                if not a_tag: continue
                u = a_tag['href']
                name = a_tag.text.strip()
                
                if u in seen: continue
                seen.add(u)
                found_new = True
                
                print(f"   Procesando: {name}...")

                p_new_tag = item.select_one('.content_price .price')
                p_old_tag = item.select_one('.content_price .old-price')
                p_new = p_new_tag.text.strip() if p_new_tag else "0€"
                p_old = p_old_tag.text.strip() if p_old_tag else p_new
                
                img_tag = item.select_one('.product-image-container img')
                img_url = img_tag['src'] if img_tag else ""

                # Cache check
                with get_db_connection() as conn:
                    cached = conn.execute('''
                        SELECT bgg_id, confidence FROM bgg_mapping 
                        WHERE item_name=? AND (confidence >= 95 OR bgg_id = 'IGNORED' OR last_search >= ?)
                    ''', (name, (datetime.date.today() - datetime.timedelta(days=7)).isoformat())).fetchone()

                if cached:
                    id_b, conf, real_n = cached[0], cached[1], name
                else:
                    id_b, conf, real_n = fetch_bgg_id(name, u, source=source_key)
                    if not id_b: continue
                    with get_db_connection() as conn: 
                        conn.execute('INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)', (name, id_b, conf, today))

                if id_b == "IGNORED": continue

                with get_db_connection() as conn:
                    # is_expansion check
                    is_exp = any(k in name.lower() for k in ['extension','expansion','erweiterung','pack'])
                    save_deal(conn, name, p_new, p_old, u, False, is_exp, source_key, "", img_url)
                    
                    if id_b and not conn.execute('SELECT bgg_id FROM games WHERE bgg_id=?', (id_b,)).fetchone():
                        rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = fetch_details(id_b)
                        conn.execute('''
                            INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) 
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        ''', (id_b, real_n, rat, rnk, gt, today, l_dep, o_name, wgt, minp, maxp, bestp))
                conn.commit()
            
            if not found_new: break
            p += 1
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        scrape_philibert(sys.argv[1])
    else:
        print("Uso: python scraper_philibert.py [flash|occasion|private]")
