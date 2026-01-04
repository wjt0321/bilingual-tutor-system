"""
Redis缓存管理器实现
提供学习计划缓存、内容推荐缓存和用户会话缓存功能
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Pattern
import redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from ..models import (
    CacheManagerInterface, CacheConfig, CacheKey, CacheMetrics,
    DailyPlan, Content, StudySession, UserProfile
)


class RedisCacheManager(CacheManagerInterface):
    """Redis缓存管理器实现"""
    
    # 缓存键前缀常量
    DAILY_PLAN_PREFIX = "daily_plan"
    CONTENT_RECOMMENDATIONS_PREFIX = "content_rec"
    USER_SESSION_PREFIX = "user_session"
    USER_PROFILE_PREFIX = "user_profile"
    METRICS_KEY = "cache_metrics"
    
    def __init__(self, config: CacheConfig):
        """
        初始化Redis缓存管理器
        
        Args:
            config: 缓存配置
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._redis_client: Optional[redis.Redis] = None
        self._metrics = CacheMetrics()
        self._is_connected = False
        
        # 尝试连接Redis
        self._connect()
    
    def _connect(self) -> bool:
        """
        连接到Redis服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 创建连接池
            pool = redis.ConnectionPool(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                max_connections=self.config.connection_pool_size,
                socket_timeout=self.config.socket_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                decode_responses=True  # 自动解码响应为字符串
            )
            
            self._redis_client = redis.Redis(connection_pool=pool)
            
            # 测试连接
            self._redis_client.ping()
            self._is_connected = True
            
            # 设置内存策略
            try:
                self._redis_client.config_set('maxmemory', self.config.max_memory)
                self._redis_client.config_set('maxmemory-policy', self.config.eviction_policy)
            except RedisError as e:
                self.logger.warning(f"无法设置Redis内存策略: {e}")
            
            self.logger.info(f"成功连接到Redis服务器 {self.config.redis_host}:{self.config.redis_port}")
            return True
            
        except (ConnectionError, TimeoutError) as e:
            self.logger.error(f"连接Redis失败: {e}")
            self._is_connected = False
            return False
        except Exception as e:
            self.logger.error(f"Redis连接异常: {e}")
            self._is_connected = False
            return False
    
    def _ensure_connection(self) -> bool:
        """
        确保Redis连接可用
        
        Returns:
            bool: 连接是否可用
        """
        if not self._is_connected or not self._redis_client:
            return self._connect()
        
        try:
            self._redis_client.ping()
            return True
        except (ConnectionError, TimeoutError):
            self.logger.warning("Redis连接丢失，尝试重新连接...")
            return self._connect()
    
    def _create_cache_key(self, prefix: str, key: str) -> str:
        """
        创建缓存键
        
        Args:
            prefix: 键前缀
            key: 键值
            
        Returns:
            str: 完整的缓存键
        """
        return f"bilingual_tutor:{prefix}:{key}"
    
    def _serialize_data(self, data: Any) -> str:
        """
        序列化数据为JSON字符串
        
        Args:
            data: 要序列化的数据
            
        Returns:
            str: JSON字符串
        """
        try:
            if hasattr(data, 'to_dict'):
                # 如果对象有to_dict方法，使用它
                return json.dumps(data.to_dict(), ensure_ascii=False, default=str)
            elif hasattr(data, '__dict__'):
                # 如果是dataclass或普通对象，序列化其属性
                return json.dumps(data.__dict__, ensure_ascii=False, default=str)
            else:
                # 直接序列化
                return json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            self.logger.error(f"数据序列化失败: {e}")
            raise
    
    def _deserialize_data(self, data: str, target_type: type = dict) -> Any:
        """
        反序列化JSON字符串为数据对象
        
        Args:
            data: JSON字符串
            target_type: 目标类型
            
        Returns:
            Any: 反序列化的数据
        """
        try:
            json_data = json.loads(data)
            
            # 如果目标类型有from_dict方法，使用它
            if hasattr(target_type, 'from_dict'):
                return target_type.from_dict(json_data)
            
            # 否则返回字典
            return json_data
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"数据反序列化失败: {e}")
            raise
    
    def _update_metrics(self, hit: bool, response_time: float = 0.0):
        """
        更新缓存性能指标
        
        Args:
            hit: 是否命中缓存
            response_time: 响应时间（毫秒）
        """
        self._metrics.total_requests += 1
        
        if hit:
            self._metrics.hit_count += 1
        else:
            self._metrics.miss_count += 1
        
        # 更新命中率
        self._metrics.hit_rate = self._metrics.calculate_hit_rate()
        
        # 更新平均响应时间
        if response_time > 0:
            total_time = self._metrics.avg_response_time * (self._metrics.total_requests - 1)
            self._metrics.avg_response_time = (total_time + response_time) / self._metrics.total_requests
        
        self._metrics.last_updated = datetime.now()
    
    def get_daily_plan(self, user_id: str) -> Optional[DailyPlan]:
        """
        获取缓存的每日学习计划
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[DailyPlan]: 缓存的学习计划，如果不存在则返回None
        """
        if not self._ensure_connection():
            self.logger.warning("Redis连接不可用，跳过缓存查询")
            self._update_metrics(hit=False)
            return None
        
        start_time = time.time()
        
        try:
            # 使用当前日期作为键的一部分
            today = datetime.now().strftime("%Y-%m-%d")
            cache_key = self._create_cache_key(self.DAILY_PLAN_PREFIX, f"{user_id}:{today}")
            
            cached_data = self._redis_client.get(cache_key)
            
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            if cached_data:
                self.logger.debug(f"缓存命中: 用户 {user_id} 的每日学习计划")
                self._update_metrics(hit=True, response_time=response_time)
                return self._deserialize_data(cached_data, DailyPlan)
            else:
                self.logger.debug(f"缓存未命中: 用户 {user_id} 的每日学习计划")
                self._update_metrics(hit=False, response_time=response_time)
                return None
                
        except RedisError as e:
            self.logger.error(f"获取每日学习计划缓存失败: {e}")
            self._update_metrics(hit=False)
            return None
    
    def set_daily_plan(self, user_id: str, plan: DailyPlan, ttl: Optional[int] = None) -> bool:
        """
        缓存每日学习计划
        
        Args:
            user_id: 用户ID
            plan: 学习计划
            ttl: 过期时间（秒），如果为None则使用默认值
            
        Returns:
            bool: 是否成功缓存
        """
        if not self._ensure_connection():
            self.logger.warning("Redis连接不可用，跳过缓存设置")
            return False
        
        try:
            # 使用当前日期作为键的一部分
            today = datetime.now().strftime("%Y-%m-%d")
            cache_key = self._create_cache_key(self.DAILY_PLAN_PREFIX, f"{user_id}:{today}")
            
            # 序列化数据
            serialized_data = self._serialize_data(plan)
            
            # 设置过期时间（默认为一天）
            expire_time = ttl or 86400  # 24小时
            
            # 存储到Redis
            result = self._redis_client.setex(cache_key, expire_time, serialized_data)
            
            if result:
                self.logger.debug(f"成功缓存用户 {user_id} 的每日学习计划")
                return True
            else:
                self.logger.warning(f"缓存用户 {user_id} 的每日学习计划失败")
                return False
                
        except RedisError as e:
            self.logger.error(f"设置每日学习计划缓存失败: {e}")
            return False
    
    def get_content_recommendations(self, user_id: str, language: str) -> Optional[List[Content]]:
        """
        获取内容推荐缓存
        
        Args:
            user_id: 用户ID
            language: 语言（english/japanese）
            
        Returns:
            Optional[List[Content]]: 缓存的内容推荐列表
        """
        if not self._ensure_connection():
            self.logger.warning("Redis连接不可用，跳过缓存查询")
            self._update_metrics(hit=False)
            return None
        
        start_time = time.time()
        
        try:
            cache_key = self._create_cache_key(self.CONTENT_RECOMMENDATIONS_PREFIX, f"{user_id}:{language}")
            
            cached_data = self._redis_client.get(cache_key)
            
            response_time = (time.time() - start_time) * 1000
            
            if cached_data:
                self.logger.debug(f"缓存命中: 用户 {user_id} 的 {language} 内容推荐")
                self._update_metrics(hit=True, response_time=response_time)
                
                # 反序列化为内容列表
                content_list_data = self._deserialize_data(cached_data)
                return [self._deserialize_data(json.dumps(item), Content) for item in content_list_data]
            else:
                self.logger.debug(f"缓存未命中: 用户 {user_id} 的 {language} 内容推荐")
                self._update_metrics(hit=False, response_time=response_time)
                return None
                
        except RedisError as e:
            self.logger.error(f"获取内容推荐缓存失败: {e}")
            self._update_metrics(hit=False)
            return None
    
    def set_content_recommendations(self, user_id: str, language: str, content: List[Content], ttl: Optional[int] = None) -> bool:
        """
        缓存内容推荐
        
        Args:
            user_id: 用户ID
            language: 语言
            content: 内容列表
            ttl: 过期时间（秒）
            
        Returns:
            bool: 是否成功缓存
        """
        if not self._ensure_connection():
            self.logger.warning("Redis连接不可用，跳过缓存设置")
            return False
        
        try:
            cache_key = self._create_cache_key(self.CONTENT_RECOMMENDATIONS_PREFIX, f"{user_id}:{language}")
            
            # 序列化内容列表
            content_list_data = [item.__dict__ if hasattr(item, '__dict__') else item for item in content]
            serialized_data = json.dumps(content_list_data, ensure_ascii=False, default=str)
            
            # 设置过期时间（默认为1小时）
            expire_time = ttl or 3600
            
            result = self._redis_client.setex(cache_key, expire_time, serialized_data)
            
            if result:
                self.logger.debug(f"成功缓存用户 {user_id} 的 {language} 内容推荐")
                return True
            else:
                self.logger.warning(f"缓存用户 {user_id} 的 {language} 内容推荐失败")
                return False
                
        except RedisError as e:
            self.logger.error(f"设置内容推荐缓存失败: {e}")
            return False
    
    def get_user_session(self, session_id: str) -> Optional[StudySession]:
        """
        获取用户会话缓存
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[StudySession]: 缓存的用户会话
        """
        if not self._ensure_connection():
            self.logger.warning("Redis连接不可用，跳过缓存查询")
            self._update_metrics(hit=False)
            return None
        
        start_time = time.time()
        
        try:
            cache_key = self._create_cache_key(self.USER_SESSION_PREFIX, session_id)
            
            cached_data = self._redis_client.get(cache_key)
            
            response_time = (time.time() - start_time) * 1000
            
            if cached_data:
                self.logger.debug(f"缓存命中: 会话 {session_id}")
                self._update_metrics(hit=True, response_time=response_time)
                return self._deserialize_data(cached_data, StudySession)
            else:
                self.logger.debug(f"缓存未命中: 会话 {session_id}")
                self._update_metrics(hit=False, response_time=response_time)
                return None
                
        except RedisError as e:
            self.logger.error(f"获取用户会话缓存失败: {e}")
            self._update_metrics(hit=False)
            return None
    
    def set_user_session(self, session_id: str, session: StudySession, ttl: Optional[int] = None) -> bool:
        """
        缓存用户会话
        
        Args:
            session_id: 会话ID
            session: 用户会话
            ttl: 过期时间（秒）
            
        Returns:
            bool: 是否成功缓存
        """
        if not self._ensure_connection():
            self.logger.warning("Redis连接不可用，跳过缓存设置")
            return False
        
        try:
            cache_key = self._create_cache_key(self.USER_SESSION_PREFIX, session_id)
            
            serialized_data = self._serialize_data(session)
            
            # 设置过期时间（默认为2小时）
            expire_time = ttl or 7200
            
            result = self._redis_client.setex(cache_key, expire_time, serialized_data)
            
            if result:
                self.logger.debug(f"成功缓存会话 {session_id}")
                return True
            else:
                self.logger.warning(f"缓存会话 {session_id} 失败")
                return False
                
        except RedisError as e:
            self.logger.error(f"设置用户会话缓存失败: {e}")
            return False
    
    def invalidate_user_cache(self, user_id: str) -> bool:
        """
        清除用户相关的所有缓存
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功清除
        """
        if not self._ensure_connection():
            self.logger.warning("Redis连接不可用，跳过缓存清除")
            return False
        
        try:
            # 构建用户相关的缓存键模式
            patterns = [
                f"bilingual_tutor:{self.DAILY_PLAN_PREFIX}:{user_id}:*",
                f"bilingual_tutor:{self.CONTENT_RECOMMENDATIONS_PREFIX}:{user_id}:*",
                f"bilingual_tutor:{self.USER_PROFILE_PREFIX}:{user_id}",
            ]
            
            deleted_count = 0
            
            for pattern in patterns:
                keys = self._redis_client.keys(pattern)
                if keys:
                    deleted_count += self._redis_client.delete(*keys)
            
            self.logger.info(f"成功清除用户 {user_id} 的 {deleted_count} 个缓存项")
            return True
            
        except RedisError as e:
            self.logger.error(f"清除用户缓存失败: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        根据模式清除缓存
        
        Args:
            pattern: 缓存键模式
            
        Returns:
            int: 清除的缓存项数量
        """
        if not self._ensure_connection():
            self.logger.warning("Redis连接不可用，跳过缓存清除")
            return 0
        
        try:
            # 添加系统前缀
            full_pattern = f"bilingual_tutor:{pattern}"
            keys = self._redis_client.keys(full_pattern)
            
            if keys:
                deleted_count = self._redis_client.delete(*keys)
                self.logger.info(f"根据模式 '{pattern}' 清除了 {deleted_count} 个缓存项")
                return deleted_count
            else:
                self.logger.debug(f"模式 '{pattern}' 未匹配到任何缓存项")
                return 0
                
        except RedisError as e:
            self.logger.error(f"根据模式清除缓存失败: {e}")
            return 0
    
    def preload_cache(self, user_id: str) -> bool:
        """
        预热用户缓存
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功预热
        """
        if not self._ensure_connection():
            self.logger.warning("Redis连接不可用，跳过缓存预热")
            return False
        
        try:
            # 这里可以实现缓存预热逻辑
            # 例如：预加载用户档案、常用内容推荐等
            
            self.logger.info(f"开始为用户 {user_id} 预热缓存")
            
            # 预热逻辑将在后续与其他组件集成时实现
            # 目前返回True表示预热成功
            
            return True
            
        except Exception as e:
            self.logger.error(f"缓存预热失败: {e}")
            return False
    
    def get_cache_metrics(self) -> CacheMetrics:
        """
        获取缓存性能指标
        
        Returns:
            CacheMetrics: 缓存性能指标
        """
        if self._ensure_connection():
            try:
                # 获取Redis内存使用情况
                info = self._redis_client.info('memory')
                self._metrics.memory_usage = info.get('used_memory', 0)
                
                # 获取活跃键数量
                self._metrics.active_keys = self._redis_client.dbsize()
                
            except RedisError as e:
                self.logger.error(f"获取Redis统计信息失败: {e}")
        
        return self._metrics
    
    def health_check(self) -> bool:
        """
        缓存系统健康检查
        
        Returns:
            bool: 系统是否健康
        """
        try:
            if not self._ensure_connection():
                return False
            
            # 执行ping测试
            self._redis_client.ping()
            
            # 测试基本读写操作
            test_key = "bilingual_tutor:health_check"
            test_value = f"health_check_{int(time.time())}"
            
            # 写入测试
            self._redis_client.setex(test_key, 10, test_value)
            
            # 读取测试
            retrieved_value = self._redis_client.get(test_key)
            
            # 清理测试键
            self._redis_client.delete(test_key)
            
            # 验证读写一致性
            if retrieved_value == test_value:
                self.logger.debug("缓存系统健康检查通过")
                return True
            else:
                self.logger.error("缓存系统健康检查失败：读写不一致")
                return False
                
        except Exception as e:
            self.logger.error(f"缓存系统健康检查异常: {e}")
            return False
    
    def close(self):
        """关闭Redis连接"""
        if self._redis_client:
            try:
                self._redis_client.close()
                self.logger.info("Redis连接已关闭")
            except Exception as e:
                self.logger.error(f"关闭Redis连接时出错: {e}")
            finally:
                self._redis_client = None
                self._is_connected = False


