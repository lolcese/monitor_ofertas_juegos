import sqlite3
import os

BGG_CACHE_DB = 'bgg_cache.db'

def check_db():
    if not os.path.exists(BGG_CACHE_DB):
        print("DB not found")
        return
    
    conn = sqlite3.connect(BGG_CACHE_DB)
    try:
        rows = conn.execute("SELECT item_name, bgg_id, confidence, candidate_id FROM bgg_mapping WHERE bgg_id = 'WAITING' LIMIT 30").fetchall()
        print(f"Found {len(rows)} WAITING items:")
        for r in rows:
            print(f"Name: {r[0]}, Conf: {r[2]}, Cand: {r[3]}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
