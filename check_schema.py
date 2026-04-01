import sqlite3
import os

BGG_CACHE_DB = 'bgg_cache.db'
conn = sqlite3.connect(BGG_CACHE_DB)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(deals)")
columns = cursor.fetchall()
for col in columns:
    print(col)
conn.close()
