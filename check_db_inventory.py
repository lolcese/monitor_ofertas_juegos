import sqlite3
conn = sqlite3.connect('bgg_cache.db')
r = conn.execute("SELECT deal_source, COUNT(*) FROM deals GROUP BY deal_source").fetchall()
print("Deals in DB:")
for row in r:
    print(row)
conn.close()
