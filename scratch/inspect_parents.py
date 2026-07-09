import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

key = os.getenv('PHILIBERT_COOKIE_KEY')
cookie_val = None

cookie_file = os.path.join(BASE_DIR, 'philibert_cookie.txt')
if os.path.exists(cookie_file) and key:
    try:
        from cryptography.fernet import Fernet
        fernet = Fernet(key.encode('utf-8'))
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookie_val = fernet.decrypt(f.read().strip().encode('utf-8')).decode('utf-8')
    except Exception as e:
        print(f"Decryption failed: {e}")

if not cookie_val:
    cookie_val = os.getenv('PHILIBERT_COOKIE')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Cookie": cookie_val
}

url = "https://www.philibertnet.com/fr/15007-ventes-privees"
try:
    res = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(res.content, 'html.parser')
    
    items = soup.select('.product-card')
    print(f"Total product cards found: {len(items)}")
    
    for i, item in enumerate(items):
        title_tag = item.select_one('.product-card__title')
        title = title_tag.text.strip() if title_tag else "No Title"
        
        # Traverse up the DOM to find parent IDs and classes
        parents = []
        p = item.parent
        while p and p.name != 'html':
            p_desc = f"{p.name}"
            if p.get('id'):
                p_desc += f"#{p.get('id')}"
            if p.get('class'):
                p_desc += f".{'.'.join(p.get('class'))}"
            parents.append(p_desc)
            p = p.parent
            
        print(f"\n[{i+1}] {title}")
        print(" -> Parents hierarchy (inner to outer):")
        print("    " + " -> ".join(parents[:4]))
        
except Exception as e:
    print(f"Error: {e}")
