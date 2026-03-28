import sqlite3
from monitor_core import get_db_connection, IGNORE_KEYWORDS

def purge_ignored():
    print(">>> Purgando artículos ignorados de la base de datos...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    total_deleted = 0
    for kw in IGNORE_KEYWORDS:
        # Purgar de DEALS
        cursor.execute("DELETE FROM deals WHERE item_name LIKE ?", (f"%{kw}%",))
        total_deleted += cursor.rowcount
        
        # Opcionalmente marcar como IGNORED en mapping
        cursor.execute("UPDATE bgg_mapping SET bgg_id = 'IGNORED' WHERE item_name LIKE ?", (f"%{kw}%",))

    conn.commit()
    conn.close()
    print(f">>> Se han eliminado/ignorado {total_deleted} registros basados en IGNORE_KEYWORDS.")

if __name__ == "__main__":
    purge_ignored()
