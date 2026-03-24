import sqlite3
import datetime
import time
from philibert_core import get_db_connection, fetch_details, init_db

def refresh_all_metadata():
    init_db()
    today = datetime.date.today().isoformat()
    
    with get_db_connection() as conn:
        c = conn.cursor()
        # Buscamos juegos con datos insuficientes (Ranking N/A, Idioma '-', o Rating N/A)
        c.execute("""
            SELECT bgg_id, name 
            FROM games 
            WHERE rank = 'N/A' 
               OR rank = '999999'
               OR rating = 'N/A' 
               OR rating = '0.0'
               OR language_dependency = '-'
               OR language_dependency IS NULL
               OR weight = 'N/A'
               OR weight = '0.0'
        """)
        rows = c.fetchall()
        
        if not rows:
            print("✨ ¡Todos los juegos en la base de datos están correctamente informados!")
            return

        print(f"🚀 Refrescando datos para {len(rows)} juegos que tienen información incompleta...")
        
        current = 0
        total = len(rows)
        for bgg_id, local_name in rows:
            current += 1
            print(f"[{current}/{total}] Refrescando: {local_name} (ID: {bgg_id})...")
            
            # Traemos los datos frescos usando el núcleo modular corregido
            rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = fetch_details(bgg_id)
            
            if o_name or rnk != "N/A":
                c.execute("""
                    UPDATE games 
                    SET rating=?, rank=?, type=?, last_updated=?, 
                        language_dependency=?, original_name=?, weight=?, 
                        min_players=?, max_players=?, best_players=? 
                    WHERE bgg_id=?
                """, (rat, rnk, gt, today, l_dep, o_name, wgt, minp, maxp, bestp, bgg_id))
                conn.commit()
                print(f"   ✅ Actualizado: {o_name} | Rank: #{rnk} | Idioma: {l_dep}")
            else:
                print(f"   ⚠️  Fallo al traer datos para ID {bgg_id} (posible Rate Limit). Saltando...")
                time.sleep(2) # Pausa extra por si hay limite de API
            
            # Pausa de seguridad para BGG
            time.sleep(1)

    print("\n✅ ¡Base de datos saneada con éxito!")

if __name__ == "__main__":
    refresh_all_metadata()
