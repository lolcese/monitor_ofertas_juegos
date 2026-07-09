import sys
import datetime
import requests
import time
import re
import urllib.request
from bs4 import BeautifulSoup
from monitor_core import (
    get_db_connection, init_db, fetch_bgg_id, fetch_details, 
    save_deal, NOISE_RE, IGNORE_KEYWORDS, HEADERS_GENERIC,
    update_last_run
)

SITE_NAME = 'Zatu Games'
SOURCES = {
    'sale': "https://zatu.com/collections/board-games-sale-1",
    'outlet': "https://zatu.com/collections/outlet-store?filter.p.m.custom.type=Board+Games"
}

def scrape_zatu(source_key):
    if source_key not in SOURCES:
        print(f"Fuente desconocida: {source_key}")
        return

    url_base = SOURCES[source_key]
    today = datetime.date.today().isoformat()
    source_tag = f"zatu_{source_key}"
    
    print(f"\n[ZATU] Iniciando sección: {source_key.upper()}")
    
    init_db()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('DELETE FROM deals WHERE date_found=? AND deal_source=?', (today, source_tag))
    finally:
        conn.close()

    p = 1
    max_pages = 500
    seen = set()
    while p < max_pages:
        separator = "&" if "?" in url_base else "?"
        url = f"{url_base}{separator}page={p}"
        print(f"-> [ZATU] Página {p} - Cargando...")
        try:
            req = urllib.request.Request(url, headers=HEADERS_GENERIC)
            with urllib.request.urlopen(req, timeout=15) as res:
                if res.status != 200: break
                html_content = res.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # DETECTAR FIN DE PAGINACIÓN (Zatu devuelve cards vacías/ocultas al final)
            if "No products match those filters" in soup.get_text():
                print(f"[ZATU] Fin de catálogo detectado en página {p}.")
                break

            items = soup.select('.product-card')
            if not items: break
                
            found_new = False
            for item in items:
                a_tag = item.select_one('.product-card__title a')
                if not a_tag: continue
                
                u = "https://zatu.com" + a_tag['href']
                if u in seen: continue
                seen.add(u)
                
                name = a_tag.text.strip()
                
                # LIMPIEZA DE RUIDO
                name = re.sub(r'\(Clearance\)|\(Last Chance\)|\(New Arrival\)|\(Preorder\)|\*?\b[AB] Grade\b\*?', '', name, flags=re.I).strip()
                
                # FILTRO DE PALABRAS IGNORADAS
                if any(k.lower() in name.lower() for k in IGNORE_KEYWORDS) or \
                   any(k.lower() in name.lower() for k in ['Zatu Dice', 'Tote Bag', 'Zed Plush', 'Zed Pin', 'Playing Cards', 'Puzzle', '500pc', '1000pc', 'Accessories']):
                    continue
                
                print(f"   [ITEM] [ZATU] Procesando: {name}")
                found_new = True
                
                # Precios
                p_new_tag = item.select_one('.f-price-item--sale')
                p_old_tag = item.select_one('.f-price-item--regular s')
                
                # Zatu uses £, but we'll store it as is for report_generator to handle
                p_new = p_new_tag.text.strip() if p_new_tag else "0£"
                p_old = p_old_tag.text.strip() if p_old_tag else p_new
                
                # Limpiar texto extra en p_old (a veces dice "RRP: £XX.XX")
                p_old_search = re.search(r'£\s*\d+[.,]\d+', p_old)
                p_old = p_old_search.group(0) if p_old_search else p_new

                # Descontar el 20% de VAT (impuesto del Reino Unido) para pedidos internacionales
                def remove_vat(price_str):
                    match = re.search(r'\d+(?:\.\d+)?', price_str.replace(',', '.'))
                    if match:
                        val = float(match.group(0))
                        val_no_vat = val / 1.20
                        return f"£{val_no_vat:.2f}"
                    return price_str

                p_new = remove_vat(p_new)
                p_old = remove_vat(p_old)
                
                img_tag = item.select_one('.product-card__image img')
                img_url = ""
                if img_tag:
                    img_url = img_tag.get('src') or img_tag.get('srcset')
                    if img_url and img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    if ' ' in img_url: # srcset case
                        img_url = img_url.split(' ')[0]
                    
                    # Shopify Optimization: Request a smaller version (200px)
                    if 'cdn.shopify.com' in img_url or '/cdn/shop/' in img_url:
                        if '?' in img_url:
                            img_url = re.sub(r'width=\d+', 'width=200', img_url)
                            if 'width=' not in img_url:
                                img_url += '&width=200'
                        else:
                            img_url += '?width=200'

                # 5. Mapeo BGG - OPTIMIZACION
                id_b = None
                conf = 0
                is_final = False
                
                conn_c = get_db_connection()
                try:
                    m_res = conn_c.execute("SELECT bgg_id, confidence, candidate_id FROM bgg_mapping WHERE item_name = ?", (name,)).fetchone()
                    if m_res:
                        bid_c, conf_c, cand_c = m_res
                        if bid_c in ['WAITING', 'IGNORED'] or conf_c == 100:
                            id_b, conf = bid_c, conf_c
                            is_final = True
                        elif str(bid_c).isdigit():
                            g_res = conn_c.execute("SELECT bgg_id FROM games WHERE bgg_id = ?", (bid_c,)).fetchone()
                            if g_res: id_b, conf = bid_c, conf_c
                        elif cand_c:
                            id_b, conf = (cand_c, conf_c)
                finally: conn_c.close()

                if not id_b and not is_final:
                    id_b, conf = fetch_bgg_id(name, u, source=source_tag)
                    if id_b and str(id_b).isdigit() and conf >= 95:
                        fetch_details(id_b)

                # Clasificación Final
                if not is_final:
                    if id_b in ['WAITING', 'IGNORED']:
                        final_id = id_b
                    else:
                        final_id = id_b if (conf >= 95 and str(id_b).isdigit()) else 'N/A'
                    
                    cand_id = id_b if (conf < 95 and str(id_b).isdigit()) else None
                    
                    conn_u = get_db_connection()
                    try:
                        with conn_u:
                            conn_u.execute('INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search, candidate_id) VALUES (?,?,?,?,?)', (name, final_id, conf, today, cand_id))
                    finally: conn_u.close()
                    id_b = final_id

                if id_b in ["IGNORED", "WAITING"]: continue

                conn = get_db_connection()
                try:
                    with conn:
                        is_exp = any(k in name.lower() for k in ['extension','expansion','erweiterung','pack'])
                        save_deal(conn, name, p_new, p_old, u, False, is_exp, source_tag, "", img_url)
                        
                        if id_b and not conn.execute('SELECT bgg_id FROM games WHERE bgg_id=?', (id_b,)).fetchone():
                            rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = fetch_details(id_b)
                            conn.execute('''
                                INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) 
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                            ''', (id_b, name, rat, rnk, gt, today, l_dep, o_name, wgt, minp, maxp, bestp))
                finally:
                    conn.close()
            
            p += 1
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            break

    # Guardar registro de la corrida exitosa
    update_last_run(source_tag)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        scrape_zatu(sys.argv[1])
    else:
        scrape_zatu('sale')
