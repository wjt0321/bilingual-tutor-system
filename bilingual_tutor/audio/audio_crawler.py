"""
Audio Crawler - 音频爬虫
Crawls pronunciation audio files for English and Japanese vocabulary
爬取英语和日语词汇的发音音频文件
"""

import os
import requests
import hashlib
import time
import logging
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import json
import re


@dataclass
class AudioSource:
    """音频来源配置"""
    name: str
    base_url: str
    language: str  # english/japanese
    levels: List[str]  # CET-4, CET-5, CET-6 or N5, N4, N3, N2, N1
    audio_format: str  # mp3, wav, etc.
    rate_limit: float  # seconds between requests
    headers: Dict[str, str]
    url_pattern: str  # URL pattern with placeholders


@dataclass
class AudioFile:
    """音频文件信息"""
    word: str
    language: str
    level: str
    source_url: str
    local_path: str
    file_size: int
    duration: Optional[float] = None
    quality: str = "standard"  # standard, high, low
    created_at: str = None


class AudioCrawler:
    """
    音频爬虫 - 爬取英语和日语发音音频
    Audio Crawler - Crawls English and Japanese pronunciation audio
    """
    
    def __init__(self, storage_path: str = None):
        """
        初始化音频爬虫
        Args:
            storage_path: 音频文件存储路径
        """
        if storage_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_path = os.path.join(base_dir, "..", "data", "audio")
        
        self.storage_path = storage_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 确保存储目录存在
        os.makedirs(self.storage_path, exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "english"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "japanese"), exist_ok=True)
        
        # 配置音频来源
        self.audio_sources = self._load_audio_sources()
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _load_audio_sources(self) -> List[AudioSource]:
        """加载音频来源配置"""
        return [
            # 英语音频来源
            AudioSource(
                name="Cambridge Dictionary",
                base_url="https://dictionary.cambridge.org",
                language="english",
                levels=["CET-4", "CET-5", "CET-6"],
                audio_format="mp3",
                rate_limit=1.0,
                headers={"Referer": "https://dictionary.cambridge.org"},
                url_pattern="/media/english/us_pron/{word}.mp3"
            ),
            AudioSource(
                name="Oxford Learner's Dictionary",
                base_url="https://www.oxfordlearnersdictionaries.com",
                language="english", 
                levels=["CET-4", "CET-5", "CET-6"],
                audio_format="mp3",
                rate_limit=1.5,
                headers={"Referer": "https://www.oxfordlearnersdictionaries.com"},
                url_pattern="/media/english/us_pron/{word}.mp3"
            ),
            # 日语音频来源
            AudioSource(
                name="Forvo",
                base_url="https://forvo.com",
                language="japanese",
                levels=["N5", "N4", "N3", "N2", "N1"],
                audio_format="mp3",
                rate_limit=2.0,
                headers={"Referer": "https://forvo.com"},
                url_pattern="/word/{word}/#ja"
            ),
            AudioSource(
                name="JapanesePod101",
                base_url="https://assets.languagepod101.com",
                language="japanese",
                levels=["N5", "N4", "N3", "N2", "N1"],
                audio_format="mp3",
                rate_limit=1.0,
                headers={"Referer": "https://www.japanesepod101.com"},
                url_pattern="/dictionary/japanese/{word}.mp3"
            )
        ]
    
    def crawl_english_pronunciation(self, words: List[str], levels: List[str] = None) -> List[AudioFile]:
        """
        爬取英语发音音频 (CET-4到CET-6)
        Args:
            words: 要爬取的单词列表
            levels: 目标级别列表，默认为所有CET级别
        Returns:
            List[AudioFile]: 成功爬取的音频文件列表
        """
        if levels is None:
            levels = ["CET-4", "CET-5", "CET-6"]
        
        self.logger.info(f"开始爬取英语发音音频，单词数量: {len(words)}")
        
        audio_files = []
        english_sources = [s for s in self.audio_sources if s.language == "english"]
        
        for word in words:
            for level in levels:
                for source in english_sources:
                    if level in source.levels:
                        try:
                            audio_file = self._crawl_single_audio(word, level, source)
                            if audio_file:
                                audio_files.append(audio_file)
                                self.logger.info(f"成功爬取: {word} ({level}) from {source.name}")
                                break  # 找到一个来源就够了
                        except Exception as e:
                            self.logger.warning(f"爬取失败: {word} from {source.name}: {e}")
                            continue
                    
                    # 遵守速率限制
                    time.sleep(source.rate_limit)
        
        self.logger.info(f"英语发音爬取完成，成功: {len(audio_files)}/{len(words) * len(levels)}")
        return audio_files
    
    def crawl_japanese_pronunciation(self, words: List[str], levels: List[str] = None) -> List[AudioFile]:
        """
        爬取日语发音音频 (N5到N1)
        Args:
            words: 要爬取的单词列表
            levels: 目标级别列表，默认为所有JLPT级别
        Returns:
            List[AudioFile]: 成功爬取的音频文件列表
        """
        if levels is None:
            levels = ["N5", "N4", "N3", "N2", "N1"]
        
        self.logger.info(f"开始爬取日语发音音频，单词数量: {len(words)}")
        
        audio_files = []
        japanese_sources = [s for s in self.audio_sources if s.language == "japanese"]
        
        for word in words:
            for level in levels:
                for source in japanese_sources:
                    if level in source.levels:
                        try:
                            audio_file = self._crawl_single_audio(word, level, source)
                            if audio_file:
                                audio_files.append(audio_file)
                                self.logger.info(f"成功爬取: {word} ({level}) from {source.name}")
                                break  # 找到一个来源就够了
                        except Exception as e:
                            self.logger.warning(f"爬取失败: {word} from {source.name}: {e}")
                            continue
                    
                    # 遵守速率限制
                    time.sleep(source.rate_limit)
        
        self.logger.info(f"日语发音爬取完成，成功: {len(audio_files)}/{len(words) * len(levels)}")
        return audio_files
    
    def _crawl_single_audio(self, word: str, level: str, source: AudioSource) -> Optional[AudioFile]:
        """
        爬取单个音频文件
        Args:
            word: 单词
            level: 级别
            source: 音频来源
        Returns:
            AudioFile: 音频文件信息，失败返回None
        """
        try:
            # 构建音频URL
            audio_url = self._build_audio_url(word, source)
            if not audio_url:
                return None
            
            # 生成本地文件路径
            local_path = self._generate_local_path(word, level, source)
            
            # 检查文件是否已存在
            if os.path.exists(local_path):
                self.logger.debug(f"音频文件已存在: {local_path}")
                return AudioFile(
                    word=word,
                    language=source.language,
                    level=level,
                    source_url=audio_url,
                    local_path=local_path,
                    file_size=os.path.getsize(local_path)
                )
            
            # 下载音频文件
            response = self.session.get(audio_url, headers=source.headers, timeout=30)
            response.raise_for_status()
            
            # 验证内容类型
            content_type = response.headers.get('content-type', '')
            if not any(audio_type in content_type.lower() for audio_type in ['audio', 'mpeg', 'mp3', 'wav']):
                self.logger.warning(f"无效的音频内容类型: {content_type} for {audio_url}")
                return None
            
            # 保存文件
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # 验证文件大小
            file_size = len(response.content)
            if file_size < 1024:  # 小于1KB可能是错误页面
                os.remove(local_path)
                self.logger.warning(f"音频文件太小，可能无效: {file_size} bytes")
                return None
            
            return AudioFile(
                word=word,
                language=source.language,
                level=level,
                source_url=audio_url,
                local_path=local_path,
                file_size=file_size
            )
            
        except requests.RequestException as e:
            self.logger.error(f"网络请求失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"爬取音频失败: {e}")
            return None
    
    def _build_audio_url(self, word: str, source: AudioSource) -> Optional[str]:
        """
        构建音频URL
        Args:
            word: 单词
            source: 音频来源
        Returns:
            str: 完整的音频URL
        """
        try:
            # 清理单词（移除特殊字符）
            clean_word = re.sub(r'[^\w\s-]', '', word.lower().strip())
            
            # 根据来源构建URL
            if source.name == "Cambridge Dictionary":
                # Cambridge使用单词的MD5哈希
                word_hash = hashlib.md5(clean_word.encode()).hexdigest()[:8]
                audio_path = f"/media/english/us_pron/{word_hash}.mp3"
            elif source.name == "Oxford Learner's Dictionary":
                # Oxford使用直接的单词路径
                audio_path = f"/media/english/us_pron/{clean_word}.mp3"
            elif source.name == "Forvo":
                # Forvo需要特殊处理，这里简化为直接构建
                audio_path = f"/download/mp3/{clean_word}/ja/"
            elif source.name == "JapanesePod101":
                # JapanesePod101使用直接路径
                audio_path = f"/dictionary/japanese/{clean_word}.mp3"
            else:
                # 使用通用模式
                audio_path = source.url_pattern.format(word=clean_word)
            
            return urljoin(source.base_url, audio_path)
            
        except Exception as e:
            self.logger.error(f"构建音频URL失败: {e}")
            return None
    
    def _generate_local_path(self, word: str, level: str, source: AudioSource) -> str:
        """
        生成本地文件路径
        Args:
            word: 单词
            level: 级别
            source: 音频来源
        Returns:
            str: 本地文件路径
        """
        # 清理文件名
        clean_word = re.sub(r'[^\w\s-]', '', word.lower().strip())
        clean_word = re.sub(r'\s+', '_', clean_word)
        
        # 构建路径: storage/language/level/source_word.format
        filename = f"{source.name.lower().replace(' ', '_')}_{clean_word}.{source.audio_format}"
        return os.path.join(
            self.storage_path,
            source.language,
            level,
            filename
        )
    
    def get_crawl_statistics(self) -> Dict[str, int]:
        """
        获取爬取统计信息
        Returns:
            Dict: 包含各语言和级别的音频文件数量统计
        """
        stats = {
            "total": 0,
            "english": {"total": 0},
            "japanese": {"total": 0}
        }
        
        # 统计英语音频文件
        english_path = os.path.join(self.storage_path, "english")
        if os.path.exists(english_path):
            for level in ["CET-4", "CET-5", "CET-6"]:
                level_path = os.path.join(english_path, level)
                if os.path.exists(level_path):
                    count = len([f for f in os.listdir(level_path) if f.endswith(('.mp3', '.wav'))])
                    stats["english"][level] = count
                    stats["english"]["total"] += count
        
        # 统计日语音频文件
        japanese_path = os.path.join(self.storage_path, "japanese")
        if os.path.exists(japanese_path):
            for level in ["N5", "N4", "N3", "N2", "N1"]:
                level_path = os.path.join(japanese_path, level)
                if os.path.exists(level_path):
                    count = len([f for f in os.listdir(level_path) if f.endswith(('.mp3', '.wav'))])
                    stats["japanese"][level] = count
                    stats["japanese"]["total"] += count
        
        stats["total"] = stats["english"]["total"] + stats["japanese"]["total"]
        return stats
    
    def cleanup_invalid_files(self) -> int:
        """
        清理无效的音频文件（文件大小过小或损坏）
        Returns:
            int: 清理的文件数量
        """
        cleaned_count = 0
        
        for root, dirs, files in os.walk(self.storage_path):
            for file in files:
                if file.endswith(('.mp3', '.wav')):
                    file_path = os.path.join(root, file)
                    try:
                        # 检查文件大小
                        if os.path.getsize(file_path) < 1024:  # 小于1KB
                            os.remove(file_path)
                            cleaned_count += 1
                            self.logger.info(f"清理无效文件: {file_path}")
                    except Exception as e:
                        self.logger.error(f"清理文件失败: {file_path}: {e}")
        
        return cleaned_count
    
    def close(self):
        """关闭爬虫，清理资源"""
        if self.session:
            self.session.close()