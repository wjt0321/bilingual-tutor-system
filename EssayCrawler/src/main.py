import json
import logging
import time
import schedule
import threading
import os
import datetime
import sqlite3
from src.crawler import GenericArticleCrawler
from src.processor import DataProcessor

class EssayCrawlerSystem:
    def __init__(self):
        self.config = self.load_config()
        self.processor = DataProcessor(self.config)
        self.crawler = GenericArticleCrawler(self.config)
        self.is_running = False
        self.log_callback = None  # Function to update GUI log

    def load_config(self):
        try:
            with open('config/settings.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Config load error: {e}")
            return {}

    def log(self, message):
        logging.info(message)
        if self.log_callback:
            self.log_callback(message)

    def run_single_job(self):
        self.log("Starting scheduled crawl job...")
        targets = self.config.get('targets', [])
        total_crawled = 0
        
        for target in targets:
            if not target.get('enabled', True):
                continue
                
            self.log(f"Crawling target: {target['name']}")
            try:
                articles = self.crawler.crawl_site(target)
                self.log(f"Found {len(articles)} articles from {target['name']}")
                
                for article in articles:
                    if self.processor.process_and_save(article):
                        total_crawled += 1
                        self.log(f"Saved: {article['title']}")
            except Exception as e:
                self.log(f"Error crawling {target['name']}: {e}")
        
        self.log(f"Job finished. Total new articles: {total_crawled}")
        self.generate_daily_report()
        return total_crawled

    def generate_daily_report(self):
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        report_path = os.path.join("data", "reports", f"{today}.md")
        
        try:
            conn = sqlite3.connect(self.config['storage']['db_path'])
            cursor = conn.cursor()
            cursor.execute("SELECT title, category, source_url, word_count FROM articles WHERE crawled_at LIKE ?", (f"{today}%",))
            rows = cursor.fetchall()
            conn.close()
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"# 爬取报告: {today}\n\n")
                f.write(f"**总计文章数**: {len(rows)}\n\n")
                f.write("| 标题 | 分类 | 字数 | 来源 |\n")
                f.write("|---|---|---|---|\n")
                for row in rows:
                    f.write(f"| {row[0]} | {row[1]} | {row[3]} | [链接]({row[2]}) |\n")
            
            self.log(f"Report generated: {report_path}")
        except Exception as e:
            self.log(f"Failed to generate report: {e}")

    def start_scheduler(self):
        run_time = self.config['schedule']['run_at']
        schedule.every().day.at(run_time).do(self.run_single_job)
        
        self.is_running = True
        self.log(f"Scheduler started. Will run at {run_time}")
        
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        self.is_running = False
        self.log("Stopping scheduler...")

if __name__ == "__main__":
    system = EssayCrawlerSystem()
    system.run_single_job()
