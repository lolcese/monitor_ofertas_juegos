import sqlite3
conn = sqlite3.connect('bgg_cache.db')
r = conn.execute("SELECT deal_source, MAX(date_found) FROM deals WHERE deal_source LIKE 'mm%' GROUP BY deal_source").fetchall()
print("MM Dates:")
for row in r:
    print(row)
conn.close()
