import sqlite3
import os
from philibert_core import IMG_DIR, fetch_details, download_image

def fix_all_image_paths():
    db_path = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
    conn = sqlite3.connect(db_path)
    print("Saneando rutas de imágenes para TODAS las ofertas...")
    
    # 1. Obtenemos todas las ofertas junto con su bgg_id del mapeo
    deals = conn.execute("""
        SELECT d.philibert_name, m.bgg_id 
        FROM deals d
        INNER JOIN bgg_mapping m ON d.philibert_name = m.philibert_name
    """).fetchall()
    
    count = 0
    for philibert_name, bgg_id in deals:
        if not bgg_id: continue
        # La ruta correcta debe ser SIEMPRE C:\...\assets\images\<bgg_id>.jpg
        correct_path = os.path.join(IMG_DIR, f"{bgg_id}.jpg")
        
        # 2. Actualizamos la base de datos
        conn.execute("UPDATE deals SET image_local = ? WHERE philibert_name = ?", (correct_path, philibert_name))
        
        # 3. Nos aseguramos de que el archivo exista, si no, lo bajamos
        if not os.path.exists(correct_path):
            print(f"Descargando imagen faltante para ID: {bgg_id}...")
            details = fetch_details(bgg_id)
            if details and details[4]: # index 4 es img_url
                download_image(bgg_id, details[4])
        
        count += 1
    
    conn.commit()
    print(f"Base de datos ACTUALIZADA: {count} rutas de imágenes corregidas.")
    conn.close()

if __name__ == "__main__":
    fix_all_image_paths()
