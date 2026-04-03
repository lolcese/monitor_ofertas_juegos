import sqlite3
import time
from monitor_core import get_db_connection, fetch_bgg_id, init_db

def reprocess_all_unmapped():
    print("🚀 Iniciando BARRIDO TOTAL de juegos sin mapear...")
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
            AND d.date_found >= date('now', '-7 days')
            GROUP BY d.item_name
        """)
        pending = cursor.fetchall()
        
        print(f"📦 Encontrados {len(pending)} juegos vírgenes o con fallos previos.")
        
        for (name,) in pending:
            print(f"   🔍 Analizando: {name}...")
            id_b, conf = fetch_bgg_id(name)
            
            if id_b and id_b != 'N/A':
                # Si conf es alta, mapeo directo. Si no, Sugerencia.
                final_id = id_b if conf >= 95 else 'WAITING'
                cand_id = id_b if conf < 95 else None
                with conn:
                    conn.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search, candidate_id) VALUES (?,?,?,?,?)", (name, final_id, conf, today, cand_id))
                print(f"      {'✅ AUTO' if conf >= 95 else '💡 SUGERENCIA'} -> {id_b} ({conf}%)")
            else:
                # Si falló, guardamos 'N/A' para no re-intentar en cada segundo
                with conn:
                    conn.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)", (name, 'N/A', 0, today))
                print(f"      ❌ Sin resultados en BGG.")
            
            time.sleep(2) # Respeto API
            
    finally:
        conn.close()
        print("\n✅ Barrido finalizado. ¡Echa un ojo al Gestor ahora!")

if __name__ == "__main__":
    reprocess_all_unmapped()
