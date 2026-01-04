"""
智能内容生成器
Intelligent Content Generator

实现基于用户薄弱环节的练习生成、多种练习形式和内容质量评估机制。
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import random

from bilingual_tutor.services.ai_service import (
    AIService,
    AIRequest,
    LanguageLevel,
    ExerciseType,
    get_ai_service
)
from bilingual_tutor.infrastructure.logging_system import get_logger


logger = get_logger(__name__)


class ContentQuality(Enum):
    """内容质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


@dataclass
class Exercise:
    """练习题目"""
    id: str
    type: ExerciseType
    question: str
    correct_answer: str
    explanation: str
    options: Optional[List[str]] = None
    difficulty: float = 0.5  # 0-1之间，0.5为中等难度
    weakness_areas: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'type': self.type.value,
            'question': self.question,
            'options': self.options,
            'correct_answer': self.correct_answer,
            'explanation': self.explanation,
            'difficulty': self.difficulty,
            'weakness_areas': self.weakness_areas,
            'metadata': self.metadata
        }


@dataclass
class ExerciseBatch:
    """练习批次"""
    exercises: List[Exercise]
    target_level: LanguageLevel
    target_areas: List[str]
    quality_score: float
    generation_duration_ms: float
    exercise_count: int = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.exercise_count is None:
            self.exercise_count = len(self.exercises)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'exercises': [ex.to_dict() for ex in self.exercises],
            'target_level': self.target_level.value,
            'target_areas': self.target_areas,
            'quality_score': self.quality_score,
            'generation_duration_ms': self.generation_duration_ms,
            'exercise_count': self.exercise_count
        }


@dataclass
class QualityMetrics:
    """质量指标"""
    clarity_score: float = 0.0  # 清晰度
    relevance_score: float = 0.0  # 相关性
    difficulty_match_score: float = 0.0  # 难度匹配度
    variety_score: float = 0.0  # 多样性
    completeness_score: float = 0.0  # 完整性
    overall_score: float = 0.0  # 总体得分
    
    def calculate_overall(self) -> float:
        """计算总体得分"""
        self.overall_score = (
            self.clarity_score * 0.25 +
            self.relevance_score * 0.20 +
            self.difficulty_match_score * 0.20 +
            self.variety_score * 0.15 +
            self.completeness_score * 0.20
        )
        return self.overall_score
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'clarity_score': self.clarity_score,
            'relevance_score': self.relevance_score,
            'difficulty_match_score': self.difficulty_match_score,
            'variety_score': self.variety_score,
            'completeness_score': self.completeness_score,
            'overall_score': self.overall_score
        }


