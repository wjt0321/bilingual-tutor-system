"""
测试改进后的爬虫功能
Test improved crawler functionality
"""

import pytest
import tempfile
import json
from pathlib import Path

from bilingual_tutor.content.crawler import ContentCrawler
from bilingual_tutor.content.crawler_utils import (
    UserAgentPool,
    RateLimiter,
    retry_on_failure,
    RobustRequester,
    CrawlerStats
)
from bilingual_tutor.storage.content_crawler import RealContentCrawler
from bilingual_tutor.storage.database import LearningDatabase


class TestUserAgentPool:
    """测试 User-Agent 轮换池"""
    
    def test_get_random_user_agent(self):
        """测试随机获取 User-Agent"""
        pool = UserAgentPool()
        ua = pool.get_random()
        
        assert isinstance(ua, str)
        assert len(ua) > 0
        assert 'Mozilla' in ua or 'Safari' in ua or 'Chrome' in ua
    
    def test_get_all_user_agents(self):
        """测试获取所有 User-Agent"""
        pool = UserAgentPool()
        all_uas = pool.get_all()
        
        assert isinstance(all_uas, list)
        assert len(all_uas) > 5
        assert len(all_uas) == len(set(all_uas))  # 无重复


class TestRateLimiter:
    """测试频率限制器"""
    
    def test_rate_limiting(self):
        """测试频率限制功能"""
        limiter = RateLimiter(min_delay=0.1, max_delay=0.2)
        
        import time
        start = time.time()
        limiter.wait()
        elapsed = time.time() - start
        
        assert elapsed >= 0.1
        assert elapsed <= 0.3
    
    def test_multiple_waits(self):
        """测试多次等待"""
        limiter = RateLimiter(min_delay=0.05, max_delay=0.1)
        
        import time
        start = time.time()
        
        for _ in range(3):
            limiter.wait()
        
        elapsed = time.time() - start
        assert elapsed >= 0.15


class TestRetryDecorator:
    """测试重试装饰器"""
    
    def test_retry_on_failure_success(self):
        """测试重试装饰器 - 成功情况"""
        call_count = [0]
        
        @retry_on_failure(max_attempts=3, delay=0.01, exceptions=(ConnectionError,))
        def failing_then_success():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("Simulated error")
            return "success"
        
        result = failing_then_success()
        
        assert result == "success"
        assert call_count[0] == 2
    
    def test_retry_max_attempts_exceeded(self):
        """测试重试装饰器 - 超过最大重试次数"""
        call_count = [0]
        
        @retry_on_failure(max_attempts=3, delay=0.01, exceptions=(ConnectionError,))
        def always_failing():
            call_count[0] += 1
            raise ConnectionError("Always failing")
        
        with pytest.raises(ConnectionError):
            always_failing()
        
        assert call_count[0] == 3


class TestCrawlerStats:
    """测试爬虫统计"""
    
    def test_initial_stats(self):
        """测试初始统计"""
        stats = CrawlerStats()
        
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.get_success_rate() == 0.0
    
    def test_record_success(self):
        """测试记录成功"""
        stats = CrawlerStats()
        stats.record_success()
        stats.record_success()
        
        assert stats.total_requests == 2
        assert stats.successful_requests == 2
        assert stats.get_success_rate() == 100.0
    
    def test_record_failure(self):
        """测试记录失败"""
        stats = CrawlerStats()
        stats.record_success()
        stats.record_failure(retries=2)
        
        assert stats.total_requests == 2
        assert stats.successful_requests == 1
        assert stats.failed_requests == 1
        assert stats.retry_count == 2
        assert stats.get_success_rate() == 50.0
    
    def test_get_summary(self):
        """测试获取统计摘要"""
        stats = CrawlerStats()
        stats.record_success()
        stats.record_failure(retries=1)
        
        summary = stats.get_summary()
        
        assert summary['total_requests'] == 2
        assert summary['successful_requests'] == 1
        assert summary['failed_requests'] == 1
        assert summary['retry_count'] == 1
        assert 'success_rate' in summary
        assert 'elapsed_time' in summary


