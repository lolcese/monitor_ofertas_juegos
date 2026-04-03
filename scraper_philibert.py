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
    
    print(f"\n🚀 [PHILIBERT] Iniciando sección: {source_key.upper()}")
    
    init_db()
    
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('DELETE FROM deals WHERE date_found=? AND deal_source=?', (today, source_key))
    finally:
        conn.close()

    p = 1
    seen = set()
    while p < 15:
        if p == 1:
            url = url_base
        else:
            url = f"{url_base}?p={p}"
        
        print(f"▶️ [PHILIBERT] Página {p} - Cargando...")
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
                
                # FILTRO DE PALABRAS IGNORADAS
                if any(k.lower() in name.lower() for k in IGNORE_KEYWORDS):
                    continue
                
                # FILTRO DE CATEGORÍA & CACHÉ DE IGNORADOS (OPTIMIZADO)
                conn_id = get_db_connection()
                is_rpg = False
                try:
                    exists = conn_id.execute("SELECT bgg_id FROM bgg_mapping WHERE item_name=?", (name,)).fetchone()
                    
                    if exists and exists[0] == 'IGNORED':
                        continue
                        
                    if not exists:
                        # Solo entramos al detalle si no lo conocemos
                        try:
                            res_p = requests.get(u, headers=HEADERS_PHILI, timeout=8)
                            if res_p.status_code == 200:
                                p_soup = BeautifulSoup(res_p.content, 'html.parser')
                                bc = p_soup.select_one('.breadcrumb')
                                if bc:
                                    text = bc.text.lower()
                                    # Palabras clave de categorías que NO son juegos de mesa
                                    if any(kw in text for kw in ['jeux de rôle', 'wargames de figurines', 'accessoires', 'peinture', 'modélisme', 'pinceaux', 'scénographie', 'terrains']):
                                        is_rpg = True
                                        print(f"      🚫 [PHILIBERT] Filtro Categoría: {bc.text.strip().split('>')[-1].strip()}")
                                        with conn_id:
                                            conn_id.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)", (name, 'IGNORED', 100, today))
                        except: pass
                finally:
                    conn_id.close()
                
                if is_rpg: continue

                if u in seen: continue
                seen.add(u)
                found_new = True

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

                # 5. Mapeo BGG - OPTIMIZACION TOTAL
                id_b = None
                conf = 0
                
                # Usamos una sola conexión para la caché
                conn_c = get_db_connection()
                try:
                    m_res = conn_c.execute("SELECT bgg_id, confidence, candidate_id FROM bgg_mapping WHERE item_name = ?", (name,)).fetchone()
                    if m_res:
                        bid_c, conf_c, cand_c = m_res
                        # Si ya tenemos ID real y los datos en 'games', saltamos TODO
                        if str(bid_c).isdigit():
                            g_res = conn_c.execute("SELECT bgg_id FROM games WHERE bgg_id = ?", (bid_c,)).fetchone()
                            if g_res:
                                id_b, conf = bid_c, conf_c
                                # log(f"      [OK] Mapeado Philibert local: {id_b}")
                        
                        # Si no tenemos ID real pero tenemos un candidato, lo mantenemos sin buscar
                        if not id_b and cand_c:
                            id_b, conf = (cand_c, conf_c) if (bid_c == 'WAITING' or bid_c == 'N/A') else (bid_c, conf_c)
                finally: conn_c.close()

                if not id_b:
                    id_b, conf = fetch_bgg_id(name, u, source=source_key)
                    # Bajamos detalles solo si hay un match firme
                    if id_b and str(id_b).isdigit() and conf >= 95:
                        fetch_details(id_b)

                # Clasificacion Segura
                final_id = id_b if (conf >= 95 and str(id_b).isdigit()) else 'WAITING'
                cand_id = id_b if (conf < 95 and str(id_b).isdigit()) else None
                
                # Actualizar Mapeo
                conn_u = get_db_connection()
                try:
                    with conn_u:
                        conn_u.execute('INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search, candidate_id) VALUES (?,?,?,?,?)', (name, final_id, conf, today, cand_id))
                finally: conn_u.close()

                if id_b in ["IGNORED", "WAITING"]: continue

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
