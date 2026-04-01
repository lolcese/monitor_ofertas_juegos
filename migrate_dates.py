import sqlite3
import os

BGG_CACHE_DB = 'bgg_cache.db'
conn = sqlite3.connect(BGG_CACHE_DB)
cursor = conn.cursor()

# Si la columna existe (ya debería por el init_db actualizado), 
# rellenamos los nulos con la fecha de date_found
try:
    cursor.execute("UPDATE deals SET date_first_seen = date_found WHERE date_first_seen IS NULL")
    conn.commit()
    print(f"Migración completada. Filas actualizadas: {cursor.rowcount}")
except Exception as e:
    print(f"Error en migración: {e}")

conn.close()
