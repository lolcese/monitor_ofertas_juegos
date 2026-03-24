import sqlite3

def fix_ranks():
    db_path = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
    conn = sqlite3.connect(db_path)
    print("Limpiando rankings fantasmales...")
    
    # Convertimos los '', 'Not Ranked' y NULLs al número de control 999999
    conn.execute("UPDATE games SET rank = '999999' WHERE rank = '' OR rank = 'Not Ranked' OR rank IS NULL")
    conn.commit()
    print(f"Base de datos SANEADA: {conn.total_changes} cambios realizados.")
    conn.close()

if __name__ == "__main__":
    fix_ranks()
