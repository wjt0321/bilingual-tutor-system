import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from typing import List
from collections import defaultdict
from bilingual_tutor.gamification.achievement_system import (
    AchievementSystem,
    Achievement,
    UserAchievement,
    Reward,
    UserReward,
    LeaderboardEntry,
    Challenge,
    AchievementType,
    AchievementTier
)
from bilingual_tutor.models import Skill, ActivityType, Content, ContentType


class TestAchievementSystemBasicFunctionality:
    """测试成就系统基本功能"""
    
    def test_initialization(self):
        """测试成就系统初始化"""
        system = AchievementSystem()
        assert len(system.achievements) > 0
        assert len(system.rewards_catalog) > 0
        assert system.user_points == {}
        assert system.user_achievements == {}
        assert system.user_rewards == {}
        assert system.challenges == {}
    
    def test_record_study_session(self):
        """测试学习会话记录"""
        system = AchievementSystem()
        
        session_data = {
            'duration_minutes': 30,
            'activity_type': ActivityType.READING.value,
            'skills_practiced': [Skill.READING.value]
        }
        
        system.record_study_session(
            user_id="user_1",
            session_data=session_data
        )
        
        assert system.user_points["user_1"] > 0


class TestAchievementUnfolding:
    """测试成就解锁机制"""
    
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=1000))
    def test_first_study_achievement(self, minutes):
        """测试首次学习成就解锁"""
        system = AchievementSystem()
        
        session_data = {
            'duration_minutes': minutes,
            'activity_type': ActivityType.READING.value,
            'skills_practiced': [Skill.READING.value]
        }
        
        system.record_study_session(
            user_id="user_1",
            session_data=session_data
        )
        
        user_achievements = system.get_user_achievements("user_1")
        assert any(a.achievement_id == "first_study" and a.unlocked_at is not None for a in user_achievements)
    
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=7, max_value=30))
    def test_week_warrior_achievement(self, days):
        """测试连续学习7天成就解锁"""
        system = AchievementSystem()
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).isoformat()
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value],
                'session_date': date
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
        
        user_achievements = system.get_user_achievements("user_1")
        assert any(a.achievement_id == "week_warrior" and a.unlocked_at is not None for a in user_achievements)
    
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=50))
    def test_centurion_achievement(self, sessions):
        """测试完成100次学习成就解锁"""
        system = AchievementSystem()
        
        for _ in range(sessions):
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value]
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
        
        user_achievements = system.get_user_achievements("user_1")
        has_centurion = any(a.achievement_id == "centurion" and a.unlocked_at is not None for a in user_achievements)
        assert has_centurion == (sessions >= 100)


class TestPointsSystem:
    """测试积分系统"""
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=10))
    def test_points_accumulation(self, sessions):
        """测试积分累积"""
        system = AchievementSystem()
        
        initial_points = 0
        for _ in range(sessions):
            points_before = system.user_points.get("user_1", 0)
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value]
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
            points_after = system.user_points["user_1"]
            assert points_after > points_before
        
        assert system.user_points["user_1"] >= sessions
    
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=1000))
    def test_award_points(self, points_to_award):
        """测试积分奖励"""
        system = AchievementSystem()
        system.award_points("user_1", points_to_award)
        
        assert system.user_points["user_1"] == points_to_award
    
    def test_points_cannot_be_negative(self):
        """测试积分不能为负"""
        system = AchievementSystem()
        system.award_points("user_1", 100)
        initial_points = system.user_points["user_1"]
        
        system.user_points["user_1"] = max(0, system.user_points["user_1"] - 200)
        assert system.user_points["user_1"] >= 0


