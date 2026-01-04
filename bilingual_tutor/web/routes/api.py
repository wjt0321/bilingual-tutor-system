"""
API routes for learning functionality
双语导师系统学习功能API路由
"""

import os
import sys
import uuid
import random
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from bilingual_tutor.core.engine import CoreLearningEngine
from bilingual_tutor.core.system_integrator import SystemIntegrator
from bilingual_tutor.models import UserProfile, Goals, Preferences, Skill, ContentType, WeakArea
from bilingual_tutor.content.learning_content import get_all_content
from bilingual_tutor.storage.database import LearningDatabase

api_bp = Blueprint('api', __name__)

# 延迟初始化组件，避免导入时阻塞
_system_integrator = None
_learning_content = None

def get_system_integrator():
    """获取或初始化系统集成器"""
    global _system_integrator
    if _system_integrator is None:
        from bilingual_tutor.core.system_integrator import SystemIntegrator
        _system_integrator = SystemIntegrator()
    return _system_integrator

def get_engine():
    """获取核心学习引擎"""
    return get_system_integrator().core_engine

def get_learning_db():
    """获取学习数据库"""
    return get_system_integrator().learning_db

def get_learning_content_cache():
    """获取静态学习内容缓存"""
    global _learning_content
    if _learning_content is None:
        from bilingual_tutor.content.learning_content import get_all_content
        _learning_content = get_all_content()
    return _learning_content

# In-memory storage for user profiles and sessions
user_profiles = {}
user_learning_sessions = {}

