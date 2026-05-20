import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('token')

url = "https://boardgamegeek.com/xmlapi2/search"
q = "Catan"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Authorization": f"Bearer {token}"
}
res = requests.get(url, params={"query": q, "exact": 0}, headers=headers)
print("Status Code:", res.status_code)
print("Content:", res.content[:500])