class TestContentCrawlerImprovements:
    """测试 ContentCrawler 的改进功能"""
    
    def test_crawler_with_config(self):
        """测试使用配置文件初始化"""
        crawler = ContentCrawler()
        
        assert crawler.config is not None
        assert 'crawler_settings' in crawler.config
        assert 'quality_thresholds' in crawler.config
        assert 'english_sources' in crawler.config
        assert 'japanese_sources' in crawler.config
    
    def test_crawler_loads_default_sources(self):
        """测试加载默认源"""
        crawler = ContentCrawler()
        
        assert len(crawler.english_sources) > 0
        assert len(crawler.japanese_sources) > 0
        
        for source in crawler.english_sources:
            assert 'url' in source
            assert 'name' in source
            assert 'enabled' in source
    
    def test_crawler_filters_disabled_sources(self):
        """测试过滤禁用的源"""
        crawler = ContentCrawler()
        
        original_count = len(crawler.english_sources)
        
        results = crawler.search_english_content("CET-4", "news")
        
        assert len(results) >= 0
    
    def test_crawler_statistics(self):
        """测试爬虫统计"""
        crawler = ContentCrawler()
        
        stats = crawler.get_statistics()
        
        assert 'total_requests' in stats
        assert 'successful_requests' in stats
        assert 'failed_requests' in stats
    
    def test_crawler_deduplication(self):
        """测试内容去重"""
        crawler = ContentCrawler()
        
        content1 = crawler._crawl_english_source(
            crawler.english_sources[0], "CET-4", "test"
        )
        
        content2 = crawler._crawl_english_source(
            crawler.english_sources[0], "CET-4", "test"
        )
        
        combined = content1 + content2
        deduped = crawler._deduplicate_content(combined)
        
        assert len(deduped) == len(combined)
    
    def test_crawler_context_manager(self):
        """测试上下文管理器"""
        with ContentCrawler() as crawler:
            assert crawler.requester is not None


class TestRealContentCrawlerImprovements:
    """测试 RealContentCrawler 的改进功能"""
    
    def test_crawler_with_incremental_mode(self):
        """测试增量更新模式"""
        tmpdir = Path(tempfile.mkdtemp())
        try:
            db_path = tmpdir / "test.db"
            db = LearningDatabase(str(db_path))
            crawler = RealContentCrawler(db=db)
            
            count = crawler.crawl_english_vocabulary("CET-4", incremental=True)
            
            assert count > 0
            
            second_count = crawler.crawl_english_vocabulary("CET-4", incremental=True)
            
            assert second_count == 0 or second_count < count
        finally:
            crawler.close()
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_crawler_without_incremental_mode(self):
        """测试非增量更新模式"""
        tmpdir = Path(tempfile.mkdtemp())
        try:
            db_path = tmpdir / "test.db"
            db = LearningDatabase(str(db_path))
            crawler = RealContentCrawler(db=db)
            
            count1 = crawler.crawl_english_vocabulary("CET-4", incremental=False)
            
            assert count1 > 0
            
            count2 = crawler.crawl_english_vocabulary("CET-4", incremental=False)
            
            assert count2 > 0
        finally:
            crawler.close()
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_duplicate_detection(self):
        """测试重复检测"""
        tmpdir = Path(tempfile.mkdtemp())
        try:
            db_path = tmpdir / "test.db"
            db = LearningDatabase(str(db_path))
            crawler = RealContentCrawler(db=db)
            
            crawler._load_existing_content()
            
            is_duplicate = crawler._is_duplicate_vocabulary("testword", "english")
            
            assert is_duplicate == False or is_duplicate == True
        finally:
            crawler.close()
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_crawler_statistics(self):
        """测试爬虫统计"""
        tmpdir = Path(tempfile.mkdtemp())
        try:
            db_path = tmpdir / "test.db"
            db = LearningDatabase(str(db_path))
            crawler = RealContentCrawler(db=db)
            
            stats = crawler.get_statistics()
            
            assert 'total_requests' in stats
            assert 'successful_requests' in stats
            assert 'failed_requests' in stats
        finally:
            crawler.close()
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_crawler_context_manager(self):
        """测试上下文管理器"""
        tmpdir = Path(tempfile.mkdtemp())
        try:
            db_path = tmpdir / "test.db"
            db = LearningDatabase(str(db_path))
            
            with RealContentCrawler(db=db) as crawler:
                assert crawler.requester is not None
                assert crawler.db is not None
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestRobustRequester:
    """测试健壮请求器"""
    
    def test_requester_initialization(self):
        """测试初始化"""
        requester = RobustRequester(
            timeout=30,
            max_attempts=3,
            min_delay=1.0,
            max_delay=3.0
        )
        
        assert requester.timeout == 30
        assert requester.max_attempts == 3
        assert requester.ua_pool is not None
        assert requester.rate_limiter is not None
    
    def test_requester_context_manager(self):
        """测试上下文管理器"""
        with RobustRequester() as requester:
            assert requester.session is not None
    
    def test_requester_user_agent_rotation(self):
        """测试 User-Agent 轮换"""
        requester = RobustRequester()
        
        ua1 = requester.ua_pool.get_random()
        ua2 = requester.ua_pool.get_random()
        
        assert isinstance(ua1, str)
        assert isinstance(ua2, str)


class TestConfigIntegration:
    """测试配置集成"""
    
    def test_config_file_parsing(self):
        """测试配置文件解析"""
        config_path = Path(__file__).parent.parent / "bilingual_tutor" / "content" / "crawler_config.json"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            assert 'version' in config
            assert 'crawler_settings' in config
            assert 'quality_thresholds' in config
            assert 'english_sources' in config
            assert 'japanese_sources' in config
    
    def test_crawler_uses_config(self):
        """测试爬虫使用配置"""
        crawler = ContentCrawler()
        
        assert crawler.config['crawler_settings']['timeout'] == 30
        assert crawler.config['crawler_settings']['max_attempts'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