def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_or_create_user_profile(user_id):
    """Get existing user profile or create a new one."""
    if user_id not in user_profiles:
        # Import users from auth module to get registration data
        from bilingual_tutor.web.routes.auth import users
        
        # Get user data from registration if available
        user_data = users.get(user_id, {})
        english_level = user_data.get('english_level', 'CET-4')
        japanese_level = user_data.get('japanese_level', 'N5')
        daily_time = user_data.get('daily_time', 60)
        
        goals = Goals(
            target_english_level="CET-6",
            target_japanese_level="N1",
            target_completion_date=datetime.now() + timedelta(days=730),
            priority_skills=[Skill.VOCABULARY, Skill.READING, Skill.LISTENING],
            custom_objectives=["提高英语综合能力", "通过日语N1考试"]
        )
        preferences = Preferences(
            preferred_study_times=["晚上"],
            content_preferences=[ContentType.ARTICLE, ContentType.NEWS],
            difficulty_preference="适中",
            language_balance={"english": 0.6, "japanese": 0.4}
        )
        user_profiles[user_id] = UserProfile(
            user_id=user_id,
            english_level=english_level,
            japanese_level=japanese_level,
            daily_study_time=daily_time,
            target_goals=goals,
            learning_preferences=preferences,
            weak_areas=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    return user_profiles[user_id]

def get_learning_content_from_db(language: str, content_type: str, level: str):
    """从数据库获取学习内容"""
    try:
        if content_type == "vocabulary":
            vocab_items = get_learning_db().get_vocabulary(language, level, limit=10)
            if vocab_items:
                content_parts = ["📚 **今日词汇学习**\n"]
                for i, item in enumerate(vocab_items[:5], 1):
                    content_parts.append(f"\n**{i}. {item.word}** {item.reading}")
                    content_parts.append(f"   释义：{item.meaning}")
                    if item.example_sentence:
                        content_parts.append(f"   例句：{item.example_sentence}")
                    if item.example_translation:
                        content_parts.append(f"   译文：{item.example_translation}")
                    content_parts.append("")
                
                content_parts.append("\n💡 **学习提示**：认真记忆每个单词，完成后点击「完成学习」。")
                
                return {
                    "title": f"{level} 词汇学习",
                    "body": "\n".join(content_parts),
                    "vocab_ids": [item.id for item in vocab_items[:5]]
                }
        
        elif content_type == "grammar":
            grammar_items = get_learning_db().get_grammar(language, level, limit=3)
            if grammar_items:
                content_parts = ["📖 **语法学习**\n"]
                for item in grammar_items[:2]:
                    content_parts.append(f"\n### {item['name']}")
                    content_parts.append(f"**句型**：{item['pattern']}")
                    content_parts.append(f"\n{item['explanation']}")
                    content_parts.append("\n**例句**：")
                    for ex in item.get('examples', [])[:3]:
                        content_parts.append(f"- {ex}")
                    content_parts.append("")
                
                return {
                    "title": f"{level} 语法学习",
                    "body": "\n".join(content_parts)
                }
        
        elif content_type == "reading":
            content_items = get_learning_db().get_content(language, level, "reading", limit=1)
            if content_items:
                item = content_items[0]
                return {
                    "title": item.title,
                    "body": item.body
                }
    except Exception as e:
        print(f"Error getting content from DB: {e}")
    
    return None

def get_learning_content(language: str, content_type: str):
    """获取指定语言和类型的学习内容（优先从数据库）"""
    user_id = session.get('user_id')
    if user_id and user_id in user_profiles:
        profile = user_profiles[user_id]
        level = profile.english_level if language == "english" else profile.japanese_level
    else:
        level = "CET-4" if language == "english" else "N5"
    
    # 尝试从数据库获取
    learning_db = get_learning_db()
    db_content = get_learning_content_from_db(language, content_type, level)
    if db_content:
        return db_content
    
    # 回退到静态内容
    learning_content = get_learning_content_cache()
    if language == "mixed":
        content_list = []
        for lang in ["english", "japanese"]:
            if lang in learning_content.get("review", {}):
                content_list.extend(learning_content["review"][lang])
        return random.choice(content_list) if content_list else None
    
    lang_content = learning_content.get(language, {})
    type_content = lang_content.get(content_type, [])
    
    if type_content:
        return random.choice(type_content)
    
    # Fallback to any available content for this language
    for ctype in ["vocabulary", "grammar", "reading"]:
        if ctype in lang_content and lang_content[ctype]:
            return random.choice(lang_content[ctype])
    
    return None

# ==================== User Profile API ====================

@api_bp.route('/user/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get user profile."""
    try:
        user_id = session['user_id']
        profile = get_or_create_user_profile(user_id)
        
        return jsonify({
            'success': True,
            'profile': {
                'user_id': profile.user_id,
                'english_level': profile.english_level,
                'japanese_level': profile.japanese_level,
                'daily_study_time': profile.daily_study_time,
                'target_english': profile.target_goals.target_english_level,
                'target_japanese': profile.target_goals.target_japanese_level,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': '获取用户资料失败'}), 500

@api_bp.route('/user/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update user profile."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        user_id = session['user_id']
        profile = get_or_create_user_profile(user_id)
        
        # Update settings with validation
        if 'english_level' in data:
            valid_levels = ['CET-4', 'CET-5', 'CET-6']
            if data['english_level'] in valid_levels:
                profile.english_level = data['english_level']
            else:
                return jsonify({'success': False, 'message': '英语水平选择无效'}), 400
        
        if 'japanese_level' in data:
            valid_levels = ['N5', 'N4', 'N3', 'N2', 'N1']
            if data['japanese_level'] in valid_levels:
                profile.japanese_level = data['japanese_level']
            else:
                return jsonify({'success': False, 'message': '日语水平选择无效'}), 400
        
        if 'daily_time' in data:
            try:
                daily_time = int(data['daily_time'])
                if 15 <= daily_time <= 300:
                    profile.daily_study_time = daily_time
                else:
                    return jsonify({'success': False, 'message': '每日学习时间应在15-300分钟之间'}), 400
            except (ValueError, TypeError):
                return jsonify({'success': False, 'message': '每日学习时间格式错误'}), 400
        
        profile.updated_at = datetime.now()
        
        return jsonify({'success': True, 'message': '设置已更新'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': '更新用户资料失败'}), 500

# ==================== Learning Plan API ====================

@api_bp.route('/learning/plan', methods=['GET'])
@require_auth
def get_learning_plan():
    """Get today's learning plan with integrated content and audio."""
    try:
        user_id = session['user_id']
        
        # Use system integrator to create integrated learning session
        session_result = get_system_integrator().create_integrated_learning_session(
            user_id, 
            preferences=session.get('user_preferences', {})
        )
        
        if not session_result['success']:
            return jsonify(session_result), 500
        
        # Extract plan data from session result
        session_data = session_result['session']
        
        return jsonify({
            'success': True,
            'plan': {
                'plan_id': session_data['session_id'],
                'date': datetime.now().isoformat(),
                'total_time': session_data['time_allocation']['total'],
                'review_time': session_data['time_allocation']['review'],
                'english_time': session_data['time_allocation']['english'],
                'japanese_time': session_data['time_allocation']['japanese'],
                'activities': session_data['activities'],
                'objectives': session_data['objectives']
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取学习计划失败'}), 500

@api_bp.route('/learning/start', methods=['POST'])
@require_auth
def start_session():
    """Start a learning session."""
    try:
        user_id = session['user_id']
        study_session = get_engine().start_daily_session(user_id)
        
        return jsonify({
            'success': True,
            'session': {
                'session_id': study_session.session_id,
                'duration': study_session.planned_duration,
                'status': study_session.status.value
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '启动学习会话失败'}), 500

@api_bp.route('/learning/execute/<activity_id>', methods=['POST'])
@require_auth
def execute_activity(activity_id):
    """Execute a learning activity with integrated audio and database recording."""
    try:
        user_id = session['user_id']
        
        # Get user responses from request
        data = request.get_json() or {}
        user_responses = data.get('responses', {})
        
        # Use system integrator to execute integrated activity
        result = get_system_integrator().execute_integrated_activity(
            user_id, activity_id, user_responses
        )
        
        if not result['success']:
            return jsonify(result), 404
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': '执行学习活动失败'}), 500

# ==================== Progress API ====================

@api_bp.route('/progress/status', methods=['GET'])
@require_auth
def get_progress():
    """Get comprehensive progress status with integrated data."""
    try:
        user_id = session['user_id']
        
        # Use system integrator to get comprehensive progress report
        report_result = get_system_integrator().get_integrated_progress_report(user_id)
        
        if not report_result['success']:
            return jsonify(report_result), 500
        
        report = report_result['report']
        
        return jsonify({
            'success': True,
            'progress': {
                'vocabulary': report['core_progress'].get('vocabulary_progress', {}),
                'weaknesses': report['core_progress'].get('weakness_analysis', {}),
                'content_history': report['core_progress'].get('content_history', {}),
                'review_schedule': report['core_progress'].get('review_schedule', {}),
                'database_stats': report['database_stats'],
                'audio_stats': report['audio_stats'],
                'integration_health': report['integration_health']
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取进度状态失败'}), 500

@api_bp.route('/progress/report', methods=['GET'])
@require_auth
def get_report():
    """Get progress report."""
    try:
        user_id = session['user_id']
        profile = get_or_create_user_profile(user_id)
        
        # Get various statistics
        status = get_engine().get_comprehensive_user_status(user_id)
        
        return jsonify({
            'success': True,
            'report': {
                'user_level': {
                    'english': profile.english_level,
                    'japanese': profile.japanese_level
                },
                'target_level': {
                    'english': profile.target_goals.target_english_level,
                    'japanese': profile.target_goals.target_japanese_level
                },
                'daily_time': profile.daily_study_time,
                'vocabulary_progress': status.get('vocabulary_progress', {}),
                'weakness_analysis': status.get('weakness_analysis', {}),
                'content_learned': status.get('content_history', {}).get('total_content_seen', 0)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取进度报告失败'}), 500

# ==================== Spaced Repetition API ====================

@api_bp.route('/review/record', methods=['POST'])
@require_auth
def record_learning():
    """记录学习结果（艾宾浩斯曲线核心）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        user_id = session['user_id']
        item_id = data.get('item_id')
        item_type = data.get('item_type', 'vocabulary')
        correct = data.get('correct', True)
        
        if not item_id:
            return jsonify({'success': False, 'message': '缺少 item_id'}), 400
        
        # 记录学习结果
        record = get_learning_db().record_learning(user_id, item_id, item_type, correct)
        
        return jsonify({
            'success': True,
            'record': {
                'learn_count': record.learn_count,
                'correct_count': record.correct_count,
                'memory_strength': record.memory_strength,
                'mastery_level': record.mastery_level,
                'next_review': record.next_review_date.isoformat() if record.next_review_date else None
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '记录学习结果失败'}), 500

@api_bp.route('/review/due', methods=['GET'])
@require_auth
def get_due_reviews():
    """获取需要复习的内容"""
    try:
        user_id = session['user_id']
        item_type = request.args.get('type', None)
        
        due_items = get_learning_db().get_due_reviews(user_id, item_type, limit=20)
        
        return jsonify({
            'success': True,
            'due_count': len(due_items),
            'items': due_items
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取复习内容失败'}), 500

@api_bp.route('/review/stats', methods=['GET'])
@require_auth
def get_learning_stats():
    """获取学习统计（艾宾浩斯进度）"""
    try:
        user_id = session['user_id']
        stats = get_learning_db().get_learning_stats(user_id)
        
        # 添加数据库总量统计
        stats['database'] = {
            'english_vocab': get_learning_db().get_vocabulary_count('english'),
            'japanese_vocab': get_learning_db().get_vocabulary_count('japanese'),
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取学习统计失败'}), 500

@api_bp.route('/database/status', methods=['GET'])
def database_status():
    """获取数据库状态"""
    try:
        stats = {
            'english_vocab_cet4': get_learning_db().get_vocabulary_count('english', 'CET-4'),
            'english_vocab_cet6': get_learning_db().get_vocabulary_count('english', 'CET-6'),
            'japanese_vocab_n5': get_learning_db().get_vocabulary_count('japanese', 'N5'),
            'japanese_vocab_n4': get_learning_db().get_vocabulary_count('japanese', 'N4'),
            'total_english': get_learning_db().get_vocabulary_count('english'),
            'total_japanese': get_learning_db().get_vocabulary_count('japanese'),
        }
        
        return jsonify({
            'success': True,
            'database': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取数据库状态失败'}), 500

# ==================== Audio System API ====================

@api_bp.route('/audio/vocabulary/<int:vocab_id>', methods=['GET'])
@require_auth
def get_vocabulary_audio(vocab_id):
    """获取词汇发音音频"""
    try:
        # Get vocabulary item from database
        vocab_item = get_learning_db().get_vocabulary_by_id(vocab_id)
        if not vocab_item:
            return jsonify({'success': False, 'message': '词汇未找到'}), 404
        
        # Get audio file path
        audio_path = get_system_integrator().pronunciation_manager.get_pronunciation_audio(
            vocab_item.word, vocab_item.language, vocab_item.level
        )
        
        if audio_path and os.path.exists(audio_path):
            return jsonify({
                'success': True,
                'audio': {
                    'word': vocab_item.word,
                    'language': vocab_item.language,
                    'level': vocab_item.level,
                    'audio_path': audio_path,
                    'audio_available': True
                }
            })
        else:
            return jsonify({
                'success': True,
                'audio': {
                    'word': vocab_item.word,
                    'language': vocab_item.language,
                    'level': vocab_item.level,
                    'audio_available': False
                }
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取音频失败'}), 500

@api_bp.route('/audio/batch-crawl', methods=['POST'])
@require_auth
def batch_crawl_audio():
    """批量爬取词汇发音"""
    try:
        data = request.get_json()
        if not data or 'vocabulary_items' not in data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        vocabulary_items = data['vocabulary_items']
        
        # Use system integrator to crawl and integrate audio
        result = get_system_integrator().integrate_audio_with_vocabulary(vocabulary_items)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': '批量爬取音频失败'}), 500

@api_bp.route('/audio/statistics', methods=['GET'])
@require_auth
def get_audio_statistics():
    """获取音频系统统计信息"""
    try:
        stats = get_system_integrator().pronunciation_manager.get_pronunciation_statistics()
        
        return jsonify({
            'success': True,
            'audio_statistics': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取音频统计失败'}), 500

# ==================== System Optimization API ====================

@api_bp.route('/system/optimize', methods=['POST'])
@require_auth
def optimize_system():
    """优化系统性能"""
    try:
        # Use system integrator to optimize database and caches
        optimization_result = get_system_integrator().optimize_database_queries()
        
        return jsonify(optimization_result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': '系统优化失败'}), 500

@api_bp.route('/system/health', methods=['GET'])
def system_health():
    """获取系统健康状态"""
    try:
        # Get integrated progress report to check system health
        health_result = get_system_integrator().get_integrated_progress_report('system_health_check')
        
        if health_result['success']:
            health_status = health_result['report']['integration_health']
        else:
            health_status = {'overall': 'unknown'}
        
        return jsonify({
            'success': True,
            'health': health_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取系统健康状态失败'}), 500

@api_bp.route('/content/cached/<content_type>/<language>/<level>', methods=['GET'])
@require_auth
def get_cached_content(content_type, language, level):
    """获取缓存的学习内容"""
    try:
        # Use system integrator to get cached content
        content = get_system_integrator().get_cached_content(content_type, language, level)
        
        if content:
            return jsonify({
                'success': True,
                'content': content,
                'cached': True
            })
        else:
            return jsonify({
                'success': False,
                'message': '内容未找到'
            }), 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取缓存内容失败'}), 500