import sqlite3
import os

db_path = r"c:\Users\Profesor\Desktop\Personal\monitor_ofertas\bgg_cache.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT item_name FROM deals WHERE deal_source = 'zatu_sale' ORDER BY rowid DESC LIMIT 10")
rows = cursor.fetchall()
for row in rows:
    print(row[0])
conn.close()
