import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

def test():
    url = "https://www.philibertnet.com/fr/flash-sales"
    print(f"Testing URL: {url}")
    res = requests.get(url, headers=HEADERS)
    print(f"Status Code: {res.status_code}")
    if res.status_code != 200:
        return
    
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # Try old selector
    old_items = soup.select('.ajax_block_product')
    print(f"Old items found: {len(old_items)}")
    
    # Try new selectors reported by subagent
    new_items = soup.select('.product-card')
    print(f"New items found: {len(new_items)}")
    
    if new_items:
        item = new_items[0]
        title_tag = item.select_one('.product-card__title')
        price_tag = item.select_one('.product-card__price')
        old_price_tag = item.select_one('.product-card__price--old')
        img_tag = item.select_one('img.product-card__thumb')
        
        print(f"Title: {title_tag.text.strip() if title_tag else 'NOT FOUND'}")
        print(f"Link: {title_tag['href'] if title_tag and 'href' in title_tag.attrs else 'NOT FOUND'}")
        print(f"Price: {price_tag.text.strip() if price_tag else 'NOT FOUND'}")
        print(f"Old Price: {old_price_tag.text.strip() if old_price_tag else 'NOT FOUND'}")
        print(f"Img: {img_tag['src'] if img_tag else 'NOT FOUND'}")

    # Check pagination
    next_page = soup.select_one('.paginator-item__next')
    print(f"Next page link found: {'YES' if next_page else 'NO'}")
    if next_page:
        print(f"Next page URL: {next_page.get('href')}")

if __name__ == "__main__":
    test()
