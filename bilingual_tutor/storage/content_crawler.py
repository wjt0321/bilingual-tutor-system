"""
真实内容爬虫 - 从公开免费资源获取学习内容
Real Content Crawler - Fetch learning content from free public resources
"""

import json
import hashlib
import time
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .database import LearningDatabase, VocabularyItem, ContentItem
from ..content.crawler_utils import RobustRequester, CrawlerStats, retry_on_failure


class RealContentCrawler:
    """
    真实内容爬虫
    从公开免费资源获取英语和日语学习内容
    支持增量更新、去重、统计等功能
    """
    
    def __init__(self, db: LearningDatabase = None, config_path: Optional[str] = None):
        """
        初始化爬虫
        
        Args:
            db: 数据库实例
            config_path: 配置文件路径
        """
        self.db = db or LearningDatabase()
        self.config = self._load_config(config_path)
        self.crawler_settings = self.config.get('crawler_settings', {})
        self.incremental_settings = self.config.get('incremental_update_settings', {})
        
        self.requester = RobustRequester(
            timeout=self.crawler_settings.get('timeout', 30),
            max_attempts=self.crawler_settings.get('max_attempts', 3),
            min_delay=self.crawler_settings.get('min_delay', 1.0),
            max_delay=self.crawler_settings.get('max_delay', 3.0)
        )
        self.stats = CrawlerStats()
        self.crawled_words: Set[str] = set()
        self.crawled_contents: Set[str] = set()
        self.last_crawl_time: Optional[datetime] = None
        
        # 加载词汇源配置
        self.vocabulary_sources = self._load_vocabulary_sources()
    
    # ==================== 英语词汇爬取 ====================
    
    def _get_cet_vocabulary(self, level: str) -> List[Dict]:
        """
        获取 CET 词汇（优先从网络加载，失败时使用内置数据）
        
        Args:
            level: 词汇级别（CET-4 或 CET-6）
            
        Returns:
            词汇列表
        """
        # 尝试从网络加载
        if self.vocabulary_sources:
            source_key = f"CET-{level}" if level in ["4", "6"] else level
            english_sources = self.vocabulary_sources.get('english_sources', {})
            source_config = english_sources.get(level, english_sources.get(source_key, {}))
            
            if source_config.get('enabled') and source_config.get('type') == 'url':
                return self._fetch_vocabulary_from_url(
                    source_config.get('url'),
                    'english',
                    level,
                    source_config.get('format', 'json'),
                    source_config.get('backup_builtin', True)
                )
        
        # 回退到内置数据
        return self._get_builtin_cet_vocabulary(level)
    
    def _fetch_vocabulary_from_url(self, url: str, language: str, level: str, 
                                     format_type: str = 'json', 
                                     backup_builtin: bool = True) -> List[Dict]:
        """
        从 URL 获取词汇
        
        Args:
            url: 词汇源 URL
            language: 语言（'english' 或 'japanese'）
            level: 词汇级别
            format_type: 数据格式（'json', 'csv', 'html'）
            backup_builtin: 网络失败时是否使用内置词汇
            
        Returns:
            词汇列表
        """
        print(f"  尝试从网络加载 {language} {level} 词汇...")
        print(f"  URL: {url}")
        
        try:
            response = self.requester.get(url)
            if response is None:
                print(f"  ✗ 网络请求失败")
                if backup_builtin:
                    print(f"  → 使用内置词汇作为备份")
                else:
                    print(f"  → 跳过此词汇源")
                return []
            
            content = response.text
            
            # 根据格式解析
            if format_type == 'json':
                data = json.loads(content)
                # 检查数据结构
                if isinstance(data, dict):
                    # 可能是 {"words": [...]} 或类似结构
                    if 'words' in data:
                        words = data['words']
                    elif 'vocabulary' in data:
                        words = data['vocabulary']
                    elif 'data' in data:
                        words = data['data']
                    else:
                        # 假设直接是列表
                        words = list(data.values())[0] if data else []
                elif isinstance(data, list):
                    words = data
                else:
                    words = []
            elif format_type == 'csv':
                import io
                import csv
                reader = csv.DictReader(io.StringIO(content))
                words = list(reader)
            elif format_type == 'html':
                soup = BeautifulSoup(content, 'html.parser')
                words = self._parse_html_vocabulary(soup, language)
            else:
                print(f"  ✗ 不支持的格式: {format_type}")
                words = []
            
            # 统一数据格式
            normalized_words = self._normalize_vocabulary(words, language, level)
            
            print(f"  ✓ 成功加载 {len(normalized_words)} 个词汇")
            return normalized_words
            
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON 解析失败: {e}")
            if backup_builtin:
                print(f"  → 使用内置词汇作为备份")
                return self._get_builtin_cet_vocabulary(level) if language == 'english' else self._get_builtin_jlpt_vocabulary(level)
            return []
        except Exception as e:
            print(f"  ✗ 加载失败: {e}")
            if backup_builtin:
                print(f"  → 使用内置词汇作为备份")
                return self._get_builtin_cet_vocabulary(level) if language == 'english' else self._get_builtin_jlpt_vocabulary(level)
            return []
    
    def _normalize_vocabulary(self, words: List[Dict], language: str, level: str) -> List[Dict]:
        """
        标准化词汇数据格式
        
        Args:
            words: 原始词汇数据
            language: 语言
            level: 级别
            
        Returns:
            标准化后的词汇列表
        """
        normalized = []
        for word_data in words:
            if not isinstance(word_data, dict):
                continue
            
            # 智能识别字段
            word = word_data.get('word') or word_data.get('text') or word_data.get('name') or ''
            if not word:
                continue
            
            # 英语和日语的字段名可能不同
            if language == 'english':
                normalized_item = {
                    'word': word,
                    'phonetic': word_data.get('phonetic') or word_data.get('pronunciation') or word_data.get('reading') or '',
                    'meaning': word_data.get('meaning') or word_data.get('definition') or word_data.get('translation') or '',
                    'example': word_data.get('example') or word_data.get('sentence') or '',
                    'example_cn': word_data.get('example_cn') or word_data.get('translation') or '',
                    'pos': word_data.get('pos') or word_data.get('part_of_speech') or word_data.get('type') or '',
                }
            else:  # japanese
                normalized_item = {
                    'word': word,
                    'reading': word_data.get('reading') or word_data.get('kana') or word_data.get('hiragana') or '',
                    'meaning': word_data.get('meaning') or word_data.get('definition') or word_data.get('translation') or '',
                    'example': word_data.get('example') or word_data.get('sentence') or '',
                    'example_cn': word_data.get('example_cn') or word_data.get('translation') or '',
                    'pos': word_data.get('pos') or word_data.get('part_of_speech') or word_data.get('type') or '',
                }
            
            normalized.append(normalized_item)
        
        return normalized
    
    def _parse_html_vocabulary(self, soup: BeautifulSoup, language: str) -> List[Dict]:
        """
        解析 HTML 格式的词汇
        
        Args:
            soup: BeautifulSoup 对象
            language: 语言
            
        Returns:
            词汇列表
        """
        words = []
        # 查找词汇表格或列表
        if language == 'english':
            # 查找表格或列表
            table = soup.find('table') or soup.find(class_='word-list')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        words.append({
                            'word': cells[0].get_text().strip(),
                            'meaning': cells[1].get_text().strip()
                        })
        else:  # japanese
            # 查找日语词汇
            for item in soup.find_all(class_='word-item'):
                word_elem = item.find(class_='word')
                reading_elem = item.find(class_='reading')
                meaning_elem = item.find(class_='meaning')
                
                if word_elem:
                    words.append({
                        'word': word_elem.get_text().strip(),
                        'reading': reading_elem.get_text().strip() if reading_elem else '',
                        'meaning': meaning_elem.get_text().strip() if meaning_elem else ''
                    })
        
        return words
    
    def _get_builtin_cet_vocabulary(self, level: str) -> List[Dict]:
        """获取 CET 内置词汇（备用数据）"""
        cet4_words = [
            {"word": "abandon", "phonetic": "/əˈbændən/", "meaning": "v. 放弃；抛弃", "pos": "verb", 
             "example": "He abandoned his car in the snow.", "example_cn": "他把车扔在雪地里了。"},
            {"word": "ability", "phonetic": "/əˈbɪləti/", "meaning": "n. 能力；才能", "pos": "noun",
             "example": "She has the ability to solve problems.", "example_cn": "她有解决问题的能力。"},
            {"word": "abroad", "phonetic": "/əˈbrɔːd/", "meaning": "adv. 在国外；到国外", "pos": "adverb",
             "example": "She went abroad for her studies.", "example_cn": "她出国留学了。"},
            {"word": "absent", "phonetic": "/ˈæbsənt/", "meaning": "adj. 缺席的；不在的", "pos": "adj",
             "example": "He was absent from school yesterday.", "example_cn": "他昨天没来上学。"},
            {"word": "absolute", "phonetic": "/ˈæbsəluːt/", "meaning": "adj. 绝对的；完全的", "pos": "adj",
             "example": "I have absolute confidence in you.", "example_cn": "我对你有绝对的信心。"},
            {"word": "absorb", "phonetic": "/əbˈsɔːrb/", "meaning": "v. 吸收；吸引", "pos": "verb",
             "example": "Plants absorb carbon dioxide.", "example_cn": "植物吸收二氧化碳。"},
            {"word": "abstract", "phonetic": "/ˈæbstrækt/", "meaning": "adj. 抽象的 n. 摘要", "pos": "adj/noun",
             "example": "This is an abstract concept.", "example_cn": "这是一个抽象的概念。"},
            {"word": "academic", "phonetic": "/ˌækəˈdemɪk/", "meaning": "adj. 学术的；学业的", "pos": "adj",
             "example": "She has an excellent academic record.", "example_cn": "她的学习成绩优秀。"},
            {"word": "accept", "phonetic": "/əkˈsept/", "meaning": "v. 接受；认可", "pos": "verb",
             "example": "Please accept my apology.", "example_cn": "请接受我的道歉。"},
            {"word": "access", "phonetic": "/ˈækses/", "meaning": "n. 通道；访问 v. 访问", "pos": "noun/verb",
             "example": "Students have access to the library.", "example_cn": "学生可以使用图书馆。"},
            {"word": "accident", "phonetic": "/ˈæksɪdənt/", "meaning": "n. 事故；意外", "pos": "noun",
             "example": "He was killed in a car accident.", "example_cn": "他死于一场车祸。"},
            {"word": "accommodation", "phonetic": "/əˌkɒməˈdeɪʃn/", "meaning": "n. 住宿；膳宿", "pos": "noun",
             "example": "The hotel provides good accommodation.", "example_cn": "这家酒店提供良好的住宿条件。"},
            {"word": "accompany", "phonetic": "/əˈkʌmpəni/", "meaning": "v. 陪伴；伴随", "pos": "verb",
             "example": "She accompanied me to the airport.", "example_cn": "她陪我去了机场。"},
            {"word": "accomplish", "phonetic": "/əˈkɒmplɪʃ/", "meaning": "v. 完成；实现", "pos": "verb",
             "example": "We accomplished our goal.", "example_cn": "我们实现了目标。"},
            {"word": "according", "phonetic": "/əˈkɔːdɪŋ/", "meaning": "prep. 根据；按照", "pos": "prep",
             "example": "According to the report, sales increased.", "example_cn": "根据报告，销售额增加了。"},
            {"word": "account", "phonetic": "/əˈkaʊnt/", "meaning": "n. 账户；描述 v. 解释", "pos": "noun/verb",
             "example": "I opened a bank account.", "example_cn": "我开了一个银行账户。"},
            {"word": "accurate", "phonetic": "/ˈækjərət/", "meaning": "adj. 精确的；准确的", "pos": "adj",
             "example": "The data is highly accurate.", "example_cn": "这些数据非常准确。"},
            {"word": "accuse", "phonetic": "/əˈkjuːz/", "meaning": "v. 指控；谴责", "pos": "verb",
             "example": "He was accused of theft.", "example_cn": "他被指控盗窃。"},
            {"word": "achieve", "phonetic": "/əˈtʃiːv/", "meaning": "v. 达到；取得", "pos": "verb",
             "example": "She achieved her dream.", "example_cn": "她实现了自己的梦想。"},
            {"word": "acknowledge", "phonetic": "/əkˈnɒlɪdʒ/", "meaning": "v. 承认；确认", "pos": "verb",
             "example": "He acknowledged his mistake.", "example_cn": "他承认了自己的错误。"},
            {"word": "acquire", "phonetic": "/əˈkwaɪər/", "meaning": "v. 获得；学到", "pos": "verb",
             "example": "He acquired the skill through practice.", "example_cn": "他通过练习获得了这项技能。"},
            {"word": "activity", "phonetic": "/ækˈtɪvəti/", "meaning": "n. 活动；行动", "pos": "noun",
             "example": "There are many outdoor activities.", "example_cn": "有许多户外活动。"},
            {"word": "actual", "phonetic": "/ˈæktʃuəl/", "meaning": "adj. 实际的；真实的", "pos": "adj",
             "example": "The actual cost was higher.", "example_cn": "实际成本更高。"},
            {"word": "adapt", "phonetic": "/əˈdæpt/", "meaning": "v. 适应；改编", "pos": "verb",
             "example": "You must adapt to the new environment.", "example_cn": "你必须适应新环境。"},
            {"word": "addition", "phonetic": "/əˈdɪʃn/", "meaning": "n. 加法；增加", "pos": "noun",
             "example": "In addition, we need more time.", "example_cn": "此外，我们需要更多时间。"},
            {"word": "address", "phonetic": "/əˈdres/", "meaning": "n. 地址 v. 解决；演讲", "pos": "noun/verb",
             "example": "What's your email address?", "example_cn": "你的电子邮箱地址是什么？"},
            {"word": "adequate", "phonetic": "/ˈædɪkwət/", "meaning": "adj. 足够的；充分的", "pos": "adj",
             "example": "We have adequate resources.", "example_cn": "我们有足够的资源。"},
            {"word": "adjust", "phonetic": "/əˈdʒʌst/", "meaning": "v. 调整；适应", "pos": "verb",
             "example": "Please adjust the volume.", "example_cn": "请调整音量。"},
            {"word": "administration", "phonetic": "/ədˌmɪnɪˈstreɪʃn/", "meaning": "n. 管理；行政", "pos": "noun",
             "example": "The school administration made a decision.", "example_cn": "学校管理层做出了决定。"},
            {"word": "admire", "phonetic": "/ədˈmaɪər/", "meaning": "v. 钦佩；赞赏", "pos": "verb",
             "example": "I admire her courage.", "example_cn": "我钦佩她的勇气。"},
            {"word": "admit", "phonetic": "/ədˈmɪt/", "meaning": "v. 承认；准许进入", "pos": "verb",
             "example": "He admitted his fault.", "example_cn": "他承认了自己的错误。"},
            {"word": "adopt", "phonetic": "/əˈdɒpt/", "meaning": "v. 采用；收养", "pos": "verb",
             "example": "They adopted a new strategy.", "example_cn": "他们采用了新策略。"},
            {"word": "adult", "phonetic": "/ˈædʌlt/", "meaning": "n. 成年人 adj. 成年的", "pos": "noun/adj",
             "example": "Adults should be responsible.", "example_cn": "成年人应该负责任。"},
            {"word": "advance", "phonetic": "/ədˈvɑːns/", "meaning": "v. 前进；提前 n. 进步", "pos": "verb/noun",
             "example": "Technology advances quickly.", "example_cn": "技术进步很快。"},
            {"word": "advantage", "phonetic": "/ədˈvɑːntɪdʒ/", "meaning": "n. 优势；好处", "pos": "noun",
             "example": "What's the advantage of this?", "example_cn": "这有什么好处？"},
            {"word": "adventure", "phonetic": "/ədˈventʃər/", "meaning": "n. 冒险；奇遇", "pos": "noun",
             "example": "Life is an adventure.", "example_cn": "生活是一场冒险。"},
            {"word": "advertise", "phonetic": "/ˈædvətaɪz/", "meaning": "v. 做广告；宣传", "pos": "verb",
             "example": "They advertised the new product.", "example_cn": "他们为新产品做了广告。"},
            {"word": "advice", "phonetic": "/ədˈvaɪs/", "meaning": "n. 建议；忠告", "pos": "noun",
             "example": "Can you give me some advice?", "example_cn": "你能给我一些建议吗？"},
            {"word": "affect", "phonetic": "/əˈfekt/", "meaning": "v. 影响；感动", "pos": "verb",
             "example": "This will affect our decision.", "example_cn": "这将影响我们的决定。"},
            {"word": "afford", "phonetic": "/əˈfɔːd/", "meaning": "v. 买得起；负担得起", "pos": "verb",
             "example": "I can't afford this car.", "example_cn": "我买不起这辆车。"},
            # 更多词汇...
            {"word": "agree", "phonetic": "/əˈɡriː/", "meaning": "v. 同意；一致", "pos": "verb",
             "example": "I agree with you.", "example_cn": "我同意你的看法。"},
            {"word": "agriculture", "phonetic": "/ˈæɡrɪkʌltʃər/", "meaning": "n. 农业", "pos": "noun",
             "example": "Agriculture is important for the economy.", "example_cn": "农业对经济很重要。"},
            {"word": "aim", "phonetic": "/eɪm/", "meaning": "n. 目标 v. 瞄准；旨在", "pos": "noun/verb",
             "example": "What's your aim in life?", "example_cn": "你人生的目标是什么？"},
            {"word": "alarm", "phonetic": "/əˈlɑːrm/", "meaning": "n. 警报；闹钟 v. 使惊慌", "pos": "noun/verb",
             "example": "The fire alarm went off.", "example_cn": "火警警报响了。"},
            {"word": "album", "phonetic": "/ˈælbəm/", "meaning": "n. 相册；专辑", "pos": "noun",
             "example": "I bought her new album.", "example_cn": "我买了她的新专辑。"},
            {"word": "alcohol", "phonetic": "/ˈælkəhɒl/", "meaning": "n. 酒精；酒", "pos": "noun",
             "example": "Don't drink alcohol and drive.", "example_cn": "不要酒后驾车。"},
            {"word": "allow", "phonetic": "/əˈlaʊ/", "meaning": "v. 允许；准许", "pos": "verb",
             "example": "Smoking is not allowed here.", "example_cn": "这里不允许吸烟。"},
            {"word": "almost", "phonetic": "/ˈɔːlməʊst/", "meaning": "adv. 几乎；差不多", "pos": "adverb",
             "example": "It's almost time to go.", "example_cn": "差不多该走了。"},
            {"word": "alone", "phonetic": "/əˈləʊn/", "meaning": "adj./adv. 独自的；单独", "pos": "adj/adv",
             "example": "She lives alone.", "example_cn": "她独自生活。"},
            {"word": "alternative", "phonetic": "/ɔːlˈtɜːnətɪv/", "meaning": "n. 选择 adj. 替代的", "pos": "noun/adj",
             "example": "We have no alternative.", "example_cn": "我们别无选择。"},
            {"word": "amaze", "phonetic": "/əˈmeɪz/", "meaning": "v. 使吃惊", "pos": "verb",
             "example": "The result amazed everyone.", "example_cn": "结果让每个人都很吃惊。"},
            {"word": "ambition", "phonetic": "/æmˈbɪʃn/", "meaning": "n. 野心；抱负", "pos": "noun",
             "example": "She has great ambition.", "example_cn": "她有远大的抱负。"},
            {"word": "ambulance", "phonetic": "/ˈæmbjələns/", "meaning": "n. 救护车", "pos": "noun",
             "example": "The ambulance arrived quickly.", "example_cn": "救护车很快就到了。"},
            {"word": "amount", "phonetic": "/əˈmaʊnt/", "meaning": "n. 数量；金额", "pos": "noun",
             "example": "A large amount of money.", "example_cn": "一大笔钱。"},
            {"word": "amuse", "phonetic": "/əˈmjuːz/", "meaning": "v. 逗乐；娱乐", "pos": "verb",
             "example": "The story amused the children.", "example_cn": "这个故事逗乐了孩子们。"},
            {"word": "analyze", "phonetic": "/ˈænəlaɪz/", "meaning": "v. 分析", "pos": "verb",
             "example": "We need to analyze the data.", "example_cn": "我们需要分析这些数据。"},
            {"word": "ancestor", "phonetic": "/ˈænsestər/", "meaning": "n. 祖先", "pos": "noun",
             "example": "Our ancestors lived here.", "example_cn": "我们的祖先住在这里。"},
            {"word": "ancient", "phonetic": "/ˈeɪnʃənt/", "meaning": "adj. 古老的", "pos": "adj",
             "example": "This is an ancient building.", "example_cn": "这是一座古老的建筑。"},
            {"word": "anger", "phonetic": "/ˈæŋɡər/", "meaning": "n. 愤怒", "pos": "noun",
             "example": "He couldn't hide his anger.", "example_cn": "他无法掩饰自己的愤怒。"},
            {"word": "angle", "phonetic": "/ˈæŋɡl/", "meaning": "n. 角度；角", "pos": "noun",
             "example": "The angle is 90 degrees.", "example_cn": "这个角度是90度。"},
            {"word": "animal", "phonetic": "/ˈænɪml/", "meaning": "n. 动物", "pos": "noun",
             "example": "Dogs are popular animals.", "example_cn": "狗是受欢迎的宠物。"},
            {"word": "ankle", "phonetic": "/ˈæŋkl/", "meaning": "n. 脚踝", "pos": "noun",
             "example": "I hurt my ankle.", "example_cn": "我的脚踝受伤了。"},
            {"word": "announce", "phonetic": "/əˈnaʊns/", "meaning": "v. 宣布", "pos": "verb",
             "example": "They announced the news.", "example_cn": "他们宣布了这个消息。"},
            {"word": "annoy", "phonetic": "/əˈnɔɪ/", "meaning": "v. 使恼火", "pos": "verb",
             "example": "The noise annoyed me.", "example_cn": "噪音让我很恼火。"},
            {"word": "annual", "phonetic": "/ˈænjuəl/", "meaning": "adj. 每年的；年度的", "pos": "adj",
             "example": "The annual meeting is in May.", "example_cn": "年度会议在五月。"},
            {"word": "another", "phonetic": "/əˈnʌðər/", "meaning": "adj. 另一个", "pos": "adj",
             "example": "I need another cup of coffee.", "example_cn": "我需要再来一杯咖啡。"},
            {"word": "answer", "phonetic": "/ˈɑːnsər/", "meaning": "n. 答案 v. 回答", "pos": "noun/verb",
             "example": "Please answer my question.", "example_cn": "请回答我的问题。"},
            {"word": "anxious", "phonetic": "/ˈæŋkʃəs/", "meaning": "adj. 焦虑的", "pos": "adj",
             "example": "She was anxious about the exam.", "example_cn": "她为考试感到焦虑。"},
            {"word": "anyway", "phonetic": "/ˈeniweɪ/", "meaning": "adv. 无论如何", "pos": "adverb",
             "example": "It's raining, but let's go anyway.", "example_cn": "下雨了，但我们还是走吧。"},
            {"word": "apart", "phonetic": "/əˈpɑːrt/", "meaning": "adv. 分开；相隔", "pos": "adverb",
             "example": "The two houses are far apart.", "example_cn": "这两座房子相距很远。"},
            {"word": "apartment", "phonetic": "/əˈpɑːrtmənt/", "meaning": "n. 公寓", "pos": "noun",
             "example": "She lives in a small apartment.", "example_cn": "她住在一个小公寓里。"},
            {"word": "apologize", "phonetic": "/əˈpɒlədʒaɪz/", "meaning": "v. 道歉", "pos": "verb",
             "example": "You should apologize to her.", "example_cn": "你应该向她道歉。"},
            {"word": "appear", "phonetic": "/əˈpɪr/", "meaning": "v. 出现；似乎", "pos": "verb",
             "example": "A cat appeared in the garden.", "example_cn": "花园里出现了一只猫。"},
            {"word": "apple", "phonetic": "/ˈæpl/", "meaning": "n. 苹果", "pos": "noun",
             "example": "I ate an apple for breakfast.", "example_cn": "我早餐吃了一个苹果。"},
            {"word": "application", "phonetic": "/ˌæplɪˈkeɪʃn/", "meaning": "n. 申请；应用", "pos": "noun",
             "example": "I submitted my application.", "example_cn": "我提交了申请。"},
            {"word": "apply", "phonetic": "/əˈplaɪ/", "meaning": "v. 申请；应用", "pos": "verb",
             "example": "Apply online for the job.", "example_cn": "在线申请这份工作。"},
            {"word": "appoint", "phonetic": "/əˈpɔɪnt/", "meaning": "v. 任命；指定", "pos": "verb",
             "example": "They appointed a new manager.", "example_cn": "他们任命了一位新经理。"},
            {"word": "appreciate", "phonetic": "/əˈpriːʃieɪt/", "meaning": "v. 感激；欣赏", "pos": "verb",
             "example": "I appreciate your help.", "example_cn": "我很感激你的帮助。"},
            {"word": "approach", "phonetic": "/əˈprəʊtʃ/", "meaning": "v. 接近 n. 方法", "pos": "verb/noun",
             "example": "The train is approaching.", "example_cn": "火车正在靠近。"},
            {"word": "appropriate", "phonetic": "/əˈprəʊpriət/", "meaning": "adj. 适当的", "pos": "adj",
             "example": "Please wear appropriate clothing.", "example_cn": "请穿着适当的服装。"},
            {"word": "approve", "phonetic": "/əˈpruːv/", "meaning": "v. 批准；赞成", "pos": "verb",
             "example": "The manager approved the plan.", "example_cn": "经理批准了这个计划。"},
            {"word": "approximate", "phonetic": "/əˈprɒksɪmət/", "meaning": "adj. 大约的；近似的", "pos": "adj",
             "example": "The approximate cost is $100.", "example_cn": "大约的费用是100美元。"},
            {"word": "arbitrary", "phonetic": "/ˈɑːrbɪtrəri/", "meaning": "adj. 任意的；随意的", "pos": "adj",
             "example": "The decision was arbitrary.", "example_cn": "这个决定是随意的。"},
            {"word": "architect", "phonetic": "/ˈɑːrkɪtekt/", "meaning": "n. 建筑师", "pos": "noun",
             "example": "He is a famous architect.", "example_cn": "他是一位著名的建筑师。"},
            {"word": "area", "phonetic": "/ˈeəriə/", "meaning": "n. 区域；面积", "pos": "noun",
             "example": "This is a residential area.", "example_cn": "这是一个住宅区。"},
            {"word": "argue", "phonetic": "/ˈɑːrɡjuː/", "meaning": "v. 争论；辩论", "pos": "verb",
             "example": "They argued about the problem.", "example_cn": "他们争论这个问题。"},
            {"word": "arise", "phonetic": "/əˈraɪz/", "meaning": "v. 出现；发生", "pos": "verb",
             "example": "A problem arose.", "example_cn": "出现了问题。"},
            {"word": "arithmetic", "phonetic": "/əˈrɪθmətɪk/", "meaning": "n. 算术", "pos": "noun",
             "example": "She is good at arithmetic.", "example_cn": "她擅长算术。"},
            {"word": "arm", "phonetic": "/ɑːrm/", "meaning": "n. 手臂 v. 武装", "pos": "noun/verb",
             "example": "She broke her arm.", "example_cn": "她的手臂骨折了。"},
            {"word": "army", "phonetic": "/ˈɑːrmi/", "meaning": "n. 军队", "pos": "noun",
             "example": "He joined the army.", "example_cn": "他参了军。"},
            {"word": "around", "phonetic": "/əˈraʊnd/", "meaning": "prep. 在周围 adv. 大约", "pos": "prep/adverb",
             "example": "There are trees around the house.", "example_cn": "房子周围有树。"},
            {"word": "arrange", "phonetic": "/əˈreɪndʒ/", "meaning": "v. 安排；整理", "pos": "verb",
             "example": "I can arrange a meeting.", "example_cn": "我可以安排一个会议。"},
            {"word": "arrest", "phonetic": "/əˈrest/", "meaning": "v. 逮捕", "pos": "verb",
             "example": "The police arrested the thief.", "example_cn": "警察逮捕了小偷。"},
            {"word": "arrive", "phonetic": "/əˈraɪv/", "meaning": "v. 到达", "pos": "verb",
             "example": "When will you arrive?", "example_cn": "你什么时候到？"},
            {"word": "arrow", "phonetic": "/ˈærəʊ/", "meaning": "n. 箭", "pos": "noun",
             "example": "He shot an arrow at the target.", "example_cn": "他向目标射了一箭。"},
            {"word": "art", "phonetic": "/ɑːrt/", "meaning": "n. 艺术；美术", "pos": "noun",
             "example": "She loves art.", "example_cn": "她热爱艺术。"},
            {"word": "article", "phonetic": "/ˈɑːrtɪkl/", "meaning": "n. 文章；物品", "pos": "noun",
             "example": "I read an interesting article.", "example_cn": "我读了一篇有趣的文章。"},
            {"word": "artist", "phonetic": "/ˈɑːrtɪst/", "meaning": "n. 艺术家", "pos": "noun",
             "example": "He is a talented artist.", "example_cn": "他是一位有天赋的艺术家。"},
            {"word": "ash", "phonetic": "/æʃ/", "meaning": "n. 灰烬", "pos": "noun",
             "example": "The fire left only ash.", "example_cn": "大火只留下了灰烬。"},
            {"word": "ashamed", "phonetic": "/əˈʃeɪmd/", "meaning": "adj. 羞愧的", "pos": "adj",
             "example": "He felt ashamed of his mistake.", "example_cn": "他对自己的错误感到羞愧。"},
            {"word": "aside", "phonetic": "/əˈsaɪd/", "meaning": "adv. 在旁边", "pos": "adverb",
             "example": "Step aside, please.", "example_cn": "请让开。"},
            {"word": "ask", "phonetic": "/æsk/", "meaning": "v. 问；请求", "pos": "verb",
             "example": "Can I ask you a question?", "example_cn": "我可以问你一个问题吗？"},
            {"word": "asleep", "phonetic": "/əˈsliːp/", "meaning": "adj. 睡着的", "pos": "adj",
             "example": "The baby is asleep.", "example_cn": "婴儿睡着了。"},
            {"word": "aspect", "phonetic": "/ˈæspekt/", "meaning": "n. 方面；外观", "pos": "noun",
             "example": "We must consider every aspect.", "example_cn": "我们必须考虑每个方面。"},
            {"word": "assess", "phonetic": "/əˈses/", "meaning": "v. 评估；评定", "pos": "verb",
             "example": "We need to assess the situation.", "example_cn": "我们需要评估形势。"},
            {"word": "assist", "phonetic": "/əˈsɪst/", "meaning": "v. 协助；帮助", "pos": "verb",
             "example": "I can assist you with that.", "example_cn": "我可以帮你处理那个。"},
            {"word": "associate", "phonetic": "/əˈsəʊʃieɪt/", "meaning": "v. 联想；交往 n. 同事", "pos": "verb/noun",
             "example": "I associate summer with ice cream.", "example_cn": "我把夏天和冰淇淋联系在一起。"},
            {"word": "assume", "phonetic": "/əˈsjuːm/", "meaning": "v. 假定；承担", "pos": "verb",
             "example": "Don't assume anything.", "example_cn": "不要做任何假设。"},
            {"word": "astonish", "phonetic": "/əˈstɒnɪʃ/", "meaning": "v. 使惊讶", "pos": "verb",
             "example": "The news astonished everyone.", "example_cn": "这个消息让每个人都很惊讶。"},
            {"word": "athlete", "phonetic": "/ˈæθliːt/", "meaning": "n. 运动员", "pos": "noun",
             "example": "She is a professional athlete.", "example_cn": "她是一名职业运动员。"},
            {"word": "atmosphere", "phonetic": "/ˈætməsfɪr/", "meaning": "n. 大气；气氛", "pos": "noun",
             "example": "The atmosphere was relaxed.", "example_cn": "气氛很轻松。"},
            {"word": "attach", "phonetic": "/əˈtætʃ/", "meaning": "v. 系上；附加", "pos": "verb",
             "example": "Please attach the file.", "example_cn": "请附上文件。"},
            {"word": "attack", "phonetic": "/əˈtæk/", "meaning": "v. 攻击 n. 发作", "pos": "verb/noun",
             "example": "The dog attacked the stranger.", "example_cn": "狗攻击了陌生人。"},
            {"word": "attempt", "phonetic": "/əˈtempt/", "meaning": "v. 尝试 n. 企图", "pos": "verb/noun",
             "example": "He attempted to escape.", "example_cn": "他试图逃跑。"},
            {"word": "attend", "phonetic": "/əˈtend/", "meaning": "v. 出席；参加", "pos": "verb",
             "example": "Did you attend the meeting?", "example_cn": "你参加会议了吗？"},
            {"word": "attitude", "phonetic": "/ˈætɪtjuːd/", "meaning": "n. 态度", "pos": "noun",
             "example": "She has a positive attitude.", "example_cn": "她有积极的态度。"},
            {"word": "attract", "phonetic": "/əˈtrækt/", "meaning": "v. 吸引", "pos": "verb",
             "example": "The flowers attract butterflies.", "example_cn": "花朵吸引了蝴蝶。"},
            {"word": "audience", "phonetic": "/ˈɔːdiəns/", "meaning": "n. 观众", "pos": "noun",
             "example": "The audience applauded.", "example_cn": "观众鼓掌。"},
            {"word": "author", "phonetic": "/ˈɔːθər/", "meaning": "n. 作者", "pos": "noun",
             "example": "Who is the author of this book?", "example_cn": "这本书的作者是谁？"},
            {"word": "authority", "phonetic": "/ɔːˈθɒrəti/", "meaning": "n. 权威；当局", "pos": "noun",
             "example": "The local authorities took action.", "example_cn": "当局采取了行动。"},
            {"word": "automatic", "phonetic": "/ˌɔːtəˈmætɪk/", "meaning": "adj. 自动的", "pos": "adj",
             "example": "The door is automatic.", "example_cn": "门是自动的。"},
            {"word": "available", "phonetic": "/əˈveɪləbl/", "meaning": "adj. 可用的；有空的", "pos": "adj",
             "example": "Are you available tomorrow?", "example_cn": "你明天有空吗？"},
            {"word": "average", "phonetic": "/ˈævərɪdʒ/", "meaning": "n. 平均 adj. 平均的", "pos": "noun/adj",
             "example": "The average age is 25.", "example_cn": "平均年龄是25岁。"},
            {"word": "avoid", "phonetic": "/əˈvɔɪd/", "meaning": "v. 避免", "pos": "verb",
             "example": "You should avoid smoking.", "example_cn": "你应该避免吸烟。"},
            {"word": "awake", "phonetic": "/əˈweɪk/", "meaning": "adj. 醒着的 v. 唤醒", "pos": "adj/verb",
             "example": "I was awake all night.", "example_cn": "我整晚没睡。"},
            {"word": "award", "phonetic": "/əˈwɔːrd/", "meaning": "n. 奖品 v. 授予", "pos": "noun/verb",
             "example": "She won an award.", "example_cn": "她获奖了。"},
            {"word": "aware", "phonetic": "/əˈwer/", "meaning": "adj. 意识到的", "pos": "adj",
             "example": "Are you aware of the problem?", "example_cn": "你意识到这个问题了吗？"},
            {"word": "away", "phonetic": "/əˈweɪ/", "meaning": "adv. 离开；远离", "pos": "adverb",
             "example": "She is away on business.", "example_cn": "她出差去了。"},
            {"word": "awesome", "phonetic": "/ˈɔːsəm/", "meaning": "adj. 令人敬畏的；极好的", "pos": "adj",
             "example": "The view is awesome.", "example_cn": "景色太棒了。"},
            {"word": "awful", "phonetic": "/ˈɔːfl/", "meaning": "adj. 可怕的；糟糕的", "pos": "adj",
             "example": "The weather is awful.", "example_cn": "天气太糟糕了。"},
        ]
        
        # 根据级别返回不同词汇
        if level == "CET-4":
            return cet4_words
        elif level == "CET-6":
            # CET-6 添加更高级词汇
            cet6_words = cet4_words + [
                {"word": "abbreviation", "phonetic": "/əˌbriːviˈeɪʃn/", "meaning": "n. 缩写；缩略词", "pos": "noun",
                 "example": "'Dr.' is an abbreviation for 'Doctor'.", "example_cn": "'Dr.'是'Doctor'的缩写。"},
                {"word": "abolish", "phonetic": "/əˈbɒlɪʃ/", "meaning": "v. 废除；废止", "pos": "verb",
                 "example": "Slavery was abolished in 1865.", "example_cn": "奴隶制于1865年被废除。"},
                {"word": "abrupt", "phonetic": "/əˈbrʌpt/", "meaning": "adj. 突然的；唐突的", "pos": "adj",
                 "example": "His abrupt manner offended them.", "example_cn": "他唐突的态度冒犯了他们。"},
                {"word": "absurd", "phonetic": "/əbˈsɜːd/", "meaning": "adj. 荒谬的；可笑的", "pos": "adj",
                 "example": "What an absurd idea!", "example_cn": "多么荒谬的想法！"},
                {"word": "abundance", "phonetic": "/əˈbʌndəns/", "meaning": "n. 丰富；充足", "pos": "noun",
                 "example": "There is an abundance of food.", "example_cn": "食物很丰富。"},
            ]
            return cet6_words
        else:
            return cet4_words
    
    # ==================== 日语词汇爬取 ====================
    
    def _get_jlpt_vocabulary(self, level: str) -> List[Dict]:
        """
        获取 JLPT 词汇（优先从网络加载，失败时使用内置数据）
        
        Args:
            level: JLPT级别（N5, N4, N3, N2, N1）
            
        Returns:
            词汇列表
        """
        # 尝试从网络加载
        if self.vocabulary_sources:
            japanese_sources = self.vocabulary_sources.get('japanese_sources', {})
            source_config = japanese_sources.get(level, {})
            
            if source_config.get('enabled') and source_config.get('type') == 'url':
                return self._fetch_vocabulary_from_url(
                    source_config.get('url'),
                    'japanese',
                    level,
                    source_config.get('format', 'json'),
                    source_config.get('backup_builtin', True)
                )
        
        # 回退到内置数据
        return self._get_builtin_jlpt_vocabulary(level)
    
    def _get_builtin_jlpt_vocabulary(self, level: str) -> List[Dict]:
        """获取 JLPT 内置词汇（备用数据）"""
        # JLPT N5 核心词汇
        n5_words = [
            {"word": "あう", "reading": "会う", "meaning": "v. 见面", "pos": "動詞",
             "example": "友達に会います。", "example_cn": "和朋友见面。"},
            {"word": "あおい", "reading": "青い", "meaning": "adj. 蓝色的", "pos": "形容詞",
             "example": "空は青いです。", "example_cn": "天空是蓝色的。"},
            {"word": "あかい", "reading": "赤い", "meaning": "adj. 红色的", "pos": "形容詞",
             "example": "りんごは赤いです。", "example_cn": "苹果是红色的。"},
            {"word": "あかるい", "reading": "明るい", "meaning": "adj. 明亮的", "pos": "形容詞",
             "example": "この部屋は明るいです。", "example_cn": "这个房间很明亮。"},
            {"word": "あき", "reading": "秋", "meaning": "n. 秋天", "pos": "名詞",
             "example": "秋は涼しいです。", "example_cn": "秋天很凉爽。"},
            {"word": "あける", "reading": "開ける", "meaning": "v. 打开", "pos": "動詞",
             "example": "窓を開けてください。", "example_cn": "请打开窗户。"},
            {"word": "あげる", "reading": "上げる", "meaning": "v. 给；举起", "pos": "動詞",
             "example": "プレゼントをあげます。", "example_cn": "送礼物。"},
            {"word": "あさ", "reading": "朝", "meaning": "n. 早上", "pos": "名詞",
             "example": "朝ごはんを食べます。", "example_cn": "吃早饭。"},
            {"word": "あさって", "reading": "明後日", "meaning": "n. 后天", "pos": "名詞",
             "example": "明後日は日曜日です。", "example_cn": "后天是星期天。"},
            {"word": "あし", "reading": "足", "meaning": "n. 脚；腿", "pos": "名詞",
             "example": "足が痛いです。", "example_cn": "脚疼。"},
            {"word": "あした", "reading": "明日", "meaning": "n. 明天", "pos": "名詞",
             "example": "明日は雨です。", "example_cn": "明天下雨。"},
            {"word": "あそこ", "reading": "", "meaning": "pron. 那里", "pos": "代詞",
             "example": "あそこに行きましょう。", "example_cn": "去那里吧。"},
            {"word": "あそぶ", "reading": "遊ぶ", "meaning": "v. 玩", "pos": "動詞",
             "example": "公園で遊びます。", "example_cn": "在公园玩。"},
            {"word": "あたたかい", "reading": "暖かい", "meaning": "adj. 温暖的", "pos": "形容詞",
             "example": "今日は暖かいです。", "example_cn": "今天很暖和。"},
            {"word": "あたま", "reading": "頭", "meaning": "n. 头", "pos": "名詞",
             "example": "頭が痛いです。", "example_cn": "头疼。"},
            {"word": "あたらしい", "reading": "新しい", "meaning": "adj. 新的", "pos": "形容詞",
             "example": "新しい本を買いました。", "example_cn": "买了新书。"},
            {"word": "あちら", "reading": "", "meaning": "pron. 那边（敬语）", "pos": "代詞",
             "example": "あちらでお待ちください。", "example_cn": "请在那边等候。"},
            {"word": "あつい", "reading": "暑い", "meaning": "adj. 热的（天气）", "pos": "形容詞",
             "example": "今日は暑いです。", "example_cn": "今天很热。"},
            {"word": "あつい", "reading": "熱い", "meaning": "adj. 烫的", "pos": "形容詞",
             "example": "お茶は熱いです。", "example_cn": "茶很烫。"},
            {"word": "あと", "reading": "後", "meaning": "n. 之后；后面", "pos": "名詞",
             "example": "食事の後で散歩します。", "example_cn": "饭后散步。"},
            {"word": "あなた", "reading": "", "meaning": "pron. 你", "pos": "代詞",
             "example": "あなたは学生ですか？", "example_cn": "你是学生吗？"},
            {"word": "あに", "reading": "兄", "meaning": "n. 哥哥（自己的）", "pos": "名詞",
             "example": "兄は大学生です。", "example_cn": "我哥哥是大学生。"},
            {"word": "あね", "reading": "姉", "meaning": "n. 姐姐（自己的）", "pos": "名詞",
             "example": "姉は東京に住んでいます。", "example_cn": "我姐姐住在东京。"},
            {"word": "あの", "reading": "", "meaning": "det. 那个", "pos": "連體詞",
             "example": "あの人は誰ですか？", "example_cn": "那个人是谁？"},
            {"word": "アパート", "reading": "", "meaning": "n. 公寓", "pos": "名詞",
             "example": "私はアパートに住んでいます。", "example_cn": "我住在公寓里。"},
            {"word": "あびる", "reading": "浴びる", "meaning": "v. 淋；沐浴", "pos": "動詞",
             "example": "シャワーを浴びます。", "example_cn": "淋浴。"},
            {"word": "あぶない", "reading": "危ない", "meaning": "adj. 危险的", "pos": "形容詞",
             "example": "ここは危ないです。", "example_cn": "这里危险。"},
            {"word": "あまい", "reading": "甘い", "meaning": "adj. 甜的", "pos": "形容詞",
             "example": "このお菓子は甘いです。", "example_cn": "这个点心很甜。"},
            {"word": "あまり", "reading": "", "meaning": "adv. 不太（与否定连用）", "pos": "副詞",
             "example": "あまり好きではありません。", "example_cn": "不太喜欢。"},
            {"word": "あめ", "reading": "雨", "meaning": "n. 雨", "pos": "名詞",
             "example": "雨が降っています。", "example_cn": "正在下雨。"},
            {"word": "あらう", "reading": "洗う", "meaning": "v. 洗", "pos": "動詞",
             "example": "手を洗います。", "example_cn": "洗手。"},
            {"word": "ある", "reading": "", "meaning": "v. 有；在（无生命）", "pos": "動詞",
             "example": "机の上に本があります。", "example_cn": "桌子上有书。"},
            {"word": "あるく", "reading": "歩く", "meaning": "v. 走路", "pos": "動詞",
             "example": "毎日歩きます。", "example_cn": "每天走路。"},
            {"word": "いい", "reading": "良い", "meaning": "adj. 好的", "pos": "形容詞",
             "example": "いい天気ですね。", "example_cn": "天气真好啊。"},
            {"word": "いいえ", "reading": "", "meaning": "interj. 不；不是", "pos": "感嘆詞",
             "example": "いいえ、違います。", "example_cn": "不，不对。"},
            {"word": "いう", "reading": "言う", "meaning": "v. 说", "pos": "動詞",
             "example": "何と言いましたか？", "example_cn": "你说了什么？"},
            {"word": "いえ", "reading": "家", "meaning": "n. 家；房子", "pos": "名詞",
             "example": "家に帰ります。", "example_cn": "回家。"},
            {"word": "いく", "reading": "行く", "meaning": "v. 去", "pos": "動詞",
             "example": "学校に行きます。", "example_cn": "去学校。"},
            {"word": "いくつ", "reading": "", "meaning": "pron. 多少个", "pos": "代詞",
             "example": "りんごはいくつありますか？", "example_cn": "有几个苹果？"},
            {"word": "いくら", "reading": "", "meaning": "pron. 多少钱", "pos": "代詞",
             "example": "これはいくらですか？", "example_cn": "这个多少钱？"},
        ]
        
        # N4 增加更多词汇
        n4_words = [
            {"word": "あいさつ", "reading": "挨拶", "meaning": "n. 问候；打招呼", "pos": "名詞",
             "example": "朝のあいさつをします。", "example_cn": "早上打招呼。"},
            {"word": "あいだ", "reading": "間", "meaning": "n. 之间；期间", "pos": "名詞",
             "example": "友達の間で人気があります。", "example_cn": "在朋友间很受欢迎。"},
            {"word": "あう", "reading": "合う", "meaning": "v. 合适；一致", "pos": "動詞",
             "example": "このサイズは合います。", "example_cn": "这个尺寸合适。"},
            {"word": "あかちゃん", "reading": "赤ちゃん", "meaning": "n. 婴儿", "pos": "名詞",
             "example": "赤ちゃんが生まれました。", "example_cn": "婴儿出生了。"},
            {"word": "あがる", "reading": "上がる", "meaning": "v. 上升；进入", "pos": "動詞",
             "example": "気温が上がりました。", "example_cn": "气温上升了。"},
            {"word": "あいする", "reading": "愛する", "meaning": "v. 爱", "pos": "動詞",
             "example": "家族を愛します。", "example_cn": "爱家人。"},
            {"word": "あいて", "reading": "相手", "meaning": "n. 对象；对手", "pos": "名詞",
             "example": "相手を変えました。", "example_cn": "换了对手。"},
            {"word": "あきらめる", "reading": "諦める", "meaning": "v. 放弃", "pos": "動詞",
             "example": "諦めないでください。", "example_cn": "请不要放弃。"},
            {"word": "あける", "reading": "明ける", "meaning": "v. 过（时间）", "pos": "動詞",
             "example": "夜が明けました。", "example_cn": "天亮了。"},
            {"word": "あげる", "reading": "上げる", "meaning": "v. 举起；提高", "pos": "動詞",
             "example": "手を上げます。", "example_cn": "举手。"},
            {"word": "あそぶ", "reading": "遊ぶ", "meaning": "v. 玩", "pos": "動詞",
             "example": "公園で遊びます。", "example_cn": "在公园玩。"},
            {"word": "あたえる", "reading": "与える", "meaning": "v. 给；给予", "pos": "動詞",
             "example": "影響を与えます。", "example_cn": "给予影响。"},
            {"word": "あたたまる", "reading": "集まる", "meaning": "v. 聚集", "pos": "動詞",
             "example": "駅に集まりました。", "example_cn": "聚集在车站。"},
            {"word": "あつめる", "reading": "集める", "meaning": "v. 收集", "pos": "動詞",
             "example": "切手を集めます。", "example_cn": "收集邮票。"},
            {"word": "あつかう", "reading": "扱う", "meaning": "v. 处理；对待", "pos": "動詞",
             "example": "お客様を扱います。", "example_cn": "接待客人。"},
            {"word": "あてな", "reading": "宛名", "meaning": "n. 收件人姓名", "pos": "名詞",
             "example": "宛名を書きます。", "example_cn": "写收件人姓名。"},
            {"word": "あてはまる", "reading": "当てはまる", "meaning": "v. 适合；符合", "pos": "動詞",
             "example": "条件に当てはまります。", "example_cn": "符合条件。"},
            {"word": "あな", "reading": "穴", "meaning": "n. 洞；孔", "pos": "名詞",
             "example": "ポケットに穴が開きました。", "example_cn": "口袋破了。"},
            {"word": "あぶら", "reading": "油", "meaning": "n. 油", "pos": "名詞",
             "example": "油で揚げます。", "example_cn": "用油炸。"},
            {"word": "あぶる", "reading": "炙る", "meaning": "v. 烤", "pos": "動詞",
             "example": "魚を炙ります。", "example_cn": "烤鱼。"},
            {"word": "あまど", "reading": "雨戸", "meaning": "n. 雨窗", "pos": "名詞",
             "example": "雨戸を閉めます。", "example_cn": "关雨窗。"},
            {"word": "あまや", "reading": "雨屋", "meaning": "n. 雨点", "pos": "名詞",
             "example": "雨屋が見えます。", "example_cn": "能看到雨云。"},
            {"word": "あやまる", "reading": "謝る", "meaning": "v. 道歉", "pos": "動詞",
             "example": "先生に謝ります。", "example_cn": "向老师道歉。"},
            {"word": "あらい", "reading": "洗い", "meaning": "n. 洗", "pos": "名詞",
             "example": "車を洗いに行きます。", "example_cn": "去洗车。"},
            {"word": "あらす", "reading": "荒らす", "meaning": "v. 弄脏；破坏", "pos": "動詞",
             "example": "部屋を荒らさないでください。", "example_cn": "请不要弄乱房间。"},
            {"word": "あらわす", "reading": "表す", "meaning": "v. 表现；表示", "pos": "動詞",
             "example": "言葉で表します。", "example_cn": "用语言表达。"},
            {"word": "あらわれる", "reading": "現れる", "meaning": "v. 出现", "pos": "動詞",
             "example": "月が現れました。", "example_cn": "月亮出现了。"},
            {"word": "ある", "reading": "在る", "meaning": "v. 在（有生命）", "pos": "動詞",
             "example": "庭に犬がいます。", "example_cn": "院子里有狗。"},
            {"word": "あわ", "reading": "泡", "meaning": "n. 泡沫", "pos": "名詞",
             "example": "口に泡が立ちます。", "example_cn": "嘴上有泡沫。"},
            {"word": "あわてる", "reading": "慌てる", "meaning": "v. 慌张", "pos": "動詞",
             "example": "慌てないでください。", "example_cn": "请不要慌张。"},
            {"word": "あんしん", "reading": "安心", "meaning": "n. 安心", "pos": "名詞",
             "example": "安心しました。", "example_cn": "放心了。"},
            {"word": "あんてい", "reading": "安定", "meaning": "n. 稳定", "pos": "名詞",
             "example": "生活が安定しました。", "example_cn": "生活稳定了。"},
            {"word": "あんない", "reading": "案内", "meaning": "n. 向导；指南", "pos": "名詞",
             "example": "駅の案内をします。", "example_cn": "在车站做向导。"},
            {"word": "あんぜん", "reading": "安全", "meaning": "n. 安全", "pos": "名詞",
             "example": "安全に気をつけてください。", "example_cn": "请注意安全。"},
            {"word": "い", "reading": "胃", "meaning": "n. 胃", "pos": "名詞",
             "example": "胃が痛いです。", "example_cn": "胃疼。"},
            {"word": "いう", "reading": "言う", "meaning": "v. 说；叫做", "pos": "動詞",
             "example": "田中と言います。", "example_cn": "叫田中。"},
            {"word": "いえ", "reading": "家", "meaning": "n. 家；房子", "pos": "名詞",
             "example": "家を買いました。", "example_cn": "买了房子。"},
            {"word": "いか", "reading": "以下", "meaning": "n. 以下", "pos": "名詞",
             "example": "18歳以下の人は入れません。", "example_cn": "18岁以下的人不能进。"},
            {"word": "いがい", "reading": "以外", "meaning": "n. 以外", "pos": "名詞",
             "example": "日曜以外は仕事です。", "example_cn": "除了周日都工作。"},
            {"word": "いかす", "reading": "生かす", "meaning": "v. 弄活；利用", "pos": "動詞",
             "example": "経験を生かします。", "example_cn": "利用经验。"},
            {"word": "いかり", "reading": "錨", "meaning": "n. 锚", "pos": "名詞",
             "example": "錨を下ろします。", "example_cn": "下锚。"},
            {"word": "いき", "reading": "息", "meaning": "n. 呼吸", "pos": "名詞",
             "example": "息を吸います。", "example_cn": "吸气。"},
            {"word": "いきおい", "reading": "勢い", "meaning": "n. 势头", "pos": "名詞",
             "example": "勢いがあります。", "example_cn": "有势头。"},
            {"word": "いきなり", "reading": "", "meaning": "adv. 突然", "pos": "副詞",
             "example": "いきなり来ました。", "example_cn": "突然来了。"},
            {"word": "いくじ", "reading": "育児", "meaning": "n. 育儿", "pos": "名詞",
             "example": "育児が大変です。", "example_cn": "育儿很辛苦。"},
            {"word": "いけん", "reading": "意思", "meaning": "n. 意思", "pos": "名詞",
             "example": "意思を伝えます。", "example_cn": "传达意思。"},
            {"word": "いしき", "reading": "意識", "meaning": "n. 意识", "pos": "名詞",
             "example": "意識がありません。", "example_cn": "没有意识。"},
            {"word": "いし", "reading": "意思", "meaning": "n. 意思", "pos": "名詞",
             "example": "意思が通じません。", "example_cn": "意思不通。"},
            {"word": "いしつ", "reading": "衣食", "meaning": "n. 衣食", "pos": "名詞",
             "example": "衣食住に困っています。", "example_cn": "衣食住有困难。"},
            {"word": "いじゅう", "reading": "衣食住", "meaning": "n. 衣食住", "pos": "名詞",
             "example": "衣食住が大切です。", "example_cn": "衣食住很重要。"},
            {"word": "いじ", "reading": "意地", "meaning": "n. 意气；固执", "pos": "名詞",
             "example": "意地を張ります。", "example_cn": "固执己见。"},
            {"word": "いじょう", "reading": "以上", "meaning": "n. 以上", "pos": "名詞",
             "example": "100人以上が集まりました。", "example_cn": "聚集了100人以上。"},
            {"word": "いじょうに", "reading": "以上に", "meaning": "adv. 非常；很", "pos": "副詞",
             "example": "以上に寒いです。", "example_cn": "非常冷。"},
            {"word": "いす", "reading": "椅子", "meaning": "n. 椅子", "pos": "名詞",
             "example": "椅子に座ります。", "example_cn": "坐在椅子上。"},
            {"word": "いぜん", "reading": "以前", "meaning": "n. 以前", "pos": "名詞",
             "example": "以前は良かったです。", "example_cn": "以前挺好的。"},
            {"word": "いそがしい", "reading": "忙しい", "meaning": "adj. 忙的", "pos": "形容詞",
             "example": "忙しい日です。", "example_cn": "忙碌的一天。"},
            {"word": "いたい", "reading": "痛い", "meaning": "adj. 疼的", "pos": "形容詞",
             "example": "頭が痛いです。", "example_cn": "头疼。"},
            {"word": "いただく", "reading": "頂く", "meaning": "v. 收下；吃", "pos": "動詞",
             "example": "いただきます。", "example_cn": "我开动了。"},
            {"word": "いただきます", "reading": "頂きます", "meaning": "expression. 我开动了", "pos": "表現",
             "example": "いただきます。", "example_cn": "我开动了。"},
            {"word": "いち", "reading": "一", "meaning": "num. 一", "pos": "数詞",
             "example": "一つください。", "example_cn": "请给我一个。"},
            {"word": "いちおう", "reading": "一応", "meaning": "adv. 姑且；大致", "pos": "副詞",
             "example": "一応見ておきます。", "example_cn": "姑且先看看。"},
            {"word": "いちじ", "reading": "一時", "meaning": "n. 一点；暂时", "pos": "名詞",
             "example": "一時帰ります。", "example_cn": "暂时回去。"},
            {"word": "いちだい", "reading": "一代", "meaning": "n. 一代", "pos": "名詞",
             "example": "一代の英雄です。", "example_cn": "一代英雄。"},
            {"word": "いちど", "reading": "一度", "meaning": "n. 一次；一回", "pos": "名詞",
             "example": "一度行ってみたいです。", "example_cn": "想去一次。"},
            {"word": "いちばん", "reading": "一番", "meaning": "n. 最；第一", "pos": "名詞",
             "example": "一番好きです。", "example_cn": "最喜欢。"},
            {"word": "いちめん", "reading": "一面", "meaning": "n. 一面；另一方面", "pos": "名詞",
             "example": "一面から見ます。", "example_cn": "从一面看。"},
            {"word": "いちりつ", "reading": "一律", "meaning": "n. 一律", "pos": "名詞",
             "example": "一律に処理します。", "example_cn": "一律处理。"},
            {"word": "いちれん", "reading": "一連", "meaning": "n. 一系列", "pos": "名詞",
             "example": "一連の出来事です。", "example_cn": "一系列事件。"},
            {"word": "いつか", "reading": "", "meaning": "adv. 总有一天", "pos": "副詞",
             "example": "いつか会えます。", "example_cn": "总有一天能见面。"},
            {"word": "いつ", "reading": "", "meaning": "pron. 什么时候", "pos": "代詞",
             "example": "いつ来ますか？", "example_cn": "什么时候来？"},
            {"word": "いっか", "reading": "一家", "meaning": "n. 一家；全家", "pos": "名詞",
             "example": "一家団欒です。", "example_cn": "一家团圆。"},
            {"word": "いっけん", "reading": "一見", "meaning": "n. 一看；乍一看", "pos": "名詞",
             "example": "一見難しそうです。", "example_cn": "乍一看很难。"},
            {"word": "いっこく", "reading": "一刻", "meaning": "n. 一刻", "pos": "名詞",
             "example": "一刻も早く行きます。", "example_cn": "尽快去。"},
            {"word": "いっしょ", "reading": "一緒", "meaning": "n. 一起", "pos": "名詞",
             "example": "一緒に行きましょう。", "example_cn": "一起去吧。"},
            {"word": "いっしょう", "reading": "一生", "meaning": "n. 一生", "pos": "名詞",
             "example": "一生忘れません。", "example_cn": "一生不会忘记。"},
            {"word": "いったい", "reading": "一体", "meaning": "adv. 到底；究竟", "pos": "副詞",
             "example": "一体どうしたの？", "example_cn": "到底怎么了？"},
            {"word": "いったん", "reading": "一旦", "meaning": "adv. 暂且；一旦", "pos": "副詞",
             "example": "一旦帰ります。", "example_cn": "暂且回去。"},
            {"word": "いつつ", "reading": "五つ", "meaning": "num. 五个", "pos": "数詞",
             "example": "リンゴを五つ買いました。", "example_cn": "买了五个苹果。"},
            {"word": "いつぱい", "reading": "一杯", "meaning": "n. 满；满", "pos": "名詞",
             "example": "お腹がいっぱいです。", "example_cn": "肚子饱了。"},
            {"word": "いどう", "reading": "移動", "meaning": "n. 移动", "pos": "名詞",
             "example": "移動が不便です。", "example_cn": "移动不方便。"},
            {"word": "いない", "reading": "居ない", "meaning": "v. 不在", "pos": "動詞",
             "example": "部屋には誰もいません。", "example_cn": "房间里没有人。"},
            {"word": "いなか", "reading": "田舎", "meaning": "n. 乡下", "pos": "名詞",
             "example": "田舎で育ちました。", "example_cn": "在乡下长大。"},
            {"word": "いぬ", "reading": "犬", "meaning": "n. 狗", "pos": "名詞",
             "example": "犬を飼っています。", "example_cn": "养狗。"},
            {"word": "いのる", "reading": "祈る", "meaning": "v. 祈祷", "pos": "動詞",
             "example": "健康を祈ります。", "example_cn": "祈祷健康。"},
            {"word": "いま", "reading": "今", "meaning": "n. 现在", "pos": "名詞",
             "example": "今何時ですか？", "example_cn": "现在几点？"},
            {"word": "いみ", "reading": "意味", "meaning": "n. 意思", "pos": "名詞",
             "example": "意味が分かりません。", "example_cn": "不懂意思。"},
            {"word": "いもうと", "reading": "妹", "meaning": "n. 妹妹", "pos": "名詞",
             "example": "妹は大学生です。", "example_cn": "妹妹是大学生。"},
            {"word": "いや", "reading": "嫌", "meaning": "adj. 讨厌的", "pos": "形容詞",
             "example": "いやな予感です。", "example_cn": "讨厌的预感。"},
            {"word": "いやがる", "reading": "嫌がる", "meaning": "v. 讨厌", "pos": "動詞",
             "example": "子供が嫌がっています。", "example_cn": "孩子讨厌。"},
            {"word": "いやしい", "reading": "卑しい", "meaning": "adj. 卑鄙的", "pos": "形容詞",
             "example": "卑しい考えです。", "example_cn": "卑鄙的想法。"},
            {"word": "いよいよ", "reading": "", "meaning": "adv. 越来越", "pos": "副詞",
             "example": "いよいよ寒くなります。", "example_cn": "越来越冷。"},
            {"word": "いらっしゃる", "reading": "", "meaning": "v. 来；在（敬语）", "pos": "動詞",
             "example": "いらっしゃいますか？", "example_cn": "您在吗？"},
            {"word": "いる", "reading": "居る", "meaning": "v. 在（有生命）", "pos": "動詞",
             "example": "猫がいます。", "example_cn": "有猫。"},
            {"word": "いれかえる", "reading": "入れ替える", "meaning": "v. 更换", "pos": "動詞",
             "example": "電球を入れ替えます。", "example_cn": "更换灯泡。"},
            {"word": "いれる", "reading": "入れる", "meaning": "v. 放入；加入", "pos": "動詞",
             "example": "お茶を入れます。", "example_cn": "泡茶。"},
            {"word": "いろ", "reading": "色", "meaning": "n. 颜色", "pos": "名詞",
             "example": "色がきれいです。", "example_cn": "颜色很漂亮。"},
            {"word": "いろいろ", "reading": "色々", "meaning": "adj. 各种各样", "pos": "形容詞",
             "example": "色々な人と話しました。", "example_cn": "和各色人等交谈了。"},
            {"word": "いわい", "reading": "祝い", "meaning": "n. 庆祝；贺礼", "pos": "名詞",
             "example": "誕生日の祝いをします。", "example_cn": "庆祝生日。"},
            {"word": "いわう", "reading": "祝う", "meaning": "v. 庆祝", "pos": "動詞",
             "example": "成功を祝います。", "example_cn": "庆祝成功。"},
        ]
        
        if level == "N5":
            return n5_words
        elif level == "N4":
            return n5_words + n4_words
        else:
            return n5_words
    
    # ==================== 语法内容 ====================
    
    def add_grammar_content(self, language: str, level: str) -> int:
        """添加语法学习内容"""
        print(f"添加 {language} {level} 语法内容...")
        
        if language == "english":
            grammar_list = self._get_english_grammar(level)
        else:
            grammar_list = self._get_japanese_grammar(level)
        
        count = 0
        for g in grammar_list:
            result = self.db.add_grammar(
                name=g['name'],
                pattern=g['pattern'],
                explanation=g['explanation'],
                examples=g['examples'],
                language=language,
                level=level
            )
            if result > 0:
                count += 1
        
        print(f"成功添加 {count} 个语法点")
        return count
    
    def _get_english_grammar(self, level: str) -> List[Dict]:
        """获取英语语法内容"""
        cet4_grammar = [
            {
                "name": "一般现在时",
                "pattern": "主语 + 动词原形 (第三人称加s)",
                "explanation": "表示经常性或习惯性动作，客观事实或真理。",
                "examples": [
                    "I study English every day. 我每天学英语。",
                    "The sun rises in the east. 太阳从东方升起。",
                    "She works in a hospital. 她在医院工作。"
                ]
            },
            {
                "name": "现在进行时",
                "pattern": "主语 + am/is/are + 动词-ing",
                "explanation": "表示说话时正在进行的动作。",
                "examples": [
                    "I am reading a book. 我正在读书。",
                    "They are playing football. 他们正在踢足球。",
                    "She is cooking dinner. 她正在做晚饭。"
                ]
            },
            {
                "name": "一般过去时",
                "pattern": "主语 + 动词过去式",
                "explanation": "表示过去某个时间发生的动作或存在的状态。",
                "examples": [
                    "I went to Beijing last year. 我去年去了北京。",
                    "She visited her grandparents. 她看望了她的祖父母。",
                    "We had a party yesterday. 我们昨天开了派对。"
                ]
            },
            {
                "name": "现在完成时",
                "pattern": "主语 + have/has + 过去分词",
                "explanation": "表示过去发生的动作对现在的影响或结果。",
                "examples": [
                    "I have finished my homework. 我已经完成了作业。",
                    "She has lived here for five years. 她在这里住了五年了。",
                    "Have you ever been to Japan? 你去过日本吗？"
                ]
            },
            {
                "name": "被动语态",
                "pattern": "主语 + be + 过去分词 (+ by 执行者)",
                "explanation": "当主语是动作的承受者时使用被动语态。",
                "examples": [
                    "English is spoken worldwide. 英语在全世界被使用。",
                    "The book was written by him. 这本书是他写的。",
                    "The window was broken. 窗户被打破了。"
                ]
            },
        ]
        return cet4_grammar
    
    def _get_japanese_grammar(self, level: str) -> List[Dict]:
        """获取日语语法内容"""
        n5_grammar = [
            {
                "name": "です / である",
                "pattern": "名詞 + です",
                "explanation": "表示「是...」的意思，是最基本的判断句型。",
                "examples": [
                    "私は学生です。我是学生。",
                    "これは本です。这是书。",
                    "田中さんは先生です。田中先生是老师。"
                ]
            },
            {
                "name": "ます形",
                "pattern": "動詞ます形 + ます",
                "explanation": "动词的礼貌形式，用于正式场合。",
                "examples": [
                    "毎日、日本語を勉強します。每天学习日语。",
                    "私は朝6時に起きます。我早上6点起床。",
                    "本を読みます。读书。"
                ]
            },
            {
                "name": "助词「は」",
                "pattern": "主題 + は + 述語",
                "explanation": "提示句子的主题，相当于「关于...」。",
                "examples": [
                    "私は田中です。我是田中。",
                    "今日は天気がいいです。今天天气很好。",
                    "日本語は難しいです。日语很难。"
                ]
            },
            {
                "name": "助词「を」",
                "pattern": "目的語 + を + 動詞",
                "explanation": "标记动作的对象（宾语）。",
                "examples": [
                    "本を読みます。读书。",
                    "ご飯を食べます。吃饭。",
                    "音楽を聴きます。听音乐。"
                ]
            },
            {
                "name": "助词「に」",
                "pattern": "場所/時間 + に + 動詞",
                "explanation": "表示动作的目的地、时间点或存在位置。",
                "examples": [
                    "学校に行きます。去学校。",
                    "7時に起きます。7点起床。",
                    "部屋に本があります。房间里有书。"
                ]
            },
        ]
        return n5_grammar
    
    # ==================== 阅读内容 ====================
    
    def add_reading_content(self, language: str, level: str) -> int:
        """添加阅读内容"""
        print(f"添加 {language} {level} 阅读内容...")
        
        if language == "english":
            readings = self._get_english_readings(level)
        else:
            readings = self._get_japanese_readings(level)
        
        count = 0
        for r in readings:
            item = ContentItem(
                title=r['title'],
                body=r['body'],
                content_type='reading',
                language=language,
                level=level,
                source_url=r.get('source', 'internal')
            )
            result = self.db.add_content(item)
            if result > 0:
                count += 1
        
        print(f"成功添加 {count} 篇阅读内容")
        return count
    
    def _get_english_readings(self, level: str) -> List[Dict]:
        """获取英语阅读内容"""
        return [
            {
                "title": "My Daily Routine",
                "body": """My name is Li Ming. I am a university student in Beijing. Every day, I wake up at 6:30 in the morning.

After washing my face and brushing my teeth, I have breakfast at 7 o'clock. I usually eat bread and drink milk for breakfast.

I leave home at 7:30 and take the subway to school. It takes about 40 minutes. Classes begin at 8:30. I have four classes in the morning and two in the afternoon.

After school, I often go to the library to study or play basketball with my friends. I have dinner at 6 o'clock and then do my homework.

Before going to bed, I like to read books or listen to music. I usually go to bed at 11 o'clock.

**Vocabulary:**
- routine /ruːˈtiːn/ n. 日常
- subway /ˈsʌbweɪ/ n. 地铁
- library /ˈlaɪbrəri/ n. 图书馆"""
            },
            {
                "title": "The Internet Changes Our Life",
                "body": """The Internet has changed our lives in many ways. Today, we can do almost everything online.

**Online Shopping**
We can shop for clothes, books, and food without leaving home. Online shopping is very convenient, and we can compare prices easily.

**Social Media**
Social media is very popular among young people. They use apps like WeChat and Weibo to share their photos and stories with friends.

**Online Learning**
Many people also use the Internet for education. They can take online courses and learn new skills from home.

**Problems**
However, the Internet also has some problems. Some people spend too much time online and forget to exercise or meet friends in person. It's important to balance our online and offline life.

**Vocabulary:**
- social media 社交媒体
- popular /ˈpɒpjələ/ adj. 流行的
- balance /ˈbæləns/ v./n. 平衡"""
            },
            {
                "title": "Environmental Protection",
                "body": """Environmental protection is an important issue in today's world. Our planet faces many challenges, including air pollution, water pollution, and climate change.

**What Can We Do?**

1. **Reduce waste**
   We should use less plastic and recycle more. Bring your own bags when shopping.

2. **Save energy**
   Turn off lights when leaving a room. Use public transportation instead of driving.

3. **Plant trees**
   Trees absorb carbon dioxide and produce oxygen. They are essential for our environment.

4. **Protect wildlife**
   Many animals are endangered. We should protect their habitats and stop illegal hunting.

**Everyone's Responsibility**
Environmental protection is not just the government's job. Everyone can make a difference. Small actions add up to big changes.

Let's work together to protect our beautiful planet!

**Vocabulary:**
- environmental /ɪnˌvaɪrənˈmentl/ adj. 环境的
- pollution /pəˈluːʃn/ n. 污染  
- climate change 气候变化"""
            }
        ]
    
    def _get_japanese_readings(self, level: str) -> List[Dict]:
        """获取日语阅读内容"""
        return [
            {
                "title": "私の一日",
                "body": """私は大学生です。毎日、朝6時半に起きます。

顔を洗って、歯を磨いてから、朝ごはんを食べます。朝ごはんはパンと牛乳です。

7時半に家を出て、電車で学校に行きます。学校まで40分ぐらいかかります。

授業は9時から始まります。午前中は3つの授業があります。お昼は学校の食堂で友達と一緒に食べます。

午後は2つの授業があります。授業が終わってから、図書館で勉強したり、友達とバスケットボールをしたりします。

夜7時ごろ家に帰ります。晩ごはんの後で、宿題をしたり、本を読んだりします。

11時ごろ寝ます。

**単語：**
- 磨く（みがく）刷牙
- 食堂（しょくどう）食堂
- 図書館（としょかん）图书馆"""
            },
            {
                "title": "私の家族",
                "body": """私の家族を紹介します。私の家族は5人です。

**父**
父は会社員です。毎日、電車で会社に行きます。趣味はゴルフです。週末によくゴルフをします。

**母**
母は先生です。小学校で英語を教えています。料理がとても上手です。

**兄**
兄は大学生です。東京の大学で勉強しています。今は一人で東京に住んでいます。

**妹**
妹は高校生です。音楽が大好きで、毎日ピアノを弾いています。将来の夢はピアニストになることです。

**家族との時間**
私たちは週末によく一緒に出かけます。映画を見たり、レストランで食事をしたりします。家族と一緒にいる時間が一番楽しいです。

**単語：**
- 紹介する（しょうかいする）介绍
- 会社員（かいしゃいん）公司职员
- 趣味（しゅみ）爱好"""
            },
            {
                "title": "日本の四季",
                "body": """日本には四つの季節があります。春、夏、秋、冬です。

**春（はる）3月〜5月**
春は暖かいです。桜がきれいです。多くの人が公園で花見をします。

**夏（なつ）6月〜8月**
夏は暑いです。海に行ったり、花火を見たりします。お盆休みがあります。

**秋（あき）9月〜11月**
秋は涼しいです。紅葉がきれいです。食べ物がおいしい季節です。

**冬（ふゆ）12月〜2月**
冬は寒いです。北の地方では雪がたくさん降ります。スキーやスノーボードができます。

日本の四季はとてもきれいで、外国人にも人気があります。

**単語：**
- 季節（きせつ）季节
- 桜（さくら）樱花
- 紅葉（こうよう）红叶
- 花見（はなみ）赏花"""
            }
        ]
    
    # ==================== 批量导入 ====================
    
    def populate_all_content(self, incremental: bool = True):
        """
        填充所有学习内容
        
        Args:
            incremental: 是否启用增量更新（默认True）
        """
        print("\n" + "=" * 50)
        print("开始填充学习内容数据库")
        if incremental and self.incremental_settings.get('enabled', True):
            print("(增量更新模式)")
        print("=" * 50 + "\n")
        
        total = 0
        
        # 加载已存在的词汇和内容，用于去重
        self._load_existing_content()
        
        # 英语内容
        print("\n【英语内容】")
        total += self.crawl_english_vocabulary("CET-4", incremental=incremental)
        total += self.crawl_english_vocabulary("CET-6", incremental=incremental)
        total += self.add_grammar_content("english", "CET-4")
        total += self.add_reading_content("english", "CET-4")
        
        # 日语内容
        print("\n【日语内容】")
        total += self.crawl_japanese_vocabulary("N5", incremental=incremental)
        total += self.crawl_japanese_vocabulary("N4", incremental=incremental)
        total += self.add_grammar_content("japanese", "N5")
        total += self.add_reading_content("japanese", "N5")
        
        self.last_crawl_time = datetime.now()
        
        print("\n" + "=" * 50)
        print(f"内容填充完成！共添加 {total} 条记录")
        print("=" * 50)
        
        # 显示统计
        stats = {
            "english_vocab": self.db.get_vocabulary_count("english"),
            "japanese_vocab": self.db.get_vocabulary_count("japanese"),
        }
        print(f"\n📊 数据库统计：")
        print(f"   英语词汇：{stats['english_vocab']} 个")
        print(f"   日语词汇：{stats['japanese_vocab']} 个")
        
        self.print_statistics()
        
        return total
    
    def _load_config(self, config_path: Optional[str] = None) -> dict:
        """加载爬虫配置"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "content" / "crawler_config.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            "crawler_settings": {
                "timeout": 30,
                "max_attempts": 3,
                "min_delay": 1.0,
                "max_delay": 3.0
            },
            "incremental_update_settings": {
                "enabled": True,
                "check_last_modified": True,
                "update_mode": "smart",
                "max_age_days": 30,
                "batch_size": 100
            }
        }
    
    def _load_vocabulary_sources(self) -> dict:
        """
        加载词汇源配置
        
        Returns:
            词汇源配置字典
        """
        vocab_config_path = Path(__file__).parent.parent.parent / "vocabulary_sources.json"
        
        try:
            with open(vocab_config_path, 'r', encoding='utf-8') as f:
                sources = json.load(f)
                print(f"✓ 成功加载词汇源配置: {vocab_config_path}")
                return sources
        except FileNotFoundError:
            print(f"✗ 词汇源配置文件不存在: {vocab_config_path}")
            print("  将使用内置词汇库")
            return {}
        except json.JSONDecodeError as e:
            print(f"✗ 词汇源配置文件格式错误: {e}")
            print("  将使用内置词汇库")
            return {}
        except Exception as e:
            print(f"✗ 加载词汇源配置失败: {e}")
            print("  将使用内置词汇库")
            return {}
    
    def _load_existing_content(self):
        """加载已存在的词汇和内容，用于增量更新和去重"""
        try:
            if hasattr(self.db, 'conn'):
                cursor = self.db.conn.cursor()
                
                # 加载已存在的词汇
                cursor.execute("SELECT DISTINCT word FROM vocabulary WHERE language = 'english'")
                self.crawled_words.update(row[0] for row in cursor.fetchall())
                
                cursor.execute("SELECT DISTINCT word FROM vocabulary WHERE language = 'japanese'")
                self.crawled_words.update(row[0] for row in cursor.fetchall())
                
                # 加载已存在的内容URL
                cursor.execute("SELECT DISTINCT source_url FROM content")
                self.crawled_contents.update(row[0] for row in cursor.fetchall() if row[0])
                
                print(f"已加载 {len(self.crawled_words)} 个词汇，{len(self.crawled_contents)} 个内容记录用于去重")
        except Exception as e:
            print(f"加载已存在内容时出错: {e}")
    
    def _is_duplicate_vocabulary(self, word: str, language: str) -> bool:
        """检查词汇是否已存在"""
        if word in self.crawled_words:
            return True
        
        if hasattr(self.db, 'conn'):
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM vocabulary WHERE word = ? AND language = ?",
                (word, language)
            )
            count = cursor.fetchone()[0]
            if count > 0:
                self.crawled_words.add(word)
                return True
        
        return False
    
    def _is_duplicate_content(self, source_url: str) -> bool:
        """检查内容URL是否已存在"""
        if source_url in self.crawled_contents:
            return True
        
        if hasattr(self.db, 'conn'):
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM content WHERE source_url = ?",
                (source_url,)
            )
            count = cursor.fetchone()[0]
            if count > 0:
                self.crawled_contents.add(source_url)
                return True
        
        return False
    
    def crawl_english_vocabulary(self, level: str = "CET-4", incremental: bool = True) -> int:
        """
        爬取英语词汇
        
        Args:
            level: 词汇级别
            incremental: 是否启用增量更新（跳过已存在的词汇）
        """
        print(f"开始爬取 {level} 英语词汇{'（增量更新）' if incremental else ''}...")
        
        vocabulary = self._get_cet_vocabulary(level)
        
        items = []
        skipped = 0
        
        for word_data in vocabulary:
            word = word_data['word']
            
            # 增量更新：跳过已存在的词汇
            if incremental and self._is_duplicate_vocabulary(word, 'english'):
                skipped += 1
                continue
            
            item = VocabularyItem(
                word=word_data['word'],
                reading=word_data.get('phonetic', ''),
                meaning=word_data['meaning'],
                example_sentence=word_data.get('example', ''),
                example_translation=word_data.get('example_cn', ''),
                language='english',
                level=level,
                category=word_data.get('pos', ''),
                tags=level.lower()
            )
            items.append(item)
            self.crawled_words.add(word)
        
        if items:
            count = self.db.add_vocabulary_batch(items)
            self.stats.record_success()
        else:
            count = 0
            if skipped > 0:
                print(f"   跳过 {skipped} 个已存在的词汇")
        
        print(f"成功添加 {count} 个 {level} 词汇")
        return count
    
    def crawl_japanese_vocabulary(self, level: str = "N5", incremental: bool = True) -> int:
        """
        爬取日语 JLPT 词汇
        
        Args:
            level: JLPT级别
            incremental: 是否启用增量更新（跳过已存在的词汇）
        """
        print(f"开始爬取 JLPT {level} 日语词汇{'（增量更新）' if incremental else ''}...")
        
        vocabulary = self._get_jlpt_vocabulary(level)
        
        items = []
        skipped = 0
        
        for word_data in vocabulary:
            word = word_data['word']
            
            # 增量更新：跳过已存在的词汇
            if incremental and self._is_duplicate_vocabulary(word, 'japanese'):
                skipped += 1
                continue
            
            item = VocabularyItem(
                word=word_data['word'],
                reading=word_data.get('reading', ''),
                meaning=word_data['meaning'],
                example_sentence=word_data.get('example', ''),
                example_translation=word_data.get('example_cn', ''),
                language='japanese',
                level=level,
                category=word_data.get('pos', ''),
                tags=level.lower()
            )
            items.append(item)
            self.crawled_words.add(word)
        
        if items:
            count = self.db.add_vocabulary_batch(items)
            self.stats.record_success()
        else:
            count = 0
            if skipped > 0:
                print(f"   跳过 {skipped} 个已存在的词汇")
        
        print(f"成功添加 {count} 个 JLPT {level} 词汇")
        return count
    
    def get_statistics(self) -> Dict:
        """获取爬虫统计信息"""
        return self.stats.get_summary()
    
    def print_statistics(self):
        """打印爬虫统计信息"""
        self.stats.print_summary()
    
    def close(self):
        """关闭资源"""
        self.requester.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def init_learning_database(incremental: bool = True):
    """
    初始化并填充学习数据库
    
    Args:
        incremental: 是否启用增量更新（默认True）
    """
    crawler = RealContentCrawler()
    crawler.populate_all_content(incremental=incremental)
    return crawler.db


if __name__ == "__main__":
    # 直接运行时填充数据库
    init_learning_database(incremental=True)
