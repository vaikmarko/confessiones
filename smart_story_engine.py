"""
Smart Story Generation Engine

This engine integrates with existing intelligent engines to determine when conversations
have story potential and should be transformed into meaningful stories. It analyzes
conversation flow, emotional depth, narrative structure, and personal context to make
intelligent decisions about story generation.

Integrates with:
- KnowledgeEngine: For domain insights and user patterns
- PersonalContextMapper: For personal context and user profiling
- ConversationPlanner: For guided conversation strategies
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import re
import openai
import os

logger = logging.getLogger(__name__)

class SmartStoryEngine:
    """
    Intelligent story generation engine that understands conversation context
    and determines when chats should become stories vs continue as conversations.
    Now powered by OpenAI for smart analysis instead of rule-based patterns.
    """
    
    def __init__(self, knowledge_engine=None, personal_context_mapper=None, conversation_planner=None):
        self.knowledge_engine = knowledge_engine
        self.personal_context_mapper = personal_context_mapper
        self.conversation_planner = conversation_planner
        
        # Initialize OpenAI client
        self.openai_client = None
        try:
            if os.getenv('OPENAI_API_KEY'):
                openai.api_key = os.getenv('OPENAI_API_KEY')
                self.openai_client = openai
                logger.info("SmartStoryEngine: OpenAI client initialized successfully")
            else:
                logger.warning("SmartStoryEngine: OPENAI_API_KEY not found - using fallback analysis")
        except Exception as e:
            logger.warning(f"SmartStoryEngine: Failed to initialize OpenAI client: {e}")
            self.openai_client = None
        
        # Fallback rule-based indicators (for when OpenAI is unavailable)
        self.story_indicators = {
            'narrative_elements': [
                'when i', 'i remember', 'there was a time', 'i once', 'last week', 'yesterday',
                'a few months ago', 'back then', 'it happened', 'i was', 'we were',
                'the moment', 'suddenly', 'then', 'after that', 'meanwhile', 'later'
            ],
            'emotional_depth': [
                'felt', 'feeling', 'emotion', 'heart', 'soul', 'deeply', 'overwhelmed',
                'realized', 'understood', 'learned', 'changed', 'transformed', 'impact',
                'meaningful', 'significant', 'important', 'life-changing', 'profound'
            ],
            'conflict_resolution': [
                'struggle', 'challenge', 'difficult', 'problem', 'overcome', 'solved',
                'breakthrough', 'turning point', 'decision', 'choice', 'dilemma',
                'conflict', 'tension', 'resolution', 'growth', 'lesson'
            ],
            'personal_revelation': [
                'realized', 'discovered', 'understood', 'learned about myself',
                'insight', 'awareness', 'clarity', 'perspective', 'truth',
                'pattern', 'behavior', 'tendency', 'habit', 'characteristic'
            ]
        }
        
        # Conversation continuation indicators
        self.conversation_indicators = {
            'questions': [
                'what do you think', 'how should i', 'what would you do',
                'can you help', 'i need advice', 'what if', 'should i',
                'do you understand', 'does that make sense'
            ],
            'exploration': [
                'i wonder', 'maybe', 'perhaps', 'could be', 'might be',
                'not sure', 'confused', 'unclear', 'thinking about',
                'considering', 'exploring', 'trying to understand'
            ],
            'ongoing_process': [
                'currently', 'right now', 'these days', 'lately', 'recently',
                'still', 'continuing', 'working on', 'dealing with',
                'in the process', 'ongoing', 'developing'
            ]
        }
    
    def analyze_conversation_for_story_potential(self, conversation: List[Dict], user_id: str) -> Dict[str, Any]:
        """
        Analyze a conversation to determine if it has story potential or should continue as chat.
        Now uses OpenAI for intelligent analysis when available.
        """
        
        if not conversation or len(conversation) < 2:
            return self._create_analysis_result(False, 0.0, 'continue_conversation', 
                                              'Not enough conversation content yet')
        
        # Get user messages only (filter out system and assistant messages)
        user_messages = [msg['content'] for msg in conversation if msg.get('role') == 'user']
        
        if len(user_messages) < 1:
            return self._create_analysis_result(False, 0.0, 'continue_conversation',
                                              'No user messages to analyze')
        
        # Use OpenAI for intelligent analysis if available
        if self.openai_client:
            return self._analyze_with_openai(conversation, user_messages, user_id)
        else:
            # Fallback to rule-based analysis
            return self._analyze_with_rules(conversation, user_messages, user_id)
    
    def _analyze_with_openai(self, conversation: List[Dict], user_messages: List[str], user_id: str) -> Dict[str, Any]:
        """Use OpenAI to intelligently analyze conversation for story potential."""
        
        try:
            # Prepare conversation context for analysis
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in conversation[-10:]  # Last 10 messages for context
            ])
            
            # Create smart analysis prompt
            system_prompt = """You are an expert conversation analyst who determines whether conversations contain meaningful personal stories or should continue as supportive dialogue.

