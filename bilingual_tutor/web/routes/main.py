"""
Main page routes
双语导师系统主页面路由
"""

from flask import Blueprint, render_template, session, redirect, url_for

main_bp = Blueprint('main', __name__)

def require_login(f):
    """Decorator to require login for page access"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login_page'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@main_bp.route('/')
@require_login
def index():
    """Home page / Dashboard."""
    return render_template('index.html', user_id=session.get('user_id'))

@main_bp.route('/login')
def login_page():
    """Login page."""
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    return render_template('login.html')

@main_bp.route('/register')
def register_page():
    """Register page."""
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    return render_template('register.html')

@main_bp.route('/learn')
@require_login
def learn_page():
    """Learning activity page."""
    return render_template('learn.html', user_id=session.get('user_id'))

@main_bp.route('/progress')
@require_login
def progress_page():
    """Progress report page."""
    return render_template('progress.html', user_id=session.get('user_id'))

@main_bp.route('/settings')
@require_login
def settings_page():
    """Settings page."""
    return render_template('settings.html', user_id=session.get('user_id'))

@main_bp.route('/preview')
def preview_page():
    """UI/UX preview page."""
    return render_template('preview.html')

@main_bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@main_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('errors/500.html'), 500