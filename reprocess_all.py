import sqlite3
import time
from monitor_core import get_db_connection, fetch_bgg_id, init_db

def reprocess_all_unmapped():
    print("[REPROCESS_ALL] Iniciando BARRIDO TOTAL de juegos sin mapear...")
    init_db()
    conn = get_db_connection()
    today = "2026-04-02"
    
    try:
        cursor = conn.cursor()
        # Buscamos TODO lo que no sea un éxito rotundo (95%+) y esté activo
        cursor.execute("""
            SELECT d.item_name 
            FROM deals d
            LEFT JOIN bgg_mapping m ON d.item_name = m.item_name
            WHERE (m.bgg_id IS NULL OR m.bgg_id = 'N/A' OR m.bgg_id = '')
            AND (m.bgg_id NOT IN ('WAITING', 'IGNORED') OR m.bgg_id IS NULL)
            AND d.date_found >= date('now', '-7 days')
            GROUP BY d.item_name
        """)
        pending = cursor.fetchall()
        
        print(f"[ITEM] Encontrados {len(pending)} juegos vírgenes o con fallos previos.")
        
        for (name,) in pending:
            # Doble check dentro del loop por seguridad
            curr = cursor.execute("SELECT bgg_id, confidence FROM bgg_mapping WHERE item_name = ?", (name,)).fetchone()
            if curr and (curr[0] in ['WAITING', 'IGNORED'] or curr[1] == 100):
                print(f"   [SKIP] {name} ya tiene un estado final ({curr[0]})")
                continue

            print(f"   [SEARCH] Analizando: {name}...")
            id_b, conf = fetch_bgg_id(name)
            
            if id_b:
                if id_b in ['WAITING', 'IGNORED']: 
                    final_id = id_b
                else:
                    # Si conf es alta, mapeo directo. Si no, Sugerencia.
                    final_id = id_b if conf >= 95 else 'WAITING'
                
                cand_id = id_b if (conf < 95 and str(id_b).isdigit()) else None
                with conn:
                    conn.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search, candidate_id) VALUES (?,?,?,?,?)", (name, final_id, conf, today, cand_id))
                print(f"      {'[OK] AUTO' if conf >= 95 else '[SUG] SUGERENCIA'} -> {final_id} ({conf}%)")
            else:
                # Si falló, guardamos 'N/A' para no re-intentar en cada segundo
                with conn:
                    conn.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)", (name, 'N/A', 0, today))
                print(f"      [ERR] Sin resultados en BGG.")
            
            time.sleep(2) # Respeto API
            
    finally:
        conn.close()
        print("\n[OK] Barrido finalizado. ¡Echa un ojo al Gestor ahora!")

if __name__ == "__main__":
    reprocess_all_unmapped()
