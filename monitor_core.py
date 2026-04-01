import os
import requests
import sqlite3
import re
import time
import datetime
import difflib
import unicodedata
import random
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# --- Configuración Compartida ---
load_dotenv()
TOKEN = os.getenv('token')
COOKIE = os.getenv('PHILIBERT_COOKIE')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BGG_CACHE_DB = os.path.join(BASE_DIR, 'bgg_cache.db')
IMG_DIR = os.path.join(BASE_DIR, 'assets', 'images')
LOG_HTML_PATH = os.path.join(BASE_DIR, 'coincidencias_fallidas.html')
SEARCH_LOG = os.path.join(BASE_DIR, 'bgg_search.log')

os.makedirs(IMG_DIR, exist_ok=True)

def log_search(msg):
    try:
        with open(SEARCH_LOG, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except: pass

HEADERS_GENERIC = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
}

HEADERS_BGG = HEADERS_GENERIC.copy()
if TOKEN: HEADERS_BGG["Authorization"] = f"Bearer {TOKEN}"

HEADERS_PHILI = HEADERS_GENERIC.copy()
if COOKIE: HEADERS_PHILI["Cookie"] = COOKIE

# --- Motor de Limpieza Pulido ---
NOISE_RE = r'\b(core box|core game|jeu de base|boite de base|complete|bundle|big box|box|set|game|pack|edition|edicion|essentielle|essential|ancienne version|nouvelle version|en français|version|française|extension|expansion|deluxe|collector|anniversary|impression|jeu|l\'âge|des|les|aux|de|la|le|(\+?\s*)?expansi[oó]n|erw|erweiterung|printing|pression|copy|sundrop|standard|fr|en|de|es|promo|preorder|l\'aube|d\'un|stefan feld|uwe rosenberg|knizia|recharged|vital lacerda|lacerda|board game|jeu de plateau|token|tokens|galactic|galactic edition|card holder|standees|deck box|extra player pack|clearance|last chance|occasions?|flash sales?|sales?|backdoor|miniature market|philibert|case|case\s*\(\d+\)|\d+(st|nd|rd|th)(\s+edition)?)\b'
IGNORE_KEYWORDS = ['Jeu de Rôle', 'Jeu de Role', ' JDR', 'RPG', 'Livre de base', 'Warhammer', 'Citadel', 'Peinture', 'Pinceau', 'Colle', 'Puzzle', 'Puzzles', '1000 Pièces', '500 Pièces', 'Neoprene Mat', 'Playmat', 'Play Mat', 'Tapis', 'Insert', 'Inserts', 'Sleeves', 'Gaming Mat', 'Game Mat', 'Protector', 'Protege-cartes', 'Supplément', 'Scénario', 'Scénarios', 'Ecran', 'Écran', 'MJ', 'Livre de règles']

def get_db_connection(timeout=60): 
    conn = sqlite3.connect(BGG_CACHE_DB, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL") 
    return conn

def remove_accents(s): return "".join([c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)]) if s else ""

def norm_plain(s):
    if not s: return ""
    s = remove_accents(s.lower())
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    return " ".join(s.split())

def download_image(url, name, source='generic'):
    if not url: return None
    clean_name = re.sub(r'[^a-z0-9]', '_', name.lower())
    filename = f"{clean_name}.jpg"
    path = os.path.join(IMG_DIR, filename)
    if os.path.exists(path): return filename
    try:
        res = requests.get(url, headers=HEADERS_GENERIC, stream=True, timeout=10)
        if res.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in res.iter_content(1024): f.write(chunk)
            return filename
    except: pass
    return None

