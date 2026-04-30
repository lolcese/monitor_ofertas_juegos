import sqlite3
import os

db_path = r"c:\Users\Profesor\Desktop\Personal\monitor_ofertas\bgg_cache.db"
if not os.path.exists(db_path):
    print("DB not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT deal_source, count(*) FROM deals GROUP BY deal_source")
    rows = cursor.fetchall()
    for row in rows:
        print(f"{row[0]}: {row[1]}")
    conn.close()
