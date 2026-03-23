import os
import sqlite3
import requests
import time
import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# --- Configuración ---
load_dotenv()
TOKEN = os.getenv('token')
DB_PATH = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

def fetch_details(bgg_id):
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
    time.sleep(1.5) # Un poco más de calma para evitar 429
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, 'xml')
            item = soup.find('item')
            if not item: return "-", ""
            
            # Nombre Primario (usando atributo value)
            name_tag = item.find('name', attrs={'type': 'primary'}) or item.find('name')
            o_name = name_tag.get('value', '') if name_tag else ""
            
            # Dependencia de Idioma (Poll: language_dependence)
            l_dep = "-"
            poll = item.find('poll', attrs={'name': 'language_dependence'})
            if poll:
                max_v = -1
                best_opt = "-"
                # Buscamos en los resultados de la encuesta
                for result in poll.find_all('result'):
                    try:
                        v = int(result.get('numvotes', 0))
                        if v > max_v:
                            max_v = v
                            best_opt = result.get('value', "-")
                    except: continue
                l_dep = best_opt
            return l_dep, o_name
    except Exception as e:
        print(f"Error en ID {bgg_id}: {e}")
    return "-", ""

def init_missing_cols(conn):
    c = conn.cursor()
    try: c.execute("ALTER TABLE games ADD COLUMN language_dependency TEXT")
    except: pass
    try: c.execute("ALTER TABLE games ADD COLUMN original_name TEXT")
    except: pass

def refresh_metadata():
    if not os.path.exists(DB_PATH):
        print(f"Error: No se encuentra la base de datos en {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    init_missing_cols(conn)
    c = conn.cursor()
    
    # Buscamos juegos que no tengan idioma o nombre original
    c.execute("SELECT bgg_id, name FROM games WHERE language_dependency IS NULL OR language_dependency = '-' OR original_name IS NULL OR original_name = ''")
    rows = c.fetchall()
    
    if not rows:
        print("Todos los juegos ya tienen metadatos de idioma y nombre original.")
        conn.close()
        return

    print(f"Refrescando metadatos para {len(rows)} juegos usando TOKEN...")
    
    count = 0
    for b_id, local_name in rows:
        l_dep, o_name = fetch_details(b_id)
        if o_name or l_dep != "-":
            c.execute("UPDATE games SET language_dependency=?, original_name=? WHERE bgg_id=?", (l_dep, o_name, b_id))
            conn.commit()
            print(f"[{b_id}] {local_name} -> {o_name} | {l_dep}")
            count += 1
        else:
            print(f"[{b_id}] {local_name} -> Sin datos (posible rate limit o ID inexistante)")
            time.sleep(2) # Pausa extra si falla
            
    conn.close()
    print(f"\nProceso finalizado. Se han actualizado {count} juegos.")

if __name__ == "__main__":
    refresh_metadata()
