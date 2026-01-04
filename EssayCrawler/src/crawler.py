import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import random
import logging
from urllib.parse import urljoin, urlparse
import re
import sqlite3
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/crawler.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class BaseCrawler:
    def __init__(self, config):
        self.config = config
        self.ua = UserAgent()
        self.session = requests.Session()
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def get_headers(self):
        if self.config['crawler']['user_agent_rotate']:
            self.headers['User-Agent'] = self.ua.random
        else:
            self.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        return self.headers

    def fetch(self, url):
        retries = self.config['crawler']['max_retries']
        for i in range(retries):
            try:
                # Sleep to be polite
                delay = self.config['crawler']['request_delay']
                time.sleep(random.uniform(delay[0], delay[1]))

                response = self.session.get(
                    url, 
                    headers=self.get_headers(), 
                    timeout=self.config['crawler']['timeout'],
                    verify=False # Ignore SSL errors for some old sites
                )
                response.raise_for_status()
                
                # Handle encoding
                if response.encoding == 'ISO-8859-1':
                    response.encoding = response.apparent_encoding
                
                return response.text
            except requests.RequestException as e:
                logging.warning(f"Attempt {i+1}/{retries} failed for {url}: {e}")
        
        logging.error(f"Failed to fetch {url} after {retries} attempts")
        return None

    def parse(self, html):
        if not html:
            return None
        return BeautifulSoup(html, 'html.parser')

class GenericArticleCrawler(BaseCrawler):
    # Define site-specific rules
    SITE_RULES = {
        'zuowen.com': {
            'article_pattern': r'/(e|a)/\d+/[a-zA-Z0-9]+\.s?html?|/xsczw/.+/[a-zA-Z0-9]+\.s?html?',  # Allow alphanumeric id
            'exclude_pattern': r'(map|include|help|tiku|wk|list|index)',
            'content_selector': ['div.con_content', 'div.article_content', 'div.main_content', 'div#article_content'],
            'title_selector': 'h1'
        },
        'zww.cn': {
            'article_pattern': r'(/zuowen/.+/\d+\.s?html?)', # Ensure digits are present to avoid category pages
            'exclude_pattern': r'(list|index|about|user|baike|member|hot|new)',
            'content_selector': ['.content', 'div#text', 'div.zw-content', 'div.art_content', 'td.zw_content'],
            'title_selector': 'h1'
        },
        'duwenzhang.com': {
            'article_pattern': r'/wenzhang/.+/\d+/\d+\.html',
            'exclude_pattern': r'(list|index)',
            'content_selector': ['div#wenzhangziti'],
            'title_selector': 'h1'
        },
        'cnprose.com': {
            'article_pattern': r'/article-detail/[a-zA-Z0-9]+',
            'exclude_pattern': r'(list|index)',
            'content_selector': ['div.inner-detail'],
            'title_selector': 'h1'
        },
        'vsread.com': {
            'article_pattern': r'/article-\d+\.html',
            'exclude_pattern': r'(list|index|space|user)',
            'content_selector': ['div#mainContent', 'div.notice'],
            'title_selector': 'h1',
            'remove_selectors': ['div.title1', 'div.title']
        }
    }

    def is_url_crawled(self, url):
        """Check if URL exists in the database."""
        db_path = self.config['storage']['db_path']
        if not os.path.exists(db_path):
            return False
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Check if the table exists first to avoid errors on fresh install
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
            if not cursor.fetchone():
                conn.close()
                return False
                
            cursor.execute("SELECT 1 FROM articles WHERE source_url = ?", (url,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception as e:
            logging.error(f"Error checking URL in DB: {e}")
            return False

    def get_site_rule(self, url):
        domain = urlparse(url).netloc
        for key, rule in self.SITE_RULES.items():
            if key in domain:
                return rule
        return None

    def crawl_site(self, site_config):
        url = site_config['url']
        logging.info(f"Starting crawl for: {site_config['name']} ({url})")
        
        html = self.fetch(url)
        soup = self.parse(html)
        
        if not soup:
            return []

        articles = []
        links = soup.find_all('a', href=True)
        
        # Get rules for this site
        rule = self.get_site_rule(url)
        
        count = 0
        seen_urls = set()

        for link in links:
            if count >= 5: # Limit per run
                break
                
            href = link['href']
            title = link.get_text().strip()
            full_url = urljoin(url, href)
            
            # logging.info(f"Checking link: {full_url}") # DEBUG
            
            if full_url in seen_urls:
                continue
            
            # Check database for existing URL
            if self.is_url_crawled(full_url):
                logging.info(f"  Skipping already crawled URL: {full_url}")
                continue
            
            # Apply filters
            if not self.is_valid_url(full_url, rule):
                # logging.info(f"  Skipped by filter: {full_url}") # DEBUG
                continue
                
            # Visit the detail page
            article_data = self.crawl_detail(full_url, title, rule)
            if article_data:
                articles.append(article_data)
                seen_urls.add(full_url)
                count += 1
        
        return articles

    def is_valid_url(self, url, rule):
        if not rule:
            # Generic fallback: basic sanity check
            return len(url) > 20 and 'javascript' not in url
            
        # Check includes
        if not re.search(rule['article_pattern'], url):
            # logging.debug(f"URL {url} failed include pattern {rule['article_pattern']}")
            return False
            
        # Check excludes
        if rule.get('exclude_pattern') and re.search(rule['exclude_pattern'], url):
            # logging.debug(f"URL {url} failed exclude pattern {rule['exclude_pattern']}")
            return False
            
        return True

    def crawl_detail(self, url, title, rule):
        logging.info(f"  Crawling detail: {title} -> {url}")
        html = self.fetch(url)
        soup = self.parse(html)
        
        if not soup:
            return None

        content_div = None
        
        # 1. Try site-specific selectors
        if rule:
            for selector in rule['content_selector']:
                content_div = soup.select_one(selector)
                if content_div:
                    break
            
            # Try to get better title
            if rule.get('title_selector'):
                title_tag = soup.select_one(rule['title_selector'])
                if title_tag:
                    title = title_tag.get_text().strip()

        # 2. Fallback to generic heuristic
        if not content_div:
            candidates = soup.find_all(['div', 'article'], class_=lambda x: x and any(k in x.lower() for k in ['content', 'article', 'text', 'detail', 'main']))
            if candidates:
                content_div = max(candidates, key=lambda x: len(x.get_text()))
            else:
                divs = soup.find_all('div')
                if divs:
                    content_div = max(divs, key=lambda x: len(x.find_all('p')))

        if content_div:
            # 3. Apply site-specific cleanup
            if rule and rule.get('remove_selectors'):
                for selector in rule['remove_selectors']:
                    for tag in content_div.select(selector):
                        tag.decompose()

            # Clean content
            for tag in content_div(['script', 'style', 'iframe']):
                tag.decompose()
                
            for tag in content_div(['a']):
                 tag.unwrap() # Keep text, remove link
                 
            for tag in content_div(['div']): 
                # Only remove if it's clearly noise
                if 'ad' in str(tag.get('class', '')) or 'page' in str(tag.get('class', '')):
                     tag.decompose()
            
            text = content_div.get_text(separator='\n').strip()
            
            # Final sanity check for content length
            if len(text) < 50:
                logging.warning(f"    Content too short ({len(text)} chars), skipping.")
                return None

            return {
                'title': title,
                'url': url,
                'content': text,
                'crawled_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        logging.warning("    No content found.")
        return None












