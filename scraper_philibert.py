import sys
import datetime
import requests
import time
import re
from bs4 import BeautifulSoup
from monitor_core import (
    get_db_connection, init_db, fetch_bgg_id, fetch_details, 
    HEADERS_PHILI, save_deal, NOISE_RE, IGNORE_KEYWORDS, COOKIE
)

# Configuración específica de Philibert
# Los precios se muestran tal cual aparecen en la web (con la cookie de sesión activa).
REMOVE_FRENCH_VAT = False
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

    # Las ventas privadas requieren cookie de sesión para mostrar precios correctos.
    # Sin cookie, Philibert muestra los precios normales (sin descuento), lo que no es útil.
    if source_key == 'private' and not COOKIE:
        print(f"[PHILIBERT] AVISO: Se omite 'private' porque no hay cookie de sesión configurada.")
        print(f"            Sin cookie, los precios de ventas privadas son incorrectos.")
        print(f"            Configurá PHILIBERT_COOKIE en el archivo .env para habilitarlas.")
        return

    url_base = SOURCES[source_key]
    today = datetime.date.today().isoformat()
    
    print(f"\n[PHILIBERT] Iniciando sección: {source_key.upper()}")
    if COOKIE:
        print(f"[PHILIBERT] Cookie activa: precios tal cual se muestran en la web.")
    else:
        print(f"[PHILIBERT] Sin cookie: precios con IVA incluido.")
    
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
        
        print(f"-> [PHILIBERT] Página {p} - Cargando...")
        try:
            res = requests.get(url, headers=HEADERS_PHILI, timeout=15)
            if res.status_code != 200: break
            
            soup = BeautifulSoup(res.content, 'html.parser')
            items = soup.select('.product-card')
            if not items: break
                
            found_new = False
            for item in items:
                a_tag = item.select_one('.product-card__title')
                if not a_tag: continue
                u = a_tag['href']
                if u.startswith('/'):
                    u = "https://www.philibertnet.com" + u
                    
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
                                        cat_display = bc.text.replace('\n', ' ').strip().split('/')[-1].strip()
                                        print(f"      [FILTER] Philibert Filtro Categoría: {cat_display}")
                                        with conn_id:
                                            conn_id.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)", (name, 'IGNORED', 100, today))
                        except: pass
                finally:
                    conn_id.close()
                
                if is_rpg: continue

                if u in seen: continue
                seen.add(u)
                found_new = True
                
                print(f"   [ITEM] Philibert Procesando: {name}")
                
                p_new_tag = item.select_one('.product-card__price')
                p_old_tag = item.select_one('.product-card__price--old')
                
                # Fallback if both are the same or one is missing
                p_new = p_new_tag.text.strip() if p_new_tag else "0€"
                p_old = p_old_tag.text.strip() if p_old_tag else p_new
                
                if REMOVE_FRENCH_VAT:
                    try:
                        vn = float(p_new.replace('€', '').replace(',', '.').strip())
                        vo = float(p_old.replace('€', '').replace(',', '.').strip())
                        p_new = f"{vn / 1.20:.2f} €".replace('.', ',')
                        p_old = f"{vo / 1.20:.2f} €".replace('.', ',')
                    except:
                        pass
                
                img_tag = item.select_one('img.product-card__thumb')
                img_url = img_tag['src'] if img_tag else ""

                # 5. Mapeo BGG - OPTIMIZACION TOTAL & RESPETO A MANUALES
                id_b = None
                conf = 0
                is_final = False
                
                conn_c = get_db_connection()
                try:
                    m_res = conn_c.execute("SELECT bgg_id, confidence, candidate_id FROM bgg_mapping WHERE item_name = ?", (name,)).fetchone()
                    if m_res:
                        bid_c, conf_c, cand_c = m_res
                        # 1. Si es WAITING, IGNORED o MANUAL (100%), lo usamos tal cual y marcamos como final
                        if bid_c in ['WAITING', 'IGNORED'] or conf_c == 100:
                            id_b, conf = bid_c, conf_c
                            is_final = True
                        # 2. Si es un éxito automatizado previo (ID real + datos descargados)
                        elif str(bid_c).isdigit():
                            g_res = conn_c.execute("SELECT bgg_id FROM games WHERE bgg_id = ?", (bid_c,)).fetchone()
                            if g_res: id_b, conf = bid_c, conf_c
                        # 3. Sugerencia previa
                        elif cand_c:
                            id_b, conf = (cand_c, conf_c)
                finally: conn_c.close()

                if not id_b and not is_final:
                    id_b, conf = fetch_bgg_id(name, u, source=source_key)
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
