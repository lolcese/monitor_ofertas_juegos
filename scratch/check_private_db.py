import sqlite3
import datetime

conn = sqlite3.connect('bgg_cache.db')
today = datetime.date.today().isoformat()
print(f"Deals for today ({today}):")
rows = conn.execute("SELECT item_name, price, old_price, url FROM deals WHERE date_found=? AND deal_source='private'", (today,)).fetchall()
for r in rows:
    print(f"Name: {r[0]} | Price: {r[1]} | Old Price: {r[2]} | URL: {r[3]}")
conn.close()
