import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

def test_breadcrumb():
    # URL from previous test
    url = "https://www.philibertnet.com/fr/mandaloriens/175243-star-wars-legion-mandalorian-special-edition-army-box-2100001342142.html"
    print(f"Testing Product URL: {url}")
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"Failed to fetch product page: {res.status_code}")
        return
    
    soup = BeautifulSoup(res.content, 'html.parser')
    bc = soup.select_one('.breadcrumb')
    print(f"Breadcrumb found: {'YES' if bc else 'NO'}")
    if bc:
        print(f"Breadcrumb text: {bc.text.strip()}")

if __name__ == "__main__":
    test_breadcrumb()