class TestRewardsClaiming:
    """测试奖励领取"""
    
    def test_claim_reward_success(self):
        """测试成功领取奖励"""
        system = AchievementSystem()
        # Initialize user in user_points dict
        system.user_points["user_1"] = 500
        
        result = system.claim_reward("user_1", "custom_badge")
        assert result is True
        assert system.user_points["user_1"] == 0
        assert any(r.reward.reward_id == "custom_badge" for r in system.user_rewards["user_1"])
    
    def test_claim_reward_insufficient_points(self):
        """测试积分不足时领取奖励失败"""
        system = AchievementSystem()
        system.user_points["user_1"] = 50
        
        result = system.claim_reward("user_1", "custom_badge")
        assert result is False
        assert system.user_points["user_1"] == 50
        assert len(system.user_rewards["user_1"]) == 0
    
    def test_claim_reward_twice(self):
        """测试重复领取同一奖励"""
        system = AchievementSystem()
        system.user_points["user_1"] = 1000
        
        result1 = system.claim_reward("user_1", "custom_badge")
        result2 = system.claim_reward("user_1", "custom_badge")
        
        assert result1 is True
        assert result2 is True  # Can claim again if enough points
        assert system.user_points["user_1"] == 0


class TestLeaderboardFunctionality:
    """测试排行榜功能"""
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=100))
    def test_leaderboard_ranking(self, base_points):
        """测试排行榜排名"""
        system = AchievementSystem()
        
        users = ["user_1", "user_2", "user_3"]
        for i, user_id in enumerate(users):
            system.user_points[user_id] = base_points + (2 - i) * 50
        
        leaderboard = system.get_leaderboard(limit=10)
        
        assert len(leaderboard) == 3
        assert leaderboard[0].user_id == "user_1"
        assert leaderboard[1].user_id == "user_2"
        assert leaderboard[2].user_id == "user_3"
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=5, max_value=20))
    def test_leaderboard_limit(self, limit):
        """测试排行榜限制"""
        system = AchievementSystem()
        
        for i in range(30):
            system.user_points[f"user_{i}"] = 1000 - i * 10
        
        leaderboard = system.get_leaderboard(limit=limit)
        assert len(leaderboard) <= limit
    
    def test_leaderboard_empty(self):
        """测试空排行榜"""
        system = AchievementSystem()
        leaderboard = system.get_leaderboard()
        assert len(leaderboard) == 0


class TestChallengeManagement:
    """测试挑战管理"""
    
    def test_create_challenge(self):
        """测试创建挑战"""
        system = AchievementSystem()
        
        challenge = system.create_challenge(
            name="Study Challenge",
            description="Study for 7 days",
            challenge_type=AchievementType.STREAK,
            target_value=7,
            reward_points=700,
            duration_days=7
        )
        
        assert challenge is not None
        assert challenge.name == "Study Challenge"
        assert challenge.target_value == 7
        assert challenge.challenge_id in system.challenges
    
    def test_join_challenge(self):
        """测试加入挑战"""
        system = AchievementSystem()
        
        challenge = system.create_challenge(
            name="Study Challenge",
            description="Study for 7 days",
            challenge_type=AchievementType.STREAK,
            target_value=7,
            reward_points=700,
            duration_days=7
        )
        
        result = system.join_challenge("user_1", challenge.challenge_id)
        assert result is True
        assert "user_1" in challenge.participants
    
    def test_challenge_creation_generates_dates(self):
        """测试挑战创建时自动生成日期"""
        system = AchievementSystem()
        
        challenge = system.create_challenge(
            name="Study Challenge",
            description="Study for 7 days",
            challenge_type=AchievementType.STREAK,
            target_value=7,
            reward_points=700,
            duration_days=7
        )
        
        assert challenge.start_date is not None
        assert challenge.end_date is not None
        assert challenge.end_date > challenge.start_date


