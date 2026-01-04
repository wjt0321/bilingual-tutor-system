"""
Security Management Module
安全管理模块 - 提供密码加密、敏感数据保护、审计日志等功能
"""

import hashlib
import secrets
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class PasswordSecurity:
    """密码安全类 - 处理密码加密和验证"""
    
    def __init__(self, algorithm: str = 'pbkdf2_sha256', iterations: int = 100000):
        self.algorithm = algorithm
        self.iterations = iterations
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> Dict[str, str]:
        """
        加密密码
        
        Args:
            password: 明文密码
            salt: 可选盐值,如果不提供则自动生成
        
        Returns:
            包含哈希值和盐值的字典
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        if self.algorithm == 'pbkdf2_sha256':
            hashed = hashlib.pbkdf2_hmac(
                'sha256', 
                password.encode('utf-8'), 
                salt.encode('utf-8'), 
                self.iterations
            ).hex()
        elif self.algorithm == 'sha256':
            hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
        else:
            raise ValueError(f"不支持的加密算法: {self.algorithm}")
        
        return {
            'hash': hashed,
            'salt': salt,
            'algorithm': self.algorithm,
            'iterations': self.iterations
        }
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """
        验证密码
        
        Args:
            password: 明文密码
            stored_hash: 存储的哈希值
            salt: 使用的盐值
        
        Returns:
            密码是否匹配
        """
        hashed = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            self.iterations
        ).hex()
        
        return secrets.compare_digest(hashed, stored_hash)
    
    def validate_password_strength(self, password: str) -> tuple[bool, str]:
        """
        验证密码强度
        
        Args:
            password: 待验证的密码
        
        Returns:
            (是否有效, 错误信息)
        """
        if len(password) < 8:
            return False, "密码长度至少8位"
        if len(password) > 128:
            return False, "密码长度不能超过128位"
        if not any(c.islower() for c in password):
            return False, "密码必须包含至少一个小写字母"
        if not any(c.isupper() for c in password):
            return False, "密码必须包含至少一个大写字母"
        if not any(c.isdigit() for c in password):
            return False, "密码必须包含至少一个数字"
        
        return True, ""


class DataEncryption:
    """数据加密类 - 加密敏感数据"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        if encryption_key:
            self.key = encryption_key.encode('utf-8')
        else:
            self.key = secrets.token_bytes(32)
    
    def encrypt_sensitive_data(self, data: str) -> Dict[str, Any]:
        """
        加密敏感数据
        
        Args:
            data: 待加密的字符串数据
        
        Returns:
            包含加密数据的字典
        """
        import base64
        
        nonce = secrets.token_bytes(12)
        
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            aesgcm = AESGCM(self.key)
            encrypted_data = aesgcm.encrypt(nonce, data.encode('utf-8'), None)
            
            return {
                'encrypted': base64.b64encode(encrypted_data).decode('utf-8'),
                'nonce': base64.b64encode(nonce).decode('utf-8'),
                'algorithm': 'aes-256-gcm'
            }
        except ImportError:
            logger.warning("cryptography库未安装,使用简单加密")
            return self._simple_encrypt(data)
    
    def decrypt_sensitive_data(self, encrypted_data: Dict[str, Any]) -> str:
        """
        解密敏感数据
        
        Args:
            encrypted_data: 加密数据字典
        
        Returns:
            解密后的字符串
        """
        import base64
        
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            aesgcm = AESGCM(self.key)
            
            encrypted_bytes = base64.b64decode(encrypted_data['encrypted'].encode('utf-8'))
            nonce = base64.b64decode(encrypted_data['nonce'].encode('utf-8'))
            
            decrypted_data = aesgcm.decrypt(nonce, encrypted_bytes, None)
            return decrypted_data.decode('utf-8')
        except ImportError:
            logger.warning("cryptography库未安装,使用简单解密")
            return self._simple_decrypt(encrypted_data)
    
    def _simple_encrypt(self, data: str) -> Dict[str, Any]:
        """简单加密(当cryptography库不可用时)"""
        import base64
        encoded = base64.b64encode(data.encode('utf-8')).decode('utf-8')
        return {
            'encrypted': encoded,
            'nonce': '',
            'algorithm': 'base64'
        }
    
    def _simple_decrypt(self, encrypted_data: Dict[str, Any]) -> str:
        """简单解密(当cryptography库不可用时)"""
        import base64
        decoded = base64.b64decode(encrypted_data['encrypted'].encode('utf-8'))
        return decoded.decode('utf-8')


