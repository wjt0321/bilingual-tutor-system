"""
Audio Database Migration - 音频数据库迁移
Adds audio support to the existing database schema
为现有数据库架构添加音频支持
"""

import sqlite3
import os
import logging
from datetime import datetime


def migrate_audio_support(db_path: str) -> bool:
    """
    为数据库添加音频支持
    Args:
        db_path: 数据库文件路径
    Returns:
        bool: 迁移是否成功
    """
    logger = logging.getLogger(__name__)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查是否已经存在音频相关表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='audio_files'
        """)
        
        if cursor.fetchone():
            logger.info("音频表已存在，跳过迁移")
            conn.close()
            return True
        
        logger.info("开始音频数据库迁移")
        
        # 创建音频文件表
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
        
        # 为音频文件表创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_word ON audio_files(word)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_language_level ON audio_files(language, level)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_vocabulary ON audio_files(vocabulary_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_source ON audio_files(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_quality ON audio_files(quality)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_access ON audio_files(access_count)")
        
        # 为现有词汇表添加音频URL字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE vocabulary ADD COLUMN audio_url TEXT")
            logger.info("为词汇表添加音频URL字段")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.info("音频URL字段已存在")
            else:
                raise e
        
        # 创建音频下载队列表（用于批量下载管理）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_download_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                language TEXT NOT NULL,
                level TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                last_attempt DATETIME,
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(word, language, level)
            )
        """)
        
        # 为下载队列创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON audio_download_queue(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_priority ON audio_download_queue(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_language_level ON audio_download_queue(language, level)")
        
        # 创建音频使用统计表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audio_file_id INTEGER NOT NULL,
                user_id TEXT,
                usage_type TEXT DEFAULT 'play',
                usage_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (audio_file_id) REFERENCES audio_files (id) ON DELETE CASCADE
            )
        """)
        
        # 为使用统计表创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_audio ON audio_usage_stats(audio_file_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_user ON audio_usage_stats(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_date ON audio_usage_stats(usage_date)")
        
        # 提交所有更改
        conn.commit()
        
        logger.info("音频数据库迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"音频数据库迁移失败: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def rollback_audio_migration(db_path: str) -> bool:
    """
    回滚音频迁移（删除音频相关表）
    Args:
        db_path: 数据库文件路径
    Returns:
        bool: 回滚是否成功
    """
    logger = logging.getLogger(__name__)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("开始回滚音频数据库迁移")
        
        # 删除音频相关表
        cursor.execute("DROP TABLE IF EXISTS audio_usage_stats")
        cursor.execute("DROP TABLE IF EXISTS audio_download_queue")
        cursor.execute("DROP TABLE IF EXISTS audio_files")
        
        # 尝试删除词汇表的音频URL字段（SQLite不支持DROP COLUMN，需要重建表）
        try:
            # 获取词汇表结构
            cursor.execute("PRAGMA table_info(vocabulary)")
            columns = cursor.fetchall()
            
            # 过滤掉audio_url字段
            filtered_columns = [col for col in columns if col[1] != 'audio_url']
            
            if len(filtered_columns) < len(columns):
                # 需要重建表
                column_defs = []
                for col in filtered_columns:
                    col_def = f"{col[1]} {col[2]}"
                    if col[3]:  # NOT NULL
                        col_def += " NOT NULL"
                    if col[4] is not None:  # DEFAULT
                        col_def += f" DEFAULT {col[4]}"
                    if col[5]:  # PRIMARY KEY
                        col_def += " PRIMARY KEY"
                    column_defs.append(col_def)
                
                # 创建临时表
                cursor.execute(f"""
                    CREATE TABLE vocabulary_temp (
                        {', '.join(column_defs)}
                    )
                """)
                
                # 复制数据（排除audio_url字段）
                column_names = [col[1] for col in filtered_columns]
                cursor.execute(f"""
                    INSERT INTO vocabulary_temp ({', '.join(column_names)})
                    SELECT {', '.join(column_names)} FROM vocabulary
                """)
                
                # 删除原表并重命名临时表
                cursor.execute("DROP TABLE vocabulary")
                cursor.execute("ALTER TABLE vocabulary_temp RENAME TO vocabulary")
                
                logger.info("从词汇表移除音频URL字段")
        
        except Exception as e:
            logger.warning(f"移除音频URL字段失败: {e}")
        
        conn.commit()
        logger.info("音频数据库迁移回滚完成")
        return True
        
    except Exception as e:
        logger.error(f"音频数据库迁移回滚失败: {e}")
        return False
    finally:
        if conn:
            conn.close()


def check_audio_migration_status(db_path: str) -> Dict[str, bool]:
    """
    检查音频迁移状态
    Args:
        db_path: 数据库文件路径
    Returns:
        Dict: 迁移状态信息
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        status = {
            "audio_files_table": False,
            "audio_download_queue_table": False,
            "audio_usage_stats_table": False,
            "vocabulary_audio_url_column": False
        }
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('audio_files', 'audio_download_queue', 'audio_usage_stats')
        """)
        
        existing_tables = {row[0] for row in cursor.fetchall()}
        status["audio_files_table"] = "audio_files" in existing_tables
        status["audio_download_queue_table"] = "audio_download_queue" in existing_tables
        status["audio_usage_stats_table"] = "audio_usage_stats" in existing_tables
        
        # 检查词汇表的音频URL字段
        try:
            cursor.execute("SELECT audio_url FROM vocabulary LIMIT 1")
            status["vocabulary_audio_url_column"] = True
        except sqlite3.OperationalError:
            status["vocabulary_audio_url_column"] = False
        
        conn.close()
        return status
        
    except Exception as e:
        logging.error(f"检查音频迁移状态失败: {e}")
        return {}


if __name__ == "__main__":
    # 测试迁移
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python migrate_audio.py <database_path> [rollback]")
        sys.exit(1)
    
    db_path = sys.argv[1]
    rollback = len(sys.argv) > 2 and sys.argv[2] == "rollback"
    
    logging.basicConfig(level=logging.INFO)
    
    if rollback:
        success = rollback_audio_migration(db_path)
        print(f"音频迁移回滚: {'成功' if success else '失败'}")
    else:
        success = migrate_audio_support(db_path)
        print(f"音频迁移: {'成功' if success else '失败'}")
        
        if success:
            status = check_audio_migration_status(db_path)
            print("迁移状态:", status)