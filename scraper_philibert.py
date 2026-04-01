import sys
import datetime
import requests
import time
import re
from bs4 import BeautifulSoup
from monitor_core import (
    get_db_connection, init_db, fetch_bgg_id, fetch_details, 
    HEADERS_PHILI, save_deal, NOISE_RE, IGNORE_KEYWORDS
)

# Configuración específica de Philibert
SITE_NAME = 'Philibert'
SOURCES = {
    'flash': "https://www.philibertnet.com/fr/flash-sales",
    'occasion': "https://www.philibertnet.com/fr/214-occasions",
    'private': "https://www.philibertnet.com/fr/15007-ventes-privees",
    'preorder': "https://www.philibertnet.com/fr/578-precommandes"
}

def scrape_philibert(source_key):
    if source_key not in SOURCES:
        print(f"Fuente desconocida: {source_key}")
        return

    url_base = SOURCES[source_key]
    today = datetime.date.today().isoformat()
    
    print(f"--- [INICIO] Scraping {SITE_NAME} {source_key.upper()} ---")
    
    init_db()
    
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('DELETE FROM deals WHERE date_found=? AND deal_source=?', (today, source_key))
    finally:
        conn.close()

    p = 1
    seen = set()
    while p < 10:
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
                a_tag = item.select_one('.s_title_block a') or item.select_one('.product-name a')
                if not a_tag: continue
                u = a_tag['href']
                name = a_tag.text.strip()
                # LIMPIEZA DE RUIDO
                name = re.sub(r' - Occasion|\(Last Chance\)|\(Clearance\)|\(New Arrival\)|\(Preorder\)', '', name, flags=re.I).strip()
                print(f"   - Procesando: {name}")
                
                # FILTRO DE PALABRAS IGNORADAS
                if any(k.lower() in name.lower() for k in IGNORE_KEYWORDS):
                    continue
                
                # FILTRO DE CATEGORÍA (OPCIONAL/DEEP CHECK)
                # Si el nombre no fue filtrado por keywords pero sospechamos (o para asegurar), 
                # podemos verificar la breadcrumb en la página del producto.
                # Como esto es lento, lo hacemos solo si es un producto nuevo para nosotros.
                conn = get_db_connection()
                is_rpg = False
                try:
                    exists = conn.execute("SELECT bgg_id FROM bgg_mapping WHERE item_name=?", (name,)).fetchone()
                    if not exists:
                        # Check product page category
                        try:
                            res_p = requests.get(u, headers=HEADERS_PHILI, timeout=8)
                            if res_p.status_code == 200:
                                if 'itemprop="breadcrumb"' in res_p.text or 'breadcrumb' in res_p.text:
                                    p_soup = BeautifulSoup(res_p.content, 'html.parser')
                                    bc = p_soup.select_one('.breadcrumb')
                                    if bc:
                                        text = bc.text.lower()
                                        if any(kw in text for kw in ['jeux de rôle', 'wargames de figurines', 'accessoires', 'peinture', 'modélisme']):
                                            is_rpg = True
                                            print(f"      [!] Filtrado por categoría: {bc.text.strip()}")
                                            conn.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)", (name, 'IGNORED', 100, today))
                        except: pass
                finally:
                    conn.close()
                
                if is_rpg: continue

                if u in seen: continue
                seen.add(u)
                found_new = True
                
                p_new_tag = item.select_one('.price:not(.old-price)') or item.select_one('.current-price')
                p_old_tag = item.select_one('.old-price') or item.select_one('.regular-price')
                
                # Fallback if both are the same or one is missing
                p_new = p_new_tag.text.strip() if p_new_tag else "0€"
                p_old = p_old_tag.text.strip() if p_old_tag else p_new
                
                img_tag = item.select_one('.product_img_link img') or item.select_one('.product-image-container img')
                img_url = img_tag['src'] if img_tag else ""

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
                    id_b, conf = fetch_bgg_id(name, u, source=source_key)
                    # Guardamos el mapeo fallido/parcial para que aparezca en el gestor manual
                    conn = get_db_connection()
                    try:
                        with conn:
                            conn.execute('INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)', (name, id_b, conf, today))
                    finally:
                        conn.close()

                if id_b == "IGNORED": continue

                conn = get_db_connection()
                try:
                    with conn:
                        # is_expansion check
                        is_exp = any(k in name.lower() for k in ['extension','expansion','erweiterung','pack'])
                        save_deal(conn, name, p_new, p_old, u, False, is_exp, source_key, "", img_url)
                        
                        if id_b and not conn.execute('SELECT bgg_id FROM games WHERE bgg_id=?', (id_b,)).fetchone():
                            rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = fetch_details(id_b)
                            conn.execute('''
                                INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) 
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                            ''', (id_b, name, rat, rnk, gt, today, l_dep, o_name, wgt, minp, maxp, bestp))
                finally:
                    conn.close()
            
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
        print("Uso: python scraper_philibert.py [flash|occasion|private|preorder]")
