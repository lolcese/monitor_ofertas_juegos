import sqlite3
import os
import datetime
import shutil

DB_PATH = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
PUBLIC_DIR = r'c:\Datos\Luis\bgg\Phillibert\public'
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
        if wf <= 1.8: return "#27ae60" # Muy fácil (Verde)
        if wf <= 2.8: return "#2ecc71" # Fácil (Verde claro)
        if wf <= 3.6: return "#f39c12" # Medio (Naranja)
        return "#e74c3c" # Difícil (Rojo)
    except: return "#7f8c8d" # N/A

def color_lang(dep):
    dep_low = dep.lower()
    if dep_low == "sin": return "#27ae60" # Verde
    if dep_low == "baja": return "#2980b9" # Azul
    if dep_low == "moderada": return "#f39c12" # Naranja
    if dep_low in ["alta", "injugable"]: return "#e74c3c" # Rojo
    return "#7f8c8d"

def generate_report():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Aseguramos que el reporte solo muestre ofertas seguras (confianza >= 95)
    query = """
    SELECT 
        d.philibert_name, d.price, d.old_price, d.url, d.deal_source,
        g.name as bgg_name, g.bgg_id, g.rating, g.rank, d.is_accessory, d.is_expansion,
        g.language_dependency, g.original_name, g.type, g.weight, g.min_players, g.max_players, g.best_players, d.image_local
    FROM deals d
    INNER JOIN bgg_mapping m ON d.philibert_name = m.philibert_name
    INNER JOIN games g ON m.bgg_id = g.bgg_id
    WHERE d.date_found = (SELECT MAX(date_found) FROM deals)
    AND m.confidence >= 95
    ORDER BY CASE WHEN g.rank = '999999' OR g.rank = 'N/A' OR g.rank IS NULL THEN 1 ELSE 0 END, CAST(g.rank AS INTEGER) ASC
    """
    c.execute(query)
    rows = c.fetchall()
    
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Ofertas Philibert - Monitor</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f7f6; margin: 25px; color: #333; }
            h1 { color: #2c3e50; text-align: center; }
            .container { background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 98%; margin: auto; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: auto; }
            th { background-color: #3498db; color: white; cursor: pointer; padding: 12px; text-align: left; position: sticky; top: 0; }
            th:hover { background-color: #2980b9; }
            td { border-bottom: 1px solid #ddd; padding: 10px; vertical-align: middle; }
            tr:hover { background-color: #f1f1f1; }
            .price-new { font-weight: bold; color: #e74c3c; font-size: 1.1em; }
            .price-old { text-decoration: line-through; color: #95a5a6; font-size: 0.85em; margin-right: 5px; }
            .discount-badge { background: #e74c3c; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9em; }
            .badge-flash { background: #f1c40f; color: #333; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
            .badge-occasion { background: #9b59b6; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
            .badge-private { background: #2c3e50; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
            .type-base { color: #2980b9; font-weight: bold; font-size: 0.85em; }
            .type-expansion { color: #d35400; font-weight: bold; font-size: 0.85em; }
            .type-accessory { color: #7f8c8d; font-weight: bold; font-size: 0.85em; }
            .lang-dep { font-size: 0.75em; font-weight: bold; padding: 2px 5px; border-radius: 3px; color: white; display: inline-block; margin-top: 5px; }
            .orig-name { font-size: 0.8em; color: #7f8c8d; font-style: italic; display: block; margin-top: 3px; }
            a { text-decoration: none; color: #3498db; }
            a:hover { text-decoration: underline; }
            .rank { color: #27ae60; font-weight: bold; }
            .rating { color: #f39c12; font-weight: bold; }
            .center { text-align: center; }
            .game-img { width: 60px; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            footer { margin-top: 30px; text-align: center; font-size: 0.9em; color: #7f8c8d; border-top: 1px solid #ddd; padding-top: 15px; }
            .contact-btn { display: inline-block; background-color: #0088cc; color: white; padding: 6px 15px; border-radius: 20px; text-decoration: none; margin-left: 10px; font-weight: bold; }
            .contact-btn:hover { background-color: #0077b5; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Ofertas Philibert - Monitor</h1>
            <div style="text-align:center; margin-bottom: 25px;">
                <span style="font-size: 0.9em; color: #7f8c8d;">Desarrollado por <b>Luis Olcese</b></span>
                <a href="https://t.me/Luis_Olcese" target="_blank" class="contact-btn">✉️ Contactar en Telegram</a>
            </div>
            <p style="text-align:center; margin-bottom: 5px;">Mostrando <b>""" + str(len(rows)) + """</b> ofertas verificadas el día: <b>""" + str(datetime.date.today()) + """</b></p>
            
            <div style="margin-bottom: 20px; text-align: center;">
                <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="🔍 Buscar por nombre, categoría, idioma, fuente..." 
                style="padding: 12px; width: 60%; border-radius: 8px; border: 1px solid #ddd; font-size: 1em; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
            </div>

            <table id="offersTable">
                <thead>
                    <tr>
                        <th class="center">Imagen</th>
                        <th onclick="sortTable(1)">Producto Philibert</th>
                        <th onclick="sortTable(2)">Categoría</th>
                        <th onclick="sortTable(3)">Precio</th>
                        <th onclick="sortTable(4)" class="center">% Dto</th>
                        <th onclick="sortTable(5)" class="center">Fuente</th>
                        <th onclick="sortTable(6)">Nombre BGG</th>
                        <th onclick="sortTable(7)" class="center">Dependencia idioma</th>
                        <th onclick="sortTable(8)" class="center">Peso</th>
                        <th onclick="sortTable(9)" class="center">Jugadores</th>
                        <th onclick="sortTable(10)" class="center">Rating</th>
                        <th onclick="sortTable(11)" class="center">Rank</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for row in rows:
        p_name, p_price, p_old, p_url, p_source, b_name, b_id, b_rating, b_rank, is_acc, is_exp, l_dep, o_name, g_type, g_wgt, min_p, max_p, best_p, img_local = row
        
        p_display_name = p_name.replace(' - Occasion', '').strip()
        
        try:
            val_new = float(p_price.replace('€','').replace(',','.').strip())
            val_old = float(p_old.replace('€','').replace(',','.').strip()) if (p_old and p_old != "0€") else val_new
            discount = round((1 - val_new/val_old) * 100) if val_old > 0 else 0
        except:
            discount = 0
            
        source_badge = f'<span class="badge-flash">FLASH</span>'
        if p_source == 'occasion': source_badge = f'<span class="badge-occasion">OCCASION</span>'
        elif p_source == 'private': source_badge = f'<span class="badge-private">PRIVÉE</span>'
        
        # Prioridad de categoría (BGG manda si existe el dato)
        final_is_exp = is_exp or (g_type == 'boardgameexpansion')
        
        if is_acc: cat_html = '<span class="type-accessory">Accesorio</span>'
        elif final_is_exp: cat_html = '<span class="type-expansion">Expa</span>'
        else: cat_html = '<span class="type-base">Base</span>'
            
        bgg_url_link = f'https://boardgamegeek.com/boardgame/{b_id}'
        # BGG display (Original name only)
        bgg_display = f'<a href="{bgg_url_link}" target="_blank">{o_name or b_name}</a>'

        # Traducción de Idioma
        l_dep_translated = LANG_MAPPING.get(l_dep, l_dep or "-")
        l_color = color_lang(l_dep_translated)
        l_dep_display = f'<span class="lang-dep" style="background-color:{l_color}">{l_dep_translated}</span>'
        
        # New: Weight decoration
        w_color = color_weight(g_wgt)
        w_display = f'<span class="lang-dep" style="background-color:{w_color}; font-weight:bold;">{g_wgt or "N/A"}</span>'
        
        # New: Players decoration
        p_range = f"{min_p}-{max_p}" if min_p != max_p else f"{min_p}"
        players_display = f"{p_range}"

        rat_val = b_rating if (b_rating and b_rating != "N/A" and b_rating != "0.0") else "-"
        rnk_val = f"#{b_rank}" if (b_rank and b_rank != "N/A" and b_rank != "999999") else "-"
        
        # Image Display (Relativa para portabilidad)
        img_filename = os.path.basename(img_local) if img_local else ""
        img_html = f'<img src="assets/images/{img_filename}" class="game-img">' if img_filename else '<div class="game-img" style="height:60px; background:#eee; display:flex; align-items:center; justify-content:center; color:#ccc;">📷</div>'

        html += f"""
            <tr>
                <td class="center">{img_html}</td>
                <td><a href="{p_url}" target="_blank">{p_display_name}</a></td>
                <td>{cat_html}</td>
                <td data-sort="{val_new}"><span class="price-old">{p_old if p_old != '0€' else ''}</span><br><span class="price-new">{p_price}</span></td>
                <td class="center" data-sort="{discount}"><span class="discount-badge">-{discount}%</span></td>
                <td class="center">{source_badge}</td>
                <td>{bgg_display}</td>
                <td class="center">{l_dep_display}</td>
                <td class="center">{w_display}</td>
                <td class="center">{players_display}</td>
                <td class="center" data-sort="{rat_val}">{rat_val}</td>
                <td class="center" data-sort="{(b_rank if b_rank != 'N/A' else '999999')}"><b>{rnk_val}</b></td>
            </tr>
        """
        
    html += """
                </tbody>
            </table>
        </div>
        <script>
            function filterTable() {
                var input, filter, table, tr, td, i, j, txtValue, display;
                input = document.getElementById("searchInput");
                filter = input.value.toUpperCase();
                table = document.getElementById("offersTable");
                tr = table.getElementsByTagName("tr");
                for (i = 1; i < tr.length; i++) {
                    display = "none";
                    td = tr[i].getElementsByTagName("td");
                    for (j = 0; j < td.length; j++) {
                        if (td[j]) {
                            txtValue = td[j].textContent || td[j].innerText;
                            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                                display = "";
                                break;
                            }
                        }
                    }
                    tr[i].style.display = display;
                }
            }

            function sortTable(n) {
                var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                table = document.getElementById("offersTable");
                switching = true;
                dir = "asc"; 
                while (switching) {
                    switching = false;
                    rows = table.rows;
                    for (i = 1; i < (rows.length - 1); i++) {
                        shouldSwitch = false;
                        x = rows[i].getElementsByTagName("TD")[n];
                        y = rows[i + 1].getElementsByTagName("TD")[n];
                        
                        var xVal = x.getAttribute("data-sort") || x.textContent.trim().toLowerCase();
                        var yVal = y.getAttribute("data-sort") || y.textContent.trim().toLowerCase();
                        // Si es numérico (Columnas 3, 4, 8, 9, 10, 11)
                        if ([3, 4, 8, 9, 10, 11].includes(n)) {
                            xVal = parseFloat(xVal.replace(/[€%#]|not ranked|n\\/a/g, '').replace(',', '.'));
                            yVal = parseFloat(yVal.replace(/[€%#]|not ranked|n\\/a/g, '').replace(',', '.'));
                            if (isNaN(xVal)) xVal = 999999;
                            if (isNaN(yVal)) yVal = 999999;
                        }

                        if (dir == "asc") {
                            if (xVal > yVal) { shouldSwitch = true; break; }
                        } else if (dir == "desc") {
                            if (xVal < yVal) { shouldSwitch = true; break; }
                        }
                    }
                    if (shouldSwitch) {
                        rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                        switching = true;
                        switchcount ++;      
                    } else {
                        if (switchcount == 0 && dir == "asc") {
                            dir = "desc";
                            switching = true;
                        }
                    }
                }
            }
        </script>
    </body>
    </html>
    """
    
    # Aseguramos que la carpeta pública y la de imágenes existan
    os.makedirs(IMAGE_DEST_DIR, exist_ok=True)
    
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
        f.flush()
        os.fsync(f.fileno())
        
    print(f"Informe v2.1 (MODO DESPLIEGUE SEGURO) generado en: {REPORT_PATH}")
    
    # Copiamos solo las imágenes necesarias de las ofertas de hoy
    print("Sincronizando imágenes en carpeta pública...")
    count_img = 0
    for row in rows:
        img_absolute = row[18] # La columna 19 (índice 18) es image_local
        if img_absolute and os.path.exists(img_absolute):
            filename = os.path.basename(img_absolute)
            dest = os.path.join(IMAGE_DEST_DIR, filename)
            if not os.path.exists(dest):
                shutil.copy2(img_absolute, dest)
                count_img += 1
                
    print(f"PROCESAMIENTO COMPLETADO. Se han copiado {count_img} imágenes nuevas.")
    print(f"Carpeta lista para publicar: {PUBLIC_DIR}")
    print(f"Sube el contenido de 'public' a Netlify.")

if __name__ == "__main__":
    generate_report()
