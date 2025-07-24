"""
Knowledge Engine
===============

Provides domain insights and cross-conversation analysis using strategic AI integration.
Focuses on understanding themes, patterns, and connections across user conversations.

Cost-conscious approach:
- Batch processing for expensive AI analysis
- Rules-based categorization for basic operations
- AI for deep insight generation and semantic connections
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import openai
import os
from collections import defaultdict, Counter
import re

logger = logging.getLogger(__name__)

class KnowledgeEngine:
    """
    Hybrid engine for domain insights and knowledge exploration.
    Balances intelligence with cost-effectiveness.
    """
    
    def __init__(self, db=None):
        self.db = db
        
        # Initialize OpenAI for deep analysis
        self.openai_client = None
        try:
            if os.getenv('OPENAI_API_KEY'):
                openai.api_key = os.getenv('OPENAI_API_KEY')
                self.openai_client = openai
                logger.info("KnowledgeEngine: OpenAI initialized for deep analysis")
            else:
                logger.warning("KnowledgeEngine: No OpenAI - using rules-only approach")
        except Exception as e:
            logger.warning(f"KnowledgeEngine: OpenAI initialization failed: {e}")
        
        # Domain categories for rules-based classification
        self.domain_patterns = {
            'relationships': [
                'family', 'friend', 'partner', 'love', 'marriage', 'dating', 'relationship',
                'connection', 'trust', 'communication', 'conflict', 'support', 'intimacy'
            ],
            'career': [
                'job', 'work', 'career', 'boss', 'colleague', 'promotion', 'interview',
                'salary', 'office', 'business', 'professional', 'skill', 'achievement'
            ],
            'personal_growth': [
                'growth', 'learning', 'insight', 'realization', 'change', 'progress',
                'development', 'improvement', 'reflection', 'discovery', 'understanding'
            ],
            'emotions': [
                'feel', 'emotion', 'mood', 'happy', 'sad', 'angry', 'excited', 'anxious',
                'stress', 'peace', 'joy', 'fear', 'hope', 'guilt', 'pride', 'shame'
            ],
            'health_wellness': [
                'health', 'fitness', 'exercise', 'diet', 'sleep', 'energy', 'wellness',
                'meditation', 'therapy', 'healing', 'recovery', 'balance'
            ],
            'creativity': [
                'creative', 'art', 'music', 'writing', 'design', 'imagination',
                'inspiration', 'expression', 'artistic', 'craft', 'beauty'
            ]
        }
    
    # =============================================================================
    # RULES-BASED DOMAIN ANALYSIS (Fast, cost-effective)
    # =============================================================================
    
    def analyze_story_for_insights(self, content: str, user_id: str) -> Dict[str, Any]:
        """Analyze content for domain insights using rules-based approach"""
        
        # Basic domain classification
        domains = self._classify_content_domains(content)
        
        # Extract key themes using rules
        themes = self._extract_themes_rules_based(content)
        
        # Detect emotional markers
        emotional_markers = self._detect_emotional_markers(content)
        
        # Calculate insight confidence
        confidence = self._calculate_insight_confidence(domains, themes, emotional_markers)
        
        insights = {
            'domains': domains,
            'themes': themes,
            'emotional_markers': emotional_markers,
            'confidence': confidence,
            'analysis_method': 'rules_based',
            'timestamp': datetime.now().isoformat()
        }
        
        # Store insights for future analysis
        if self.db:
            try:
                self.db.collection('content_insights').add({
                    'user_id': user_id,
                    'content_hash': hash(content),
                    'insights': insights,
                    'content_length': len(content),
                    'word_count': len(content.split())
                })
            except Exception as e:
                logger.warning(f"Failed to store insights: {e}")
        
        return insights
    
    def get_user_knowledge_overview(self, user_id: str) -> Dict[str, Any]:
        """Get overview of user's knowledge domains and patterns"""
        if not self.db:
            return self._get_default_knowledge_overview()
        
        try:
            # Get all user insights
            insights_ref = self.db.collection('content_insights').where('user_id', '==', user_id)
            insights_docs = list(insights_ref.stream())
            
            if not insights_docs:
                return self._get_default_knowledge_overview()
            
            # Aggregate insights
            domain_counts = defaultdict(int)
            theme_counts = defaultdict(int)
            emotional_patterns = defaultdict(int)
            
            for doc in insights_docs:
                data = doc.to_dict()
                insights = data.get('insights', {})
                
                # Count domains
                for domain, confidence in insights.get('domains', {}).items():
                    domain_counts[domain] += confidence
                
                # Count themes
                for theme in insights.get('themes', []):
                    theme_counts[theme] += 1
                
                # Count emotional markers
                for emotion in insights.get('emotional_markers', []):
                    emotional_patterns[emotion] += 1
            
            # Calculate top patterns
            top_domains = dict(Counter(domain_counts).most_common(5))
            top_themes = dict(Counter(theme_counts).most_common(10))
            top_emotions = dict(Counter(emotional_patterns).most_common(5))
            
            overview = {
                'total_conversations_analyzed': len(insights_docs),
                'primary_domains': top_domains,
                'common_themes': top_themes,
                'emotional_patterns': top_emotions,
                'knowledge_depth': len(insights_docs) / 10.0,  # Rough measure
                'last_updated': datetime.now().isoformat()
            }
            
            return overview
            
        except Exception as e:
            logger.error(f"Error getting knowledge overview for {user_id}: {e}")
            return self._get_default_knowledge_overview()
    
    # =============================================================================
    # AI-POWERED DEEP ANALYSIS (Strategic usage)
    # =============================================================================
    
    def generate_cross_conversation_insights(self, user_id: str) -> Dict[str, Any]:
        """Generate deep insights across multiple conversations using AI"""
        if not self.openai_client or not self.db:
            return {'insights': [], 'connections': [], 'patterns': []}
        
        try:
            # Get recent conversation data
            insights_ref = (self.db.collection('content_insights')
                          .where('user_id', '==', user_id)
                          .order_by('timestamp', direction='desc')
                          .limit(10))
            
            insights_docs = list(insights_ref.stream())
            
            if len(insights_docs) < 3:
                return {'insights': [], 'connections': [], 'note': 'Need more conversations for cross-analysis'}
            
            # Prepare data for AI analysis
            conversation_themes = []
            for doc in insights_docs:
                data = doc.to_dict()
                insights = data.get('insights', {})
                themes = insights.get('themes', [])
                domains = list(insights.get('domains', {}).keys())
                conversation_themes.append({
                    'themes': themes,
                    'domains': domains,
                    'emotional_markers': insights.get('emotional_markers', [])
                })
            
            # AI analysis prompt
            analysis_prompt = f"""
            Analyze these conversation patterns and provide deep insights:
            
            Conversation data: {json.dumps(conversation_themes, indent=2)}
            
            Provide analysis in this JSON structure:
            {{
                "recurring_patterns": ["pattern1", "pattern2", "pattern3"],
                "cross_domain_connections": ["connection1", "connection2"],
                "growth_trajectory": ["observation1", "observation2"],
                "hidden_themes": ["theme1", "theme2"],
                "emotional_evolution": ["evolution1", "evolution2"],
                "recommended_explorations": ["exploration1", "exploration2"]
            }}
            
            Focus on meaningful patterns that span multiple conversations.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing conversation patterns and identifying deep psychological and behavioral insights."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse AI response
            analysis_text = response.choices[0].message.content.strip()
            
            try:
                cross_insights = json.loads(analysis_text)
                
                # Cache cross-conversation insights
                if self.db:
                    self.db.collection('user_knowledge').document(user_id).set({
                        'cross_conversation_insights': cross_insights,
                        'generated_at': datetime.now().isoformat(),
                        'conversations_analyzed': len(insights_docs)
                    }, merge=True)
                
                return cross_insights
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse cross-conversation insights: {analysis_text}")
                return {'insights': [], 'connections': [], 'note': 'AI analysis parsing failed'}
                
        except Exception as e:
            logger.error(f"Error generating cross-conversation insights: {e}")
            return {'insights': [], 'connections': [], 'error': str(e)}
    
    def find_semantic_connections(self, content: str, user_id: str) -> List[Dict[str, Any]]:
        """Find semantic connections to previous conversations using AI"""
        if not self.openai_client:
            return []
        
        try:
            # Get user's conversation history
            overview = self.get_user_knowledge_overview(user_id)
            
            if not overview.get('common_themes'):
                return []  # Not enough history for connections
            
            # AI prompt for semantic connection finding
            connection_prompt = f"""
            Find semantic connections between this new content and the user's conversation history:
            
            New content: "{content}"
            
            User's common themes: {list(overview.get('common_themes', {}).keys())}
            User's primary domains: {list(overview.get('primary_domains', {}).keys())}
            
            Return connections in this JSON structure:
            {{
                "direct_connections": ["connection1", "connection2"],
                "thematic_links": ["link1", "link2"],
                "potential_insights": ["insight1", "insight2"]
            }}
            
            Only include meaningful connections, not superficial word matches.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Cheaper model for connection finding
                messages=[
                    {"role": "system", "content": "You are an expert at finding meaningful semantic connections between ideas and themes."},
                    {"role": "user", "content": connection_prompt}
                ],
                max_tokens=400,
                temperature=0.4
            )
            
            connections_text = response.choices[0].message.content.strip()
            connections = json.loads(connections_text)
            
            return connections
            
        except Exception as e:
            logger.warning(f"Error finding semantic connections: {e}")
            return []
    
    # =============================================================================
    # HELPER METHODS (Rules-based)
    # =============================================================================
    
    def _classify_content_domains(self, content: str) -> Dict[str, float]:
        """Classify content into domains using rules-based approach"""
        content_lower = content.lower()
        domain_scores = {}
        
        for domain, keywords in self.domain_patterns.items():
            matches = sum(1 for keyword in keywords if keyword in content_lower)
            if matches > 0:
                # Normalize score based on content length and keyword density
                score = min(matches / len(keywords), 1.0)
                domain_scores[domain] = score
        
        return domain_scores
    
    def _extract_themes_rules_based(self, content: str) -> List[str]:
        """Extract key themes using rules-based approach"""
        # Common theme patterns
        theme_patterns = {
            'change': ['change', 'transform', 'shift', 'evolve', 'transition'],
            'challenge': ['difficult', 'hard', 'struggle', 'challenge', 'obstacle'],
            'discovery': ['discover', 'realize', 'understand', 'learn', 'insight'],
            'relationship': ['connect', 'bond', 'relate', 'together', 'apart'],
            'growth': ['grow', 'develop', 'improve', 'progress', 'advance'],
            'reflection': ['think', 'consider', 'reflect', 'ponder', 'contemplate'],
            'emotion': ['feel', 'emotion', 'heart', 'soul', 'spirit'],
            'time': ['past', 'future', 'present', 'now', 'then', 'when'],
            'memory': ['remember', 'forget', 'memory', 'recall', 'remind'],
            'decision': ['decide', 'choose', 'option', 'choice', 'pick']
        }
        
        found_themes = []
        content_lower = content.lower()
        
        for theme, keywords in theme_patterns.items():
            if any(keyword in content_lower for keyword in keywords):
                found_themes.append(theme)
        
        return found_themes
    
    def _detect_emotional_markers(self, content: str) -> List[str]:
        """Detect emotional markers in content"""
        emotional_indicators = {
            'positive': ['happy', 'joy', 'excited', 'love', 'amazing', 'wonderful'],
            'negative': ['sad', 'angry', 'frustrated', 'hurt', 'pain', 'difficult'],
            'contemplative': ['think', 'wonder', 'consider', 'reflect', 'ponder'],
            'uncertain': ['maybe', 'perhaps', 'not sure', 'confused', 'unclear'],
            'confident': ['certain', 'sure', 'confident', 'believe', 'know'],
            'vulnerable': ['vulnerable', 'exposed', 'open', 'honest', 'raw']
        }
        
        found_emotions = []
        content_lower = content.lower()
        
        for emotion, indicators in emotional_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                found_emotions.append(emotion)
        
        return found_emotions
    
    def _calculate_insight_confidence(self, domains: Dict, themes: List, emotions: List) -> float:
        """Calculate confidence in the insight analysis"""
        confidence_factors = {
            'domain_diversity': min(len(domains) / 3, 1.0),  # Max at 3 domains
            'theme_richness': min(len(themes) / 5, 1.0),    # Max at 5 themes
            'emotional_depth': min(len(emotions) / 3, 1.0),  # Max at 3 emotions
            'domain_strength': sum(domains.values()) / max(len(domains), 1)
        }
        
        return sum(confidence_factors.values()) / len(confidence_factors)
    
    def _get_default_knowledge_overview(self) -> Dict[str, Any]:
        """Get default knowledge overview structure"""
        return {
            'total_conversations_analyzed': 0,
            'primary_domains': {},
            'common_themes': {},
            'emotional_patterns': {},
            'knowledge_depth': 0.0,
            'last_updated': datetime.now().isoformat()
        } 