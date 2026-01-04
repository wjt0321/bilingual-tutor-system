"""
Improvement Advisor - Provides targeted suggestions and examples for weak areas.
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from ..models import WeakArea, Skill, ActivityResult


class ImprovementAdvisor:
    """
    Provides targeted suggestions and examples for weak areas identified
    by the weakness analyzer.
    """
    
    def __init__(self):
        """Initialize the improvement advisor."""
        self.improvement_strategies: Dict[Skill, List[str]] = self._initialize_strategies()
        self.example_database: Dict[Skill, Dict[str, List[str]]] = self._initialize_examples()
        self.practice_recommendations: Dict[Skill, List[str]] = self._initialize_practice_recommendations()
        self.improvement_tracking: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def generate_improvement_plan(self, weakness: WeakArea) -> Dict[str, any]:
        """
        Generate a comprehensive improvement plan for a weakness.
        
        Args:
            weakness: Weakness to generate improvement plan for
            
        Returns:
            Dictionary containing improvement plan details
        """
        plan = {
            'weakness_id': weakness.area_id,
            'skill': weakness.skill.value,
            'language': weakness.language,
            'severity': weakness.severity,
            'strategies': self._get_strategies_for_skill(weakness.skill, weakness.language),
            'examples': self._get_examples_for_weakness(weakness),
            'practice_exercises': self._get_practice_exercises(weakness),
            'timeline': self._calculate_improvement_timeline(weakness.severity),
            'success_metrics': self._define_success_metrics(weakness),
            'chinese_explanation': self._generate_chinese_explanation(weakness)
        }
        
        return plan
    
    def provide_examples(self, concept: str, language: str) -> List[str]:
        """
        Provide specific examples for a concept in the given language.
        
        Args:
            concept: The concept to provide examples for
            language: Language context (english or japanese)
            
        Returns:
            List of examples with Chinese explanations
        """
        examples = []
        
        # Get examples based on concept type
        if 'vocabulary' in concept.lower():
            examples = self._get_vocabulary_examples(concept, language)
        elif 'grammar' in concept.lower():
            examples = self._get_grammar_examples(concept, language)
        elif 'pronunciation' in concept.lower():
            examples = self._get_pronunciation_examples(concept, language)
        else:
            # General examples
            examples = self._get_general_examples(concept, language)
        
        # Add Chinese explanations
        examples_with_explanations = []
        for example in examples:
            explanation = self._add_chinese_explanation(example, concept, language)
            examples_with_explanations.append(explanation)
        
        return examples_with_explanations
    
    def recommend_practice(self, skill: Skill, level: str) -> List[Dict[str, str]]:
        """
        Recommend specific practice exercises for a skill and level.
        
        Args:
            skill: Skill to practice
            level: Current proficiency level
            
        Returns:
            List of practice recommendations with details
        """
        recommendations = []
        
        base_practices = self.practice_recommendations.get(skill, [])
        
        for practice in base_practices:
            recommendation = {
                'exercise_type': practice,
                'difficulty': self._adjust_difficulty_for_level(practice, level),
                'duration': self._estimate_practice_duration(practice, skill),
                'frequency': self._recommend_frequency(skill, practice),
                'chinese_instructions': self._translate_instructions_to_chinese(practice, skill),
                'success_criteria': self._define_practice_success_criteria(practice, skill)
            }
            recommendations.append(recommendation)
        
        return recommendations
    
    def track_improvement(self, user_id: str, weakness: WeakArea, current_performance: float) -> Dict[str, any]:
        """
        Track improvement progress for a specific weakness.
        
        Args:
            user_id: User identifier
            weakness: Weakness being tracked
            current_performance: Current performance score
            
        Returns:
            Improvement tracking data
        """
        tracking_key = f"{user_id}_{weakness.area_id}"
        
        # Record current performance
        if tracking_key not in self.improvement_tracking:
            self.improvement_tracking[tracking_key] = []
        
        self.improvement_tracking[tracking_key].append((datetime.now(), current_performance))
        
        # Calculate improvement metrics
        performance_history = self.improvement_tracking[tracking_key]
        
        if len(performance_history) < 2:
            return {
                'improvement_rate': 0.0,
                'trend': 'insufficient_data',
                'recommendation': '继续练习以收集更多数据'
            }
        
        # Calculate improvement rate
        initial_performance = performance_history[0][1]
        latest_performance = performance_history[-1][1]
        improvement_rate = ((latest_performance - initial_performance) / initial_performance) * 100 if initial_performance > 0 else 0
        
        # Determine trend
        recent_scores = [score for _, score in performance_history[-5:]]  # Last 5 scores
        trend = self._analyze_trend(recent_scores)
        
        # Generate recommendation based on progress
        recommendation = self._generate_progress_recommendation(improvement_rate, trend, weakness)
        
        return {
            'improvement_rate': improvement_rate,
            'trend': trend,
            'recommendation': recommendation,
            'sessions_tracked': len(performance_history),
            'best_score': max(score for _, score in performance_history),
            'average_score': sum(score for _, score in performance_history) / len(performance_history)
        }
    
    def _initialize_strategies(self) -> Dict[Skill, List[str]]:
        """Initialize improvement strategies for each skill."""
        return {
            Skill.VOCABULARY: [
                "间隔重复记忆法",
                "词汇卡片练习",
                "语境学习法",
                "词根词缀分析",
                "同义词反义词对比"
            ],
            Skill.GRAMMAR: [
                "语法规则系统学习",
                "句型模仿练习",
                "错误分析纠正",
                "语法填空训练",
                "句子重组练习"
            ],
            Skill.READING: [
                "分级阅读训练",
                "快速阅读技巧",
                "精读理解练习",
                "阅读策略学习",
                "词汇推测训练"
            ],
            Skill.LISTENING: [
                "听力材料分级训练",
                "听写练习",
                "语音识别训练",
                "听力策略学习",
                "语调语音模仿"
            ],
            Skill.SPEAKING: [
                "发音纠正练习",
                "口语流利度训练",
                "对话模拟练习",
                "语音语调练习",
                "表达准确性训练"
            ],
            Skill.WRITING: [
                "写作结构训练",
                "句式多样化练习",
                "语法准确性训练",
                "词汇运用练习",
                "文体风格学习"
            ],
            Skill.PRONUNCIATION: [
                "音标学习练习",
                "发音对比训练",
                "语音模仿练习",
                "录音自我纠正",
                "语调节奏练习"
            ],
            Skill.COMPREHENSION: [
                "理解策略学习",
                "推理判断训练",
                "主旨大意把握",
                "细节信息提取",
                "逻辑关系分析"
            ]
        }
    
    def _initialize_examples(self) -> Dict[Skill, Dict[str, List[str]]]:
        """Initialize example database for each skill."""
        return {
            Skill.VOCABULARY: {
                'english': [
                    "abandon (放弃) - He decided to abandon his plan. 他决定放弃他的计划。",
                    "benefit (好处) - Exercise has many benefits. 运动有很多好处。",
                    "challenge (挑战) - Learning a new language is a challenge. 学习新语言是一个挑战。"
                ],
                'japanese': [
                    "あきらめる (放弃) - 彼は計画をあきらめた。他放弃了计划。",
                    "べんり (方便) - このアプリはとてもべんりです。这个应用很方便。",
                    "ちょうせん (挑战) - 新しいちょうせんを始める。开始新的挑战。"
                ]
            },
            Skill.GRAMMAR: {
                'english': [
                    "Present Perfect: I have studied English for 3 years. 我学英语已经3年了。",
                    "Passive Voice: The book was written by Shakespeare. 这本书是莎士比亚写的。",
                    "Conditional: If I had time, I would travel. 如果我有时间，我会去旅行。"
                ],
                'japanese': [
                    "て形: 本を読んでいます。正在读书。",
                    "敬语: いらっしゃいませ。欢迎光临（敬语）。",
                    "可能形: 日本語が話せます。会说日语。"
                ]
            }
        }
    
    def _initialize_practice_recommendations(self) -> Dict[Skill, List[str]]:
        """Initialize practice recommendations for each skill."""
        return {
            Skill.VOCABULARY: [
                "flashcard_review",
                "context_sentences",
                "word_association",
                "synonym_antonym_practice",
                "vocabulary_games"
            ],
            Skill.GRAMMAR: [
                "fill_in_blanks",
                "sentence_transformation",
                "error_correction",
                "pattern_practice",
                "grammar_drills"
            ],
            Skill.READING: [
                "graded_reading",
                "speed_reading",
                "comprehension_questions",
                "vocabulary_inference",
                "text_analysis"
            ],
            Skill.LISTENING: [
                "dictation_practice",
                "audio_comprehension",
                "pronunciation_mimicking",
                "listening_strategies",
                "sound_discrimination"
            ],
            Skill.SPEAKING: [
                "pronunciation_drills",
                "conversation_practice",
                "fluency_exercises",
                "intonation_practice",
                "recording_self_assessment"
            ],
            Skill.WRITING: [
                "structured_writing",
                "sentence_variety",
                "grammar_accuracy",
                "vocabulary_usage",
                "style_practice"
            ],
            Skill.PRONUNCIATION: [
                "phonetic_practice",
                "sound_repetition",
                "minimal_pairs",
                "intonation_drills",
                "recording_comparison"
            ],
            Skill.COMPREHENSION: [
                "reading_comprehension",
                "listening_comprehension",
                "inference_practice",
                "context_clues",
                "main_idea_identification"
            ]
        }
    
    def _get_strategies_for_skill(self, skill: Skill, language: str) -> List[str]:
        """Get improvement strategies for a specific skill."""
        base_strategies = self.improvement_strategies.get(skill, [])
        
        # Add language-specific strategies
        if language == 'japanese':
            if skill == Skill.VOCABULARY:
                base_strategies.extend(["汉字学习法", "假名练习"])
            elif skill == Skill.GRAMMAR:
                base_strategies.extend(["助词用法练习", "敬语系统学习"])
        
        return base_strategies
    
    def _get_examples_for_weakness(self, weakness: WeakArea) -> List[str]:
        """Get specific examples for a weakness."""
        skill_examples = self.example_database.get(weakness.skill, {})
        language_examples = skill_examples.get(weakness.language, [])
        
        # Filter examples based on error patterns
        relevant_examples = []
        for example in language_examples:
            # Check if example addresses the error patterns
            if any(pattern.lower() in example.lower() for pattern in weakness.error_patterns):
                relevant_examples.append(example)
        
        # If no specific examples found, return general examples
        if not relevant_examples:
            relevant_examples = language_examples[:3]  # Return first 3 as default
        
        return relevant_examples
    
    def _get_practice_exercises(self, weakness: WeakArea) -> List[Dict[str, str]]:
        """Get practice exercises for a weakness."""
        exercises = []
        base_practices = self.practice_recommendations.get(weakness.skill, [])
        
        for practice in base_practices:
            exercise = {
                'type': practice,
                'description': self._get_exercise_description(practice, weakness.language),
                'difficulty': 'adjusted_for_weakness',
                'focus_areas': weakness.error_patterns
            }
            exercises.append(exercise)
        
        return exercises
    
    def _calculate_improvement_timeline(self, severity: float) -> Dict[str, str]:
        """Calculate expected improvement timeline based on severity."""
        if severity >= 0.8:
            return {
                'short_term': '2-3周内看到初步改善',
                'medium_term': '1-2个月内显著提升',
                'long_term': '3-4个月内基本掌握'
            }
        elif severity >= 0.5:
            return {
                'short_term': '1-2周内看到改善',
                'medium_term': '3-4周内显著提升',
                'long_term': '2-3个月内熟练掌握'
            }
        else:
            return {
                'short_term': '几天内看到改善',
                'medium_term': '1-2周内显著提升',
                'long_term': '1个月内完全掌握'
            }
    
    def _define_success_metrics(self, weakness: WeakArea) -> List[str]:
        """Define success metrics for improvement."""
        return [
            f"错误率降低到{max(0.1, weakness.severity * 0.3):.1f}以下",
            f"相关练习准确率达到85%以上",
            f"连续一周无相关错误",
            f"能够正确应用到新语境中"
        ]
    
    def _generate_chinese_explanation(self, weakness: WeakArea) -> str:
        """Generate Chinese explanation for the weakness."""
        skill_names = {
            Skill.VOCABULARY: "词汇",
            Skill.GRAMMAR: "语法",
            Skill.READING: "阅读",
            Skill.LISTENING: "听力",
            Skill.SPEAKING: "口语",
            Skill.WRITING: "写作",
            Skill.PRONUNCIATION: "发音",
            Skill.COMPREHENSION: "理解"
        }
        
        skill_name = skill_names.get(weakness.skill, "语言技能")
        language_name = "英语" if weakness.language == "english" else "日语"
        
        explanation = f"您在{language_name}{skill_name}方面存在弱点，"
        explanation += f"严重程度为{weakness.severity:.1f}（满分1.0）。"
        
        if weakness.error_patterns:
            explanation += f"主要错误模式包括：{', '.join(weakness.error_patterns[:3])}。"
        
        explanation += "建议通过针对性练习和系统学习来改善这一弱点。"
        
        return explanation
    
    def _get_vocabulary_examples(self, concept: str, language: str) -> List[str]:
        """Get vocabulary-specific examples."""
        examples = self.example_database.get(Skill.VOCABULARY, {}).get(language, [])
        return examples[:5]  # Return top 5 examples
    
    def _get_grammar_examples(self, concept: str, language: str) -> List[str]:
        """Get grammar-specific examples."""
        examples = self.example_database.get(Skill.GRAMMAR, {}).get(language, [])
        return examples[:5]
    
    def _get_pronunciation_examples(self, concept: str, language: str) -> List[str]:
        """Get pronunciation-specific examples."""
        # Pronunciation examples would be audio-based in real implementation
        return [
            f"发音练习示例 - {concept}",
            f"语音对比练习 - {concept}",
            f"语调练习 - {concept}"
        ]
    
    def _get_general_examples(self, concept: str, language: str) -> List[str]:
        """Get general examples for any concept."""
        return [
            f"基础练习示例 - {concept}",
            f"应用练习示例 - {concept}",
            f"综合练习示例 - {concept}"
        ]
    
    def _add_chinese_explanation(self, example: str, concept: str, language: str) -> str:
        """Add Chinese explanation to an example."""
        if "(" in example and ")" in example:
            # Already has Chinese explanation
            return example
        else:
            # Add basic Chinese explanation
            return f"{example} (针对{concept}的练习示例)"
    
    def _adjust_difficulty_for_level(self, practice: str, level: str) -> str:
        """Adjust practice difficulty based on user level."""
        if level in ["CET-4", "N5"]:
            return "beginner"
        elif level in ["CET-5", "N4", "N3"]:
            return "intermediate"
        else:
            return "advanced"
    
    def _estimate_practice_duration(self, practice: str, skill: Skill) -> str:
        """Estimate duration for practice exercise."""
        duration_map = {
            "flashcard_review": "10-15分钟",
            "fill_in_blanks": "15-20分钟",
            "conversation_practice": "20-30分钟",
            "reading_comprehension": "25-35分钟",
            "listening_practice": "15-25分钟"
        }
        return duration_map.get(practice, "15-20分钟")
    
    def _recommend_frequency(self, skill: Skill, practice: str) -> str:
        """Recommend practice frequency."""
        if skill in [Skill.VOCABULARY, Skill.PRONUNCIATION]:
            return "每日练习"
        elif skill in [Skill.GRAMMAR, Skill.READING]:
            return "每周3-4次"
        else:
            return "每周2-3次"
    
    def _translate_instructions_to_chinese(self, practice: str, skill: Skill) -> str:
        """Translate practice instructions to Chinese."""
        instructions = {
            "flashcard_review": "使用词汇卡片进行复习，正面显示单词，背面显示含义和例句",
            "fill_in_blanks": "完成语法填空练习，注意时态、语态和词形变化",
            "conversation_practice": "进行对话练习，注意发音、语调和表达的准确性",
            "reading_comprehension": "阅读文章并回答理解问题，注意主旨和细节",
            "listening_practice": "听音频材料并完成相关练习，提高听力理解能力"
        }
        return instructions.get(practice, f"进行{skill.value}相关练习")
    
    def _define_practice_success_criteria(self, practice: str, skill: Skill) -> List[str]:
        """Define success criteria for practice."""
        return [
            "准确率达到80%以上",
            "完成时间在预期范围内",
            "能够应用到实际语境中",
            "错误类型逐渐减少"
        ]
    
    def _analyze_trend(self, scores: List[float]) -> str:
        """Analyze performance trend from recent scores."""
        if len(scores) < 2:
            return "insufficient_data"
        
        # Calculate trend
        first_half = scores[:len(scores)//2]
        second_half = scores[len(scores)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg * 1.1:
            return "improving"
        elif second_avg < first_avg * 0.9:
            return "declining"
        else:
            return "stable"
    
    def _generate_progress_recommendation(self, improvement_rate: float, trend: str, weakness: WeakArea) -> str:
        """Generate recommendation based on progress."""
        if improvement_rate > 20 and trend == "improving":
            return "进步很好！继续当前的学习方法，可以适当增加练习难度。"
        elif improvement_rate > 10 and trend in ["improving", "stable"]:
            return "有一定进步，建议保持当前练习频率，注意巩固已学内容。"
        elif trend == "declining":
            return "最近表现有所下降，建议回顾基础知识，调整学习策略。"
        else:
            return "进步较慢，建议增加练习时间，或尝试不同的学习方法。"
    
    def _get_exercise_description(self, practice: str, language: str) -> str:
        """Get description for practice exercise."""
        descriptions = {
            "flashcard_review": f"使用{language}词汇卡片进行记忆练习",
            "fill_in_blanks": f"完成{language}语法填空题",
            "conversation_practice": f"进行{language}对话练习",
            "reading_comprehension": f"阅读{language}文章并回答问题",
            "listening_practice": f"听{language}音频并完成练习"
        }
        return descriptions.get(practice, f"{language}综合练习")