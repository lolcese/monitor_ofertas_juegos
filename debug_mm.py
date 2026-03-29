import requests
from bs4 import BeautifulSoup
url = "https://www.miniaturemarket.com/dailydeal?properties=019262c7e0db711a97a94030d6103aa9"
res = requests.get(url, timeout=15)
soup = BeautifulSoup(res.content, 'html.parser')
items = soup.select('.product-box')
print(f"URL: {url}")
print(f"Status: {res.status_code}")
print(f"COUNT_BOX: {len(items)}")
for i, item in enumerate(items[:2]):
    name_tag = item.select_one('.product-name')
    price_tag = item.select_one('.product-price')
    print(f"ITEM {i}: NAME={'FOUND' if name_tag else 'MISSING'} PRICE={'FOUND' if price_tag else 'MISSING'}")
    if name_tag: print(f"  NAME_VAL: {name_tag.get('title', name_tag.text.strip())}")
    if price_tag: print(f"  PRICE_VAL: {price_tag.text.strip()}")
