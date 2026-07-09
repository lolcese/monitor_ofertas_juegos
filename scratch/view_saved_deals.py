import sqlite3
import datetime

conn = sqlite3.connect('bgg_cache.db')
cur = conn.cursor()
today = datetime.date.today().isoformat()
rows = cur.execute("SELECT item_name, price, deal_source, date_found FROM deals WHERE deal_source='private' AND date_found=?", (today,)).fetchall()
print(f"Total deals found for 'private' today ({today}): {len(rows)}")
for r in rows:
    print(f" - {r[0]} | Price: {r[1]}")
conn.close()
