import sqlite3
import os

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BGG_CACHE_DB = os.path.join(BASE_DIR, 'bgg_cache.db')

def cleanup_waiting_status():
    print("[CLEANUP] El script de limpieza de 'WAITING' ha sido desactivado.")
    print("[INFO] Bajo el nuevo sistema, los juegos marcados como 'WAITING' son permanentes e ignorados.")
    print("- Ya no se los trata como fallos.")
    print("- Ya no se los mueve a 'N/A'.")
    print("- Se quedan en su propia pestaña del gestor de mapeo.")

    conn = sqlite3.connect(BGG_CACHE_DB)
    try:
        cursor = conn.cursor()
        
        # 1. Contar cuántos items están en 'WAITING' con confianza 0
        cursor.execute("SELECT COUNT(*) FROM bgg_mapping WHERE bgg_id = 'WAITING' AND (confidence = 0 OR confidence IS NULL) AND (candidate_id IS NULL OR candidate_id = '')")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("[INFO] No se encontraron items automáticos en 'WAITING' con confianza 0. ¡Tu base de datos está limpia!")
        else:
            print(f"[INFO] Se han encontrado {count} items que serán movidos a 'N/A' (Sin Sugerencia).")
            
            # 2. Ejecutar la actualización
            with conn:
                cursor.execute("""
                    UPDATE bgg_mapping 
                    SET bgg_id = 'N/A' 
                    WHERE bgg_id = 'WAITING' 
                    AND (confidence = 0 OR confidence IS NULL) 
                    AND (candidate_id IS NULL OR candidate_id = '')
                """)
            
            print(f"[OK] Se han actualizado {cursor.rowcount} registros correctamente.")
            
    except Exception as e:
        print(f"[ERR] Error durante la limpieza: {e}")
    finally:
        conn.close()
        print("[OK] Proceso de limpieza finalizado.")

if __name__ == "__main__":
    cleanup_waiting_status()
