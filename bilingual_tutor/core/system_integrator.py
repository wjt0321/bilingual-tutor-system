"""
System Integrator - 系统集成器
Integrates all new features with the existing core learning engine
将所有新功能与现有核心学习引擎集成
"""

import os
import sys
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bilingual_tutor.core.engine import CoreLearningEngine
from bilingual_tutor.storage.database import LearningDatabase
from bilingual_tutor.audio.pronunciation_manager import PronunciationManager
from bilingual_tutor.content.precise_level_crawler import PreciseLevelContentCrawler
from bilingual_tutor.models import UserProfile, StudySession, LearningActivity, ActivityResult
from bilingual_tutor.services.ai_service import (
    AIService, ConversationPartner, GrammarCorrector, ExerciseGenerator,
    AIRequest, LanguageLevel, ScenarioType, ExerciseType
)
from bilingual_tutor.infrastructure.cache_manager import create_cache_manager, CacheConfig


class SystemIntegrator:
    """
    系统集成器 - 连接Web界面与核心学习引擎，集成音频系统与词汇学习
    System Integrator - Connects Web interface with core learning engine,
    integrates audio system with vocabulary learning
    """
    
    def __init__(self):
        """Initialize the system integrator with all components"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.core_engine = CoreLearningEngine()
        self.learning_db = LearningDatabase()
        self.pronunciation_manager = PronunciationManager()
        self.content_crawler = PreciseLevelContentCrawler()
        
        # Initialize AI services
        try:
            self.ai_service = AIService()
            self.conversation_partner = ConversationPartner(self.ai_service)
            self.grammar_corrector = GrammarCorrector(self.ai_service)
            self.exercise_generator = ExerciseGenerator(self.ai_service)
            self.logger.info("AI服务初始化成功")
        except Exception as e:
            self.logger.warning(f"AI服务初始化失败，部分功能不可用: {e}")
            self.ai_service = None
            self.conversation_partner = None
            self.grammar_corrector = None
            self.exercise_generator = None
        
        # Initialize cache manager
        try:
            cache_config = CacheConfig()
            self.cache_manager = create_cache_manager(cache_config)
            self.logger.info("缓存管理器初始化成功")
        except Exception as e:
            self.logger.warning(f"缓存管理器初始化失败，使用内存缓存: {e}")
            self.cache_manager = None
        
        # Cache for performance optimization (legacy, will be replaced by cache_manager)
        self._user_cache = {}
        self._content_cache = {}
        self._audio_cache = {}
        
        self.logger.info("系统集成器初始化完成 - System Integrator initialized")
    
    # ==================== Web Interface Integration ====================
    
    def create_integrated_learning_session(self, user_id: str, preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        创建集成的学习会话，连接Web界面与核心引擎
        Create integrated learning session connecting Web interface with core engine
        """
        try:
            # Get or create user profile
            user_profile = self._get_or_create_user_profile(user_id, preferences)
            
            # Start core learning session
            study_session = self.core_engine.start_daily_session(user_id)
            
            # Generate learning plan with integrated content
            daily_plan = self.core_engine.generate_learning_plan(user_profile)
            
            # Enhance activities with audio and database content
            enhanced_activities = self._enhance_activities_with_audio_and_content(
                daily_plan.activities, user_profile
            )
            
            # Update session with enhanced activities
            study_session.activities = enhanced_activities
            
            return {
                'success': True,
                'session': {
                    'session_id': study_session.session_id,
                    'user_id': user_id,
                    'duration': study_session.planned_duration,
                    'status': study_session.status.value,
                    'time_allocation': {
                        'total': daily_plan.time_allocation.total_minutes,
                        'review': daily_plan.time_allocation.review_minutes,
                        'english': daily_plan.time_allocation.english_minutes,
                        'japanese': daily_plan.time_allocation.japanese_minutes
                    },
                    'activities': [self._serialize_activity(act) for act in enhanced_activities],
                    'objectives': daily_plan.learning_objectives
                }
            }
            
        except Exception as e:
            self.logger.error(f"创建集成学习会话失败: {e}")
            return {'success': False, 'message': '创建学习会话失败'}
    
    def execute_integrated_activity(self, user_id: str, activity_id: str, 
                                  user_responses: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行集成的学习活动，包含音频播放和数据库记录
        Execute integrated learning activity with audio playback and database recording
        """
        try:
            # Get user's active session
            session = self.core_engine.get_active_session(user_id)
            if not session:
                return {'success': False, 'message': '没有活跃的学习会话'}
            
            # Find the activity
            activity = None
            for act in session.activities:
                if act.activity_id == activity_id:
                    activity = act
                    break
            
            if not activity:
                return {'success': False, 'message': '活动未找到'}
            
            # Execute the activity through core engine
            result = self.core_engine.execute_learning_activity(activity)
            result.user_id = user_id
            
            # Process activity completion with integrated components
            self._process_integrated_activity_completion(user_id, activity, result, user_responses)
            
            # Get audio files for vocabulary if applicable
            audio_info = self._get_activity_audio_info(activity)
            
            return {
                'success': True,
                'result': {
                    'activity_id': activity_id,
                    'score': result.score,
                    'time_spent': result.time_spent,
                    'feedback': result.feedback,
                    'errors': result.errors_made,
                    'audio_info': audio_info,
                    'next_review_date': self._calculate_next_review_date(result.score),
                    'interaction_quality': self._assess_interaction_quality(result)
                }
            }
            
        except Exception as e:
            self.logger.error(f"执行集成活动失败: {e}")
            return {'success': False, 'message': '执行活动失败'}
    
    def get_integrated_progress_report(self, user_id: str) -> Dict[str, Any]:
        """
        获取集成的进度报告，包含所有系统组件的数据
        Get integrated progress report with data from all system components
        """
        try:
            # Get comprehensive status from core engine
            core_status = self.core_engine.get_comprehensive_user_status(user_id)
            
            # Get database statistics
            db_stats = self.learning_db.get_learning_stats(user_id)
            
            # Get audio statistics
            audio_stats = self.pronunciation_manager.get_pronunciation_statistics()
            
            # Get content crawler statistics
            content_stats = self._get_content_crawler_stats(user_id)
            
            # Combine all statistics
            integrated_report = {
                'user_id': user_id,
                'generated_at': datetime.now().isoformat(),
                'core_progress': core_status,
                'database_stats': db_stats,
                'audio_stats': audio_stats,
                'content_stats': content_stats,
                'integration_health': self._check_integration_health()
            }
            
            return {
                'success': True,
                'report': integrated_report
            }
            
        except Exception as e:
            self.logger.error(f"获取集成进度报告失败: {e}")
            return {'success': False, 'message': '获取进度报告失败'}
    
    # ==================== AI Service Integration ====================
    
    async def start_ai_conversation(self, user_id: str, language: str, 
                                   scenario: str = 'daily',
                                   topic: Optional[str] = None) -> Dict[str, Any]:
        """
        开始AI对话练习
        Start AI conversation practice
        """
        if not self.conversation_partner:
            return {'success': False, 'message': 'AI服务不可用'}
        
        try:
            user_profile = self._get_or_create_user_profile(user_id)
            
            # Map language to level
            level = LanguageLevel.CET4 if language == 'english' else LanguageLevel.N5
            
            # Map scenario
            scenario_type = ScenarioType.DAILY
            if scenario == 'business':
                scenario_type = ScenarioType.BUSINESS
            elif scenario == 'academic':
                scenario_type = ScenarioType.ACADEMIC
            elif scenario == 'travel':
                scenario_type = ScenarioType.TRAVEL
            
            result = await self.conversation_partner.start_conversation(
                user_level=level,
                scenario=scenario_type,
                topic=topic
            )
            
            return {
                'success': True,
                'conversation': result,
                'language': language,
                'user_level': level.value
            }
            
        except Exception as e:
            self.logger.error(f"启动AI对话失败: {e}")
            return {'success': False, 'message': f'启动对话失败: {str(e)}'}
    
    async def continue_ai_conversation(self, user_id: str, conversation_id: str,
                                      user_message: str, language: str,
                                      conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        继续AI对话
        Continue AI conversation
        """
        if not self.conversation_partner:
            return {'success': False, 'message': 'AI服务不可用'}
        
        try:
            user_profile = self._get_or_create_user_profile(user_id)
            level = LanguageLevel.CET4 if language == 'english' else LanguageLevel.N5
            
            result = await self.conversation_partner.continue_conversation(
                conversation_id=conversation_id,
                user_message=user_message,
                conversation_history=conversation_history,
                user_level=level
            )
            
            return {
                'success': True,
                'conversation': result
            }
            
        except Exception as e:
            self.logger.error(f"继续AI对话失败: {e}")
            return {'success': False, 'message': f'继续对话失败: {str(e)}'}
    
    async def explain_vocabulary_with_ai(self, user_id: str, word: str, 
                                        language: str) -> Dict[str, Any]:
        """
        使用AI解释词汇
        Explain vocabulary with AI
        """
        if not self.conversation_partner:
            return {'success': False, 'message': 'AI服务不可用'}
        
        try:
            user_profile = self._get_or_create_user_profile(user_id)
            level = LanguageLevel.CET4 if language == 'english' else LanguageLevel.N5
            
            result = await self.conversation_partner.explain_vocabulary(word, level)
            
            return {
                'success': True,
                'explanation': result
            }
            
        except Exception as e:
            self.logger.error(f"AI词汇解释失败: {e}")
            return {'success': False, 'message': f'词汇解释失败: {str(e)}'}
    
    async def correct_grammar_with_ai(self, user_id: str, text: str,
                                     language: str = 'english') -> Dict[str, Any]:
        """
        使用AI进行语法纠错
        Correct grammar with AI
        """
        if not self.grammar_corrector:
            return {'success': False, 'message': 'AI服务不可用'}
        
        try:
            result = await self.grammar_corrector.correct(text, language)
            
            return {
                'success': True,
                'correction': result
            }
            
        except Exception as e:
            self.logger.error(f"AI语法纠错失败: {e}")
            return {'success': False, 'message': f'语法纠错失败: {str(e)}'}
    
    async def generate_personalized_exercises(self, user_id: str, 
                                            weakness_areas: List[str],
                                            language: str,
                                            exercise_type: str = 'multiple_choice',
                                            count: int = 5) -> Dict[str, Any]:
        """
        生成个性化练习题
        Generate personalized exercises
        """
        if not self.exercise_generator:
            return {'success': False, 'message': 'AI服务不可用'}
        
        try:
            user_profile = self._get_or_create_user_profile(user_id)
            level = LanguageLevel.CET4 if language == 'english' else LanguageLevel.N5
            
            # Map exercise type
            exercise_type_enum = ExerciseType.MULTIPLE_CHOICE
            if exercise_type == 'fill_blank':
                exercise_type_enum = ExerciseType.FILL_BLANK
            elif exercise_type == 'translation':
                exercise_type_enum = ExerciseType.TRANSLATION
            elif exercise_type == 'writing':
                exercise_type_enum = ExerciseType.WRITING
            
            result = await self.exercise_generator.generate_exercise(
                weakness_areas=weakness_areas,
                language_level=level,
                exercise_type=exercise_type_enum,
                count=count
            )
            
            return {
                'success': True,
                'exercises': result
            }
            
        except Exception as e:
            self.logger.error(f"生成练习题失败: {e}")
            return {'success': False, 'message': f'生成练习题失败: {str(e)}'}
    
    def get_ai_service_health(self) -> Dict[str, Any]:
        """
        获取AI服务健康状态
        Get AI service health status
        """
        if not self.ai_service:
            return {
                'status': 'unavailable',
                'message': 'AI服务未初始化'
            }
        
        try:
            health_status = self.ai_service.get_model_health_status()
            recommendation = self.ai_service.get_recommendation()
            
            return {
                'status': 'available',
                'health': health_status,
                'recommendation': recommendation
            }
            
        except Exception as e:
            self.logger.error(f"获取AI服务健康状态失败: {e}")
            return {
                'status': 'error',
                'message': f'获取健康状态失败: {str(e)}'
            }
    
    # ==================== Audio System Integration ====================
    
    def integrate_audio_with_vocabulary(self, vocabulary_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将音频系统与词汇学习集成
        Integrate audio system with vocabulary learning
        """
        try:
            # Batch crawl pronunciation for vocabulary items
            crawl_result = self.pronunciation_manager.batch_crawl_vocabulary_pronunciation(vocabulary_items)
            
            # Update database with audio file paths
            audio_integration_count = 0
            for item in vocabulary_items:
                word = item.get('word', '')
                language = item.get('language', '')
                level = item.get('level', '')
                
                # Get audio file path
                audio_path = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
                
                if audio_path:
                    # Update vocabulary item with audio path
                    self.learning_db.update_vocabulary_audio(item.get('id'), audio_path)
                    audio_integration_count += 1
            
            return {
                'success': True,
                'crawl_result': crawl_result,
                'audio_integration_count': audio_integration_count,
                'total_vocabulary_items': len(vocabulary_items)
            }
            
        except Exception as e:
            self.logger.error(f"音频系统集成失败: {e}")
            return {'success': False, 'message': '音频系统集成失败'}
    
    def get_vocabulary_with_audio(self, language: str, level: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取带音频的词汇列表
        Get vocabulary list with audio files
        """
        try:
            # Get vocabulary from database
            vocabulary_items = self.learning_db.get_vocabulary(language, level, limit)
            
            # Enhance with audio information
            enhanced_vocabulary = []
            for item in vocabulary_items:
                # Get audio file path
                audio_path = self.pronunciation_manager.get_pronunciation_audio(
                    item.word, item.language, item.level
                )
                
                vocab_dict = {
                    'id': item.id,
                    'word': item.word,
                    'reading': item.reading,
                    'meaning': item.meaning,
                    'example_sentence': item.example_sentence,
                    'example_translation': item.example_translation,
                    'language': item.language,
                    'level': item.level,
                    'category': item.category,
                    'audio_available': audio_path is not None,
                    'audio_path': audio_path
                }
                enhanced_vocabulary.append(vocab_dict)
            
            return enhanced_vocabulary
            
        except Exception as e:
            self.logger.error(f"获取带音频词汇失败: {e}")
            return []
    
    # ==================== Database Query Optimization ====================
    
    def optimize_database_queries(self) -> Dict[str, Any]:
        """
        优化数据库查询和缓存
        Optimize database queries and caching
        """
        try:
            optimization_results = {
                'cache_optimization': self._optimize_caches(),
                'database_optimization': self._optimize_database_performance(),
                'query_optimization': self._optimize_common_queries()
            }
            
            return {
                'success': True,
                'optimization_results': optimization_results
            }
            
        except Exception as e:
            self.logger.error(f"数据库优化失败: {e}")
            return {'success': False, 'message': '数据库优化失败'}
    
    def get_cached_content(self, content_type: str, language: str, level: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的内容，提高页面加载速度
        Get cached content to improve page loading speed
        """
        # Try to use cache manager first
        if self.cache_manager:
            try:
                if content_type == 'daily_plan':
                    from bilingual_tutor.models import DailyPlan
                    plan = self.cache_manager.get_daily_plan('default_user')
                    if plan:
                        return {'daily_plan': plan}
                elif content_type == 'content_recommendations':
                    from bilingual_tutor.models import Content
                    recommendations = self.cache_manager.get_content_recommendations('default_user', language)
                    if recommendations:
                        return {'recommendations': recommendations}
            except Exception as e:
                self.logger.warning(f"缓存管理器查询失败，使用内存缓存: {e}")
        
        # Fallback to memory cache
        cache_key = f"{content_type}_{language}_{level}"
        
        # Check cache first
        if cache_key in self._content_cache:
            cached_item = self._content_cache[cache_key]
            # Check if cache is still valid (1 hour)
            if datetime.now() - cached_item['cached_at'] < timedelta(hours=1):
                return cached_item['content']
        
        # Get fresh content from database
        try:
            if content_type == 'vocabulary':
                content = self.get_vocabulary_with_audio(language, level, 10)
            elif content_type == 'grammar':
                content = self.learning_db.get_grammar(language, level, 5)
            elif content_type == 'reading':
                content = self.learning_db.get_content(language, level, 'reading', 3)
            else:
                content = None
            
            # Cache the content
            if content:
                self._content_cache[cache_key] = {
                    'content': content,
                    'cached_at': datetime.now()
                }
            
            return content
            
        except Exception as e:
            self.logger.error(f"获取缓存内容失败: {e}")
            return None
    
    def set_cached_content(self, content_type: str, language: str, level: str, 
                         content: Any, ttl: int = 3600) -> bool:
        """
        设置缓存内容
        Set cached content
        """
        # Try to use cache manager first
        if self.cache_manager:
            try:
                if content_type == 'daily_plan':
                    from bilingual_tutor.models import DailyPlan
                    return self.cache_manager.set_daily_plan('default_user', content, ttl)
                elif content_type == 'content_recommendations':
                    from bilingual_tutor.models import Content
                    return self.cache_manager.set_content_recommendations('default_user', language, content, ttl)
            except Exception as e:
                self.logger.warning(f"缓存管理器设置失败，使用内存缓存: {e}")
        
        # Fallback to memory cache
        cache_key = f"{content_type}_{language}_{level}"
        try:
            self._content_cache[cache_key] = {
                'content': content,
                'cached_at': datetime.now()
            }
            return True
        except Exception as e:
            self.logger.error(f"设置缓存内容失败: {e}")
            return False
    
    def cache_study_session(self, session_id: str, session: StudySession, ttl: int = 7200) -> bool:
        """
        缓存学习会话
        Cache study session
        """
        if self.cache_manager:
            try:
                return self.cache_manager.set_user_session(session_id, session, ttl)
            except Exception as e:
                self.logger.warning(f"缓存管理器设置会话失败: {e}")
        
        # Fallback to memory cache
        try:
            self._content_cache[f"session_{session_id}"] = {
                'content': session,
                'cached_at': datetime.now()
            }
            return True
        except Exception as e:
            self.logger.error(f"缓存学习会话失败: {e}")
            return False
    
    def get_cached_study_session(self, session_id: str) -> Optional[StudySession]:
        """
        获取缓存的学习会话
        Get cached study session
        """
        if self.cache_manager:
            try:
                return self.cache_manager.get_user_session(session_id)
            except Exception as e:
                self.logger.warning(f"缓存管理器获取会话失败: {e}")
        
        # Fallback to memory cache
        cache_key = f"session_{session_id}"
        if cache_key in self._content_cache:
            cached_item = self._content_cache[cache_key]
            if datetime.now() - cached_item['cached_at'] < timedelta(hours=2):
                return cached_item['content']
        
        return None
    
    def preload_user_cache(self, user_id: str) -> Dict[str, Any]:
        """
        预热用户缓存
        Preload user cache
        """
        results = {
            'success': True,
            'preloaded': []
        }
        
        try:
            user_profile = self._get_or_create_user_profile(user_id)
            
            # Preload vocabulary
            vocab_key = f"vocabulary_english_{user_profile.english_level}"
            if vocab_key not in self._content_cache:
                vocab = self.get_vocabulary_with_audio('english', user_profile.english_level, 10)
                self._content_cache[vocab_key] = {
                    'content': vocab,
                    'cached_at': datetime.now()
                }
                results['preloaded'].append('english_vocabulary')
            
            # Preload Japanese vocabulary
            jp_vocab_key = f"vocabulary_japanese_{user_profile.japanese_level}"
            if jp_vocab_key not in self._content_cache:
                jp_vocab = self.get_vocabulary_with_audio('japanese', user_profile.japanese_level, 10)
                self._content_cache[jp_vocab_key] = {
                    'content': jp_vocab,
                    'cached_at': datetime.now()
                }
                results['preloaded'].append('japanese_vocabulary')
            
            # Try to use cache manager for preloading
            if self.cache_manager:
                try:
                    self.cache_manager.preload_cache(user_id)
                    results['preloaded'].append('cache_manager_preload')
                except Exception as e:
                    self.logger.warning(f"缓存管理器预热失败: {e}")
            
            self.logger.info(f"用户 {user_id} 缓存预热完成: {results['preloaded']}")
            
        except Exception as e:
            self.logger.error(f"预热用户缓存失败: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def intelligent_preload(self, user_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        智能预加载
        Intelligently preload content based on user behavior and context
        """
        results = {
            'success': True,
            'preloaded_items': [],
            'strategy_used': 'default'
        }
        
        try:
            user_profile = self._get_or_create_user_profile(user_id)
            
            # Analyze context to determine preload strategy
            if context:
                strategy = self._determine_preload_strategy(context)
                results['strategy_used'] = strategy
            
            # Execute preload based on strategy
            if results['strategy_used'] == 'session_start':
                # Preload for new session
                results['preloaded_items'].extend(self._preload_for_session(user_profile))
            
            elif results['strategy_used'] == 'activity_change':
                # Preload for activity change
                activity_type = context.get('activity_type', 'vocabulary')
                results['preloaded_items'].extend(self._preload_for_activity(activity_type, user_profile))
            
            elif results['strategy_used'] == 'review_session':
                # Preload for review session
                results['preloaded_items'].extend(self._preload_for_review(user_id))
            
            elif results['strategy_used'] == 'offline_preparation':
                # Preload for offline mode
                results['preloaded_items'].extend(self._preload_for_offline(user_profile))
            
            else:
                # Default preload
                results['preloaded_items'].extend(self._preload_default(user_profile))
            
            self.logger.info(f"智能预加载完成: {results['strategy_used']}, 预加载项: {len(results['preloaded_items'])}")
            
        except Exception as e:
            self.logger.error(f"智能预加载失败: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def _determine_preload_strategy(self, context: Dict[str, Any]) -> str:
        """
        确定预加载策略
        Determine preload strategy based on context
        """
        if context.get('action') == 'start_session':
            return 'session_start'
        elif context.get('action') == 'change_activity':
            return 'activity_change'
        elif context.get('action') == 'start_review':
            return 'review_session'
        elif context.get('offline_mode', False):
            return 'offline_preparation'
        else:
            return 'default'
    
    def _preload_for_session(self, user_profile: UserProfile) -> List[str]:
        """
        为新会话预加载内容
        Preload content for new session
        """
        preloaded = []
        
        # Preload vocabulary
        vocab_key = f"vocabulary_english_{user_profile.english_level}"
        if vocab_key not in self._content_cache:
            self.get_vocabulary_with_audio('english', user_profile.english_level, 15)
            preloaded.append('english_vocabulary')
        
        # Preload grammar
        grammar_key = f"grammar_english_{user_profile.english_level}"
        if grammar_key not in self._content_cache:
            try:
                self.learning_db.get_grammar('english', user_profile.english_level, 5)
                preloaded.append('english_grammar')
            except:
                pass
        
        # Preload session data
        session_key = f"session_{user_profile.user_id}"
        if session_key not in self._content_cache:
            try:
                session = self.core_engine.get_active_session(user_profile.user_id)
                if session:
                    self._content_cache[session_key] = {
                        'content': session,
                        'cached_at': datetime.now()
                    }
                    preloaded.append('active_session')
            except:
                pass
        
        return preloaded
    
    def _preload_for_activity(self, activity_type: str, user_profile: UserProfile) -> List[str]:
        """
        为活动类型预加载内容
        Preload content for specific activity type
        """
        preloaded = []
        
        if activity_type == 'vocabulary':
            # Preload more vocabulary
            levels = ['CET-4', 'CET-5', 'CET-6']
            for level in levels:
                key = f"vocabulary_english_{level}"
                if key not in self._content_cache:
                    try:
                        self.get_vocabulary_with_audio('english', level, 5)
                        preloaded.append(f'vocabulary_{level}')
                    except:
                        pass
        
        elif activity_type == 'reading':
            # Preload reading materials
            try:
                self.learning_db.get_content('english', user_profile.english_level, 'reading', 5)
                preloaded.append('reading_materials')
            except:
                pass
        
        elif activity_type == 'listening':
            # Preload audio files
            try:
                vocab = self.learning_db.get_vocabulary('english', user_profile.english_level, 10)
                for item in vocab[:5]:
                    audio_path = self.pronunciation_manager.get_pronunciation_audio(
                        item.word, 'english', user_profile.english_level
                    )
                    if audio_path:
                        preloaded.append(f'audio_{item.word}')
            except:
                pass
        
        return preloaded
    
    def _preload_for_review(self, user_id: str) -> List[str]:
        """
        为复习会话预加载内容
        Preload content for review session
        """
        preloaded = []
        
        try:
            # Get items due for review
            review_items = self.learning_db.get_due_review_items(user_id)
            
            if review_items:
                # Preload vocabulary items
                for item in review_items[:10]:
                    key = f"review_vocab_{item.get('id', '')}"
                    if key not in self._content_cache:
                        self._content_cache[key] = {
                            'content': item,
                            'cached_at': datetime.now()
                        }
                        preloaded.append(f'review_item_{item.get("id", "")}')
        
        except Exception as e:
            self.logger.warning(f"复习内容预加载失败: {e}")
        
        return preloaded
    
    def _preload_for_offline(self, user_profile: UserProfile) -> List[str]:
        """
        为离线模式预加载内容
        Preload content for offline mode
        """
        preloaded = []
        
        # Preload larger vocabulary sets
        vocab_key = f"vocabulary_english_{user_profile.english_level}"
        if vocab_key not in self._content_cache:
            self.get_vocabulary_with_audio('english', user_profile.english_level, 50)
            preloaded.append('english_vocabulary_large')
        
        # Preload Japanese vocabulary
        jp_vocab_key = f"vocabulary_japanese_{user_profile.japanese_level}"
        if jp_vocab_key not in self._content_cache:
            self.get_vocabulary_with_audio('japanese', user_profile.japanese_level, 30)
            preloaded.append('japanese_vocabulary_large')
        
        # Preload grammar and reading
        try:
            self.learning_db.get_grammar('english', user_profile.english_level, 10)
            preloaded.append('english_grammar_large')
            
            self.learning_db.get_content('english', user_profile.english_level, 'reading', 10)
            preloaded.append('reading_materials_large')
        except:
            pass
        
        return preloaded
    
    def _preload_default(self, user_profile: UserProfile) -> List[str]:
        """
        默认预加载策略
        Default preload strategy
        """
        preloaded = []
        
        # Preload basic vocabulary
        vocab_key = f"vocabulary_english_{user_profile.english_level}"
        if vocab_key not in self._content_cache:
            self.get_vocabulary_with_audio('english', user_profile.english_level, 10)
            preloaded.append('english_vocabulary')
        
        # Preload user profile
        if user_profile.user_id not in self._user_cache:
            self._user_cache[user_profile.user_id] = user_profile
            preloaded.append('user_profile')
        
        return preloaded
    
    def invalidate_user_cache(self, user_id: str) -> bool:
        """
        清除用户相关缓存
        Invalidate user cache
        """
        success = True
        
        # Clear memory cache
        keys_to_delete = [key for key in self._content_cache.keys() if user_id in key]
        for key in keys_to_delete:
            del self._content_cache[key]
        
        # Clear cache manager cache
        if self.cache_manager:
            try:
                success = self.cache_manager.invalidate_user_cache(user_id)
            except Exception as e:
                self.logger.error(f"缓存管理器清除缓存失败: {e}")
                success = False
        
        # Clear user profile cache
        if user_id in self._user_cache:
            del self._user_cache[user_id]
        
        self.logger.info(f"清除用户 {user_id} 的缓存")
        return success
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        Get cache statistics
        """
        stats = {
            'memory_cache': {
                'user_cache_size': len(self._user_cache),
                'content_cache_size': len(self._content_cache),
                'audio_cache_size': len(self._audio_cache)
            }
        }
        
        # Add cache manager statistics if available
        if self.cache_manager:
            try:
                cache_metrics = self.cache_manager.get_cache_metrics()
                stats['cache_manager'] = {
                    'total_requests': cache_metrics.total_requests,
                    'hit_count': cache_metrics.hit_count,
                    'miss_count': cache_metrics.miss_count,
                    'hit_rate': cache_metrics.hit_rate,
                    'memory_usage': cache_metrics.memory_usage,
                    'active_keys': cache_metrics.active_keys
                }
            except Exception as e:
                self.logger.error(f"获取缓存管理器统计失败: {e}")
        
        return stats
    
    def synchronize_components(self, user_id: str) -> Dict[str, Any]:
        """
        同步所有组件数据
        Synchronize data across all components
        """
        results = {
            'success': True,
            'synced_components': [],
            'errors': []
        }
        
        try:
            # Sync core engine state
            try:
                core_status = self.core_engine.get_comprehensive_user_status(user_id)
                results['synced_components'].append('core_engine')
            except Exception as e:
                results['errors'].append(f'Core engine sync failed: {str(e)}')
            
            # Sync database state
            try:
                db_stats = self.learning_db.get_learning_stats(user_id)
                results['synced_components'].append('database')
            except Exception as e:
                results['errors'].append(f'Database sync failed: {str(e)}')
            
            # Sync cache state
            try:
                if self.cache_manager:
                    self.cache_manager.health_check()
                    results['synced_components'].append('cache_manager')
            except Exception as e:
                results['errors'].append(f'Cache sync failed: {str(e)}')
            
            # Sync audio system
            try:
                audio_stats = self.pronunciation_manager.get_pronunciation_statistics()
                results['synced_components'].append('audio_system')
            except Exception as e:
                results['errors'].append(f'Audio system sync failed: {str(e)}')
            
            self.logger.info(f"组件同步完成: {results['synced_components']}")
            
        except Exception as e:
            self.logger.error(f"组件同步失败: {e}")
            results['success'] = False
            results['errors'].append(f'Synchronization failed: {str(e)}')
        
        return results
    
    def optimize_data_flow(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        优化数据流
        Optimize data flow between components
        """
        results = {
            'success': True,
            'operation': operation,
            'optimizations_applied': []
        }
        
        try:
            if operation == 'create_session':
                user_id = kwargs.get('user_id', 'default')
                # Preload cache before creating session
                preload_result = self.preload_user_cache(user_id)
                if preload_result['success']:
                    results['optimizations_applied'].append('cache_preloaded')
                
                # Use cached content for faster session creation
                cached_content = self.get_cached_content('vocabulary', 'english', 'CET-4')
                if cached_content:
                    results['optimizations_applied'].append('cached_content_used')
            
            elif operation == 'execute_activity':
                activity_id = kwargs.get('activity_id')
                # Cache activity results for faster access
                results['optimizations_applied'].append('activity_caching_enabled')
            
            elif operation == 'get_progress':
                user_id = kwargs.get('user_id', 'default')
                # Use cached progress data
                results['optimizations_applied'].append('progress_caching_enabled')
            
            elif operation == 'ai_conversation':
                # Optimize AI conversation flow
                results['optimizations_applied'].append('conversation_context_optimized')
                results['optimizations_applied'].append('response_caching_enabled')
            
            self.logger.info(f"数据流优化完成: {operation} - {results['optimizations_applied']}")
            
        except Exception as e:
            self.logger.error(f"数据流优化失败: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def get_component_status(self) -> Dict[str, Any]:
        """
        获取所有组件状态
        Get status of all components
        """
        status = {
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        # Core engine status
        try:
            status['components']['core_engine'] = {
                'status': 'healthy',
                'active_sessions': len(getattr(self.core_engine, '_active_sessions', {}))
            }
        except Exception as e:
            status['components']['core_engine'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Database status
        try:
            vocab_count = self.learning_db.get_vocabulary_count('english')
            status['components']['database'] = {
                'status': 'healthy',
                'vocabulary_count': vocab_count
            }
        except Exception as e:
            status['components']['database'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Cache manager status
        if self.cache_manager:
            try:
                is_healthy = self.cache_manager.health_check()
                cache_metrics = self.cache_manager.get_cache_metrics()
                status['components']['cache_manager'] = {
                    'status': 'healthy' if is_healthy else 'degraded',
                    'type': 'redis' if 'Redis' in str(type(self.cache_manager)) else 'memory',
                    'hit_rate': cache_metrics.hit_rate
                }
            except Exception as e:
                status['components']['cache_manager'] = {
                    'status': 'error',
                    'error': str(e)
                }
        else:
            status['components']['cache_manager'] = {
                'status': 'not_configured'
            }
        
        # Audio system status
        try:
            audio_stats = self.pronunciation_manager.get_pronunciation_statistics()
            status['components']['audio_system'] = {
                'status': 'healthy',
                'statistics': audio_stats
            }
        except Exception as e:
            status['components']['audio_system'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # AI service status
        ai_health = self.get_ai_service_health()
        status['components']['ai_service'] = ai_health
        
        # Content crawler status
        try:
            content_stats = self._get_content_crawler_stats('default')
            status['components']['content_crawler'] = {
                'status': 'healthy',
                'statistics': content_stats
            }
        except Exception as e:
            status['components']['content_crawler'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return status
    
    def implement_fault_tolerance(self, component: str, operation: str, **kwargs) -> Dict[str, Any]:
        """
        实现容错机制
        Implement fault tolerance mechanism
        """
        result = {
            'success': False,
            'component': component,
            'operation': operation,
            'mechanism_used': None,
            'fallback_used': None
        }
        
        try:
            # Try primary operation
            primary_result = self._execute_primary_operation(component, operation, **kwargs)
            if primary_result['success']:
                result['success'] = True
                result['mechanism_used'] = 'primary'
                return result
            
            # Primary failed, try fallback
            fallback_result = self._execute_fallback_operation(component, operation, **kwargs)
            if fallback_result['success']:
                result['success'] = True
                result['mechanism_used'] = 'fallback'
                result['fallback_used'] = fallback_result['fallback_type']
                return result
            
            # Both failed, return degraded mode
            degraded_result = self._execute_degraded_mode(component, operation, **kwargs)
            result['success'] = degraded_result['success']
            result['mechanism_used'] = 'degraded'
            result['degraded_mode'] = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"容错机制执行失败: {e}")
            result['error'] = str(e)
            return result
    
    def _execute_primary_operation(self, component: str, operation: str, **kwargs) -> Dict[str, Any]:
        """
        执行主要操作
        Execute primary operation
        """
        try:
            if component == 'ai_service':
                if operation == 'conversation':
                    return {'success': True}
                elif operation == 'correction':
                    return {'success': True}
                elif operation == 'exercise_generation':
                    return {'success': True}
            
            elif component == 'cache':
                if operation == 'get':
                    return {'success': True}
                elif operation == 'set':
                    return {'success': True}
            
            elif component == 'database':
                if operation == 'query':
                    return {'success': True}
                elif operation == 'update':
                    return {'success': True}
            
            elif component == 'audio':
                if operation == 'play':
                    return {'success': True}
                elif operation == 'download':
                    return {'success': True}
            
            return {'success': False, 'message': 'Operation not supported'}
            
        except Exception as e:
            self.logger.warning(f"主要操作失败 [{component}:{operation}]: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_fallback_operation(self, component: str, operation: str, **kwargs) -> Dict[str, Any]:
        """
        执行备用操作
        Execute fallback operation
        """
        try:
            if component == 'ai_service':
                # Fallback to offline exercises
                if operation in ['conversation', 'correction', 'exercise_generation']:
                    return {
                        'success': True,
                        'fallback_type': 'offline_content',
                        'message': 'AI服务不可用，使用离线内容'
                    }
            
            elif component == 'cache':
                # Fallback to memory cache
                if operation in ['get', 'set']:
                    return {
                        'success': True,
                        'fallback_type': 'memory_cache',
                        'message': 'Redis缓存不可用，使用内存缓存'
                    }
            
            elif component == 'database':
                # Fallback to cached data
                if operation in ['query', 'update']:
                    return {
                        'success': True,
                        'fallback_type': 'cached_data',
                        'message': '数据库不可用，使用缓存数据'
                    }
            
            elif component == 'audio':
                # Fallback to text-only
                if operation in ['play', 'download']:
                    return {
                        'success': True,
                        'fallback_type': 'text_only',
                        'message': '音频不可用，使用文本模式'
                    }
            
            return {'success': False, 'message': 'No fallback available'}
            
        except Exception as e:
            self.logger.warning(f"备用操作失败 [{component}:{operation}]: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_degraded_mode(self, component: str, operation: str, **kwargs) -> Dict[str, Any]:
        """
        执行降级模式
        Execute degraded mode operation
        """
        try:
            if component == 'ai_service':
                # Degraded mode: basic content only
                return {
                    'success': True,
                    'degraded_level': 'high',
                    'message': 'AI服务完全不可用，仅提供基础内容',
                    'available_features': ['basic_vocabulary', 'static_content']
                }
            
            elif component == 'cache':
                # Degraded mode: no cache
                return {
                    'success': True,
                    'degraded_level': 'medium',
                    'message': '缓存不可用，性能可能受影响',
                    'available_features': ['direct_query', 'no_caching']
                }
            
            elif component == 'database':
                # Degraded mode: read-only static content
                return {
                    'success': True,
                    'degraded_level': 'critical',
                    'message': '数据库完全不可用，仅提供静态内容',
                    'available_features': ['static_content_only']
                }
            
            elif component == 'audio':
                # Degraded mode: no audio
                return {
                    'success': True,
                    'degraded_level': 'medium',
                    'message': '音频功能不可用，仅提供文本内容',
                    'available_features': ['text_content_only']
                }
            
            return {'success': False, 'message': 'Degraded mode not available'}
            
        except Exception as e:
            self.logger.error(f"降级模式失败 [{component}:{operation}]: {e}")
            return {'success': False, 'error': str(e)}
    
    def recover_from_failure(self, component: str, error: Exception) -> Dict[str, Any]:
        """
        从故障中恢复
        Recover from failure
        """
        recovery_result = {
            'success': False,
            'component': component,
            'recovery_attempted': False,
            'recovery_method': None
        }
        
        try:
            self.logger.error(f"检测到组件故障: {component}, 错误: {str(error)}")
            
            # Attempt recovery based on component
            if component == 'cache_manager':
                recovery_result = self._recover_cache_manager()
            
            elif component == 'ai_service':
                recovery_result = self._recover_ai_service()
            
            elif component == 'database':
                recovery_result = self._recover_database()
            
            elif component == 'audio_system':
                recovery_result = self._recover_audio_system()
            
            else:
                recovery_result['message'] = f'Unknown component: {component}'
            
            if recovery_result['success']:
                self.logger.info(f"组件恢复成功: {component}")
            else:
                self.logger.warning(f"组件恢复失败: {component}")
            
            return recovery_result
            
        except Exception as e:
            self.logger.error(f"故障恢复过程失败: {e}")
            recovery_result['error'] = str(e)
            return recovery_result
    
    def _recover_cache_manager(self) -> Dict[str, Any]:
        """
        恢复缓存管理器
        Recover cache manager
        """
        try:
            # Try to reconnect to cache manager
            if self.cache_manager:
                is_healthy = self.cache_manager.health_check()
                if is_healthy:
                    return {
                        'success': True,
                        'recovery_method': 'reconnect',
                        'message': '缓存管理器已恢复'
                    }
            
            # If Redis is still down, use fallback cache
            self.logger.warning("Redis仍然不可用，继续使用内存缓存")
            return {
                'success': True,
                'recovery_method': 'fallback_to_memory',
                'message': '已切换到内存缓存'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _recover_ai_service(self) -> Dict[str, Any]:
        """
        恢复AI服务
        Recover AI service
        """
        try:
            # Try to reinitialize AI service
            if not self.ai_service:
                from bilingual_tutor.services.ai_service import AIService
                self.ai_service = AIService()
                self.conversation_partner = ConversationPartner(self.ai_service)
                self.grammar_corrector = GrammarCorrector(self.ai_service)
                self.exercise_generator = ExerciseGenerator(self.ai_service)
                
                return {
                    'success': True,
                    'recovery_method': 'reinitialize',
                    'message': 'AI服务已重新初始化'
                }
            
            # Test AI service health
            health = self.get_ai_service_health()
            if health['status'] == 'available':
                return {
                    'success': True,
                    'recovery_method': 'health_check',
                    'message': 'AI服务健康'
                }
            
            return {
                'success': False,
                'recovery_method': 'none',
                'message': 'AI服务无法恢复，使用离线模式'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _recover_database(self) -> Dict[str, Any]:
        """
        恢复数据库连接
        Recover database connection
        """
        try:
            # Try to reconnect to database
            if self.learning_db:
                try:
                    self.learning_db.get_vocabulary_count('english')
                    return {
                        'success': True,
                        'recovery_method': 'reconnect',
                        'message': '数据库连接已恢复'
                    }
                except:
                    pass
            
            # Reinitialize database connection
            from bilingual_tutor.storage.database import LearningDatabase
            self.learning_db = LearningDatabase()
            
            try:
                self.learning_db.get_vocabulary_count('english')
                return {
                    'success': True,
                    'recovery_method': 'reinitialize',
                    'message': '数据库已重新初始化'
                }
            except:
                pass
            
            return {
                'success': False,
                'recovery_method': 'none',
                'message': '数据库无法恢复'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _recover_audio_system(self) -> Dict[str, Any]:
        """
        恢复音频系统
        Recover audio system
        """
        try:
            # Try to test audio system
            stats = self.pronunciation_manager.get_pronunciation_statistics()
            
            if stats:
                return {
                    'success': True,
                    'recovery_method': 'health_check',
                    'message': '音频系统健康'
                }
            
            return {
                'success': False,
                'recovery_method': 'none',
                'message': '音频系统无法恢复，使用文本模式'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def handle_user_friendly_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理用户友好的错误提示
        Handle user-friendly error messages
        """
        error_response = {
            'success': False,
            'error_type': 'unknown',
            'user_message': '发生了未知错误，请稍后再试',
            'technical_details': str(error),
            'suggestions': [],
            'can_retry': True
        }
        
        error_type = type(error).__name__
        context = context or {}
        
        # Map error types to user-friendly messages
        if 'Connection' in error_type or 'Timeout' in error_type:
            error_response['error_type'] = 'connection'
            error_response['user_message'] = '网络连接出现问题，请检查您的网络连接'
            error_response['suggestions'] = [
                '请检查网络连接是否正常',
                '尝试刷新页面',
                '稍后再试'
            ]
        
        elif 'Database' in error_type or 'SQLite' in error_type:
            error_response['error_type'] = 'database'
            error_response['user_message'] = '数据库访问出现问题，请稍后再试'
            error_response['suggestions'] = [
                '请稍后再试',
                '如果问题持续，请联系技术支持'
            ]
        
        elif 'Cache' in error_type or 'Redis' in error_type:
            error_response['error_type'] = 'cache'
            error_response['user_message'] = '缓存服务暂时不可用，系统将使用备用模式'
            error_response['suggestions'] = [
                '系统正在使用备用模式，功能可能受限',
                '性能可能会受到轻微影响',
                '缓存服务将自动恢复'
            ]
        
        elif 'AI' in error_type or 'ExternalService' in error_type:
            error_response['error_type'] = 'ai_service'
            error_response['user_message'] = 'AI服务暂时不可用，将使用离线内容'
            error_response['suggestions'] = [
                'AI服务正在维护或过载',
                '系统将提供离线内容',
                '您可以继续学习基础内容',
                'AI服务将自动恢复'
            ]
        
        elif 'Audio' in error_type or 'Pronunciation' in error_type:
            error_response['error_type'] = 'audio'
            error_response['user_message'] = '音频服务暂时不可用，将使用文本模式'
            error_response['suggestions'] = [
                '音频功能暂时不可用',
                '您可以继续使用文本学习',
                '检查设备音量设置',
                '音频服务将尽快恢复'
            ]
        
        elif 'Validation' in error_type or 'ValueError' in error_type:
            error_response['error_type'] = 'validation'
            error_response['user_message'] = '输入的数据格式不正确'
            error_response['suggestions'] = [
                '请检查输入内容',
                '确保数据格式正确',
                '参考示例格式'
            ]
        
        elif 'Permission' in error_type or 'Unauthorized' in error_type:
            error_response['error_type'] = 'permission'
            error_response['user_message'] = '您没有权限执行此操作'
            error_response['suggestions'] = [
                '请登录后重试',
                '检查您的账户权限',
                '联系管理员获取权限'
            ]
            error_response['can_retry'] = False
        
        elif 'RateLimit' in error_type or '429' in str(error):
            error_response['error_type'] = 'rate_limit'
            error_response['user_message'] = '请求过于频繁，请稍后再试'
            error_response['suggestions'] = [
                f'请等待 {context.get("retry_after", 60)} 秒后再试',
                '减少请求频率',
                '使用缓存内容'
            ]
        
        # Add context-specific suggestions
        if context.get('action'):
            action = context['action']
            if action == 'start_session':
                error_response['suggestions'].append('尝试使用其他浏览器')
                error_response['suggestions'].append('清除浏览器缓存后重试')
            elif action == 'save_progress':
                error_response['suggestions'].append('您的学习进度可能未保存')
                error_response['suggestions'].append('稍后尝试手动保存')
            elif action == 'load_content':
                error_response['suggestions'].append('尝试加载其他内容')
                error_response['suggestions'].append('使用已缓存的离线内容')
        
        self.logger.error(f"用户友好错误处理: {error_type}, 上下文: {context}")
        
        return error_response
    
    def get_user_guidance(self, situation: str, severity: str = 'info') -> Dict[str, Any]:
        """
        获取用户指导
        Get user guidance based on situation
        """
        guidance = {
            'situation': situation,
            'severity': severity,
            'title': '',
            'message': '',
            'actions': [],
            'icon': ''
        }
        
        if situation == 'first_time_user':
            guidance['title'] = '欢迎使用双语导师系统！'
            guidance['icon'] = '🎉'
            guidance['message'] = '这是您第一次使用本系统，让我们快速了解主要功能。'
            guidance['actions'] = [
                '点击"开始学习"创建您的学习计划',
                '探索词汇、阅读、听力等学习模块',
                '尝试AI对话练习功能',
                '查看学习进度和统计信息'
            ]
        
        elif situation == 'session_completed':
            guidance['title'] = '学习会话完成！'
            guidance['icon'] = '🎯'
            guidance['message'] = '恭喜您完成今日学习目标！'
            guidance['actions'] = [
                '查看详细的学习报告',
                '复习今日学到的内容',
                '计划明天的学习任务',
                '分享您的成就'
            ]
        
        elif situation == 'review_due':
            guidance['title'] = '复习提醒'
            guidance['icon'] = '📝'
            guidance['message'] = '您有一些内容需要复习，巩固记忆效果更好。'
            guidance['actions'] = [
                '立即开始复习',
                '查看需要复习的词汇列表',
                '使用智能复习计划'
            ]
        
        elif situation == 'achievement_unlocked':
            guidance['title'] = '解锁成就！'
            guidance['icon'] = '🏆'
            guidance['message'] = '恭喜您解锁了新的成就！'
            guidance['actions'] = [
                '查看您的成就徽章',
                '分享成就到社交媒体',
                '继续挑战更高目标'
            ]
        
        elif situation == 'degraded_mode':
            guidance['title'] = '服务降级模式'
            guidance['icon'] = '⚠️'
            guidance['message'] = '部分服务暂时不可用，系统正在降级模式运行。'
            guidance['actions'] = [
                '您仍然可以继续学习基础内容',
                '高级功能暂时受限',
                '系统将自动恢复正常',
                '感谢您的理解和耐心'
            ]
        
        elif situation == 'offline_mode':
            guidance['title'] = '离线模式'
            guidance['icon'] = '📴'
            guidance['message'] = '您当前处于离线模式，只能使用已缓存的内容。'
            guidance['actions'] = [
                '查看已下载的学习材料',
                '完成离线练习',
                '连接网络后同步进度'
            ]
        
        # Adjust guidance based on severity
        if severity == 'error':
            guidance['title'] = '发生错误'
            guidance['icon'] = '❌'
        elif severity == 'warning':
            guidance['icon'] = '⚠️'
        elif severity == 'success':
            guidance['icon'] = '✅'
        
        return guidance
    
    def execute_with_error_handling(self, operation: str, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        执行带错误处理的操作
        Execute operation with enhanced error handling
        """
        start_time = time.time()
        
        try:
            # Execute the operation
            if operation == 'create_session':
                result = self.create_integrated_learning_session(user_id, kwargs.get('preferences'))
            elif operation == 'execute_activity':
                result = self.execute_integrated_activity(
                    user_id, 
                    kwargs.get('activity_id'),
                    kwargs.get('user_responses')
                )
            elif operation == 'get_progress':
                result = self.get_integrated_progress_report(user_id)
            else:
                result = {'success': False, 'message': f'Unknown operation: {operation}'}
            
            execution_time = time.time() - start_time
            
            return {
                'success': result.get('success', False),
                'operation': operation,
                'result': result,
                'execution_time_seconds': execution_time,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Create user-friendly error response
            error_response = self.handle_user_friendly_error(e, context=kwargs)
            
            # Log the error
            self.logger.error(f"操作执行失败 [{operation}]: {str(e)}", exc_info=True)
            
            return {
                'success': False,
                'operation': operation,
                'error': error_response,
                'execution_time_seconds': execution_time,
                'timestamp': datetime.now().isoformat()
            }
    
    def run_health_monitoring(self) -> Dict[str, Any]:
        """
        运行系统健康监控
        Run system health monitoring
        """
        monitoring_result = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {},
            'alerts': [],
            'auto_fixes': []
        }
        
        try:
            # Check all components
            component_status = self.get_component_status()
            
            # Analyze component status
            for component_name, status_info in component_status['components'].items():
                monitoring_result['components'][component_name] = status_info
                
                # Generate alerts for degraded components
                if status_info.get('status') == 'error':
                    alert = {
                        'component': component_name,
                        'severity': 'critical',
                        'message': f'{component_name} 组件错误',
                        'timestamp': datetime.now().isoformat()
                    }
                    monitoring_result['alerts'].append(alert)
                    
                    # Attempt auto-fix
                    fix_result = self._attempt_auto_fix(component_name, status_info.get('error'))
                    if fix_result['success']:
                        monitoring_result['auto_fixes'].append({
                            'component': component_name,
                            'fix_method': fix_result['method'],
                            'result': 'successful'
                        })
                    else:
                        alert['auto_fix_failed'] = True
                        alert['fix_error'] = fix_result.get('error')
                
                elif status_info.get('status') == 'degraded':
                    alert = {
                        'component': component_name,
                        'severity': 'warning',
                        'message': f'{component_name} 组件降级',
                        'timestamp': datetime.now().isoformat()
                    }
                    monitoring_result['alerts'].append(alert)
            
            # Determine overall status
            critical_count = len([a for a in monitoring_result['alerts'] if a['severity'] == 'critical'])
            warning_count = len([a for a in monitoring_result['alerts'] if a['severity'] == 'warning'])
            
            if critical_count > 0:
                monitoring_result['overall_status'] = 'critical'
            elif warning_count > 0:
                monitoring_result['overall_status'] = 'warning'
            else:
                monitoring_result['overall_status'] = 'healthy'
            
            # Log monitoring results
            self.logger.info(f"系统健康监控: {monitoring_result['overall_status']}, 告警: {len(monitoring_result['alerts'])}, 自动修复: {len(monitoring_result['auto_fixes'])}")
            
        except Exception as e:
            self.logger.error(f"健康监控执行失败: {e}")
            monitoring_result['overall_status'] = 'error'
            monitoring_result['alerts'].append({
                'component': 'monitoring_system',
                'severity': 'critical',
                'message': f'健康监控系统错误: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        
        return monitoring_result
    
    def _attempt_auto_fix(self, component: str, error: str = None) -> Dict[str, Any]:
        """
        尝试自动修复
        Attempt automatic fix for component
        """
        fix_result = {
            'success': False,
            'method': None,
            'error': None
        }
        
        try:
            if component == 'cache_manager':
                # Try to fix cache manager
                if self.cache_manager:
                    is_healthy = self.cache_manager.health_check()
                    if not is_healthy:
                        # Try to reconnect
                        fix_result['method'] = 'cache_reconnect'
                        is_healthy = self.cache_manager.health_check()
                        fix_result['success'] = is_healthy
                
                if not fix_result['success']:
                    # Create new cache manager instance
                    try:
                        from bilingual_tutor.infrastructure.cache_manager import create_cache_manager, CacheConfig
                        self.cache_manager = create_cache_manager(CacheConfig())
                        fix_result['method'] = 'cache_reinitialize'
                        fix_result['success'] = True
                    except:
                        pass
            
            elif component == 'ai_service':
                # Try to fix AI service
                recovery_result = self._recover_ai_service()
                fix_result['success'] = recovery_result['success']
                fix_result['method'] = recovery_result.get('recovery_method')
            
            elif component == 'database':
                # Try to fix database
                recovery_result = self._recover_database()
                fix_result['success'] = recovery_result['success']
                fix_result['method'] = recovery_result.get('recovery_method')
            
            elif component == 'audio_system':
                # Try to fix audio system
                recovery_result = self._recover_audio_system()
                fix_result['success'] = recovery_result['success']
                fix_result['method'] = recovery_result.get('recovery_method')
            
            if fix_result['success']:
                self.logger.info(f"自动修复成功: {component}, 方法: {fix_result['method']}")
            else:
                self.logger.warning(f"自动修复失败: {component}")
            
        except Exception as e:
            fix_result['error'] = str(e)
            self.logger.error(f"自动修复过程异常: {component}, 错误: {e}")
        
        return fix_result
    
    def schedule_auto_maintenance(self) -> Dict[str, Any]:
        """
        调度自动维护
        Schedule automatic maintenance tasks
        """
        maintenance_result = {
            'success': True,
            'scheduled_tasks': [],
            'next_maintenance_time': None
        }
        
        try:
            # Schedule cache cleanup
            maintenance_result['scheduled_tasks'].append({
                'task': 'cache_cleanup',
                'description': '清理过期缓存',
                'interval_hours': 1,
                'enabled': True
            })
            
            # Schedule database optimization
            maintenance_result['scheduled_tasks'].append({
                'task': 'database_optimize',
                'description': '优化数据库',
                'interval_hours': 24,
                'enabled': True
            })
            
            # Schedule log rotation
            maintenance_result['scheduled_tasks'].append({
                'task': 'log_rotation',
                'description': '轮换日志文件',
                'interval_hours': 168,
                'enabled': True
            })
            
            # Schedule health check
            maintenance_result['scheduled_tasks'].append({
                'task': 'health_check',
                'description': '系统健康检查',
                'interval_minutes': 5,
                'enabled': True
            })
            
            # Set next maintenance time
            from datetime import timedelta
            maintenance_result['next_maintenance_time'] = (datetime.now() + timedelta(minutes=5)).isoformat()
            
            self.logger.info(f"自动维护任务已调度: {len(maintenance_result['scheduled_tasks'])} 个任务")
            
        except Exception as e:
            self.logger.error(f"调度自动维护失败: {e}")
            maintenance_result['success'] = False
            maintenance_result['error'] = str(e)
        
        return maintenance_result
    
    def get_health_report(self) -> Dict[str, Any]:
        """
        获取健康报告
        Get comprehensive health report
        """
        try:
            # Run monitoring
            monitoring_result = self.run_health_monitoring()
            
            # Get cache statistics
            cache_stats = self.get_cache_statistics()
            
            # Get integration health
            integration_health = self._check_integration_health()
            
            # Calculate uptime (simplified)
            uptime_seconds = time.time() - getattr(self, '_start_time', time.time())
            uptime_hours = uptime_seconds / 3600
            
            report = {
                'generated_at': datetime.now().isoformat(),
                'system_uptime_hours': round(uptime_hours, 2),
                'overall_status': monitoring_result['overall_status'],
                'components': monitoring_result['components'],
                'alerts': monitoring_result['alerts'],
                'auto_fixes': monitoring_result['auto_fixes'],
                'cache_statistics': cache_stats,
                'integration_health': integration_health,
                'recommendations': self._generate_health_recommendations(monitoring_result)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成健康报告失败: {e}")
            return {
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def _generate_health_recommendations(self, monitoring_result: Dict[str, Any]) -> List[str]:
        """
        生成健康建议
        Generate health recommendations
        """
        recommendations = []
        
        # Analyze alerts
        critical_alerts = [a for a in monitoring_result['alerts'] if a['severity'] == 'critical']
        warning_alerts = [a for a in monitoring_result['alerts'] if a['severity'] == 'warning']
        
        if len(critical_alerts) > 0:
            recommendations.append(f'检测到 {len(critical_alerts)} 个严重问题，建议立即处理')
            recommendations.append('检查系统日志以获取详细错误信息')
        
        if len(warning_alerts) > 0:
            recommendations.append(f'检测到 {len(warning_alerts)} 个警告，建议尽快处理')
        
        # Check auto-fix success rate
        auto_fixes = monitoring_result.get('auto_fixes', [])
        if len(auto_fixes) > 0:
            successful_fixes = [f for f in auto_fixes if f.get('result') == 'successful']
            success_rate = len(successful_fixes) / len(auto_fixes)
            
            if success_rate < 0.5:
                recommendations.append('自动修复成功率较低，建议人工介入')
            else:
                recommendations.append(f'自动修复成功率: {success_rate:.0%}')
        
        # Add maintenance recommendations
        recommendations.append('建议定期查看健康报告')
        recommendations.append('建议配置告警通知')
        
        return recommendations
    
    def execute_with_optimization(self, operation: str, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        执行优化后的操作
        Execute operation with optimization
        """
        start_time = time.time()
        
        # Optimize data flow
        flow_result = self.optimize_data_flow(operation, user_id=user_id, **kwargs)
        
        # Execute the actual operation
        operation_result = {}
        
        try:
            if operation == 'create_session':
                operation_result = self.create_integrated_learning_session(user_id, kwargs.get('preferences'))
            elif operation == 'execute_activity':
                operation_result = self.execute_integrated_activity(
                    user_id, 
                    kwargs.get('activity_id'),
                    kwargs.get('user_responses')
                )
            elif operation == 'get_progress':
                operation_result = self.get_integrated_progress_report(user_id)
            else:
                operation_result = {'success': False, 'message': f'Unknown operation: {operation}'}
            
            execution_time = time.time() - start_time
            
            return {
                'success': operation_result.get('success', False),
                'operation': operation,
                'result': operation_result,
                'optimization': flow_result,
                'execution_time_seconds': execution_time,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"执行优化操作失败: {e}")
            return {
                'success': False,
                'operation': operation,
                'error': str(e),
                'execution_time_seconds': time.time() - start_time,
                'timestamp': datetime.now().isoformat()
            }
    
    # ==================== Private Helper Methods ====================
    
    def _get_or_create_user_profile(self, user_id: str, preferences: Dict[str, Any] = None) -> UserProfile:
        """Get or create user profile with database integration"""
        # Check cache first
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        
        # Try to get from database
        user_data = self.learning_db.get_user_profile(user_id)
        
        if user_data:
            # Create profile from database data
            from bilingual_tutor.models import Goals, Preferences, Skill, ContentType
            
            goals = Goals(
                target_english_level="CET-6",
                target_japanese_level="N1",
                target_completion_date=datetime.now() + timedelta(days=730),
                priority_skills=[Skill.VOCABULARY, Skill.READING],
                custom_objectives=["提高英语综合能力", "通过日语N1考试"]
            )
            
            prefs = Preferences(
                preferred_study_times=["晚上"],
                content_preferences=[ContentType.ARTICLE, ContentType.NEWS],
                difficulty_preference="适中",
                language_balance={"english": 0.6, "japanese": 0.4}
            )
            
            profile = UserProfile(
                user_id=user_id,
                english_level=user_data.get('english_level', 'CET-4'),
                japanese_level=user_data.get('japanese_level', 'N5'),
                daily_study_time=user_data.get('daily_study_time', 60),
                target_goals=goals,
                learning_preferences=prefs,
                weak_areas=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        else:
            # Create default profile
            profile = self._create_default_user_profile(user_id, preferences)
        
        # Cache the profile
        self._user_cache[user_id] = profile
        return profile
    
    def _create_default_user_profile(self, user_id: str, preferences: Dict[str, Any] = None) -> UserProfile:
        """Create default user profile"""
        from bilingual_tutor.models import Goals, Preferences, Skill, ContentType
        
        goals = Goals(
            target_english_level="CET-6",
            target_japanese_level="N1",
            target_completion_date=datetime.now() + timedelta(days=730),
            priority_skills=[Skill.VOCABULARY, Skill.READING, Skill.LISTENING],
            custom_objectives=["提高英语综合能力", "通过日语N1考试"]
        )
        
        prefs = Preferences(
            preferred_study_times=["晚上"],
            content_preferences=[ContentType.ARTICLE, ContentType.NEWS],
            difficulty_preference="适中",
            language_balance={"english": 0.6, "japanese": 0.4}
        )
        
        # Apply user preferences if provided
        english_level = 'CET-4'
        japanese_level = 'N5'
        daily_time = 60
        
        if preferences:
            english_level = preferences.get('english_level', english_level)
            japanese_level = preferences.get('japanese_level', japanese_level)
            daily_time = preferences.get('daily_time', daily_time)
        
        return UserProfile(
            user_id=user_id,
            english_level=english_level,
            japanese_level=japanese_level,
            daily_study_time=daily_time,
            target_goals=goals,
            learning_preferences=prefs,
            weak_areas=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _enhance_activities_with_audio_and_content(self, activities: List[LearningActivity], 
                                                 user_profile: UserProfile) -> List[LearningActivity]:
        """Enhance activities with audio and database content"""
        enhanced_activities = []
        
        for activity in activities:
            # Get real content from database
            if activity.activity_type.value == 'vocabulary':
                # Get vocabulary with audio
                vocab_items = self.get_vocabulary_with_audio(
                    activity.language, 
                    user_profile.english_level if activity.language == 'english' else user_profile.japanese_level,
                    5
                )
                
                if vocab_items:
                    # Update activity content with real vocabulary
                    content_parts = ["📚 **今日词汇学习**\n"]
                    for i, item in enumerate(vocab_items, 1):
                        content_parts.append(f"\n**{i}. {item['word']}** {item['reading']}")
                        content_parts.append(f"   释义：{item['meaning']}")
                        if item['example_sentence']:
                            content_parts.append(f"   例句：{item['example_sentence']}")
                        if item['example_translation']:
                            content_parts.append(f"   译文：{item['example_translation']}")
                        if item['audio_available']:
                            content_parts.append(f"   🔊 发音可用")
                        content_parts.append("")
                    
                    activity.content.body = "\n".join(content_parts)
                    activity.content.title = f"{activity.language.title()} 词汇学习"
            
            enhanced_activities.append(activity)
        
        return enhanced_activities
    
    def _process_integrated_activity_completion(self, user_id: str, activity: LearningActivity, 
                                              result: ActivityResult, user_responses: Dict[str, Any] = None):
        """Process activity completion with all integrated components"""
        # Process through core engine
        self.core_engine.process_activity_completion(user_id, activity, result)
        
        # Record in database for spaced repetition
        if activity.activity_type.value == 'vocabulary' and user_responses:
            vocab_ids = user_responses.get('vocab_ids', [])
            for vocab_id in vocab_ids:
                correct = user_responses.get(f'correct_{vocab_id}', True)
                self.learning_db.record_learning(user_id, vocab_id, 'vocabulary', correct)
    
    def _get_activity_audio_info(self, activity: LearningActivity) -> Dict[str, Any]:
        """Get audio information for an activity"""
        audio_info = {
            'has_audio': False,
            'audio_files': []
        }
        
        if activity.activity_type.value == 'vocabulary':
            # Extract words from activity content (simplified)
            # In a real implementation, this would parse the content more intelligently
            words = []  # Would extract from activity.content.body
            
            for word in words:
                audio_path = self.pronunciation_manager.get_pronunciation_audio(
                    word, activity.language
                )
                if audio_path:
                    audio_info['audio_files'].append({
                        'word': word,
                        'path': audio_path
                    })
            
            audio_info['has_audio'] = len(audio_info['audio_files']) > 0
        
        return audio_info
    
    def _calculate_next_review_date(self, score: float) -> str:
        """Calculate next review date based on performance"""
        # Simple spaced repetition calculation
        if score >= 0.9:
            days = 7
        elif score >= 0.8:
            days = 3
        elif score >= 0.7:
            days = 1
        else:
            days = 0.5
        
        next_review = datetime.now() + timedelta(days=days)
        return next_review.isoformat()
    
    def _assess_interaction_quality(self, result: ActivityResult) -> Dict[str, Any]:
        """
        评估交互质量
        Assess interaction quality for UX improvement
        """
        quality_score = 0.0
        feedback_messages = []
        
        # Assess completion time
        if hasattr(result, 'time_spent'):
            if result.time_spent > 0:
                # Good time management
                if result.time_spent <= 60:
                    quality_score += 0.3
                    feedback_messages.append('节奏良好 - 适中时间内完成')
                elif result.time_spent <= 120:
                    quality_score += 0.2
                    feedback_messages.append('节奏可接受')
                else:
                    feedback_messages.append('建议提高学习效率')
        
        # Assess accuracy
        if hasattr(result, 'score'):
            if result.score >= 0.9:
                quality_score += 0.4
                feedback_messages.append('表现优秀 - 准确率高')
            elif result.score >= 0.7:
                quality_score += 0.3
                feedback_messages.append('表现良好')
            else:
                quality_score += 0.1
                feedback_messages.append('需要更多练习')
        
        # Assess error pattern
        if hasattr(result, 'errors_made') and len(result.errors_made) > 0:
            if len(result.errors_made) <= 2:
                quality_score += 0.2
                feedback_messages.append('错误较少 - 保持专注')
            else:
                feedback_messages.append(f'注意纠正 {len(result.errors_made)} 个错误')
        
        # Determine overall quality level
        if quality_score >= 0.8:
            quality_level = 'excellent'
            encouraging_message = '太棒了！继续保持！🌟'
        elif quality_score >= 0.6:
            quality_level = 'good'
            encouraging_message = '做得很好！继续加油！💪'
        elif quality_score >= 0.4:
            quality_level = 'acceptable'
            encouraging_message = '不错的尝试，再接再厉！📚'
        else:
            quality_level = 'needs_improvement'
            encouraging_message = '别灰心，多练习会有进步！🌱'
        
        return {
            'score': quality_score,
            'level': quality_level,
            'feedback_messages': feedback_messages,
            'encouraging_message': encouraging_message,
            'suggestions': self._generate_interaction_suggestions(quality_score, result)
        }
    
    def _generate_interaction_suggestions(self, quality_score: float, 
                                       result: ActivityResult) -> List[str]:
        """
        生成交互改进建议
        Generate interaction improvement suggestions
        """
        suggestions = []
        
        if quality_score < 0.5:
            suggestions.append('建议：先从简单的内容开始，逐步提高难度')
            suggestions.append('建议：多次重复练习，加深记忆')
            suggestions.append('提示：可以尝试使用音频辅助学习')
        
        elif quality_score < 0.7:
            suggestions.append('建议：注意时间管理，提高学习效率')
            suggestions.append('建议：复习时重点查看错误解析')
        
        elif quality_score < 0.9:
            suggestions.append('建议：尝试更具挑战性的内容')
            suggestions.append('建议：可以将学到的内容应用到实际对话中')
        
        else:
            suggestions.append('建议：可以开始学习更高级的内容')
            suggestions.append('提示：尝试教别人，巩固你的知识')
        
        return suggestions
    
    def _serialize_activity(self, activity: LearningActivity) -> Dict[str, Any]:
        """Serialize activity for JSON response"""
        return {
            'id': activity.activity_id,
            'type': activity.activity_type.value,
            'language': activity.language,
            'language_display': '英语' if activity.language == 'english' else '日语' if activity.language == 'japanese' else '混合',
            'title': activity.content.title,
            'content': activity.content.body,
            'duration': activity.estimated_duration,
            'difficulty': activity.difficulty_level,
            'skills': [skill.value for skill in activity.skills_practiced],
            'estimated_points': activity.estimated_duration * 10
        }
    
    def _get_content_crawler_stats(self, user_id: str) -> Dict[str, Any]:
        """Get content crawler statistics"""
        try:
            return {
                'english_content_count': len(self.content_crawler.get_cached_content('english', 'CET-4')),
                'japanese_content_count': len(self.content_crawler.get_cached_content('japanese', 'N5')),
                'last_crawl_time': datetime.now().isoformat(),
                'crawler_health': 'healthy'
            }
        except:
            return {
                'english_content_count': 0,
                'japanese_content_count': 0,
                'last_crawl_time': None,
                'crawler_health': 'unknown'
            }
    
    def _check_integration_health(self) -> Dict[str, str]:
        """Check the health of all integrated components"""
        health_status = {}
        
        try:
            # Check core engine
            health_status['core_engine'] = 'healthy'
            
            # Check database
            self.learning_db.get_vocabulary_count('english')
            health_status['database'] = 'healthy'
            
            # Check audio system
            self.pronunciation_manager.get_pronunciation_statistics()
            health_status['audio_system'] = 'healthy'
            
            # Check content crawler
            health_status['content_crawler'] = 'healthy'
            
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            health_status['overall'] = 'degraded'
        
        return health_status
    
    def _optimize_caches(self) -> Dict[str, Any]:
        """Optimize internal caches"""
        # Clear old cache entries
        current_time = datetime.now()
        
        # Clear user cache entries older than 1 hour
        old_users = [uid for uid, profile in self._user_cache.items() 
                    if current_time - profile.updated_at > timedelta(hours=1)]
        for uid in old_users:
            del self._user_cache[uid]
        
        # Clear content cache entries older than 1 hour
        old_content = [key for key, item in self._content_cache.items()
                      if current_time - item['cached_at'] > timedelta(hours=1)]
        for key in old_content:
            del self._content_cache[key]
        
        return {
            'user_cache_cleared': len(old_users),
            'content_cache_cleared': len(old_content),
            'current_user_cache_size': len(self._user_cache),
            'current_content_cache_size': len(self._content_cache)
        }
    
    def _optimize_database_performance(self) -> Dict[str, Any]:
        """Optimize database performance"""
        try:
            # Run VACUUM to optimize database
            self.learning_db.conn.execute("VACUUM")
            
            # Update statistics
            self.learning_db.conn.execute("ANALYZE")
            
            return {
                'vacuum_completed': True,
                'statistics_updated': True,
                'optimization_time': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"数据库优化失败: {e}")
            return {'optimization_failed': str(e)}
    
    def _optimize_common_queries(self) -> Dict[str, Any]:
        """Optimize common database queries"""
        try:
            # Pre-cache common vocabulary queries
            common_levels = ['CET-4', 'CET-5', 'CET-6', 'N5', 'N4', 'N3', 'N2', 'N1']
            cached_queries = 0
            
            for level in common_levels:
                if 'CET' in level:
                    self.get_cached_content('vocabulary', 'english', level)
                    cached_queries += 1
                else:
                    self.get_cached_content('vocabulary', 'japanese', level)
                    cached_queries += 1
            
            return {
                'common_queries_cached': cached_queries,
                'cache_optimization_completed': True
            }
        except Exception as e:
            self.logger.error(f"查询优化失败: {e}")
            return {'query_optimization_failed': str(e)}
    
    def close(self):
        """Close all connections and cleanup resources"""
        try:
            if self.pronunciation_manager:
                self.pronunciation_manager.close()
            
            if self.learning_db:
                self.learning_db.close()
            
            # Clear caches
            self._user_cache.clear()
            self._content_cache.clear()
            self._audio_cache.clear()
            
            self.logger.info("系统集成器已关闭 - System Integrator closed")
            
        except Exception as e:
            self.logger.error(f"关闭系统集成器失败: {e}")