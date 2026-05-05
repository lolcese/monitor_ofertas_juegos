from scraper_philibert import SOURCES
from monitor_core import HEADERS_PHILI
import requests

print("Import success")
print(f"Sources: {SOURCES}")
print(f"Headers: {HEADERS_PHILI}")

url = SOURCES['flash']
print(f"Fetching {url}...")
res = requests.get(url, headers=HEADERS_PHILI, timeout=10)
print(f"Status: {res.status_code}")
print(f"Content length: {len(res.content)}")
