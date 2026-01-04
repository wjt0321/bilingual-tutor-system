"""
Operations Routes
运维路由 - 提供系统诊断、日志管理、缓存管理等功能
"""

from flask import Blueprint, request, jsonify, send_file
from datetime import datetime

from bilingual_tutor.infrastructure.operations_manager import operations_manager

operations_bp = Blueprint('operations', __name__)


@operations_bp.route('/operations', methods=['GET'])
def operations_dashboard():
    """运维仪表板页面"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>运维工具 - 双语导师系统</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <div class="main-content">
            <h1>运维工具</h1>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 30px;">
                <div class="card" style="padding: 20px;">
                    <h3>系统诊断</h3>
                    <p>运行系统诊断检查</p>
                    <button class="btn-primary" onclick="location.href='/api/operations/diagnostics'">运行诊断</button>
                </div>
                <div class="card" style="padding: 20px;">
                    <h3>日志管理</h3>
                    <p>查看和管理系统日志</p>
                    <button class="btn-primary" onclick="location.href='/api/operations/logs'">查看日志</button>
                </div>
                <div class="card" style="padding: 20px;">
                    <h3>缓存管理</h3>
                    <p>清理和管理系统缓存</p>
                    <button class="btn-primary" onclick="location.href='/api/operations/cache'">管理缓存</button>
                </div>
                <div class="card" style="padding: 20px;">
                    <h3>备份管理</h3>
                    <p>创建和管理系统备份</p>
                    <button class="btn-primary" onclick="location.href='/api/operations/backups'">管理备份</button>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


@operations_bp.route('/api/operations/overview', methods=['GET'])
def get_operations_overview():
    """
    获取运维概览
    """
    try:
        overview = operations_manager.get_system_overview()
        
        return jsonify({
            'success': True,
            'data': overview,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取运维概览失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/diagnostics', methods=['GET'])
def run_diagnostics():
    """
    运行系统诊断
    """
    try:
        result = operations_manager.run_diagnostic_check()
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'运行诊断失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/system-info', methods=['GET'])
def get_system_info():
    """
    获取系统信息
    """
    try:
        system_info = operations_manager.diagnostics.get_system_info()
        
        return jsonify({
            'success': True,
            'data': system_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取系统信息失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/dependencies', methods=['GET'])
def check_dependencies():
    """
    检查依赖项
    """
    try:
        dependencies = operations_manager.diagnostics.check_dependencies()
        
        return jsonify({
            'success': True,
            'data': dependencies
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'检查依赖失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/logs', methods=['GET'])
def get_logs():
    """
    获取日志文件列表
    
    Query参数:
        - filename: 文件名(可选)
        - lines: 读取行数(默认100)
    """
    try:
        filename = request.args.get('filename')
        lines = int(request.args.get('lines', 100))
        
        if filename:
            log_content = operations_manager.log_manager.read_log_file(filename, lines)
            return jsonify({
                'success': True,
                'data': log_content
            })
        else:
            log_files = operations_manager.log_manager.get_log_files()
            return jsonify({
                'success': True,
                'data': log_files
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取日志失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/logs/search', methods=['GET'])
def search_logs():
    """
    搜索日志
    
    Query参数:
        - query: 搜索关键词
        - filename: 文件名筛选(可选)
        - max_results: 最大结果数(默认100)
    """
    try:
        query = request.args.get('query', '')
        filename = request.args.get('filename')
        max_results = int(request.args.get('max_results', 100))
        
        if not query:
            return jsonify({'success': False, 'message': '请提供搜索关键词'}), 400
        
        results = operations_manager.log_manager.search_logs(query, filename, max_results)
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'搜索日志失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/logs/cleanup', methods=['POST'])
def cleanup_logs():
    """
    清理旧日志
    
    Body参数:
        - days: 保留天数(默认30)
    """
    try:
        data = request.get_json() or {}
        days = int(data.get('days', 30))
        
        deleted_count = operations_manager.log_manager.delete_old_logs(days)
        
        return jsonify({
            'success': True,
            'message': f'已删除 {deleted_count} 个旧日志文件',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'清理日志失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/cache', methods=['GET'])
def get_cache_info():
    """
    获取缓存信息
    """
    try:
        cache_info = operations_manager.cache_manager.get_cache_info()
        cache_files = operations_manager.cache_manager.get_cache_files()
        
        return jsonify({
            'success': True,
            'data': {
                'info': cache_info,
                'files': cache_files
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取缓存信息失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/cache/clear', methods=['POST'])
def clear_cache():
    """
    清除缓存
    
    Body参数:
        - pattern: 文件匹配模式(默认*)
    """
    try:
        data = request.get_json() or {}
        pattern = data.get('pattern', '*')
        
        cleared_count = operations_manager.cache_manager.clear_cache(pattern)
        
        return jsonify({
            'success': True,
            'message': f'已清除 {cleared_count} 个缓存文件',
            'cleared_count': cleared_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'清除缓存失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/backups', methods=['GET'])
def get_backups():
    """
    获取备份列表
    """
    try:
        backups = operations_manager.backup_manager.list_backups()
        
        return jsonify({
            'success': True,
            'data': backups,
            'count': len(backups)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取备份列表失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/backups/create', methods=['POST'])
def create_backup():
    """
    创建备份
    
    Body参数:
        - source_dir: 源目录
        - backup_name: 备份名称(可选)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        source_dir = data.get('source_dir', 'bilingual_tutor')
        backup_name = data.get('backup_name')
        
        result = operations_manager.backup_manager.create_backup(source_dir, backup_name)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': '备份创建成功',
                'data': result
            })
        else:
            return jsonify(result), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'创建备份失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/backups/restore', methods=['POST'])
def restore_backup():
    """
    恢复备份
    
    Body参数:
        - backup_name: 备份名称
        - target_dir: 目标目录
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        backup_name = data.get('backup_name')
        target_dir = data.get('target_dir', 'bilingual_tutor')
        
        if not backup_name:
            return jsonify({'success': False, 'message': '备份名称不能为空'}), 400
        
        result = operations_manager.backup_manager.restore_backup(backup_name, target_dir)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': '备份恢复成功',
                'data': result
            })
        else:
            return jsonify(result), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'恢复备份失败: {str(e)}'
        }), 500


@operations_bp.route('/api/operations/backups/<backup_name>/delete', methods=['DELETE'])
def delete_backup(backup_name: str):
    """
    删除备份
    """
    try:
        result = operations_manager.backup_manager.delete_backup(backup_name)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': '备份删除成功'
            })
        else:
            return jsonify(result), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除备份失败: {str(e)}'
        }), 500
