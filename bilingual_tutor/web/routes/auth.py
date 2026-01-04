"""
Authentication routes
双语导师系统认证路由
"""

from flask import Blueprint, request, jsonify, session, redirect, url_for
from datetime import datetime
import hashlib
import secrets

from bilingual_tutor.infrastructure.security_manager import security_manager

auth_bp = Blueprint('auth', __name__)

# In-memory user storage (for local use)
users = {
    "test_user": {
        "password_hash": "d0a69ef790021a27960c8afd4d110da0672c6ed34e75240327c75b3528c8b8ac", # hash_password("test_password_123", "fixed_salt_for_testing")
        "salt": "fixed_salt_for_testing",
        "english_level": "CET-4",
        "japanese_level": "N5",
        "daily_time": 60,
        "created_at": datetime.now().isoformat(),
        "last_login": None
    }
}
user_sessions = {}

def hash_password(password: str, salt: str) -> str:
    """Hash password with salt for security"""
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()

def generate_salt() -> str:
    """Generate random salt for password hashing"""
    return secrets.token_hex(16)

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    return security_manager.validate_password_strength(password)

def validate_username(username: str) -> tuple[bool, str]:
    """Validate username format"""
    if not username:
        return False, "用户名不能为空"
    if len(username) < 3:
        return False, "用户名长度至少3位"
    if len(username) > 50:
        return False, "用户名长度不能超过50位"
    if not username.replace('_', '').replace('-', '').isalnum():
        return False, "用户名只能包含字母、数字、下划线和连字符"
    return True, ""

def get_client_ip() -> str:
    """Get client IP address"""
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    return request.remote_addr or 'unknown'

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login API with enhanced security"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate input
        if not username or not password:
            return jsonify({'success': False, 'message': '请输入用户名和密码'}), 400
        
        # Check if user exists
        if username not in users:
            return jsonify({'success': False, 'message': '用户不存在，请先注册'}), 401
        
        user_data = users[username]
        
        # Verify password
        hashed_password = hash_password(password, user_data['salt'])
        if hashed_password != user_data['password_hash']:
            security_manager.log_security_event(
                'login_failed',
                username,
                {'reason': 'invalid_password'},
                get_client_ip(),
                success=False
            )
            return jsonify({'success': False, 'message': '密码错误'}), 401
        
        # Create session
        session['user_id'] = username
        session['login_time'] = datetime.now().isoformat()
        session.permanent = True
        
        # Track user session
        user_sessions[username] = {
            'login_time': datetime.now(),
            'last_activity': datetime.now(),
            'session_id': session.get('_id', secrets.token_hex(16))
        }
        
        # Log successful login
        security_manager.log_security_event(
            'login_success',
            username,
            {'session_id': session.get('_id')},
            get_client_ip(),
            success=True
        )
        
        return jsonify({
            'success': True, 
            'message': '登录成功', 
            'user_id': username,
            'login_time': session['login_time']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration API with enhanced validation"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        english_level = data.get('english_level', 'CET-4')
        japanese_level = data.get('japanese_level', 'N5')
        daily_time = data.get('daily_time', 60)
        
        # Validate username
        valid_username, username_error = validate_username(username)
        if not valid_username:
            return jsonify({'success': False, 'message': username_error}), 400
        
        # Validate password
        valid_password, password_error = validate_password(password)
        if not valid_password:
            return jsonify({'success': False, 'message': password_error}), 400
        
        # Check if user already exists
        if username in users:
            return jsonify({'success': False, 'message': '用户名已存在'}), 400
        
        # Validate other fields
        try:
            daily_time = int(daily_time)
            if daily_time < 15 or daily_time > 300:
                return jsonify({'success': False, 'message': '每日学习时间应在15-300分钟之间'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '每日学习时间格式错误'}), 400
        
        # Valid level options
        valid_english_levels = ['CET-4', 'CET-5', 'CET-6']
        valid_japanese_levels = ['N5', 'N4', 'N3', 'N2', 'N1']
        
        if english_level not in valid_english_levels:
            return jsonify({'success': False, 'message': '英语水平选择无效'}), 400
        
        if japanese_level not in valid_japanese_levels:
            return jsonify({'success': False, 'message': '日语水平选择无效'}), 400
        
        # Create user with hashed password
        salt = generate_salt()
        password_hash = hash_password(password, salt)
        
        users[username] = {
            'password_hash': password_hash,
            'salt': salt,
            'english_level': english_level,
            'japanese_level': japanese_level,
            'daily_time': daily_time,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        
        # Auto-login after registration
        session['user_id'] = username
        session['login_time'] = datetime.now().isoformat()
        session.permanent = True
        
        # Track user session
        user_sessions[username] = {
            'login_time': datetime.now(),
            'last_activity': datetime.now(),
            'session_id': session.get('_id', secrets.token_hex(16))
        }
        
        return jsonify({
            'success': True, 
            'message': '注册成功', 
            'user_id': username,
            'profile': {
                'english_level': english_level,
                'japanese_level': japanese_level,
                'daily_time': daily_time
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout API with session cleanup"""
    try:
        user_id = session.get('user_id')
        
        # Clean up user session tracking
        if user_id and user_id in user_sessions:
            del user_sessions[user_id]
        
        # Clear Flask session
        session.clear()
        
        return jsonify({'success': True, 'message': '已退出登录'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': '退出登录失败'}), 500

@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """Check authentication status"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'authenticated': False})
        
        # Update last activity
        if user_id in user_sessions:
            user_sessions[user_id]['last_activity'] = datetime.now()
        
        return jsonify({
            'authenticated': True,
            'user_id': user_id,
            'login_time': session.get('login_time'),
            'session_active': True
        })
        
    except Exception as e:
        return jsonify({'authenticated': False, 'error': '会话状态检查失败'}), 500

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'message': '请输入当前密码和新密码'}), 400
        
        # Validate new password
        valid_password, password_error = validate_password(new_password)
        if not valid_password:
            return jsonify({'success': False, 'message': password_error}), 400
        
        # Verify current password
        user_data = users.get(user_id)
        if not user_data:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        current_hash = hash_password(current_password, user_data['salt'])
        if current_hash != user_data['password_hash']:
            return jsonify({'success': False, 'message': '当前密码错误'}), 401
        
        # Update password
        new_salt = generate_salt()
        new_hash = hash_password(new_password, new_salt)
        
        users[user_id]['password_hash'] = new_hash
        users[user_id]['salt'] = new_salt
        users[user_id]['password_changed_at'] = datetime.now().isoformat()
        
        return jsonify({'success': True, 'message': '密码修改成功'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500