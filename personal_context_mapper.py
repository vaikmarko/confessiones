"""
Personal Context Mapper Engine
=============================

Tracks user patterns, preferences, and context intelligently using a hybrid approach:
- Rules-based for basic tracking and categorization
- AI-powered for deep insights and behavioral analysis

Cost-conscious: Uses AI strategically for insights, not every operation.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import openai
import os
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class PersonalContextMapper:
    """
    Hybrid AI/rules engine for understanding user context and patterns.
    Balances intelligence with cost-effectiveness.
    """
    
    def __init__(self, db=None):
        self.db = db
        
        # Initialize OpenAI for insights (not for basic operations)
        self.openai_client = None
        try:
            if os.getenv('OPENAI_API_KEY'):
                openai.api_key = os.getenv('OPENAI_API_KEY')
                self.openai_client = openai
                logger.info("PersonalContextMapper: OpenAI initialized for deep insights")
            else:
                logger.warning("PersonalContextMapper: No OpenAI - using rules-only approach")
        except Exception as e:
            logger.warning(f"PersonalContextMapper: OpenAI initialization failed: {e}")
    
    # =============================================================================
    # RULES-BASED CONTEXT TRACKING (Fast, cost-effective)
    # =============================================================================
    
    def track_basic_interaction(self, user_id: str, message: str, message_type: str = "user"):
        """Track basic user interactions using rules-based approach"""
        if not self.db:
            return
        
        try:
            # Basic pattern tracking
            interaction_data = {
                'user_id': user_id,
                'message': message,
                'message_type': message_type,
                'timestamp': datetime.now().isoformat(),
                'message_length': len(message),
                'word_count': len(message.split()),
                'contains_emotion_words': self._detect_emotion_words(message),
                'contains_time_references': self._detect_time_references(message),
                'contains_relationship_words': self._detect_relationship_words(message),
                'question_count': message.count('?'),
                'exclamation_count': message.count('!')
            }
            
            # Store in user context collection
            self.db.collection('user_contexts').document(user_id).collection('interactions').add(interaction_data)
            
            # Update user profile summary
            self._update_user_profile_summary(user_id, interaction_data)
            
        except Exception as e:
            logger.error(f"Error tracking interaction for user {user_id}: {e}")
    
    def get_user_context_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user context profile using cached data and rules"""
        if not self.db:
            return self._get_default_context_profile()
        
        try:
            # Get cached profile
            profile_doc = self.db.collection('user_profiles').document(user_id).get()
            
            if profile_doc.exists:
                profile = profile_doc.to_dict()
                
                # Add real-time completeness calculation
                profile['completeness'] = self._calculate_profile_completeness(profile)
                profile['last_updated'] = profile.get('last_updated', datetime.now().isoformat())
                
                return profile
            else:
                # Create new profile
                return self._create_new_user_profile(user_id)
                
        except Exception as e:
            logger.error(f"Error getting user context for {user_id}: {e}")
            return self._get_default_context_profile()
    
    def generate_context_gathering_questions(self, user_id: str, current_topic: str = "") -> List[str]:
        """Generate contextually relevant questions using templates + AI refinement"""
        
        # Get user profile for context
        profile = self.get_user_context_profile(user_id)
        completeness = profile.get('completeness', 0)
        
        # Rules-based question templates
        base_questions = []
        
        if completeness < 0.3:
            # New user - basic exploration
            base_questions.extend([
                "What's been on your mind lately?",
                "Is there something you've been wanting to talk about?",
                "What kind of experiences tend to stick with you?"
            ])
        elif completeness < 0.6:
            # Some context - deeper exploration
            base_questions.extend([
                "That sounds meaningful. What was going through your mind during that?",
                "How did that experience change how you see things?",
                "What patterns do you notice in situations like this?"
            ])
        else:
            # Rich context - nuanced follow-ups
            base_questions.extend([
                "Given what you've shared before, how does this connect to your other experiences?",
                "What would your past self think about this situation?",
                "What insight does this give you about yourself?"
            ])
        
        # AI-enhanced personalization (cost-conscious)
        if self.openai_client and current_topic:
            try:
                enhanced_questions = self._enhance_questions_with_ai(base_questions, profile, current_topic)
                return enhanced_questions[:3]  # Limit to 3 questions
            except Exception as e:
                logger.warning(f"AI question enhancement failed: {e}")
        
        return base_questions[:2]  # Return top 2 template questions
    
    # =============================================================================
    # AI-POWERED DEEP INSIGHTS (Strategic usage)
    # =============================================================================
    
    def generate_deep_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Generate deep insights using AI - called periodically, not real-time"""
        if not self.openai_client or not self.db:
            return {'insights': [], 'patterns': [], 'recommendations': []}
        
        try:
            # Get recent interactions for analysis
            interactions = self._get_recent_interactions(user_id, limit=20)
            
            if len(interactions) < 5:
                return {'insights': [], 'patterns': [], 'note': 'Need more interactions for deep insights'}
            
            # Prepare conversation text for AI analysis
            conversation_text = "\n".join([
                f"{msg.get('message_type', 'user')}: {msg.get('message', '')}"
                for msg in interactions[-10:]  # Last 10 interactions
            ])
            
            # AI prompt for deep insight generation
            insights_prompt = f"""
            Analyze this user's conversation patterns and provide insights in JSON format:
            
            Conversation history:
            {conversation_text}
            
            Provide analysis in this exact JSON structure:
            {{
                "personality_insights": ["insight1", "insight2", "insight3"],
                "communication_patterns": ["pattern1", "pattern2"],
                "emotional_tendencies": ["tendency1", "tendency2"],
                "growth_areas": ["area1", "area2"],
                "conversation_preferences": ["preference1", "preference2"],
                "recommended_approaches": ["approach1", "approach2"]
            }}
            
            Focus on genuine patterns that help create better conversations.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at understanding communication patterns and personality insights from conversations."},
                    {"role": "user", "content": insights_prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            # Parse AI response
            insights_text = response.choices[0].message.content.strip()
            
            try:
                insights = json.loads(insights_text)
                
                # Cache insights in user profile
                self._update_user_insights_cache(user_id, insights)
                
                return insights
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse AI insights as JSON for user {user_id}")
                return {'insights': [], 'patterns': [], 'note': 'AI response parsing failed'}
                
        except Exception as e:
            logger.error(f"Error generating deep insights for user {user_id}: {e}")
            return {'insights': [], 'patterns': [], 'recommendations': []}

    def track_imported_conversation(self, user_id: str, conversation_text: str, source: str, domain_insights: Dict):
        """Track imported conversations for context building"""
        if not self.db:
            return
        
        try:
            # Analyze the imported conversation for patterns
            import_analysis = {
                'user_id': user_id,
                'source': source,
                'conversation_length': len(conversation_text),
                'word_count': len(conversation_text.split()),
                'themes': domain_insights.get('themes', []),
                'domains': list(domain_insights.get('domains', {}).keys()),
                'emotional_markers': domain_insights.get('emotional_markers', []),
                'confidence_score': domain_insights.get('confidence', 0.5),
                'imported_at': datetime.now().isoformat(),
                'contains_emotion_words': self._detect_emotion_words(conversation_text),
                'contains_relationship_words': self._detect_relationship_words(conversation_text),
                'question_density': conversation_text.count('?') / max(len(conversation_text.split()), 1)
            }
            
            # Store in imported conversations collection
            self.db.collection('user_contexts').document(user_id).collection('imported_conversations').add(import_analysis)
            
            # Update user profile with import data
            profile_ref = self.db.collection('user_profiles').document(user_id)
            profile_doc = profile_ref.get()
            
            if profile_doc.exists:
                profile = profile_doc.to_dict()
                
                # Update import statistics
                profile['imports_count'] = profile.get('imports_count', 0) + 1
                profile['total_imported_words'] = profile.get('total_imported_words', 0) + import_analysis['word_count']
                
                # Update theme tracking
                all_themes = profile.get('primary_themes', [])
                all_themes.extend(import_analysis['themes'])
                theme_counts = Counter(all_themes)
                profile['primary_themes'] = [theme for theme, count in theme_counts.most_common(10)]
                
                # Update domain engagement
                domain_engagement = profile.get('domain_engagement', {})
                for domain in import_analysis['domains']:
                    domain_engagement[domain] = domain_engagement.get(domain, 0) + 1
                profile['domain_engagement'] = domain_engagement
                
                # Update emotional expression tracking
                emotion_expressions = profile.get('emotion_expressions', 0)
                profile['emotion_expressions'] = emotion_expressions + len(import_analysis['contains_emotion_words'])
                
                # Update relationship mentions
                relationship_mentions = profile.get('relationship_mentions', 0)
                profile['relationship_mentions'] = relationship_mentions + len(import_analysis['contains_relationship_words'])
                
                profile['last_updated'] = datetime.now().isoformat()
                profile['last_import'] = datetime.now().isoformat()
                
                # Recalculate completeness
                profile['completeness'] = self._calculate_profile_completeness(profile)
                
                profile_ref.update(profile)
                
            else:
                # Create new profile with import data
                new_profile = self._create_new_user_profile(user_id)
                new_profile.update({
                    'imports_count': 1,
                    'total_imported_words': import_analysis['word_count'],
                    'primary_themes': import_analysis['themes'],
                    'domain_engagement': {domain: 1 for domain in import_analysis['domains']},
                    'emotion_expressions': len(import_analysis['contains_emotion_words']),
                    'relationship_mentions': len(import_analysis['contains_relationship_words']),
                    'last_import': datetime.now().isoformat()
                })
                new_profile['completeness'] = self._calculate_profile_completeness(new_profile)
                profile_ref.set(new_profile)
            
            logger.info(f"Tracked imported conversation for user {user_id}: {len(import_analysis['themes'])} themes, {import_analysis['source']} source")
            
        except Exception as e:
            logger.error(f"Error tracking imported conversation for user {user_id}: {e}")

    def _update_user_insights_cache(self, user_id: str, insights: Dict):
        """Cache AI-generated insights in user profile"""
        if not self.db:
            return
        
        try:
            profile_ref = self.db.collection('user_profiles').document(user_id)
            profile_ref.update({
                'ai_insights': insights,
                'insights_generated_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error caching insights for user {user_id}: {e}")
    
    # =============================================================================
    # HELPER METHODS (Rules-based)
    # =============================================================================
    
    def _detect_emotion_words(self, message: str) -> List[str]:
        """Detect emotion words using rules-based approach"""
        emotion_words = {
            'positive': ['happy', 'joy', 'excited', 'love', 'amazing', 'wonderful', 'great', 'fantastic'],
            'negative': ['sad', 'angry', 'frustrated', 'disappointed', 'hurt', 'pain', 'difficult', 'struggle'],
            'neutral': ['think', 'feel', 'believe', 'wonder', 'consider', 'reflect']
        }
        
        found_emotions = []
        message_lower = message.lower()
        
        for category, words in emotion_words.items():
            for word in words:
                if word in message_lower:
                    found_emotions.append(f"{category}:{word}")
        
        return found_emotions
    
    def _detect_time_references(self, message: str) -> List[str]:
        """Detect temporal references"""
        time_patterns = [
            'yesterday', 'today', 'tomorrow', 'last week', 'next week',
            'recently', 'lately', 'soon', 'earlier', 'later',
            'when i was', 'years ago', 'months ago', 'back then'
        ]
        
        found_times = []
        message_lower = message.lower()
        
        for pattern in time_patterns:
            if pattern in message_lower:
                found_times.append(pattern)
        
        return found_times
    
    def _detect_relationship_words(self, message: str) -> List[str]:
        """Detect relationship-related words"""
        relationship_words = [
            'family', 'friend', 'partner', 'spouse', 'mother', 'father',
            'brother', 'sister', 'colleague', 'boss', 'team', 'relationship'
        ]
        
        found_relationships = []
        message_lower = message.lower()
        
        for word in relationship_words:
            if word in message_lower:
                found_relationships.append(word)
        
        return found_relationships
    
    def _update_user_profile_summary(self, user_id: str, interaction_data: Dict):
        """Update user profile summary with new interaction data"""
        try:
            profile_ref = self.db.collection('user_profiles').document(user_id)
            profile_doc = profile_ref.get()
            
            if profile_doc.exists:
                profile = profile_doc.to_dict()
            else:
                profile = self._get_default_context_profile()
                profile['user_id'] = user_id
                profile['created_at'] = datetime.now().isoformat()
            
            # Update interaction counts
            profile['total_interactions'] = profile.get('total_interactions', 0) + 1
            profile['total_words'] = profile.get('total_words', 0) + interaction_data.get('word_count', 0)
            profile['last_interaction'] = datetime.now().isoformat()
            
            # Update patterns
            if interaction_data.get('contains_emotion_words'):
                profile['emotion_expressions'] = profile.get('emotion_expressions', 0) + 1
            
            if interaction_data.get('contains_time_references'):
                profile['temporal_references'] = profile.get('temporal_references', 0) + 1
            
            if interaction_data.get('contains_relationship_words'):
                profile['relationship_mentions'] = profile.get('relationship_mentions', 0) + 1
            
            # Calculate engagement level
            avg_message_length = profile['total_words'] / profile['total_interactions']
            if avg_message_length > 20:
                profile['engagement_level'] = 'high'
            elif avg_message_length > 10:
                profile['engagement_level'] = 'medium'
            else:
                profile['engagement_level'] = 'low'
            
            # Save updated profile
            profile_ref.set(profile)
            
        except Exception as e:
            logger.error(f"Error updating user profile summary: {e}")
    
    def _calculate_profile_completeness(self, profile: Dict) -> float:
        """Calculate how complete the user profile is"""
        completeness_factors = {
            'total_interactions': min(profile.get('total_interactions', 0) / 10, 1.0),  # Max at 10 interactions
            'emotion_expressions': min(profile.get('emotion_expressions', 0) / 5, 1.0),  # Max at 5
            'temporal_references': min(profile.get('temporal_references', 0) / 3, 1.0),  # Max at 3
            'relationship_mentions': min(profile.get('relationship_mentions', 0) / 3, 1.0),  # Max at 3
            'engagement_level': 1.0 if profile.get('engagement_level') == 'high' else 0.5 if profile.get('engagement_level') == 'medium' else 0.2
        }
        
        return sum(completeness_factors.values()) / len(completeness_factors)
    
    def _create_new_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Create a new user profile"""
        profile = self._get_default_context_profile()
        profile['user_id'] = user_id
        profile['created_at'] = datetime.now().isoformat()
        
        if self.db:
            self.db.collection('user_profiles').document(user_id).set(profile)
        
        return profile
    
    def _get_default_context_profile(self) -> Dict[str, Any]:
        """Get default context profile structure"""
        return {
            'total_interactions': 0,
            'total_words': 0,
            'emotion_expressions': 0,
            'temporal_references': 0,
            'relationship_mentions': 0,
            'engagement_level': 'new',
            'completeness': 0.0,
            'conversation_topics': [],
            'preferred_question_types': [],
            'ai_insights': {},
            'last_interaction': None,
            'insights_generated_at': None
        }
    
    def _get_recent_interactions(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get recent user interactions"""
        if not self.db:
            return []
        
        try:
            interactions = []
            interactions_ref = (self.db.collection('user_contexts')
                              .document(user_id)
                              .collection('interactions')
                              .order_by('timestamp', direction=firestore.Query.DESCENDING)
                              .limit(limit))
            
            for doc in interactions_ref.stream():
                interactions.append(doc.to_dict())
            
            return list(reversed(interactions))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Error getting recent interactions: {e}")
            return []
    
    def _enhance_questions_with_ai(self, base_questions: List[str], profile: Dict, current_topic: str) -> List[str]:
        """Enhance base questions with AI personalization"""
        
        # Only use AI if we have sufficient context and it's worth the cost
        if profile.get('completeness', 0) < 0.3:
            return base_questions  # Not enough context for AI enhancement
        
        try:
            enhancement_prompt = f"""
            Enhance these conversation questions to be more contextually relevant:
            
            Base questions: {base_questions}
            Current topic: {current_topic}
            User context: Engagement level: {profile.get('engagement_level', 'unknown')}, 
            Previous topics: {profile.get('conversation_topics', [])}
            
            Return 3 enhanced questions that:
            1. Feel natural and empathetic
            2. Build on the current topic
            3. Encourage deeper reflection
            
            Format as JSON array: ["question1", "question2", "question3"]
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Use cheaper model for question enhancement
                messages=[
                    {"role": "system", "content": "You are an expert at creating thoughtful, engaging conversation questions."},
                    {"role": "user", "content": enhancement_prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            enhanced_text = response.choices[0].message.content.strip()
            enhanced_questions = json.loads(enhanced_text)
            
            return enhanced_questions if isinstance(enhanced_questions, list) else base_questions
            
        except Exception as e:
            logger.warning(f"Question enhancement failed: {e}")
            return base_questions 