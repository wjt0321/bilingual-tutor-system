class NotificationManager:
    def __init__(self, config_manager=None):
        from .config_manager import ConfigManager
        
        self.config = config_manager or ConfigManager()
        self.enabled = self.config.get('notifications.enabled', True)
        self.notification_types = self.config.get('notifications.types', {
            'daily_reminder': True,
            'review_reminder': True,
            'achievement': True,
            'milestone': True
        })
        
        self.user_preferences = {}
        self.notification_queue = []
        
    def is_enabled(self):
        return self.enabled
    
    def is_type_enabled(self, notification_type):
        return self.notification_types.get(notification_type, False)
    
    def enable_type(self, notification_type):
        self.notification_types[notification_type] = True
        self._save_preferences()
    
    def disable_type(self, notification_type):
        self.notification_types[notification_type] = False
        self._save_preferences()
    
    def set_user_preferences(self, user_id, preferences):
        self.user_preferences[user_id] = preferences
        self._save_preferences()
    
    def get_user_preferences(self, user_id):
        return self.user_preferences.get(user_id, {
            'daily_reminder': True,
            'review_reminder': True,
            'achievement': True,
            'milestone': True,
            'quiet_hours': {'start': '22:00', 'end': '08:00'}
        })
    
    def _save_preferences(self):
        try:
            self.config.set('notifications.types', self.notification_types)
            self.config.set('notifications.user_preferences', self.user_preferences)
        except Exception:
            pass
    
    def send_daily_reminder(self, user_id, pending_tasks):
        if not self.is_enabled() or not self.is_type_enabled('daily_reminder'):
            return False
        
        preferences = self.get_user_preferences(user_id)
        
        if not preferences.get('daily_reminder'):
            return False
        
        if self._is_quiet_hours(preferences.get('quiet_hours')):
            return False
        
        notification = {
            'type': 'daily_reminder',
            'user_id': user_id,
            'title': '学习提醒',
            'body': f'您今天还有 {len(pending_tasks)} 个学习任务未完成',
            'data': {
                'tasks': pending_tasks,
                'action': 'start_learning'
            },
            'timestamp': self._get_current_timestamp()
        }
        
        self._queue_notification(notification)
        return True
    
    def send_review_reminder(self, user_id, review_count, languages):
        if not self.is_enabled() or not self.is_type_enabled('review_reminder'):
            return False
        
        preferences = self.get_user_preferences(user_id)
        
        if not preferences.get('review_reminder'):
            return False
        
        if self._is_quiet_hours(preferences.get('quiet_hours')):
            return False
        
        lang_names = '、'.join(languages)
        notification = {
            'type': 'review_reminder',
            'user_id': user_id,
            'title': '复习提醒',
            'body': f'您有 {review_count} 个{lang_names}词汇需要复习',
            'data': {
                'review_count': review_count,
                'languages': languages,
                'action': 'start_review'
            },
            'timestamp': self._get_current_timestamp()
        }
        
        self._queue_notification(notification)
        return True
    
    def send_achievement_notification(self, user_id, achievement_name, description):
        if not self.is_enabled() or not self.is_type_enabled('achievement'):
            return False
        
        preferences = self.get_user_preferences(user_id)
        
        if not preferences.get('achievement'):
            return False
        
        notification = {
            'type': 'achievement',
            'user_id': user_id,
            'title': '🎉 成就解锁',
            'body': f'恭喜您解锁成就: {achievement_name}',
            'data': {
                'achievement_name': achievement_name,
                'description': description,
                'action': 'view_achievement'
            },
            'timestamp': self._get_current_timestamp()
        }
        
        self._queue_notification(notification)
        return True
    
    def send_milestone_notification(self, user_id, milestone_name, progress):
        if not self.is_enabled() or not self.is_type_enabled('milestone'):
            return False
        
        preferences = self.get_user_preferences(user_id)
        
        if not preferences.get('milestone'):
            return False
        
        notification = {
            'type': 'milestone',
            'user_id': user_id,
            'title': '🏆 里程碑达成',
            'body': f'恭喜您达成{milestone_name}! 当前进度: {progress}%',
            'data': {
                'milestone_name': milestone_name,
                'progress': progress,
                'action': 'view_progress'
            },
            'timestamp': self._get_current_timestamp()
        }
        
        self._queue_notification(notification)
        return True
    
    def send_custom_notification(self, user_id, title, body, data=None):
        if not self.is_enabled():
            return False
        
        notification = {
            'type': 'custom',
            'user_id': user_id,
            'title': title,
            'body': body,
            'data': data or {},
            'timestamp': self._get_current_timestamp()
        }
        
        self._queue_notification(notification)
        return True
    
    def _queue_notification(self, notification):
        self.notification_queue.append(notification)
        self._process_queue()
    
    def _process_queue(self):
        while self.notification_queue:
            notification = self.notification_queue.pop(0)
            self._deliver_notification(notification)
    
    def _deliver_notification(self, notification):
        try:
            import requests
            
            api_url = self.config.get('notifications.api_url', 'http://localhost:5000/api/notifications')
            api_key = self.config.get('notifications.api_key')
            
            headers = {'Content-Type': 'application/json'}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            response = requests.post(
                api_url,
                json=notification,
                headers=headers,
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to deliver notification: {e}")
            return False
    
    def _is_quiet_hours(self, quiet_hours):
        if not quiet_hours:
            return False
        
        try:
            from datetime import datetime, time
            
            now = datetime.now().time()
            start_time = datetime.strptime(quiet_hours.get('start', '22:00'), '%H:%M').time()
            end_time = datetime.strptime(quiet_hours.get('end', '08:00'), '%H:%M').time()
            
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:
                return now >= start_time or now <= end_time
        except Exception:
            return False
    
    def _get_current_timestamp(self):
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_pending_notifications(self, user_id):
        return [
            notif for notif in self.notification_queue
            if notif['user_id'] == user_id
        ]
    
    def clear_user_notifications(self, user_id):
        self.notification_queue = [
            notif for notif in self.notification_queue
            if notif['user_id'] != user_id
        ]
    
    def get_notification_stats(self):
        stats = {
            'total_queued': len(self.notification_queue),
            'by_type': {},
            'by_user': {}
        }
        
        for notif in self.notification_queue:
            notif_type = notif['type']
            user_id = notif['user_id']
            
            stats['by_type'][notif_type] = stats['by_type'].get(notif_type, 0) + 1
            stats['by_user'][user_id] = stats['by_user'].get(user_id, 0) + 1
        
        return stats