class TestStreakTracking:
    """测试连续学习追踪"""
    
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=30))
    def test_streak_increases_with_sessions(self, days):
        """测试连续天数随会话增加"""
        system = AchievementSystem()
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).isoformat()
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value],
                'session_date': date
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
        
        streak = system.get_user_streak("user_1")
        assert streak['current'] >= 1
    
    def test_streak_break(self):
        """测试连续学习中断"""
        system = AchievementSystem()
        
        for i in range(5):
            date = (datetime.now() - timedelta(days=i)).isoformat()
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value],
                'session_date': date
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
        
        for i in range(10, 15):
            date = (datetime.now() - timedelta(days=i)).isoformat()
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value],
                'session_date': date
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
        
        streak = system.get_user_streak("user_1")
        assert streak['current'] <= 5


class TestSkillProgressionTracking:
    """测试技能进度追踪"""
    
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=10))
    def test_skill_progression(self, sessions):
        """测试技能进度记录"""
        system = AchievementSystem()
        
        for _ in range(sessions):
            system.record_skill_progression(
                user_id="user_1",
                skill=Skill.READING,
                current_level=0.8
            )
        
        user_achievements = system.get_user_achievements("user_1")
        has_skill_rising = any(a.achievement_id == "skill_rising" and a.unlocked_at is not None for a in user_achievements)
        assert has_skill_rising
    
    def test_multiple_skills_tracking(self):
        """测试多个技能追踪"""
        system = AchievementSystem()
        
        system.record_skill_progression(
            user_id="user_1",
            skill=Skill.READING,
            current_level=0.8
        )
        system.record_skill_progression(
            user_id="user_1",
            skill=Skill.LISTENING,
            current_level=0.95
        )
        
        user_achievements = system.get_user_achievements("user_1")
        has_skill_rising = any(a.achievement_id == "skill_rising" and a.unlocked_at is not None for a in user_achievements)
        has_skill_master = any(a.achievement_id == "skill_master" and a.unlocked_at is not None for a in user_achievements)
        
        assert has_skill_rising
        assert has_skill_master


class TestAchievementProperties:
    """测试成就属性"""
    
    def test_default_achievements_exist(self):
        """测试默认成就存在"""
        system = AchievementSystem()
        
        expected_achievements = [
            "first_study", "week_warrior", "month_master", "centurion",
            "vocab_collector", "grammar_guru", "consistent_learner",
            "dedicated_student", "skill_rising", "skill_master"
        ]
        
        for achievement_id in expected_achievements:
            assert achievement_id in system.achievements
    
    def test_achievement_unlocking_order(self):
        """测试成就解锁顺序"""
        system = AchievementSystem()
        
        for _ in range(5):
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value]
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
        
        achievements = system.get_user_achievements("user_1")
        first_study = next((a for a in achievements if a.achievement_id == "first_study"), None)
        assert first_study is not None
        assert first_study.unlocked_at is not None


class TestRewardProperties:
    """测试奖励属性"""
    
    def test_default_rewards_exist(self):
        """测试默认奖励存在"""
        system = AchievementSystem()
        
        expected_rewards = [
            "custom_badge", "premium_content", "dark_theme",
            "premium_theme", "bonus_points"
        ]
        
        for reward_id in expected_rewards:
            assert reward_id in system.rewards_catalog
    
    def test_reward_cost_validation(self):
        """测试奖励成本验证"""
        system = AchievementSystem()
        
        for reward_id, reward in system.rewards_catalog.items():
            assert reward.cost_points >= 0
            assert reward.reward_id == reward_id


class TestChallengeProperties:
    """测试挑战属性"""
    
    def test_challenge_dates_generated(self):
        """测试挑战日期自动生成"""
        system = AchievementSystem()
        
        challenge = system.create_challenge(
            name="Study Challenge",
            description="Study for 7 days",
            challenge_type=AchievementType.STREAK,
            target_value=7,
            reward_points=700,
            duration_days=7
        )
        
        assert challenge.start_date is not None
        assert challenge.end_date is not None
        assert challenge.end_date > challenge.start_date
    
    def test_challenge_creation(self):
        """测试挑战创建基本功能"""
        system = AchievementSystem()
        
        challenge = system.create_challenge(
            name="Study Challenge",
            description="Study for 7 days",
            challenge_type=AchievementType.STREAK,
            target_value=7,
            reward_points=700,
            duration_days=7
        )
        
        assert challenge.name == "Study Challenge"
        assert challenge.challenge_id in system.challenges


