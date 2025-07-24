"""
Formats Generation Engine
========================

Transforms stories into various engaging formats using strategic AI integration.
Supports multiple output formats while being cost-conscious and quality-focused.

Formats supported:
- Social Media: Twitter, LinkedIn, Instagram, Facebook
- Creative: Poems, Songs, Scripts, Stories
- Professional: Articles, Blog posts, Presentations
- Therapeutic: Insights, Reflections, Growth summaries
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
from enum import Enum
from prompts_engine import PromptType
from format_types import FormatType

logger = logging.getLogger(__name__)

class FormatsGenerationEngine:
    """
    Intelligent engine for transforming stories into various engaging formats.
    Uses strategic AI integration with fallback templates.
    """
    
    def __init__(self, db=None):
        self.db = db
        
        # Initialize OpenAI for format generation using legacy format
        self.openai_client = None
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                import openai
                openai.api_key = api_key
                self.openai_client = openai
                logger.info("FormatsGenerationEngine: OpenAI initialized for format generation")
            else:
                logger.warning("FormatsGenerationEngine: No OpenAI API key - AI generation disabled")
        except Exception as e:
            logger.warning(f"FormatsGenerationEngine: OpenAI initialization failed: {e}")
        
        # Format specifications for consistent output
        self.format_specs = {
            FormatType.X: {
                'max_length': 280,
                'tone': 'engaging',
                'include_hashtags': True,
                'character_limit': True
            },
            FormatType.LINKEDIN: {
                'max_length': 1300,
                'tone': 'professional',
                'include_insights': True,
                'call_to_action': True
            },
            FormatType.INSTAGRAM: {
                'max_length': 2200,
                'tone': 'visual',
                'include_hashtags': True,
                'storytelling': True
            },
            FormatType.POEM: {
                'structure': 'free_verse',
                'tone': 'artistic',
                'emotional_depth': True,
                'metaphors': True
            },
            FormatType.SONG: {
                'max_length': 200,
                'tone': 'lyrical',
                'character_limit': True,
                'musical_structure': True,
                'emotional_resonance': True
            },
            FormatType.ARTICLE: {
                'min_length': 800,
                'structure': 'introduction_body_conclusion',
                'tone': 'informative',
                'include_insights': True
            }
        }
    
    # =============================================================================
    # MAIN FORMAT GENERATION (AI + Templates)
    # =============================================================================
    
    def generate_format(self, story_content: str, format_type: FormatType, 
                       user_context: Dict = None, domain_insights: Dict = None) -> Dict[str, Any]:
        """Main entry point for format generation"""
        
        logger.info(f"Generating {format_type.value} format")
        
        # Get format specifications
        specs = self.format_specs.get(format_type, {})
        
        # Always try AI generation first (and only)
        if self.openai_client:
            logger.info(f"Using AI generation for {format_type.value}")
            result = self._generate_with_ai(story_content, format_type, specs, user_context, domain_insights)
            
            if result.get('success'):
                logger.info(f"AI generation successful for {format_type.value}")
                return result
            else:
                logger.error(f"AI generation failed for {format_type.value}: {result.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'error': f'AI generation failed: {result.get("error", "Unknown error")}',
                    'generation_method': 'failed'
                }
        else:
            logger.error(f"OpenAI client not available for {format_type.value} generation")
            return {
                'success': False,
                'error': 'OpenAI API key required for format generation. Template generation has been disabled.',
                'generation_method': 'unavailable'
            }
    
    def generate_multiple_formats(self, story_content: str, format_types: List[FormatType],
                                user_context: Dict = None, domain_insights: Dict = None) -> Dict[str, Any]:
        """Generate multiple formats efficiently"""
        
        results = {}
        successful_generations = 0
        
        for format_type in format_types:
            try:
                result = self.generate_format(story_content, format_type, user_context, domain_insights)
                results[format_type.value] = result
                
                if result.get('success', False):
                    successful_generations += 1
                    
            except Exception as e:
                logger.error(f"Error generating {format_type.value}: {e}")
                results[format_type.value] = self._create_error_response(str(e))
        
        return {
            'results': results,
            'summary': {
                'total_requested': len(format_types),
                'successful': successful_generations,
                'failed': len(format_types) - successful_generations,
                'generated_at': datetime.now().isoformat()
            }
        }
    
    # =============================================================================
    # AI-POWERED GENERATION (Strategic usage)
    # =============================================================================
    
    def _generate_with_ai(self, content: str, format_type: FormatType, specs: Dict,
                         user_context: Dict = None, domain_insights: Dict = None) -> Dict[str, Any]:
        """Generate format using OpenAI API through prompts engine"""
        
        try:
            # Validate inputs
            if not content or not content.strip():
                return {'success': False, 'error': 'Empty content provided'}
                
            # ALWAYS use prompts engine - no fallback to built-in prompts
            if not hasattr(self, 'prompts_engine') or not self.prompts_engine:
                return {'success': False, 'error': 'Prompts engine not available - required for format generation'}
                
            try:
                prompt = self.prompts_engine.get_prompt(PromptType.FORMAT_GENERATION, 
                                                      format_type=format_type, 
                                                      content=content,
                                                      user_context=user_context,
                                                      domain_insights=domain_insights)
                logger.info(f"Using prompts engine for {format_type.value} generation")
            except Exception as e:
                logger.error(f"Prompts engine failed for {format_type.value}: {e}")
                return {'success': False, 'error': f'Prompts engine failed: {e}'}
            
            # Get system prompt from prompts engine
            try:
                system_prompt = self.prompts_engine.get_system_prompt('format_generation', format_type=format_type)
            except Exception as e:
                logger.warning(f"System prompt failed, using basic system prompt: {e}")
                system_prompt = "You are a skilled content creator who transforms personal stories into engaging formats while preserving their authentic emotional core."
            
            # Use specialized system prompt when available, with song-specific override
            if format_type == FormatType.SONG:
                system_prompt_overridden = (
                    "You are a professional songwriter. Follow the user's instructions exactly. "
                    "Never add section labels like [Verse] or [Chorus] to lyrics unless explicitly requested."
                )
            else:
                system_prompt_overridden = system_prompt
            
            # Make API call using chat format for better instruction following
            try:
                completion = self.openai_client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt_overridden},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1500,
                    temperature=0.7
                )
                generated_content = completion.choices[0].message.content.strip()
                logger.info(f"AI generation successful for {format_type.value}")
                
                # Extract title from generated content
                extracted_title = self._extract_title_from_content(generated_content, format_type)
                
                return {
                    'success': True,
                    'content': generated_content,
                    'title': extracted_title,
                    'generation_method': 'ai',
                    'prompt_used': prompt[:100] + "..." if len(prompt) > 100 else prompt
                }
                
            except Exception as api_error:
                logger.error(f"OpenAI API call failed: {api_error}")
                return {
                    'success': False,
                    'error': f'OpenAI API call failed: {str(api_error)}',
                    'generation_method': 'failed'
                }
                
        except Exception as e:
            logger.error(f"AI generation error for {format_type.value}: {e}")
            return {'success': False, 'error': str(e)}
    
    # =============================================================================
    # ARCHIVED CODE REMOVED: Template generation completely removed to prevent conflicts
    # All generation now uses AI through the prompts engine.
    # =============================================================================
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _select_model_for_format(self, format_type: FormatType) -> str:
        """Select appropriate OpenAI model based on format complexity"""
        
        # Use GPT-4 for complex creative formats
        complex_formats = [FormatType.ARTICLE, FormatType.REEL, FormatType.POEM, FormatType.INSIGHTS, FormatType.PODCAST, FormatType.LETTER]
        
        if format_type in complex_formats:
            return "gpt-4"
        else:
            return "gpt-3.5-turbo"  # Cheaper for social media formats
    
    def _get_max_tokens_for_format(self, format_type: FormatType) -> int:
        """Get appropriate token limit for format"""
        token_limits = {
            FormatType.X: 100,
            FormatType.LINKEDIN: 400,
            FormatType.INSTAGRAM: 600,
            FormatType.POEM: 300,
            FormatType.ARTICLE: 1200,
            FormatType.INSIGHTS: 800
        }
        return token_limits.get(format_type, 500)
    
    def _get_temperature_for_format(self, format_type: FormatType) -> float:
        """Get appropriate creativity level for format"""
        creative_formats = [FormatType.POEM, FormatType.SONG, FormatType.REEL]
        
        if format_type in creative_formats:
            return 0.8  # More creative
        else:
            return 0.6  # Balanced
    
    def _get_system_prompt_for_format(self, format_type: FormatType) -> str:
        """Get system prompt optimized for format"""
        
        system_prompts = {
            # Social Media Formats
            FormatType.X: "You are a social media expert who creates viral, authentic content that resonates emotionally with readers while staying within character limits.",
            FormatType.LINKEDIN: "You are a professional content creator who helps people share meaningful insights in a way that builds genuine connections and encourages professional dialogue.",
            FormatType.INSTAGRAM: "You are an Instagram content specialist who creates visually-oriented, engaging posts that tell stories through authentic, relatable content with strong visual appeal.",
            FormatType.FACEBOOK: "You are a community-focused social media specialist who creates content that brings people together through shared experiences and meaningful conversations.",
            
            # Creative Formats
            FormatType.POEM: "You are a poet who transforms personal experiences into beautiful, moving verse that captures the essence of human emotion and universal truths.",
            FormatType.SONG: "You are a songwriter who creates emotionally resonant lyrics that capture life experiences in musical, memorable language that people can connect with.",
            FormatType.REEL: "You are a viral content creator who transforms personal stories into engaging short-form video scripts for social media reels, with hooks, visual cues, and compelling narratives.",
            FormatType.FAIRYTALE: "You are a skilled fairytale writer who expands personal experiences into magical, enchanting fairytales with whimsical characters, imaginative settings, and narrative depth.",
            
            # Professional Formats
            FormatType.ARTICLE: "You are a skilled writer who creates compelling personal essays that blend storytelling with universal insights and actionable wisdom.",
            FormatType.BLOG_POST: "You are an experienced blogger who creates engaging, shareable content that combines personal storytelling with practical insights and strong reader engagement.",
            FormatType.PRESENTATION: "You are a presentation specialist who transforms stories into compelling, structured presentations that engage audiences and deliver clear takeaways.",
                          FormatType.NEWSLETTER: "You are a newsletter writer who creates personal, engaging content that builds relationships with readers through authentic storytelling and valuable insights.",
              FormatType.PODCAST: "You are a podcast content specialist who creates engaging episode outlines and talking points for intimate, conversational storytelling that would work well with AI-generated audio.",
            FormatType.LETTER: "You are a heartfelt letter writer who crafts warm, personal letters that capture the writer's authentic feelings and nurture meaningful human connections.",
            
            # Therapeutic Formats
            FormatType.INSIGHTS: "You are a therapeutic content specialist who helps people extract meaningful psychological insights from their experiences with practical, actionable guidance.",
            FormatType.GROWTH_SUMMARY: "You are a personal development coach who helps people identify and articulate their growth journey with clear, actionable next steps.",
            FormatType.JOURNAL_ENTRY: "You are a journaling specialist who helps people process experiences through authentic, vulnerable self-expression and emotional exploration.",
            FormatType.REFLECTION: "You are a reflective writing coach guiding individuals to explore their experiences through thoughtful introspection and meaningful insights.",
        }
        
        return system_prompts.get(format_type, "You are a content creation expert who transforms personal stories into engaging formats while preserving their authentic emotional core.")
    
    def _validate_generated_content(self, content: str, format_type: FormatType, specs: Dict) -> Dict[str, Any]:
        """Validate generated content meets format requirements"""
        
        validation = {'valid': True, 'issues': []}
        
        # Check length requirements
        if specs.get('character_limit') and specs.get('max_length'):
            if len(content) > specs['max_length']:
                validation['valid'] = False
                validation['issues'].append(f"Exceeds character limit: {len(content)}/{specs['max_length']}")
        
        # Check for required elements
        if specs.get('include_hashtags') and '#' not in content:
            validation['issues'].append("Missing hashtags")
        
        if specs.get('call_to_action') and '?' not in content:
            validation['issues'].append("Missing call-to-action")
        
        return validation
    
    def _extract_key_words(self, content: str) -> List[str]:
        """Extract key words from content for template generation"""
        
        # Simple keyword extraction
        words = content.lower().split()
        
        # Filter out common words and keep meaningful ones
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}
        key_words = [word.strip('.,!?;:"') for word in words if word not in stop_words and len(word) > 3]
        
        return key_words[:5]  # Return top 5 keywords
    
    def _track_format_generation(self, content: str, format_type: FormatType, result: Dict):
        """Track format generation for analytics"""
        
        if not self.db:
            return
        
        try:
            self.db.collection('format_generations').add({
                'format_type': format_type.value,
                'generation_method': result.get('generation_method', 'unknown'),
                'success': result.get('success', False),
                'content_length': len(content),
                'generated_length': result.get('character_count', 0),
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Failed to track format generation: {e}")
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'success': False,
            'error': error_message,
            'generated_at': datetime.now().isoformat(),
            'content': None
        }

    def _extract_title_from_content(self, content: str, format_type: FormatType) -> str:
        """Extract title from generated content"""
        # Implement your logic to extract title based on the format type
        # This is a placeholder and should be replaced with the actual implementation
        return "Default Title"
    
    # Special compilation format uses list of stories
    def _generate_book_chapter(self, stories_markdown: str) -> Dict[str, Any]:
        try:
            prompt = self.prompts_engine.get_prompt(PromptType.BOOK_CHAPTER, stories_markdown=stories_markdown)
            response = self.openai_client.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.prompts_engine.get_system_prompt(PromptType.BOOK_CHAPTER)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2048
            )
            content = response.choices[0].message.content.strip()
            return {
                "success": True,
                "content": content,
                "generation_method": "openai_gpt4o"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    