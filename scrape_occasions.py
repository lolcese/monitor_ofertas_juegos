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
DB_PATH = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
LOG_PATH = r'c:\Datos\Luis\bgg\Phillibert\coincidencias_fallidas.txt'
LOG_HTML_PATH = r'c:\Datos\Luis\bgg\Phillibert\coincidencias_fallidas.html'
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

DEBUG = True

# Diccionario de Ruido Comercial
NOISE_RE = r'\b(core box|core game|jeu de base|boite de base|complete|bundle|big box|box|set|game|pack|edition|edicion|essentielle|essential|ancienne version|nouvelle version|en français|version|française|deluxe|collector|anniversary|impression|jeu|l\'âge|des|les|aux|de|la|le|extension|expansion|erw|erweiterung|printing|pression|copy|sundrop|standard|fr|en|de|es|promo|preorder|l\'aube|d\'un|stefan feld|uwe rosenberg|knizia|recharged|vital lacerda|lacerda|board game|jeu de plateau|token|tokens|galactic|galactic edition|card holder|standees|deck box|extra player pack)\b'

IGNORE_KEYWORDS = [
    'Jeu de Rôle', 'Jeu de Role', ' JDR', 'RPG ', 'Livre de base', 'Scénario', 'Scenario', 'Supplément', 'Supplement', 
    'Livre d\'aventures', 'Livre de reglas', 'Livre de regles', 'Campagne', 'Ecran du MJ', 'Écran du MJ',
    'Games Workshop', 'Warhammer', 'Age of Sigmar', 'Citadel', 'Peinture', 'Pinceau', 'Socle', 'Wargame Miniatures'
]

GENERIC_TITLES = {
    'le juego de plateau', 'the board game', 'jeu de plateau', 'board game', 
    'extension', 'expansion', 'erweiterung', 'pack', 'set', 'bundle'
}

TRANSLATIONS = {
    'royaute': 'regality', 'revolution': 'revolution', 'aube': 'dawn', 
    'tenebres': 'darkness', 'siecle': 'century', 'guerre': 'war',
    'chanson': 'songs', 'francaise': 'french', 'chroniques': 'chronicles', 'plateau': 'board'
}

def remove_accents(input_str):
    if not input_str: return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def is_rare_word(w, orig_word=""):
    if orig_word.isupper() and 2 <= len(orig_word) <= 4: return True
    common_words = {'the', 'of', 'in', 'and', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'an', 'is', 'it', 'was', 'were'}
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
            if any(k in classes for k in ['category-392', 'category-8000', 'category-1178', 'category-119', 'category-jeux-de-role', 'category-jeux-de-figurines', 'category-accessoires']): return True
            bread = soup.find('div', class_='breadcrumb')
            if bread:
                b_text = bread.text.lower()
                if any(k in b_text for k in ['jeu de rôle', 'jeux de rôle', 'figurine', 'accessoire', 'collectionner', 'évolutif', 'jcc', 'jce']): return True
    except: pass
    return False

def log_failed_match_html(name, url, best_id, candidates_dict):
    if not candidates_dict: return
    candidates = list(candidates_dict.values())
    max_score = max(c['score'] for c in candidates) if candidates else 0
    max_conf = max(c['conf'] for c in candidates) if candidates else 0
    html = ""
    if not os.path.exists(LOG_HTML_PATH):
        html = "<html><head><meta charset='utf-8'><style>table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:8px}tr.best-score{background-color:#d4edda}tr.best-conf{border:3px solid #ffc107;font-weight:bold}tr.assigned{border:4px solid #007bff !important}a{text-decoration:none;color:#007bff}</style></head><body>"
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    html += f"<h3><a href='{url}' target='_blank'>[OCCASION] {name}</a> ({ts})</h3>"
    html += "<table><tr><th>ID BGG</th><th>Nombre</th><th>Score</th><th>Conf %</th></tr>"
    for c in sorted(candidates, key=lambda x: x['score'], reverse=True)[:10]:
        cls = []; is_a = str(c['id']) == str(best_id)
        if c['score'] == max_score: cls.append("best-score")
        if c['conf'] == max_conf: cls.append("best-conf")
        if is_a: cls.append("assigned")
        html += f"<tr class='{' '.join(cls)}'><td>{c['id']}</td><td>{c['name']}</td><td>{c['score']:.1f}</td><td>{c['conf']:.1f}%</td></tr>"
    html += "</table><hr>"
    with open(LOG_HTML_PATH, 'a', encoding='utf-8') as f: f.write(html)

def log_failed_match(source, name, url, best_id, best_conf, candidates_dict):
    log_failed_match_html(name, url, best_id, candidates_dict)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"\n--- {datetime.datetime.now()} | [OCCASION] '{name}' ---\nURL: {url}\nASIGNADO ID: {best_id} | Conf: {best_conf:.1f}%\n" + "-"*60 + "\n")

def get_db_connection(): return sqlite3.connect(DB_PATH)