Analyze the conversation and return a JSON response with this exact structure:
{
    "story_readiness_score": 0.85,
    "recommendation": "generate_story",
    "reasoning": "Clear narrative with emotional depth and personal insight",
    "story_elements": {
        "has_narrative_structure": true,
        "emotional_depth": "high",
        "personal_revelation": true,
        "conflict_resolution": true
    },
    "conversation_type": "story_sharing",
    "guidance_needed": false
}

Story readiness score (0.0-1.0):
- 0.0-0.35: Continue conversation (seeking advice, exploring thoughts, casual chat)
- 0.35-0.65: Guide to story (has potential but needs development)
- 0.65-1.0: Generate story (complete narrative with emotional depth)

Recommendation types:
- "continue_conversation": For advice-seeking, casual chat, ongoing exploration
- "guide_to_story": For conversations with story potential that need development
- "generate_story": For complete stories with narrative structure and emotional depth

Consider:
- Narrative elements (time, place, events, characters)
- Emotional depth and vulnerability
- Personal insights and growth
- Conflict and resolution
- Completeness of the story arc"""

            # Call OpenAI for analysis
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this conversation:\n\n{conversation_text}"}
                ],
                max_tokens=800,
                temperature=0.3  # Lower temperature for more consistent analysis
            )
            
            # Parse OpenAI response
            analysis_text = response.choices[0].message.content.strip()
            
            try:
                import json
                analysis = json.loads(analysis_text)
                
                # Validate required fields
                required_fields = ['story_readiness_score', 'recommendation', 'reasoning']
                if not all(field in analysis for field in required_fields):
                    raise ValueError("Missing required fields in OpenAI response")
                
                # Ensure score is in valid range
                score = max(0.0, min(1.0, float(analysis['story_readiness_score'])))
                
                # Generate conversation guidance if needed
                conversation_guidance = None
                if analysis['recommendation'] in ['continue_conversation', 'guide_to_story']:
                    conversation_guidance = self._generate_openai_guidance(conversation, user_messages, analysis)
                
                return {
                    'has_story_potential': score > 0.3,
                    'story_readiness_score': score,
                    'recommendation': analysis['recommendation'],
                    'reasoning': analysis['reasoning'],
                    'story_elements': analysis.get('story_elements', {}),
                    'conversation_guidance': conversation_guidance,
                    'analysis_details': {
                        'analysis_method': 'openai',
                        'conversation_type': analysis.get('conversation_type', 'unknown'),
                        'guidance_needed': analysis.get('guidance_needed', False)
                    }
                }
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(f"Failed to parse OpenAI analysis response: {e}")
                logger.warning(f"Raw response: {analysis_text}")
                # Fall back to rule-based analysis
                return self._analyze_with_rules(conversation, user_messages, user_id)
                
        except Exception as e:
            logger.error(f"Error in OpenAI analysis: {e}")
            # Fall back to rule-based analysis
            return self._analyze_with_rules(conversation, user_messages, user_id)
    
    def _generate_openai_guidance(self, conversation: List[Dict], user_messages: List[str], analysis: Dict) -> Dict[str, Any]:
        """Generate conversation guidance using OpenAI."""
        
        try:
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in conversation[-5:]  # Last 5 messages
            ])
            
            recommendation = analysis.get('recommendation', 'continue_conversation')
            story_elements = analysis.get('story_elements', {})
            
            guidance_prompt = f"""Based on this conversation analysis, generate helpful guidance for continuing the conversation.

