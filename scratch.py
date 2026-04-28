import requests
from bs4 import BeautifulSoup
found = False
for p in range(1, 15):
    res = requests.get(f'https://www.philibertnet.com/fr/flash-sales?p={p}', headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    items = soup.select('.ajax_block_product')
    for i in items:
        if 'dune' in i.text.lower():
            title = i.select_one('.s_title_block a').text.strip() if i.select_one('.s_title_block a') else 'No title'
            print(f'Found on page {p}:', title)
            found = True
if not found:
    print('Not found')
