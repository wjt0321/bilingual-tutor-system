"""
Audio Storage - 音频存储管理
Manages audio file storage, indexing, and retrieval
管理音频文件存储、索引和检索
"""

import os
import json
import sqlite3
import hashlib
import shutil
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import logging


@dataclass
class AudioRecord:
    """音频记录"""
    id: int = None
    word: str = ""
    language: str = ""  # english/japanese
    level: str = ""  # CET-4, N5, etc.
    file_path: str = ""
    file_size: int = 0
    duration: Optional[float] = None
    source: str = ""  # 来源网站
    quality: str = "standard"  # standard, high, low
    created_at: str = None
    last_accessed: str = None
    access_count: int = 0


class AudioStorage:
    """
    音频存储管理器
    Audio Storage Manager - Handles audio file storage and indexing
    """
    
    def __init__(self, storage_path: str = None, db_path: str = None):
        """
        初始化音频存储管理器
        Args:
            storage_path: 音频文件存储路径
            db_path: 音频索引数据库路径
        """
        if storage_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_path = os.path.join(base_dir, "..", "data", "audio")
        
        if db_path is None:
            db_path = os.path.join(storage_path, "audio_index.db")
        
        self.storage_path = storage_path
        self.db_path = db_path
        
        # 确保目录存在
        os.makedirs(self.storage_path, exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "english"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "japanese"), exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self):
        """初始化音频索引数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建音频记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                UNIQUE(word, language, level, source)
            )
        """)
        
        # 创建索引以提高查询性能
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_word ON audio_records(word)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_language_level ON audio_records(language, level)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_source ON audio_records(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_quality ON audio_records(quality)")
        
        conn.commit()
        conn.close()
    
    def store_audio_file(self, word: str, language: str, level: str, 
                        source_path: str, source: str = "", quality: str = "standard") -> Optional[AudioRecord]:
        """
        存储音频文件到管理系统
        Args:
            word: 单词
            language: 语言 (english/japanese)
            level: 级别 (CET-4, N5, etc.)
            source_path: 源文件路径
            source: 来源网站
            quality: 音频质量
        Returns:
            AudioRecord: 音频记录，失败返回None
        """
        try:
            # 验证源文件存在
            if not os.path.exists(source_path):
                self.logger.error(f"源音频文件不存在: {source_path}")
                return None
            
            # 生成目标文件路径
            target_path = self._generate_storage_path(word, language, level, source)
            
            # 确保目标目录存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # 复制文件到存储位置
            if source_path != target_path:
                shutil.copy2(source_path, target_path)
            
            # 获取文件信息
            file_size = os.path.getsize(target_path)
            duration = self._get_audio_duration(target_path)
            
            # 保存到数据库
            record = AudioRecord(
                word=word,
                language=language,
                level=level,
                file_path=target_path,
                file_size=file_size,
                duration=duration,
                source=source,
                quality=quality,
                created_at=datetime.now().isoformat()
            )
            
            record_id = self._save_audio_record(record)
            if record_id:
                record.id = record_id
                self.logger.info(f"音频文件存储成功: {word} ({language}, {level})")
                return record
            else:
                # 如果数据库保存失败，删除文件
                if os.path.exists(target_path):
                    os.remove(target_path)
                return None
                
        except Exception as e:
            self.logger.error(f"存储音频文件失败: {e}")
            return None
    
    def get_audio_file(self, word: str, language: str, level: str = None) -> Optional[AudioRecord]:
        """
        获取音频文件记录
        Args:
            word: 单词
            language: 语言
            level: 级别（可选）
        Returns:
            AudioRecord: 音频记录，未找到返回None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if level:
                cursor.execute("""
                    SELECT * FROM audio_records 
                    WHERE word = ? AND language = ? AND level = ?
                    ORDER BY quality DESC, access_count DESC
                    LIMIT 1
                """, (word, language, level))
            else:
                cursor.execute("""
                    SELECT * FROM audio_records 
                    WHERE word = ? AND language = ?
                    ORDER BY quality DESC, access_count DESC
                    LIMIT 1
                """, (word, language))
            
            row = cursor.fetchone()
            if row:
                # 更新访问统计
                self._update_access_stats(row['id'])
                
                return AudioRecord(
                    id=row['id'],
                    word=row['word'],
                    language=row['language'],
                    level=row['level'],
                    file_path=row['file_path'],
                    file_size=row['file_size'],
                    duration=row['duration'],
                    source=row['source'],
                    quality=row['quality'],
                    created_at=row['created_at'],
                    last_accessed=row['last_accessed'],
                    access_count=row['access_count']
                )
            return None
            
        except Exception as e:
            self.logger.error(f"获取音频文件失败: {e}")
            return None
        finally:
            conn.close()
    
    def search_audio_files(self, language: str = None, level: str = None, 
                          source: str = None, limit: int = 100) -> List[AudioRecord]:
        """
        搜索音频文件
        Args:
            language: 语言过滤
            level: 级别过滤
            source: 来源过滤
            limit: 结果数量限制
        Returns:
            List[AudioRecord]: 音频记录列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 构建查询条件
            conditions = []
            params = []
            
            if language:
                conditions.append("language = ?")
                params.append(language)
            
            if level:
                conditions.append("level = ?")
                params.append(level)
            
            if source:
                conditions.append("source = ?")
                params.append(source)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor.execute(f"""
                SELECT * FROM audio_records 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """, params + [limit])
            
            records = []
            for row in cursor.fetchall():
                records.append(AudioRecord(
                    id=row['id'],
                    word=row['word'],
                    language=row['language'],
                    level=row['level'],
                    file_path=row['file_path'],
                    file_size=row['file_size'],
                    duration=row['duration'],
                    source=row['source'],
                    quality=row['quality'],
                    created_at=row['created_at'],
                    last_accessed=row['last_accessed'],
                    access_count=row['access_count']
                ))
            
            return records
            
        except Exception as e:
            self.logger.error(f"搜索音频文件失败: {e}")
            return []
        finally:
            conn.close()
    
    def delete_audio_file(self, record_id: int) -> bool:
        """
        删除音频文件
        Args:
            record_id: 音频记录ID
        Returns:
            bool: 删除是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取文件路径
            cursor.execute("SELECT file_path FROM audio_records WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            
            if not row:
                self.logger.warning(f"音频记录不存在: {record_id}")
                return False
            
            file_path = row[0]
            
            # 删除文件
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"删除音频文件: {file_path}")
            
            # 删除数据库记录
            cursor.execute("DELETE FROM audio_records WHERE id = ?", (record_id,))
            conn.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"删除音频文件失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_storage_statistics(self) -> Dict[str, any]:
        """
        获取存储统计信息
        Returns:
            Dict: 存储统计信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {
                "total_files": 0,
                "total_size": 0,
                "by_language": {},
                "by_level": {},
                "by_source": {},
                "by_quality": {}
            }
            
            # 总体统计
            cursor.execute("SELECT COUNT(*), SUM(file_size) FROM audio_records")
            row = cursor.fetchone()
            stats["total_files"] = row[0] or 0
            stats["total_size"] = row[1] or 0
            
            # 按语言统计
            cursor.execute("""
                SELECT language, COUNT(*), SUM(file_size) 
                FROM audio_records 
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
                FROM audio_records 
                GROUP BY level
            """)
            for row in cursor.fetchall():
                stats["by_level"][row[0]] = {
                    "count": row[1],
                    "size": row[2] or 0
                }
            
            # 按来源统计
            cursor.execute("""
                SELECT source, COUNT(*), SUM(file_size) 
                FROM audio_records 
                GROUP BY source
            """)
            for row in cursor.fetchall():
                stats["by_source"][row[0]] = {
                    "count": row[1],
                    "size": row[2] or 0
                }
            
            # 按质量统计
            cursor.execute("""
                SELECT quality, COUNT(*), SUM(file_size) 
                FROM audio_records 
                GROUP BY quality
            """)
            for row in cursor.fetchall():
                stats["by_quality"][row[0]] = {
                    "count": row[1],
                    "size": row[2] or 0
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取存储统计失败: {e}")
            return {}
        finally:
            conn.close()
    
    def cleanup_orphaned_files(self) -> int:
        """
        清理孤立的音频文件（数据库中没有记录的文件）
        Returns:
            int: 清理的文件数量
        """
        cleaned_count = 0
        
        try:
            # 获取数据库中所有文件路径
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM audio_records")
            db_files = {row[0] for row in cursor.fetchall()}
            conn.close()
            
            # 扫描存储目录中的所有音频文件
            for root, dirs, files in os.walk(self.storage_path):
                for file in files:
                    if file.endswith(('.mp3', '.wav', '.m4a', '.ogg')):
                        file_path = os.path.join(root, file)
                        
                        # 如果文件不在数据库中，删除它
                        if file_path not in db_files:
                            try:
                                os.remove(file_path)
                                cleaned_count += 1
                                self.logger.info(f"清理孤立文件: {file_path}")
                            except Exception as e:
                                self.logger.error(f"清理文件失败: {file_path}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"清理孤立文件失败: {e}")
            return 0
    
    def _generate_storage_path(self, word: str, language: str, level: str, source: str) -> str:
        """
        生成存储路径
        Args:
            word: 单词
            language: 语言
            level: 级别
            source: 来源
        Returns:
            str: 存储路径
        """
        # 清理文件名
        clean_word = "".join(c for c in word if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_word = clean_word.replace(' ', '_').lower()
        clean_source = "".join(c for c in source if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_source = clean_source.replace(' ', '_').lower()
        
        # 生成文件名
        if clean_source:
            filename = f"{clean_source}_{clean_word}.mp3"
        else:
            filename = f"{clean_word}.mp3"
        
        return os.path.join(self.storage_path, language, level, filename)
    
    def _save_audio_record(self, record: AudioRecord) -> Optional[int]:
        """
        保存音频记录到数据库
        Args:
            record: 音频记录
        Returns:
            int: 记录ID，失败返回None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO audio_records 
                (word, language, level, file_path, file_size, duration, source, quality, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.word, record.language, record.level, record.file_path,
                record.file_size, record.duration, record.source, record.quality,
                record.created_at
            ))
            
            conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            self.logger.error(f"保存音频记录失败: {e}")
            return None
        finally:
            conn.close()
    
    def _update_access_stats(self, record_id: int):
        """
        更新访问统计
        Args:
            record_id: 记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE audio_records 
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
            """, (datetime.now().isoformat(), record_id))
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"更新访问统计失败: {e}")
        finally:
            conn.close()
    
    def _get_audio_duration(self, file_path: str) -> Optional[float]:
        """
        获取音频文件时长（简化实现）
        Args:
            file_path: 音频文件路径
        Returns:
            float: 时长（秒），获取失败返回None
        """
        try:
            # 这里可以使用 mutagen 或其他音频库来获取准确的时长
            # 目前返回基于文件大小的估算值
            file_size = os.path.getsize(file_path)
            # 假设 MP3 128kbps，估算时长
            estimated_duration = file_size / (128 * 1024 / 8)  # 秒
            return round(estimated_duration, 2)
        except:
            return None