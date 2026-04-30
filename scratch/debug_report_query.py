import sqlite3
import datetime
import re

db_path = r"c:\Users\Profesor\Desktop\Personal\monitor_ofertas\bgg_cache.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

query = """
SELECT 
    t.deal_source
FROM (
    SELECT d.*, 
           ROW_NUMBER() OVER (PARTITION BY d.url ORDER BY CAST(REPLACE(REPLACE(REPLACE(d.price, '€', ''), '$', ''), '£', '') AS FLOAT) ASC) as rn
    FROM deals d
    INNER JOIN (
        SELECT deal_source, MAX(date_found) as latest_date 
        FROM deals 
        GROUP BY deal_source
    ) latest ON d.deal_source = latest.deal_source AND d.date_found = latest.latest_date
) t
LEFT JOIN bgg_mapping m ON t.item_name = m.item_name
WHERE t.rn = 1 AND (m.bgg_id IS NULL OR m.bgg_id NOT IN ('IGNORED', 'WAITING'))
"""

rows = c.execute(query).fetchall()
sources = {}
for r in rows:
    src = r[0]
    sources[src] = sources.get(src, 0) + 1

for src, count in sources.items():
    print(f"{src}: {count}")

conn.close()
