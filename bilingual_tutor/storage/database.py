"""
学习数据库 - 使用 SQLite 存储词汇、学习记录和内容
Learning Database - SQLite storage for vocabulary, learning records and content
"""

import sqlite3
import os
import shutil
import threading
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import logging
import time
from contextlib import contextmanager
from queue import Queue, Empty
import weakref


@dataclass
class VocabularyItem:
    """词汇条目"""
    id: int = None
    word: str = ""
    reading: str = ""  # 音标/假名
    meaning: str = ""
    example_sentence: str = ""
    example_translation: str = ""
    language: str = ""  # english/japanese
    level: str = ""  # CET-4, N5 等
    category: str = ""  # 词性
    tags: str = ""  # 标签，逗号分隔
    audio_url: str = ""  # 音频文件URL或路径


@dataclass
class LearningRecord:
    """学习记录（艾宾浩斯曲线核心）"""
    id: int = None
    user_id: str = ""
    item_id: int = 0
    item_type: str = ""  # vocabulary/grammar/content
    learn_count: int = 0
    correct_count: int = 0
    consecutive_correct: int = 0
    last_review_date: datetime = None
    next_review_date: datetime = None
    memory_strength: float = 0.0  # 0-1
    mastery_level: int = 0  # 0-5
    easiness_factor: float = 2.5  # SM-2 算法参数


@dataclass
class ContentItem:
    """学习内容条目"""
    id: int = None
    title: str = ""
    body: str = ""
    content_type: str = ""  # vocabulary/grammar/reading
    language: str = ""
    level: str = ""
    source_url: str = ""
    created_at: datetime = None


