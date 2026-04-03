import sqlite3
import os

db_path = 'bgg_cache.db'
if not os.path.exists(db_path):
    print(f"Base de datos no encontrada en {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("--- BUSCANDO TWILIGHT STRUGGLE ---")
rows = cur.execute("SELECT item_name, url, deal_source, date_found, price FROM deals WHERE item_name LIKE '%Twilight Struggle%'").fetchall()
for r in rows:
    print(f"Nombre: {r[0]}")
    print(f"URL:    {r[1]}")
    print(f"Fuente: {r[2]}")
    print(f"Fecha:  {r[3]}")
    print(f"Precio: {r[4]}")
    print("-" * 20)

print("\n--- BUSCANDO DUPLICADOS GLOBALES POR URL ---")
dupes = cur.execute("SELECT url, COUNT(*) FROM deals GROUP BY url HAVING COUNT(*) > 1").fetchall()
for d in dupes:
    print(f"URL: {d[0]} | Veces: {d[1]}")

conn.close()
