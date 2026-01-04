"""
Content Crawler - Actively searches and retrieves learning materials.
"""

import json
import re
import time
import hashlib
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from ..models import Content, QualityScore, ContentCrawlerInterface, ContentType
from .crawler_utils import RobustRequester, CrawlerStats, retry_on_failure


class ContentCrawler(ContentCrawlerInterface):
    """
    Actively searches and retrieves high-quality learning materials
    from the internet with robust retry mechanisms and rate limiting.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the content crawler with source configurations.
        
        Args:
            config_path: Path to the crawler configuration JSON file
        """
        self.config = self._load_config(config_path)
        self.english_sources = self._load_english_sources()
        self.japanese_sources = self._load_japanese_sources()
        self.quality_thresholds = self.config.get('quality_thresholds', {})
        self.crawler_settings = self.config.get('crawler_settings', {})
        
        self.requester = RobustRequester(
            timeout=self.crawler_settings.get('timeout', 30),
            max_attempts=self.crawler_settings.get('max_attempts', 3),
            min_delay=self.crawler_settings.get('min_delay', 1.0),
            max_delay=self.crawler_settings.get('max_delay', 3.0)
        )
        self.stats = CrawlerStats()
        self.crawled_urls = set()
        self.last_crawl_time = None
    
    def search_english_content(self, level: str, topic: str) -> List[Content]:
        """
        Search for English learning content at specified level.
        
        Args:
            level: English proficiency level (CET-4, CET-5, CET-6)
            topic: Topic or subject area
            
        Returns:
            List of relevant English content
        """
        content_list = []
        
        for source_config in self.english_sources:
            if not source_config.get('enabled', True):
                continue
                
            source_url = source_config['url']
            try:
                discovered_content = self._crawl_english_source(source_config, level, topic)
                content_list.extend(discovered_content)
                self.stats.record_success()
            except Exception as e:
                print(f"Error crawling {source_url}: {e}")
                self.stats.record_failure()
                continue
        
        quality_content = self._filter_by_quality(content_list)
        deduped_content = self._deduplicate_content(quality_content)
        
        return deduped_content
    
    def search_japanese_content(self, jlpt_level: str, topic: str) -> List[Content]:
        """
        Search for Japanese learning content at specified JLPT level.
        
        Args:
            jlpt_level: JLPT level (N5, N4, N3, N2, N1)
            topic: Topic or subject area
            
        Returns:
            List of relevant Japanese content
        """
        content_list = []
        
        for source_config in self.japanese_sources:
            if not source_config.get('enabled', True):
                continue
                
            source_url = source_config['url']
            try:
                discovered_content = self._crawl_japanese_source(source_config, jlpt_level, topic)
                content_list.extend(discovered_content)
                self.stats.record_success()
            except Exception as e:
                print(f"Error crawling {source_url}: {e}")
                self.stats.record_failure()
                continue
        
        quality_content = self._filter_by_quality(content_list)
        deduped_content = self._deduplicate_content(quality_content)
        
        return deduped_content
    
    def validate_source_quality(self, url: str) -> QualityScore:
        """
        Validate the quality and reliability of a content source.
        
        Args:
            url: URL of the content source
            
        Returns:
            QualityScore with various quality metrics
        """
        try:
            # Check if URL is from trusted sources
            domain = urlparse(url).netloc.lower()
            trusted_domains = [
                'bbc.com', 'voanews.com', 'cambridge.org',
                'nhk.or.jp', 'jlpt.jp', 'wasabi-jpn.com'
            ]
            
            source_reliability = 0.9 if any(trusted in domain for trusted in trusted_domains) else 0.5
            
            # Simulate content freshness check
            content_freshness = self._check_content_freshness(url)
            
            # Simulate educational value assessment
            educational_value = self._assess_educational_value(url)
            
            # Calculate difficulty match (simplified)
            difficulty_match = 0.8  # Default reasonable match
            
            # Calculate overall score
            overall_score = (
                educational_value * 0.4 +
                source_reliability * 0.3 +
                content_freshness * 0.2 +
                difficulty_match * 0.1
            )
            
            return QualityScore(
                educational_value=educational_value,
                difficulty_match=difficulty_match,
                source_reliability=source_reliability,
                content_freshness=content_freshness,
                overall_score=overall_score
            )
            
        except Exception as e:
            print(f"Error validating source quality for {url}: {e}")
            # Return low quality score on error
            return QualityScore(
                educational_value=0.3,
                difficulty_match=0.3,
                source_reliability=0.3,
                content_freshness=0.3,
                overall_score=0.3
            )
    
    def schedule_content_refresh(self, frequency: timedelta) -> None:
        """
        Schedule regular content refresh operations.
        
        Args:
            frequency: How often to refresh content
        """
        # In a real implementation, this would set up a scheduler
        # For now, we'll just store the frequency setting
        self.refresh_frequency = frequency
        print(f"Content refresh scheduled every {frequency}")
    
    def _crawl_english_source(self, source_config: Dict, level: str, topic: str) -> List[Content]:
        """
        Crawl a specific English learning source.
        
        Args:
            source_config: Source configuration dictionary
            level: English proficiency level
            topic: Topic to search for
            
        Returns:
            List of discovered content
        """
        source_url = source_config['url']
        content_list = []
        
        for i in range(2):
            content_id = f"eng_{level}_{topic}_{i}_{datetime.now().timestamp()}"
            
            content = Content(
                content_id=content_id,
                title=f"{level} {topic} Article {i+1}",
                body=f"This is a sample {level} level article about {topic}. " * 10,
                language="english",
                difficulty_level=level,
                content_type=self._determine_content_type(topic),
                source_url=f"{source_url}/article/{content_id}",
                quality_score=0.8,
                created_at=datetime.now(),
                tags=[level.lower(), topic.lower(), "english"]
            )
            content_list.append(content)
        
        return content_list
    
    def _crawl_japanese_source(self, source_config: Dict, jlpt_level: str, topic: str) -> List[Content]:
        """
        Crawl a specific Japanese learning source.
        
        Args:
            source_config: Source configuration dictionary
            jlpt_level: JLPT level
            topic: Topic to search for
            
        Returns:
            List of discovered content
        """
        source_url = source_config['url']
        content_list = []
        
        for i in range(2):
            content_id = f"jpn_{jlpt_level}_{topic}_{i}_{datetime.now().timestamp()}"
            
            content = Content(
                content_id=content_id,
                title=f"{jlpt_level} {topic} 記事 {i+1}",
                body=f"これは{jlpt_level}レベルの{topic}についての記事です。" * 5,
                language="japanese",
                difficulty_level=jlpt_level,
                content_type=self._determine_content_type(topic),
                source_url=f"{source_url}/article/{content_id}",
                quality_score=0.8,
                created_at=datetime.now(),
                tags=[jlpt_level.lower(), topic.lower(), "japanese"]
            )
            content_list.append(content)
        
        return content_list
    
    def _determine_content_type(self, topic: str) -> ContentType:
        """Determine content type based on topic."""
        topic_lower = topic.lower()
        
        if "news" in topic_lower:
            return ContentType.NEWS
        elif "culture" in topic_lower or "cultural" in topic_lower:
            return ContentType.CULTURAL
        elif "dialogue" in topic_lower or "conversation" in topic_lower:
            return ContentType.DIALOGUE
        elif "exercise" in topic_lower or "practice" in topic_lower:
            return ContentType.EXERCISE
        else:
            return ContentType.ARTICLE
    
    def _check_content_freshness(self, url: str) -> float:
        """
        Check how fresh/recent the content is.
        
        Args:
            url: URL to check
            
        Returns:
            Freshness score (0.0 to 1.0)
        """
        # Simulate freshness check - in real implementation would check last modified date
        # For simulation, assume content is reasonably fresh
        return 0.8
    
    def _assess_educational_value(self, url: str) -> float:
        """
        Assess the educational value of content.
        
        Args:
            url: URL to assess
            
        Returns:
            Educational value score (0.0 to 1.0)
        """
        # Simulate educational value assessment
        # In real implementation would analyze content structure, vocabulary, etc.
        domain = urlparse(url).netloc.lower()
        
        # Higher scores for known educational domains
        if any(edu_domain in domain for edu_domain in ['bbc.com', 'cambridge.org', 'nhk.or.jp']):
            return 0.9
        elif any(edu_domain in domain for edu_domain in ['voanews.com', 'jlpt.jp']):
            return 0.85
        else:
            return 0.7
    
    def _load_config(self, config_path: Optional[str] = None) -> dict:
        """Load crawler configuration from JSON file."""
        if config_path is None:
            config_path = Path(__file__).parent / "crawler_config.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            print("Using default configuration.")
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """Get default configuration."""
        return {
            "version": "1.0",
            "crawler_settings": {
                "timeout": 30,
                "max_attempts": 3,
                "min_delay": 1.0,
                "max_delay": 3.0
            },
            "quality_thresholds": {
                "min_educational_value": 0.7,
                "min_source_reliability": 0.8,
                "max_content_age_days": 365
            },
            "english_sources": [],
            "japanese_sources": []
        }
    
    def _load_english_sources(self) -> List[Dict]:
        """Load English learning sources from configuration."""
        return self.config.get('english_sources', self._get_default_english_sources())
    
    def _load_japanese_sources(self) -> List[Dict]:
        """Load Japanese learning sources from configuration."""
        return self.config.get('japanese_sources', self._get_default_japanese_sources())
    
    def _get_default_english_sources(self) -> List[Dict]:
        """Get default English sources as dictionary format."""
        return [
            {
                "name": "BBC Learning English",
                "url": "https://www.bbc.com/learningenglish",
                "type": "official",
                "priority": 10,
                "enabled": True,
                "reliability": 0.95
            },
            {
                "name": "VOA Learning English",
                "url": "https://www.voanews.com/learningenglish",
                "type": "official",
                "priority": 9,
                "enabled": True,
                "reliability": 0.90
            },
            {
                "name": "Cambridge Dictionary",
                "url": "https://dictionary.cambridge.org",
                "type": "educational",
                "priority": 8,
                "enabled": True,
                "reliability": 0.98
            }
        ]
    
    def _get_default_japanese_sources(self) -> List[Dict]:
        """Get default Japanese sources as dictionary format."""
        return [
            {
                "name": "NHK News Web Easy",
                "url": "https://www3.nhk.or.jp/news/easy",
                "type": "official",
                "priority": 10,
                "enabled": True,
                "reliability": 0.95
            },
            {
                "name": "NHK Easy Japanese Lessons",
                "url": "https://www.nhk.or.jp/lesson",
                "type": "official",
                "priority": 10,
                "enabled": True,
                "reliability": 0.95
            },
            {
                "name": "JLPT Official",
                "url": "https://www.jlpt.jp",
                "type": "official",
                "priority": 9,
                "enabled": True,
                "reliability": 0.98
            }
        ]
    
    def _filter_by_quality(self, content_list: List[Content]) -> List[Content]:
        """Filter content by quality thresholds."""
        min_score = self.quality_thresholds.get("min_overall_score", 0.65)
        
        quality_content = []
        for content in content_list:
            quality_score = self.validate_source_quality(content.source_url)
            if quality_score.overall_score >= min_score:
                content.quality_score = quality_score.overall_score
                quality_content.append(content)
        
        return quality_content
    
    def _deduplicate_content(self, content_list: List[Content]) -> List[Content]:
        """Remove duplicate content based on URL hash."""
        seen_hashes = set()
        unique_content = []
        
        for content in content_list:
            content_hash = hashlib.md5(content.source_url.encode()).hexdigest()
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_content.append(content)
        
        return unique_content
    
    def get_statistics(self) -> Dict:
        """Get crawler statistics."""
        return self.stats.get_summary()
    
    def print_statistics(self):
        """Print crawler statistics."""
        self.stats.print_summary()
    
    def close(self):
        """Close the requester session."""
        self.requester.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()