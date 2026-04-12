import sqlite3
import os

BGG_CACHE_DB = 'bgg_cache.db'

def cleanup_db():
    if not os.path.exists(BGG_CACHE_DB):
        print("Base de datos no encontrada.")
        return
    
    conn = sqlite3.connect(BGG_CACHE_DB)
    try:
        # Movemos a 'N/A' aquellos que tengan WAITING pero que NO hayan sido marcados manualmente
        # (Los manuales tienen confidence = 0 y candidate_id IS NULL)
        # Los automáticos suelen tener confidence > 0 o un candidate_id.
        
        cursor = conn.cursor()
        
        # Primero contamos para informar
        query_check = """
            SELECT COUNT(*) FROM bgg_mapping 
            WHERE bgg_id = 'WAITING' 
            AND (confidence > 0 OR candidate_id IS NOT NULL)
        """
        count = cursor.execute(query_check).fetchone()[0]
        
        if count == 0:
            print("No se han encontrado registros de 'esperar' automáticos para limpiar.")
            return

        print(f"Se van a mover {count} juegos de 'esperar' (WAITING) a 'revisar' (N/A).")
        
        query_update = """
            UPDATE bgg_mapping 
            SET bgg_id = 'N/A' 
            WHERE bgg_id = 'WAITING' 
            AND (confidence > 0 OR candidate_id IS NOT NULL)
        """
        
        with conn:
            cursor.execute(query_update)
            print(f"Éxito: {cursor.rowcount} registros actualizados.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_db()
