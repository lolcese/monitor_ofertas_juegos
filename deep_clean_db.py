import sqlite3
import os
import re

db_path = r'c:\Datos\Luis\bgg\monitor_ofertas_juegos\bgg_cache.db'
if not os.path.exists(db_path):
    print(f"Error: La DB {db_path} no existe.")
    exit(1)

def normalize_name(name):
    # Reemplaza múltiples espacios por uno solo y quita espacios en extremos
    if not name: return ""
    return " ".join(str(name).split())

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("--- INICIANDO LIMPIEZA PROFUNDA DE NOMBRES ---")

# 1. Limpieza de bgg_mapping (item_name es PRIMARY KEY)
try:
    mappings = c.execute("SELECT item_name, bgg_id, confidence, last_search, candidate_id FROM bgg_mapping").fetchall()
    to_delete = []
    to_update = []
    
    seen_norm = {} # norm_name -> (original_name, bgg_id, conf)
    
    for row in mappings:
        orig = row[0]
        norm = normalize_name(orig)
        bid, conf, last, cand = row[1:]
        
        if norm not in seen_norm:
            seen_norm[norm] = row
            if norm != orig:
                # No existe el normalizado, pero este tiene espacios raros -> Renombrar
                to_update.append((norm, orig))
        else:
            # Duplicado encontrado!
            prev_row = seen_norm[norm]
            # Decidir cual es mejor (el que tenga ID numerico o mayor confianza)
            prev_v = 100 if str(prev_row[1]).isdigit() else int(prev_row[2] or 0)
            curr_v = 100 if str(bid).isdigit() else int(conf or 0)
            
            if curr_v > prev_v:
                # El nuevo es mejor, borramos el viejo y actualizamos el mapa
                to_delete.append(prev_row[0])
                seen_norm[norm] = row
                if norm != orig: to_update.append((norm, orig))
            else:
                # El viejo es mejor, borramos este
                to_delete.append(orig)

    print(f"BGG MAPPING: {len(to_delete)} duplicados a borrar, {len(to_update)} nombres a limpiar.")
    
    for d in to_delete: c.execute("DELETE FROM bgg_mapping WHERE item_name = ?", (d,))
    for n, o in to_update: 
        try:
            c.execute("UPDATE OR IGNORE bgg_mapping SET item_name = ? WHERE item_name = ?", (n, o))
        except sqlite3.IntegrityError:
            # Si al renombrar choca con otro, simplemente lo borramos (ya lo habremos consolidado en el paso anterior idealmente)
            c.execute("DELETE FROM bgg_mapping WHERE item_name = ?", (o,))

    # 2. Limpieza de DEALS (Actualizar nombres normalizados)
    deals = c.execute("SELECT DISTINCT item_name FROM deals").fetchall()
    for (d_name,) in deals:
        n_name = normalize_name(d_name)
        if n_name != d_name:
            c.execute("UPDATE deals SET item_name = ? WHERE item_name = ?", (n_name, d_name))

    print("Limpieza finalizada con éxito.")
    conn.commit()
except Exception as e:
    print(f"Error durante la limpieza: {e}")
    conn.rollback()
finally:
    conn.close()
