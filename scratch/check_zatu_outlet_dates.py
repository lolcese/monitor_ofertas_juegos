import sqlite3
import os

db_path = r"c:\Users\Profesor\Desktop\Personal\monitor_ofertas\bgg_cache.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT date_found, count(*) FROM deals WHERE deal_source = 'zatu_outlet' GROUP BY date_found")
rows = cursor.fetchall()
for row in rows:
    print(f"Date: {row[0]} | Count: {row[1]}")
conn.close()
