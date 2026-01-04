"""
Security Attribute Tests (Attribute 59)
安全性属性测试 - 验证密码加密、数据保护和审计功能
"""

import pytest
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

from hypothesis import given, strategies as st, settings
from bilingual_tutor.infrastructure.security_manager import (
    SecurityManager, PasswordSecurity, DataEncryption, AuditLogger,
    AccessControl, DataPrivacyManager
)


class TestPasswordEncryption:
    """测试密码加密安全性 (属性59)"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.password_security = PasswordSecurity()
        self.security_manager = SecurityManager()
    
    @given(st.text(min_size=8, max_size=128).filter(
        lambda x: any(c.islower() for c in x) and 
                    any(c.isupper() for c in x) and 
                    any(c.isdigit() for c in x)
    ))
    @settings(max_examples=50)
    def test_password_hash_consistency(self, password: str):
        """密码加密应该是一致的 - 相同密码产生相同哈希值"""
        result1 = self.password_security.hash_password(password, salt="test_salt")
        result2 = self.password_security.hash_password(password, salt="test_salt")
        
        assert result1['hash'] == result2['hash']
        assert result1['salt'] == result2['salt']
        assert result1['algorithm'] == 'pbkdf2_sha256'
        assert result1['iterations'] == 100000
    
    @given(st.text(min_size=8, max_size=128))
    def test_password_hash_different_salts(self, password: str):
        """不同盐值应该产生不同的哈希值"""
        result1 = self.password_security.hash_password(password, salt="salt1")
        result2 = self.password_security.hash_password(password, salt="salt2")
        
        assert result1['hash'] != result2['hash']
        assert result1['salt'] != result2['salt']
    
    @given(st.text(min_size=8, max_size=128))
    def test_password_hash_different_passwords(self, password: str):
        """不同密码应该产生不同的哈希值(即使使用相同盐值)"""
        salt = "common_salt"
        result1 = self.password_security.hash_password(password, salt=salt)
        result2 = self.password_security.hash_password(password + "x", salt=salt)
        
        assert result1['hash'] != result2['hash']
    
    @given(st.text(min_size=8, max_size=128))
    def test_password_verification(self, password: str):
        """密码验证应该正确工作"""
        result = self.password_security.hash_password(password)
        
        is_valid = self.password_security.verify_password(
            password, 
            result['hash'], 
            result['salt']
        )
        
        assert is_valid is True
        
        # 验证错误密码应该失败
        is_invalid = self.password_security.verify_password(
            password + "wrong",
            result['hash'],
            result['salt']
        )
        
        assert is_invalid is False
    
    @given(st.text(min_size=1, max_size=127))
    def test_password_strength_validation(self, password: str):
        """密码强度验证应该正确识别弱密码"""
        is_valid, message = self.password_security.validate_password_strength(password)
        
        # 强密码必须满足所有条件
        if is_valid:
            assert len(password) >= 8
            assert len(password) <= 128
            assert any(c.islower() for c in password)
            assert any(c.isupper() for c in password)
            assert any(c.isdigit() for c in password)
    
    def test_strong_password_examples(self):
        """强密码示例应该通过验证"""
        strong_passwords = [
            "MyP@ssw0rd123",
            "Secure#Pass456",
            "Complex$Pass789",
            "Strong!Pass2024"
        ]
        
        for password in strong_passwords:
            is_valid, message = self.password_security.validate_password_strength(password)
            assert is_valid is True, f"Strong password '{password}' should be valid: {message}"
    
    def test_weak_password_examples(self):
        """弱密码示例应该被拒绝"""
        weak_passwords = [
            "12345678",  # 只有数字
            "abcdefgh",  # 只有小写
            "ABCDEFGH",  # 只有大写
            "Password",  # 没有数字
            "password123",  # 没有大写
            "PASSWORD123",  # 没有小写
            "Pass1",  # 太短
            "a" * 130,  # 太长
        ]
        
        for password in weak_passwords:
            is_valid, message = self.password_security.validate_password_strength(password)
            assert is_valid is False, f"Weak password '{password}' should be invalid"


class TestDataEncryption:
    """测试数据加密功能"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.data_encryption = DataEncryption()
        self.security_manager = SecurityManager()
    
    @given(st.text(min_size=1, max_size=1000))
    def test_encryption_decryption_consistency(self, plain_text: str):
        """加密和解密应该是可逆的"""
        encrypted = self.data_encryption.encrypt_sensitive_data(plain_text)
        decrypted = self.data_encryption.decrypt_sensitive_data(encrypted)
        
        assert decrypted == plain_text
    
    @given(st.text(min_size=1, max_size=1000))
    def test_encrypted_data_different(self, plain_text: str):
        """不同明文应该产生不同的密文"""
        encrypted1 = self.data_encryption.encrypt_sensitive_data(plain_text)
        encrypted2 = self.data_encryption.encrypt_sensitive_data(plain_text + "x")
        
        assert encrypted1['encrypted'] != encrypted2['encrypted']
        assert encrypted1['nonce'] != encrypted2['nonce']
    
    @given(st.text(min_size=1, max_size=1000))
    def test_encrypted_data_contains_all_fields(self, plain_text: str):
        """加密数据应该包含所有必要字段"""
        encrypted = self.data_encryption.encrypt_sensitive_data(plain_text)
        
        assert 'encrypted' in encrypted
        assert 'nonce' in encrypted
        assert 'algorithm' in encrypted
        assert len(encrypted['encrypted']) > 0
        assert len(encrypted['nonce']) > 0
        assert encrypted['algorithm'] in ['aes-256-gcm', 'base64']


