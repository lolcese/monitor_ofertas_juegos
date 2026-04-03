import sqlite3
from monitor_core import BGG_CACHE_DB

conn = sqlite3.connect(BGG_CACHE_DB)
try:
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, url, image_local, deal_source, price FROM deals WHERE item_name LIKE '%Mariposa%' LIMIT 5")
    rows = cursor.fetchall()
    print("--- RESULTADOS DB ---")
    for r in rows:
        print(f"Nombre: {r[0]}")
        print(f"URL: {r[1]}")
        print(f"Img Local: {r[2]}")
        print(f"Fuente: {r[3]}")
        print(f"Precio: {r[4]}")
        print("-------------------")
finally:
    conn.close()
