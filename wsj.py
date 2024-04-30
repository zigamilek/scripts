from bs4 import BeautifulSoup
import requests
import json


params = {
    'id': '{"application":"WSJ","marketsDiaryType":"overview"}',
    'type': 'mdc_marketsdiary'
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:73.0) Gecko/20100101 Firefox/73.0"
}
r = requests.get(
    "https://www.wsj.com/market-data/stocks", params=params, headers=headers).json()


data = json.dumps(r, indent=4)

print(data)