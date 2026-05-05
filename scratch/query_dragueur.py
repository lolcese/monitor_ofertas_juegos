import sqlite3

def get_data():
    conn = sqlite3.connect('bgg_cache.db')
    conn.row_factory = sqlite3.Row
    
    print("--- DEAL DATA ---")
    deal = conn.execute("SELECT * FROM deals WHERE item_name LIKE '%Master Dragueur%'").fetchone()
    if deal:
        for key in deal.keys():
            print(f"{key}: {deal[key]}")
            
        print("\n--- BGG MAPPING ---")
        mapping = conn.execute("SELECT * FROM bgg_mapping WHERE item_name = ?", (deal['item_name'],)).fetchone()
        if mapping:
            for key in mapping.keys():
                print(f"{key}: {mapping[key]}")
                
            if mapping['bgg_id'] and mapping['bgg_id'].isdigit():
                print("\n--- BGG GAME DATA ---")
                game = conn.execute("SELECT * FROM games WHERE bgg_id = ?", (mapping['bgg_id'],)).fetchone()
                if game:
                    for key in game.keys():
                        print(f"{key}: {game[key]}")
                else:
                    print("No details found in 'games' table.")
        else:
            print("No mapping found.")
    else:
        print("No deal found for 'Master Dragueur'.")
    
    conn.close()

if __name__ == "__main__":
    get_data()
