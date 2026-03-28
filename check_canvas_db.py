import sqlite3
conn = sqlite3.connect('bgg_cache.db')
print("Checking Canvas Reflections (335172) type:")
row = conn.execute("SELECT name, type FROM games WHERE bgg_id='335172'").fetchone()
print(row)
conn.close()
