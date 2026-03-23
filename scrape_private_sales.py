import os
import requests
import re
import sys
import time
import datetime
import sqlite3
import difflib
import unicodedata
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# --- Configuración ---
load_dotenv()
TOKEN = os.getenv('token')
COOKIE = os.getenv('PHILIBERT_COOKIE')
DB_PATH = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
LOG_PATH = r'c:\Datos\Luis\bgg\Phillibert\coincidencias_fallidas.txt'
LOG_HTML_PATH = r'c:\Datos\Luis\bgg\Phillibert\coincidencias_fallidas.html'
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
if TOKEN: HEADERS["Authorization"] = f"Bearer {TOKEN}"
if COOKIE: HEADERS["Cookie"] = COOKIE

# Diccionario de Ruido
NOISE_RE = r'\b(core box|core game|jeu de base|boite de base|complete|bundle|big box|box|set|game|pack|edition|edicion|essentielle|essential|ancienne version|nouvelle version|en français|version|française|deluxe|collector|anniversary|impression|jeu|l\'âge|des|les|aux|de|la|le|extension|expansion|erw|erweiterung|printing|pression|copy|sundrop|standard|fr|en|de|es|promo|preorder|l\'aube|d\'un|stefan feld|uwe rosenberg|knizia|recharged|vital lacerda|lacerda|board game|jeu de plateau|token|tokens|galactic|galactic edition|card holder|standees|deck box|extra player pack)\b'

IGNORE_KEYWORDS = ['Jeu de Rôle', 'Jeu de Role', ' JDR', 'RPG', 'Livre de base', 'Warhammer', 'Citadel', 'Peinture']
GENERIC_TITLES = {'board game', 'jeu de plateau', 'extension', 'expansion', 'pack', 'set'}
TRANSLATIONS = {'royaute': 'regality', 'revolution': 'revolution', 'aube': 'dawn', 'tenebres': 'darkness', 'plateau': 'board'}

def remove_accents(input_str):
    if not input_str: return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def is_rare_word(w, orig_word=""):
    if orig_word.isupper() and 2 <= len(orig_word) <= 4: return True
    common_words = {'the', 'of', 'in', 'and', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'an', 'is', 'it'}
    if not w or len(w) < 4: return False
    return w.lower() not in common_words

def is_philibert_excluded(url):
    """Verifica si el producto pertenece a Rol, Figuritas o Accesorios entrando en su página."""
    try:
        time.sleep(0.5)
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, 'html.parser')
            body = soup.find('body')
            if not body: return False
            classes = " ".join(body.get('class', []))
            # IDs: 392 (Rol), 8000+ (Figuritas), 1178 (Accesorios), 119 (JCC/JCE)
            if any(k in classes for k in ['category-392', 'category-8000', 'category-1178', 'category-119', 'category-jeux-de-role', 'category-jeux-de-figurines', 'category-accessoires']):
                return True
            # Breadcrumbs como backup
            bread = soup.find('div', class_='breadcrumb')
            if bread:
                b_text = bread.text.lower()
                if any(k in b_text for k in ['jeu de rôle', 'jeux de rôle', 'figurine', 'accessoire', 'collectionner', 'évolutif', 'jcc', 'jce']):
                    return True
    except: pass
    return False

def get_db_connection(): return sqlite3.connect(DB_PATH)

def init_db():
    with get_db_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS bgg_mapping (philibert_name TEXT PRIMARY KEY, bgg_id TEXT, last_search DATE, confidence REAL)')
        conn.execute('CREATE TABLE IF NOT EXISTS games (bgg_id TEXT PRIMARY KEY, name TEXT, last_updated DATE, rating TEXT, rank TEXT, type TEXT, language_dependency TEXT, original_name TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS deals (philibert_name TEXT PRIMARY KEY, price TEXT, old_price TEXT, url TEXT, date_found DATE, is_accessory BOOLEAN, is_expansion BOOLEAN, deal_source TEXT, condition TEXT)')