class IntelligentContentGenerator:
    """智能内容生成器"""
    
    def __init__(self, ai_service: Optional[AIService] = None):
        self.ai_service = ai_service or get_ai_service()
        self.logger = get_logger(f"{__name__}.IntelligentContentGenerator")
        self._generation_history: List[Dict[str, Any]] = []
    
    async def generate_targeted_exercises(self,
                                       weakness_areas: List[str],
                                       language_level: LanguageLevel,
                                       exercise_types: Optional[List[ExerciseType]] = None,
                                       count: int = 5) -> ExerciseBatch:
        """生成针对性练习题"""
        start_time = time.perf_counter()
        
        if exercise_types is None:
            exercise_types = list(ExerciseType)
        
        exercises = []
        
        # 为每种类型生成练习
        exercises_per_type = max(1, count // len(exercise_types))
        remaining = count % len(exercise_types)
        
        for i, exercise_type in enumerate(exercise_types):
            current_count = exercises_per_type + (1 if i < remaining else 0)
            
            type_exercises = await self._generate_exercises_by_type(
                weakness_areas=weakness_areas,
                language_level=language_level,
                exercise_type=exercise_type,
                count=current_count
            )
            
            exercises.extend(type_exercises)
        
        # 评估内容质量
        quality_metrics = await self._evaluate_content_quality(
            exercises=exercises,
            target_level=language_level,
            target_areas=weakness_areas
        )
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # 记录生成历史
        self._record_generation(
            weakness_areas=weakness_areas,
            language_level=language_level,
            exercise_count=len(exercises),
            quality_score=quality_metrics.overall_score,
            duration_ms=duration_ms
        )
        
        return ExerciseBatch(
            exercises=exercises,
            target_level=language_level,
            target_areas=weakness_areas,
            quality_score=quality_metrics.overall_score,
            generation_duration_ms=duration_ms
        )
    
    async def _generate_exercises_by_type(self,
                                        weakness_areas: List[str],
                                        language_level: LanguageLevel,
                                        exercise_type: ExerciseType,
                                        count: int) -> List[Exercise]:
        """按类型生成练习题"""
        level_description = self._get_level_description(language_level)
        type_description = self._get_type_description(exercise_type)
        weakness_text = "、".join(weakness_areas) if weakness_areas else "综合练习"
        
        system_prompt = f"""你是一个专业的语言学习练习题生成器。你的任务是根据用户的薄弱环节生成针对性的练习题。

要求：
1. 练习难度应匹配{level_description}水平
2. 生成{count}道{type_description}
3. 重点关注以下薄弱领域：{weakness_text}
4. 每道题都要提供详细的答案解析（中文）
5. 题目内容要有意义，避免无意义重复
6. 确保题目难度适中，既不太简单也不太难
7. 提供准确的标准答案

输出格式（JSON）：
{{
    "exercises": [
        {{
            "id": "Q1",
            "question": "题目内容",
            "options": ["选项A", "选项B", "选项C", "选项D"],
            "correct_answer": "正确答案",
            "explanation": "详细解析（中文）",
            "difficulty": 0.5
        }}
    ]
}}"""

        prompt = f"请生成{count}道针对{weakness_text}的{level_description}水平{type_description}"
        
        request = AIRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            language_level=language_level,
            max_tokens=2000
        )
        
        try:
            response = await self.ai_service.generate(request)
            result = json.loads(response.content)
            
            exercises = []
            for ex_data in result.get('exercises', []):
                exercise = Exercise(
                    id=ex_data.get('id', f"{exercise_type.value}_{random.randint(1000, 9999)}"),
                    type=exercise_type,
                    question=ex_data.get('question', ''),
                    options=ex_data.get('options'),
                    correct_answer=ex_data.get('correct_answer', ''),
                    explanation=ex_data.get('explanation', ''),
                    difficulty=ex_data.get('difficulty', 0.5),
                    weakness_areas=weakness_areas.copy(),
                    metadata={'duration_ms': response.duration_ms}
                )
                exercises.append(exercise)
            
            return exercises
        
        except json.JSONDecodeError as e:
            self.logger.error(f"解析练习题失败: {str(e)}")
            return []
    
    async def _evaluate_content_quality(self,
                                     exercises: List[Exercise],
                                     target_level: LanguageLevel,
                                     target_areas: List[str]) -> QualityMetrics:
        """评估内容质量"""
        metrics = QualityMetrics()
        
        if not exercises:
            return metrics
        
        # 评估清晰度（基于问题长度、解释长度）
        metrics.clarity_score = self._evaluate_clarity(exercises)
        
        # 评估相关性（基于目标领域匹配）
        metrics.relevance_score = self._evaluate_relevance(exercises, target_areas)
        
        # 评估难度匹配度
        metrics.difficulty_match_score = self._evaluate_difficulty_match(exercises, target_level)
        
        # 评估多样性
        metrics.variety_score = self._evaluate_variety(exercises)
        
        # 评估完整性
        metrics.completeness_score = self._evaluate_completeness(exercises)
        
        # 计算总体得分
        metrics.calculate_overall()
        
        return metrics
    
    def _evaluate_clarity(self, exercises: List[Exercise]) -> float:
        """评估清晰度"""
        if not exercises:
            return 0.0
        
        clarity_scores = []
        
        for exercise in exercises:
            # 问题长度适中
            question_len = len(exercise.question)
            question_score = 1.0 if 20 <= question_len <= 200 else 0.5
            
            # 解释长度适中
            explanation_len = len(exercise.explanation)
            explanation_score = 1.0 if 50 <= explanation_len <= 500 else 0.5
            
            clarity_scores.append((question_score + explanation_score) / 2)
        
        return sum(clarity_scores) / len(clarity_scores)
    
    def _evaluate_relevance(self, exercises: List[Exercise], target_areas: List[str]) -> float:
        """评估相关性"""
        if not exercises or not target_areas:
            return 1.0
        
        relevant_count = 0
        
        for exercise in exercises:
            # 检查练习是否关联到目标领域
            if exercise.weakness_areas and any(area in exercise.weakness_areas for area in target_areas):
                relevant_count += 1
        
        return relevant_count / len(exercises)
    
    def _evaluate_difficulty_match(self, exercises: List[Exercise], target_level: LanguageLevel) -> float:
        """评估难度匹配度"""
        if not exercises:
            return 0.0
        
        # 根据语言级别设定目标难度范围
        difficulty_ranges = {
            LanguageLevel.CET4: (0.2, 0.5),
            LanguageLevel.CET5: (0.3, 0.6),
            LanguageLevel.CET6: (0.4, 0.7),
            LanguageLevel.CET6_PLUS: (0.5, 0.8),
            LanguageLevel.N5: (0.2, 0.5),
            LanguageLevel.N4: (0.3, 0.6),
            LanguageLevel.N3: (0.4, 0.7),
            LanguageLevel.N2: (0.5, 0.8),
            LanguageLevel.N1: (0.6, 0.9),
            LanguageLevel.N1_PLUS: (0.7, 1.0)
        }
        
        target_min, target_max = difficulty_ranges.get(target_level, (0.4, 0.7))
        
        match_count = 0
        for exercise in exercises:
            if target_min <= exercise.difficulty <= target_max:
                match_count += 1
        
        return match_count / len(exercises)
    
    def _evaluate_variety(self, exercises: List[Exercise]) -> float:
        """评估多样性"""
        if not exercises:
            return 0.0
        
        # 检查练习类型的多样性
        type_variety = len(set(ex.type for ex in exercises)) / len(ExerciseType)
        
        # 检查难度分布的多样性
        difficulties = [ex.difficulty for ex in exercises]
        difficulty_variance = max(difficulties) - min(difficulties) if len(difficulties) > 1 else 0
        difficulty_variety = min(difficulty_variance / 0.5, 1.0)  # 归一化
        
        return (type_variety + difficulty_variety) / 2
    
    def _evaluate_completeness(self, exercises: List[Exercise]) -> float:
        """评估完整性"""
        if not exercises:
            return 0.0
        
        completeness_scores = []
        
        for exercise in exercises:
            # 检查必需字段
            has_question = bool(exercise.question)
            has_answer = bool(exercise.correct_answer)
            has_explanation = bool(exercise.explanation)
            
            # 对于选择题，需要选项
            has_options = True
            if exercise.type == ExerciseType.MULTIPLE_CHOICE:
                has_options = bool(exercise.options and len(exercise.options) >= 4)
            
            completeness = (has_question + has_answer + has_explanation + has_options) / 4
            completeness_scores.append(completeness)
        
        return sum(completeness_scores) / len(completeness_scores)
    
    def optimize_exercises(self, exercises: List[Exercise],
                         user_feedback: Optional[Dict[str, Any]] = None) -> List[Exercise]:
        """优化练习题"""
        if not exercises:
            return exercises
        
        # 根据用户反馈调整难度
        if user_feedback:
            exercises = self._adjust_difficulty_based_on_feedback(exercises, user_feedback)
        
        # 确保质量达标
        optimized_exercises = []
        for exercise in exercises:
            if self._is_exercise_quality_acceptable(exercise):
                optimized_exercises.append(exercise)
            else:
                # 可以选择重新生成或标记为低质量
                exercise.metadata['quality'] = 'low'
                optimized_exercises.append(exercise)
        
        return optimized_exercises
    
    def _adjust_difficulty_based_on_feedback(self,
                                          exercises: List[Exercise],
                                          feedback: Dict[str, Any]) -> List[Exercise]:
        """根据用户反馈调整难度"""
        accuracy = feedback.get('accuracy', 0.5)
        
        # 如果准确率很高，提高难度
        if accuracy > 0.8:
            adjustment_factor = 1.1
        # 如果准确率很低，降低难度
        elif accuracy < 0.5:
            adjustment_factor = 0.9
        else:
            adjustment_factor = 1.0
        
        for exercise in exercises:
            exercise.difficulty = min(1.0, max(0.1, exercise.difficulty * adjustment_factor))
        
        return exercises
    
    def _is_exercise_quality_acceptable(self, exercise: Exercise) -> bool:
        """检查练习质量是否可接受"""
        # 问题不能太短或太长
        if len(exercise.question) < 10 or len(exercise.question) > 300:
            return False
        
        # 必须有答案
        if not exercise.correct_answer:
            return False
        
        # 解释不能太短
        if len(exercise.explanation) < 20:
            return False
        
        # 选择题必须有选项
        if exercise.type == ExerciseType.MULTIPLE_CHOICE:
            if not exercise.options or len(exercise.options) < 4:
                return False
        
        return True
    
    def _record_generation(self,
                        weakness_areas: List[str],
                        language_level: LanguageLevel,
                        exercise_count: int,
                        quality_score: float,
                        duration_ms: float) -> None:
        """记录生成历史"""
        record = {
            'timestamp': time.time(),
            'weakness_areas': weakness_areas,
            'language_level': language_level.value,
            'exercise_count': exercise_count,
            'quality_score': quality_score,
            'duration_ms': duration_ms
        }
        
        self._generation_history.append(record)
        
        # 只保留最近100条记录
        if len(self._generation_history) > 100:
            self._generation_history = self._generation_history[-100:]
    
    def get_generation_statistics(self) -> Dict[str, Any]:
        """获取生成统计信息"""
        if not self._generation_history:
            return {
                'total_generations': 0,
                'average_quality_score': 0.0,
                'average_duration_ms': 0.0
            }
        
        total_generations = len(self._generation_history)
        total_quality = sum(r['quality_score'] for r in self._generation_history)
        total_duration = sum(r['duration_ms'] for r in self._generation_history)
        
        return {
            'total_generations': total_generations,
            'average_quality_score': total_quality / total_generations,
            'average_duration_ms': total_duration / total_generations,
            'recent_history': self._generation_history[-10:]
        }
    
    def _get_level_description(self, level: LanguageLevel) -> str:
        """获取级别描述"""
        descriptions = {
            LanguageLevel.CET4: "大学英语四级",
            LanguageLevel.CET5: "大学英语五级",
            LanguageLevel.CET6: "大学英语六级",
            LanguageLevel.CET6_PLUS: "大学英语六级以上",
            LanguageLevel.N5: "日语N5",
            LanguageLevel.N4: "日语N4",
            LanguageLevel.N3: "日语N3",
            LanguageLevel.N2: "日语N2",
            LanguageLevel.N1: "日语N1",
            LanguageLevel.N1_PLUS: "日语N1以上"
        }
        return descriptions.get(level, "中级")
    
    def _get_type_description(self, exercise_type: ExerciseType) -> str:
        """获取练习类型描述"""
        descriptions = {
            ExerciseType.MULTIPLE_CHOICE: "选择题",
            ExerciseType.FILL_BLANK: "填空题",
            ExerciseType.TRANSLATION: "翻译题",
            ExerciseType.WRITING: "写作题"
        }
        return descriptions.get(exercise_type, "练习题")


# 全局智能内容生成器实例
_global_intelligent_generator: Optional[IntelligentContentGenerator] = None


def get_intelligent_content_generator() -> IntelligentContentGenerator:
    """获取智能内容生成器单例"""
    global _global_intelligent_generator
    if _global_intelligent_generator is None:
        _global_intelligent_generator = IntelligentContentGenerator()
    return _global_intelligent_generator