def init_db():
    with get_db_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS bgg_mapping (philibert_name TEXT PRIMARY KEY, bgg_id TEXT, last_search DATE, confidence REAL)')
        conn.execute('CREATE TABLE IF NOT EXISTS games (bgg_id TEXT PRIMARY KEY, name TEXT, last_updated DATE, rating TEXT, rank TEXT, type TEXT, language_dependency TEXT, original_name TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS deals (philibert_name TEXT PRIMARY KEY, price TEXT, old_price TEXT, url TEXT, date_found DATE, is_accessory BOOLEAN, is_expansion BOOLEAN, deal_source TEXT, condition TEXT)')
        try: conn.execute('ALTER TABLE games ADD COLUMN language_dependency TEXT')
        except: pass
        try: conn.execute('ALTER TABLE games ADD COLUMN original_name TEXT')
        except: pass

def norm_plain(s):
    s = s.lower().replace('&', ' and ')
    s = re.sub(r'(?<=\w)\.(?=\w)', '', s)
    s = re.sub(r'[:\-\–\(\)\.\/]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return remove_accents(s)

def fetch_bgg_id(game_name, phili_url, source='occasion'):
    url = "https://boardgamegeek.com/xmlapi2/search"
    phili_plain = norm_plain(game_name)
    phili_parts = [p.strip() for p in re.split(r'[:\-–\(]', game_name) if p.strip()]
    is_base_explicit = any(kw in game_name.lower() for kw in ['jeu de base', 'core box', 'big box', 'bundle', 'complete'])
    is_ext = any(kw in game_name.lower() for kw in ['extension', 'expansion', 'pack', 'set', 'erw']) and not is_base_explicit
    phili_nums = re.findall(r'\b(\d+)(?:e|rd|st|nd|th|ème)?\b', game_name.lower())
    target_clean = re.sub(NOISE_RE, '', phili_plain, flags=re.I).strip()
    target_orig_words = re.findall(r'\w+', re.sub(r'[:\-\–\(\)\.\/]', ' ', game_name))
    target_clean_words = set(re.findall(r'\w+', target_clean))
    
    # ESTRATEGIAS v5.12: Comillas y palabras de 2 letras para nombres cortos
    raw_strategies = [f'"{game_name.strip()}"', game_name.strip(), phili_plain] + phili_parts
    word_min_len = 2 if len(target_clean) < 8 else 3
    raw_strategies += [w for w in target_clean_words if len(w) >= word_min_len]
    
    strategies = []
    for s in raw_strategies:
        s_n = s.lower().strip()
        if len(s_n) >= word_min_len and s_n not in GENERIC_TITLES: strategies.append(s_n)
    strategies = sorted(list(set(strategies)), key=len, reverse=True)
    
    best_item, best_score, best_confidence, best_real_name = None, -5000, 0, ""
    all_candidates = {}

    for q in strategies:
        time.sleep(1)
        try:
            res = requests.get(url, params={"query": q, "type": "boardgame,boardgameexpansion"}, headers=HEADERS, timeout=10)
            if res.status_code != 200: continue
            soup = BeautifulSoup(res.content, 'xml')
            for item in soup.find_all('item')[:20]:
                b_id = item['id']; b_orig = (item.find('name', attrs={'type': 'primary'}) or item.find('name'))['value']
                b_plain = norm_plain(b_orig); b_clean = re.sub(NOISE_RE, '', b_plain, flags=re.I).strip()
                b_clean_words = set(re.findall(r'\w+', b_clean)); b_nums = re.findall(r'\b(\d+)(?:e|rd|st|nd|th|ème)?\b', b_orig.lower())
                
                score = 0; matches = 0
                for tw in target_clean_words:
                    orig_w = next((ow for ow in target_orig_words if norm_plain(ow) == tw), tw)
                    if tw in TRANSLATIONS and TRANSLATIONS[tw] in b_clean: score += 750; matches += 1; continue
                    bw_sim = 0
                    for bw in b_clean_words:
                        r = difflib.SequenceMatcher(None, tw, bw).ratio()
                        if r > bw_sim: bw_sim = r
                    if bw_sim > 0.85: score += 500 if is_rare_word(tw, orig_w) else 100; matches += 1
                    elif bw_sim > 0.70: score += 50
                    else: score -= 50

                if matches >= len(target_clean_words): score += 2500
                if b_clean == target_clean: 
                    score += 2000
                    if len(target_clean) < 10: score += 5000
                
                # VETO RADICAL Sa-Rê
                len_diff = abs(len(b_clean) - len(target_clean))
                if len(target_clean) < 10 and len_diff > 12: score -= 6000

                if phili_nums and b_nums and phili_nums[0] != b_nums[0]: score -= 4500
                for bw in b_clean_words:
                    if bw not in target_clean_words and all(tw not in bw for tw in target_clean_words): score -= 300
                if is_base_explicit and item.get('type') == 'boardgameexpansion': score -= 4000
                elif is_ext and item.get('type') == 'boardgame': score -= 1500
                
                conf = (matches / max(len(target_clean_words), 1)) * 100
                if b_id not in all_candidates or score > all_candidates[b_id]['score']:
                    all_candidates[b_id] = {'id': b_id, 'name': b_orig, 'score': score, 'conf': conf}
                if score > best_score: best_score, best_item, best_confidence, best_real_name = score, b_id, conf, b_orig
        except: continue
        if best_confidence >= 100: break
    
    if best_confidence < 90 and is_philibert_excluded(phili_url): return None, 0, ""
    if best_confidence < 95: log_failed_match(source, game_name, phili_url, best_item, best_confidence, all_candidates)
    return best_item, best_confidence, best_real_name

def fetch_details(bgg_id):
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
    time.sleep(1)
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, 'xml')
            item = soup.find('item')
            if not item: return "N/A", "N/A", "Unknown", "-", ""
            stats = item.find('statistics'); rat, rnk = "N/A", "N/A"
            if stats:
                avg = stats.find('average'); rat = f"{float(avg.get('value', 0)):.1f}" if avg else "N/A"
                for r in stats.find_all('rank'):
                    if r.get('name') == 'boardgame': rnk = r.get('value', 'N/A'); break
            o_name = (item.find('name', attrs={'type': 'primary'}) or item.find('name'))['value']
            l_dep = "-"
            poll = item.find('poll', attrs={'name': 'language_dependency'})
            if poll:
                max_v = -1
                for result in poll.find_all('result'):
                    v = int(result['numvotes'])
                    if v > max_v: max_v = v; l_dep = result['value']
            return rat, rnk, item.get('type', 'Unknown'), l_dep, o_name
    except: pass
    return "N/A", "N/A", "Unknown", "-", ""