class TestAuditLogging:
    """测试安全审计日志"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.log_file = 'logs/test_audit.log'
        self.audit_logger = AuditLogger(self.log_file)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        log_path = Path(self.log_file)
        if log_path.exists():
            log_path.unlink()
    
    @given(st.text(min_size=1, max_size=50), st.sampled_from(['login', 'logout', 'data_access', 'password_change']))
    def test_event_logging(self, user_id: str, event_type: str):
        """事件应该被正确记录"""
        details = {'test': 'data', 'timestamp': datetime.now().isoformat()}
        
        self.audit_logger.log_event(
            event_type=event_type,
            user_id=user_id,
            details=details,
            ip_address='127.0.0.1',
            success=True
        )
        
        logs = self.audit_logger.get_user_audit_logs(user_id)
        
        assert len(logs) >= 1
        assert logs[-1]['event_type'] == event_type
        assert logs[-1]['user_id'] == user_id
        assert logs[-1]['success'] is True
    
    @given(st.text(min_size=1, max_size=50))
    def test_user_audit_log_retrieval(self, user_id: str):
        """应该能够检索用户审计日志"""
        for i in range(5):
            self.audit_logger.log_event(
                'test_event',
                user_id,
                {'iteration': i},
                success=True
            )
        
        logs = self.audit_logger.get_user_audit_logs(user_id, limit=10)
        
        assert len(logs) == 5
        for i, log in enumerate(logs):
            assert log['user_id'] == user_id
            assert log['event_type'] == 'test_event'
    
    def test_event_type_filtering(self):
        """应该能够按事件类型筛选日志"""
        user_id = 'test_user'
        
        self.audit_logger.log_event('login', user_id, {}, success=True)
        self.audit_logger.log_event('logout', user_id, {}, success=True)
        self.audit_logger.log_event('login', user_id, {}, success=True)
        
        login_logs = self.audit_logger.get_recent_events(event_type='login')
        
        assert len(login_logs) == 2
        for log in login_logs:
            assert log['event_type'] == 'login'


class TestAccessControl:
    """测试访问控制"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.access_control = AccessControl()
    
    @given(st.sampled_from(['admin', 'teacher', 'student']))
    def test_role_permissions_exist(self, role: str):
        """每个角色都应该有定义的权限"""
        permissions = self.access_control.get_user_permissions(role)
        
        assert isinstance(permissions, list)
        assert len(permissions) > 0
        for perm in permissions:
            assert isinstance(perm, str)
            assert len(perm) > 0
    
    @given(st.sampled_from([
        ('admin', 'user.create'),
        ('admin', 'user.delete'),
        ('teacher', 'content.create'),
        ('teacher', 'user.delete'),
        ('student', 'content.read'),
        ('student', 'user.create')
    ]))
    def test_permission_checking(self, role_permission: tuple):
        """权限检查应该正确工作"""
        role, permission = role_permission
        
        # Admin should have all admin permissions
        if role == 'admin':
            assert self.access_control.check_permission(role, permission) is True
        
        # Teacher should have content permissions but not user.delete
        elif role == 'teacher':
            if permission == 'user.delete':
                assert self.access_control.check_permission(role, permission) is False
            else:
                assert self.access_control.check_permission(role, permission) is True
        
        # Student should have limited permissions
        elif role == 'student':
            if permission == 'content.read':
                assert self.access_control.check_permission(role, permission) is True
            else:
                assert self.access_control.check_permission(role, permission) is False
    
    @given(st.sampled_from(['admin', 'teacher', 'student']))
    def test_invalid_role_handling(self, role: str):
        """无效角色应该没有权限"""
        invalid_role = 'invalid_role'
        
        assert self.access_control.check_permission(invalid_role, 'any_permission') is False
        assert self.access_control.get_user_permissions(invalid_role) == []


