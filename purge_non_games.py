import sqlite3
from monitor_core import get_db_connection

def purge_non_games():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Identificar juegos que son accesorios, RPGs o desconocidos
    # Tipos permitidos: boardgame, boardgameexpansion
    query_bad = "SELECT bgg_id, name, type FROM games WHERE type NOT IN ('boardgame', 'boardgameexpansion')"
    bad_items = cursor.execute(query_bad).fetchall()
    
    if not bad_items:
        print(">>> No se encontraron elementos no-juego para purgar.")
        conn.close()
        return

    print(f"\n>>> Iniciando purga de {len(bad_items)} elementos (Accesorios, RPGs, etc.)...")
    
    for b_id, name, g_type in bad_items:
        print(f"    - Purgando: [{b_id}] {name} ({g_type})")
        
        # Marcar como IGNORED en el mapeo para no volver a encontrarlos
        cursor.execute("UPDATE bgg_mapping SET bgg_id = 'IGNORED', confidence = 0 WHERE bgg_id = ?", (b_id,))
        
        # Eliminar de la tabla de juegos (metadatos)
        cursor.execute("DELETE FROM games WHERE bgg_id = ?", (b_id,))
        
        # Opcionalmente, podríamos eliminar las ofertas asociadas, 
        # pero es mejor dejarlas con ID=None para que aparezcan en el gestor de fallos si el usuario quiere arreglarlas manualmente
        # Sin embargo, como el mapeo ahora es IGNORED, no molestarán en el reporte principal.

    conn.commit()
    conn.close()
    print("\n>>> Purga completada y mapeos actualizados a 'IGNORED'.")

if __name__ == "__main__":
    purge_non_games()
