"""
Routes module initialization
双语导师系统路由模块初始化
"""

from flask import Blueprint

def register_routes(app):
    """Register all route blueprints with the Flask app"""
    # 只加载核心路由，避免阻塞初始化
    from bilingual_tutor.web.routes.auth import auth_bp
    from bilingual_tutor.web.routes.main import main_bp
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # API 路由已修复，现在可以安全启用
    from bilingual_tutor.web.routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

