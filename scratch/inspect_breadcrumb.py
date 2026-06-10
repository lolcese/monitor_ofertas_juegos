import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from bs4 import BeautifulSoup
from monitor_core import HEADERS_PHILI

url = "https://www.philibertnet.com/fr/matagot/158096-evenfall-la-voie-des-cristaux-3760372235598.html"
print(f"Requesting product page: {url}")
try:
    res = requests.get(url, headers=HEADERS_PHILI, timeout=15)
    print(f"Status: {res.status_code}")
    print(f"Contains 'breadcrumb': {'breadcrumb' in res.text.lower()}")
    
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # Try finding breadcrumbs
    bc = soup.select_one('.breadcrumb')
    if bc:
        print("Found breadcrumb by '.breadcrumb':")
        print(bc.text.strip())
    else:
        # Search for tags with class containing 'breadcrumb' or 'bc'
        print("Trying selector '[class*=\"breadcrumb\"]':")
        bc_tags = soup.select('[class*="breadcrumb"]')
        for t in bc_tags:
            print("Tag name:", t.name, "Class:", t.get('class'))
            print("Content:", t.text.strip()[:200])
except Exception as e:
    print(f"Error: {e}")
