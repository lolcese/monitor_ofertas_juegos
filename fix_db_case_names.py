import sqlite3
import re
from monitor_core import get_db_connection

def fix_db_case_names():
    print(">>> Iniciando limpieza de sufijos 'CASE (x)' en la base de datos...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Regex para detectar CASE (6), CASE (12), etc (insensible a mayúsculas)
    pattern = r'\s*CASE\s*\(\d+\)'
    
    # 1. Tabla DEALS
    # Buscamos nombres que contengan 'CASE ('
    rows = cursor.execute("SELECT item_name, deal_source, date_found FROM deals WHERE item_name LIKE '%CASE (%'").fetchall()
    for name, source, df in rows:
        new_name = re.sub(pattern, '', name, flags=re.I).strip()
        if new_name != name:
            print(f"DEALS: '{name}' -> '{new_name}'")
            try:
                cursor.execute("UPDATE deals SET item_name=? WHERE item_name=? AND deal_source=? AND date_found=?", (new_name, name, source, df))
            except sqlite3.IntegrityError:
                # Si por alguna razón ya existe el mismo juego ese día sin el CASE, borramos el duplicado con CASE
                cursor.execute("DELETE FROM deals WHERE item_name=? AND deal_source=? AND date_found=?", (name, source, df))
    
    # 2. Tabla BGG_MAPPING
    rows = cursor.execute("SELECT item_name FROM bgg_mapping WHERE item_name LIKE '%CASE (%'").fetchall()
    for (name,) in rows:
        new_name = re.sub(pattern, '', name, flags=re.I).strip()
        if new_name != name:
            print(f"MAPPING: '{name}' -> '{new_name}'")
            try:
                cursor.execute("UPDATE bgg_mapping SET item_name=? WHERE item_name=?", (new_name, name))
            except sqlite3.IntegrityError:
                # Si ya existe el nombre limpio en el mapping, borramos el que tiene CASE
                cursor.execute("DELETE FROM bgg_mapping WHERE item_name=?", (name,))

    # 3. Tabla GAMES (el nombre que bajó de BGG o el que asignamos)
    rows = cursor.execute("SELECT bgg_id, name FROM games WHERE name LIKE '%CASE (%'").fetchall()
    for b_id, name in rows:
        new_name = re.sub(pattern, '', name, flags=re.I).strip()
        if new_name != name:
            print(f"GAMES: '{name}' -> '{new_name}'")
            cursor.execute("UPDATE games SET name=? WHERE bgg_id=?", (new_name, b_id))

    conn.commit()
    conn.close()
    print(">>> Limpieza finalizada.")

if __name__ == "__main__":
    fix_db_case_names()
