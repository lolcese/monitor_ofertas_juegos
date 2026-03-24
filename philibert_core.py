import os
import requests
import sqlite3
import re
import time
import datetime
import difflib
import unicodedata
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# --- Configuración Compartida ---
load_dotenv()
TOKEN = os.getenv('token')
COOKIE = os.getenv('PHILIBERT_COOKIE')
DB_PATH = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
IMG_DIR = r'c:\Datos\Luis\bgg\Phillibert\assets\images'
LOG_PATH = r'c:\Datos\Luis\bgg\Phillibert\coincidencias_fallidas.txt'
LOG_HTML_PATH = r'c:\Datos\Luis\bgg\Phillibert\coincidencias_fallidas.html'

os.makedirs(IMG_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
if TOKEN: HEADERS["Authorization"] = f"Bearer {TOKEN}"
if COOKIE: HEADERS["Cookie"] = COOKIE

# --- Constantes de Filtrado ---
NOISE_RE = r'\b(core box|core game|jeu de base|boite de base|complete|bundle|big box|box|set|game|pack|edition|edicion|essentielle|essential|ancienne version|nouvelle version|en français|version|française|deluxe|collector|anniversary|impression|jeu|l\'âge|des|les|aux|de|la|le|extension|expansion|erw|erweiterung|printing|pression|copy|sundrop|standard|fr|en|de|es|promo|preorder|l\'aube|d\'un|stefan feld|uwe rosenberg|knizia|recharged|vital lacerda|lacerda|board game|jeu de plateau|token|tokens|galactic|galactic edition|card holder|standees|deck box|extra player pack)\b'
IGNORE_KEYWORDS = ['Jeu de Rôle', 'Jeu de Role', ' JDR', 'RPG', 'Livre de base', 'Warhammer', 'Citadel', 'Peinture']
GENERIC_TITLES = {'board game', 'jeu de plateau', 'extension', 'expansion', 'pack', 'set'}
TRANSLATIONS = {'royaute': 'regality', 'revolution': 'revolution', 'aube': 'dawn', 'tenebres': 'darkness', 'plateau': 'board'}

# --- Funciones de Utilidad ---
def get_db_connection(): return sqlite3.connect(DB_PATH)

def remove_accents(input_str):
    if not input_str: return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def norm_plain(s):
    s = s.lower().replace('&', ' and ')
    s = re.sub(r'(?<=\w)\.(?=\w)', '', s)
    s = re.sub(r'[:\-\–\(\)\.\/]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return remove_accents(s)

def is_rare_word(w, orig_word=""):
    if orig_word.isupper() and 2 <= len(orig_word) <= 4: return True
    common_words = {'the', 'of', 'in', 'and', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'an', 'is', 'it', 'was', 'were'}
    if not w or len(w) < 4: return False
    return w.lower() not in common_words

def download_image(url, product_id):
    if not url: return ""
    local_filename = f"{product_id}.jpg"
    local_path = os.path.join(IMG_DIR, local_filename)
    if os.path.exists(local_path): return local_filename
    try:
        res = requests.get(url, headers=HEADERS, timeout=10, stream=True)
        if res.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in res.iter_content(1024): f.write(chunk)
            return local_filename
    except: pass
    return ""

def is_philibert_excluded(url):
    try:
        time.sleep(1)
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, 'html.parser')
            body = soup.find('body')
            if not body: return False
            classes = " ".join(body.get('class', []))
            if any(k in classes for k in ['category-392', 'category-8000', 'category-1178', 'category-119']): return True
            bread = soup.find('div', class_='breadcrumb')
            if bread:
                b_text = bread.text.lower()
                if any(k in b_text for k in ['jeu de rôle', 'figurine', 'accessoire', 'jcc', 'jce']): return True
    except: pass
    return False

def is_hard_excluded(name):
    n_low = name.lower()
    return any(k in n_low for k in ['star wars: legion', 'star wars legion', 'card pack', 'booster pack'])

def log_failed_match(name, url, best_id, best_conf, candidates_dict, source='match'):
    if not candidates_dict: return
    html = ""
    if not os.path.exists(LOG_HTML_PATH):
        html = "<html><head><meta charset='utf-8'><style>table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:8px}tr.assigned{border:4px solid #007bff !important}a{text-decoration:none;color:#007bff}</style></head><body>"
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    html += f"<h3><a href='{url}' target='_blank'>[{source.upper()}] {name}</a> ({ts})</h3>"
    html += "<table><tr><th>ID BGG</th><th>Nombre</th><th>Score</th><th>Conf %</th></tr>"
    candidates = sorted(candidates_dict.values(), key=lambda x: x['score'], reverse=True)[:10]
    for c in candidates:
        is_a = str(c['id']) == str(best_id)
        html += f"<tr class='{'assigned' if is_a else ''}'><td>{c['id']}</td><td>{c['name']}</td><td>{c['score']:.1f}</td><td>{c['conf']:.1f}%</td></tr>"
    html += "</table><hr>"
    with open(LOG_HTML_PATH, 'a', encoding='utf-8') as f: f.write(html)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"\n--- {ts} | [{source.upper()}] '{name}' ---\nURL: {url}\nASIGNADO ID: {best_id} | Conf: {best_conf:.1f}%\n" + "-"*60 + "\n")

