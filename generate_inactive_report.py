import os
import sqlite3
import datetime
import re
import shutil
from monitor_core import get_db_connection, init_db, fetch_details, IMG_DIR

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, 'public', 'ofertas_finalizadas.html')
IMAGE_DEST_DIR = os.path.join(BASE_DIR, 'public', 'assets', 'images')

LANG_MAPPING = {
    "No necessary in-game text": "Sin dependencia",
    "Some necessary text - easily memorized or small crib sheet": "Baja",
    "Moderate in-game text - needs objects to be explained or text on cards": "Moderada",
    "Extensive use of text - description of objects/cards, part of game inventory": "Alta",
    "Unplayable but for veteran gamers": "Injugable",
    "-": "-"
}

def color_lang(dep):
    dep_low = (dep or "").lower()
    if "sin" in dep_low: return "#27ae60"
    if "baja" in dep_low: return "#2980b9"
    if "moderada" in dep_low: return "#f39c12"
    if any(k in dep_low for k in ["alta", "injugable"]): return "#e74c3c"
    return "#7f8c8d"

def color_weight(w):
    try:
        wf = float(w)
        if wf < 2.0: return "#27ae60"
        if wf < 3.0: return "#2980b9"
        if wf < 4.0: return "#f39c12"
        return "#e74c3c"
    except: return "#7f8c8d"

def generate_inactive_report():
    print(">>> Generando reporte de OFERTAS FINALIZADAS...")
    init_db()
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
    
    conn = get_db_connection()
    try:
        c = conn.cursor()
        
        # Consulta para encontrar ofertas que YA NO ESTÁN en la última descarga de su fuente
        query = """
        SELECT 
            d.item_name, d.price, d.old_price, d.url, d.deal_source, 
            IFNULL(m.item_name, d.item_name) as bgg_name, 
            IFNULL(m.bgg_id, 'N/A') as bgg_id, 
            IFNULL(g.rating, 'N/A') as rating, 
            IFNULL(g.rank, '999999') as rank, 
            d.is_accessory, 
            d.is_expansion, 
            IFNULL(g.language_dependency, '-') as language_dependency, 
            IFNULL(g.original_name, d.item_name) as original_name, 
            IFNULL(g.type, 'UNKNOWN') as bgg_type, 
            IFNULL(g.weight, 'N/A') as weight, 
            IFNULL(g.min_players, 0) as min_p, 
            IFNULL(g.max_players, 0) as max_p, 
            IFNULL(g.best_players, '-') as best_p, 
            d.image_local, 
            MAX(d.date_found) as last_seen
        FROM deals d
        LEFT JOIN bgg_mapping m ON d.item_name = m.item_name
        LEFT JOIN games g ON m.bgg_id = g.bgg_id
        WHERE d.date_found < COALESCE((SELECT last_run FROM scraper_runs WHERE scraper_runs.deal_source = d.deal_source), (SELECT MAX(date_found) FROM deals d2 WHERE d2.deal_source = d.deal_source))
        AND d.item_name NOT IN (
            SELECT d3.item_name FROM deals d3 WHERE d3.date_found = COALESCE(
                (SELECT last_run FROM scraper_runs WHERE scraper_runs.deal_source = d3.deal_source),
                (SELECT MAX(date_found) FROM deals d4 WHERE d4.deal_source = d3.deal_source)
            )
        )
        GROUP BY d.item_name
        ORDER BY last_seen DESC
        LIMIT 500
        """
        rows = c.execute(query).fetchall()
    finally:
        conn.close()

    h_head = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Ofertas Finalizadas - Historial</title><style>
    body { font-family: sans-serif; background: #f4f4f4; margin: 20px; }
    h1 { color: #c0392b; text-align: center; }
    .container { max-width: 1200px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th, td { padding: 12px; border: 1px solid #ddd; text-align: left; font-size: 0.9em; }
    th { background: #34495e; color: white; cursor: pointer; }
    tr:nth-child(even) { background: #f9f9f9; }
    .price-old { text-decoration: line-through; color: #999; font-size: 0.8em; }
    .price-new { font-weight: bold; color: #c0392b; }
    .last-seen { background: #eee; padding: 2px 5px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }
    .game-img { width: 50px; border-radius: 4px; }
    .badge-src { background: #7f8c8d; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    </style></head><body><div class="container">
    <h1>📉 Ofertas Finalizadas (Historico)</h1>
    <p style="text-align:center;">Estas ofertas ya no están activas en las tiendas. Se muestra la última vez que fueron vistas.</p>
    <table><thead><tr><th>Imagen</th><th>Producto</th><th>Fuente</th><th>Última vez visto</th><th>Precio Final</th><th>BGG Name</th><th>Rating</th><th>Rank</th></tr></thead><tbody>"""
    
    h_body = ""
    for row in rows:
        name, price, old, url, src, b_name, b_id, rat, rnk, is_acc, is_exp, l_dep, o_name, g_type, g_wgt, min_p, max_p, best_p, img_local, last_seen = row
        img_h = f'<img src="assets/images/{img_local}" class="game-img">' if img_local else ''
        h_body += f"""<tr>
            <td>{img_h}</td>
            <td><a href="{url}" target="_blank">{name}</a></td>
            <td><span class="badge-src">{src.upper()}</span></td>
            <td><span class="last-seen">{last_seen}</span></td>
            <td><span class="price-old">{old}</span><br><span class="price-new">{price}</span></td>
            <td>{o_name or b_name}</td>
            <td style="color:#f39c12; font-weight:bold;">{rat if rat != 'N/A' else '-'}</td>
            <td>{f'#{rnk}' if rnk != '999999' else '-'}</td>
        </tr>"""
    
    h_foot = "</tbody></table></div></body></html>"
    
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(h_head + h_body + h_foot)
    
    print(f">>> Reporte de finalizadas generado en: {FILE_PATH}")

if __name__ == "__main__":
    generate_inactive_report()
