import sqlite3
import os
BASE_DIR = os.getcwd()
DB_PATH = os.path.join(BASE_DIR, 'bgg_cache.db')

def test_labels():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT deal_source, MAX(date_found) FROM deals GROUP BY deal_source").fetchall()
    conn.close()
    
    dates = {row[0]: row[1] for row in rows}
    print("DATES DICT keys:", list(dates.keys()))
    print("dates.get('mm_sales'):", dates.get('mm_sales'))
    print("dates.get('planeton'):", dates.get('planeton'))

test_labels()
