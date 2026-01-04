"""
Level-Appropriate Content Generator - Creates and filters content based on user proficiency levels.
"""

from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime
import uuid
import re

from ..models import (
    Content, ContentType, UserProfile, LearningActivity, 
    ActivityType, Skill, WeakArea
)


class LevelAppropriateContentGenerator:
    """
    Generates and filters content appropriate for user's proficiency levels.
    Implements content filtering by proficiency level, vocabulary and grammar matching,
    and difficulty assessment algorithms.
    """
    
    def __init__(self):
        """Initialize the level-appropriate content generator."""
        self.vocabulary_levels = self._load_vocabulary_levels()
        self.grammar_levels = self._load_grammar_levels()
        self.difficulty_metrics = self._load_difficulty_metrics()
        self.level_hierarchies = self._load_level_hierarchies()
    
    def generate_level_appropriate_content(self, user_profile: UserProfile, 
                                         language: str, content_type: ContentType,
                                         topic: Optional[str] = None) -> List[Content]:
        """
        Generate content appropriate for user's current proficiency level.
        
        Args:
            user_profile: User's profile with current levels and preferences
            language: Target language (english/japanese)
            content_type: Type of content to generate
            topic: Optional specific topic to focus on
            
        Returns:
            List of Content objects appropriate for user's level
        """
        # Get user's current level for the language
        current_level = self._get_user_level(user_profile, language)
        
        # Generate base content for the level
        base_content = self._generate_base_content(language, current_level, content_type, topic)
        
        # Filter content by vocabulary appropriateness
        vocab_filtered = self._filter_by_vocabulary_level(base_content, language, current_level)
        
        # Filter content by grammar complexity
        grammar_filtered = self._filter_by_grammar_level(vocab_filtered, language, current_level)
        
        # Assess and adjust difficulty
        difficulty_assessed = self._assess_and_adjust_difficulty(grammar_filtered, current_level)
        
        # Prioritize based on user's weak areas
        prioritized_content = self._prioritize_by_weak_areas(
            difficulty_assessed, user_profile.weak_areas, language
        )
        
        return prioritized_content
    
    def assess_content_difficulty(self, content: Content) -> str:
        """
        Assess the difficulty level of existing content.
        
        Args:
            content: Content to assess
            
        Returns:
            Assessed difficulty level string
        """
        language = content.language
        text = content.title + " " + content.body
        
        # Calculate vocabulary difficulty
        vocab_difficulty = self._calculate_vocabulary_difficulty(text, language)
        
        # Calculate grammar difficulty
        grammar_difficulty = self._calculate_grammar_difficulty(text, language)
        
        # Calculate structural complexity
        structural_difficulty = self._calculate_structural_difficulty(text)
        
        # Combine metrics to determine overall difficulty
        overall_difficulty = (vocab_difficulty + grammar_difficulty + structural_difficulty) / 3
        
        return self._map_difficulty_to_level(overall_difficulty, language)
    
    def match_vocabulary_to_level(self, vocabulary_list: List[str], 
                                language: str, target_level: str) -> List[str]:
        """
        Filter vocabulary list to match target proficiency level.
        
        Args:
            vocabulary_list: List of vocabulary words
            language: Language of the vocabulary
            target_level: Target proficiency level
            
        Returns:
            Filtered vocabulary list appropriate for the level
        """
        if language not in self.vocabulary_levels:
            return vocabulary_list
        
        level_vocab = self.vocabulary_levels[language].get(target_level, set())
        
        # Include vocabulary from current level and below
        allowed_vocab = set()
        level_hierarchy = self.level_hierarchies[language]
        
        try:
            target_index = level_hierarchy.index(target_level)
            for i in range(target_index + 1):
                level_name = level_hierarchy[i]
                allowed_vocab.update(self.vocabulary_levels[language].get(level_name, set()))
        except ValueError:
            # If level not found, return original list
            return vocabulary_list
        
        # Filter vocabulary to only include appropriate words
        filtered_vocab = [word for word in vocabulary_list if word.lower() in allowed_vocab]
        
        return filtered_vocab
    
    def match_grammar_to_level(self, content: Content, target_level: str) -> bool:
        """
        Check if content's grammar complexity matches target level.
        
        Args:
            content: Content to check
            target_level: Target proficiency level
            
        Returns:
            True if grammar is appropriate for the level
        """
        language = content.language
        if language not in self.grammar_levels:
            return True
        
        text = content.title + " " + content.body
        grammar_patterns = self._extract_grammar_patterns(text, language)
        
        # Get allowed grammar patterns for the level
        allowed_patterns = set()
        level_hierarchy = self.level_hierarchies[language]
        
        try:
            target_index = level_hierarchy.index(target_level)
            for i in range(target_index + 1):
                level_name = level_hierarchy[i]
                allowed_patterns.update(self.grammar_levels[language].get(level_name, set()))
        except ValueError:
            return True
        
        # Check if all grammar patterns in content are allowed
        for pattern in grammar_patterns:
            if pattern not in allowed_patterns:
                return False
        
        return True
    
    def adjust_content_for_level(self, content: Content, target_level: str) -> Content:
        """
        Adjust existing content to be appropriate for target level.
        
        Args:
            content: Original content
            target_level: Target proficiency level
            
        Returns:
            Adjusted content appropriate for the level
        """
        # Create a copy of the content
        adjusted_content = Content(
            content_id=str(uuid.uuid4()),
            title=content.title,
            body=content.body,
            language=content.language,
            difficulty_level=target_level,
            content_type=content.content_type,
            source_url=content.source_url,
            quality_score=content.quality_score,
            created_at=datetime.now(),
            tags=content.tags + ["level_adjusted"]
        )
        
        # Adjust vocabulary complexity
        adjusted_content.body = self._adjust_vocabulary_complexity(
            adjusted_content.body, content.language, target_level
        )
        
        # Adjust sentence structure if needed
        adjusted_content.body = self._adjust_sentence_structure(
            adjusted_content.body, content.language, target_level
        )
        
        # Update difficulty level
        adjusted_content.difficulty_level = target_level
        
        return adjusted_content
    
    def _get_user_level(self, user_profile: UserProfile, language: str) -> str:
        """Get user's current level for specified language."""
        if language == "english":
            return user_profile.english_level
        elif language == "japanese":
            return user_profile.japanese_level
        else:
            return "beginner"
    
    def _generate_base_content(self, language: str, level: str, 
                             content_type: ContentType, topic: Optional[str]) -> List[Content]:
        """Generate base content for the specified parameters."""
        # This is a simplified implementation - in a real system, this would
        # interface with content crawlers and databases
        
        content_templates = self._get_content_templates(language, level, content_type)
        generated_content = []
        
        for template in content_templates:
            content = Content(
                content_id=str(uuid.uuid4()),
                title=template["title"],
                body=template["body"],
                language=language,
                difficulty_level=level,
                content_type=content_type,
                source_url="internal://generated",
                quality_score=0.8,
                created_at=datetime.now(),
                tags=[language, level, content_type.value]
            )
            
            if topic:
                content.tags.append(topic)
            
            generated_content.append(content)
        
        return generated_content
    
    def _filter_by_vocabulary_level(self, content_list: List[Content], 
                                   language: str, level: str) -> List[Content]:
        """Filter content based on vocabulary appropriateness."""
        filtered_content = []
        
        for content in content_list:
            if self._is_vocabulary_appropriate(content, language, level):
                filtered_content.append(content)
        
        return filtered_content
    
    def _filter_by_grammar_level(self, content_list: List[Content], 
                                language: str, level: str) -> List[Content]:
        """Filter content based on grammar complexity."""
        filtered_content = []
        
        for content in content_list:
            if self.match_grammar_to_level(content, level):
                filtered_content.append(content)
        
        return filtered_content
    
    def _assess_and_adjust_difficulty(self, content_list: List[Content], 
                                    target_level: str) -> List[Content]:
        """Assess and adjust content difficulty to match target level."""
        adjusted_content = []
        
        for content in content_list:
            assessed_level = self.assess_content_difficulty(content)
            
            if assessed_level == target_level:
                adjusted_content.append(content)
            else:
                # Try to adjust content to target level
                try:
                    adjusted = self.adjust_content_for_level(content, target_level)
                    adjusted_content.append(adjusted)
                except Exception:
                    # If adjustment fails, skip this content
                    continue
        
        return adjusted_content
    
    def _prioritize_by_weak_areas(self, content_list: List[Content], 
                                weak_areas: List[WeakArea], language: str) -> List[Content]:
        """Prioritize content based on user's identified weak areas."""
        if not weak_areas:
            return content_list
        
        # Get weak areas for this language
        language_weaknesses = [w for w in weak_areas if w.language == language]
        if not language_weaknesses:
            return content_list
        
        # Score content based on how well it addresses weaknesses
        scored_content = []
        for content in content_list:
            weakness_score = self._calculate_weakness_coverage_score(content, language_weaknesses)
            scored_content.append((content, weakness_score))
        
        # Sort by weakness coverage score (descending)
        scored_content.sort(key=lambda x: x[1], reverse=True)
        
        return [content for content, score in scored_content]
    
    def _is_vocabulary_appropriate(self, content: Content, language: str, level: str) -> bool:
        """Check if content vocabulary is appropriate for the level."""
        text = content.title + " " + content.body
        words = self._extract_words(text, language)
        
        # Check what percentage of words are appropriate for the level
        appropriate_words = self.match_vocabulary_to_level(words, language, level)
        
        if not words:
            return True
        
        appropriateness_ratio = len(appropriate_words) / len(words)
        
        # Require at least 80% of words to be appropriate for the level
        return appropriateness_ratio >= 0.8
    
    def _calculate_vocabulary_difficulty(self, text: str, language: str) -> float:
        """Calculate vocabulary difficulty score (0.0 to 1.0)."""
        words = self._extract_words(text, language)
        if not words:
            return 0.0
        
        difficulty_scores = []
        
        for word in words:
            word_difficulty = self._get_word_difficulty(word, language)
            difficulty_scores.append(word_difficulty)
        
        return sum(difficulty_scores) / len(difficulty_scores)
    
    def _calculate_grammar_difficulty(self, text: str, language: str) -> float:
        """Calculate grammar complexity score (0.0 to 1.0)."""
        grammar_patterns = self._extract_grammar_patterns(text, language)
        
        if not grammar_patterns:
            return 0.0
        
        difficulty_scores = []
        
        for pattern in grammar_patterns:
            pattern_difficulty = self._get_grammar_pattern_difficulty(pattern, language)
            difficulty_scores.append(pattern_difficulty)
        
        return sum(difficulty_scores) / len(difficulty_scores)
    
    def _calculate_structural_difficulty(self, text: str) -> float:
        """Calculate structural complexity score (0.0 to 1.0)."""
        # Analyze sentence length, complexity, etc.
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        # Calculate average sentence length
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        # Normalize to 0-1 scale (assuming 20+ words is complex)
        length_complexity = min(1.0, avg_sentence_length / 20.0)
        
        # Check for complex punctuation patterns
        complex_punctuation = len(re.findall(r'[;:,\-\(\)]', text)) / len(text)
        punctuation_complexity = min(1.0, complex_punctuation * 100)
        
        return (length_complexity + punctuation_complexity) / 2
    
    def _map_difficulty_to_level(self, difficulty_score: float, language: str) -> str:
        """Map difficulty score to proficiency level."""
        if language == "english":
            if difficulty_score < 0.3:
                return "CET-4"
            elif difficulty_score < 0.6:
                return "CET-5"
            else:
                return "CET-6"
        elif language == "japanese":
            if difficulty_score < 0.2:
                return "N5"
            elif difficulty_score < 0.4:
                return "N4"
            elif difficulty_score < 0.6:
                return "N3"
            elif difficulty_score < 0.8:
                return "N2"
            else:
                return "N1"
        else:
            return "beginner"
    
    def _extract_words(self, text: str, language: str) -> List[str]:
        """Extract words from text based on language."""
        # Simple word extraction - can be enhanced with proper tokenization
        if language == "japanese":
            # For Japanese, we'd need proper tokenization (MeCab, etc.)
            # For now, use simple character-based approach
            words = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', text)
        else:
            # For English and other languages
            words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        return words
    
    def _extract_grammar_patterns(self, text: str, language: str) -> Set[str]:
        """Extract grammar patterns from text."""
        patterns = set()
        
        if language == "english":
            # Simple English grammar pattern detection
            if re.search(r'\b(have|has)\s+\w+ed\b', text):
                patterns.add("present_perfect")
            if re.search(r'\bwill\s+\w+\b', text):
                patterns.add("future_simple")
            if re.search(r'\b\w+ing\b', text):
                patterns.add("present_continuous")
            if re.search(r'\bif\s+.*,\s+.*would\b', text):
                patterns.add("conditional")
        
        elif language == "japanese":
            # Simple Japanese grammar pattern detection
            if re.search(r'です|である', text):
                patterns.add("polite_form")
            if re.search(r'ます', text):
                patterns.add("masu_form")
            if re.search(r'た|だ', text):
                patterns.add("past_tense")
            if re.search(r'ている', text):
                patterns.add("progressive")
        
        return patterns
    
    def _get_word_difficulty(self, word: str, language: str) -> float:
        """Get difficulty score for a specific word."""
        # Simplified difficulty assessment
        if language not in self.vocabulary_levels:
            return 0.5
        
        # Check which level the word belongs to
        for level, vocab_set in self.vocabulary_levels[language].items():
            if word.lower() in vocab_set:
                level_hierarchy = self.level_hierarchies[language]
                try:
                    level_index = level_hierarchy.index(level)
                    return level_index / len(level_hierarchy)
                except ValueError:
                    continue
        
        # If word not found in any level, assume it's advanced
        return 0.9
    
    def _get_grammar_pattern_difficulty(self, pattern: str, language: str) -> float:
        """Get difficulty score for a grammar pattern."""
        # Simplified grammar difficulty mapping
        if language not in self.grammar_levels:
            return 0.5
        
        for level, patterns_set in self.grammar_levels[language].items():
            if pattern in patterns_set:
                level_hierarchy = self.level_hierarchies[language]
                try:
                    level_index = level_hierarchy.index(level)
                    return level_index / len(level_hierarchy)
                except ValueError:
                    continue
        
        return 0.7  # Default for unknown patterns
    
    def _adjust_vocabulary_complexity(self, text: str, language: str, target_level: str) -> str:
        """Adjust vocabulary complexity to match target level."""
        # This is a simplified implementation
        # In a real system, this would involve sophisticated NLP
        words = self._extract_words(text, language)
        appropriate_words = self.match_vocabulary_to_level(words, language, target_level)
        
        # For now, just return original text
        # Real implementation would replace complex words with simpler alternatives
        return text
    
    def _adjust_sentence_structure(self, text: str, language: str, target_level: str) -> str:
        """Adjust sentence structure complexity to match target level."""
        # Simplified implementation - would need sophisticated NLP in practice
        return text
    
    def _calculate_weakness_coverage_score(self, content: Content, 
                                         weak_areas: List[WeakArea]) -> float:
        """Calculate how well content addresses user's weak areas."""
        if not weak_areas:
            return 0.0
        
        coverage_score = 0.0
        
        for weakness in weak_areas:
            # Check if content addresses this weakness
            if self._content_addresses_weakness(content, weakness):
                # Weight by weakness severity
                coverage_score += weakness.severity
        
        return coverage_score / len(weak_areas)
    
    def _content_addresses_weakness(self, content: Content, weakness: WeakArea) -> bool:
        """Check if content addresses a specific weakness."""
        # Check if content type matches weakness skill
        skill_to_activity = {
            Skill.VOCABULARY: [ContentType.EXERCISE, ContentType.ARTICLE],
            Skill.GRAMMAR: [ContentType.EXERCISE, ContentType.DIALOGUE],
            Skill.READING: [ContentType.ARTICLE, ContentType.NEWS],
            Skill.LISTENING: [ContentType.AUDIO, ContentType.VIDEO],
            Skill.SPEAKING: [ContentType.DIALOGUE, ContentType.AUDIO],
            Skill.WRITING: [ContentType.EXERCISE]
        }
        
        appropriate_types = skill_to_activity.get(weakness.skill, [])
        if content.content_type in appropriate_types:
            return True
        
        # Check if content tags match weakness patterns
        for pattern in weakness.error_patterns:
            if pattern.lower() in content.body.lower() or pattern.lower() in ' '.join(content.tags):
                return True
        
        return False
    
    def _get_content_templates(self, language: str, level: str, 
                             content_type: ContentType) -> List[Dict[str, str]]:
        """Get content templates for specified parameters."""
        # Simplified template system - would be much more sophisticated in practice
        templates = []
        
        if language == "english" and level == "CET-4":
            if content_type == ContentType.ARTICLE:
                templates.append({
                    "title": "Daily Life in English",
                    "body": "Learning English through daily activities helps students improve their language skills. Simple conversations about weather, food, and hobbies provide practical vocabulary for everyday use."
                })
            elif content_type == ContentType.EXERCISE:
                templates.append({
                    "title": "Basic Grammar Exercise",
                    "body": "Complete the sentences with the correct form of the verb: 1. I ___ (go) to school every day. 2. She ___ (like) reading books."
                })
        
        elif language == "japanese" and level == "N5":
            if content_type == ContentType.ARTICLE:
                templates.append({
                    "title": "日本の文化",
                    "body": "日本には美しい文化があります。桜の季節には多くの人が花見をします。日本料理も世界中で人気です。"
                })
            elif content_type == ContentType.EXERCISE:
                templates.append({
                    "title": "ひらがな練習",
                    "body": "次の単語をひらがなで書いてください：1. 学校 2. 友達 3. 先生"
                })
        
        return templates if templates else [{"title": "Sample Content", "body": "Sample content for practice."}]
    
    def _load_vocabulary_levels(self) -> Dict[str, Dict[str, Set[str]]]:
        """Load vocabulary organized by language and proficiency level."""
        return {
            "english": {
                "CET-4": {"hello", "good", "morning", "student", "school", "book", "read", "write", "learn", "study"},
                "CET-5": {"academic", "research", "analysis", "development", "professional", "communication"},
                "CET-6": {"sophisticated", "comprehensive", "methodology", "implementation", "theoretical"}
            },
            "japanese": {
                "N5": {"こんにちは", "学生", "学校", "本", "読む", "書く", "勉強", "友達"},
                "N4": {"研究", "分析", "開発", "専門", "コミュニケーション"},
                "N3": {"理論", "方法論", "実装", "包括的"},
                "N2": {"洗練された", "体系的", "概念的"},
                "N1": {"哲学的", "抽象的", "複雑"}
            }
        }
    
    def _load_grammar_levels(self) -> Dict[str, Dict[str, Set[str]]]:
        """Load grammar patterns organized by language and proficiency level."""
        return {
            "english": {
                "CET-4": {"present_simple", "present_continuous", "past_simple"},
                "CET-5": {"present_perfect", "future_simple", "conditional"},
                "CET-6": {"past_perfect", "subjunctive", "complex_conditional"}
            },
            "japanese": {
                "N5": {"masu_form", "polite_form", "present_tense"},
                "N4": {"past_tense", "progressive", "potential_form"},
                "N3": {"passive_voice", "causative", "conditional"},
                "N2": {"honorific", "humble", "complex_conditional"},
                "N1": {"literary_forms", "classical_grammar", "advanced_keigo"}
            }
        }
    
    def _load_difficulty_metrics(self) -> Dict[str, Dict[str, float]]:
        """Load difficulty metrics for assessment."""
        return {
            "vocabulary_complexity": {"simple": 0.2, "intermediate": 0.5, "advanced": 0.8},
            "grammar_complexity": {"basic": 0.2, "intermediate": 0.5, "advanced": 0.8},
            "structural_complexity": {"simple": 0.2, "moderate": 0.5, "complex": 0.8}
        }
    
    def _load_level_hierarchies(self) -> Dict[str, List[str]]:
        """Load proficiency level hierarchies for each language."""
        return {
            "english": ["CET-4", "CET-5", "CET-6", "CET-6+"],
            "japanese": ["N5", "N4", "N3", "N2", "N1", "N1+"]
        }