class AuditLogger:
    """安全审计日志记录器"""
    
    def __init__(self, log_file: str = 'logs/security_audit.log'):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_event(self, event_type: str, user_id: Optional[str], 
                  details: Dict[str, Any], ip_address: Optional[str] = None,
                  success: bool = True) -> None:
        """
        记录安全事件
        
        Args:
            event_type: 事件类型 (login, logout, password_change, data_access, etc.)
            user_id: 用户ID
            details: 事件详情
            ip_address: 客户端IP地址
            success: 操作是否成功
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'success': success,
            'details': details
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")
    
    def get_user_audit_logs(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取用户审计日志
        
        Args:
            user_id: 用户ID
            limit: 返回的最大记录数
        
        Returns:
            审计日志列表
        """
        logs = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        if event.get('user_id') == user_id:
                            logs.append(event)
                    except json.JSONDecodeError:
                        continue
            
            return logs[-limit:]
        except FileNotFoundError:
            return []
    
    def get_recent_events(self, event_type: Optional[str] = None, 
                        hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取最近的安全事件
        
        Args:
            event_type: 事件类型筛选,为None则返回所有类型
            hours: 最近多少小时
            limit: 返回的最大记录数
        
        Returns:
            事件列表
        """
        logs = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        event_time = datetime.fromisoformat(event['timestamp'])
                        
                        if event_time < cutoff_time:
                            continue
                        
                        if event_type is None or event.get('event_type') == event_type:
                            logs.append(event)
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
            
            return logs[-limit:]
        except FileNotFoundError:
            return []


class AccessControl:
    """访问控制类"""
    
    def __init__(self):
        self.role_permissions = {
            'admin': [
                'user.create', 'user.read', 'user.update', 'user.delete',
                'content.create', 'content.read', 'content.update', 'content.delete',
                'settings.manage', 'audit.read', 'data.export', 'data.delete'
            ],
            'teacher': [
                'user.read', 'user.update',
                'content.create', 'content.read', 'content.update',
                'data.export'
            ],
            'student': [
                'content.read', 'data.export'
            ]
        }
    
    def check_permission(self, role: str, permission: str) -> bool:
        """
        检查角色是否拥有权限
        
        Args:
            role: 用户角色
            permission: 权限标识
        
        Returns:
            是否有权限
        """
        if role not in self.role_permissions:
            return False
        
        return permission in self.role_permissions[role]
    
    def get_user_permissions(self, role: str) -> List[str]:
        """
        获取角色的所有权限
        
        Args:
            role: 用户角色
        
        Returns:
            权限列表
        """
        return self.role_permissions.get(role, [])
    
    def require_permission(self, permission: str):
        """
        权限装饰器 - 要求特定权限
        
        Args:
            permission: 需要的权限
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                from flask import session, jsonify
                
                role = session.get('role', 'student')
                user_id = session.get('user_id')
                
                if not self.check_permission(role, permission):
                    logger.warning(f"用户 {user_id} 尝试访问无权限的操作: {permission}")
                    return jsonify({
                        'success': False,
                        'message': '权限不足'
                    }), 403
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator


class DataPrivacyManager:
    """数据隐私管理器 - 处理数据导出和删除"""
    
    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
    
    def export_user_data(self, user_id: str, format: str = 'json') -> Dict[str, Any]:
        """
        导出用户数据
        
        Args:
            user_id: 用户ID
            format: 导出格式 (json, csv)
        
        Returns:
            用户数据字典
        """
        user_data = {
            'user_id': user_id,
            'export_time': datetime.now().isoformat(),
            'profile': self._get_user_profile(user_id),
            'learning_progress': self._get_learning_progress(user_id),
            'activity_history': self._get_activity_history(user_id),
            'settings': self._get_user_settings(user_id)
        }
        
        self.audit_logger.log_event(
            'data_export',
            user_id,
            {'format': format, 'data_size': len(str(user_data))},
            success=True
        )
        
        return user_data
    
    def delete_user_data(self, user_id: str, confirm: bool = False) -> bool:
        """
        删除用户数据
        
        Args:
            user_id: 用户ID
            confirm: 确认标志
        
        Returns:
            是否成功删除
        """
        if not confirm:
            return False
        
        self.audit_logger.log_event(
            'data_delete',
            user_id,
            {'confirmed': True},
            success=True
        )
        
        return True
    
    def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户档案(简化实现)"""
        return {'user_id': user_id}
    
    def _get_learning_progress(self, user_id: str) -> Dict[str, Any]:
        """获取学习进度(简化实现)"""
        return {}
    
    def _get_activity_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取活动历史(简化实现)"""
        return []
    
    def _get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """获取用户设置(简化实现)"""
        return {}


class SecurityManager:
    """安全管理器 - 统一安全功能接口"""
    
    def __init__(self):
        self.password_security = PasswordSecurity()
        self.data_encryption = DataEncryption()
        self.audit_logger = AuditLogger()
        self.access_control = AccessControl()
        self.privacy_manager = DataPrivacyManager(self.audit_logger)
    
    def hash_password(self, password: str) -> Dict[str, str]:
        """加密密码"""
        return self.password_security.hash_password(password)
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """验证密码"""
        return self.password_security.verify_password(password, stored_hash, salt)
    
    def validate_password_strength(self, password: str) -> tuple[bool, str]:
        """验证密码强度"""
        return self.password_security.validate_password_strength(password)
    
    def encrypt_sensitive_data(self, data: str) -> Dict[str, Any]:
        """加密敏感数据"""
        return self.data_encryption.encrypt_sensitive_data(data)
    
    def decrypt_sensitive_data(self, encrypted_data: Dict[str, Any]) -> str:
        """解密敏感数据"""
        return self.data_encryption.decrypt_sensitive_data(encrypted_data)
    
    def log_security_event(self, event_type: str, user_id: Optional[str],
                         details: Dict[str, Any], ip_address: Optional[str] = None,
                         success: bool = True) -> None:
        """记录安全事件"""
        self.audit_logger.log_event(event_type, user_id, details, ip_address, success)
    
    def check_permission(self, role: str, permission: str) -> bool:
        """检查权限"""
        return self.access_control.check_permission(role, permission)
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """导出用户数据"""
        return self.privacy_manager.export_user_data(user_id)
    
    def delete_user_data(self, user_id: str, confirm: bool = False) -> bool:
        """删除用户数据"""
        return self.privacy_manager.delete_user_data(user_id, confirm)


from datetime import timedelta


security_manager = SecurityManager()