def save_deal(cursor, philibert_name, price, old_price, url, is_accessory, is_expansion, source, condition="", img_url=None):
    """Guarda una oferta en la base de datos y descarga su imagen de Philibert si existe."""
    # Descargar imagen de Philibert si se proporciona
    img_local = ""
    if img_url:
        # Generamos un nombre basado en el nombre de Philibert (limpio)
        clean_name = "".join(c for c in philibert_name if c.isalnum() or c in (' ', '-', '_')).strip()
        img_id = clean_name.replace(' ', '_').lower()
        img_local = download_image(img_id, img_url)

    cursor.execute("""
        INSERT INTO deals (philibert_name, price, old_price, url, date_found, is_accessory, is_expansion, deal_source, condition, image_local)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (philibert_name, price, old_price, url, datetime.date.today(), is_accessory, is_expansion, source, condition, img_local))

def init_db():
    with get_db_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS bgg_mapping (philibert_name TEXT PRIMARY KEY, bgg_id TEXT, last_search DATE, confidence REAL)')
        conn.execute('CREATE TABLE IF NOT EXISTS games (bgg_id TEXT PRIMARY KEY, name TEXT, last_updated DATE, rating TEXT, rank TEXT, type TEXT, language_dependency TEXT, original_name TEXT, weight TEXT, min_players INTEGER, max_players INTEGER, best_players TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS deals (philibert_name TEXT PRIMARY KEY, price TEXT, old_price TEXT, url TEXT, date_found DATE, is_accessory BOOLEAN, is_expansion BOOLEAN, deal_source TEXT, condition TEXT, image_local TEXT)')
        # Auto-reparación
        try: conn.execute('ALTER TABLE deals ADD COLUMN image_local TEXT')
        except: pass
        try: 
            conn.execute('ALTER TABLE games ADD COLUMN weight TEXT')
            conn.execute('ALTER TABLE games ADD COLUMN min_players INTEGER')
            conn.execute('ALTER TABLE games ADD COLUMN max_players INTEGER')
            conn.execute('ALTER TABLE games ADD COLUMN best_players TEXT')
            conn.execute('ALTER TABLE games ADD COLUMN language_dependency TEXT')
            conn.execute('ALTER TABLE games ADD COLUMN original_name TEXT')
        except: pass

def fetch_bgg_id(game_name, phili_url, source='match'):
    url = "https://boardgamegeek.com/xmlapi2/search"
    phili_plain = norm_plain(game_name)
    target_clean = re.sub(NOISE_RE, '', phili_plain, flags=re.I).strip()
    target_clean_words = set(re.findall(r'\w+', target_clean))
    
    raw_strategies = [f'"{game_name.strip()}"', game_name.strip(), target_clean]
    strategies = [s.lower().strip() for s in raw_strategies if len(s.strip()) >= 2]
    
    best_item, best_score, best_confidence, best_real_name = None, -5000, 0, ""
    all_candidates = {}

    for q in sorted(list(set(strategies)), key=len, reverse=True):
        time.sleep(1)
        try:
            res = requests.get(url, params={"query": q, "type": "boardgame,boardgameexpansion"}, headers=HEADERS, timeout=10)
            if res.status_code != 200: continue
            soup = BeautifulSoup(res.content, 'xml')
            for item in soup.find_all('item')[:20]:
                b_id = item['id']; b_orig = (item.find('name', attrs={'type': 'primary'}) or item.find('name'))['value']
                b_plain = norm_plain(b_orig); b_clean = re.sub(NOISE_RE, '', b_plain, flags=re.I).strip()
                b_clean_words = set(re.findall(r'\w+', b_clean))
                
                score = 0; matches = sum(1 for tw in target_clean_words if any(difflib.SequenceMatcher(None, tw, bw).ratio() > 0.85 for bw in b_clean_words))
                if matches >= len(target_clean_words): score += 2500
                if b_clean == target_clean: score += 5000
                
                conf = (matches / max(len(target_clean_words), 1)) * 100
                if b_id not in all_candidates or score > all_candidates[b_id]['score']:
                    all_candidates[b_id] = {'id': b_id, 'name': b_orig, 'score': score, 'conf': conf}
                if score > best_score: best_score, best_item, best_confidence, best_real_name = score, b_id, conf, b_orig
        except: continue
        if best_confidence >= 100: break
    
    if is_hard_excluded(game_name): return "IGNORED", 0, ""
    if best_confidence < 90 and is_philibert_excluded(phili_url): return "IGNORED", 0, ""
    if 0 < best_confidence < 95: log_failed_match(game_name, phili_url, best_item, best_confidence, all_candidates, source)
    return best_item, best_confidence, best_real_name

def fetch_details(bgg_id):
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
    time.sleep(1)
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, 'xml')
        item = soup.find('item')
        if not item: return "N/A", "999999", "Unknown", "-", "", "N/A", 0, 0, "-"
        
        rat = "N/A"
        rnk = "999999" # Default value for rank
        
        stats = item.find('statistics')
        if stats:
            avg = stats.find('average'); rat = f"{float(avg.get('value', 0)):.1f}" if avg else "N/A"
            
            rank_tag = stats.find('rank', attrs={'name': 'boardgame'})
            if rank_tag and rank_tag.get('value') and rank_tag['value'].isdigit():
                rnk = rank_tag['value']
        
        o_name = (item.find('name', attrs={'type': 'primary'}) or item.find('name'))['value']
        l_dep = "-"
        poll = item.find('poll', attrs={'name': 'language_dependence'})
        if poll: 
            v_max = -1
            for r in poll.find_all('result'):
                if int(r.get('numvotes', 0)) > v_max:
                    v_max = int(r.get('numvotes', 0))
                    l_dep = r.get('value', "-")

        weight = "N/A"
        avg_w = item.find('averageweight')
        if avg_w: weight = f"{float(avg_w.get('value', 0)):.1f}"
        
        min_p = int(item.find('minplayers').get('value', 0))
        max_p = int(item.find('maxplayers').get('value', 0))
        
        best_p, v_best = "-", -1
        poll_p = item.find('poll', attrs={'name': 'suggested_numplayers'})
        if poll_p:
            for res_p in poll_p.find_all('results'):
                for opt in res_p.find_all('result', attrs={'value': 'Best'}):
                    if int(opt.get('numvotes', 0)) > v_best:
                        v_best = int(opt.get('numvotes', 0))
                        best_p = res_p.get('numplayers', "-")
        
        return rat, rnk, item.get('type', 'Unknown'), l_dep, o_name, weight, min_p, max_p, best_p
    except Exception as e:
        print(f"Error en fetch_details({bgg_id}): {e}")
        return "N/A", "N/A", "Unknown", "-", "", "N/A", 0, 0, "-"