Current recommendation: {recommendation}
Story elements present: {story_elements}

Conversation:
{conversation_text}

Provide specific guidance in JSON format:
{{
    "strategy": "supportive_listening|story_development|exploration_and_discovery",
    "suggested_responses": ["response1", "response2", "response3"],
    "story_development_questions": ["question1", "question2"],
    "next_steps": "what should happen next"
}}

Make responses natural, empathetic, and contextually appropriate."""

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert conversation guide who helps create meaningful dialogue."},
                    {"role": "user", "content": guidance_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            guidance_text = response.choices[0].message.content.strip()
            
            try:
                import json
                return json.loads(guidance_text)
            except json.JSONDecodeError:
                # Return basic guidance if parsing fails
                return {
                    "strategy": "supportive_listening",
                    "suggested_responses": [
                        "I'm here to listen. Can you tell me more about that?",
                        "That sounds really meaningful. How did that make you feel?",
                        "What was going through your mind during that experience?"
                    ],
                    "story_development_questions": [],
                    "next_steps": "Continue exploring the user's experience with empathy"
                }
                
        except Exception as e:
            logger.warning(f"Error generating OpenAI guidance: {e}")
            return {
                "strategy": "supportive_listening",
                "suggested_responses": ["I'm here to listen. What's most important to you right now?"],
                "story_development_questions": [],
                "next_steps": "Provide supportive conversation"
            }
    
    def _analyze_with_rules(self, conversation: List[Dict], user_messages: List[str], user_id: str) -> Dict[str, Any]:
        """Fallback to rule-based analysis when OpenAI is unavailable."""
        
        # Analyze conversation elements
        story_elements = self._analyze_story_elements(user_messages)
        conversation_flow = self._analyze_conversation_flow(conversation)
        emotional_depth = self._analyze_emotional_depth(user_messages)
        narrative_structure = self._analyze_narrative_structure(user_messages)
        
        # Get personal context if available
        personal_context = {}
        if self.personal_context_mapper:
            try:
                personal_context = self.personal_context_mapper.get_user_context_profile(user_id)
            except Exception as e:
                logger.warning(f"Could not get personal context for user {user_id}: {e}")
        
        # Calculate story readiness score
        story_readiness_score = self._calculate_story_readiness_score(
            story_elements, emotional_depth, narrative_structure, conversation_flow, personal_context
        )
        
        # Determine recommendation
        recommendation, reasoning = self._determine_recommendation(
            story_readiness_score, story_elements, conversation_flow, user_messages
        )
        
        # Generate conversation guidance if needed
        conversation_guidance = None
        if recommendation in ['continue_conversation', 'guide_to_story']:
            conversation_guidance = self._generate_conversation_guidance(
                story_elements, conversation_flow, user_messages, user_id
            )
        
        return {
            'has_story_potential': story_readiness_score > 0.3,
            'story_readiness_score': story_readiness_score,
            'recommendation': recommendation,
            'reasoning': reasoning,
            'story_elements': story_elements,
            'conversation_guidance': conversation_guidance,
            'analysis_details': {
                'emotional_depth': emotional_depth,
                'narrative_structure': narrative_structure,
                'conversation_flow': conversation_flow,
                'personal_context_available': bool(personal_context)
            }
        }
    
    def _analyze_story_elements(self, user_messages: List[str]) -> Dict[str, Any]:
        """Analyze messages for story elements like narrative, emotion, conflict, revelation."""
        
        combined_text = ' '.join(user_messages).lower()
        
        elements = {}
        total_indicators = 0
        
        for category, indicators in self.story_indicators.items():
            found_indicators = [ind for ind in indicators if ind in combined_text]
            elements[category] = {
                'found': found_indicators,
                'count': len(found_indicators),
                'strength': min(1.0, len(found_indicators) / 3)  # Normalize to 0-1
            }
            total_indicators += len(found_indicators)
        
        # Calculate overall story element strength
        elements['overall_strength'] = min(1.0, total_indicators / 10)  # Normalize
        elements['total_indicators'] = total_indicators
        
        return elements
    
    def _analyze_conversation_flow(self, conversation: List[Dict]) -> Dict[str, Any]:
        """Analyze the flow and direction of the conversation."""
        
        user_messages = [msg['content'] for msg in conversation if msg.get('role') == 'user']
        assistant_messages = [msg['content'] for msg in conversation if msg.get('role') == 'assistant']
        
        flow_analysis = {
            'message_count': len(conversation),
            'user_message_count': len(user_messages),
            'assistant_message_count': len(assistant_messages),
            'avg_user_message_length': sum(len(msg) for msg in user_messages) / len(user_messages) if user_messages else 0,
            'conversation_depth': len(conversation) / 2,  # Rough measure of back-and-forth
            'is_exploratory': False,
            'is_narrative': False,
            'is_seeking_advice': False
        }
        
        # Analyze conversation type
        combined_user_text = ' '.join(user_messages).lower()
        
        # Check for exploratory conversation
        exploration_count = sum(1 for indicator in self.conversation_indicators['exploration'] 
                              if indicator in combined_user_text)
        flow_analysis['is_exploratory'] = exploration_count > 0
        
        # Check for narrative flow
        narrative_count = sum(1 for indicator in self.story_indicators['narrative_elements'] 
                            if indicator in combined_user_text)
        flow_analysis['is_narrative'] = narrative_count > 2
        
        # Check for advice-seeking
        question_count = sum(1 for indicator in self.conversation_indicators['questions'] 
                           if indicator in combined_user_text)
        flow_analysis['is_seeking_advice'] = question_count > 0
        
        return flow_analysis
    
    def _analyze_emotional_depth(self, user_messages: List[str]) -> Dict[str, Any]:
        """Analyze the emotional depth and vulnerability in messages."""
        
        combined_text = ' '.join(user_messages).lower()
        
        # Count emotional indicators
        emotional_words = self.story_indicators['emotional_depth']
        found_emotions = [word for word in emotional_words if word in combined_text]
        
        # Analyze vulnerability indicators
        vulnerability_indicators = [
            'scared', 'afraid', 'vulnerable', 'open up', 'share', 'personal',
            'private', 'secret', 'never told', 'first time', 'honest',
            'truth', 'real', 'authentic', 'genuine'
        ]
        vulnerability_count = sum(1 for indicator in vulnerability_indicators if indicator in combined_text)
        
        # Calculate emotional depth score
        emotional_depth_score = min(1.0, (len(found_emotions) + vulnerability_count * 2) / 8)
        
        return {
            'emotional_words_found': found_emotions,
            'emotional_word_count': len(found_emotions),
            'vulnerability_indicators': vulnerability_count,
            'depth_score': emotional_depth_score,
            'has_significant_emotion': emotional_depth_score > 0.3
        }
    
    def _analyze_narrative_structure(self, user_messages: List[str]) -> Dict[str, Any]:
        """Analyze if messages follow a narrative structure."""
        
        combined_text = ' '.join(user_messages)
        
        # Look for narrative structure elements
        structure_elements = {
            'setting': ['when', 'where', 'during', 'at the time', 'back then'],
            'characters': ['i', 'we', 'he', 'she', 'they', 'my friend', 'my family'],
            'conflict': ['problem', 'issue', 'challenge', 'difficult', 'struggle'],
            'resolution': ['solved', 'resolved', 'learned', 'realized', 'understood'],
            'reflection': ['now i', 'looking back', 'in hindsight', 'i understand']
        }
        
        found_elements = {}
        total_structure_score = 0
        
        for element, indicators in structure_elements.items():
            found = [ind for ind in indicators if ind.lower() in combined_text.lower()]
            found_elements[element] = {
                'found': found,
                'present': len(found) > 0
            }
            if len(found) > 0:
                total_structure_score += 1
        
        # Check for temporal progression
        temporal_indicators = ['first', 'then', 'next', 'after', 'finally', 'eventually']
        temporal_progression = sum(1 for ind in temporal_indicators if ind in combined_text.lower())
        
        narrative_score = min(1.0, (total_structure_score + temporal_progression) / 8)
        
        return {
            'structure_elements': found_elements,
            'temporal_progression': temporal_progression,
            'narrative_score': narrative_score,
            'has_clear_narrative': narrative_score > 0.4
        }
    
    def _calculate_story_readiness_score(self, story_elements: Dict, emotional_depth: Dict, 
                                       narrative_structure: Dict, conversation_flow: Dict,
                                       personal_context: Dict) -> float:
        """Calculate overall story readiness score (0-1)."""
        
        # Base scores from analysis - adjusted weights for better sensitivity
        story_element_score = story_elements.get('overall_strength', 0) * 0.35  # Increased weight
        emotional_score = emotional_depth.get('depth_score', 0) * 0.30  # Increased weight
        narrative_score = narrative_structure.get('narrative_score', 0) * 0.20  # Slightly reduced
        
        # Conversation flow adjustments - more generous scoring
        flow_score = 0
        if conversation_flow.get('is_narrative', False):
            flow_score += 0.15  # Increased bonus for narrative flow
        if conversation_flow.get('avg_user_message_length', 0) > 80:  # Lowered threshold
            flow_score += 0.08  # Increased bonus for substantial messages
        if conversation_flow.get('conversation_depth', 0) > 1.5:  # Lowered threshold
            flow_score += 0.05
        
        # Emotional depth bonus - reward vulnerability and insight
        if emotional_depth.get('has_significant_emotion', False):
            flow_score += 0.10
        if emotional_depth.get('vulnerability_indicators', 0) > 0:
            flow_score += 0.08
        
        # Story elements bonus - reward specific story indicators
        total_indicators = story_elements.get('total_indicators', 0)
        if total_indicators >= 5:
            flow_score += 0.10
        elif total_indicators >= 3:
            flow_score += 0.05
        
        # Personal context bonus
        context_bonus = 0
        if personal_context and personal_context.get('completeness', 0) > 0.3:
            context_bonus = 0.08  # Reduced but still meaningful bonus
        
        total_score = story_element_score + emotional_score + narrative_score + flow_score + context_bonus
        
        return min(1.0, total_score)
    
    def _determine_recommendation(self, story_readiness_score: float, story_elements: Dict,
                                conversation_flow: Dict, user_messages: List[str]) -> Tuple[str, str]:
        """Determine what action to recommend based on analysis."""
        
        # Adjusted thresholds for better story detection
        # High story readiness - generate story
        if story_readiness_score > 0.65:  # Lowered from 0.7
            return 'generate_story', f"Strong story elements detected (score: {story_readiness_score:.2f}). The conversation contains clear narrative structure, emotional depth, and meaningful content suitable for a story."
        
        # Medium story readiness - guide toward story
        elif story_readiness_score > 0.35:  # Lowered from 0.4
            missing_elements = []
            if story_elements.get('emotional_depth', {}).get('strength', 0) < 0.3:
                missing_elements.append("emotional depth")
            if story_elements.get('narrative_elements', {}).get('strength', 0) < 0.3:
                missing_elements.append("narrative structure")
            if story_elements.get('personal_revelation', {}).get('strength', 0) < 0.3:
                missing_elements.append("personal insights")
            
            if missing_elements:
                return 'guide_to_story', f"Moderate story potential (score: {story_readiness_score:.2f}). Could develop into a story with more {', '.join(missing_elements)}."
            else:
                return 'guide_to_story', f"Good story potential (score: {story_readiness_score:.2f}). Let's explore this further to develop it into a complete story."
        
        # Low story readiness - continue conversation
        else:
            if conversation_flow.get('is_seeking_advice', False):
                return 'continue_conversation', f"User is seeking advice and guidance (score: {story_readiness_score:.2f}). Continue supportive conversation."
            elif conversation_flow.get('is_exploratory', False):
                return 'continue_conversation', f"User is exploring thoughts and feelings (score: {story_readiness_score:.2f}). Continue exploratory conversation."
            else:
                return 'continue_conversation', f"Limited story elements detected (score: {story_readiness_score:.2f}). Continue building rapport and understanding."
    
    def _generate_conversation_guidance(self, story_elements: Dict, conversation_flow: Dict,
                                      user_messages: List[str], user_id: str) -> Dict[str, Any]:
        """Generate guidance for continuing or directing the conversation."""
        
        guidance = {
            'strategy': 'supportive_listening',
            'suggested_responses': [],
            'story_development_questions': [],
            'context_gathering_questions': []
        }
        
        # Determine conversation strategy
        if conversation_flow.get('is_seeking_advice', False):
            guidance['strategy'] = 'advice_and_support'
            guidance['suggested_responses'] = [
                "That sounds really challenging. What feels most important to you right now?",
                "I can understand why that would be difficult. What options are you considering?",
                "Thank you for sharing that with me. What would feel most helpful to explore?"
            ]
        
        elif story_elements.get('overall_strength', 0) > 0.2:
            guidance['strategy'] = 'story_development'
            guidance['story_development_questions'] = [
                "That sounds like it was a significant moment for you. What was going through your mind when that happened?",
                "How did that experience change you or your perspective?",
                "What did you learn about yourself from that situation?",
                "Can you tell me more about how you felt during that time?"
            ]
        
        else:
            guidance['strategy'] = 'exploration_and_discovery'
            guidance['suggested_responses'] = [
                "I'm here to listen. What's been on your mind lately?",
                "That's interesting. Can you tell me more about that?",
                "How are you feeling about all of this?",
                "What's most important to you in this situation?"
            ]
        
        # Add context gathering questions if personal context mapper is available
        if self.personal_context_mapper:
            try:
                context_questions = self.personal_context_mapper.generate_context_gathering_questions(
                    user_id, current_conversation_topic=' '.join(user_messages[-2:]) if len(user_messages) >= 2 else user_messages[-1] if user_messages else ""
                )
                guidance['context_gathering_questions'] = context_questions
            except Exception as e:
                logger.warning(f"Could not generate context questions: {e}")
        
        return guidance
    
    def _create_analysis_result(self, has_potential: bool, score: float, recommendation: str, reasoning: str) -> Dict[str, Any]:
        """Create a standardized analysis result."""
        return {
            'has_story_potential': has_potential,
            'story_readiness_score': score,
            'recommendation': recommendation,
            'reasoning': reasoning,
            'story_elements': {},
            'conversation_guidance': None,
            'analysis_details': {}
        }
    
    def should_generate_story_now(self, conversation: List[Dict], user_id: str) -> bool:
        """Simple boolean check if a story should be generated right now."""
        analysis = self.analyze_conversation_for_story_potential(conversation, user_id)
        return analysis['recommendation'] == 'generate_story'
    
    def get_conversation_guidance(self, conversation: List[Dict], user_id: str) -> Optional[Dict[str, Any]]:
        """Get guidance for continuing the conversation."""
        analysis = self.analyze_conversation_for_story_potential(conversation, user_id)
        return analysis.get('conversation_guidance')
    
    def generate_story_worthy_response(self, conversation: List[Dict], user_id: str) -> str:
        """Generate a response that helps guide the conversation toward story potential."""
        
        analysis = self.analyze_conversation_for_story_potential(conversation, user_id)
        guidance = analysis.get('conversation_guidance', {})
        
        # Get the latest user message for context
        user_messages = [msg['content'] for msg in conversation if msg.get('role') == 'user']
        if not user_messages:
            return "I'm here to listen. What's on your heart today?"
        
        latest_message = user_messages[-1].lower()
        story_score = analysis.get('story_readiness_score', 0)
        
        # Generate contextual, engaging responses based on content and score
        if story_score > 0.4:  # High potential - encourage deeper sharing
            return self._generate_deep_engagement_response(latest_message, user_messages)
        elif story_score > 0.2:  # Medium potential - guide toward story
            return self._generate_story_guidance_response(latest_message, user_messages)
        else:  # Low potential - build rapport and explore
            return self._generate_rapport_building_response(latest_message, user_messages)
    
    def _generate_deep_engagement_response(self, latest_message: str, all_messages: List[str]) -> str:
        """Generate deeply engaging responses for high story potential conversations."""
        
        # Analyze emotional content and themes
        if any(word in latest_message for word in ['grandmother', 'grandma', 'grandpa']):
            return "There's something so profound about the wisdom our grandparents carry. It sounds like this moment with her really opened your eyes to something important. What did you discover about yourself in that experience?"
        
        elif any(word in latest_message for word in ['dad', 'father']) and any(word in latest_message for word in ['job', 'work', 'lost']):
            return "Watching a parent struggle can be such a defining moment - it changes how we see the world and ourselves. That decision you made at 16 sounds like it shaped your entire path. How do you think it's influenced the person you've become?"
        
        elif any(word in latest_message for word in ['presentation', 'ceo', 'developer']):
            return "Those sink-or-swim moments often reveal strengths we didn't know we had! It's fascinating how imposter syndrome can hold us back from recognizing our own capabilities. What was it like realizing you actually knew more than you thought?"
        
        elif any(word in latest_message for word in ['realized', 'learned', 'understood']):
            return "Those moments of realization can be so powerful - like puzzle pieces suddenly clicking into place. It sounds like this experience taught you something fundamental about yourself. How has that insight changed how you approach life now?"
        
        elif any(word in latest_message for word in ['scared', 'afraid', 'nervous', 'terrified']):
            return "It takes real courage to push through that kind of fear. There's something beautiful about how our biggest challenges often become our greatest growth moments. What do you think gave you the strength to keep going despite being so scared?"
        
        else:
            return "What you're sharing has such depth to it. I can sense there's a really meaningful story here. What was the moment that changed everything for you in this situation?"
    
    def _generate_story_guidance_response(self, latest_message: str, all_messages: List[str]) -> str:
        """Generate responses that gently guide toward story development."""
        
        if any(word in latest_message for word in ['sister', 'brother', 'sibling']):
            return "Family relationships can be so complex, can't they? The way they evolve over time often tells such interesting stories. What's been the turning point in reconnecting with your sister?"
        
        elif any(word in latest_message for word in ['decision', 'choice', 'struggling']):
            return "Big life decisions can feel so overwhelming, especially when they involve leaving behind what's familiar. There's usually a deeper story behind what's really driving these choices. What's your gut telling you about this opportunity?"
        
        elif any(word in latest_message for word in ['relationship', 'dating', 'partner']):
            return "Relationships have such a way of teaching us about ourselves, don't they? Every connection seems to reveal something new. What have you been discovering about yourself through this experience?"
        
        elif any(word in latest_message for word in ['work', 'job', 'career']):
            return "Our work lives can be such a reflection of our values and dreams. It sounds like there's more to this story than just the surface details. What's really driving this situation for you?"
        
        elif any(word in latest_message for word in ['thinking', 'reflecting', 'wondering']):
            return "I love that you're taking time to really reflect on this. Sometimes the most interesting insights come when we sit with our thoughts like this. What's been coming up for you as you've been thinking about it?"
        
        else:
            return "There seems to be something deeper here that's worth exploring. What's the part of this story that feels most significant to you?"
    
    def _generate_rapport_building_response(self, latest_message: str, all_messages: List[str]) -> str:
        """Generate warm, engaging responses that build connection and explore interests."""
        
        # Handle simple greetings and check-ins
        if any(word in latest_message for word in ['how are you', 'doing today', 'how\'s it going']):
            return "I'm doing well, thank you for asking! I'm curious about you though - what's been the highlight of your day so far?"
        
        elif any(word in latest_message for word in ['weather', 'weekend', 'plans']):
            return "Nice! I hope you get some good weather for whatever you have planned. Are you someone who likes to have your weekends all mapped out, or do you prefer to see where the day takes you?"
        
        elif any(word in latest_message for word in ['tired', 'busy', 'stressed']):
            return "It sounds like you've got a lot on your plate right now. What's been keeping you busiest lately? And more importantly - are you finding any time for the things that actually energize you?"
        
        elif any(word in latest_message for word in ['work', 'job']) and len(latest_message) < 50:
            return "Work can be such a big part of our lives, can't it? What's your work situation like - are you in something that feels meaningful to you, or more of a stepping stone to something else?"
        
        elif any(word in latest_message for word in ['good', 'great', 'fine', 'okay']):
            return "That's good to hear! Sometimes 'good' can mean so many different things though. What's been making it feel good for you lately?"
        
        elif any(word in latest_message for word in ['nothing much', 'not much', 'same old']):
            return "Sometimes those 'nothing much' days can actually be pretty nice - there's something to be said for a steady rhythm. But I'm curious - if you could add one thing to make your days more interesting, what would it be?"
        
        else:
            # Contextual follow-ups based on conversation flow
            if len(all_messages) == 1:
                return "Thanks for sharing that with me. I'm genuinely curious to know more about you. What's been on your mind lately - anything you've been thinking about or working through?"
            else:
                return "That's interesting. I feel like there might be more to explore here. What's the part of this that feels most important to you right now?"
    
    def integrate_with_knowledge_engine(self, conversation: List[Dict], user_id: str) -> Dict[str, Any]:
        """Integrate story analysis with knowledge engine insights."""
        
        if not self.knowledge_engine:
            return {}
        
        # Get the latest user message
        user_messages = [msg['content'] for msg in conversation if msg.get('role') == 'user']
        if not user_messages:
            return {}
        
        latest_message = user_messages[-1]
        
        try:
            # Analyze for domain insights
            domain_insights = self.knowledge_engine.analyze_story_for_insights(latest_message, user_id)
            
            # Get story analysis
            story_analysis = self.analyze_conversation_for_story_potential(conversation, user_id)
            
            # Combine insights
            integrated_analysis = {
                'story_analysis': story_analysis,
                'domain_insights': domain_insights,
                'recommendation': self._integrate_recommendations(story_analysis, domain_insights),
                'enhanced_guidance': self._enhance_guidance_with_insights(
                    story_analysis.get('conversation_guidance', {}), domain_insights
                )
            }
            
            return integrated_analysis
            
        except Exception as e:
            logger.error(f"Error integrating with knowledge engine: {e}")
            return {'error': str(e)}
    
    def _integrate_recommendations(self, story_analysis: Dict, domain_insights: Dict) -> str:
        """Integrate story and knowledge recommendations."""
        
        story_rec = story_analysis.get('recommendation', 'continue_conversation')
        
        # If we have strong domain insights, it might indicate story potential
        if domain_insights and len(domain_insights) >= 2:
            if story_rec == 'continue_conversation':
                return 'guide_to_story'  # Upgrade recommendation
        
        return story_rec
    
    def _enhance_guidance_with_insights(self, guidance: Dict, domain_insights: Dict) -> Dict:
        """Enhance conversation guidance with domain insights."""
        
        if not guidance or not domain_insights:
            return guidance
        
        enhanced_guidance = guidance.copy()
        
        # Add insight-specific questions
        insight_questions = []
        
        if 'relationships' in domain_insights:
            insight_questions.append("How do your relationships typically influence situations like this?")
        
        if 'emotions' in domain_insights:
            insight_questions.append("What emotions come up for you when you think about this?")
        
        if 'life_patterns' in domain_insights:
            insight_questions.append("Do you notice any patterns in how you handle similar situations?")
        
        if insight_questions:
            enhanced_guidance['insight_based_questions'] = insight_questions
        
        return enhanced_guidance 