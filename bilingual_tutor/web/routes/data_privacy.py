"""
Data Privacy Routes
数据隐私路由 - 处理数据导出、删除和访问控制
"""

from flask import Blueprint, request, jsonify, session, send_file
from datetime import datetime
import json
import csv
import io
from pathlib import Path

from bilingual_tutor.infrastructure.security_manager import security_manager, AccessControl

data_privacy_bp = Blueprint('data_privacy', __name__)

access_control = AccessControl()


@data_privacy_bp.route('/api/data/export', methods=['GET', 'POST'])
def export_data():
    """
    导出用户数据
    
    支持格式: json, csv
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        # Check permission
        role = session.get('role', 'student')
        if not access_control.check_permission(role, 'data.export'):
            security_manager.log_security_event(
                'data_export_failed',
                user_id,
                {'reason': 'permission_denied'},
                request.remote_addr,
                success=False
            )
            return jsonify({'success': False, 'message': '权限不足'}), 403
        
        # Get format from request
        if request.method == 'POST':
            data = request.get_json() or {}
            export_format = data.get('format', 'json').lower()
        else:
            export_format = request.args.get('format', 'json').lower()
        
        if export_format not in ['json', 'csv']:
            return jsonify({'success': False, 'message': '不支持的导出格式'}), 400
        
        # Export user data
        user_data = security_manager.export_user_data(user_id, export_format)
        
        if export_format == 'json':
            return jsonify({
                'success': True,
                'message': '数据导出成功',
                'data': user_data,
                'export_time': datetime.now().isoformat()
            })
        elif export_format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write CSV data
            writer.writerow(['Category', 'Key', 'Value', 'Timestamp'])
            
            for category, items in user_data.items():
                if category in ['user_id', 'export_time']:
                    writer.writerow([category, '', str(items), user_data['export_time']])
                elif isinstance(items, dict):
                    for key, value in items.items():
                        writer.writerow([category, key, str(value), ''])
                elif isinstance(items, list):
                    for i, item in enumerate(items):
                        if isinstance(item, dict):
                            for key, value in item.items():
                                writer.writerow([category, f'{i}.{key}', str(value), ''])
                        else:
                            writer.writerow([category, str(i), str(item), ''])
            
            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'user_data_{user_id}_{datetime.now().strftime("%Y%m%d")}.csv'
            )
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'数据导出失败: {str(e)}'}), 500


@data_privacy_bp.route('/api/data/delete', methods=['POST'])
def delete_data():
    """
    删除用户数据
    
    需要二次确认
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        # Check permission
        role = session.get('role', 'student')
        if not access_control.check_permission(role, 'data.delete'):
            security_manager.log_security_event(
                'data_delete_failed',
                user_id,
                {'reason': 'permission_denied'},
                request.remote_addr,
                success=False
            )
            return jsonify({'success': False, 'message': '权限不足'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        confirm = data.get('confirm', False)
        confirmation_code = data.get('confirmation_code', '')
        
        # Verify confirmation code (username)
        if confirmation_code != user_id:
            return jsonify({
                'success': False,
                'message': '确认码不正确,请输入您的用户名'
            }), 400
        
        if not confirm:
            return jsonify({
                'success': False,
                'message': '请确认删除操作,此操作不可恢复'
            }), 400
        
        # Delete user data
        success = security_manager.delete_user_data(user_id, confirm=True)
        
        if success:
            security_manager.log_security_event(
                'data_delete_success',
                user_id,
                {'confirmed': True, 'method': 'user_request'},
                request.remote_addr,
                success=True
            )
            
            return jsonify({
                'success': True,
                'message': '用户数据已删除'
            })
        else:
            return jsonify({'success': False, 'message': '数据删除失败'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'数据删除失败: {str(e)}'}), 500


@data_privacy_bp.route('/api/data/audit-logs', methods=['GET'])
def get_audit_logs():
    """
    获取安全审计日志
    
    需要管理员权限
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        # Check permission
        role = session.get('role', 'student')
        if not access_control.check_permission(role, 'audit.read'):
            return jsonify({'success': False, 'message': '权限不足'}), 403
        
        # Get query parameters
        event_type = request.args.get('event_type')
        user_filter = request.args.get('user_id')
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 100))
        
        # Get audit logs
        logs = security_manager.audit_logger.get_recent_events(
            event_type=event_type,
            hours=hours,
            limit=limit
        )
        
        # Filter by user if specified
        if user_filter:
            logs = [log for log in logs if log.get('user_id') == user_filter]
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取审计日志失败: {str(e)}'}), 500


@data_privacy_bp.route('/api/data/user-logs', methods=['GET'])
def get_user_logs():
    """
    获取当前用户的审计日志
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        limit = int(request.args.get('limit', 50))
        
        logs = security_manager.audit_logger.get_user_audit_logs(user_id, limit)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取用户日志失败: {str(e)}'}), 500


@data_privacy_bp.route('/api/permissions', methods=['GET'])
def get_permissions():
    """
    获取当前用户的权限列表
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        role = session.get('role', 'student')
        permissions = access_control.get_user_permissions(role)
        
        return jsonify({
            'success': True,
            'role': role,
            'permissions': permissions
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取权限失败: {str(e)}'}), 500


@data_privacy_bp.route('/api/security/password-strength', methods=['POST'])
def check_password_strength():
    """
    检查密码强度
    
    不需要登录
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        password = data.get('password', '')
        
        is_valid, message = security_manager.validate_password_strength(password)
        
        # Calculate strength score
        score = 0
        if len(password) >= 8:
            score += 20
        if len(password) >= 12:
            score += 10
        if any(c.islower() for c in password):
            score += 15
        if any(c.isupper() for c in password):
            score += 15
        if any(c.isdigit() for c in password):
            score += 20
        if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            score += 20
        
        # Determine strength level
        if score < 40:
            level = 'weak'
            level_text = '弱'
        elif score < 70:
            level = 'medium'
            level_text = '中等'
        else:
            level = 'strong'
            level_text = '强'
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'message': message,
            'strength': {
                'score': score,
                'level': level,
                'text': level_text
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'检查密码强度失败: {str(e)}'}), 500


@data_privacy_bp.route('/api/security/encrypt', methods=['POST'])
def encrypt_data():
    """
    加密敏感数据
    
    需要登录
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        plain_text = data.get('data', '')
        
        if not plain_text:
            return jsonify({'success': False, 'message': '数据不能为空'}), 400
        
        encrypted = security_manager.encrypt_sensitive_data(plain_text)
        
        return jsonify({
            'success': True,
            'encrypted_data': encrypted
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'数据加密失败: {str(e)}'}), 500


@data_privacy_bp.route('/api/security/decrypt', methods=['POST'])
def decrypt_data():
    """
    解密敏感数据
    
    需要登录
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
        
        encrypted_data = data.get('encrypted_data', {})
        
        if not encrypted_data:
            return jsonify({'success': False, 'message': '加密数据不能为空'}), 400
        
        decrypted = security_manager.decrypt_sensitive_data(encrypted_data)
        
        return jsonify({
            'success': True,
            'decrypted_data': decrypted
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'数据解密失败: {str(e)}'}), 500
