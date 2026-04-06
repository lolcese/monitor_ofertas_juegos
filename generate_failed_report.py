import sqlite3
import datetime
import os
from monitor_core import BGG_CACHE_DB, LOG_HTML_PATH, get_db_connection

def generate_failed_report():
    print(f"Generando reporte de coincidencias fallidas en: {LOG_HTML_PATH}...")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Obtenemos productos de bgg_mapping con confianza baja o sin ID, cruzando con deals para tener la URL
        query = """
        SELECT 
            m.item_name, m.bgg_id, m.confidence, m.last_search, d.url, d.deal_source
        FROM bgg_mapping m
        JOIN deals d ON m.item_name = d.item_name
        WHERE (m.confidence < 95 OR m.bgg_id IS NULL)
        AND d.date_found >= (SELECT date(MAX(date_found), '-1 day') FROM deals)
        GROUP BY m.item_name
        ORDER BY m.last_search DESC
        """
        failed = cursor.execute(query).fetchall()
    finally:
        conn.close()
        
    if not failed:
        with open(LOG_HTML_PATH, "w", encoding="utf-8") as f:
            f.write("<html><body><h1>No hay coincidencias fallidas recientes.</h1></body></html>")
        print("No se encontraron fallos recientes.")
        return

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Coincidencias Fallidas BGG</title>
    <style>
        body {{ font-family: sans-serif; background: #fdfdfd; padding: 20px; }}
        h1 {{ color: #c0392b; border-bottom: 2px solid #c0392b; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; }}
        th {{ background: #c0392b; color: white; padding: 10px; text-align: left; }}
        td {{ border-bottom: 1px solid #eee; padding: 10px; }}
        tr:hover {{ background: #f9f2f2; }}
        .low-conf {{ color: #d35400; font-weight: bold; }}
        .no-id {{ color: #c0392b; font-weight: bold; }}
        .btn {{ display: inline-block; padding: 5px 10px; background: #3498db; color: white; text-decoration: none; border-radius: 4px; font-size: 0.8em; }}
        .btn:hover {{ background: #2980b9; }}
    </style>
</head>
<body>
    <h1>📋 Coincidencias Fallidas / Por Corregir</h1>
    <p>Fecha del reporte: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>Estos productos no se vincularon automáticamente con BGG o tienen baja confianza.</p>
    
    <table>
        <thead>
            <tr>
                <th>Producto (Tienda)</th>
                <th>BGG ID Actual</th>
                <th>Confianza</th>
                <th>Último Intento</th>
                <th>Fuente</th>
                <th>Acciones</th>
            </tr>
        </thead>
        <tbody>
"""
    for name, b_id, conf, last, url, source in failed:
        status_cls = "no-id" if not b_id else ("low-conf" if conf < 95 else "")
        status_text = "SIN ID" if not b_id else f"{conf}%"
        
        # Limpiar nombre para búsqueda manual en Google/BGG
        search_query = name.replace(' ', '+').replace('(', '').replace(')', '')
        google_url = f"https://www.google.com/search?q={search_query}+boardgamegeek"
        
        html += f"""
            <tr>
                <td><b>{name}</b></td>
                <td><span class="{status_cls}">{b_id or '-'}</span></td>
                <td><span class="{status_cls}">{status_text}</span></td>
                <td>{last}</td>
                <td>{source}</td>
                <td>
                    <a href="{url}" target="_blank" class="btn">Ver en Tienda</a>
                    <a href="{google_url}" target="_blank" class="btn" style="background:#4285f4;">Buscar en BGG</a>
                </td>
            </tr>"""

    html += """
        </tbody>
    </table>
</body>
</html>"""

    with open(LOG_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Reporte generado: {len(failed)} fallos encontrados.")

if __name__ == "__main__":
    generate_failed_report()
