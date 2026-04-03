import sqlite3
import os

db_path = r'c:\Datos\Luis\bgg\monitor_ofertas_juegos\bgg_cache.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Total IGNORED
    c.execute("SELECT COUNT(*) FROM bgg_mapping WHERE bgg_id='IGNORED'")
    ignored = c.fetchone()[0]
    
    # 2. Total Mapeos Correctos (100% de confianza real)
    c.execute("SELECT COUNT(*) FROM bgg_mapping WHERE confidence=100.0 AND bgg_id NOT IN ('IGNORED', 'WAITING', 'N/A')")
    correct = c.fetchone()[0]
    
    # 3. Total Pendientes (WAITING)
    c.execute("SELECT COUNT(*) FROM bgg_mapping WHERE bgg_id='WAITING'")
    waiting = c.fetchone()[0]
    
    print(f"RESUMEN DE ESTADO DE LA BASE DE DATOS:")
    print(f"--------------------------------------")
    print(f"Productos Ignorados (Accesorios/Others): {ignored}")
    print(f"Productos Mapeados con Éxito (100%): {correct}")
    print(f"Productos Pendientes de Revisar: {waiting}")
    print(f"--------------------------------------")
    
    conn.close()
else:
    print("No se encuentra la base de datos.")
