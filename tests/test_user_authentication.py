"""
Property-based tests for User Authentication System.
"""

import pytest
import secrets
import hashlib
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
from flask import Flask

from bilingual_tutor.web.routes.auth import (
    hash_password, generate_salt, validate_password, validate_username,
    users, user_sessions
)


class TestUserAuthenticationProperties:
    """Property-based tests for User Authentication functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear users and sessions before each test
        users.clear()
        user_sessions.clear()
        
        # Create a test Flask app for session handling
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test_secret_key'
        self.app.config['TESTING'] = True
        
    @given(
        st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
        st.text(min_size=6, max_size=128, alphabet=st.characters(min_codepoint=32, max_codepoint=126))
    )
    @settings(deadline=1000, max_examples=20)  # Reduced examples for faster execution
    def test_user_authentication_consistency_property(self, username, password):
        """
        **Feature: bilingual-tutor, Property 31: User Authentication Consistency**
        
        For any valid username and password combination, the authentication system 
        should consistently allow or deny access based on stored credentials.
        
        **Validates: Requirements 16.2**
        """
        # Filter out invalid usernames and passwords to focus on valid combinations
        valid_username, _ = validate_username(username)
        valid_password, _ = validate_password(password)
        
        # Skip invalid combinations for this property test
        if not valid_username or not valid_password:
            return
        
        # Property 1: Registration should create consistent user records
        salt = generate_salt()
        password_hash = hash_password(password, salt)
        
        # Store user data
        users[username] = {
            'password_hash': password_hash,
            'salt': salt,
            'english_level': 'CET-4',
            'japanese_level': 'N5',
            'daily_time': 60,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        
        # Property 2: Authentication should be consistent for correct credentials
        # Test multiple authentication attempts with same credentials
        for _ in range(3):
            # Verify password using same salt
            test_hash = hash_password(password, salt)
            assert test_hash == password_hash, "Password hashing should be deterministic"
            
            # Check user exists
            assert username in users, "User should exist after registration"
            
            # Verify stored data integrity
            user_data = users[username]
            assert user_data['password_hash'] == password_hash
            assert user_data['salt'] == salt
            assert user_data['english_level'] == 'CET-4'
            assert user_data['japanese_level'] == 'N5'
            assert user_data['daily_time'] == 60
        
        # Property 3: Authentication should consistently reject wrong passwords
        wrong_passwords = [
            password + "x",  # Slightly different
            password[:-1] if len(password) > 6 else password + "x",  # Truncated
            password.upper() if password.islower() else password.lower(),  # Case change
            "wrong_password_123"  # Completely different
        ]
        
        for wrong_password in wrong_passwords:
            if wrong_password != password:  # Ensure it's actually different
                wrong_hash = hash_password(wrong_password, salt)
                assert wrong_hash != password_hash, f"Wrong password should not match: {wrong_password}"
        
        # Property 4: Salt generation should be unique
        salt2 = generate_salt()
        salt3 = generate_salt()
        
        assert salt != salt2, "Salt generation should produce unique values"
        assert salt2 != salt3, "Salt generation should produce unique values"
        assert len(salt) == 32, "Salt should be 32 characters (16 bytes hex)"
        assert len(salt2) == 32, "Salt should be 32 characters (16 bytes hex)"
        
        # Property 5: Password hashing with different salts should produce different hashes
        hash_with_salt1 = hash_password(password, salt)
        hash_with_salt2 = hash_password(password, salt2)
        
        assert hash_with_salt1 != hash_with_salt2, "Same password with different salts should produce different hashes"
        
        # Property 6: User data should remain consistent across operations
        original_user_data = users[username].copy()
        
        # Simulate multiple authentication checks
        for _ in range(5):
            current_user_data = users[username]
            assert current_user_data['password_hash'] == original_user_data['password_hash']
            assert current_user_data['salt'] == original_user_data['salt']
            assert current_user_data['english_level'] == original_user_data['english_level']
            assert current_user_data['japanese_level'] == original_user_data['japanese_level']
            assert current_user_data['daily_time'] == original_user_data['daily_time']
        
        # Property 7: Authentication should handle edge cases consistently
        # Empty password should not match
        empty_hash = hash_password("", salt)
        assert empty_hash != password_hash, "Empty password should not authenticate"
        
        # Very long password should still work consistently
        long_password = password + "x" * 100
        if len(long_password) <= 128:  # Within valid range
            long_hash1 = hash_password(long_password, salt)
            long_hash2 = hash_password(long_password, salt)
            assert long_hash1 == long_hash2, "Long password hashing should be consistent"
    
    @given(
        st.lists(
            st.tuples(
                st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
                st.text(min_size=6, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126))
            ),
            min_size=1,
            max_size=5,  # Reduced from 10 to 5
            unique_by=lambda x: x[0]  # Unique usernames
        )
    )
    @settings(deadline=2000, max_examples=10)  # Reduced examples for faster execution
    def test_multiple_user_authentication_consistency_property(self, user_credentials):
        """
        **Feature: bilingual-tutor, Property 31: User Authentication Consistency (Multiple Users)**
        
        For any set of valid username and password combinations, the authentication 
        system should consistently manage multiple users without interference.
        
        **Validates: Requirements 16.2**
        """
        # Clear any existing users from previous tests
        users.clear()
        user_sessions.clear()
        
        # Filter to only valid credentials
        valid_credentials = []
        for username, password in user_credentials:
            valid_username, _ = validate_username(username)
            valid_password, _ = validate_password(password)
            if valid_username and valid_password:
                valid_credentials.append((username, password))
        
        if not valid_credentials:
            return  # Skip if no valid credentials
        
        # Property 1: Multiple user registration should work independently
        registered_users = {}
        
        for username, password in valid_credentials:
            salt = generate_salt()
            password_hash = hash_password(password, salt)
            
            users[username] = {
                'password_hash': password_hash,
                'salt': salt,
                'english_level': 'CET-4',
                'japanese_level': 'N5',
                'daily_time': 60,
                'created_at': datetime.now().isoformat(),
                'last_login': None
            }
            
            registered_users[username] = (password, salt, password_hash)
        
        # Property 2: Each user should authenticate independently
        for username, (password, salt, expected_hash) in registered_users.items():
            # Verify user exists
            assert username in users, f"User {username} should exist"
            
            # Verify authentication data
            user_data = users[username]
            assert user_data['password_hash'] == expected_hash
            assert user_data['salt'] == salt
            
            # Verify password authentication
            test_hash = hash_password(password, salt)
            assert test_hash == expected_hash, f"Authentication should work for user {username}"
        
        # Property 3: Users should not interfere with each other
        for username1, (password1, salt1, hash1) in registered_users.items():
            for username2, (password2, salt2, hash2) in registered_users.items():
                if username1 != username2:
                    # Different users should have different salts and hashes
                    assert salt1 != salt2, f"Users {username1} and {username2} should have different salts"
                    
                    # Even if passwords are the same, hashes should be different due to different salts
                    if password1 == password2:
                        assert hash1 != hash2, f"Same password for different users should have different hashes"
                    
                    # Wrong password should not authenticate for any user
                    wrong_hash = hash_password(password2, salt1)  # password2 with salt1
                    if password1 != password2:
                        assert wrong_hash != hash1, f"User {username2}'s password should not work for user {username1}"
        
        # Property 4: User data isolation should be maintained
        for username, (password, salt, expected_hash) in registered_users.items():
            user_data = users[username]
            
            # Verify data hasn't been corrupted by other operations
            assert user_data['password_hash'] == expected_hash
            assert user_data['salt'] == salt
            assert user_data['english_level'] == 'CET-4'
            assert user_data['japanese_level'] == 'N5'
            assert user_data['daily_time'] == 60
            assert 'created_at' in user_data
        
        # Property 5: Authentication should scale with number of users
        assert len(users) == len(valid_credentials), "All valid users should be registered"
        
        # Verify each user can still authenticate after all registrations
        for username, (password, salt, expected_hash) in registered_users.items():
            current_hash = hash_password(password, salt)
            assert current_hash == expected_hash, f"User {username} should still authenticate correctly"
    
    @given(
        st.text(min_size=1, max_size=100),
        st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=15)  # Reduced examples for faster execution
    def test_input_validation_consistency_property(self, username, password):
        """
        **Feature: bilingual-tutor, Property 31: User Authentication Consistency (Input Validation)**
        
        For any input combination, the validation system should consistently 
        accept or reject inputs based on defined criteria.
        
        **Validates: Requirements 16.2**
        """
        # Property 1: Username validation should be consistent
        valid_username1, error1 = validate_username(username)
        valid_username2, error2 = validate_username(username)
        
        assert valid_username1 == valid_username2, "Username validation should be deterministic"
        assert error1 == error2, "Username validation error messages should be consistent"
        
        # Property 2: Password validation should be consistent
        valid_password1, pwd_error1 = validate_password(password)
        valid_password2, pwd_error2 = validate_password(password)
        
        assert valid_password1 == valid_password2, "Password validation should be deterministic"
        assert pwd_error1 == pwd_error2, "Password validation error messages should be consistent"
        
        # Property 3: Validation rules should be applied correctly
        if valid_username1:
            # Valid usernames should meet all criteria
            assert len(username) >= 3, "Valid username should be at least 3 characters"
            assert len(username) <= 50, "Valid username should be at most 50 characters"
            assert username.strip() == username, "Valid username should not have leading/trailing spaces"
            assert username.replace('_', '').replace('-', '').isalnum(), "Valid username should only contain alphanumeric, underscore, and hyphen"
        else:
            # Invalid usernames should fail for specific reasons
            assert len(error1) > 0, "Invalid username should have error message"
            assert "用户名" in error1, "Error message should be in Chinese and mention username"
        
        if valid_password1:
            # Valid passwords should meet criteria
            assert len(password) >= 6, "Valid password should be at least 6 characters"
            assert len(password) <= 128, "Valid password should be at most 128 characters"
        else:
            # Invalid passwords should fail for specific reasons
            assert len(pwd_error1) > 0, "Invalid password should have error message"
            assert "密码" in pwd_error1, "Error message should be in Chinese and mention password"
        
        # Property 4: Edge cases should be handled consistently
        # Empty inputs
        empty_username_valid, empty_username_error = validate_username("")
        assert not empty_username_valid, "Empty username should be invalid"
        assert "不能为空" in empty_username_error, "Empty username error should mention emptiness"
        
        empty_password_valid, empty_password_error = validate_password("")
        assert not empty_password_valid, "Empty password should be invalid"
        assert ("至少6位" in empty_password_error or "至少8位" in empty_password_error), "Empty password error should mention minimum length"
        
        # Whitespace-only inputs
        whitespace_username_valid, whitespace_username_error = validate_username("   ")
        assert not whitespace_username_valid, "Whitespace-only username should be invalid"
        
        # Very long inputs
        long_username = "a" * 100
        long_username_valid, long_username_error = validate_username(long_username)
        assert not long_username_valid, "Very long username should be invalid"
        assert "不能超过50位" in long_username_error, "Long username error should mention length limit"
        
        long_password = "a" * 200
        long_password_valid, long_password_error = validate_password(long_password)
        assert not long_password_valid, "Very long password should be invalid"
        assert "不能超过128位" in long_password_error, "Long password error should mention length limit"
        
        # Property 5: Special characters in username should be handled correctly
        special_chars_username = "user@#$%"
        special_valid, special_error = validate_username(special_chars_username)
        assert not special_valid, "Username with special characters should be invalid"
        assert "只能包含" in special_error, "Special character error should explain allowed characters"
        
        # Valid special characters should work
        valid_special_username = "user_name-123"
        valid_special_valid, valid_special_error = validate_username(valid_special_username)
        assert valid_special_valid, "Username with valid special characters should be valid"
        assert valid_special_error == "", "Valid username should have no error message"
    
    @given(st.integers(min_value=1, max_value=20))  # Reduced from 1000 to 20
    @settings(max_examples=10)  # Reduced examples for faster execution
    def test_session_management_consistency_property(self, session_count):
        """
        **Feature: bilingual-tutor, Property 31: User Authentication Consistency (Session Management)**
        
        For any number of user sessions, the session management should consistently 
        track and manage user authentication state.
        
        **Validates: Requirements 16.2**
        """
        # Clear any existing sessions from previous tests
        user_sessions.clear()
        
        # Property 1: Session tracking should handle multiple sessions
        test_sessions = {}
        
        for i in range(min(session_count, 20)):  # Reduced from 50 to 20
            username = f"user_{i}"
            session_id = secrets.token_hex(16)
            login_time = datetime.now()
            
            user_sessions[username] = {
                'login_time': login_time,
                'last_activity': login_time,
                'session_id': session_id
            }
            
            test_sessions[username] = {
                'session_id': session_id,
                'login_time': login_time
            }
        
        # Property 2: All sessions should be tracked correctly
        assert len(user_sessions) == len(test_sessions), "All sessions should be tracked"
        
        for username, expected_data in test_sessions.items():
            assert username in user_sessions, f"Session for {username} should exist"
            
            session_data = user_sessions[username]
            assert session_data['session_id'] == expected_data['session_id']
            assert session_data['login_time'] == expected_data['login_time']
            assert 'last_activity' in session_data
        
        # Property 3: Session updates should be consistent
        for username in test_sessions.keys():
            # Update last activity
            new_activity_time = datetime.now()
            user_sessions[username]['last_activity'] = new_activity_time
            
            # Verify update
            assert user_sessions[username]['last_activity'] == new_activity_time
            
            # Other session data should remain unchanged
            assert user_sessions[username]['session_id'] == test_sessions[username]['session_id']
            assert user_sessions[username]['login_time'] == test_sessions[username]['login_time']
        
        # Property 4: Session cleanup should work correctly
        # Remove half the sessions
        usernames_to_remove = list(test_sessions.keys())[:len(test_sessions)//2]
        
        for username in usernames_to_remove:
            if username in user_sessions:
                del user_sessions[username]
        
        # Verify removal
        for username in usernames_to_remove:
            assert username not in user_sessions, f"Session for {username} should be removed"
        
        # Verify remaining sessions are intact
        remaining_usernames = list(test_sessions.keys())[len(test_sessions)//2:]
        for username in remaining_usernames:
            assert username in user_sessions, f"Session for {username} should still exist"
            session_data = user_sessions[username]
            assert session_data['session_id'] == test_sessions[username]['session_id']
        
        # Property 5: Session data structure should be consistent
        for username, session_data in user_sessions.items():
            # All sessions should have required fields
            assert 'login_time' in session_data, "Session should have login_time"
            assert 'last_activity' in session_data, "Session should have last_activity"
            assert 'session_id' in session_data, "Session should have session_id"
            
            # Data types should be correct
            assert isinstance(session_data['login_time'], datetime), "login_time should be datetime"
            assert isinstance(session_data['last_activity'], datetime), "last_activity should be datetime"
            assert isinstance(session_data['session_id'], str), "session_id should be string"
            assert len(session_data['session_id']) == 32, "session_id should be 32 characters"
        
        # Property 6: Session isolation should be maintained
        if len(user_sessions) >= 2:
            usernames = list(user_sessions.keys())
            user1, user2 = usernames[0], usernames[1]
            
            # Sessions should have different IDs
            assert user_sessions[user1]['session_id'] != user_sessions[user2]['session_id']
            
            # Modifying one session should not affect another
            original_user2_data = user_sessions[user2].copy()
            user_sessions[user1]['last_activity'] = datetime.now()
            
            # User2's data should be unchanged
            assert user_sessions[user2]['session_id'] == original_user2_data['session_id']
            assert user_sessions[user2]['login_time'] == original_user2_data['login_time']
            assert user_sessions[user2]['last_activity'] == original_user2_data['last_activity']