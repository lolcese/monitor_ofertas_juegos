import sqlite3
import os
import datetime
import shutil
import json
import re
from monitor_core import BGG_CACHE_DB, IMG_DIR, init_db, fetch_details, download_image, get_db_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')
REPORT_PATH = os.path.join(PUBLIC_DIR, 'index.html')
PLANETON_PATH = os.path.join(PUBLIC_DIR, 'planeton.html')
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
        cursor.execute("SELECT DISTINCT m.bgg_id, m.item_name FROM bgg_mapping m JOIN deals d ON m.item_name = d.item_name LEFT JOIN games g ON m.bgg_id = g.bgg_id WHERE (g.bgg_id IS NULL OR g.original_name = 'Unknown') AND m.confidence >= 95 AND m.bgg_id NOT IN ('IGNORED', 'WAITING') AND m.bgg_id glob '[0-9]*'")
        missing_bgg = cursor.fetchall()
        for b_id, item_name in missing_bgg:
            details = fetch_details(b_id)
            if details:
                rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = details
                with conn:
                    cursor.execute('INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (b_id, item_name, rat, rnk, gt, datetime.date.today().isoformat(), l_dep, o_name, wgt, minp, maxp, bestp))
    finally:
        conn.close()

def sync_images_to_public():
    os.makedirs(IMAGE_DEST_DIR, exist_ok=True)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT image_local FROM deals WHERE image_local IS NOT NULL AND image_local != '' AND date_found >= date('now', '-7 days')")
        active_imgs = [r[0] for r in cursor.fetchall()]
        active_set = set(active_imgs)
        for img in active_imgs:
            src = os.path.join(IMG_DIR, img)
            dst = os.path.join(IMAGE_DEST_DIR, img)
            if os.path.exists(src) and (not os.path.exists(dst) or os.path.getsize(src) != os.path.getsize(dst)):
                try: shutil.copy2(src, dst)
                except: pass
        for filename in os.listdir(IMAGE_DEST_DIR):
            if filename not in active_set and filename.endswith('.jpg'):
                try: os.remove(os.path.join(IMAGE_DEST_DIR, filename))
                except: pass
        for logo in ["Logo_Philibert.png", "miniaturemarket_logo.jpeg", "planeton_logo.jpg", "favicon.png"]:
            src_l = os.path.join(BASE_DIR, "assets", logo)
            dst_l = os.path.join(PUBLIC_DIR, "assets", logo)
            os.makedirs(os.path.dirname(dst_l), exist_ok=True)
            if os.path.exists(src_l): shutil.copy2(src_l, dst_l)
    finally:
        conn.close()

def generate_report():
    ensure_all_games_fetched()
    sync_images_to_public()
    
    conn = get_db_connection()
    today_iso = datetime.date.today().isoformat()
    
    try:
        c = conn.cursor()
        query = """
        SELECT 
            d.item_name, d.price, d.old_price, d.url, d.deal_source,
            IFNULL(g.name, d.item_name) as bgg_name, IFNULL(m.bgg_id, '0') as bgg_id, 
            IFNULL(g.rating, 'N/A') as rating, IFNULL(g.rank, '999999') as rank, 
            d.is_accessory, d.is_expansion, IFNULL(g.language_dependency, '-') as language_dependency, 
            IFNULL(g.original_name, d.item_name) as original_name, IFNULL(g.type, 'UNKNOWN') as bgg_type, 
            IFNULL(g.weight, 'N/A') as weight, IFNULL(g.min_players, 0) as min_p, 
            IFNULL(g.max_players, 0) as max_p, IFNULL(g.best_players, '-') as best_p, 
            d.image_local, MAX(d.date_found) as last_seen, MAX(d.date_first_seen) as first_seen
        FROM deals d
        LEFT JOIN bgg_mapping m ON d.item_name = m.item_name
        LEFT JOIN games g ON m.bgg_id = g.bgg_id
        WHERE d.date_found >= date('now', '-7 days')
        AND (m.bgg_id IS NULL OR m.bgg_id != 'IGNORED')
        GROUP BY d.item_name
        ORDER BY CASE WHEN g.rank = '999999' OR g.rank = 'N/A' OR g.rank IS NULL THEN 1 ELSE 0 END, CAST(g.rank AS INTEGER) ASC
        """
        all_rows = c.execute(query).fetchall()
        
        def process_row(r):
            p_name, p_price, p_old, p_url, p_source, b_name, b_id, b_rat, b_rank, is_acc, is_exp, l_dep, o_name, g_type, g_wgt, min_p, max_p, best_p, img, last, first = r
            p_name_clean = re.sub(r'\(Clearance\)|\(Last Chance\)| - Occasion', '', p_name, flags=re.I).strip()
            try:
                vn = float(p_price.replace('€','').replace('$','').replace(',','.').strip())
                vo = float(p_old.replace('€','').replace('$','').replace(',','.').strip()) if (p_old and p_old not in ["0€","0$"]) else vn
                disc = round((1 - vn/vo) * 100) if vo > 0 else 0
            except: vn=0; vo=0; disc=0
            cat_l = "Accesorio" if is_acc else ("Expa" if (is_exp or g_type == 'boardgameexpansion') else "Base")
            cat_c = "type-accessory" if is_acc else ("type-expansion" if (is_exp or g_type == 'boardgameexpansion') else "type-base")
            src = str(p_source).lower()
            if 'miniature' in src or 'mm_' in src: 
                sg = "MI"; sk = 'mm_clearance' if 'clearance' in src else ('mm_backdoor' if 'backrooms' in src else ('mm_preorder' if 'preorder' in src else 'mm_deals'))
            elif 'planeton' in src: 
                sg = "PL"; sk = 'planeton_preorder' if 'preorder' in src else ('planeton_catalog' if 'catalog' in src else 'planeton')
            else: 
                sg = "PH"; sk = src if src in ['flash','occasion','private','preorder'] else 'flash'
            
            is_high = False
            try:
                rf = float(b_rat) if (b_rat != "N/A" and b_rat != "-") else 0
                bf = int(b_rank) if str(b_rank).isdigit() else 999999
                if rf >= 7.8 or (bf <= 1500 and bf > 0) or disc >= 45: is_high = True
            except: pass

            return {
                "n": p_name_clean, "p": p_price, "o": p_old, "u": p_url, "s": p_source, "sg": sg, "sk": sk,
                "bn": o_name or b_name, "bid": b_id, "rat": b_rat, "rnk": b_rank, 
                "cat_l": cat_l, "cat_c": cat_c, "ld": LANG_MAPPING.get(l_dep, l_dep or "-"), "ldc": color_lang(l_dep),
                "w": g_wgt, "wc": color_weight(g_wgt), "pl": f"{min_p}-{max_p}" if min_p != max_p else str(min_p),
                "img": os.path.basename(img) if img else "", "d": disc, "high": is_high, "new": (first == today_iso), "vn": vn
            }

        # Separar datos
        deals_data = [] # Philibert, MM, y Planeton (Solo Ofertas/Pre/Catalog no)
        catalog_planeton_data = [] # Solo Planeton (Todo)

        for r in all_rows:
            p_source = str(r[4]).lower()
            item = process_row(r)
            
            # Catálogo Planeton Completo
            if 'planeton' in p_source:
                catalog_planeton_data.append(item)
            
            # Reporte Principal (Deals)
            # Regla: Cualquier cosa de Phili/MM, o Planeton si es oferta real (disc > 0) o preorder
            if 'planeton' not in p_source:
                deals_data.append(item)
            else:
                # Incluir en el principal solo si tiene descuento real o es preventa
                if item["d"] > 0 or "preorder" in item["sk"]:
                    deals_data.append(item)

        # Generar archivos
        write_html(REPORT_PATH, deals_data, "Monitor de OFERTAS y Joyas", is_catalog=False)
        write_html(PLANETON_PATH, catalog_planeton_data, "Catálogo Completo PLANETON GAMES", is_catalog=True)

    finally:
        conn.close()

def write_html(path, data, title, is_catalog=False):
    today_iso = datetime.date.today().isoformat()
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Calcular contadores para la cabecera
    stats = {'PH': 0, 'MI': 0, 'PL': 0}
    t_counts = {}
    for it in data:
        stats[it['sg']] += 1
        t_counts[it['sk']] = t_counts.get(it['sk'], 0) + 1

    nav_btn = f'<a href="planeton.html" class="nav-extra-btn">🌍 VER CATÁLOGO PLANETON ({stats["PL"]})</a>' if not is_catalog else '<a href="index.html" class="nav-extra-btn">🏠 VOLVER A OFERTAS</a>'

    sum_h = '<div class="summary-wrapper">'
    if not is_catalog:
        # SUMARIO MULTITIENDA
        sum_h += '<div class="summary-card"><img src="assets/Logo_Philibert.png" class="sum-logo"><h3>FR Philibert</h3><div class="sum-badges">'
        for k, l in [('flash','FLASH'),('occasion','OCCASION'),('private','PRIVÉE'),('preorder','PRE-ORDER')]:
            c = t_counts.get(k, 0)
            if c > 0: sum_h += f'<span class="badge-{k}" onclick="filterBySource(\'{k}\')">{l}: {c}</span>'
        sum_h += '</div></div>'
        sum_h += '<div class="summary-card"><img src="assets/miniaturemarket_logo.jpeg" class="sum-logo"><h3>US Miniature Market</h3><div class="sum-badges">'
        for k, l in [('mm_deals','DEALS'),('mm_clearance','CLEARANCE'),('mm_backdoor','BACKROOMS'),('mm_preorder','PRE-ORDER')]:
            c = t_counts.get(k, 0)
            if c > 0: sum_h += f'<span class="badge-{k.replace("mm_","mm-")}" onclick="filterBySource(\'{k}\')">{l}: {c}</span>'
        sum_h += '</div></div>'
        sum_h += '<div class="summary-card"><img src="assets/planeton_logo.jpg" class="sum-logo"><h3>Planeton (Ofertas)</h3><div class="sum-badges">'
        c_p = t_counts.get('planeton', 0); c_p_pre = t_counts.get('planeton_preorder', 0)
        if c_p > 0: sum_h += f'<span class="badge-planeton" onclick="filterBySource(\'planeton\')">OFERTAS: {c_p}</span>'
        if c_p_pre > 0: sum_h += f'<span class="badge-mm-preorder" onclick="filterBySource(\'planeton_preorder\')">RESERVAS: {c_p_pre}</span>'
        sum_h += '</div></div>'
    else:
        # SUMARIO SOLO PLANETON
        sum_h += '<div class="summary-card" style="min-width: 50%"><img src="assets/planeton_logo.jpg" class="sum-logo"><h3>CATÁLOGO PLANETON</h3><div class="sum-badges">'
        sum_h += f'<span class="badge-planeton" style="padding:10px 20px; font-size:1em">Total Juegos en Catálogo: {len(data)}</span>'
        sum_h += '</div></div>'
    sum_h += '</div>'

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="icon" type="image/png" href="assets/favicon.png"><title>{title}</title><style>
        :root {{ --primary: #3498db; --bg: #f4f7f6; --card: #ffffff; --text: #2c3e50; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); margin: 0; padding: 20px; color: var(--text); }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        h1 {{ margin: 0 0 5px; font-weight: 800; color: #2c3e50; }}
        .subtitle {{ color: #7f8c8d; font-size: 0.9em; }}
        .nav-extra-btn {{ display: inline-block; background: #e67e22; color: white; padding: 10px 20px; border-radius: 30px; font-weight: bold; text-decoration: none; margin: 15px 0; transition: 0.3s; box-shadow: 0 4px 10px rgba(230,126,34,0.3); }}
        .nav-extra-btn:hover {{ transform: scale(1.05); background: #d35400; }}
        
        .container {{ background: var(--card); border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.08); padding: 25px; margin: auto; max-width: 1500px; }}
        .summary-wrapper {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 25px; flex-wrap: wrap; }}
        .summary-card {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 12px; padding: 15px; min-width: 250px; text-align: center; }}
        .sum-logo {{ height: 20px; margin-bottom: 10px; }}
        .sum-badges {{ display: flex; justify-content: center; gap: 5px; flex-wrap: wrap; }}
        .sum-badges span {{ padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 0.8em; cursor: pointer; color: white; }}
        
        #virtual-scroll-container {{ height: 750px; overflow-y: auto; position: relative; border-radius: 0 0 10px 10px; background: #fff; border: 1px solid #ddd; border-top: none; }}
        #virtual-scroll-content {{ position: relative; }}
        .table-header {{ display: flex; align-items: center; background: #3498db; color: white; font-weight: bold; padding: 12px 0; border-radius: 10px 10px 0 0; position: sticky; top: 0; z-index: 110; }}
        .table-header .col {{ color: white !important; font-size: 0.9em; }}
        .table-row {{ display: flex; align-items: center; border-bottom: 1px solid #f0f0f0; position: absolute; left: 0; width: 100%; box-sizing: border-box; font-size: 0.95em; background: white; }}
        .table-row:hover {{ background: #f9fbff; }}
        .col {{ padding: 0 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .col-img {{ width: 70px; text-align: center; }}
        .col-name {{ flex: 5; font-weight: 500; min-width: 200px; }}
        .col-cat {{ width: 60px; text-align: center; }}
        .col-price {{ width: 90px; text-align: right; }}
        .col-disc {{ width: 60px; text-align: center; }}
        .col-source {{ width: 110px; text-align: center; }}
        .col-bgg {{ flex: 5; color: #7f8c8d; font-size: 0.9em; min-width: 200px; }}
        .col-lang {{ width: 100px; text-align: center; }}
        .col-weight {{ width: 50px; text-align: center; font-weight: bold; }}
        .col-rating {{ width: 60px; text-align: center; font-weight: bold; color: #f39c12; }}
        .col-rank {{ width: 60px; text-align: center; font-weight: bold; }}
        
        .game-img {{ height: 50px; border-radius: 5px; }}
        .badge {{ display: inline-block; padding: 2px 6px; border-radius: 4px; color: white; font-size: 0.65em; font-weight: bold; vertical-align: middle; margin-right: 3px; }}
        .badge-new {{ background: #27ae60; animation: pulse 2s infinite; border-radius: 20px; }}
        .badge-high {{ background: #f39c12; border-radius: 50%; padding: 2px 4px; }}
        .badge-flash {{ background: #f1c40f; color: black; }} .badge-occasion {{ background: #9b59b6; }} .badge-private {{ background: #2c3e50; }}
        .badge-preorder, .badge-mm-preorder, .badge-planeton-preorder {{ background: #16a085; }}
        .badge-mm-deals, .badge-mm-clearance {{ background: #27ae60; }}
        .badge-mm-backdoor {{ background: #e67e22; }}
        .badge-planeton, .badge-planeton-catalog {{ background: #c0392b; }}
        @keyframes pulse {{ 0%{{opacity:1}} 50%{{opacity:0.8}} 100%{{opacity:1}} }}
        
        .lang-badge {{ font-size: 0.75em; font-weight: bold; padding: 2px 5px; border-radius: 4px; color: white; }}
        .price-new {{ color: #e74c3c; font-weight: bold; }} .price-old {{ text-decoration: line-through; color: #95a5a6; font-size: 0.8em; display: block; }}
        .search-area {{ display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 20px; position: sticky; top: 0; background: white; padding: 15px; z-index: 100; border-bottom: 1px solid #eee; }}
        #searchInput {{ width: 60%; padding: 10px 20px; border-radius: 30px; border: 1px solid #ddd; outline: none; }}
        .filter-buttons button {{ background: #eee; border: none; padding: 6px 15px; border-radius: 20px; cursor: pointer; font-weight: bold; font-size: 0.8em; }}
        .filter-buttons button.active {{ background: var(--primary); color: white; }}
        a {{ text-decoration: none; color: inherit; }} a:hover {{ color: var(--primary); }}

        /* Floating Back to Top Button */
        .back-to-top {{ position: fixed; bottom: 30px; right: 30px; width: 50px; height: 50px; background: var(--primary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; cursor: pointer; border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.2); z-index: 1000; transition: 0.3s; }}
        .back-to-top:hover {{ transform: scale(1.1); background: #2980b9; }}
    </style></head><body>
    <div class="header">
        <h1>{title}</h1>
        <div class="subtitle">Generado el {now_str} • {len(data)} juegos monitoreados</div>
        {nav_btn}
    </div>
    <button class="back-to-top" onclick="window.scrollToTop()" title="Volver arriba">↑</button>
    <div class="container">
        {sum_h}
        <div class="search-area">
            <input type="text" id="searchInput" placeholder="🔍 Buscar..." autocomplete="off">
            <div class="filter-buttons">
                <button id="btn-all" onclick="clearFilters()" class="active">Ver Todos</button>
                <button id="btn-new" onclick="filterType('new')">✨ NUEVOS</button>
                <button id="btn-high" onclick="filterType('high')">⭐ JOYAS</button>
                <button id="btn-pre" onclick="filterType('pre')">🚀 PREVENTAS</button>
            </div>
        </div>
        <div class="table-header">
            <div class="col col-img">Img</div>
            <div class="col col-name" onclick="resort('n')" style="cursor:pointer">Producto ⇅</div>
            <div class="col col-cat">Cat</div>
            <div class="col col-price" onclick="resort('vn')" style="cursor:pointer">Precio ⇅</div>
            <div class="col col-disc" onclick="resort('d')" style="cursor:pointer">% ⇅</div>
            <div class="col col-source">Fuente</div>
            <div class="col col-bgg" onclick="resort('bn')" style="cursor:pointer">Nombre BGG ⇅</div>
            <div class="col col-lang">Dep. Idioma</div>
            <div class="col col-weight">Peso</div>
            <div class="col col-rating" onclick="resort('rat')" style="cursor:pointer">Rat ⇅</div>
            <div class="col col-rank" onclick="resort('rnk')" style="cursor:pointer">Rank ⇅</div>
        </div>
        <div id="virtual-scroll-container"><div id="virtual-scroll-content"></div></div>
    </div>
    <script>
        const allOffers = {json.dumps(data)};
        let filteredOffers = [...allOffers];
        let sortState = {{ key: 'rnk', dir: 1 }};
        const isCatalogMode = {'true' if is_catalog else 'false'};
        const container = document.getElementById('virtual-scroll-container');
        const content = document.getElementById('virtual-scroll-content');
        const ROW_HEIGHT = 75; const VISIBLE_COUNT = 20;

        function render() {{
            const st = container.scrollTop;
            const start = Math.max(0, Math.floor(st / ROW_HEIGHT) - 5);
            const end = Math.min(filteredOffers.length, start + VISIBLE_COUNT + 10);
            content.style.height = (filteredOffers.length * ROW_HEIGHT) + 'px';
            let h = '';
            for (let i = start; i < end; i++) {{
                const it = filteredOffers[i];
                const logoImg = it.sg == 'PH' ? 'Logo_Philibert.png' : (it.sg == 'MI' ? 'miniaturemarket_logo.jpeg' : 'planeton_logo.jpg');
                const logoHtml = `<img src="assets/${{logoImg}}" style="height:14px;display:block;margin:0 auto 2px;">`;
                
                let labelText = "";
                if (it.sk === "planeton_preorder") labelText = "RESERVA";
                else if (it.sk === "planeton" || it.sk === "planeton_catalog") labelText = "OFERTA";
                else labelText = it.sk.toUpperCase().replace("MM_", "").replace("MM-", "");
                
                h += `<div class="table-row" style="top: ${{i * ROW_HEIGHT}}px; height: ${{ROW_HEIGHT}}px;">
                    <div class="col col-img">${{it.img ? `<img src="assets/images/${{it.img}}" class="game-img">` : ''}}</div>
                    <div class="col col-name"><a href="${{it.u}}" target="_blank">${{it.new ? '<span class="badge badge-new">NUEVO</span>' : ''}}${{it.high ? '<span class="badge badge-high">⭐</span>' : ''}}${{it.n}}</a></div>
                    <div class="col col-cat" style="font-size:0.7em">${{it.cat_l}}</div>
                    <div class="col col-price"><span class="price-old">${{it.o || ''}}</span><span class="price-new">${{it.p}}</span></div>
                    <div class="col col-disc"><span style="background:#e74c3c;color:white;padding:2px 5px;border-radius:20px;font-size:0.8em">-${{it.d}}%</span></div>
                    <div class="col col-source">${{logoHtml}}<span class="badge-${{it.sk.replace('_','-')}}" style="font-size:0.6em;padding:1px 4px;border-radius:3px;color:white">${{labelText}}</span></div>
                    <div class="col col-bgg"><a href="https://boardgamegeek.com/boardgame/${{it.bid}}" target="_blank">${{it.bn}}</a></div>
                    <div class="col col-lang"><span class="lang-badge" style="background:${{it.ldc}}">${{it.ld}}</span></div>
                    <div class="col col-weight"><span class="lang-badge" style="background:${{it.wc}}">${{it.w}}</span></div>
                    <div class="col col-rating">${{it.rat}}</div>
                    <div class="col col-rank">#${{it.rnk != '999999' ? it.rnk : '-'}}</div>
                </div>`;
            }}
            content.innerHTML = h;
        }}
        window.scrollToTop = function() {{ container.scrollTop = 0; render(); }};
        container.addEventListener('scroll', render);
        document.getElementById('searchInput').addEventListener('input', (e) => {{
            const t = e.target.value.toLowerCase();
            filteredOffers = allOffers.filter(o => o.n.toLowerCase().includes(t) || o.bn.toLowerCase().includes(t) || o.sk.toLowerCase().includes(t));
            container.scrollTop = 0; render();
        }});
        function resort(k) {{
            if (sortState.key === k) sortState.dir *= -1; else {{ sortState.key = k; sortState.dir = 1; }}
            filteredOffers.sort((a,b) => {{
                let vA = a[k], vB = b[k];
                if (['rnk', 'rat', 'vn', 'd'].includes(k)) {{
                    vA = parseFloat(String(vA).replace('#','')) || (sortState.dir===1?999999:-999999);
                    vB = parseFloat(String(vB).replace('#','')) || (sortState.dir===1?999999:-999999);
                }} else {{ vA = String(vA).toLowerCase(); vB = String(vB).toLowerCase(); }}
                return vA < vB ? -1*sortState.dir : (vA > vB ? 1*sortState.dir : 0);
            }});
            container.scrollTop = 0; render();
        }}
        function filterType(t) {{
            document.querySelectorAll('.filter-buttons button').forEach(b => b.classList.remove('active'));
            if (t==='new') {{ filteredOffers = allOffers.filter(o => o.new); document.getElementById('btn-new').classList.add('active'); }}
            else if (t==='high') {{ filteredOffers = allOffers.filter(o => o.high); document.getElementById('btn-high').classList.add('active'); }}
            else if (t==='pre') {{ filteredOffers = allOffers.filter(o => o.sk.includes('preorder')); document.getElementById('btn-pre').classList.add('active'); }}
            container.scrollTop = 0; render();
        }}
        function filterBySource(s) {{ filteredOffers = allOffers.filter(o => o.sk === s); container.scrollTop = 0; render(); }}
        function clearFilters() {{ 
            document.querySelectorAll('.filter-buttons button').forEach(b => b.classList.remove('active'));
            document.getElementById('btn-all').classList.add('active');
            filteredOffers = [...allOffers]; document.getElementById('searchInput').value = ""; 
            container.scrollTop = 0; render(); 
        }}
        window.addEventListener('resize', render); render();
    </script></body></html>"""
    with open(path, 'w', encoding='utf-8') as f: f.write(html)

def sync_db_and_vacuum():
    conn = get_db_connection()
    try: 
        print("Limpiando y optimizando base de datos...")
        conn.execute("VACUUM")
        print("Mantenimiento finalizado.")
    finally: conn.close()

if __name__ == "__main__":
    generate_report()
    sync_db_and_vacuum()
