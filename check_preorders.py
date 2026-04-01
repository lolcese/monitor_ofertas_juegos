import sqlite3
import os

db_path = 'bgg_cache.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT count(*) FROM deals WHERE deal_source='preorder'").fetchone()[0]
    print(f"Total Philibert Pre-orders in DB: {count}")
    conn.close()
else:
    print("DB not found")
