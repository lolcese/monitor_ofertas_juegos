import sqlite3
import re
from monitor_core import get_db_connection, NOISE_RE

def clean_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Patrones de ruido (incluyendo los nuevos añadidos)
    # Algunos ya están en NOISE_RE pero para estar seguros los detallamos
    PATS = [
        r'\(Clearance\)', r'\(Last Chance\)', r'\(New Arrival\)', r'\(Preorder\)',
        r' - Occasion', r'\s*CASE\s*\(\d+\)', r'\s*\d+(st|nd|rd|th)\s+edition',
        r'\(.*?edition\)', r'\[.*?edition\]',
        r'PREVENTA', r'RESERVALO', r'ver fecha'
    ]
    COMBINED = re.compile('|'.join(PATS), re.I)
    
    print(">>> Iniciando limpieza profunda de nombres en la base de datos...")
    
    # 1. Obtener todos los mapeos actuales para evitar duplicados al renombrar
    # (Si renombramos "Juego (Clearance)" a "Juego" y "Juego" ya existía)
    mapping_changes = []
    
    # Primero Deals
    print("   Limpiando tabla 'deals'...")
    rows = cursor.execute("SELECT rowid, item_name FROM deals").fetchall()
    d_count = 0
    for rowid, name in rows:
        new_name = COMBINED.sub('', name).strip()
        new_name = " ".join(new_name.split()) # Quitar espacios dobles
        if new_name != name:
            try:
                cursor.execute("UPDATE deals SET item_name = ? WHERE rowid = ?", (new_name, rowid))
                d_count += 1
            except sqlite3.IntegrityError:
                # Colisión: ya existe un registro con el nombre limpio para esta fuente/fecha
                cursor.execute("DELETE FROM deals WHERE rowid = ?", (rowid,))
            
    # Luego BGG Mapping
    print("   Limpiando tabla 'bgg_mapping' y unificando registros...")
    m_count = 0
    rows = cursor.execute("SELECT item_name, bgg_id, confidence, last_search FROM bgg_mapping").fetchall()
    for name, b_id, conf, ls in rows:
        new_name = COMBINED.sub('', name).strip()
        new_name = " ".join(new_name.split())
        if new_name != name:
            # Intentar actualizar. Si falla por UNIQUE, nos quedamos con el mejor (el que ya existía o este)
            try:
                cursor.execute("UPDATE bgg_mapping SET item_name = ? WHERE item_name = ?", (new_name, name))
                m_count += 1
            except sqlite3.IntegrityError:
                # Ya existe un registro con el nombre limpio. 
                # Si el actual tiene ID pero el existente no, podríamos priorizar, 
                # pero por simplicidad borramos el ruidoso para que mande el limpio.
                cursor.execute("DELETE FROM bgg_mapping WHERE item_name = ?", (name,))
                m_count += 1

    conn.commit()
    conn.close()
    print(f"\n>>> Limpieza finalizada.")
    print(f"    - Deals actualizados: {d_count}")
    print(f"    - Mappings unificados: {m_count}")

if __name__ == "__main__":
    clean_db()
