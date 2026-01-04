from flask import Blueprint, request, jsonify
from functools import wraps
import logging

logger = logging.getLogger(__name__)

notifications_bp = Blueprint('notifications', __name__)


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


@notifications_bp.route('/api/notifications/preferences', methods=['GET'])
@require_auth
def get_notification_preferences():
    try:
        from ...infrastructure.notification_manager import NotificationManager
        
        manager = NotificationManager()
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        preferences = manager.get_user_preferences(user_id)
        
        return jsonify({
            'success': True,
            'preferences': preferences
        })
    except Exception as e:
        logger.error(f"Error getting notification preferences: {e}")
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/api/notifications/preferences', methods=['POST'])
@require_auth
def update_notification_preferences():
    try:
        from ...infrastructure.notification_manager import NotificationManager
        
        data = request.get_json()
        user_id = data.get('user_id')
        preferences = data.get('preferences')
        
        if not user_id or not preferences:
            return jsonify({'error': 'user_id and preferences required'}), 400
        
        manager = NotificationManager()
        manager.set_user_preferences(user_id, preferences)
        
        return jsonify({
            'success': True,
            'message': 'Preferences updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}")
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/api/notifications/daily-reminder', methods=['POST'])
@require_auth
def send_daily_reminder():
    try:
        from ...infrastructure.notification_manager import NotificationManager
        
        data = request.get_json()
        user_id = data.get('user_id')
        pending_tasks = data.get('pending_tasks', [])
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        manager = NotificationManager()
        success = manager.send_daily_reminder(user_id, pending_tasks)
        
        return jsonify({
            'success': success,
            'message': 'Reminder sent successfully' if success else 'Reminder not sent'
        })
    except Exception as e:
        logger.error(f"Error sending daily reminder: {e}")
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/api/notifications/review-reminder', methods=['POST'])
@require_auth
def send_review_reminder():
    try:
        from ...infrastructure.notification_manager import NotificationManager
        
        data = request.get_json()
        user_id = data.get('user_id')
        review_count = data.get('review_count', 0)
        languages = data.get('languages', [])
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        manager = NotificationManager()
        success = manager.send_review_reminder(user_id, review_count, languages)
        
        return jsonify({
            'success': success,
            'message': 'Review reminder sent successfully' if success else 'Reminder not sent'
        })
    except Exception as e:
        logger.error(f"Error sending review reminder: {e}")
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/api/notifications/achievement', methods=['POST'])
@require_auth
def send_achievement_notification():
    try:
        from ...infrastructure.notification_manager import NotificationManager
        
        data = request.get_json()
        user_id = data.get('user_id')
        achievement_name = data.get('achievement_name')
        description = data.get('description', '')
        
        if not user_id or not achievement_name:
            return jsonify({'error': 'user_id and achievement_name required'}), 400
        
        manager = NotificationManager()
        success = manager.send_achievement_notification(user_id, achievement_name, description)
        
        return jsonify({
            'success': success,
            'message': 'Achievement notification sent successfully' if success else 'Notification not sent'
        })
    except Exception as e:
        logger.error(f"Error sending achievement notification: {e}")
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/api/notifications/custom', methods=['POST'])
@require_auth
def send_custom_notification():
    try:
        from ...infrastructure.notification_manager import NotificationManager
        
        data = request.get_json()
        user_id = data.get('user_id')
        title = data.get('title')
        body = data.get('body')
        notification_data = data.get('data')
        
        if not user_id or not title or not body:
            return jsonify({'error': 'user_id, title, and body required'}), 400
        
        manager = NotificationManager()
        success = manager.send_custom_notification(user_id, title, body, notification_data)
        
        return jsonify({
            'success': success,
            'message': 'Custom notification sent successfully' if success else 'Notification not sent'
        })
    except Exception as e:
        logger.error(f"Error sending custom notification: {e}")
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/api/notifications/pending', methods=['GET'])
@require_auth
def get_pending_notifications():
    try:
        from ...infrastructure.notification_manager import NotificationManager
        
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        manager = NotificationManager()
        notifications = manager.get_pending_notifications(user_id)
        
        return jsonify({
            'success': True,
            'notifications': notifications
        })
    except Exception as e:
        logger.error(f"Error getting pending notifications: {e}")
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/api/notifications/stats', methods=['GET'])
@require_auth
def get_notification_stats():
    try:
        from ...infrastructure.notification_manager import NotificationManager
        
        manager = NotificationManager()
        stats = manager.get_notification_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting notification stats: {e}")
        return jsonify({'error': str(e)}), 500