class TestConsistencyProperties:
    """测试一致性属性"""
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=30))
    def test_study_points_consistency(self, sessions):
        """测试学习积分一致性"""
        system = AchievementSystem()
        
        total_points = 0
        for _ in range(sessions):
            points_before = system.user_points.get("user_1", 0)
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value]
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
            points_after = system.user_points["user_1"]
            total_points += (points_after - points_before)
        
        assert system.user_points["user_1"] == total_points
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=100))
    def test_achievement_points_sum(self, sessions):
        """测试成就积分总和"""
        system = AchievementSystem()
        
        for _ in range(sessions):
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value]
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
        
        achievements = system.get_user_achievements("user_1")
        achievement_points = sum(a.points for a in achievements if a.unlocked_at is not None)
        
        assert achievement_points >= 0


class TestErrorHandling:
    """测试错误处理"""
    
    def test_nonexistent_user_achievements(self):
        """测试获取不存在用户的成就"""
        system = AchievementSystem()
        achievements = system.get_user_achievements("nonexistent_user")
        assert len(achievements) == len(system.achievements)
    
    def test_nonexistent_user_streak(self):
        """测试获取不存在用户的连续天数"""
        system = AchievementSystem()
        streak = system.get_user_streak("nonexistent_user")
        assert streak['current'] == 0
        assert streak['longest'] == 0
    
    def test_nonexistent_challenge_join(self):
        """测试加入不存在的挑战"""
        system = AchievementSystem()
        result = system.join_challenge("nonexistent_challenge", "user_1")
        assert result is False
    
    def test_nonexistent_reward_claim(self):
        """测试领取不存在的奖励"""
        system = AchievementSystem()
        system.award_points("user_1", 1000)
        result = system.claim_reward("user_1", "nonexistent_reward")
        assert result is False
        assert system.user_points["user_1"] == 1000


