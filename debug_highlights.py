import sqlite3
import datetime

def check_highlights():
    conn = sqlite3.connect('bgg_cache.db')
    c = conn.cursor()
    
    # 1. Total deals in the last 7 days
    c.execute("SELECT COUNT(*) FROM deals WHERE date_found >= date('now', '-7 days')")
    total_deals = c.fetchone()[0]
    print(f"Total deals (last 7d): {total_deals}")
    
    # Check what items were found today (if any)
    today = datetime.date.today().isoformat()
    c.execute("SELECT COUNT(*) FROM deals WHERE date_found = ?", (today,))
    total_today = c.fetchone()[0]
    print(f"Total deals (today {today}): {total_today}")
    
    # 2. Check why they might be missing (check rank/rating distribution)
    query = """
    SELECT 
        d.item_name, g.rating, g.rank, d.price, d.old_price 
    FROM deals d
    LEFT JOIN bgg_mapping m ON d.item_name = m.item_name
    LEFT JOIN games g ON m.bgg_id = g.bgg_id
    WHERE d.date_found >= date('now', '-7 days')
    """
    rows = c.execute(query).fetchall()
    
    highlights_count = 0
    for r in rows:
        name, rat, rnk, price, old = r
        try:
            vn = float(price.replace('€','').replace('$','').replace(',','.').strip())
            vo = float(old.replace('€','').replace('$','').replace(',','.').strip()) if (old and old not in ["0€","0$"]) else vn
            disc = (1 - vn/vo) if vo > 0 else 0
        except: disc = 0
        
        try:
            rat_f = float(rat) if (rat and rat != "-" and rat != "Cargando...") else 0
            rnk_f = int(rnk) if (rnk and str(rnk).isdigit()) else 999999
        except: 
            rat_f, rnk_f = 0, 999999
            
        if rat_f >= 7.8 or (rnk_f <= 1500 and rnk_f > 0) or disc >= 0.45:
            highlights_count += 1
            if highlights_count <= 5:
                print(f"Sample highlight: {name} (Rating: {rat_f}, Rank: {rnk_f}, Dto: {disc*100:.1f}%)")
                
    print(f"Highlights count: {highlights_count}")
    conn.close()

check_highlights()
