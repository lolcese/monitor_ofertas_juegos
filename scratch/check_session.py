import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from scratch.apply_cookie import raw_cookies

cookie_str = '; '.join([f"{item['name']}={item['value']}" for item in raw_cookies])
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 'Cookie': cookie_str}
res = requests.get('https://www.philibertnet.com/fr/mon-compte', headers=headers, timeout=12)
print('Status code:', res.status_code)
print('URL:', res.url)
print('Logged in (deconnexion):', 'deconnexion' in res.text.lower() or 'déconnexion' in res.text.lower())
