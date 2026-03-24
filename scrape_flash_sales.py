import datetime
import requests
import re
from bs4 import BeautifulSoup
from philibert_core import (
    get_db_connection, init_db, fetch_bgg_id, fetch_details, 
    download_image, HEADERS, is_philibert_excluded
)

def scrape_flash_sales():
    init_db()
    today = datetime.date.today().isoformat()
    # Limpiamos antes de empezar el día
    with get_db_connection() as conn:
        conn.execute('DELETE FROM deals WHERE date_found=? AND deal_source="flash"', (today,))
        conn.commit()

    url = "https://www.philibertnet.com/fr/flash-sales"
    p = 1; seen = set()
    while True:
        target_url = url if p == 1 else f"{url}?p={p}"
        try:
            res = requests.get(target_url, headers=HEADERS, timeout=15)
            if res.status_code != 200: break
            soup = BeautifulSoup(res.content, 'html.parser')
            items = soup.find_all('li', class_='ajax_block_product')
            if not items or all(li.find('p', class_='s_title_block').find('a')['href'] in seen for li in items): break
            
            for item in items:
                a = item.find('p', class_='s_title_block').find('a')
                u = a['href']; name = a.text.strip(); seen.add(u)
                print(f"[{p}] Procesando Flash: {name}...")
                
                # Pre-filtros rápidos
                if any(k in name.lower() for k in ['peinture', 'citadel', 'warhammer']): continue

                p_new = item.find('span', class_='price').text.strip()
                p_old = item.find('span', class_='old-price').text.strip() if item.find('span', class_='old-price') else "0€"
                is_acc = any(k.lower() in name.lower() for k in ['rangement','organizer','sleeves','tapis','mat','token','card holder'])
                
                # Image
                img_tag = item.find('a', class_='product_img_link').find('img') if item.find('a', class_='product_img_link') else None
                img_url = img_tag['src'] if img_tag else ""
                p_id_match = re.search(r'/(\d+)-', img_url)
                p_id = p_id_match.group(1) if p_id_match else name.replace(" ","_")
                img_local = download_image(img_url, p_id)

                if is_acc:
                    with get_db_connection() as conn:
                        conn.execute('INSERT OR REPLACE INTO deals (philibert_name, price, old_price, url, date_found, is_accessory, is_expansion, deal_source, image_local) VALUES (?,?,?,?,?,?,?,?,?)', (name, p_new, p_old, u, today, 1, 0, 'flash', img_local))
                    continue

                # Cache check (7 días)
                with get_db_connection() as conn:
                    cached = conn.execute('''
                        SELECT bgg_id, confidence FROM bgg_mapping 
                        WHERE philibert_name=? AND (confidence >= 95 OR bgg_id = 'IGNORED' OR last_search >= ?)
                    ''', (name, (datetime.date.today() - datetime.timedelta(days=7)).isoformat())).fetchone()
                
                if cached:
                    id_b, conf, real_n = cached[0], cached[1], name
                else:
                    id_b, conf, real_n = fetch_bgg_id(name, u, source='flash')
                    if not id_b: continue
                    with get_db_connection() as conn:
                        conn.execute('INSERT OR REPLACE INTO bgg_mapping (philibert_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)', (name, id_b, conf, today))
                
                if id_b == "IGNORED": continue

                with get_db_connection() as conn:
                    conn.execute('INSERT OR REPLACE INTO deals (philibert_name, price, old_price, url, date_found, is_accessory, is_expansion, deal_source, image_local) VALUES (?,?,?,?,?,?,?,?,?)', (name, p_new, p_old, u, today, 0, any(k in name.lower() for k in ['extens','expans','pack']), 'flash', img_local))
                    if id_b and not conn.execute('SELECT bgg_id FROM games WHERE bgg_id=?', (id_b,)).fetchone():
                        rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = fetch_details(id_b)
                        conn.execute('INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (id_b, real_n, rat, rnk, gt, today, l_dep, o_name, wgt, minp, maxp, bestp))
                conn.commit()
            p += 1
        except: break

if __name__ == "__main__":
    scrape_flash_sales()
