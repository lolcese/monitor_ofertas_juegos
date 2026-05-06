import requests
from bs4 import BeautifulSoup

url = "https://zatu.com/collections/outlet-store?filter.p.m.custom.type=Board+Games&page=1"
res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(res.content, 'html.parser')
if "No products match those filters" in soup.get_text():
    print("Failed with &page=1")
else:
    print("Success! Items found:", len(soup.select('.product-card')))
