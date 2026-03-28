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

os.makedirs(IMG_DIR, exist_ok=True)

HEADERS_GENERIC = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/xml, text/xml, */*"
}

HEADERS_BGG = HEADERS_GENERIC.copy()
if TOKEN: HEADERS_BGG["Authorization"] = f"Bearer {TOKEN}"

HEADERS_PHILI = HEADERS_GENERIC.copy()
if COOKIE: HEADERS_PHILI["Cookie"] = COOKIE

# --- Motor de Limpieza Pulido ---
NOISE_RE = r'\b(core box|core game|jeu de base|boite de base|complete|bundle|big box|box|set|game|pack|edition|edicion|essentielle|essential|ancienne version|nouvelle version|en français|version|française|deluxe|collector|anniversary|impression|jeu|l\'âge|des|les|aux|de|la|le|extension|expansion|erw|erweiterung|printing|pression|copy|sundrop|standard|fr|en|de|es|promo|preorder|l\'aube|d\'un|stefan feld|uwe rosenberg|knizia|recharged|vital lacerda|lacerda|board game|jeu de plateau|token|tokens|galactic|galactic edition|card holder|standees|deck box|extra player pack|clearance|last chance|occasions?|flash sales?|sales?|backdoor|miniature market|philibert)\b'
IGNORE_KEYWORDS = ['Jeu de Rôle', 'Jeu de Role', ' JDR', 'RPG', 'Livre de base', 'Warhammer', 'Citadel', 'Peinture', 'Pinceau', 'Colle']

def get_db_connection(timeout=60): 
    conn = sqlite3.connect(BGG_CACHE_DB, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL") 
    return conn
def remove_accents(s): return "".join([c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)]) if s else ""
def norm_plain(s):
    if not s: return ""
    s = s.lower().replace('&', ' and ')
    s = re.sub(r'(?<=\w)\.(?=\w)', '', s)
    s = re.sub(r'[:\-\–\(\)\.\/]', ' ', s)
    return remove_accents(re.sub(r'\s+', ' ', s).strip())

def download_image(url, product_id, source=None):
    if not url: return ""
    lf = f"{product_id}.jpg"; lp = os.path.join(IMG_DIR, lf)
    if os.path.exists(lp): return lf
    headers = HEADERS_PHILI if source == 'philibert' else HEADERS_GENERIC
    try:
        res = requests.get(url, headers=headers, timeout=12, stream=True)
        if res.status_code == 200:
            with open(lp, 'wb') as f:
                for chunk in res.iter_content(1024): f.write(chunk)
            return lf
    except: pass
    return ""

def init_db():
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('CREATE TABLE IF NOT EXISTS bgg_mapping (item_name TEXT PRIMARY KEY, bgg_id TEXT, last_search DATE, confidence REAL)')
            conn.execute('CREATE TABLE IF NOT EXISTS games (bgg_id TEXT PRIMARY KEY, name TEXT, last_updated DATE, rating TEXT, rank TEXT, type TEXT, language_dependency TEXT, original_name TEXT, weight TEXT, min_players INTEGER, max_players INTEGER, best_players TEXT)')
            conn.execute('CREATE TABLE IF NOT EXISTS deals (item_name TEXT, price TEXT, old_price TEXT, url TEXT, date_found DATE, is_accessory BOOLEAN, is_expansion BOOLEAN, deal_source TEXT, condition TEXT, image_local TEXT, PRIMARY KEY (item_name, deal_source))')
    finally:
        conn.close()

def save_deal(cursor, item_name, price, old_price, url, is_accessory, is_expansion, source, condition="", img_url=None):
    today = datetime.date.today().isoformat(); img_local = ""
    if img_url:
        clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', item_name).lower()
        img_local = download_image(img_url, clean_name, source='philibert' if 'phili' in source.lower() else 'generic')
    cursor.execute("INSERT OR REPLACE INTO deals (item_name, price, old_price, url, date_found, is_accessory, is_expansion, deal_source, condition, image_local) VALUES (?,?,?,?,?,?,?,?,?,?)", (item_name, price, old_price, url, today, is_accessory, is_expansion, source, condition, img_local))

def fetch_bgg_id(game_name, phili_url=None, source='match'):
    print(f"Buscando en BGG: '{game_name}'...")
    url = "https://boardgamegeek.com/xmlapi2/search"
    
    # 1. Limpieza inicial pulida
    name_clean = re.sub(r'\(.*?\)|\[.*?\]', '', game_name) # Quitar todo lo que esté entre paréntesis
    name_clean = re.sub(NOISE_RE, '', name_clean, flags=re.I).strip()
    
    # Estrategias de búsqueda: Nombre completo, Nombre hasta el primer : o -, y el nombre original
    strategies = [name_clean, game_name.strip()]
    if ':' in name_clean: strategies.append(name_clean.split(':')[0].strip())
    if '-' in name_clean: strategies.append(name_clean.split('-')[0].strip())
    # Para casos muy largos con ':' y '-', el nombre hasta el primer separador es útil
    primera_parte = re.split(r'[:\-]', name_clean)[0].strip()
    if len(primera_parte) > 5: strategies.append(primera_parte)

    target_plain = norm_plain(name_clean)
    target_words = set(re.findall(r'\w+', target_plain))
    
    best_item, best_score, best_confidence, best_real_name = None, -100, 0, ""

    # Ordenamos estrategias por longitud descendente para intentar el match más preciso primero
    for q in sorted(list(set(strategies)), key=len, reverse=True):
        if len(q) < 4: continue # Evitar búsquedas de 3 letras que devuelven miles de resultados
        time.sleep(random.uniform(2.5, 4.5)) # Pausa prudente
        try:
            res = requests.get(url, params={"query": q, "exact": 0}, headers=HEADERS_BGG, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.content, 'xml')
                items = soup.find_all('item')
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
                    
                    if score > best_score:
                        best_score, best_item, best_confidence, best_real_name = score, b_id, conf, b_orig
            elif res.status_code == 401:
                print("Error 401: Token inválido.") ; break
            elif res.status_code == 429:
                print("Error 429: Rate limit. Pausando 60s...") ; time.sleep(60)
            
            # Si ya tenemos un match muy bueno (>95% confianza y score alto), no seguimos con estrategias más cortas
            if best_confidence >= 95 and best_score >= 80: break
        except Exception as e:
            print(f"Error en búsqueda: {e}")
            time.sleep(5)
            
    return best_item, best_confidence

def fetch_details(bgg_id):
    if not bgg_id or bgg_id == "IGNORED": return "N/A", "999999", "Unknown", "-", "Unknown", "N/A", 0, 0, "-"
    print(f"Bajando detalles BGG ID {bgg_id}...")
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
    
    for attempt in range(3):
        time.sleep(random.uniform(3.0, 5.0)) # Pausa entre detalles
        try:
            res = requests.get(url, headers=HEADERS_BGG, timeout=22)
            if res.status_code == 200:
                soup = BeautifulSoup(res.content, 'xml')
                item = soup.find('item')
                if not item: return "N/A", "999999", "Unknown", "-", "Unknown", "N/A", 0, 0, "-"
                
                stats = item.find('statistics'); rat, rnk = "N/A", "999999"
                if stats:
                    avg = stats.find('average')
                    rat = f"{float(avg['value']):.1f}" if (avg and avg.get('value') and avg['value'] != '0') else "N/A"
                    rank_tag = stats.find('rank', attrs={'name': 'boardgame'})
                    if rank_tag and rank_tag.get('value') and rank_tag['value'].isdigit(): rnk = rank_tag['value']
                
                name_tag = item.find('name', attrs={'type': 'primary'}) or item.find('name')
                o_name = name_tag['value'] if name_tag else "Unknown"
                
                l_dep = "-"
                poll = item.find('poll', attrs={'name': 'language_dependence'})
                if poll:
                    v_max = -1
                    for r in poll.find_all('result'):
                        if int(r.get('numvotes', 0)) >= v_max: v_max = int(r.get('numvotes', 0)); l_dep = r.get('value', "-")

                weight = "N/A"
                avg_w = item.find('averageweight') or (stats.find('averageweight') if stats else None)
                if avg_w and avg_w.get('value') and avg_w['value'] != '0': weight = f"{float(avg_w['value']):.1f}"
                
                min_p = int(item.find('minplayers')['value']) if item.find('minplayers') else 0
                max_p = int(item.find('maxplayers')['value']) if item.find('maxplayers') else 0
                
                best_p, v_best = "-", -1
                poll_p = item.find('poll', attrs={'name': 'suggested_numplayers'})
                if poll_p:
                    for res_p in poll_p.find_all('results'):
                        for opt in res_p.find_all('result', attrs={'value': 'Best'}):
                            if int(opt.get('numvotes', 0)) > v_best: v_best = int(opt.get('numvotes', 0)); best_p = res_p.get('numplayers', "-")
                
                return rat, rnk, item.get('type', 'Unknown'), l_dep, o_name, weight, min_p, max_p, best_p
            elif res.status_code in [429, 401]:
                print(f"Error {res.status_code}. Pausando...")
                time.sleep(30)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
    return "N/A", "999999", "Unknown", "-", "Unknown", "N/A", 0, 0, "-"

if __name__ == "__main__":
    init_db()
