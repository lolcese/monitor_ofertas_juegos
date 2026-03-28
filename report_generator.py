import sqlite3
import os
import datetime
import shutil
import time
import re
from monitor_core import BGG_CACHE_DB, IMG_DIR, init_db, fetch_details, download_image, get_db_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')
REPORT_PATH = os.path.join(PUBLIC_DIR, 'index.html')
IMAGE_DEST_DIR = os.path.join(PUBLIC_DIR, 'assets', 'images')

LANG_MAPPING = {
    "No necessary in-game text": "Sin",
    "Some necessary text - easily memorized or small crib sheet": "Baja",
    "Moderate in-game text - needs crib sheet or paste ups": "Moderada",
    "Extensive use of text - massive conversion needed to be playable": "Alta",
    "Unplayable in another language": "Injugable"
}

def color_weight(w):
    try:
        wf = float(w)
        if wf <= 1.8: return "#27ae60"
        if wf <= 2.8: return "#2ecc71"
        if wf <= 3.6: return "#f39c12"
        return "#e74c3c"
    except: return "#7f8c8d"

def color_lang(dep):
    dep_low = (dep or "").lower()
    if dep_low == "sin": return "#27ae60"
    if dep_low == "baja": return "#2980b9"
    if dep_low == "moderada": return "#f39c12"
    if dep_low in ["alta", "injugable"]: return "#e74c3c"
    return "#7f8c8d"

