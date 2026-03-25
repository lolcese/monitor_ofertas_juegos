import requests
from bs4 import BeautifulSoup
from monitor_core import HEADERS_PHILI

url = "https://www.philibertnet.com/fr/15007-ventes-privees"
print("Headers:", {k: v for k, v in HEADERS_PHILI.items() if k != 'Cookie'})
print("Has cookie:", 'Cookie' in HEADERS_PHILI)
res = requests.get(url, headers=HEADERS_PHILI, timeout=15)
print("Status code:", res.status_code)
print("Final URL:", res.url)

soup = BeautifulSoup(res.content, 'html.parser')
items = soup.select('.ajax_block_product')
print("Items found:", len(items))

error_msg = soup.select_one('.alert-danger')
if error_msg: print("Error:", error_msg.text.strip())
    
warning_msg = soup.select_one('.alert-warning')
if warning_msg: print("Warning:", warning_msg.text.strip())

print("Page title:", soup.title.string if soup.title else "No title")
