import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from bs4 import BeautifulSoup
from monitor_core import HEADERS_PHILI

url = "https://www.philibertnet.com/fr/flash-sales"
res = requests.get(url, headers=HEADERS_PHILI, timeout=15)
soup = BeautifulSoup(res.content, 'html.parser')
items = soup.select('.product-card')

print(f"Total items found: {len(items)}")
if items:
    first_item = items[0]
    print("\n--- FIRST ITEM HTML ---")
    print(first_item.prettify()[:2000])
    
    print("\n--- EXTRACTING PARTS ---")
    # Title / Link
    a_tag = first_item.select_one('.product-card__title a') or first_item.select_one('a.product-card__title') or first_item.select_one('a')
    if a_tag:
        print("Link tag found:", a_tag)
        print("Href:", a_tag.get('href'))
        print("Text:", a_tag.text.strip())
    else:
        print("No a_tag found")
        
    # Prices
    price_new = first_item.select_one('.product-card__price') or first_item.select_one('.price')
    print("Price new tag:", price_new)
    if price_new:
        print("Price new text:", price_new.text.strip())
        
    price_old = first_item.select_one('.product-card__prices del') or first_item.select_one('.product-card__price-container del') or first_item.select_one('.old-price')
    # Let's search for any del or strike or old price classes
    if not price_old:
        price_old = first_item.select_one('del')
    print("Price old tag:", price_old)
    if price_old:
        print("Price old text:", price_old.text.strip())
        
    # Image
    img_tag = first_item.select_one('.product-card__thumb img') or first_item.select_one('img')
    print("Img tag:", img_tag)
    if img_tag:
        print("Img src:", img_tag.get('src') or img_tag.get('data-src'))
