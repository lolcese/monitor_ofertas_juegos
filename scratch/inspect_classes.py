import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from bs4 import BeautifulSoup
from monitor_core import HEADERS_PHILI

url = "https://www.philibertnet.com/fr/15007-ventes-privees"
res = requests.get(url, headers=HEADERS_PHILI, timeout=15)
soup = BeautifulSoup(res.content, 'html.parser')

print("Title:", soup.title.string if soup.title else "No Title")
# Print first 50 class names found in the HTML
classes = set()
for tag in soup.find_all(True):
    if tag.has_attr('class'):
        for c in tag['class']:
            classes.add(c)

print("Total unique classes:", len(classes))
print("Sample classes:", list(classes)[:100])

# Let's search for some product elements or anything with 'product' in it
product_classes = [c for c in classes if 'product' in c.lower() or 'item' in c.lower() or 'block' in c.lower()]
print("Product related classes:", product_classes)

# Let's check if there are <a> tags with product links or image URLs
links = soup.find_all('a')
product_links = [a.get('href') for a in links if a.get('href') and '/fr/' in a.get('href') and '.html' in a.get('href')]
print(f"Found {len(product_links)} links matching /fr/...html")
if product_links:
    print("Sample product links:", product_links[:10])
