"""
Chinese Interface Layer - Ensures all user interactions are in Chinese.
"""

import re
from typing import Dict, Any, Optional
from ..models import Content, ChineseInterfaceInterface, Skill, ActivityType


class ChineseInterface(ChineseInterfaceInterface):
    """
    Ensures all user interactions are conducted in Chinese with culturally
    appropriate communication.
    """
    
    def __init__(self):
        """Initialize the Chinese interface with message templates."""
        self.message_templates = self._load_message_templates()
        self.cultural_contexts = self._load_cultural_contexts()
        self.phonetic_mappings = self._load_phonetic_mappings()
        self.grammar_explanations = self._load_grammar_explanations()
    
    def display_message(self, message_key: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Display a localized message in Chinese.
        
        Args:
            message_key: Key for the message template
            params: Parameters to substitute in the message
            
        Returns:
            Formatted Chinese message
        """
        if params is None:
            params = {}
            
        template = self.message_templates.get(message_key, f"未找到消息模板: {message_key}")
        
        try:
            # Format the template with provided parameters
            formatted_message = template.format(**params)
            return formatted_message
        except KeyError as e:
            # Handle missing parameters gracefully
            return f"消息格式错误，缺少参数: {e}"
    
    def format_feedback(self, feedback: str) -> str:
        """
        Format feedback in Chinese with appropriate tone and style.
        
        Args:
            feedback: Raw feedback content
            
        Returns:
            Formatted Chinese feedback
        """
        # Add encouraging tone and proper formatting
        if not feedback:
            return "继续努力！"
        
        # Add appropriate prefixes based on feedback type
        if "correct" in feedback.lower() or "正确" in feedback:
            return f"✓ 很好！{feedback}"
        elif "incorrect" in feedback.lower() or "错误" in feedback:
            return f"✗ 需要改进：{feedback}"
        elif "hint" in feedback.lower() or "提示" in feedback:
            return f"💡 提示：{feedback}"
        else:
            return f"📝 反馈：{feedback}"
    
    def translate_content(self, content: Content, target_lang: str) -> str:
        """
        Translate content with Chinese explanations and cultural context.
        
        Args:
            content: Content to translate
            target_lang: Target language for translation
            
        Returns:
            Translated content with Chinese explanations
        """
        # If content is already in Chinese, return as-is
        if content.language.lower() == "chinese" or content.language.lower() == "中文":
            return content.body
        
        # For foreign language content, always provide Chinese explanations
        # regardless of target language
        translation = f"【{content.language.upper()}原文】\n{content.body}\n\n"
        
        if content.language.lower() == "english":
            translation += "【中文解释】\n"
            translation += self._add_english_explanations(content.body)
        elif content.language.lower() == "japanese":
            translation += "【中文解释】\n"
            translation += self._add_japanese_explanations(content.body)
        else:
            # For other languages or edge cases, provide generic explanation
            translation += "【中文解释】\n"
            translation += f"这是{content.language}语言内容，建议查阅相关词典了解具体含义。"
        
        # Add cultural context if available
        cultural_context = self._get_cultural_context_for_content(content)
        if cultural_context:
            translation += f"\n\n【文化背景】\n{cultural_context}"
        
        return translation
    
    def provide_cultural_context(self, concept: str) -> str:
        """
        Provide cultural context for foreign language concepts in Chinese.
        
        Args:
            concept: Foreign language concept
            
        Returns:
            Cultural context explanation in Chinese
        """
        concept_lower = concept.lower()
        
        # Check for direct matches first
        if concept_lower in self.cultural_contexts:
            return self.cultural_contexts[concept_lower]
        
        # Check for partial matches
        for key, context in self.cultural_contexts.items():
            if concept_lower in key or key in concept_lower:
                return context
        
        # Provide generic cultural context based on language
        if any(eng_word in concept_lower for eng_word in ["english", "british", "american"]):
            return "英语文化强调直接表达和个人主义，与中文的含蓄表达方式有所不同。"
        elif any(jp_word in concept_lower for jp_word in ["japanese", "japan", "日本"]):
            return "日本文化重视礼貌和等级秩序，这在语言使用中体现得尤为明显。"
        
        return f"关于 '{concept}' 的文化背景信息暂时不可用，建议查阅相关文化资料。"
    
    def provide_pronunciation_guidance(self, word: str, language: str) -> str:
        """
        Provide pronunciation guidance using Chinese phonetic descriptions.
        
        Args:
            word: Word to provide pronunciation for
            language: Language of the word (english/japanese)
            
        Returns:
            Chinese phonetic description
        """
        if language.lower() == "english":
            return self._get_english_pronunciation(word)
        elif language.lower() == "japanese":
            return self._get_japanese_pronunciation(word)
        else:
            return f"暂不支持 {language} 语言的发音指导"
    
    def explain_grammar_rule(self, rule: str, language: str) -> str:
        """
        Explain grammar rules in Chinese with examples.
        
        Args:
            rule: Grammar rule to explain
            language: Language of the grammar rule
            
        Returns:
            Chinese explanation of the grammar rule
        """
        rule_key = f"{language.lower()}_{rule.lower()}"
        
        if rule_key in self.grammar_explanations:
            return self.grammar_explanations[rule_key]
        
        # Provide generic explanation
        return f"【语法规则】{rule}\n这是{language}语法中的重要概念，建议通过练习加深理解。"
    
    def _load_message_templates(self) -> Dict[str, str]:
        """Load Chinese message templates."""
        return {
            # Session management
            "welcome": "欢迎使用双语导师系统！",
            "session_start": "开始今日学习计划",
            "session_complete": "恭喜完成今日学习！",
            "session_paused": "学习已暂停，稍后可继续",
            "session_resumed": "继续学习计划",
            
            # Level progression
            "level_up": "恭喜！您已升级到 {level} 级别！",
            "level_up_english": "英语水平提升至 {level}！",
            "level_up_japanese": "日语水平提升至 {level}！",
            
            # Progress feedback
            "progress_good": "学习进度良好，继续保持！",
            "progress_excellent": "学习进度优秀，超出预期！",
            "progress_needs_improvement": "需要加强练习，建议增加学习时间",
            
            # Activity feedback
            "vocabulary_mastered": "词汇 '{word}' 已掌握！",
            "grammar_understood": "语法点 '{rule}' 理解正确！",
            "exercise_completed": "练习完成，正确率 {accuracy}%",
            
            # Error messages
            "content_not_found": "未找到合适的学习内容",
            "session_error": "学习会话出现错误，请重试",
            "network_error": "网络连接问题，请检查网络设置",
            
            # Encouragement
            "keep_going": "继续努力，您正在进步！",
            "daily_goal_reached": "今日学习目标已达成！",
            "streak_maintained": "已连续学习 {days} 天！",
            
            # Time management
            "time_allocation": "今日学习时间分配：英语 {english_min} 分钟，日语 {japanese_min} 分钟",
            "review_time": "复习时间：{review_min} 分钟",
            "break_reminder": "建议休息 {break_min} 分钟后继续学习",
        }
    
    def _load_cultural_contexts(self) -> Dict[str, str]:
        """Load cultural context explanations."""
        return {
            # English cultural contexts
            "english_formal": "英语中的正式用语类似于中文的书面语，多用于商务和学术场合",
            "english_informal": "英语口语更加直接和随意，朋友间常用缩写和俚语",
            "american_english": "美式英语发音较为清晰，语调相对平缓",
            "british_english": "英式英语发音更加正式，有明显的阶层色彩",
            "english_politeness": "英语的礼貌用语如'please'和'thank you'使用频率很高",
            
            # Japanese cultural contexts
            "japanese_keigo": "日语敬语体系反映了日本社会的等级观念，分为尊敬语、谦让语和丁宁语",
            "japanese_formal": "日语正式场合必须使用敬语，体现对对方的尊重",
            "japanese_casual": "日语朋友间可以使用普通形，但仍需注意上下级关系",
            "japanese_bowing": "日语中的问候语往往伴随鞠躬，体现日本的礼仪文化",
            "japanese_seasons": "日语中有丰富的季节词汇，反映日本人对自然的敏感",
            
            # General language learning
            "language_immersion": "语言学习需要创造沉浸式环境，多听多说多练习",
            "cultural_sensitivity": "学习语言时要了解文化背景，避免文化冲突",
            "pronunciation_importance": "发音准确性直接影响交流效果，需要重点练习",
        }
    
    def _load_phonetic_mappings(self) -> Dict[str, str]:
        """Load phonetic description mappings for pronunciation guidance."""
        return {
            # English phonetic mappings (IPA to Chinese description)
            "θ": "咬舌音，舌尖轻触上齿",
            "ð": "浊咬舌音，舌尖轻触上齿并振动",
            "ʃ": "嘘音，类似中文'嘘'",
            "ʒ": "浊嘘音，类似中文'日'的声母",
            "tʃ": "齿音，类似中文'吃'",
            "dʒ": "浊齿音，类似中文'机'",
            "r": "卷舌音，舌尖向上卷",
            "l": "舌音，舌尖抵住上齿龈",
            
            # Japanese phonetic mappings (romaji to Chinese description)
            "tsu": "促音，类似中文'次'但更短促",
            "chi": "齿音，类似中文'七'",
            "shi": "嘘音，类似中文'西'",
            "fu": "轻唇音，类似中文'夫'但更轻",
            "ra": "弹舌音，舌尖轻弹上齿龈",
            "rya": "拗音，快速连读",
        }
    
    def _load_grammar_explanations(self) -> Dict[str, str]:
        """Load grammar explanations in Chinese."""
        return {
            # English grammar
            "english_present_perfect": "【现在完成时】表示过去发生但对现在有影响的动作，结构：have/has + 过去分词",
            "english_passive_voice": "【被动语态】强调动作的承受者，结构：be + 过去分词",
            "english_conditional": "【条件句】表示假设情况，分为真实条件句和虚拟条件句",
            "english_gerund": "【动名词】动词的-ing形式作名词使用，可作主语、宾语等",
            
            # Japanese grammar
            "japanese_particles": "【助词】日语的语法标记，如は(主题)、を(宾语)、に(方向/时间)等",
            "japanese_keigo": "【敬语】表示尊敬的语法形式，包括尊敬语、谦让语和丁宁语",
            "japanese_te_form": "【て形】动词的连接形式，用于表示持续、完成等多种意义",
            "japanese_adjectives": "【形容词】分为い形容词和な形容词，变化规则不同",
        }
    
    def _add_english_explanations(self, text: str) -> str:
        """Add Chinese explanations for English text."""
        # Handle edge cases first
        if not text or len(text.strip()) < 3:
            return "内容过短，建议查阅词典了解含义和用法。"
        
        # This is a simplified implementation
        # In a real system, this would use NLP to identify key terms and grammar
        explanations = []
        
        # Look for common English patterns and provide explanations
        if "have been" in text.lower():
            explanations.append("'have been' - 现在完成进行时，表示从过去开始持续到现在的动作")
        
        if "would like" in text.lower():
            explanations.append("'would like' - 礼貌的表达方式，比'want'更正式")
        
        # Check for numbers or minimal content
        if text.strip().isdigit() or len(set(text.strip())) <= 2:
            explanations.append("此内容主要为数字或重复字符，建议在实际语境中学习英语表达。")
        
        if not explanations:
            explanations.append("建议查阅词典了解生词含义和用法。")
        
        return "\n".join(explanations)
    
    def _add_japanese_explanations(self, text: str) -> str:
        """Add Chinese explanations for Japanese text."""
        # Handle edge cases first
        if not text or len(text.strip()) < 2:
            return "内容过短，建议查阅日语词典了解含义。"
        
        # This is a simplified implementation
        explanations = []
        
        # Look for common Japanese patterns
        if "です" in text:
            explanations.append("'です' - 丁宁语结尾，表示礼貌")
        
        if "ます" in text:
            explanations.append("'ます' - 丁宁语动词结尾，正式场合使用")
        
        # Check for numbers or minimal content
        if text.strip().isdigit() or len(set(text.strip())) <= 2:
            explanations.append("此内容主要为数字或重复字符，建议在实际语境中学习日语表达。")
        
        if not explanations:
            explanations.append("建议使用日语词典查阅汉字读音和词义。")
        
        return "\n".join(explanations)
    
    def _get_cultural_context_for_content(self, content: Content) -> Optional[str]:
        """Get cultural context for specific content."""
        # Analyze content tags and type to provide relevant cultural context
        if content.content_type.value == "cultural":
            return "此内容包含文化背景信息，有助于理解语言的实际使用场景"
        
        if "business" in content.tags:
            return "商务场合的语言使用更加正式，需要注意礼貌用语"
        
        if "casual" in content.tags:
            return "日常对话相对随意，但仍需注意基本礼貌"
        
        return None
    
    def _get_english_pronunciation(self, word: str) -> str:
        """Get English pronunciation guidance in Chinese."""
        # This is a simplified implementation
        # In a real system, this would use a pronunciation dictionary
        
        common_pronunciations = {
            "the": "读作'得'，轻声",
            "through": "θru: 咬舌音开头，类似'丝如'",
            "thought": "θɔːt: 咬舌音，类似'骚特'",
            "water": "ˈwɔːtər: 美式发音类似'沃特'",
        }
        
        if word.lower() in common_pronunciations:
            return common_pronunciations[word.lower()]
        
        # Provide general guidance
        guidance = f"'{word}' 的发音指导：\n"
        
        if "th" in word.lower():
            guidance += "- 注意'th'的咬舌音发音\n"
        
        if word.lower().endswith("ed"):
            guidance += "- 过去式结尾发音规则：清辅音后读/t/，浊辅音后读/d/\n"
        
        guidance += "建议查阅发音词典获取准确音标"
        
        return guidance
    
    def _get_japanese_pronunciation(self, word: str) -> str:
        """Get Japanese pronunciation guidance in Chinese."""
        # This is a simplified implementation
        
        common_pronunciations = {
            "こんにちは": "kon-ni-chi-wa: 你好，重音在'ni'",
            "ありがとう": "a-ri-ga-to-u: 谢谢，重音在'ga'",
            "すみません": "su-mi-ma-sen: 对不起，重音在'ma'",
        }
        
        if word in common_pronunciations:
            return common_pronunciations[word]
        
        # Provide general guidance
        guidance = f"'{word}' 的发音指导：\n"
        guidance += "- 日语发音相对规整，每个假名发音时长相等\n"
        guidance += "- 注意长音和促音的区别\n"
        guidance += "建议听标准发音并跟读练习"
        
        return guidance