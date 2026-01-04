#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
双语导师系统 - Flask Web应用
Bilingual Tutor System - Flask Web Application

重构版本：
- 延迟初始化系统组件，避免导入时阻塞
- 简化路由结构
- 优化错误处理
- 移除可能导致测试卡住的组件
"""

import os
import sys
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 延迟导入，避免在模块级别初始化重型组件
_system_integrator = None
_learning_db = None

def get_system_integrator():
    """延迟初始化系统集成器"""
    global _system_integrator
    if _system_integrator is None:
        from bilingual_tutor.core.system_integrator import SystemIntegrator
        _system_integrator = SystemIntegrator()
    return _system_integrator

def get_learning_db():
    """延迟初始化学习数据库"""
    global _learning_db
    if _learning_db is None:
        from bilingual_tutor.storage.database import LearningDatabase
        _learning_db = LearningDatabase()
    return _learning_db

def create_app():
    """应用工厂模式，创建Flask应用"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # 基础安全配置
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32)),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
        SESSION_COOKIE_SECURE=False,  # 生产环境中使用HTTPS时设为True
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB最大文件上传
    )
    
    # 配置CORS
    CORS(app, 
         origins=['http://localhost:5000', 'http://127.0.0.1:5000'],
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    # 注册模块化路由（使用 routes 模块中的完整 blueprint 注册）
    from bilingual_tutor.web.routes import register_routes
    register_routes(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册健康检查 API
    @app.route('/api/health')
    def health_check():
        """健康检查API"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0'
        })
    
    return app


def register_error_handlers(app):
    """注册错误处理器"""
    
    @app.errorhandler(400)
    def bad_request(error):
        if request.is_json:
            return jsonify({'success': False, 'message': '请求格式错误'}), 400
        return render_template('error.html', message='请求格式错误'), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        if request.is_json:
            return jsonify({'success': False, 'message': '未授权访问'}), 401
        return redirect(url_for('login'))
    
    @app.errorhandler(404)
    def not_found(error):
        if request.is_json:
            return jsonify({'success': False, 'message': '资源未找到'}), 404
        return render_template('error.html', message='页面未找到'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if request.is_json:
            return jsonify({'success': False, 'message': '服务器内部错误'}), 500
        return render_template('error.html', message='服务器内部错误'), 500

# 创建应用实例（但不在模块级别初始化重型组件）
app = create_app()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("        双语导师系统 Web 服务")
    print("        Bilingual Tutor System Web Server")
    print("=" * 60)
    print("\n  访问地址: http://localhost:5000")
    print("  Access URL: http://localhost:5000")
    print("\n  按 Ctrl+C 停止服务器")
    print("=" * 60 + "\n")

    # 只在直接运行时显示系统状态
    try:
        print("🔧 系统状态检查...")
        print("   Web应用: 就绪")
        print("   数据库: 延迟加载")
        print("   AI服务: 延迟加载")
        print("   缓存系统: 延迟加载")
        print("")
    except Exception as e:
        print(f"⚠️  系统状态检查失败: {e}")
        print("")

    # 启动开发服务器
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True,
        use_reloader=True,
        use_debugger=True
    )