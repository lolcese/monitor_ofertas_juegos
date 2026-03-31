import sqlite3
import datetime
from monitor_core import get_db_connection, fetch_bgg_id, fetch_details

def reprocess_failed_matches():
    print(">>> Iniciando reprocesamiento de juegos con 0% de confianza o sin ID...")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Seleccionamos juegos con 0% o sin ID que no estén en IGNORED
        query = """
        SELECT item_name FROM bgg_mapping 
        WHERE (confidence < 50 OR bgg_id IS NULL OR bgg_id = '') 
        AND bgg_id NOT IN ('IGNORED', 'WAITING')
        """
        failed = cursor.execute(query).fetchall()
        print(f"Encontrados {len(failed)} juegos para reintentar.")
        
        for (name,) in failed:
            print(f"\n--- Procesando: {name} ---")
            b_id, conf = fetch_bgg_id(name)
            
            if b_id:
                print(f"¡Encontrado! ID: {b_id} (Confianza: {conf}%)")
                with conn:
                    cursor.execute("UPDATE bgg_mapping SET bgg_id = ?, confidence = ?, last_search = ? WHERE item_name = ?", 
                                  (b_id, conf, datetime.date.today().isoformat(), name))
                    
                    # Además descargamos los detalles si es un ID válido para que el reporte esté completo
                    details = fetch_details(b_id)
                    if details and details[4] != "Unknown":
                        rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = details
                        cursor.execute('INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (b_id, name, rat, rnk, gt, datetime.date.today().isoformat(), l_dep, o_name, wgt, minp, maxp, bestp))
            else:
                print("No se encontró coincidencia automática.")
                with conn:
                    cursor.execute("UPDATE bgg_mapping SET last_search = ? WHERE item_name = ?", (datetime.date.today().isoformat(), name))
    finally:
        conn.close()
    print("\n>>> Reprocesamiento finalizado.")

if __name__ == "__main__":
    reprocess_failed_matches()
