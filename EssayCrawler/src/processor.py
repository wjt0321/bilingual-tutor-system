import sqlite3
import os
import re
import jieba
import logging
import json

class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.db_path = config['storage']['db_path']
        self.init_db()

    def init_db(self):
        """Initialize SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT,
                    category TEXT,
                    source_url TEXT UNIQUE,
                    crawled_at TEXT,
                    word_count INTEGER,
                    score INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")

    def clean_text(self, text):
        """Remove extra whitespace and noise."""
        if not text:
            return ""
        
        # Remove full-width spaces often used for indentation in Chinese
        text = text.replace('　', '')
        
        # Replace multiple newlines with a single one (or double for paragraph)
        # First normalize newlines
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        
        # Filter out empty lines and join with double newline for Markdown paragraphs
        cleaned_lines = [line for line in lines if line]
        
        return '\n\n'.join(cleaned_lines)

    def classify_article(self, text):
        """Classify article based on keywords."""
        categories = self.config['classification']['categories']
        
        # Simple keyword counting
        scores = {cat: 0 for cat in categories}
        
        # Use jieba to tokenize (optional, but better for Chinese)
        # If jieba is too slow for many articles, simple substring check works too
        words = list(jieba.cut(text))
        
        for word in words:
            for cat, keywords in categories.items():
                if word in keywords:
                    scores[cat] += 1
        
        # Find max score
        best_cat = max(scores, key=scores.get)
        if scores[best_cat] > 0:
            return best_cat
        return "未分类"

    def process_and_save(self, article_data):
        """Pipeline: Clean -> Classify -> Save DB -> Save File"""
        title = article_data['title']
        content = self.clean_text(article_data['content'])
        url = article_data['url']
        crawled_at = article_data['crawled_at']
        
        # Quality check: Word count
        word_count = len(content)
        if word_count < self.config['classification']['min_length']:
            logging.info(f"Skipping {title}: too short ({word_count} chars)")
            return False

        # Classification
        category = self.classify_article(content)
        
        # Save to DB
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO articles (title, content, category, source_url, crawled_at, word_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, content, category, url, crawled_at, word_count))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"DB Save failed for {title}: {e}")

        # Save to Markdown
        self.save_to_markdown(title, content, category, url, crawled_at)
        return True

    def save_to_markdown(self, title, content, category, url, date):
        base_path = self.config['storage']['save_path']
        # Create category folder
        cat_path = os.path.join(base_path, category)
        if not os.path.exists(cat_path):
            os.makedirs(cat_path)
        
        # Sanitize filename
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        filename = f"{safe_title}.md"
        filepath = os.path.join(cat_path, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                f.write(f"**分类**: {category} | **字数**: {len(content)} | **来源**: {url}\n")
                f.write(f"**时间**: {date}\n\n")
                f.write("---\n\n")
                f.write(content)
        except Exception as e:
            logging.error(f"File write failed for {title}: {e}")