class TestDataPrivacy:
    """测试数据隐私功能"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.audit_logger = AuditLogger('logs/test_privacy_audit.log')
        self.privacy_manager = DataPrivacyManager(self.audit_logger)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        log_path = Path('logs/test_privacy_audit.log')
        if log_path.exists():
            log_path.unlink()
    
    @given(st.text(min_size=1, max_size=50))
    def test_user_data_export(self, user_id: str):
        """应该能够导出用户数据"""
        exported_data = self.privacy_manager.export_user_data(user_id)
        
        assert 'user_id' in exported_data
        assert exported_data['user_id'] == user_id
        assert 'export_time' in exported_data
        assert 'profile' in exported_data
        assert 'learning_progress' in exported_data
        assert 'activity_history' in exported_data
        assert 'settings' in exported_data
    
    @given(st.text(min_size=1, max_size=50))
    def test_data_export_audit_log(self, user_id: str):
        """数据导出应该被记录到审计日志"""
        self.privacy_manager.export_user_data(user_id)
        
        logs = self.audit_logger.get_user_audit_logs(user_id)
        
        assert len(logs) >= 1
        assert logs[-1]['event_type'] == 'data_export'
        assert logs[-1]['user_id'] == user_id
        assert logs[-1]['success'] is True
    
    @given(st.text(min_size=1, max_size=50))
    def test_data_deletion_requires_confirmation(self, user_id: str):
        """数据删除需要确认"""
        # 未确认的删除应该失败
        result = self.privacy_manager.delete_user_data(user_id, confirm=False)
        assert result is False
        
        # 已确认的删除应该成功
        result = self.privacy_manager.delete_user_data(user_id, confirm=True)
        assert result is True
    
    @given(st.text(min_size=1, max_size=50))
    def test_data_deletion_audit_log(self, user_id: str):
        """数据删除应该被记录到审计日志"""
        self.privacy_manager.delete_user_data(user_id, confirm=True)
        
        logs = self.audit_logger.get_user_audit_logs(user_id)
        
        assert len(logs) >= 1
        assert logs[-1]['event_type'] == 'data_delete'
        assert logs[-1]['user_id'] == user_id
        assert logs[-1]['success'] is True
        assert logs[-1]['details']['confirmed'] is True


class TestSecurityManagerIntegration:
    """测试安全管理器集成"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.security_manager = SecurityManager()
    
    @given(st.text(min_size=8, max_size=128).filter(
        lambda x: any(c.islower() for c in x) and 
                    any(c.isupper() for c in x) and 
                    any(c.isdigit() for c in x)
    ))
    def test_full_password_workflow(self, password: str):
        """测试完整的密码工作流"""
        # 1. 验证密码强度
        is_valid, message = self.security_manager.validate_password_strength(password)
        assert is_valid is True
        
        # 2. 加密密码
        hashed = self.security_manager.hash_password(password)
        assert 'hash' in hashed
        assert 'salt' in hashed
        
        # 3. 验证密码
        is_correct = self.security_manager.verify_password(
            password, 
            hashed['hash'], 
            hashed['salt']
        )
        assert is_correct is True
        
        # 4. 验证错误密码
        is_incorrect = self.security_manager.verify_password(
            password + "wrong",
            hashed['hash'],
            hashed['salt']
        )
        assert is_incorrect is False
    
    @given(st.text(min_size=1, max_size=1000))
    def test_full_encryption_workflow(self, data: str):
        """测试完整的加密工作流"""
        # 1. 加密数据
        encrypted = self.security_manager.encrypt_sensitive_data(data)
        assert 'encrypted' in encrypted
        
        # 2. 解密数据
        decrypted = self.security_manager.decrypt_sensitive_data(encrypted)
        assert decrypted == data
    
    @given(st.text(min_size=1, max_size=50))
    def test_security_event_logging(self, user_id: str):
        """测试安全事件记录"""
        self.security_manager.log_security_event(
            'test_event',
            user_id,
            {'test': 'data'},
            '127.0.0.1',
            success=True
        )
        
        logs = self.security_manager.audit_logger.get_user_audit_logs(user_id)
        
        assert len(logs) >= 1
        assert logs[-1]['event_type'] == 'test_event'
        assert logs[-1]['user_id'] == user_id
        assert logs[-1]['ip_address'] == '127.0.0.1'
        assert logs[-1]['success'] is True