class ConnectionPool:
    """数据库连接池管理器"""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        """
        初始化连接池
        Args:
            db_path: 数据库文件路径
            max_connections: 最大连接数
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool = Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = threading.Lock()
        
        # 预创建一些连接
        for _ in range(min(3, max_connections)):
            conn = self._create_connection()
            self._pool.put_nowait(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """创建新的数据库连接"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # 优化连接设置
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB
        
        with self._lock:
            self._created_connections += 1
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            # 尝试从池中获取连接
            try:
                conn = self._pool.get_nowait()
            except Empty:
                # 池中没有可用连接，创建新连接
                with self._lock:
                    if self._created_connections < self.max_connections:
                        conn = self._create_connection()
                    else:
                        # 等待可用连接
                        conn = self._pool.get(timeout=5.0)
            
            yield conn
            
        except Exception as e:
            logging.error(f"数据库连接错误: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                try:
                    # 将连接返回池中
                    self._pool.put_nowait(conn)
                except:
                    # 池已满，关闭连接
                    conn.close()
                    with self._lock:
                        self._created_connections -= 1
    
    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break
        
        with self._lock:
            self._created_connections = 0


def _measure_query_time(query_name: str):
    """查询性能测量装饰器"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            try:
                result = func(self, *args, **kwargs)
                return result
            finally:
                end_time = time.time()
                query_time = end_time - start_time
                
                # 记录性能统计
                self._performance_stats['query_count'] += 1
                self._performance_stats['total_query_time'] += query_time
                
                # 记录慢查询（超过100ms）
                if query_time > 0.1:
                    self._performance_stats['slow_queries'].append({
                        'query': query_name,
                        'time': query_time,
                        'timestamp': datetime.now().isoformat()
                    })
                    logging.warning(f"慢查询检测: {query_name} 耗时 {query_time:.3f}s")
        
        return wrapper
    return decorator


class LearningDatabase:
    """学习数据库管理类 - 支持连接池和性能优化"""
    
    def __init__(self, db_path: str = None, max_connections: int = 10):
        """
        初始化数据库连接
        Args:
            db_path: 数据库文件路径
            max_connections: 最大连接数
        """
        if db_path is None:
            # 默认数据库路径
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "learning.db")
        
        self.db_path = db_path
        self._pool = ConnectionPool(db_path, max_connections)
        self._lock = threading.Lock()  # 线程安全锁
        self._performance_stats = {
            'query_count': 0,
            'total_query_time': 0.0,
            'slow_queries': []
        }
        
        # 初始化数据库结构和索引
        self._init_database()
        self._create_performance_indexes()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # 词汇表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    reading TEXT,
                    meaning TEXT NOT NULL,
                    example_sentence TEXT,
                    example_translation TEXT,
                    language TEXT NOT NULL,
                    level TEXT NOT NULL,
                    category TEXT,
                    tags TEXT,
                    audio_url TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(word, language, level)
                )
            """)
            
            # 语法表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grammar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    examples TEXT,
                    language TEXT NOT NULL,
                    level TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, language, level)
                )
            """)
            
            # 阅读内容表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    language TEXT NOT NULL,
                    level TEXT NOT NULL,
                    source_url TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 学习记录表（艾宾浩斯曲线核心）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    item_id INTEGER NOT NULL,
                    item_type TEXT NOT NULL,
                    learn_count INTEGER DEFAULT 0,
                    correct_count INTEGER DEFAULT 0,
                    consecutive_correct INTEGER DEFAULT 0,
                    last_review_date DATETIME,
                    next_review_date DATETIME,
                    memory_strength REAL DEFAULT 0.0,
                    mastery_level INTEGER DEFAULT 0,
                    easiness_factor REAL DEFAULT 2.5,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, item_id, item_type)
                )
            """)
            
            # 用户表（Web应用支持）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    english_level TEXT DEFAULT 'CET-4',
                    japanese_level TEXT DEFAULT 'N5',
                    daily_study_time INTEGER DEFAULT 60,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 用户偏好表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE(user_id, preference_key)
                )
            """)
            
            # 音频文件表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audio_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vocabulary_id INTEGER,
                    word TEXT NOT NULL,
                    language TEXT NOT NULL,
                    level TEXT NOT NULL,
                    file_path TEXT NOT NULL UNIQUE,
                    file_size INTEGER DEFAULT 0,
                    duration REAL,
                    source TEXT,
                    quality TEXT DEFAULT 'standard',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_accessed DATETIME,
                    access_count INTEGER DEFAULT 0,
                    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary (id) ON DELETE CASCADE,
                    UNIQUE(word, language, level, source)
                )
            """)
            
            conn.commit()
    
    def _create_performance_indexes(self):
        """创建性能优化索引 - 基于需求21的性能要求"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # 词汇表索引 - 支持复合查询
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_language_level ON vocabulary(language, level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_word ON vocabulary(word)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_created_at ON vocabulary(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_category ON vocabulary(category)")
            
            # 语法表索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_grammar_language_level ON grammar(language, level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_grammar_name ON grammar(name)")
            
            # 内容表索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_language_level ON content(language, level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_type ON content(content_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_created_at ON content(created_at)")
            
            # 学习记录表索引（性能关键 - 需求21.1, 21.5, 21.6）
            # 复习查询优化索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_user_review ON learning_records(user_id, next_review_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_user_type ON learning_records(user_id, item_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_user_mastery ON learning_records(user_id, mastery_level)")
            
            # 词汇查询复合索引（需求21.6）
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_vocab_query ON learning_records(user_id, item_type, mastery_level)")
            
            # 性能监控索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_memory_strength ON learning_records(memory_strength)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_last_review ON learning_records(last_review_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_item ON learning_records(item_id, item_type)")
            
            # 检查并添加 consecutive_correct 列（向后兼容）
            try:
                cursor.execute("SELECT consecutive_correct FROM learning_records LIMIT 1")
            except sqlite3.OperationalError:
                # 列不存在，添加它
                cursor.execute("ALTER TABLE learning_records ADD COLUMN consecutive_correct INTEGER DEFAULT 0")
                # 为现有记录计算 consecutive_correct 值
                cursor.execute("""
                    UPDATE learning_records 
                    SET consecutive_correct = CASE 
                        WHEN correct_count = learn_count THEN correct_count
                        ELSE 0
                    END
                """)
                conn.commit()
            
            # 用户表索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            
            # 用户偏好表索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_preferences_user ON user_preferences(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_preferences_key ON user_preferences(preference_key)")
            
            # 音频文件表索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_word ON audio_files(word)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_word_lang ON audio_files(word, language)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_language_level ON audio_files(language, level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_vocab_id ON audio_files(vocabulary_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_source ON audio_files(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_quality ON audio_files(quality)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_access ON audio_files(access_count)")
            
            # 分析查询优化
            cursor.execute("ANALYZE")
            
            conn.commit()
            logging.info("数据库性能索引创建完成")
    
    def backup_database(self, backup_path: str = None) -> bool:
        """
        备份数据库
        Args:
            backup_path: 备份文件路径，如果为None则使用默认路径
        Returns:
            bool: 备份是否成功
        """
        try:
            with self._lock:
                if backup_path is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
                    os.makedirs(backup_dir, exist_ok=True)
                    backup_path = os.path.join(backup_dir, f"learning_backup_{timestamp}.db")
                
                # 使用 SQLite 的 backup API
                backup_conn = sqlite3.connect(backup_path)
                with self._pool.get_connection() as conn:
                    conn.backup(backup_conn)
                backup_conn.close()
                
                logging.info(f"Database backed up to: {backup_path}")
                return True
        except Exception as e:
            logging.error(f"Database backup failed: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """
        从备份恢复数据库
        Args:
            backup_path: 备份文件路径
        Returns:
            bool: 恢复是否成功
        """
        try:
            with self._lock:
                if not os.path.exists(backup_path):
                    logging.error(f"Backup file not found: {backup_path}")
                    return False
                
                # 关闭连接池
                self._pool.close_all()
                
                # 复制备份文件到当前数据库位置
                shutil.copy2(backup_path, self.db_path)
                
                # 重新初始化连接池和数据库
                self._pool = ConnectionPool(self.db_path, self._pool.max_connections)
                self._init_database()
                self._create_performance_indexes()
                
                logging.info(f"Database restored from: {backup_path}")
                return True
        except Exception as e:
            logging.error(f"Database restore failed: {e}")
            return False
    
    def vacuum_database(self) -> bool:
        """
        清理数据库，回收空间并优化性能
        Returns:
            bool: 清理是否成功
        """
        try:
            with self._lock:
                with self._pool.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("VACUUM")
                    cursor.execute("ANALYZE")
                    conn.commit()
                    logging.info("Database vacuum completed")
                    return True
        except Exception as e:
            logging.error(f"Database vacuum failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict:
        """
        获取数据库统计信息
        Returns:
            Dict: 包含各表记录数和数据库大小的统计信息
        """
        try:
            with self._pool.get_connection() as conn:
                cursor = conn.cursor()
                stats = {}
                
                # 获取各表记录数
                tables = ['vocabulary', 'grammar', 'content', 'learning_records', 'users', 'user_preferences']
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                
                # 获取数据库文件大小
                if os.path.exists(self.db_path):
                    stats['db_size_bytes'] = os.path.getsize(self.db_path)
                    stats['db_size_mb'] = round(stats['db_size_bytes'] / (1024 * 1024), 2)
                
                # 获取页面统计
                cursor.execute("PRAGMA page_count")
                stats['page_count'] = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA page_size")
                stats['page_size'] = cursor.fetchone()[0]
                
                return stats
        except Exception as e:
            logging.error(f"Failed to get database stats: {e}")
            return {}
    
    # ==================== 词汇操作 ====================
    
    def add_vocabulary(self, item: VocabularyItem) -> int:
        """添加词汇"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO vocabulary 
                    (word, reading, meaning, example_sentence, example_translation, 
                     language, level, category, tags, audio_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (item.word, item.reading, item.meaning, item.example_sentence,
                      item.example_translation, item.language, item.level, 
                      item.category, item.tags, item.audio_url))
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                print(f"Error adding vocabulary: {e}")
                return -1
    
    def add_vocabulary_batch(self, items: List[VocabularyItem]) -> int:
        """批量添加词汇 - 优化版本使用事务"""
        if not items:
            return 0
            
        with self._lock:
            with self._pool.get_connection() as conn:
                cursor = conn.cursor()
                count = 0
                
                # 使用事务批量插入以提高性能
                try:
                    cursor.execute("BEGIN TRANSACTION")
                    
                    # 准备批量插入语句
                    insert_sql = """
                        INSERT OR REPLACE INTO vocabulary 
                        (word, reading, meaning, example_sentence, example_translation, 
                         language, level, category, tags, audio_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    # 批量执行
                    batch_data = []
                    for item in items:
                        batch_data.append((
                            item.word, item.reading, item.meaning, item.example_sentence,
                            item.example_translation, item.language, item.level, 
                            item.category, item.tags, item.audio_url
                        ))
                    
                    cursor.executemany(insert_sql, batch_data)
                    count = cursor.rowcount
                    
                    cursor.execute("COMMIT")
                    logging.info(f"Batch inserted {count} vocabulary items")
                    
                except Exception as e:
                    cursor.execute("ROLLBACK")
                    logging.error(f"Batch vocabulary insert failed: {e}")
                    count = 0
                
                return count
    
    def get_vocabulary(self, language: str, level: str, limit: int = 50, 
                      exclude_mastered: bool = False, user_id: str = None) -> List[VocabularyItem]:
        """获取词汇列表 - 优化版本支持排除已掌握词汇"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            
            if exclude_mastered and user_id:
                # 排除已掌握的词汇（掌握级别 >= 3）
                cursor.execute("""
                    SELECT v.* FROM vocabulary v
                    LEFT JOIN learning_records lr ON v.id = lr.item_id 
                        AND lr.item_type = 'vocabulary' AND lr.user_id = ?
                    WHERE v.language = ? AND v.level = ?
                        AND (lr.mastery_level IS NULL OR lr.mastery_level < 3)
                    ORDER BY RANDOM()
                    LIMIT ?
                """, (user_id, language, level, limit))
            else:
                cursor.execute("""
                    SELECT * FROM vocabulary 
                    WHERE language = ? AND level = ?
                    ORDER BY RANDOM()
                    LIMIT ?
                """, (language, level, limit))
            
            rows = cursor.fetchall()
            return [VocabularyItem(
                id=row['id'],
                word=row['word'],
                reading=row['reading'] or "",
                meaning=row['meaning'],
                example_sentence=row['example_sentence'] or "",
                example_translation=row['example_translation'] or "",
                language=row['language'],
                level=row['level'],
                category=row['category'] or "",
                tags=row['tags'] or "",
                audio_url=row['audio_url'] or ""
            ) for row in rows]
    
    def get_vocabulary_count(self, language: str = None, level: str = None) -> int:
        """获取词汇数量"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            if language and level:
                cursor.execute("SELECT COUNT(*) FROM vocabulary WHERE language = ? AND level = ?", 
                              (language, level))
            elif language:
                cursor.execute("SELECT COUNT(*) FROM vocabulary WHERE language = ?", (language,))
            else:
                cursor.execute("SELECT COUNT(*) FROM vocabulary")
            return cursor.fetchone()[0]
    
    # ==================== 语法操作 ====================
    
    def add_grammar(self, name: str, pattern: str, explanation: str, 
                   examples: List[str], language: str, level: str) -> int:
        """添加语法点"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO grammar 
                    (name, pattern, explanation, examples, language, level)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, pattern, explanation, json.dumps(examples, ensure_ascii=False), 
                      language, level))
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                print(f"Error adding grammar: {e}")
                return -1
    
    def get_grammar(self, language: str, level: str, limit: int = 20) -> List[Dict]:
        """获取语法列表"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM grammar 
                WHERE language = ? AND level = ?
                ORDER BY RANDOM()
                LIMIT ?
            """, (language, level, limit))
            
            rows = cursor.fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item['examples'] = json.loads(item['examples']) if item['examples'] else []
                result.append(item)
            return result
    
    # ==================== 内容操作 ====================
    
    def add_content(self, item: ContentItem) -> int:
        """添加学习内容"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO content 
                    (title, body, content_type, language, level, source_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (item.title, item.body, item.content_type, 
                      item.language, item.level, item.source_url))
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                print(f"Error adding content: {e}")
                return -1
    
    def get_content(self, language: str, level: str, content_type: str = None, 
                   limit: int = 10) -> List[ContentItem]:
        """获取学习内容"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            if content_type:
                cursor.execute("""
                    SELECT * FROM content 
                    WHERE language = ? AND level = ? AND content_type = ?
                    ORDER BY RANDOM()
                    LIMIT ?
                """, (language, level, content_type, limit))
            else:
                cursor.execute("""
                    SELECT * FROM content 
                    WHERE language = ? AND level = ?
                    ORDER BY RANDOM()
                    LIMIT ?
                """, (language, level, limit))
            
            rows = cursor.fetchall()
            return [ContentItem(
                id=row['id'],
                title=row['title'],
                body=row['body'],
                content_type=row['content_type'],
                language=row['language'],
                level=row['level'],
                source_url=row['source_url'] or "",
                created_at=row['created_at']
            ) for row in rows]
    
    # ==================== 学习记录操作 ====================
    
    def record_learning(self, user_id: str, item_id: int, item_type: str, 
                       correct: bool) -> LearningRecord:
        """
        记录学习结果，更新艾宾浩斯曲线参数
        使用 SM-2 算法计算下次复习时间
        """
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # 查找现有记录
            cursor.execute("""
                SELECT * FROM learning_records 
                WHERE user_id = ? AND item_id = ? AND item_type = ?
            """, (user_id, item_id, item_type))
            row = cursor.fetchone()
            
            now = datetime.now()
            
            if row:
                # 更新现有记录
                learn_count = row['learn_count'] + 1
                correct_count = row['correct_count'] + (1 if correct else 0)
                ef = row['easiness_factor']
                
                # 计算连续正确次数
                if correct:
                    consecutive_correct = (row['consecutive_correct'] if row['consecutive_correct'] is not None else 0) + 1
                else:
                    consecutive_correct = 0
                
                # SM-2 算法：计算新的 easiness factor
                quality = 5 if correct else 2  # 正确=5分，错误=2分
                ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
                ef = max(1.3, ef)  # EF 最小值为 1.3
                
                # 计算下次复习间隔
                if correct:
                    if consecutive_correct == 1:
                        interval = 1
                    elif consecutive_correct == 2:
                        interval = 6
                    else:
                        # 使用上次预定间隔 * EF (SM-2算法正确实现)
                        if row['last_review_date'] and row['next_review_date']:
                            last_date = datetime.fromisoformat(row['last_review_date'])
                            next_date = datetime.fromisoformat(row['next_review_date'])
                            previous_intended_interval = (next_date - last_date).days or 1
                            interval = int(previous_intended_interval * ef)
                            # 限制最大间隔为365天（1年）
                            interval = min(interval, 365)
                        else:
                            interval = 6
                else:
                    interval = 1  # 错误则重新开始
                
                next_review = now + timedelta(days=interval)
                memory_strength = min(1.0, correct_count / learn_count if learn_count > 0 else 0)
                mastery_level = min(5, correct_count // 2)
                
                cursor.execute("""
                    UPDATE learning_records 
                    SET learn_count = ?, correct_count = ?, consecutive_correct = ?, last_review_date = ?,
                        next_review_date = ?, memory_strength = ?, mastery_level = ?,
                        easiness_factor = ?
                    WHERE id = ?
                """, (learn_count, correct_count, consecutive_correct, now.isoformat(), next_review.isoformat(),
                      memory_strength, mastery_level, ef, row['id']))
                
                record = LearningRecord(
                    id=row['id'], user_id=user_id, item_id=item_id, item_type=item_type,
                    learn_count=learn_count, correct_count=correct_count, consecutive_correct=consecutive_correct,
                    last_review_date=now, next_review_date=next_review,
                    memory_strength=memory_strength, mastery_level=mastery_level,
                    easiness_factor=ef
                )
            else:
                # 创建新记录
                consecutive_correct = 1 if correct else 0
                next_review = now + timedelta(days=1)
                cursor.execute("""
                    INSERT INTO learning_records 
                    (user_id, item_id, item_type, learn_count, correct_count, consecutive_correct,
                     last_review_date, next_review_date, memory_strength, mastery_level)
                    VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, 0)
                """, (user_id, item_id, item_type, 1 if correct else 0, consecutive_correct,
                      now.isoformat(), next_review.isoformat(), 1.0 if correct else 0.0))
                
                record = LearningRecord(
                    id=cursor.lastrowid, user_id=user_id, item_id=item_id, item_type=item_type,
                    learn_count=1, correct_count=1 if correct else 0, consecutive_correct=consecutive_correct,
                    last_review_date=now, next_review_date=next_review,
                    memory_strength=1.0 if correct else 0.0, mastery_level=0
                )
            
            conn.commit()
            return record

    def batch_insert_learning_records(self, records: List[Dict]) -> bool:
        """批量插入学习记录（需求21.2）"""
        if not records:
            return True
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN TRANSACTION")
                # 过滤掉不存在于表中的字段（如果有的话）
                cursor.executemany("""
                    INSERT OR REPLACE INTO learning_records (user_id, item_id, item_type, 
                        learn_count, correct_count, memory_strength, mastery_level, 
                        next_review_date, last_review_date, easiness_factor)
                    VALUES (:user_id, :item_id, :item_type, :learn_count, :correct_count, 
                        :memory_strength, :mastery_level, :next_review_date, :last_review_date, 
                        :easiness_factor)
                """, records)
                cursor.execute("COMMIT")
                return True
            except Exception as e:
                cursor.execute("ROLLBACK")
                logging.error(f"Error in batch_insert_learning_records: {e}")
                return False

    def batch_update_learning_records(self, updates: List[Tuple]) -> bool:
        """批量更新学习记录（需求21.2）"""
        if not updates:
            return True
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN TRANSACTION")
                cursor.executemany("""
                    UPDATE learning_records 
                    SET learn_count = ?, correct_count = ?, memory_strength = ?, 
                        mastery_level = ?, next_review_date = ?, last_review_date = ?
                    WHERE id = ?
                """, updates)
                cursor.execute("COMMIT")
                return True
            except Exception as e:
                cursor.execute("ROLLBACK")
                logging.error(f"Error in batch_update_learning_records: {e}")
                return False

    @_measure_query_time("optimize_vocabulary_queries")
    def optimize_vocabulary_queries(self, user_id: str, language: str, mastery_levels: List[int]) -> List[Dict]:
        """优化的词汇查询（需求21.6 - 复合索引支持）"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # 使用复合索引 idx_records_vocab_query (user_id, item_type, mastery_level)
            placeholders = ', '.join(['?'] * len(mastery_levels))
            cursor.execute(f"""
                SELECT lr.*, v.word, v.meaning, v.reading
                FROM learning_records lr
                INNER JOIN vocabulary v ON lr.item_id = v.id
                WHERE lr.user_id = ? AND lr.item_type = 'vocabulary' 
                    AND v.language = ? AND lr.mastery_level IN ({placeholders})
            """, (user_id, language, *mastery_levels))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_learning_stats(self, user_id: str) -> Dict:
        """获取用户学习统计"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            stats = {
                'total_learned': 0,
                'mastery_distribution': {},
                'item_type_distribution': {}
            }
            
            cursor.execute("SELECT COUNT(*) FROM learning_records WHERE user_id = ?", (user_id,))
            stats['total_learned'] = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT mastery_level, COUNT(*) 
                FROM learning_records 
                WHERE user_id = ? 
                GROUP BY mastery_level
            """, (user_id,))
            for row in cursor.fetchall():
                stats['mastery_distribution'][str(row[0])] = row[1]
                
            cursor.execute("""
                SELECT item_type, COUNT(*) 
                FROM learning_records 
                WHERE user_id = ? 
                GROUP BY item_type
            """, (user_id,))
            for row in cursor.fetchall():
                stats['item_type_distribution'][row[0]] = row[1]
                
            return stats

    def get_performance_stats(self) -> Dict:
        """获取数据库性能统计信息（需求21.7）"""
        stats = self._performance_stats.copy()
        
        # 计算平均查询耗时
        if stats['query_count'] > 0:
            stats['avg_query_time'] = stats['total_query_time'] / stats['query_count']
        else:
            stats['avg_query_time'] = 0.0
            
        # 添加连接池状态
        stats['connection_pool_size'] = self._pool._created_connections
        stats['max_connections'] = self._pool.max_connections
        stats['slow_queries_count'] = len(stats['slow_queries'])
        
        return stats
    
    @_measure_query_time("get_due_reviews")
    def get_due_reviews(self, user_id: str, item_type: str = None, 
                       limit: int = 20) -> List[Dict]:
        """获取需要复习的内容（艾宾浩斯曲线核心）- 性能优化版本"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            if item_type:
                # 使用优化的复合索引查询（需求21.1, 21.5）
                cursor.execute("""
                    SELECT lr.*, v.word, v.meaning, v.reading
                    FROM learning_records lr
                    LEFT JOIN vocabulary v ON lr.item_id = v.id AND lr.item_type = 'vocabulary'
                    WHERE lr.user_id = ? AND lr.item_type = ? AND lr.next_review_date <= ?
                    ORDER BY lr.next_review_date ASC, lr.memory_strength ASC
                    LIMIT ?
                """, (user_id, item_type, now, limit))
            else:
                cursor.execute("""
                    SELECT lr.*, v.word, v.meaning, v.reading
                    FROM learning_records lr
                    LEFT JOIN vocabulary v ON lr.item_id = v.id AND lr.item_type = 'vocabulary'
                    WHERE lr.user_id = ? AND lr.next_review_date <= ?
                    ORDER BY lr.next_review_date ASC, lr.memory_strength ASC
                    LIMIT ?
                """, (user_id, now, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def batch_update_learning_records(self, updates: List[Tuple]) -> bool:
        """
        批量更新学习记录（需求21.2）
        Args:
            updates: 更新数据列表，每个元素为(learn_count, correct_count, memory_strength, 
                    mastery_level, next_review_date, last_review_date, record_id)
        Returns:
            bool: 更新是否成功
        """
        try:
            with self._pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany("""
                    UPDATE learning_records 
                    SET learn_count = ?, correct_count = ?, memory_strength = ?,
                        mastery_level = ?, next_review_date = ?, last_review_date = ?
                    WHERE id = ?
                """, updates)
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"批量更新学习记录失败: {e}")
            return False
    
    def batch_insert_learning_records(self, records: List[Dict]) -> bool:
        """
        批量插入学习记录（需求21.2）
        Args:
            records: 学习记录列表
        Returns:
            bool: 插入是否成功
        """
        try:
            with self._pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # 准备批量插入数据
                insert_data = []
                for record in records:
                    insert_data.append((
                        record['user_id'], record['item_id'], record['item_type'],
                        record.get('learn_count', 1), record.get('correct_count', 0),
                        record.get('consecutive_correct', 0),
                        record.get('last_review_date', datetime.now().isoformat()),
                        record.get('next_review_date', datetime.now().isoformat()),
                        record.get('memory_strength', 0.5),
                        record.get('mastery_level', 1),
                        record.get('easiness_factor', 2.5)
                    ))
                
                cursor.executemany("""
                    INSERT OR REPLACE INTO learning_records 
                    (user_id, item_id, item_type, learn_count, correct_count, 
                     consecutive_correct, last_review_date, next_review_date, 
                     memory_strength, mastery_level, easiness_factor)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, insert_data)
                
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"批量插入学习记录失败: {e}")
            return False
    
    @_measure_query_time("get_learning_stats")
    def get_learning_stats(self, user_id: str) -> Dict:
        """获取学习统计 - 性能优化版本使用更高效的查询"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # 使用单个查询获取基本统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total, 
                    SUM(learn_count) as total_reviews,
                    AVG(memory_strength) as avg_strength,
                    COUNT(CASE WHEN mastery_level >= 3 THEN 1 END) as total_mastered
                FROM learning_records 
                WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            stats = {
                'total': row['total'] or 0,
                'total_reviews': row['total_reviews'] or 0,
                'avg_strength': round(row['avg_strength'] or 0.0, 3),
                'total_mastered': row['total_mastered'] or 0
            }
            
            # 按类型统计 - 使用优化的GROUP BY查询
            cursor.execute("""
                SELECT 
                    item_type,
                    COUNT(*) as count,
                    COUNT(CASE WHEN mastery_level >= 3 THEN 1 END) as mastered,
                    AVG(memory_strength) as avg_strength
                FROM learning_records 
                WHERE user_id = ?
                GROUP BY item_type
            """, (user_id,))
            
            type_stats = {}
            for row in cursor.fetchall():
                type_stats[row['item_type']] = {
                    'total': row['count'],
                    'mastered': row['mastered'],
                    'avg_strength': round(row['avg_strength'] or 0.0, 3)
                }
            stats['by_type'] = type_stats
            
            # 待复习数 - 使用索引优化的查询（需求21.5）
            now = datetime.now().isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM learning_records 
                WHERE user_id = ? AND next_review_date <= ?
            """, (user_id, now))
            stats['due_reviews'] = cursor.fetchone()[0]
            
            # 最近7天的学习活动
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM learning_records 
                WHERE user_id = ? AND last_review_date >= ?
            """, (user_id, week_ago))
            stats['recent_activity'] = cursor.fetchone()[0]
            
            return stats
    
    def get_performance_stats(self) -> Dict:
        """
        获取数据库性能统计信息（需求21.7）
        Returns:
            Dict: 性能统计数据
        """
        avg_query_time = 0.0
        if self._performance_stats['query_count'] > 0:
            avg_query_time = self._performance_stats['total_query_time'] / self._performance_stats['query_count']
        
        return {
            'query_count': self._performance_stats['query_count'],
            'total_query_time': round(self._performance_stats['total_query_time'], 3),
            'avg_query_time': round(avg_query_time, 3),
            'slow_queries_count': len(self._performance_stats['slow_queries']),
            'slow_queries': self._performance_stats['slow_queries'][-10:],  # 最近10个慢查询
            'connection_pool_size': self._pool._created_connections,
            'max_connections': self._pool.max_connections
        }
    
    def optimize_vocabulary_queries(self, user_id: str, language: str, mastery_levels: List[int]) -> List[Dict]:
        """
        优化的词汇查询（需求21.6 - 复合索引支持）
        Args:
            user_id: 用户ID
            language: 语言
            mastery_levels: 掌握程度列表
        Returns:
            List[Dict]: 词汇记录列表
        """
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # 使用复合索引优化查询
            placeholders = ','.join('?' * len(mastery_levels))
            query = f"""
                SELECT lr.*, v.word, v.meaning, v.reading, v.level
                FROM learning_records lr
                JOIN vocabulary v ON lr.item_id = v.id AND lr.item_type = 'vocabulary'
                WHERE lr.user_id = ? AND v.language = ? AND lr.mastery_level IN ({placeholders})
                ORDER BY lr.memory_strength ASC, lr.last_review_date ASC
            """
            
            params = [user_id, language] + mastery_levels
            cursor.execute(query, params)
            
            return [dict(row) for row in cursor.fetchall()]
    
    @_measure_query_time("optimized_review_query")
    def execute_optimized_review_query(self, user_id: str, max_items: int = 50) -> List[Dict]:
        """
        执行优化的复习查询（需求21.1 - 50%性能提升目标）
        使用预编译查询和批量处理
        """
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # 使用优化的查询计划
            # 简化排序逻辑以强制使用 (user_id, next_review_date) 索引
            cursor.execute("""
                SELECT lr.id, lr.user_id, lr.item_id, lr.item_type, lr.memory_strength, 
                       lr.mastery_level, lr.next_review_date,
                       v.word, v.meaning, v.reading, v.level
                FROM learning_records lr
                LEFT JOIN vocabulary v ON lr.item_id = v.id AND lr.item_type = 'vocabulary'
                WHERE lr.user_id = ? AND lr.next_review_date <= ?
                ORDER BY lr.next_review_date ASC
                LIMIT ?
            """, (user_id, now, max_items))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """关闭数据库连接池"""
        if hasattr(self, '_pool'):
            self._pool.close_all()
            logging.info("数据库连接池已关闭")
    
    def __enter__(self):
        """上下文管理器支持"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器支持"""
        self.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        执行自定义查询（用于复杂查询优化）
        Args:
            query: SQL查询语句
            params: 查询参数
        Returns:
            List[Dict]: 查询结果
        """
        try:
            with self._lock:
                with self._pool.get_connection() as conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Query execution failed: {e}")
            return []
    
    def get_user_learning_summary(self, user_id: str, days: int = 30) -> Dict:
        """
        获取用户学习总结（优化的复合查询）
        Args:
            user_id: 用户ID
            days: 统计天数
        Returns:
            Dict: 学习总结数据
        """
        try:
            with self._pool.get_connection() as conn:
                cursor = conn.cursor()
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                # 使用CTE（公共表表达式）优化复杂查询
                query = """
                WITH recent_activity AS (
                    SELECT 
                        item_type,
                        COUNT(*) as activities,
                        AVG(CASE WHEN correct_count > 0 THEN 
                            CAST(correct_count AS REAL) / learn_count ELSE 0 END) as accuracy,
                        COUNT(CASE WHEN mastery_level >= 3 THEN 1 END) as mastered_items
                    FROM learning_records 
                    WHERE user_id = ? AND last_review_date >= ?
                    GROUP BY item_type
                ),
                overall_stats AS (
                    SELECT 
                        COUNT(*) as total_items,
                        AVG(memory_strength) as avg_memory_strength,
                        COUNT(CASE WHEN next_review_date <= datetime('now') THEN 1 END) as due_reviews
                    FROM learning_records 
                    WHERE user_id = ?
                )
                SELECT 
                    ra.item_type,
                    ra.activities,
                    ra.accuracy,
                    ra.mastered_items,
                    os.total_items,
                    os.avg_memory_strength,
                    os.due_reviews
                FROM recent_activity ra
                CROSS JOIN overall_stats os
                UNION ALL
                SELECT 
                    'overall' as item_type,
                    0 as activities,
                    0 as accuracy,
                    0 as mastered_items,
                    os.total_items,
                    os.avg_memory_strength,
                    os.due_reviews
                FROM overall_stats os
                """
                
                cursor.execute(query, (user_id, cutoff_date, user_id))
                results = cursor.fetchall()
                
                summary = {
                    'period_days': days,
                    'by_type': {},
                    'overall': {}
                }
                
                for row in results:
                    if row['item_type'] == 'overall':
                        summary['overall'] = {
                            'total_items': row['total_items'],
                            'avg_memory_strength': round(row['avg_memory_strength'] or 0.0, 3),
                            'due_reviews': row['due_reviews']
                        }
                    else:
                        summary['by_type'][row['item_type']] = {
                            'recent_activities': row['activities'],
                            'accuracy': round(row['accuracy'] or 0.0, 3),
                            'mastered_items': row['mastered_items']
                        }
                
                return summary
            
        except Exception as e:
            logging.error(f"Failed to get user learning summary: {e}")
            return {}
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """获取用户档案信息"""
        try:
            with self._pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, english_level, japanese_level, daily_study_time,
                           created_at, updated_at
                    FROM users 
                    WHERE username = ? OR id = ?
                """, (user_id, user_id))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'user_id': user_id,
                        'username': row['username'],
                        'english_level': row['english_level'],
                        'japanese_level': row['japanese_level'],
                        'daily_study_time': row['daily_study_time'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    }
                return None
            
        except Exception as e:
            logging.error(f"Failed to get user profile: {e}")
            return None
    
    def get_latest_learning_record(self, user_id: str, item_id: int, item_type: str) -> Optional[LearningRecord]:
        """获取最新的学习记录"""
        try:
            with self._pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM learning_records 
                    WHERE user_id = ? AND item_id = ? AND item_type = ?
                    ORDER BY last_review_date DESC
                    LIMIT 1
                """, (user_id, item_id, item_type))
                
                row = cursor.fetchone()
                if row:
                    return LearningRecord(
                        id=row['id'],
                        user_id=row['user_id'],
                        item_id=row['item_id'],
                        item_type=row['item_type'],
                        learn_count=row['learn_count'],
                        correct_count=row['correct_count'],
                        consecutive_correct=row['consecutive_correct'],
                        last_review_date=datetime.fromisoformat(row['last_review_date']) if row['last_review_date'] else None,
                        next_review_date=datetime.fromisoformat(row['next_review_date']) if row['next_review_date'] else None,
                        memory_strength=row['memory_strength'],
                        mastery_level=row['mastery_level'],
                        easiness_factor=row['easiness_factor']
                    )
                return None
            
        except Exception as e:
            logging.error(f"Failed to get latest learning record: {e}")
            return None
    
    # ==================== 音频文件操作 ====================
    
    def add_audio_file(self, word: str, language: str, level: str, file_path: str,
                      file_size: int = 0, duration: float = None, source: str = "",
                      quality: str = "standard", vocabulary_id: int = None) -> int:
        """
        添加音频文件记录
        Args:
            word: 单词
            language: 语言
            level: 级别
            file_path: 文件路径
            file_size: 文件大小
            duration: 音频时长
            source: 来源
            quality: 质量
            vocabulary_id: 关联的词汇ID
        Returns:
            int: 音频文件ID，失败返回-1
        """
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO audio_files 
                    (vocabulary_id, word, language, level, file_path, file_size, 
                     duration, source, quality)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (vocabulary_id, word, language, level, file_path, file_size,
                      duration, source, quality))
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                logging.error(f"Error adding audio file: {e}")
                return -1
    
    def get_audio_file(self, word: str, language: str, level: str = None) -> Optional[Dict]:
        """
        获取音频文件信息
        Args:
            word: 单词
            language: 语言
            level: 级别（可选）
        Returns:
            Dict: 音频文件信息，未找到返回None
        """
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if level:
                    cursor.execute("""
                        SELECT * FROM audio_files 
                        WHERE word = ? AND language = ? AND level = ?
                        ORDER BY quality DESC, access_count DESC
                        LIMIT 1
                    """, (word, language, level))
                else:
                    cursor.execute("""
                        SELECT * FROM audio_files 
                        WHERE word = ? AND language = ?
                        ORDER BY quality DESC, access_count DESC
                        LIMIT 1
                    """, (word, language))
                
                row = cursor.fetchone()
                if row:
                    # 更新访问统计
                    self._update_audio_access_stats(row['id'])
                    return dict(row)
                return None
                
            except Exception as e:
                logging.error(f"Error getting audio file: {e}")
                return None
    
    def update_vocabulary_audio_url(self, vocabulary_id: int, audio_url: str) -> bool:
        """
        更新词汇的音频URL
        Args:
            vocabulary_id: 词汇ID
            audio_url: 音频URL或路径
        Returns:
            bool: 更新是否成功
        """
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE vocabulary SET audio_url = ? WHERE id = ?
                """, (audio_url, vocabulary_id))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                logging.error(f"Error updating vocabulary audio URL: {e}")
                return False
    
    def get_vocabulary_with_audio(self, language: str, level: str, limit: int = 50) -> List[Dict]:
        """
        获取带音频的词汇列表
        Args:
            language: 语言
            level: 级别
            limit: 数量限制
        Returns:
            List[Dict]: 词汇和音频信息列表
        """
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT v.*, af.file_path as audio_file_path, af.duration, af.quality
                    FROM vocabulary v
                    LEFT JOIN audio_files af ON v.id = af.vocabulary_id
                    WHERE v.language = ? AND v.level = ?
                    ORDER BY v.word
                    LIMIT ?
                """, (language, level, limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
            except Exception as e:
                logging.error(f"Error getting vocabulary with audio: {e}")
                return []
    
    def get_audio_statistics(self) -> Dict[str, any]:
        """
        获取音频文件统计信息
        Returns:
            Dict: 音频统计信息
        """
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                stats = {
                    "total_files": 0,
                    "total_size": 0,
                    "by_language": {},
                    "by_level": {},
                    "by_quality": {}
                }
                
                # 总体统计
                cursor.execute("SELECT COUNT(*), SUM(file_size) FROM audio_files")
                row = cursor.fetchone()
                stats["total_files"] = row[0] or 0
                stats["total_size"] = row[1] or 0
                
                # 按语言统计
                cursor.execute("""
                    SELECT language, COUNT(*), SUM(file_size) 
                    FROM audio_files 
                    GROUP BY language
                """)
                for row in cursor.fetchall():
                    stats["by_language"][row[0]] = {
                        "count": row[1],
                        "size": row[2] or 0
                    }
                
                # 按级别统计
                cursor.execute("""
                    SELECT level, COUNT(*), SUM(file_size) 
                    FROM audio_files 
                    GROUP BY level
                """)
                for row in cursor.fetchall():
                    stats["by_level"][row[0]] = {
                        "count": row[1],
                        "size": row[2] or 0
                    }
                
                # 按质量统计
                cursor.execute("""
                    SELECT quality, COUNT(*), SUM(file_size) 
                    FROM audio_files 
                    GROUP BY quality
                """)
                for row in cursor.fetchall():
                    stats["by_quality"][row[0]] = {
                        "count": row[1],
                        "size": row[2] or 0
                    }
                
                return stats
                
            except Exception as e:
                logging.error(f"Error getting audio statistics: {e}")
                return {}
    
    def _update_audio_access_stats(self, audio_id: int):
        """
        更新音频访问统计
        Args:
            audio_id: 音频文件ID
        """
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE audio_files 
                    SET last_accessed = ?, access_count = access_count + 1
                    WHERE id = ?
                """, (datetime.now().isoformat(), audio_id))
                conn.commit()
            except Exception as e:
                logging.error(f"Error updating audio access stats: {e}")
    
    def cleanup_missing_audio_files(self) -> int:
        """
        清理数据库中指向不存在文件的音频记录
        Returns:
            int: 清理的记录数量
        """
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            cleaned_count = 0
            
            try:
                # 获取所有音频文件记录
                cursor.execute("SELECT id, file_path FROM audio_files")
                audio_records = cursor.fetchall()
                
                for record in audio_records:
                    audio_id, file_path = record
                    if not os.path.exists(file_path):
                        # 文件不存在，删除记录
                        cursor.execute("DELETE FROM audio_files WHERE id = ?", (audio_id,))
                        cleaned_count += 1
                        logging.info(f"清理缺失音频文件记录: {file_path}")
                
                conn.commit()
                return cleaned_count
                
            except Exception as e:
                logging.error(f"清理缺失音频文件失败: {e}")
                return 0