class FallbackCacheManager(CacheManagerInterface):
    """
    回退缓存管理器
    当Redis不可用时使用内存缓存作为回退方案
    """
    
    def __init__(self):
        """初始化回退缓存管理器"""
        self.logger = logging.getLogger(__name__)
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._metrics = CacheMetrics()
        self.logger.warning("使用内存回退缓存管理器")
    
    def _create_cache_key(self, prefix: str, key: str) -> str:
        """创建缓存键"""
        return f"{prefix}:{key}"
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存项是否过期"""
        if 'expires_at' not in cache_entry:
            return False
        
        return datetime.now() > cache_entry['expires_at']
    
    def _update_metrics(self, hit: bool):
        """更新缓存指标"""
        self._metrics.total_requests += 1
        
        if hit:
            self._metrics.hit_count += 1
        else:
            self._metrics.miss_count += 1
        
        self._metrics.hit_rate = self._metrics.calculate_hit_rate()
        self._metrics.last_updated = datetime.now()
    
    def get_daily_plan(self, user_id: str) -> Optional[DailyPlan]:
        """获取每日学习计划（内存缓存）"""
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = self._create_cache_key("daily_plan", f"{user_id}:{today}")
        
        if cache_key in self._memory_cache:
            cache_entry = self._memory_cache[cache_key]
            
            if not self._is_expired(cache_entry):
                self._update_metrics(hit=True)
                return cache_entry['data']
            else:
                # 清除过期缓存
                del self._memory_cache[cache_key]
        
        self._update_metrics(hit=False)
        return None
    
    def set_daily_plan(self, user_id: str, plan: DailyPlan, ttl: Optional[int] = None) -> bool:
        """设置每日学习计划（内存缓存）"""
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = self._create_cache_key("daily_plan", f"{user_id}:{today}")
        
        expires_at = datetime.now() + timedelta(seconds=ttl or 86400)
        
        self._memory_cache[cache_key] = {
            'data': plan,
            'expires_at': expires_at
        }
        
        return True
    
    def get_content_recommendations(self, user_id: str, language: str) -> Optional[List[Content]]:
        """获取内容推荐（内存缓存）"""
        cache_key = self._create_cache_key("content_rec", f"{user_id}:{language}")
        
        if cache_key in self._memory_cache:
            cache_entry = self._memory_cache[cache_key]
            
            if not self._is_expired(cache_entry):
                self._update_metrics(hit=True)
                return cache_entry['data']
            else:
                del self._memory_cache[cache_key]
        
        self._update_metrics(hit=False)
        return None
    
    def set_content_recommendations(self, user_id: str, language: str, content: List[Content], ttl: Optional[int] = None) -> bool:
        """设置内容推荐（内存缓存）"""
        cache_key = self._create_cache_key("content_rec", f"{user_id}:{language}")
        
        expires_at = datetime.now() + timedelta(seconds=ttl or 3600)
        
        self._memory_cache[cache_key] = {
            'data': content,
            'expires_at': expires_at
        }
        
        return True
    
    def get_user_session(self, session_id: str) -> Optional[StudySession]:
        """获取用户会话（内存缓存）"""
        cache_key = self._create_cache_key("user_session", session_id)
        
        if cache_key in self._memory_cache:
            cache_entry = self._memory_cache[cache_key]
            
            if not self._is_expired(cache_entry):
                self._update_metrics(hit=True)
                return cache_entry['data']
            else:
                del self._memory_cache[cache_key]
        
        self._update_metrics(hit=False)
        return None
    
    def set_user_session(self, session_id: str, session: StudySession, ttl: Optional[int] = None) -> bool:
        """设置用户会话（内存缓存）"""
        cache_key = self._create_cache_key("user_session", session_id)
        
        expires_at = datetime.now() + timedelta(seconds=ttl or 7200)
        
        self._memory_cache[cache_key] = {
            'data': session,
            'expires_at': expires_at
        }
        
        return True
    
    def invalidate_user_cache(self, user_id: str) -> bool:
        """清除用户相关缓存（内存缓存）"""
        keys_to_delete = []
        
        for key in self._memory_cache.keys():
            if user_id in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._memory_cache[key]
        
        self.logger.info(f"清除用户 {user_id} 的 {len(keys_to_delete)} 个内存缓存项")
        return True
    
    def invalidate_pattern(self, pattern: str) -> int:
        """根据模式清除缓存（内存缓存）"""
        keys_to_delete = []
        
        for key in self._memory_cache.keys():
            if pattern in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._memory_cache[key]
        
        return len(keys_to_delete)
    
    def preload_cache(self, user_id: str) -> bool:
        """预热缓存（内存缓存）"""
        # 内存缓存不需要预热
        return True
    
    def get_cache_metrics(self) -> CacheMetrics:
        """获取缓存指标（内存缓存）"""
        self._metrics.memory_usage = len(self._memory_cache) * 1024  # 估算内存使用
        self._metrics.active_keys = len(self._memory_cache)
        return self._metrics
    
    def health_check(self) -> bool:
        """健康检查（内存缓存）"""
        return True


def create_cache_manager(config: Optional[CacheConfig] = None) -> CacheManagerInterface:
    """
    创建缓存管理器实例
    
    Args:
        config: 缓存配置，如果为None则使用默认配置
        
    Returns:
        CacheManagerInterface: 缓存管理器实例
    """
    if config is None:
        config = CacheConfig()
    
    try:
        # 尝试创建Redis缓存管理器
        redis_manager = RedisCacheManager(config)
        
        # 测试连接
        if redis_manager.health_check():
            return redis_manager
        else:
            # Redis不可用，使用回退缓存管理器
            redis_manager.close()
            return FallbackCacheManager()
            
    except Exception as e:
        logging.getLogger(__name__).error(f"创建Redis缓存管理器失败: {e}")
        return FallbackCacheManager()