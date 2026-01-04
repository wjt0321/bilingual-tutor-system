"""
Pronunciation Manager - 发音管理器
High-level interface for managing pronunciation audio files
管理发音音频文件的高级接口
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from .audio_crawler import AudioCrawler, AudioFile
from .audio_storage import AudioStorage, AudioRecord


class PronunciationManager:
    """
    发音管理器 - 统一管理音频爬取和存储
    Pronunciation Manager - Unified management of audio crawling and storage
    """
    
    def __init__(self, storage_path: str = None):
        """
        初始化发音管理器
        Args:
            storage_path: 音频存储路径
        """
        if storage_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_path = os.path.join(base_dir, "..", "data", "audio")
        
        self.storage_path = storage_path
        self.crawler = AudioCrawler(storage_path)
        self.storage = AudioStorage(storage_path)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
    
    def crawl_and_store_english_pronunciation(self, words: List[str], 
                                            levels: List[str] = None) -> Dict[str, any]:
        """
        爬取并存储英语发音音频 (CET-4到CET-6)
        Args:
            words: 要爬取的单词列表
            levels: 目标级别列表
        Returns:
            Dict: 爬取结果统计
        """
        if levels is None:
            levels = ["CET-4", "CET-5", "CET-6"]
        
        self.logger.info(f"开始爬取并存储英语发音，单词数量: {len(words)}")
        
        # 爬取音频文件
        audio_files = self.crawler.crawl_english_pronunciation(words, levels)
        
        # 存储到管理系统
        stored_count = 0
        failed_count = 0
        
        for audio_file in audio_files:
            try:
                record = self.storage.store_audio_file(
                    word=audio_file.word,
                    language=audio_file.language,
                    level=audio_file.level,
                    source_path=audio_file.local_path,
                    source="crawler",
                    quality=audio_file.quality
                )
                
                if record:
                    stored_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                self.logger.error(f"存储音频文件失败: {audio_file.word}: {e}")
                failed_count += 1
        
        result = {
            "language": "english",
            "levels": levels,
            "total_words": len(words),
            "crawled_files": len(audio_files),
            "stored_files": stored_count,
            "failed_files": failed_count,
            "success_rate": round(stored_count / len(words) * 100, 2) if words else 0
        }
        
        self.logger.info(f"英语发音爬取完成: {result}")
        return result
    
    def crawl_and_store_japanese_pronunciation(self, words: List[str], 
                                             levels: List[str] = None) -> Dict[str, any]:
        """
        爬取并存储日语发音音频 (N5到N1)
        Args:
            words: 要爬取的单词列表
            levels: 目标级别列表
        Returns:
            Dict: 爬取结果统计
        """
        if levels is None:
            levels = ["N5", "N4", "N3", "N2", "N1"]
        
        self.logger.info(f"开始爬取并存储日语发音，单词数量: {len(words)}")
        
        # 爬取音频文件
        audio_files = self.crawler.crawl_japanese_pronunciation(words, levels)
        
        # 存储到管理系统
        stored_count = 0
        failed_count = 0
        
        for audio_file in audio_files:
            try:
                record = self.storage.store_audio_file(
                    word=audio_file.word,
                    language=audio_file.language,
                    level=audio_file.level,
                    source_path=audio_file.local_path,
                    source="crawler",
                    quality=audio_file.quality
                )
                
                if record:
                    stored_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                self.logger.error(f"存储音频文件失败: {audio_file.word}: {e}")
                failed_count += 1
        
        result = {
            "language": "japanese",
            "levels": levels,
            "total_words": len(words),
            "crawled_files": len(audio_files),
            "stored_files": stored_count,
            "failed_files": failed_count,
            "success_rate": round(stored_count / len(words) * 100, 2) if words else 0
        }
        
        self.logger.info(f"日语发音爬取完成: {result}")
        return result
    
    def get_pronunciation_audio(self, word: str, language: str, level: str = None) -> Optional[str]:
        """
        获取单词的发音音频文件路径
        Args:
            word: 单词
            language: 语言 (english/japanese)
            level: 级别（可选）
        Returns:
            str: 音频文件路径，未找到返回None
        """
        record = self.storage.get_audio_file(word, language, level)
        if record and os.path.exists(record.file_path):
            return record.file_path
        return None
    
    def batch_crawl_vocabulary_pronunciation(self, vocabulary_items: List[Dict[str, str]]) -> Dict[str, any]:
        """
        批量爬取词汇发音
        Args:
            vocabulary_items: 词汇项目列表，每项包含 word, language, level
        Returns:
            Dict: 批量爬取结果统计
        """
        self.logger.info(f"开始批量爬取词汇发音，词汇数量: {len(vocabulary_items)}")
        
        # 按语言分组
        english_words = {}
        japanese_words = {}
        
        for item in vocabulary_items:
            word = item.get('word', '').strip()
            language = item.get('language', '').lower()
            level = item.get('level', '')
            
            if not word or not language:
                continue
            
            if language == 'english':
                if level not in english_words:
                    english_words[level] = []
                english_words[level].append(word)
            elif language == 'japanese':
                if level not in japanese_words:
                    japanese_words[level] = []
                japanese_words[level].append(word)
        
        results = {
            "total_items": len(vocabulary_items),
            "english_results": {},
            "japanese_results": {},
            "overall_success_rate": 0
        }
        
        total_stored = 0
        total_attempted = 0
        
        # 爬取英语发音
        for level, words in english_words.items():
            if words:
                result = self.crawl_and_store_english_pronunciation(words, [level])
                results["english_results"][level] = result
                total_stored += result["stored_files"]
                total_attempted += result["total_words"]
        
        # 爬取日语发音
        for level, words in japanese_words.items():
            if words:
                result = self.crawl_and_store_japanese_pronunciation(words, [level])
                results["japanese_results"][level] = result
                total_stored += result["stored_files"]
                total_attempted += result["total_words"]
        
        # 计算总体成功率
        if total_attempted > 0:
            results["overall_success_rate"] = round(total_stored / total_attempted * 100, 2)
        
        self.logger.info(f"批量爬取完成，总成功率: {results['overall_success_rate']}%")
        return results
    
    def get_pronunciation_statistics(self) -> Dict[str, any]:
        """
        获取发音音频统计信息
        Returns:
            Dict: 统计信息
        """
        # 获取存储统计
        storage_stats = self.storage.get_storage_statistics()
        
        # 获取爬虫统计
        crawler_stats = self.crawler.get_crawl_statistics()
        
        # 合并统计信息
        combined_stats = {
            "storage": storage_stats,
            "crawler": crawler_stats,
            "summary": {
                "total_stored_files": storage_stats.get("total_files", 0),
                "total_storage_size": storage_stats.get("total_size", 0),
                "storage_size_mb": round(storage_stats.get("total_size", 0) / (1024 * 1024), 2),
                "english_files": storage_stats.get("by_language", {}).get("english", {}).get("count", 0),
                "japanese_files": storage_stats.get("by_language", {}).get("japanese", {}).get("count", 0)
            }
        }
        
        return combined_stats
    
    def cleanup_audio_files(self) -> Dict[str, int]:
        """
        清理音频文件（无效文件和孤立文件）
        Returns:
            Dict: 清理结果统计
        """
        self.logger.info("开始清理音频文件")
        
        # 清理爬虫的无效文件
        invalid_cleaned = self.crawler.cleanup_invalid_files()
        
        # 清理存储的孤立文件
        orphaned_cleaned = self.storage.cleanup_orphaned_files()
        
        result = {
            "invalid_files_cleaned": invalid_cleaned,
            "orphaned_files_cleaned": orphaned_cleaned,
            "total_cleaned": invalid_cleaned + orphaned_cleaned
        }
        
        self.logger.info(f"音频文件清理完成: {result}")
        return result
    
    def get_storage_info(self) -> Dict[str, any]:
        """
        获取音频存储信息
        Returns:
            Dict: 存储信息统计
        """
        try:
            stats = self.get_pronunciation_statistics()
            storage_info = {
                'storage_path': self.storage.base_path,
                'total_files': stats.get('summary', {}).get('total_stored_files', 0),
                'storage_size_mb': stats.get('summary', {}).get('storage_size_mb', 0),
                'languages': list(stats.get('by_language', {}).keys()),
                'levels': []
            }
            
            # 收集所有级别信息
            for lang_stats in stats.get('by_language', {}).values():
                for level_stats in lang_stats.get('by_level', {}).values():
                    if level_stats.get('level') not in storage_info['levels']:
                        storage_info['levels'].append(level_stats.get('level'))
            
            return storage_info
            
        except Exception as e:
            self.logger.error(f"获取存储信息失败: {e}")
            return {
                'storage_path': getattr(self.storage, 'base_path', ''),
                'total_files': 0,
                'storage_size_mb': 0,
                'languages': [],
                'levels': []
            }
    
    def get_audio_file_info(self, file_path: str) -> Optional[Dict[str, any]]:
        """
        获取音频文件信息
        Args:
            file_path: 音频文件路径
        Returns:
            Dict: 文件信息，如果文件不存在返回None
        """
        try:
            if not file_path or not os.path.exists(file_path):
                return None
            
            file_stat = os.stat(file_path)
            return {
                'exists': True,
                'file_size': file_stat.st_size,
                'file_path': file_path,
                'last_modified': file_stat.st_mtime
            }
            
        except Exception as e:
            self.logger.error(f"获取音频文件信息失败: {e}")
            return None
    
    def search_pronunciation_files(self, language: str = None, level: str = None, 
                                 word_pattern: str = None, limit: int = 100) -> List[Dict[str, any]]:
        """
        搜索发音文件
        Args:
            language: 语言过滤
            level: 级别过滤
            word_pattern: 单词模式过滤
            limit: 结果数量限制
        Returns:
            List[Dict]: 搜索结果
        """
        records = self.storage.search_audio_files(language, level, limit=limit)
        
        results = []
        for record in records:
            # 如果指定了单词模式，进行过滤
            if word_pattern and word_pattern.lower() not in record.word.lower():
                continue
            
            # 检查文件是否存在
            file_exists = os.path.exists(record.file_path) if record.file_path else False
            
            results.append({
                "id": record.id,
                "word": record.word,
                "language": record.language,
                "level": record.level,
                "file_path": record.file_path,
                "file_exists": file_exists,
                "file_size": record.file_size,
                "duration": record.duration,
                "source": record.source,
                "quality": record.quality,
                "created_at": record.created_at,
                "access_count": record.access_count
            })
        
        return results
    
    def export_pronunciation_index(self, output_path: str) -> bool:
        """
        导出发音索引到JSON文件
        Args:
            output_path: 输出文件路径
        Returns:
            bool: 导出是否成功
        """
        try:
            # 获取所有音频记录
            all_records = self.storage.search_audio_files(limit=10000)
            
            # 转换为可序列化的格式
            export_data = {
                "export_time": datetime.now().isoformat(),
                "total_records": len(all_records),
                "records": []
            }
            
            for record in all_records:
                export_data["records"].append({
                    "word": record.word,
                    "language": record.language,
                    "level": record.level,
                    "file_path": record.file_path,
                    "file_size": record.file_size,
                    "duration": record.duration,
                    "source": record.source,
                    "quality": record.quality,
                    "created_at": record.created_at
                })
            
            # 写入JSON文件
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"发音索引导出成功: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出发音索引失败: {e}")
            return False
    
    def close(self):
        """关闭管理器，清理资源"""
        if self.crawler:
            self.crawler.close()