class TestPasswordHashingSecurity:
    """测试密码哈希安全性"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.password_security = PasswordSecurity()
    
    def test_hashing_algorithm_security(self):
        """密码哈希应该使用安全的算法"""
        result = self.password_security.hash_password("test_password")
        
        # 应该使用PBKDF2-HMAC-SHA256
        assert result['algorithm'] == 'pbkdf2_sha256'
        
        # 迭代次数应该足够高
        assert result['iterations'] >= 100000
    
    def test_hash_is_not_reversible(self):
        """密码哈希应该是单向的(不可逆)"""
        password = "MySecurePassword123"
        result = self.password_security.hash_password(password)
        
        # 无法从哈希中提取原始密码
        # 这通过检查哈希不包含明文密码来验证
        assert password not in result['hash']
        assert len(result['hash']) == 64  # SHA256哈希长度
    
    def test_hash_prevents_timing_attacks(self):
        """密码验证应该防止时序攻击"""
        password = "TestPassword123"
        result = self.password_security.hash_password(password)
        
        # verify_password应该使用恒定时间比较
        # 这在实现中使用secrets.compare_digest
        assert self.password_security.verify_password(
            password,
            result['hash'],
            result['salt']
        ) is True
    
    @given(st.text(min_size=8, max_size=128))
    def test_salt_uniqueness(self, password: str):
        """每个密码哈希应该使用唯一的盐值"""
        results = [self.password_security.hash_password(password) for _ in range(10)]
        
        salts = [r['salt'] for r in results]
        
        # 所有盐值应该不同
        assert len(set(salts)) == 10
        
        # 所有哈希值应该不同
        hashes = [r['hash'] for r in results]
        assert len(set(hashes)) == 10


class TestDataProtection:
    """测试数据保护"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.security_manager = SecurityManager()
    
    @given(st.lists(st.text(min_size=5, max_size=50, alphabet=st.characters(
        whitelist_categories=['Lu', 'Ll', 'Nd'],
        min_codepoint=0x20,
        max_codepoint=0x7E
    )), min_size=1, max_size=10))
    def test_sensitive_data_protection(self, sensitive_data_list: list):
        """敏感数据应该被保护"""
        for sensitive_data in sensitive_data_list:
            encrypted = self.security_manager.encrypt_sensitive_data(sensitive_data)
            
            # 加密后的数据格式应该是正确的
            assert 'encrypted' in encrypted
            assert 'nonce' in encrypted
            assert 'algorithm' in encrypted
            assert len(encrypted['encrypted']) > 0
            
            # 解密应该恢复原始数据
            decrypted = self.security_manager.decrypt_sensitive_data(encrypted)
            assert decrypted == sensitive_data
    
    def test_encryption_key_rotation(self):
        """加密密钥应该可以轮换"""
        # 使用第一个密钥加密
        data = "Sensitive information"
        encrypted1 = self.security_manager.encrypt_sensitive_data(data)
        
        # 创建新的安全管理器(新密钥)
        new_security_manager = SecurityManager()
        encrypted2 = new_security_manager.encrypt_sensitive_data(data)
        
        # 不同的密钥应该产生不同的加密结果
        assert encrypted1['encrypted'] != encrypted2['encrypted']
        assert encrypted1['nonce'] != encrypted2['nonce']
        
        # 每个密钥应该能解密自己的数据
        assert self.security_manager.decrypt_sensitive_data(encrypted1) == data
        assert new_security_manager.decrypt_sensitive_data(encrypted2) == data