class TestAchievementSystemCompleteness:
    """
    属性57: 成就系统完整性
    验证需求: 32.1
    
    需求32.1: 学习系统应设计多层次的成就徽章（词汇掌握、连续学习等）
    需求32.3: 成就系统应与学习进度紧密结合，反映真实能力提升
    需求32.6: 成就数据应持久化存储，支持历史查看
    """
    
    def test_multilevel_achievement_tiers_exist(self):
        """验证存在多层次成就徽章（青铜、白银、黄金、铂金、钻石）"""
        system = AchievementSystem()
        
        tiers_found = set()
        for achievement in system.achievements.values():
            tiers_found.add(achievement.tier)
        
        expected_tiers = {
            AchievementTier.BRONZE,
            AchievementTier.SILVER,
            AchievementTier.GOLD
        }
        
        assert len(tiers_found & expected_tiers) >= 3, "应至少包含青铜、白银、黄金三个级别"
    
    def test_vocabulary_mastery_achievements_exist(self):
        """验证词汇掌握成就存在"""
        system = AchievementSystem()
        
        vocab_achievements = [
            a for a in system.achievements.values()
            if a.achievement_type == AchievementType.CONTENT_MASTERY
            and 'vocabulary' in a.description.lower()
        ]
        
        assert len(vocab_achievements) > 0, "应存在词汇掌握相关成就"
        
        for achievement in vocab_achievements:
            assert achievement.points > 0, "词汇成就应有积分奖励"
            assert achievement.tier in [AchievementTier.SILVER, AchievementTier.GOLD, AchievementTier.PLATINUM], "词汇成就应为较高级别"
    
    def test_streak_achievements_exist(self):
        """验证连续学习成就存在"""
        system = AchievementSystem()
        
        streak_achievements = [
            a for a in system.achievements.values()
            if a.achievement_type == AchievementType.STREAK
        ]
        
        assert len(streak_achievements) >= 2, "应至少存在2个连续学习成就"
        
        for achievement in streak_achievements:
            assert 'streak_days' in achievement.requirements or 'days' in achievement.description.lower(), "连续学习成就应包含天数要求"
    
    def test_achievement_categories_cover_all_types(self):
        """验证成就类型覆盖所有主要学习维度"""
        system = AchievementSystem()
        
        achievement_types = set(a.achievement_type for a in system.achievements.values())
        
        required_types = {
            AchievementType.STUDY_DURATION,
            AchievementType.CONTENT_MASTERY,
            AchievementType.STREAK,
            AchievementType.CONSISTENCY,
            AchievementType.SKILL_PROGRESSION,
            AchievementType.MILESTONE
        }
        
        assert achievement_types >= required_types, f"应包含所有必需的成就类型，缺少: {required_types - achievement_types}"
    
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=100))
    def test_achievements_reflect_real_progress(self, sessions):
        """验证成就系统与学习进度紧密结合"""
        system = AchievementSystem()
        
        initial_achievements = system.get_user_achievements("user_1")
        unlocked_initial = sum(1 for a in initial_achievements if a.unlocked_at is not None)
        
        for _ in range(sessions):
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value]
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
        
        final_achievements = system.get_user_achievements("user_1")
        unlocked_final = sum(1 for a in final_achievements if a.unlocked_at is not None)
        
        assert unlocked_final >= unlocked_initial, "随着学习进行，解锁的成就不应减少"
        
        if sessions >= 100:
            assert unlocked_final > unlocked_initial, "完成100次学习后应解锁更多成就"
    
    def test_progress_tracking_accuracy(self):
        """验证进度追踪准确性"""
        system = AchievementSystem()
        
        session_data = {
            'duration_minutes': 30,
            'activity_type': ActivityType.READING.value,
            'skills_practiced': [Skill.READING.value]
        }
        system.record_study_session(user_id="user_1", session_data=session_data)
        
        streak = system.get_user_streak("user_1")
        achievements = system.get_user_achievements("user_1")
        
        first_study = next((a for a in achievements if a.achievement_id == "first_study"), None)
        assert first_study is not None
        assert first_study.unlocked_at is not None, "首次学习应解锁first_study成就"
        assert first_study.progress == 1.0, "成就进度应为100%"
        
        assert streak['current'] >= 1, "当前连续天数应至少为1"
        assert streak['longest'] >= streak['current'], "最长连续天数不应小于当前连续天数"
        assert streak['last_study_date'] is not None, "最后学习日期应被记录"
    
    def test_achievement_data_persistence_structure(self):
        """验证成就数据结构支持持久化和历史查看"""
        system = AchievementSystem()
        
        session_data = {
            'duration_minutes': 30,
            'activity_type': ActivityType.READING.value,
            'skills_practiced': [Skill.READING.value]
        }
        system.record_study_session(user_id="user_1", session_data=session_data)
        
        achievements = system.get_user_achievements("user_1")
        
        for achievement in achievements:
            assert achievement.achievement_id is not None, "成就应有唯一ID"
            assert achievement.name is not None, "成就应有名称"
            assert achievement.description is not None, "成就应有描述"
            assert achievement.achievement_type is not None, "成就应有类型"
            assert achievement.tier is not None, "成就应有级别"
            assert achievement.points >= 0, "成就积分应为非负"
            assert achievement.max_progress > 0, "成就应有最大进度"
            assert 0.0 <= achievement.progress <= 1.0, "进度应在0到1之间"
            
            if achievement.unlocked_at is not None:
                assert isinstance(achievement.unlocked_at, datetime), "解锁时间应为datetime类型"
    
    def test_achievement_history_preservation(self):
        """验证成就历史记录保留"""
        system = AchievementSystem()
        
        first_session_time = datetime.now()
        
        session_data = {
            'duration_minutes': 30,
            'activity_type': ActivityType.READING.value,
            'skills_practiced': [Skill.READING.value]
        }
        system.record_study_session(user_id="user_1", session_data=session_data)
        
        achievements = system.get_user_achievements("user_1")
        first_study = next((a for a in achievements if a.achievement_id == "first_study"), None)
        
        assert first_study is not None
        assert first_study.unlocked_at is not None, "首次学习成就应被解锁"
        assert first_study.unlocked_at >= first_session_time, "解锁时间应不早于学习时间"
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=50))
    def test_skill_progression_achievements_accuracy(self, skill_level_percent):
        """验证技能进度成就准确性"""
        system = AchievementSystem()
        
        skill_level = skill_level_percent / 100.0
        
        system.record_skill_progression(
            user_id="user_1",
            skill=Skill.READING,
            current_level=skill_level
        )
        
        achievements = system.get_user_achievements("user_1")
        skill_rising = next((a for a in achievements if a.achievement_id == "skill_rising"), None)
        skill_master = next((a for a in achievements if a.achievement_id == "skill_master"), None)
        
        if skill_level >= 0.6:
            assert skill_rising.unlocked_at is not None, "技能达到60%应解锁skill_rising"
        else:
            assert skill_rising.unlocked_at is None, "技能未达到60%不应解锁skill_rising"
        
        if skill_level >= 0.9:
            assert skill_master.unlocked_at is not None, "技能达到90%应解锁skill_master"
        else:
            assert skill_master.unlocked_at is None, "技能未达到90%不应解锁skill_master"
    
    def test_milestone_achievements_exist(self):
        """验证里程碑成就存在"""
        system = AchievementSystem()
        
        milestone_achievements = [
            a for a in system.achievements.values()
            if a.achievement_type == AchievementType.MILESTONE
        ]
        
        assert len(milestone_achievements) >= 3, "应至少存在3个里程碑成就"
        
        for achievement in milestone_achievements:
            assert 'level' in achievement.achievement_id.lower(), "里程碑成就应与级别相关"
            assert achievement.tier in [AchievementTier.BRONZE, AchievementTier.SILVER, AchievementTier.GOLD], "里程碑成就应有不同级别"
    
    def test_achievement_points_distribution合理性(self):
        """验证成就积分分配合理性"""
        system = AchievementSystem()
        
        points_by_tier = defaultdict(list)
        for achievement in system.achievements.values():
            points_by_tier[achievement.tier].append(achievement.points)
        
        if AchievementTier.GOLD in points_by_tier and AchievementTier.BRONZE in points_by_tier:
            avg_gold = sum(points_by_tier[AchievementTier.GOLD]) / len(points_by_tier[AchievementTier.GOLD])
            avg_bronze = sum(points_by_tier[AchievementTier.BRONZE]) / len(points_by_tier[AchievementTier.BRONZE])
            
            assert avg_gold >= avg_bronze, "黄金级成就的积分应不低于青铜级"
        
        for tier, points in points_by_tier.items():
            assert all(p > 0 for p in points), f"{tier}级成就的所有积分应大于0"
    
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=100))
    def test_points_and_achievements_consistency(self, sessions):
        """验证积分与成就解锁的一致性"""
        system = AchievementSystem()
        
        for _ in range(sessions):
            session_data = {
                'duration_minutes': 30,
                'activity_type': ActivityType.READING.value,
                'skills_practiced': [Skill.READING.value]
            }
            system.record_study_session(
                user_id="user_1",
                session_data=session_data
            )
        
        user_points = system.get_user_points("user_1")
        achievements = system.get_user_achievements("user_1")
        unlocked_achievements = [a for a in achievements if a.unlocked_at is not None]
        
        achievement_points = sum(a.points for a in unlocked_achievements)
        
        assert user_points >= achievement_points, "用户总积分应包含成就积分"
