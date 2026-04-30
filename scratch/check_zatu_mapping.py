import sqlite3
import os

db_path = r"c:\Users\Profesor\Desktop\Personal\monitor_ofertas\bgg_cache.db"
if not os.path.exists(db_path):
    print("DB not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT m.item_name, m.bgg_id, d.deal_source FROM bgg_mapping m JOIN deals d ON m.item_name = d.item_name WHERE d.deal_source LIKE 'zatu%'")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Name: {row[0]} | BGG_ID: {row[1]} | Source: {row[2]}")
    conn.close()