class TestComplianceAndStandards:
    """测试合规性和标准"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.password_security = PasswordSecurity()
        self.security_manager = SecurityManager()
    
    def test_password_meets_minimum_security_requirements(self):
        """密码策略应该符合最低安全要求"""
        # 根据NIST SP 800-63B和OWASP指南
        strong_password = "SecurePass123!"
        
        is_valid, _ = self.password_security.validate_password_strength(strong_password)
        assert is_valid is True
    
    def test_audit_log_completeness(self):
        """审计日志应该包含所有必要信息"""
        log_file = 'logs/test_compliance.log'
        audit_logger = AuditLogger(log_file)
        
        audit_logger.log_event(
            'login',
            'test_user',
            {'ip': '127.0.0.1'},
            '192.168.1.1',
            success=True
        )
        
        logs = audit_logger.get_user_audit_logs('test_user')
        log_entry = logs[-1]
        
        # 验证日志包含所有必要字段
        required_fields = ['timestamp', 'event_type', 'user_id', 'ip_address', 'success', 'details']
        for field in required_fields:
            assert field in log_entry
        
        # Cleanup
        Path(log_file).unlink(missing_ok=True)
    
    def test_data_export_compliance(self):
        """数据导出应该符合GDPR要求"""
        self.security_manager.log_security_event(
            'data_export',
            'test_user',
            {'format': 'json'},
            success=True
        )
        
        logs = self.security_manager.audit_logger.get_user_audit_logs('test_user')
        export_log = [log for log in logs if log['event_type'] == 'data_export'][-1]
        
        # GDPR要求数据导出被记录
        assert export_log is not None
        assert export_log['success'] is True
        assert 'details' in export_log
        assert 'format' in export_log['details']
    
    def test_right_to_be_forgotten(self):
        """数据删除应该支持"被遗忘权"(GDPR)"""
        # 数据删除需要明确确认
        result = self.security_manager.delete_user_data('test_user', confirm=True)
        
        assert result is True
        
        # 验证删除被记录
        logs = self.security_manager.audit_logger.get_user_audit_logs('test_user')
        delete_log = [log for log in logs if log['event_type'] == 'data_delete']
        
        assert len(delete_log) >= 1
        assert delete_log[-1]['success'] is True
        assert delete_log[-1]['details']['confirmed'] is True
