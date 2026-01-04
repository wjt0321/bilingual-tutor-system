"""
Property-based tests for Personalized Dashboard Generation.
个性化仪表板生成属性测试
"""

import pytest
import json
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
from flask import Flask

from bilingual_tutor.web.app import create_app
from bilingual_tutor.models import UserProfile, Goals, Preferences, Skill, ContentType
from bilingual_tutor.core.engine import CoreLearningEngine


class TestPersonalizedDashboardProperties:
    """Property-based tests for Personalized Dashboard Generation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create test Flask app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Initialize engine
        self.engine = CoreLearningEngine()
        
        # Clear any existing data
        from bilingual_tutor.web.routes.auth import users, user_sessions
        from bilingual_tutor.web.routes.api import user_profiles, user_learning_sessions
        users.clear()
        user_sessions.clear()
        user_profiles.clear()
        user_learning_sessions.clear()
    
    def create_test_user(self, username, password="test_password_123"):
        """Helper to create and authenticate a test user."""
        # Register user
        register_data = {
            'username': username,
            'password': password,
            'english_level': 'CET-4',
            'japanese_level': 'N5',
            'daily_time': 60
        }
        
        register_response = self.client.post('/auth/register', 
                                           data=json.dumps(register_data),
                                           content_type='application/json')
        
        if register_response.status_code != 200:
            return None
        
        # Login user
        login_data = {'username': username, 'password': password}
        login_response = self.client.post('/auth/login',
                                        data=json.dumps(login_data),
                                        content_type='application/json')
        
        return login_response.status_code == 200
    
    @given(
        st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
        st.sampled_from(['CET-4', 'CET-5', 'CET-6']),
        st.sampled_from(['N5', 'N4', 'N3', 'N2', 'N1']),
        st.integers(min_value=30, max_value=120)
    )
    @settings(deadline=3000, max_examples=15)
    def test_personalized_dashboard_generation_property(self, username, english_level, japanese_level, daily_time):
        """
        **Feature: bilingual-tutor, Property 32: Personalized Dashboard Generation**
        
        For any authenticated user, the dashboard should display their specific 
        learning plan and progress data.
        
        **Validates: Requirements 16.3**
        """
        # Skip invalid usernames
        if not username.replace('_', '').replace('-', '').isalnum():
            return
        
        # Create and authenticate user
        with self.app.test_client() as client:
            # Register user with specific profile
            register_data = {
                'username': username,
                'password': 'test_password_123',
                'english_level': english_level,
                'japanese_level': japanese_level,
                'daily_time': daily_time
            }
            
            register_response = client.post('/auth/register', 
                                          data=json.dumps(register_data),
                                          content_type='application/json')
            
            if register_response.status_code != 200:
                return  # Skip if registration fails
            
            # Login user
            login_data = {'username': username, 'password': 'test_password_123'}
            login_response = client.post('/auth/login',
                                       data=json.dumps(login_data),
                                       content_type='application/json')
            
            if login_response.status_code != 200:
                return  # Skip if login fails
            
            # Property 1: Dashboard should be accessible for authenticated users
            dashboard_response = client.get('/')
            assert dashboard_response.status_code == 200, "Dashboard should be accessible for authenticated users"
            
            # Property 2: User profile API should return personalized data
            profile_response = client.get('/api/user/profile')
            assert profile_response.status_code == 200, "Profile API should be accessible"
            
            profile_data = json.loads(profile_response.data)
            assert profile_data['success'] is True, "Profile API should return success"
            assert 'profile' in profile_data, "Profile API should return profile data"
            
            profile = profile_data['profile']
            assert profile['user_id'] == username, "Profile should contain correct user ID"
            assert profile['english_level'] == english_level, "Profile should contain correct English level"
            assert profile['japanese_level'] == japanese_level, "Profile should contain correct Japanese level"
            assert profile['daily_study_time'] == daily_time, "Profile should contain correct daily study time"
            
            # Property 3: Learning plan should be personalized based on user profile
            plan_response = client.get('/api/learning/plan')
            assert plan_response.status_code == 200, "Learning plan API should be accessible"
            
            plan_data = json.loads(plan_response.data)
            assert plan_data['success'] is True, "Learning plan API should return success"
            assert 'plan' in plan_data, "Learning plan API should return plan data"
            
            plan = plan_data['plan']
            
            # Property 4: Time allocation should respect user's daily time setting
            assert plan['total_time'] <= daily_time, "Total planned time should not exceed user's daily time setting"
            assert plan['review_time'] > 0, "Review time should be allocated"
            assert plan['english_time'] >= 0, "English time should be non-negative"
            assert plan['japanese_time'] >= 0, "Japanese time should be non-negative"
            
            # Property 5: Time allocation should follow the 20% review rule
            expected_review_time = int(daily_time * 0.2)
            tolerance = 5  # Allow 5-minute tolerance
            assert abs(plan['review_time'] - expected_review_time) <= tolerance, \
                f"Review time should be approximately 20% of daily time (expected ~{expected_review_time}, got {plan['review_time']})"
            
            # Property 6: Activities should be appropriate for user's levels
            assert 'activities' in plan, "Plan should contain activities"
            activities = plan['activities']
            assert len(activities) > 0, "Plan should contain at least one activity"
            
            for activity in activities:
                assert 'language' in activity, "Activity should specify language"
                assert 'duration' in activity, "Activity should specify duration"
                assert 'type' in activity, "Activity should specify type"
                assert activity['duration'] > 0, "Activity duration should be positive"
                
                # Language-specific validation
                if activity['language'] == 'english':
                    # English activities should be appropriate for user's English level
                    assert activity['language_display'] == '英语', "English activities should be labeled in Chinese"
                elif activity['language'] == 'japanese':
                    # Japanese activities should be appropriate for user's Japanese level
                    assert activity['language_display'] == '日语', "Japanese activities should be labeled in Chinese"
                elif activity['language'] == 'mixed':
                    # Mixed activities (review) should be labeled appropriately
                    assert activity['language_display'] == '复习', "Review activities should be labeled in Chinese"
            
            # Property 7: Total activity duration should not exceed allocated time
            total_activity_duration = sum(activity['duration'] for activity in activities)
            assert total_activity_duration <= daily_time, \
                "Total activity duration should not exceed user's daily time limit"
            
            # Property 8: Progress data should be personalized and accessible
            progress_response = client.get('/api/progress/status')
            assert progress_response.status_code == 200, "Progress API should be accessible"
            
            progress_data = json.loads(progress_response.data)
            assert progress_data['success'] is True, "Progress API should return success"
            assert 'progress' in progress_data, "Progress API should return progress data"
            
            progress = progress_data['progress']
            assert 'vocabulary' in progress, "Progress should include vocabulary data"
            assert 'content_history' in progress, "Progress should include content history"
            
            # Property 9: Dashboard should provide learning objectives
            assert 'objectives' in plan, "Plan should contain learning objectives"
            objectives = plan['objectives']
            assert isinstance(objectives, list), "Objectives should be a list"
            
            # Property 10: All dashboard data should be consistent across API calls
            # Make multiple calls to ensure consistency
            for _ in range(3):
                profile_check = client.get('/api/user/profile')
                profile_check_data = json.loads(profile_check.data)
                
                assert profile_check_data['profile']['user_id'] == username
                assert profile_check_data['profile']['english_level'] == english_level
                assert profile_check_data['profile']['japanese_level'] == japanese_level
                assert profile_check_data['profile']['daily_study_time'] == daily_time
    
    @given(
        st.lists(
            st.tuples(
                st.text(min_size=3, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
                st.sampled_from(['CET-4', 'CET-5', 'CET-6']),
                st.sampled_from(['N5', 'N4', 'N3', 'N2', 'N1']),
                st.integers(min_value=30, max_value=120)
            ),
            min_size=1,
            max_size=3,
            unique_by=lambda x: x[0]  # Unique usernames
        )
    )
    @settings(deadline=5000, max_examples=8)
    def test_multiple_user_dashboard_isolation_property(self, user_data_list):
        """
        **Feature: bilingual-tutor, Property 32: Personalized Dashboard Generation (Multi-User)**
        
        For any set of authenticated users, each user's dashboard should display 
        only their specific learning plan and progress data without interference.
        
        **Validates: Requirements 16.3**
        """
        # Filter valid usernames
        valid_users = []
        for username, english_level, japanese_level, daily_time in user_data_list:
            if username.replace('_', '').replace('-', '').isalnum():
                valid_users.append((username, english_level, japanese_level, daily_time))
        
        if not valid_users:
            return
        
        # Create multiple users and verify dashboard isolation
        user_sessions = {}
        
        for username, english_level, japanese_level, daily_time in valid_users:
            with self.app.test_client() as client:
                # Register user
                register_data = {
                    'username': username,
                    'password': 'test_password_123',
                    'english_level': english_level,
                    'japanese_level': japanese_level,
                    'daily_time': daily_time
                }
                
                register_response = client.post('/auth/register', 
                                              data=json.dumps(register_data),
                                              content_type='application/json')
                
                if register_response.status_code != 200:
                    continue
                
                # Login user
                login_data = {'username': username, 'password': 'test_password_123'}
                login_response = client.post('/auth/login',
                                           data=json.dumps(login_data),
                                           content_type='application/json')
                
                if login_response.status_code != 200:
                    continue
                
                # Get user's personalized data
                profile_response = client.get('/api/user/profile')
                plan_response = client.get('/api/learning/plan')
                progress_response = client.get('/api/progress/status')
                
                if (profile_response.status_code == 200 and 
                    plan_response.status_code == 200 and 
                    progress_response.status_code == 200):
                    
                    user_sessions[username] = {
                        'profile': json.loads(profile_response.data),
                        'plan': json.loads(plan_response.data),
                        'progress': json.loads(progress_response.data),
                        'expected_english': english_level,
                        'expected_japanese': japanese_level,
                        'expected_daily_time': daily_time
                    }
        
        # Property 1: Each user should have distinct personalized data
        usernames = list(user_sessions.keys())
        for i, username1 in enumerate(usernames):
            for username2 in usernames[i+1:]:
                user1_data = user_sessions[username1]
                user2_data = user_sessions[username2]
                
                # Users should have different profiles
                profile1 = user1_data['profile']['profile']
                profile2 = user2_data['profile']['profile']
                
                assert profile1['user_id'] != profile2['user_id'], "Users should have different user IDs"
                
                # If users have different settings, their data should reflect that
                if (user1_data['expected_english'] != user2_data['expected_english'] or
                    user1_data['expected_japanese'] != user2_data['expected_japanese'] or
                    user1_data['expected_daily_time'] != user2_data['expected_daily_time']):
                    
                    # At least one aspect of their plans should be different
                    plan1 = user1_data['plan']['plan']
                    plan2 = user2_data['plan']['plan']
                    
                    different_aspects = (
                        profile1['english_level'] != profile2['english_level'] or
                        profile1['japanese_level'] != profile2['japanese_level'] or
                        profile1['daily_study_time'] != profile2['daily_study_time'] or
                        plan1['total_time'] != plan2['total_time']
                    )
                    
                    assert different_aspects, f"Users {username1} and {username2} with different settings should have different dashboard data"
        
        # Property 2: Each user's data should match their expected profile
        for username, session_data in user_sessions.items():
            profile = session_data['profile']['profile']
            plan = session_data['plan']['plan']
            
            assert profile['user_id'] == username, f"Profile should match username for {username}"
            assert profile['english_level'] == session_data['expected_english'], f"English level should match for {username}"
            assert profile['japanese_level'] == session_data['expected_japanese'], f"Japanese level should match for {username}"
            assert profile['daily_study_time'] == session_data['expected_daily_time'], f"Daily time should match for {username}"
            
            # Plan should respect user's time constraints
            assert plan['total_time'] <= session_data['expected_daily_time'], f"Plan should respect time limit for {username}"
        
        # Property 3: Dashboard data should be consistent for each user
        for username, session_data in user_sessions.items():
            with self.app.test_client() as client:
                # Re-login the user
                login_data = {'username': username, 'password': 'test_password_123'}
                login_response = client.post('/auth/login',
                                           data=json.dumps(login_data),
                                           content_type='application/json')
                
                if login_response.status_code == 200:
                    # Get data again and verify consistency
                    new_profile_response = client.get('/api/user/profile')
                    if new_profile_response.status_code == 200:
                        new_profile_data = json.loads(new_profile_response.data)
                        original_profile = session_data['profile']['profile']
                        new_profile = new_profile_data['profile']
                        
                        assert new_profile['user_id'] == original_profile['user_id']
                        assert new_profile['english_level'] == original_profile['english_level']
                        assert new_profile['japanese_level'] == original_profile['japanese_level']
                        assert new_profile['daily_study_time'] == original_profile['daily_study_time']
    
    @given(
        st.text(min_size=3, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
        st.sampled_from(['CET-4', 'CET-5', 'CET-6']),
        st.sampled_from(['N5', 'N4', 'N3', 'N2', 'N1']),
        st.integers(min_value=30, max_value=120)
    )
    @settings(deadline=2000, max_examples=10)
    def test_dashboard_content_personalization_property(self, username, english_level, japanese_level, daily_time):
        """
        **Feature: bilingual-tutor, Property 32: Personalized Dashboard Generation (Content Personalization)**
        
        For any authenticated user, the dashboard content should be personalized 
        based on their language levels and learning preferences.
        
        **Validates: Requirements 16.3**
        """
        # Skip invalid usernames
        if not username.replace('_', '').replace('-', '').isalnum():
            return
        
        with self.app.test_client() as client:
            # Create user with specific profile
            register_data = {
                'username': username,
                'password': 'test_password_123',
                'english_level': english_level,
                'japanese_level': japanese_level,
                'daily_time': daily_time
            }
            
            register_response = client.post('/auth/register', 
                                          data=json.dumps(register_data),
                                          content_type='application/json')
            
            if register_response.status_code != 200:
                return
            
            # Login user
            login_data = {'username': username, 'password': 'test_password_123'}
            login_response = client.post('/auth/login',
                                       data=json.dumps(login_data),
                                       content_type='application/json')
            
            if login_response.status_code != 200:
                return
            
            # Get learning plan
            plan_response = client.get('/api/learning/plan')
            assert plan_response.status_code == 200, "Learning plan should be accessible"
            
            plan_data = json.loads(plan_response.data)
            plan = plan_data['plan']
            activities = plan['activities']
            
            # Property 1: Activities should be appropriate for user's language levels
            english_activities = [a for a in activities if a['language'] == 'english']
            japanese_activities = [a for a in activities if a['language'] == 'japanese']
            
            # Property 2: Content difficulty should match user levels
            for activity in english_activities:
                # English activities should be appropriate for the user's English level
                assert 'difficulty' in activity, "English activities should have difficulty specified"
                # The difficulty should be related to the user's level
                if english_level == 'CET-4':
                    assert activity['difficulty'] in ['CET-4', 'beginner', 'intermediate'], \
                        f"CET-4 user should get appropriate difficulty, got {activity['difficulty']}"
                elif english_level == 'CET-6':
                    assert activity['difficulty'] in ['CET-6', 'intermediate', 'advanced'], \
                        f"CET-6 user should get appropriate difficulty, got {activity['difficulty']}"
            
            for activity in japanese_activities:
                # Japanese activities should be appropriate for the user's Japanese level
                assert 'difficulty' in activity, "Japanese activities should have difficulty specified"
                if japanese_level == 'N5':
                    assert activity['difficulty'] in ['N5', 'beginner'], \
                        f"N5 user should get appropriate difficulty, got {activity['difficulty']}"
                elif japanese_level == 'N1':
                    assert activity['difficulty'] in ['N1', 'advanced'], \
                        f"N1 user should get appropriate difficulty, got {activity['difficulty']}"
            
            # Property 3: Time allocation should be personalized
            total_allocated = plan['english_time'] + plan['japanese_time'] + plan['review_time']
            assert total_allocated <= daily_time, "Total allocated time should not exceed user's daily limit"
            
            # Property 4: Dashboard should show user-specific progress
            progress_response = client.get('/api/progress/status')
            if progress_response.status_code == 200:
                progress_data = json.loads(progress_response.data)
                progress = progress_data['progress']
                
                # Progress should be structured for the user's languages
                assert 'vocabulary' in progress, "Progress should include vocabulary tracking"
                assert 'content_history' in progress, "Progress should include content history"
            
            # Property 5: Learning objectives should be relevant to user's levels
            objectives = plan.get('objectives', [])
            assert isinstance(objectives, list), "Objectives should be a list"
            
            # Property 6: Dashboard should maintain user context across requests
            # Make multiple requests and verify user context is maintained
            for _ in range(3):
                context_check = client.get('/api/user/profile')
                if context_check.status_code == 200:
                    context_data = json.loads(context_check.data)
                    context_profile = context_data['profile']
                    
                    assert context_profile['user_id'] == username, "User context should be maintained"
                    assert context_profile['english_level'] == english_level, "English level should be consistent"
                    assert context_profile['japanese_level'] == japanese_level, "Japanese level should be consistent"
                    assert context_profile['daily_study_time'] == daily_time, "Daily time should be consistent"
    
    def test_unauthenticated_dashboard_access_property(self):
        """
        **Feature: bilingual-tutor, Property 32: Personalized Dashboard Generation (Authentication Required)**
        
        For any unauthenticated request, the dashboard should not be accessible 
        and should redirect to login.
        
        **Validates: Requirements 16.3**
        """
        with self.app.test_client() as client:
            # Property 1: Unauthenticated users should not access dashboard
            dashboard_response = client.get('/')
            # Should redirect to login (302) or show login page
            assert dashboard_response.status_code in [302, 401], \
                "Unauthenticated users should not access dashboard directly"
            
            # Property 2: API endpoints should require authentication
            api_endpoints = [
                '/api/user/profile',
                '/api/learning/plan',
                '/api/progress/status'
            ]
            
            for endpoint in api_endpoints:
                api_response = client.get(endpoint)
                assert api_response.status_code == 401, \
                    f"API endpoint {endpoint} should require authentication"
                
                if api_response.content_type == 'application/json':
                    api_data = json.loads(api_response.data)
                    assert api_data['success'] is False, \
                        f"API endpoint {endpoint} should return success=False for unauthenticated requests"
                    assert '登录' in api_data.get('message', ''), \
                        f"API endpoint {endpoint} should return Chinese login message"
            
            # Property 3: Login page should be accessible
            login_response = client.get('/login')
            assert login_response.status_code == 200, "Login page should be accessible to unauthenticated users"
            
            # Property 4: Registration page should be accessible
            register_response = client.get('/register')
            assert register_response.status_code == 200, "Registration page should be accessible to unauthenticated users"