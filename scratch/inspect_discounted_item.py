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

found = False
for index, item in enumerate(items):
    # check for old price / discount
    price_container = item.select_one('.product-card__price-container') or item.select_one('.product-card__prices')
    # Let's search if there's any 'del' or two prices
    del_tag = item.select_one('del')
    if del_tag:
        print(f"Found discounted item at index {index}!")
        print(item.prettify())
        found = True
        break

if not found:
    print("No item with '<del>' tag found in the first page of flash sales.")
    # Print the full HTML structure of the first item's price section
    first_item = items[0]
    prices_section = first_item.select_one('.product-card__prices') or first_item.select_one('[class*="price"]')
    if prices_section:
        print("\nPrice section of first item:")
        print(prices_section.prettify())
    else:
        # Print all tags that have class containing 'price'
        print("\nAll tags containing 'price' in class:")
        for tag in first_item.find_all(True):
            classes = tag.get('class', [])
            if any('price' in c.lower() for c in classes):
                print(tag.prettify())
