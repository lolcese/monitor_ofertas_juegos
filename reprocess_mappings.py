import sqlite3
import time
from monitor_core import get_db_connection, fetch_bgg_id, init_db

def reprocess_pending():
    print("[REPROCESS] Iniciando REPROCESAMIENTO de candidatos pendientes...")
    init_db()
    conn = get_db_connection()
    today = "2026-04-02"
    
    try:
        # Buscar juegos que no están mapeados o están en espera
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.item_name 
            FROM bgg_mapping m 
            JOIN deals d ON m.item_name = d.item_name
            WHERE (m.bgg_id IS NULL OR m.bgg_id IN ('WAITING', 'N/A', ''))
            AND m.bgg_id != 'IGNORED'
            AND d.date_found >= date('now', '-7 days')
            GROUP BY m.item_name
        """)
        pending = cursor.fetchall()
        
        print(f"📦 Se han encontrado {len(pending)} juegos para buscar candidatos.")
        
        for (name,) in pending:
            print(f"   🔍 Buscando candidato para: {name}...")
            # IMPORTANTE: fetch_bgg_id ahora devuelve (best_id, confidence) sin filtrar por 95%
            id_b, conf = fetch_bgg_id(name)
            
            if id_b and str(id_b).isdigit():
                with conn:
                    if conf >= 95:
                        print(f"      [OK] Mapeo automático directo: {id_b} ({conf}%)")
                        conn.execute("UPDATE bgg_mapping SET bgg_id=?, confidence=?, last_search=?, candidate_id=NULL WHERE item_name=?", (id_b, conf, today, name))
                    else:
                        print(f"      [SUG] Candidato encontrado: {id_b} ({conf}%)")
                        conn.execute("UPDATE bgg_mapping SET bgg_id='WAITING', confidence=?, last_search=?, candidate_id=? WHERE item_name=?", (conf, today, id_b, name))
            else:
                print(f"      [ERR] No se encontró ningún candidato.")
                with conn:
                    conn.execute("UPDATE bgg_mapping SET bgg_id='N/A', confidence=0, last_search=?, candidate_id=NULL WHERE item_name=?", (today, name))
            
            time.sleep(2) # Respeto a la API de BGG
            
    finally:
        conn.close()
        print("\n[OK] Reprocesamiento finalizado. ¡Ya puedes abrir el Gestor Manual!")

if __name__ == "__main__":
    reprocess_pending()