def ensure_all_games_fetched():
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT m.bgg_id, m.item_name FROM bgg_mapping m JOIN deals d ON m.item_name = d.item_name LEFT JOIN games g ON m.bgg_id = g.bgg_id WHERE (g.bgg_id IS NULL OR g.original_name = 'Unknown') AND m.confidence >= 95 AND m.bgg_id != 'IGNORED'")
        missing_bgg = cursor.fetchall()
        for b_id, item_name in missing_bgg:
            rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = fetch_details(b_id)
            with conn:
                cursor.execute('INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (b_id, item_name, rat, rnk, gt, datetime.date.today().isoformat(), l_dep, o_name, wgt, minp, maxp, bestp))
        
        # Sincronizar campo image_local si falta
        cursor.execute("SELECT d.item_name, d.deal_source FROM deals d WHERE (d.image_local IS NULL OR d.image_local = '')")
        for iname, source in cursor.fetchall():
            cname = re.sub(r'[^a-zA-Z0-9_\-]', '_', iname).lower()
            if os.path.exists(os.path.join(IMG_DIR, f"{cname}.jpg")):
                with conn:
                    cursor.execute("UPDATE deals SET image_local = ? WHERE item_name = ? AND deal_source = ?", (f"{cname}.jpg", iname, source))
    finally:
        conn.close()

def sync_images_to_public():
    """Copia todas las imágenes de la carpeta assets central a la carpeta public/assets para el reporte."""
    os.makedirs(IMAGE_DEST_DIR, exist_ok=True)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT image_local FROM deals WHERE image_local IS NOT NULL AND image_local != ''")
        imgs = [r[0] for r in cursor.fetchall()]
        
        print(f"Sincronizando {len(imgs)} imágenes a la carpeta pública...")
        for img in imgs:
            src = os.path.join(IMG_DIR, img)
            dst = os.path.join(IMAGE_DEST_DIR, img)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                except: pass
    finally:
        conn.close()

def generate_report():
    ensure_all_games_fetched()
    sync_images_to_public()
    
    conn = get_db_connection()
    try:
        c = conn.cursor()
        query = """
        SELECT 
            d.item_name, d.price, d.old_price, d.url, d.deal_source, 
            IFNULL(g.name, d.item_name) as bgg_name, IFNULL(m.bgg_id, 'N/A') as bgg_id, 
            IFNULL(g.rating, 'N/A') as rating, IFNULL(g.rank, '999999') as rank, 
            d.is_accessory, d.is_expansion, IFNULL(g.language_dependency, '-') as language_dependency, 
            IFNULL(g.original_name, d.item_name) as original_name, 
            IFNULL(g.type, 'UNKNOWN') as bgg_type, IFNULL(g.weight, 'N/A') as weight, 
            IFNULL(g.min_players, 0) as min_p, IFNULL(g.max_players, 0) as max_p, 
            IFNULL(g.best_players, '-') as best_p, 
            d.image_local, d.date_found
        FROM deals d
        LEFT JOIN bgg_mapping m ON d.item_name = m.item_name
        LEFT JOIN games g ON m.bgg_id = g.bgg_id
        WHERE d.date_found = (SELECT MAX(date_found) FROM deals d2 WHERE d2.deal_source = d.deal_source)
        AND d.date_found >= date('now', '-7 days')
        AND (m.bgg_id IS NULL OR m.bgg_id != 'IGNORED')
        AND d.is_accessory = 0
        ORDER BY CASE WHEN g.rank = '999999' OR g.rank = 'N/A' OR g.rank IS NULL THEN 1 ELSE 0 END, CAST(g.rank AS INTEGER) ASC
        """
        rows = c.execute(query).fetchall()
        st_counts = {'Philibert': 0, 'Miniature Market': 0}
        t_counts = {}
        for r in rows:
            src = str(r[4]).lower()
            if any(k in src for k in ['miniature', 'mm_', 'deals']):
                st_counts['Miniature Market'] += 1
                sk = 'mm_clearance' if 'clearance' in src else ('mm_backdoor' if 'backrooms' in src or 'backdoor' in src else 'mm_deals')
                t_counts[sk] = t_counts.get(sk, 0) + 1
            else:
                st_counts['Philibert'] += 1
                t_counts[src] = t_counts.get(src, 0) + 1
    finally:
        conn.close()
                
    phili_lbls = {'flash': 'FLASH', 'occasion': 'OCCASION', 'private': 'PRIVÉE'}
    mm_lbls = {'mm_deals': 'MM DEALS', 'mm_backdoor': 'BACKDOOR', 'mm_clearance': 'CLEARANCE'}
    
    sum_h = '<div style="display:flex; justify-content:center; gap:20px; flex-wrap:wrap; margin-bottom:25px;">'
    
    sum_h += '<div style="background:#f8f9fa; border:1px solid #dee2e6; border-radius:12px; padding:15px; min-width:300px; text-align:center;">'
    sum_h += f'<h3 style="margin-top:0; color:#003566; font-size:1em; border-bottom:2px solid #003566; padding-bottom:5px;">FR Philibert ({st_counts["Philibert"]})</h3><div style="display:flex; justify-content:center; gap:5px; flex-wrap:wrap;">'
    for k, l in phili_lbls.items():
        cnt = t_counts.get(k, 0)
        if cnt > 0:
            sum_h += f'<span class="badge-{k}" onclick="filterByCategory(\'{l.upper()}\')" style="cursor:pointer; padding: 5px 12px; border-radius:6px; font-weight:bold; font-size:0.9em;" title="Click para filtrar">{l}: {cnt}</span>'
    sum_h += '</div></div>'
    
    sum_h += '<div style="background:#f8f9fa; border:1px solid #dee2e6; border-radius:12px; padding:15px; min-width:300px; text-align:center;">'
    sum_h += f'<h3 style="margin-top:0; color:#e67e22; font-size:1em; border-bottom:2px solid #e67e22; padding-bottom:5px;">US Miniature Market ({st_counts["Miniature Market"]})</h3><div style="display:flex; justify-content:center; gap:5px; flex-wrap:wrap;">'
    for k, l in mm_lbls.items():
        cnt = t_counts.get(k, 0)
        if cnt > 0:
            short_l = l.replace('MM ', '')
            sum_h += f'<span class="badge-{k.replace("mm_","mm-")}" onclick="filterByCategory(\'{l.upper()}\')" style="cursor:pointer; padding: 5px 12px; border-radius:6px; font-weight:bold; font-size:0.9em;" title="Click para filtrar">{short_l}: {cnt}</span>'
    sum_h += '</div></div>'
    
    sum_h += '</div><div style="text-align:center; margin-bottom:15px;"><button onclick="filterByCategory(\'\')" style="background:#6c757d; color:white; border:none; padding:5px 15px; border-radius:20px; cursor:pointer; font-weight:bold; font-size:0.85em;">Ver Todos los Resultados</button></div>'

    h_head = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><link rel="icon" type="image/png" href="assets/favicon.png"><title>Monitor de Ofertas Multitienda</title><style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f7f6; margin: 25px; color: #333; }}
    h1 {{ color: #2c3e50; text-align: center; margin-bottom: 5px; font-weight: 800; }}
    .developed-by {{ text-align: center; margin-bottom: 25px; color: #7f8c8d; font-size: 0.9em; }}
    .container {{ background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 98%; margin: auto; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th {{ background-color: #3498db; color: white; cursor: pointer; padding: 12px; text-align: left; position: sticky; top: 0; z-index: 5; }}
    th:hover {{ background-color: #2980b9; }}
    td {{ border-bottom: 1px solid #ddd; padding: 12px; vertical-align: middle; }}
    tr:hover {{ background-color: #f1f1f1; }}
    .price-new {{ font-weight: bold; color: #e74c3c; font-size: 1.1em; }}
    .price-old {{ text-decoration: line-through; color: #95a5a6; font-size: 0.85em; margin-right: 5px; }}
    .discount-badge {{ background: #e74c3c; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9em; }}
    .badge-flash {{ background: #f1c40f; color: #333; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }}
    .badge-occasion {{ background: #9b59b6; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }}
    .badge-private {{ background: #2c3e50; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }}
    .badge-mm-backdoor {{ background: #e67e22; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }}
    .badge-mm-deals {{ background: #27ae60; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }}
    .badge-mm-clearance {{ background: #c0392b; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }}
    .type-base {{ color: #2980b9; font-weight: bold; font-size: 0.85em; }}
    .type-expansion {{ color: #d35400; font-weight: bold; font-size: 0.85em; }}
    .type-accessory {{ color: #7f8c8d; font-weight: bold; font-size: 0.85em; }}
    .lang-dep {{ font-size: 0.75em; font-weight: bold; padding: 2px 5px; border-radius: 3px; color: white; display: inline-block; margin-top: 5px; }}
    .rating {{ color: #f39c12; font-weight: bold; }}
    .center {{ text-align: center; }}
    a {{ text-decoration: none; color: #3498db; }}
    a:hover {{ text-decoration: underline; }}
    .game-img {{ width: 60px; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
    .contact-btn {{ display: inline-block; background-color: #0088cc; color: white; padding: 6px 15px; border-radius: 20px; text-decoration: none; font-weight: bold; margin-bottom: 25px; transition: transform 0.2s; }}
    .contact-btn:hover {{ transform: scale(1.05); color: white; }}
    </style></head><body><div class="container"><h1>Monitor de Ofertas Multitienda</h1><div class="developed-by">Desarrollado por <b>Luis Olcese</b></div><div style="text-align:center;"><a href="https://t.me/Luis_Olcese" target="_blank" class="contact-btn">✉️ Contactar en Telegram</a></div>{sum_h}<p style="text-align:center;">Mostrando <b>{len(rows)}</b> ofertas recientemente</p><div style="margin-bottom: 20px; text-align: center;"><input type="text" id="searchInput" onkeyup="filterTable()" placeholder="🔍 Buscar nombre, categoría, fuente, idioma..." style="padding: 14px; width: 60%; border-radius: 8px; border: 1px solid #ddd; font-size: 1em;"></div><table id="offersTable"><thead><tr><th class="center">Imagen</th><th onclick="sortTable(1)">Producto</th><th onclick="sortTable(2)">Categoría</th><th onclick="sortTable(3)">Precio</th><th onclick="sortTable(4)" class="center">% Dto</th><th onclick="sortTable(5)" class="center">Fuente</th><th onclick="sortTable(6)">BGG Name</th><th onclick="sortTable(7)" class="center">Dep. idioma</th><th onclick="sortTable(8)" class="center">Peso</th><th onclick="sortTable(9)" class="center">Jugadores</th><th onclick="sortTable(10)" class="center">Rating</th><th onclick="sortTable(11)" class="center">Rank</th></tr></thead><tbody>"""
    
    h_body = ""
    plogo = '<img src="assets/Logo_Philibert.png" style="height:18px; display:block; margin: 0 auto 3px auto;">'
    mlogo = '<img src="assets/miniaturemarket_logo.jpeg" style="height:18px; display:block; margin: 0 auto 3px auto;">'
    
    for row in rows:
        p_name, p_price, p_old, p_url, p_source, b_name, b_id, b_rating, b_rank, is_acc, is_exp, l_dep, o_name, g_type, g_wgt, min_p, max_p, best_p, img_local, last_seen = row
        p_name = re.sub(r'\(Clearance\)|\(Last Chance\)| - Occasion', '', p_name, flags=re.I).strip()
        try:
            vn = float(p_price.replace('€','').replace('$','').replace(',','.').strip())
            vo = float(p_old.replace('€','').replace('$','').replace(',','.').strip()) if (p_old and p_old not in ["0€","0$"]) else vn
            disc = round((1 - vn/vo) * 100) if vo > 0 else 0
        except: disc = 0
        sl = str(p_source).lower()
        if sl == 'flash': sb = f'{plogo}<span class="badge-flash">FLASH</span>'
        elif sl == 'occasion': sb = f'{plogo}<span class="badge-occasion">OCCASION</span>'
        elif sl == 'private': sb = f'{plogo}<span class="badge-private">PRIVÉE</span>'
        elif 'clearance' in sl: sb = f'{mlogo}<span class="badge-mm-clearance">CLEARANCE</span>'
        elif 'backrooms' in sl or 'backdoor' in sl: sb = f'{mlogo}<span class="badge-mm-backdoor">BACKDOOR</span>'
        elif any(k in sl for k in ['miniature','mm_','deals']): sb = f'{mlogo}<span class="badge-mm-deals">MM DEALS</span>'
        else: sb = p_source
        cat = '<span class="type-accessory">Accesorio</span>' if is_acc else ('<span class="type-expansion">Expa</span>' if (is_exp or g_type == 'BOARDGAMEEXPANSION') else '<span class="type-base">Base</span>')
        rat = b_rating if (b_rating and b_rating != "N/A" and b_rating != "Cargando...") else "-"
        rnk = f"#{b_rank}" if (b_rank and b_rank != "999999" and b_rank != "-") else "-"
        img_h = f'<img src="assets/images/{os.path.basename(img_local)}" class="game-img">' if img_local else '<div class="game-img" style="height:60px; background:#eee;"></div>'
        h_body += f"""<tr><td class="center">{img_h}</td><td><a href="{p_url}" target="_blank">{p_name}</a></td><td>{cat}</td><td data-sort="{vn}"><span class="price-old">{p_old if (p_old and p_old not in ['0€','0$']) else ''}</span><br><span class="price-new">{p_price}</span></td><td class="center" data-sort="{disc}"><span class="discount-badge">-{disc}%</span></td><td class="center">{sb}</td><td><a href="https://boardgamegeek.com/boardgame/{b_id}" target="_blank">{o_name or b_name}</a></td><td class="center"><span class="lang-dep" style="background-color:{color_lang(LANG_MAPPING.get(l_dep, l_dep or '-'))}">{LANG_MAPPING.get(l_dep, l_dep or "-")}</span></td><td class="center"><span class="lang-dep" style="background-color:{color_weight(g_wgt)}; font-weight:bold;">{g_wgt or "N/A"}</span></td><td class="center">{f"{min_p}-{max_p}" if (min_p and min_p != max_p) else f"{min_p or '-'}"}</td><td class="center" data-sort="{rat if rat != 'Cargando...' else '0'}"><span class="rating">{rat}</span></td><td class="center" data-sort="{b_rank}"><b>{rnk if rnk != '#999999' else '-'}</b></td></tr>"""
    
    h_foot = """</tbody></table></div><script>
    var rowData = [];
    var searchTimeout;
    
    // Inicializar caché de filas al cargar
    window.onload = function() {
        var rows = document.querySelectorAll("#offersTable tbody tr");
        rows.forEach(row => {
            rowData.push({
                el: row,
                text: row.innerText.toUpperCase(),
                cells: Array.from(row.cells).map(c => c.getAttribute("data-sort") || c.textContent.trim())
            });
        });
    };

    function filterTable() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            var f = document.getElementById("searchInput").value.toUpperCase();
            rowData.forEach(item => {
                item.el.style.display = item.text.includes(f) ? "" : "none";
            });
        }, 150);
    }

    function filterByCategory(cat) {
        document.getElementById("searchInput").value = cat;
        // Sin debounce para clicks en botones de categoría
        var f = cat.toUpperCase();
        rowData.forEach(item => {
            item.el.style.display = item.text.includes(f) ? "" : "none";
        });
    }

    function sortTable(n) {
        var t = document.getElementById("offersTable");
        var b = t.tBodies[0];
        var d = t.getAttribute("sort-dir-" + n) === "asc" ? -1 : 1;
        
        // Ordenar el array de caché para mayor velocidad
        rowData.sort((a, b) => {
            var x = a.cells[n], y = b.cells[n];
            var fX = parseFloat(x), fY = parseFloat(y);
            if (!isNaN(fX) && !isNaN(fY)) return (fX - fY) * d;
            return x.localeCompare(y, undefined, {numeric: true, sensitivity: 'base'}) * d;
        });

        // Aplicar a DOM en un solo fragmento para evitar reflows continuos
        var fragment = document.createDocumentFragment();
        rowData.forEach(item => fragment.appendChild(item.el));
        b.appendChild(fragment);

        t.setAttribute("sort-dir-" + n, d === 1 ? "asc" : "desc");
    }
    </script></body></html>"""
    
    with open(REPORT_PATH, "w", encoding="utf-8") as f: f.write(h_head + h_body + h_foot)
    print(f"Reporte generado con éxito.")

if __name__ == "__main__":
    generate_report()
