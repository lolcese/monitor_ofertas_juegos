import sqlite3
import datetime

def analyze_new_deals():
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    
    conn = sqlite3.connect('bgg_cache.db')
    c = conn.cursor()
    
    # Total deals today
    c.execute("SELECT COUNT(*) FROM deals WHERE date_found = ?", (today,))
    total_today = c.fetchone()[0]
    
    # New deals (not seen yesterday)
    # Using EXCEPT or NOT IN
    c.execute("""
        SELECT item_name, price, old_price, deal_source, url 
        FROM deals 
        WHERE date_found = ? 
        AND item_name NOT IN (SELECT item_name FROM deals WHERE date_found < ?)
    """, (today, today))
    new_deals_raw = c.fetchall()
    
    # Enrichment from games table (join with mapping)
    enriched_new = []
    for d in new_deals_raw:
        c.execute("""
            SELECT g.name, g.rating, g.rank, g.weight 
            FROM bgg_mapping m 
            JOIN games g ON m.bgg_id = g.bgg_id 
            WHERE m.item_name = ?
        """, (d[0],))
        ginfo = c.fetchone()
        if ginfo:
            enriched_new.append(list(d) + list(ginfo))
        else:
            enriched_new.append(list(d) + [None, None, None, None])
            
    conn.close()
    
    return total_today, enriched_new

total, new_items = analyze_new_deals()
print(f"Total hoy: {total}")
print(f"Nuevos hoy: {len(new_items)}")

# Filtrar interesantes para el resumen (top rating o buen rank o gran descuento)
def get_highlights(items):
    highlights = []
    for item in items:
        # p_name, price, old, source, url, b_name, rat, rnk, wgt
        name = item[5] or item[0]
        try:
            p_new = float(item[1].replace('€','').replace('$','').replace(',','.').strip())
            p_old = float(item[2].replace('€','').replace('$','').replace(',','.').strip()) if item[2] else p_new
            discount = round((1 - p_new/p_old)*100) if p_old > 0 else 0
        except: discount = 0
        
        rating = float(item[6]) if (item[6] and item[6] != 'N/A') else 0
        rank = int(item[7]) if (item[7] and item[7] != '999999' and str(item[7]).isdigit()) else 999999
        
        if rating >= 7.5 or (rank < 2000) or (discount >= 50):
            highlights.append({
                'name': name,
                'price': item[1],
                'old': item[2],
                'discount': discount,
                'source': item[3],
                'rating': rating,
                'rank': rank,
                'url': item[4]
            })
    return highlights

highlights = get_highlights(new_items)
print(f"Highlights: {len(highlights)}")
for h in sorted(highlights, key=lambda x: (x['rating'], -x['rank']), reverse=True)[:15]:
    print(f"- {h['name']} ({h['source']}): {h['price']} (Dto: {h['discount']}%) - Rating: {h['rating']}, Rank: #{h['rank']}")
    print(f"  {h['url']}")
