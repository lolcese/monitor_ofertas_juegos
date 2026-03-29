import sqlite3
conn = sqlite3.connect('bgg_cache.db')
r = conn.execute("SELECT deal_source, MAX(date_found), COUNT(*) FROM deals GROUP BY deal_source").fetchall()
print("Source | Max Date | Count")
print("-" * 30)
for row in r:
    print(f"'{row[0]}' | {row[1]} | {row[2]}")
conn.close()