def scrape_occasions():
    init_db(); today = datetime.date.today().isoformat()
    with get_db_connection() as conn: conn.execute('DELETE FROM deals WHERE date_found=? AND deal_source="occasion"', (today,)); conn.commit()
    url_base = "https://www.philibertnet.com/fr/214-occasions"
    p = 1; seen = set()
    while True:
        url = url_base if p == 1 else f"{url_base}?p={p}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code != 200: break
            soup = BeautifulSoup(res.content, 'html.parser')
            items = soup.find_all('li', class_='ajax_block_product')
            if not items or all(li.find('p', class_='s_title_block').find('a')['href'] in seen for li in items): break
            for item in items:
                a = item.find('p', class_='s_title_block').find('a'); u = a['href']; seen.add(u); name = a.text.strip()
                if any(k.lower() in name.lower() for k in IGNORE_KEYWORDS) or any(k.lower() in u.lower() for k in ['jeu-de-role', 'figurine']): continue 
                
                p_new = item.find('span', class_='price').text.strip(); p_old = item.find('span', class_='old-price').text.strip() if item.find('span', class_='old-price') else "0€"
                is_acc = any(k.lower() in name.lower() for k in ['Rangement','Organizer','Sleeves','Tapis','Mat','Token','Card Holder','Standees','Deck Box'])
                
                if is_acc:
                    with get_db_connection() as conn: conn.execute('INSERT OR REPLACE INTO deals (philibert_name, price, old_price, url, date_found, is_accessory, is_expansion, deal_source, condition) VALUES (?,?,?,?,?,?,?,?,?)', (name, p_new, p_old, u, today, 1, 0, 'occasion', "Occasion"))
                    continue
                
                with get_db_connection() as conn: cached = conn.execute('SELECT bgg_id, confidence FROM bgg_mapping WHERE philibert_name=? AND confidence >= 95', (name,)).fetchone()
                if cached: id_b, conf, real_n = cached[0], cached[1], name
                else:
                    id_b, conf, real_n = fetch_bgg_id(re.sub(r' - Occasion$', '', name, flags=re.IGNORECASE).strip(), u, source='occasion')
                    if not id_b: continue
                    with get_db_connection() as conn: conn.execute('INSERT OR REPLACE INTO bgg_mapping (philibert_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)', (name, id_b, conf, today))
                
                with get_db_connection() as conn:
                    conn.execute('INSERT OR REPLACE INTO deals (philibert_name, price, old_price, url, date_found, is_accessory, is_expansion, deal_source, condition) VALUES (?,?,?,?,?,?,?,?,?)', (name, p_new, p_old, u, today, 0, any(k in name.lower() for k in ['extens','expans','pack']), 'occasion', "Occasion"))
                    if id_b and not conn.execute('SELECT bgg_id FROM games WHERE bgg_id=?', (id_b,)).fetchone():
                        rat, rnk, gt, l_dep, o_name = fetch_details(id_b)
                        conn.execute('INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name) VALUES (?,?,?,?,?,?,?,?)', (id_b, real_n, rat, rnk, gt, today, l_dep, o_name))
                conn.commit()
            p += 1
        except: break

if __name__ == "__main__": scrape_occasions()
