import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from bs4 import BeautifulSoup
from monitor_core import HEADERS_PHILI

url = "https://www.philibertnet.com/fr/connexion"
try:
    res = requests.get(url, headers=HEADERS_PHILI, timeout=15)
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # Find all form tags
    forms = soup.find_all('form')
    print(f"Found {len(forms)} forms:")
    for i, form in enumerate(forms):
        print(f"\nForm {i}:")
        print("Action:", form.get('action'))
        print("Method:", form.get('method'))
        print("Class:", form.get('class'))
        print("Inputs:")
        for inp in form.find_all(['input', 'button']):
            print(f"  - Name: {inp.get('name')}, Type: {inp.get('type')}, ID: {inp.get('id')}, Value: {inp.get('value')}")
except Exception as e:
    print(f"Error: {e}")
