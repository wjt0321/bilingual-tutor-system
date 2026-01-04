import requests
from bs4 import BeautifulSoup
import urllib3
import re

urllib3.disable_warnings()

sites = [
    "https://www.cnprose.com/",
    "https://www.duwenzhang.com/",
    "https://www.vsread.com/"
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

for url in sites:
    print(f"--- Analyzing {url} ---")
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print(f"Title: {soup.title.string if soup.title else 'No Title'}")
        
        links = soup.find_all('a', href=True)
        count = 0
        print("Sample Links:")
        for link in links:
            href = link['href']
            text = link.get_text().strip()
            # Heuristic for article links: contain digits or 'html'
            if text and (re.search(r'\d+', href) or 'html' in href):
                print(f"  {text} -> {href}")
                count += 1
                if count >= 8:
                    break
        print("\n")
        
    except Exception as e:
        print(f"Error: {e}\n")


