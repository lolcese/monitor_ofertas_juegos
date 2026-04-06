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
    'planeton_preorder': "https://www.planetongames.com/es/proximamente-192",
    'planeton_catalog': "https://www.planetongames.com/es/juegos-de-mesa-divertidos-10/s-1/idioma_del_juego-juegos_de_mesa_divertidos/en_stock-si"
}

def scrape_planeton(target='planeton'):
    base_url = URLS.get(target, URLS['planeton'])
    source_tag = target
    
    print(f"\n[PLANETON] Iniciando sección: {target.upper()}")
    today = datetime.date.today().isoformat()
    
    page = 1
    total_new = 0
    seen_urls = set()
    
    while True: # Paginación automática hasta que no haya más productos
        url = f"{base_url}?page={page}"
        print(f"-> [PLANETON] Página {page} - Cargando...")
        
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
                
                if target in ['planeton', 'planeton_catalog']:
                    if "stock" not in stock_text.lower(): continue
                else: # proximamente (preorder)
                    if "Preventa" not in stock_text and "Resérvalo" not in stock_text: continue
                
                title_tag = item.select_one('.product-title a') or item.select_one('h3.product-title a')
                if not title_tag: continue
                
                u = title_tag['href']
                if not u.startswith('http'): u = "https://www.planetongames.com" + u
                if u in seen_urls: continue
                seen_urls.add(u)
                
                raw_name = title_tag.text.strip()
                # Limpiar etiquetas y Normalizar ESPACIOS
                name = re.sub(r'\(New Arrival\)|\(Preorder\)|PREVENTA|RESERVALO|ver fecha', '', raw_name, flags=re.I).strip()
                name = re.sub(NOISE_RE, '', name, flags=re.I).strip()
                name = " ".join(name.split()) # Quitar espacios dobles/triples
                
                if any(k.lower() in name.lower() for k in IGNORE_KEYWORDS): continue

                # 1. Comprobar si ya conocemos este deal para no perder tiempo
                conn = get_db_connection()
                try:
                    # Si ya está en deals con la fecha de hoy, saltar
                    is_done = conn.execute("SELECT 1 FROM deals WHERE item_name=? AND date_found=? AND deal_source=?", (name, today, source_tag)).fetchone()
                    if is_done: continue

                    # 2. CACHÉ / IGNORED CHECK DE BGG
                    cached = conn.execute('SELECT bgg_id, confidence FROM bgg_mapping WHERE item_name=?', (name,)).fetchone()
                    if cached and cached[0] == "IGNORED":
                        continue

                    # 3. Deep Category Check solo para nombres nuevos
                    is_filtered = False
                    if not cached:
                        try:
                            # Entramos al detalle del producto para ver el breadcrumb
                            res_p = requests.get(u, headers=HEADERS_GENERIC, timeout=10)
                            if res_p.status_code == 200:
                                p_soup = BeautifulSoup(res_p.content, 'html.parser')
                                bc = p_soup.select_one('.breadcrumb')
                                if bc:
                                    bc_text = bc.text.lower()
                                    if any(kw in bc_text for kw in ['rol', 'merchandise', 'accesorios', 'miniaturas', 'fundas', 'figuras', 'revistas', 'modelismo', 'pinturas']):
                                        is_filtered = True
                                        print(f"      [!] Filtrado por categoría: {bc.text.strip()}")
                                        with conn:
                                            conn.execute('INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)', (name, 'IGNORED', 100, today))
                        except: pass
                    
                    if is_filtered: continue

                    # 4. Obtención de Precios y Fotos
                    p_new_tag = item.select_one('.price')
                    p_old_tag = item.select_one('.regular-price')
                    p_new = p_new_tag.text.strip() if p_new_tag else "0€"
                    p_old = p_old_tag.text.strip() if p_old_tag else p_new
                    
                    img_tag = item.select_one('img.product-image') or item.select_one('meta[itemprop="image"]')
                    if img_tag and img_tag.name == 'meta':
                        img_url = img_tag['content']
                    elif img_tag:
                        img_url = img_tag.get('src', '')
                    else:
                        img_url = ""
                    
                    if img_url and not img_url.startswith('http'):
                        img_url = "https://www.planetongames.com" + img_url

                    print(f"   [ITEM] [PLANETON] Procesando: {name}")
                    
                    # 5. Mapeo BGG con Lógica de Candidatos
                    id_b = None
                    conf = 0
                    
                    # OPTIMIZACION: Si ya esta mapeado en local y existe en games, saltamos búsqueda
                    if cached and str(cached[0]).isdigit():
                        g_res = conn.execute("SELECT bgg_id FROM games WHERE bgg_id = ?", (cached[0],)).fetchone()
                        if g_res:
                            id_b = cached[0]
                            conf = cached[1]
                            # print(f"      [OK] Mapeo local encontrado: {id_b}")
                    
                    if not id_b:
                        id_b, conf = fetch_bgg_id(name, u, source=source_tag)
                        # Si la confianza es baja, lo marcamos como WAITING y guardamos el candidato
                        # Pero si no hay candidatos (conf 0), lo marcamos como N/A
                        final_id = id_b if conf >= 95 else ('WAITING' if (id_b and str(id_b).isdigit()) else 'N/A')
                        cand_id = id_b if (conf < 95 and str(id_b).isdigit()) else None
                        
                        with conn:
                            conn.execute('INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search, candidate_id) VALUES (?,?,?,?,?)', (name, final_id, conf, today, cand_id))
                        id_b = final_id # Para el resto de la ejecución

                    # 6. Guardar Deal y Datos BGG (Sólo si está mapeado)
                    with conn:
                        is_exp = any(k in name.lower() for k in ['expansion','expansion','pack','ampliacion'])
                        save_deal(conn, name, p_new, p_old, u, False, is_exp, source_tag, "", img_url)
                        
                        if id_b and id_b not in ['N/A', 'IGNORED', 'WAITING']:
                            if not conn.execute('SELECT bgg_id FROM games WHERE bgg_id=?', (id_b,)).fetchone():
                                details = fetch_details(id_b)
                                if details:
                                    rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = details
                                    conn.execute('INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (id_b, name, rat, rnk, gt, today, l_dep, o_name, wgt, minp, maxp, bestp))
                    total_new += 1
                finally:
                    conn.close()
            
            time.sleep(0.1) # Pausa mínima para no estresar el servidor pero procesar rápido
                
        except Exception as e:
            print(f"[ERR] [PLANETON] Error en página {page}: {e}")
            break
            
        page += 1
        time.sleep(3) # Cooldown entre páginas

    print(f"\n[OK] [PLANETON] {target} finalizado. Total: {total_new}")

if __name__ == "__main__":
    import sys
    mode = 'planeton'
    if len(sys.argv) > 1:
        if sys.argv[1] == 'preorder': mode = 'planeton_preorder'
        elif sys.argv[1] == 'catalog': mode = 'planeton_catalog'
    scrape_planeton(mode)