def norm_plain(s):
    s = s.lower().replace('&', ' and ')
    s = re.sub(r'[:\-\–\(\)\.\/]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return remove_accents(s)

def fetch_bgg_id(game_name, phili_url):
    url = "https://boardgamegeek.com/xmlapi2/search"
    phili_plain = norm_plain(game_name)
    target_clean = re.sub(NOISE_RE, '', phili_plain, flags=re.I).strip()
    target_clean_words = set(re.findall(r'\w+', target_clean))
    
    # Estrategia v5.13 (Comillas)
    raw_strategies = [f'"{game_name.strip()}"', target_clean]
    word_min_len = 2 if len(target_clean) < 8 else 3
    
    best_item, best_score, best_confidence, best_real_name = None, -5000, 0, ""
    for q in raw_strategies:
        time.sleep(1)
        try:
            res = requests.get(url, params={"query": q, "type": "boardgame,boardgameexpansion"}, headers=HEADERS, timeout=10)
            if res.status_code != 200: continue
            soup = BeautifulSoup(res.content, 'xml')
            for item in soup.find_all('item')[:20]:
                b_id = item['id']; b_orig = (item.find('name', attrs={'type': 'primary'}) or item.find('name'))['value']
                b_plain = norm_plain(b_orig); b_clean = re.sub(NOISE_RE, '', b_plain, flags=re.I).strip()
                b_clean_words = set(re.findall(r'\w+', b_clean))
                
                score = 0; matches = 0
                for tw in target_clean_words:
                    bw_sim = max([difflib.SequenceMatcher(None, tw, bw).ratio() for bw in b_clean_words] + [0])
                    if bw_sim > 0.85: score += 500 if is_rare_word(tw) else 100; matches += 1
                
                if matches >= len(target_clean_words): score += 2500
                if b_clean == target_clean: score += 2000
                if len(target_clean) < 10 and abs(len(b_clean)-len(target_clean)) > 12: score -= 6000
                
                conf = (matches / max(len(target_clean_words), 1)) * 100
                if score > best_score: best_score, best_item, best_confidence, best_real_name = score, b_id, conf, b_orig
        except: continue
        if best_confidence >= 100: break
    
    if best_confidence < 90 and is_philibert_excluded(phili_url): return None, 0, ""
    return best_item, best_confidence, best_real_name

def fetch_details(bgg_id):
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
    time.sleep(1)
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, 'xml')
        item = soup.find('item')
        if not item: return "N/A", "N/A", "Unknown", "-", ""
        stats = item.find('statistics'); rat, rnk = "N/A", "N/A"
        if stats:
            avg = stats.find('average'); rat = f"{float(avg.get('value', 0)):.1f}"
            for r in stats.find_all('rank'):
                if r.get('name') == 'boardgame': rnk = r.get('value'); break
        o_name = (item.find('name', attrs={'type': 'primary'}) or item.find('name'))['value']
        l_dep = "-"
        poll = item.find('poll', attrs={'name': 'language_dependence'})
        if poll:
            mv = -1
            for opt in poll.find_all('result'):
                v = int(opt.get('numvotes', 0))
                if v > mv: mv = v; l_dep = opt.get('value', "-")
        return rat, rnk, item.get('type'), l_dep, o_name
    except: return "N/A", "N/A", "Unknown", "-", ""

def scrape_private():
    init_db(); today = datetime.date.today().isoformat()
    with get_db_connection() as conn: conn.execute('DELETE FROM deals WHERE date_found=? AND deal_source="private"', (today,)); conn.commit()
    url_base = "https://www.philibertnet.com/fr/15007-ventes-privees"
    p = 1; seen = set()
    print(f"--- Iniciando Ventas Privadas (Página 1) ---", file=sys.stderr)
    while True:
        url = url_base if p == 1 else f"{url_base}?p={p}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code != 200: break
            soup = BeautifulSoup(res.content, 'html.parser')
            items = soup.find_all('li', class_='ajax_block_product')
            if not items or all(li.find('p', class_='s_title_block').find('a')['href'] in seen for li in items): break
            
            for item in items:
                a = item.find('p', class_='s_title_block').find('a'); u = a['href']; name = a.text.strip()
                if u in seen: continue
                seen.add(u)
                
                if any(k.lower() in name.lower() for k in IGNORE_KEYWORDS): continue
                
                price = item.find('span', class_='price').text.strip()
                old_p = item.find('span', class_='old-price').text.strip() if item.find('span', class_='old-price') else "0€"
                is_acc = any(k.lower() in name.lower() for k in ['Rangement','Organizer','Sleeves','Tapis','Mat','Token'])
                
                if is_acc:
                    with get_db_connection() as conn: conn.execute('INSERT OR REPLACE INTO deals (philibert_name, price, old_price, url, date_found, is_accessory, is_expansion, deal_source) VALUES (?,?,?,?,?,?,?,?)', (name, price, old_p, u, today, 1, 0, 'private'))
                    continue
                
                with get_db_connection() as conn: cached = conn.execute('SELECT bgg_id, confidence FROM bgg_mapping WHERE philibert_name=? AND confidence >= 95', (name,)).fetchone()
                if cached: id_b, conf, real_n = cached[0], cached[1], name
                else:
                    id_b, conf, real_n = fetch_bgg_id(name, u)
                    if not id_b: continue
                    with get_db_connection() as conn: conn.execute('INSERT OR REPLACE INTO bgg_mapping (philibert_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)', (name, id_b, conf, today))
                
                with get_db_connection() as conn:
                    conn.execute('INSERT OR REPLACE INTO deals (philibert_name, price, old_price, url, date_found, is_accessory, is_expansion, deal_source) VALUES (?,?,?,?,?,?,?,?)', (name, price, old_p, u, today, 0, any(k in name.lower() for k in ['extens','expans','pack']), 'private'))
                    if id_b and not conn.execute('SELECT bgg_id FROM games WHERE bgg_id=?', (id_b,)).fetchone():
                        rat, rnk, gt, l_dep, o_name = fetch_details(id_b)
                        conn.execute('INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name) VALUES (?,?,?,?,?,?,?,?)', (id_b, real_n, rat, rnk, gt, today, l_dep, o_name))
                conn.commit()
            p += 1
            print(f"Página {p} procesada...", file=sys.stderr)
        except: break

if __name__ == "__main__": scrape_private()
