import requests
from bs4 import BeautifulSoup
import json

HEADERS_PHILI = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
}

def inspect_categories():
    urls = {
        "flash": "https://www.philibertnet.com/fr/13976-soldes-jeux-de-societe",
        "occasion": "https://www.philibertnet.com/fr/214-occasions",
        "preorder": "https://www.philibertnet.com/fr/578-precommandes"
    }
    
    for key, url in urls.items():
        print(f"\n--- Testing {key.upper()} url: {url} ---")
        try:
            res = requests.get(url, headers=HEADERS_PHILI, timeout=15)
            soup = BeautifulSoup(res.content, 'html.parser')
            cards = soup.select('#product-list .product-card')
            if not cards:
                print("No cards found")
                continue
            
            # Let's inspect category fields of first 10 cards
            for i, card in enumerate(cards[:10]):
                name = card.select_one('.product-card__title').text.strip() if card.select_one('.product-card__title') else "No title"
                data_attr = card.get('data-datalayer-event')
                if data_attr:
                    try:
                        data = json.loads(data_attr)
                        cat = data.get('item_category', '')
                        cat2 = data.get('item_category2', '')
                        cat3 = data.get('item_category3', '')
                        cat4 = data.get('item_category4', '')
                        print(f"Card {i}: {name}\n  Cat1: {cat} | Cat2: {cat2} | Cat3: {cat3} | Cat4: {cat4}")
                    except Exception as json_err:
                        print(f"Card {i}: JSON parse error: {json_err}")
                else:
                    print(f"Card {i}: No data-datalayer-event attribute")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    inspect_categories()
