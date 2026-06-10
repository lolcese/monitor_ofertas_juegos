import requests
from bs4 import BeautifulSoup
from monitor_core import HEADERS_PHILI, SOURCES

url = SOURCES['private']
print(f"Requesting private sales URL: {url}")
try:
    res = requests.get(url, headers=HEADERS_PHILI, timeout=15)
    print(f"Status Code: {res.status_code}")
    print(f"Response length: {len(res.content)} bytes")
    
    # Save a snippet of the HTML to see if we're redirected or blocked
    soup = BeautifulSoup(res.content, 'html.parser')
    title = soup.title.string if soup.title else 'No Title'
    print(f"Page Title: {title}")
    
    # Let's search for some product elements
    items = soup.select('.ajax_block_product')
    print(f"Found {len(items)} products with '.ajax_block_product'")
    
    # Print some of the page text to check for "connexion" or login requirements
    text_snippet = res.text[:2000]
    if "connexion" in res.text.lower() or "login" in res.text.lower():
        print("Possible login/redirect detected in the page content!")
except Exception as e:
    print(f"Error occurred: {e}")
