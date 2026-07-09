import sqlite3
import datetime

BGG_CACHE_DB = "bgg_cache.db"

def check_deals():
    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(BGG_CACHE_DB)
    try:
        cursor = conn.cursor()
        print("--- Today's deals in DB ---")
        rows = cursor.execute(
            "SELECT deal_source, COUNT(*) FROM deals WHERE date_found=? GROUP BY deal_source",
            (today,)
        ).fetchall()
        if not rows:
            print("No deals found for today yet.")
        for row in rows:
            print(f"Source: {row[0]}, Count: {row[1]}")
            
        print("\n--- Recent scraper runs ---")
        runs = cursor.execute("SELECT * FROM scraper_runs").fetchall()
        for run in runs:
            print(f"Source: {run[0]}, Last Run: {run[1]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_deals()
