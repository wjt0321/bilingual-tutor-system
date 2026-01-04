#!/usr/bin/env python3
"""
数据库迁移脚本 - 应用性能优化
Database migration script - Apply performance optimizations
"""

import sqlite3
import os
import logging
from datetime import datetime


def migrate_database(db_path: str = None):
    """
    迁移现有数据库以应用性能优化
    Migrate existing database to apply performance optimizations
    """
    if db_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "learning.db")
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        print(f"开始迁移数据库: {db_path}")
        
        # 备份原数据库
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"已备份原数据库到: {backup_path}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 启用性能优化设置
        print("应用性能优化设置...")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # 添加新表（如果不存在）
        print("添加新表结构...")
        
        # 用户表
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
        
        # 创建所有优化索引
        print("创建性能优化索引...")
        
        indexes = [
            # 词汇表索引
            "CREATE INDEX IF NOT EXISTS idx_vocab_language_level ON vocabulary(language, level)",
            "CREATE INDEX IF NOT EXISTS idx_vocab_word ON vocabulary(word)",
            "CREATE INDEX IF NOT EXISTS idx_vocab_created_at ON vocabulary(created_at)",
            
            # 语法表索引
            "CREATE INDEX IF NOT EXISTS idx_grammar_language_level ON grammar(language, level)",
            "CREATE INDEX IF NOT EXISTS idx_grammar_name ON grammar(name)",
            
            # 内容表索引
            "CREATE INDEX IF NOT EXISTS idx_content_language_level ON content(language, level)",
            "CREATE INDEX IF NOT EXISTS idx_content_type ON content(content_type)",
            "CREATE INDEX IF NOT EXISTS idx_content_created_at ON content(created_at)",
            
            # 学习记录表索引（性能关键）
            "CREATE INDEX IF NOT EXISTS idx_records_user ON learning_records(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_records_next_review ON learning_records(next_review_date)",
            "CREATE INDEX IF NOT EXISTS idx_records_user_type ON learning_records(user_id, item_type)",
            "CREATE INDEX IF NOT EXISTS idx_records_item ON learning_records(item_id, item_type)",
            "CREATE INDEX IF NOT EXISTS idx_records_mastery ON learning_records(mastery_level)",
            "CREATE INDEX IF NOT EXISTS idx_records_memory_strength ON learning_records(memory_strength)",
            
            # 用户表索引
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            
            # 用户偏好表索引
            "CREATE INDEX IF NOT EXISTS idx_preferences_user ON user_preferences(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_preferences_key ON user_preferences(preference_key)",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
            print(f"  创建索引: {index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else '未知'}")
        
        # 更新统计信息
        print("更新数据库统计信息...")
        cursor.execute("ANALYZE")
        
        # 清理数据库
        print("清理数据库...")
        cursor.execute("VACUUM")
        
        conn.commit()
        conn.close()
        
        print("✅ 数据库迁移完成！")
        print(f"原数据库已备份到: {backup_path}")
        return True
        
    except Exception as e:
        print(f"❌ 数据库迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    migrate_database()