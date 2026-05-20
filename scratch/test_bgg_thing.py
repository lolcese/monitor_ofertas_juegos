import requests

url = "https://boardgamegeek.com/xmlapi2/thing"
res = requests.get(url, params={"id": 13}, headers={"User-Agent": "MyBoardGameMonitorTool/1.0"})
print("Thing Status Code:", res.status_code)
print("Content:", res.content[:500])
