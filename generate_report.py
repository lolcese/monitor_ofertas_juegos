import sqlite3
import os
import datetime

DB_PATH = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
REPORT_PATH = r'c:\Datos\Luis\bgg\Phillibert\ofertas_philibert.html'

LANG_MAPPING = {
    "No necessary in-game text": "Sin dependencia",
    "Some necessary text - easily memorized or small crib sheet": "Baja dependencia",
    "Moderate in-game text - needs crib sheet or paste ups": "Moderada dependencia",
    "Extensive use of text - massive conversion needed to be playable": "Alta dependencia",
    "Unplayable in another language": "Injugable en otro idioma"
}

def color_lang(dep):
    dep_low = dep.lower()
    if "no necessary" in dep_low or "sin dependencia" in dep_low: return "#27ae60" # Verde
    if "some necessary" in dep_low or "baja" in dep_low: return "#2980b9" # Azul
    if "moderate" in dep_low or "moderada" in dep_low: return "#f39c12" # Naranja
    if "extensive" in dep_low or "unplayable" in dep_low or "alta" in dep_low or "injugable" in dep_low: return "#e74c3c" # Rojo
    return "#7f8c8d"

def generate_report():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Aseguramos que el reporte solo muestre ofertas seguras (confianza >= 95)
    query = """
    SELECT 
        d.philibert_name, d.price, d.old_price, d.url, d.deal_source,
        g.name as bgg_name, g.bgg_id, g.rating, g.rank, d.is_accessory, d.is_expansion,
        g.language_dependency, g.original_name, g.type
    FROM deals d
    INNER JOIN bgg_mapping m ON d.philibert_name = m.philibert_name
    INNER JOIN games g ON m.bgg_id = g.bgg_id
    WHERE d.date_found = (SELECT MAX(date_found) FROM deals)
    AND m.confidence >= 95
    ORDER BY d.deal_source DESC, d.philibert_name ASC
    """
    c.execute(query)
    rows = c.fetchall()
    
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Ofertas Philibert - Board Game Monitor</title>
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
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔥 Philibert Board Game Monitor 🔥</h1>
            <p style="text-align:center;">Mostrando <b>""" + str(len(rows)) + """</b> ofertas 100% verificadas del día: <b>""" + str(datetime.date.today()) + """</b></p>
            
            <div style="margin-bottom: 20px; text-align: center;">
                <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="🔍 Buscar por nombre, categoría, idioma, fuente..." 
                style="padding: 12px; width: 60%; border-radius: 8px; border: 1px solid #ddd; font-size: 1em; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
            </div>

            <table id="offersTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">Producto Philibert</th>
                        <th onclick="sortTable(1)">Categoría</th>
                        <th onclick="sortTable(2)">Precio</th>
                        <th onclick="sortTable(3)" class="center">% Dto</th>
                        <th onclick="sortTable(4)" class="center">Fuente</th>
                        <th onclick="sortTable(5)">Nombre BGG</th>
                        <th onclick="sortTable(6)" class="center">Dependencia idioma</th>
                        <th onclick="sortTable(7)" class="center">⭐ Rating</th>
                        <th onclick="sortTable(8)" class="center">🏆 Rank</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for row in rows:
        p_name, p_price, p_old, p_url, p_source, b_name, b_id, b_rating, b_rank, is_acc, is_exp, l_dep, o_name, g_type = row
        
        p_display_name = p_name.replace(' - Occasion', '').strip()
        
        try:
            val_new = float(p_price.replace('€','').replace(',','.').strip())
            val_old = float(p_old.replace('€','').replace(',','.').strip()) if (p_old and p_old != "0€") else val_new
            discount = round((1 - val_new/val_old) * 100) if val_old > 0 else 0
        except:
            discount = 0
            
        source_badge = f'<span class="badge-flash">⚡ FLASH</span>'
        if p_source == 'occasion': source_badge = f'<span class="badge-occasion">🏷️ OCCASION</span>'
        elif p_source == 'private': source_badge = f'<span class="badge-private">🔐 PRIVÉE</span>'
        
        # Prioridad de categoría (BGG manda si existe el dato)
        final_is_exp = is_exp or (g_type == 'boardgameexpansion')
        
        if is_acc: cat_html = '<span class="type-accessory">🛠️ Accesorio</span>'
        elif final_is_exp: cat_html = '<span class="type-expansion">➕ Expansión</span>'
        else: cat_html = '<span class="type-base">📦 Juego Base</span>'
            
        bgg_url_link = f'https://boardgamegeek.com/boardgame/{b_id}'
        bgg_display = f'<a href="{bgg_url_link}" target="_blank">{b_name}</a>'
        orig_display = f'<span class="orig-name">{o_name}</span>' if (o_name and o_name != b_name) else ""
        
        # Traducción de Idioma
        l_dep_translated = LANG_MAPPING.get(l_dep, l_dep or "-")
        l_color = color_lang(l_dep_translated)
        l_dep_display = f'<span class="lang-dep" style="background-color:{l_color}">{l_dep_translated}</span>'
        
        rat_val = b_rating if (b_rating and b_rating != "N/A" and b_rating != "0.0") else "-"
        rnk_val = f"#{b_rank}" if (b_rank and b_rank != "N/A" and b_rank != "999999") else "-"
        
        html += f"""
                    <tr>
                        <td><a href="{p_url}" target="_blank">{p_display_name}</a></td>
                        <td>{cat_html}</td>
                        <td>
                            <span class="price-old">{p_old if (p_old and p_old != "0€") else ""}</span>
                            <span class="price-new">{p_price}</span>
                        </td>
                        <td class="center"><span class="discount-badge">-{discount}%</span></td>
                        <td class="center">{source_badge}</td>
                        <td>{bgg_display}{orig_display}</td>
                        <td class="center">{l_dep_display}</td>
                        <td class="center"><span class="rating">{rat_val}</span></td>
                        <td class="center"><span class="rank">{rnk_val}</span></td>
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
                var table = document.getElementById("offersTable");
                var rows = table.rows;
                var switching = true, i, x, y, shouldSwitch, dir = "asc", switchcount = 0;
                while (switching) {
                    switching = false;
                    for (i = 1; i < (rows.length - 1); i++) {
                        shouldSwitch = false;
                        x = rows[i].getElementsByTagName("TD")[n];
                        y = rows[i + 1].getElementsByTagName("TD")[n];
                        var xVal = x.textContent.trim().toLowerCase();
                        var yVal = y.textContent.trim().toLowerCase();
                        
                        if (n === 2 || n === 3 || n === 7 || n === 8) {
                             xVal = xVal.replace(/[€%#]|not ranked|n\\/a/g, '').replace(',', '.').trim();
                             yVal = yVal.replace(/[€%#]|not ranked|n\\/a/g, '').replace(',', '.').trim();
                             if (n === 8) {
                                  xVal = parseFloat(xVal) || 999999;
                                  yVal = parseFloat(yVal) || 999999;
                             } else {
                                  xVal = parseFloat(xVal) || 0;
                                  yVal = parseFloat(yVal) || 0;
                             }
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
                        if (switchcount == 0 && dir == "asc") { dir = "desc"; switching = true; }
                    }
                }
            }
        </script>
    </body>
    </html>
    """
    
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
        f.flush()
        os.fsync(f.fileno())
        
    print(f"Informe v1.7 con IDIOMAS y NOMBRES ORIGINALES generado en: {REPORT_PATH}")

if __name__ == "__main__":
    generate_report()
