import sqlite3
conn = sqlite3.connect('bgg_cache.db')
print("Mapping search for 'Batalla' and 'Terra Mystica':")
r = conn.execute("SELECT item_name, bgg_id, confidence, last_search FROM bgg_mapping WHERE item_name LIKE '%Batalla%' OR item_name LIKE '%Terra Mystica%'").fetchall()
for row in r:
    print(row)
conn.close()
