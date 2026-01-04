"""
爬虫工具模块 - 提供健壮的爬虫基础设施
Crawler Utilities Module - Robust crawler infrastructure
"""

import random
import time
from typing import Optional, Callable, Any, List
from functools import wraps
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError


class UserAgentPool:
    """User-Agent 轮换池"""
    
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        ]
    
    def get_random(self) -> str:
        """随机获取一个 User-Agent"""
        return random.choice(self.user_agents)
    
    def get_all(self) -> List[str]:
        """获取所有 User-Agent"""
        return self.user_agents.copy()


class RateLimiter:
    """请求频率限制器"""
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """
        初始化频率限制器
        
        Args:
            min_delay: 最小延迟（秒）
            max_delay: 最大延迟（秒）
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = None
    
    def wait(self):
        """等待以满足频率限制"""
        current_time = time.time()
        
        if self.last_request_time is None:
            self.last_request_time = current_time
            return
        
        elapsed = current_time - self.last_request_time
        delay = random.uniform(self.min_delay, self.max_delay)
        
        if elapsed < delay:
            sleep_time = delay - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (RequestException, Timeout, ConnectionError),
    on_failure: Optional[Callable[[Exception, int], Any]] = None
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟（秒）
        backoff_factor: 退避因子（每次重试延迟乘以这个因子）
        exceptions: 需要重试的异常类型
        on_failure: 失败时的回调函数
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        if on_failure:
                            on_failure(e, attempt + 1)
                        
                        print(f"请求失败（第 {attempt + 1}/{max_attempts} 次）: {str(e)}")
                        print(f"等待 {current_delay:.2f} 秒后重试...")
                        
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        print(f"重试 {max_attempts} 次后仍然失败")
                except Exception as e:
                    last_exception = e
                    if on_failure:
                        on_failure(e, attempt + 1)
                    break
            
            if last_exception:
                if on_failure:
                    on_failure(last_exception, max_attempts)
                raise last_exception
        
        return wrapper
    return decorator


class RobustRequester:
    """
    健壮的 HTTP 请求器
    结合 User-Agent 轮换、重试机制、频率限制
    """
    
    def __init__(
        self,
        timeout: int = 30,
        max_attempts: int = 3,
        min_delay: float = 1.0,
        max_delay: float = 3.0
    ):
        """
        初始化健壮请求器
        
        Args:
            timeout: 请求超时时间（秒）
            max_attempts: 最大重试次数
            min_delay: 最小请求延迟（秒）
            max_delay: 最大请求延迟（秒）
        """
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.session = requests.Session()
        self.ua_pool = UserAgentPool()
        self.rate_limiter = RateLimiter(min_delay, max_delay)
    
    def get(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        allow_redirects: bool = True
    ) -> Optional[requests.Response]:
        """
        发送 GET 请求（带重试和频率限制）
        
        Args:
            url: 请求 URL
            headers: 自定义请求头
            params: 查询参数
            allow_redirects: 是否允许重定向
            
        Returns:
            Response 对象或 None
        """
        self.rate_limiter.wait()
        
        request_headers = headers or {}
        request_headers.setdefault('User-Agent', self.ua_pool.get_random())
        request_headers.setdefault(
            'Accept',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        )
        request_headers.setdefault(
            'Accept-Language',
            'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7'
        )
        
        @retry_on_failure(
            max_attempts=self.max_attempts,
            delay=1.0,
            backoff_factor=2.0
        )
        def _make_request():
            response = self.session.get(
                url,
                headers=request_headers,
                params=params,
                timeout=self.timeout,
                allow_redirects=allow_redirects
            )
            response.raise_for_status()
            return response
        
        try:
            return _make_request()
        except Exception as e:
            print(f"GET 请求失败: {url}, 错误: {str(e)}")
            return None
    
    def post(
        self,
        url: str,
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict] = None
    ) -> Optional[requests.Response]:
        """
        发送 POST 请求（带重试和频率限制）
        
        Args:
            url: 请求 URL
            data: 表单数据
            json: JSON 数据
            headers: 自定义请求头
            
        Returns:
            Response 对象或 None
        """
        self.rate_limiter.wait()
        
        request_headers = headers or {}
        request_headers.setdefault('User-Agent', self.ua_pool.get_random())
        
        @retry_on_failure(
            max_attempts=self.max_attempts,
            delay=1.0,
            backoff_factor=2.0
        )
        def _make_request():
            response = self.session.post(
                url,
                data=data,
                json=json,
                headers=request_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
        
        try:
            return _make_request()
        except Exception as e:
            print(f"POST 请求失败: {url}, 错误: {str(e)}")
            return None
    
    def close(self):
        """关闭 session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class CrawlerStats:
    """爬虫统计信息"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.retry_count = 0
        self.start_time = time.time()
    
    def record_success(self):
        """记录成功请求"""
        self.total_requests += 1
        self.successful_requests += 1
    
    def record_failure(self, retries: int = 0):
        """记录失败请求"""
        self.total_requests += 1
        self.failed_requests += 1
        self.retry_count += retries
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests * 100
    
    def get_elapsed_time(self) -> float:
        """获取运行时间（秒）"""
        return time.time() - self.start_time
    
    def get_summary(self) -> dict:
        """获取统计摘要"""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'retry_count': self.retry_count,
            'success_rate': self.get_success_rate(),
            'elapsed_time': self.get_elapsed_time(),
            'requests_per_second': self.total_requests / self.get_elapsed_time() if self.get_elapsed_time() > 0 else 0
        }
    
    def print_summary(self):
        """打印统计摘要"""
        summary = self.get_summary()
        print("\n" + "=" * 50)
        print("爬虫统计信息")
        print("=" * 50)
        print(f"总请求数: {summary['total_requests']}")
        print(f"成功请求: {summary['successful_requests']}")
        print(f"失败请求: {summary['failed_requests']}")
        print(f"重试次数: {summary['retry_count']}")
        print(f"成功率: {summary['success_rate']:.2f}%")
        print(f"运行时间: {summary['elapsed_time']:.2f} 秒")
        print(f"请求速率: {summary['requests_per_second']:.2f} 请求/秒")
        print("=" * 50)