def save_deal(cursor, item_name, price, old_price, url, is_accessory, is_expansion, source, condition="", img_url=None):
    today = datetime.date.today().isoformat()
    img_local = None
    if img_url:
        clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', item_name).lower()
        img_local = download_image(img_url, clean_name, source='philibert' if 'phili' in source.lower() else 'generic')
    
    # 1. Buscar si ya existe para conservar su fecha original de aparición
    cursor.execute("SELECT date_first_seen FROM deals WHERE url = ? AND deal_source = ?", (url, source))
    existing = cursor.fetchone()
    first_seen = existing[0] if (existing and existing[0]) else today
    
    # 2. Prevenir duplicados por URL (si el nombre cambió pero la URL es la misma)
    cursor.execute("DELETE FROM deals WHERE url = ? AND deal_source = ?", (url, source))
    
    # 3. Guardar el deal, manteniendo la fecha original (o la de hoy si es nuevo)
    cursor.execute("INSERT OR REPLACE INTO deals (item_name, price, old_price, url, date_found, is_accessory, is_expansion, deal_source, condition, image_local, date_first_seen) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (item_name, price, old_price, url, today, is_accessory, is_expansion, source, condition, img_local, first_seen))

def fetch_bgg_id(game_name, phili_url=None, source='match'):
    buffer = []
    def log(m): buffer.append(m)
    
    log(f"--- INICIO BÚSQUEDA: '{game_name}' ---")
    url = "https://boardgamegeek.com/xmlapi2/search"
    
    # 1. Limpieza inicial pulida
    name_clean = re.sub(r'\(.*?\)|\[.*?\]', '', game_name)
    name_clean = re.sub(NOISE_RE, '', name_clean, flags=re.I).strip()
    
    strategies = [name_clean, game_name.strip()]
    if ':' in name_clean: strategies.append(name_clean.split(':')[0].strip())
    if '-' in name_clean: strategies.append(name_clean.split('-')[0].strip())
    
    parts = re.split(r'[:\-]', name_clean)
    primera_parte = parts[0].strip()
    if len(primera_parte) > 5: strategies.append(primera_parte)
    
    # Estrategia agresiva: primera palabra significativa si no hay resultados
    words = [w for w in re.findall(r'\w+', name_clean) if len(w) > 3]
    if words: strategies.append(words[0])

    log(f"Estrategias: {list(set(strategies))}")
    
    target_plain = norm_plain(name_clean)
    target_words = set(re.findall(r'\w+', target_plain))
    
    best_item, best_score, best_confidence = None, -100, 0

    for q in sorted(list(set(strategies)), key=len, reverse=True):
        if len(q) < 4: continue
        log(f"  > Probando query: '{q}'")
        time.sleep(random.uniform(2.5, 4.5))
        try:
            res = requests.get(url, params={"query": q, "exact": 0}, headers=HEADERS_BGG, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.content, 'xml')
                items = soup.find_all('item')
                log(f"    Encontrados {len(items)} resultados.")
                for item in items[:25]:
                    b_id = item['id']
                    name_tag = item.find('name', attrs={'type': 'primary'}) or item.find('name')
                    if not name_tag: continue
                    b_orig = name_tag['value']
                    b_type = item.get('type', 'boardgame')
                    if b_type not in ['boardgame', 'boardgameexpansion']: continue
                    
                    b_plain = norm_plain(b_orig)
                    b_words = set(re.findall(r'\w+', b_plain))
                    ratio = difflib.SequenceMatcher(None, target_plain, b_plain).ratio()
                    matches = sum(1 for tw in target_words if any(difflib.SequenceMatcher(None, tw, bw).ratio() > 0.8 for bw in b_words))
                    
                    score = ratio * 100
                    if b_plain == target_plain: score += 500
                    if target_plain in b_plain: score += 200
                    conf = (matches / max(len(target_words), 1)) * 100
                    
                    log(f"    - Candidato: [{b_id}] {b_orig} (Conf: {conf:.1f}%, Score: {score:.1f})")
                    
                    # PRIORIDAD: Confianza (coincidencia de palabras) > Score (similitud de cadena)
                    if conf > best_confidence or (conf == best_confidence and score > best_score) or \
                       (conf == best_confidence and score == best_score and b_id.isdigit() and int(b_id) > int(best_item or 0)):
                        best_score, best_item, best_confidence = score, b_id, conf
            elif res.status_code == 429:
                log(f"    ERROR 429: Rate limit detectado. Pausando 60s...")
                time.sleep(60)
            
            if best_confidence >= 95 and best_score >= 80:
                log(f"  Match perfecto encontrado con '{q}'.")
                break
        except Exception as e:
            log(f"    ERROR: {str(e)}")
            continue
    
    if best_confidence <= 50:
        log(f"  > Intentando búsqueda via Google (site:boardgamegeek.com)...")
        try:
            from googlesearch import search
            query = f'site:boardgamegeek.com/boardgame {game_name}'
            log(f"    Query: {query}")
            # Fix: googlesearch v3 uses 'num' instead of 'num_results', and 'stop' for total results
            for url in search(query, num=5, stop=5, pause=2.0, lang="en"):
                if 'boardgameaccessory' in url or 'rpgitem' in url:
                    log(f"    SKIPPING Non-Game: {url}")
                    continue
                # Capturar ID desde URL tipo: .../boardgame/XXXXX/name
                match = re.search(r'boardgame/(\d+)', url)
                if match:
                    g_id = match.group(1)
                    log(f"    Encontrado ID via Google: {g_id} (URL: {url})")
                    # Validamos el ID bajando sus detalles mínimos
                    log(f"    Validando ID {g_id}...")
                    details = fetch_details(g_id)
                    if details and details[4] != "Unknown":
                        best_item = g_id
                        best_confidence = 85 # Confianza alta por Google + Validación
                        log(f"    ID {g_id} validado correctamente.")
                        break
        except Exception as ge:
            log(f"    Fallo búsqueda Google: {str(ge)}")

    if best_item and best_confidence >= 60:
        log(f"GANADOR: ID {best_item} con {best_confidence:.1f}% confianza.")
    else:
        best_item = None
        log("FALLIDO: No se encontró ninguna coincidencia aceptable.")
    log("-" * 50)
    
    # SOLO guardar en log si la confianza NO es 100%
    if best_confidence < 100:
        for m in buffer:
            log_search(m)
            
    return best_item, best_confidence

def fetch_details(bgg_id):
    if not bgg_id or bgg_id in ["IGNORED", "WAITING"] or not str(bgg_id).isdigit(): return "N/A", "999999", "Unknown", "-", "Unknown", "N/A", 0, 0, "-"
    print(f"Bajando detalles BGG ID {bgg_id}...")
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
    
    for attempt in range(3):
        time.sleep(random.uniform(3.0, 5.0))
        try:
            res = requests.get(url, headers=HEADERS_BGG, timeout=22)
            if res.status_code == 200:
                soup = BeautifulSoup(res.content, 'xml')
                item = soup.find('item')
                if not item: return "N/A", "999999", "Unknown", "-", "Unknown", "N/A", 0, 0, "-"
                
                rat, rnk, weight = "0", "999999", "N/A"
                stats = item.find('statistics')
                if stats:
                    rat_tag = stats.find('ratings')
                    avg = rat_tag.find('average')
                    if avg and avg.get('value') and avg['value'] != '0': rat = f"{float(avg['value']):.1f}"
                    w_tag = rat_tag.find('averageweight')
                    if w_tag and w_tag.get('value') and float(w_tag['value']) > 0: weight = f"{float(w_tag['value']):.2f}"
                    rank_tag = stats.find('rank', attrs={'name': 'boardgame'})
                    if rank_tag and rank_tag.get('value') and rank_tag['value'].isdigit(): rnk = rank_tag['value']
                
                name_tag = item.find('name', attrs={'type': 'primary'}) or item.find('name')
                o_name = name_tag['value'] if name_tag else "Unknown"
                
                l_dep = "-"
                poll = item.find('poll', attrs={'name': 'language_dependence'})
                if poll:
                    best_v = 0; best_val = "-"
                    for res_v in poll.find_all('result'):
                        v_num = int(res_v['numvotes'])
                        if v_num > best_v:
                            best_v = v_num
                            best_val = res_v['value']
                    l_dep = best_val
                
                # minp, maxp, bestp
                min_p_tag = item.find('minplayers')
                min_p = int(min_p_tag['value']) if min_p_tag else 0
                max_p_tag = item.find('maxplayers')
                max_p = int(max_p_tag['value']) if max_p_tag else 0
                
                best_p = "-"
                poll_p = item.find('poll', attrs={'name': 'suggested_numplayers'})
                if poll_p:
                    for results in poll_p.find_all('results'):
                        best_vote = 0
                        for res_opt in results.find_all('result'):
                            if res_opt['value'] == 'Best':
                                v_num = int(res_opt['numvotes'])
                                if v_num > best_vote:
                                    best_vote = v_num
                                    best_p = results['numplayers']
                
                return rat, rnk, item.get('type', 'Unknown'), l_dep, o_name, weight, min_p, max_p, best_p
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
    return "N/A", "999999", "Unknown", "-", "Unknown", "N/A", 0, 0, "-"

def init_db():
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('CREATE TABLE IF NOT EXISTS deals (item_name TEXT, price TEXT, old_price TEXT, url TEXT, date_found DATE, is_accessory INTEGER, is_expansion INTEGER, deal_source TEXT, condition TEXT, image_local TEXT, date_first_seen DATE, PRIMARY KEY (item_name, deal_source, date_found))')
            # Migración: Añadir columna si no existe
            try: conn.execute('ALTER TABLE deals ADD COLUMN date_first_seen DATE')
            except sqlite3.OperationalError: pass
            
            conn.execute('CREATE TABLE IF NOT EXISTS bgg_mapping (item_name TEXT PRIMARY KEY, bgg_id TEXT, confidence FLOAT, last_search DATE)')
            conn.execute('CREATE TABLE IF NOT EXISTS games (bgg_id TEXT PRIMARY KEY, name TEXT, rating TEXT, rank TEXT, type TEXT, last_updated DATE, language_dependency TEXT, original_name TEXT, weight TEXT, min_players INTEGER, max_players INTEGER, best_players TEXT)')
    finally:
        conn.close()
