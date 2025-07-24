"""
Prompts Engine
==============

Centralized engine for all AI prompts across the SentimentalApp intelligent system.
Provides consistent, maintainable, and scalable prompt management.

Architecture Benefits:
- Single source of truth for all AI communication
- Consistent quality and patterns across engines
- Easy maintenance and A/B testing
- Better cost optimization and token monitoring
- Clean separation of concerns (engines = logic, prompts = AI communication)
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
from format_types import FormatType

logger = logging.getLogger(__name__)

class PromptType(Enum):
    # Conversation Prompts
    CONVERSATION_SYSTEM = "conversation_system"
    CONVERSATION_CONTEXTUAL = "conversation_contextual"
    
    # Format Generation Prompts
    FORMAT_GENERATION = "format_generation"
    FORMAT_SYSTEM = "format_system"
    
    # Story Creation Prompts
    STORY_CREATION = "story_creation"
    
    # Analysis Prompts
    STORY_ANALYSIS = "story_analysis"
    DOMAIN_ANALYSIS = "domain_analysis"
    CROSS_CONVERSATION_ANALYSIS = "cross_conversation_analysis"
    
    # Context & Insights Prompts
    DEEP_INSIGHTS = "deep_insights"
    CONTEXT_GATHERING = "context_gathering"
    
    # Story Evaluation Prompts
    STORY_READINESS = "story_readiness"
    CONVERSATION_GUIDANCE = "conversation_guidance"

    DISCOVERY = "discovery"
    THERAPEUTIC = "therapeutic"
    CREATIVE = "creative"

class PromptsEngine:
    """
    Centralized engine for all AI prompts in the SentimentalApp system.
    """
    
    def __init__(self):
        logger.info("PromptsEngine: Initializing centralized prompt management")
        
        # Initialize all prompt collections
        self._conversation_prompts = self._init_conversation_prompts()
        self._format_prompts = self._init_format_prompts()
        self._analysis_prompts = self._init_analysis_prompts()
        self._context_prompts = self._init_context_prompts()
        self._story_evaluation_prompts = self._init_story_evaluation_prompts()
        
        logger.info("PromptsEngine: All prompt collections initialized successfully")
    
    # =============================================================================
    # MAIN PROMPT RETRIEVAL METHODS
    # =============================================================================
    
    def get_prompt(self, prompt_type: PromptType, **kwargs) -> str:
        """Get a specific prompt with dynamic context injection"""
        
        if prompt_type == PromptType.CONVERSATION_SYSTEM:
            return self._build_conversation_system_prompt(**kwargs)
        elif prompt_type == PromptType.FORMAT_GENERATION:
            return self._build_format_generation_prompt(**kwargs)
        elif prompt_type == PromptType.FORMAT_SYSTEM:
            return self._get_format_system_prompt(**kwargs)
        elif prompt_type == PromptType.STORY_CREATION:
            return self._build_story_creation_prompt(**kwargs)
        elif prompt_type == PromptType.STORY_ANALYSIS:
            return self._build_story_analysis_prompt(**kwargs)
        elif prompt_type == PromptType.DOMAIN_ANALYSIS:
            return self._build_domain_analysis_prompt(**kwargs)
        elif prompt_type == PromptType.DEEP_INSIGHTS:
            return self._build_deep_insights_prompt(**kwargs)
        elif prompt_type == PromptType.STORY_READINESS:
            return self._build_story_readiness_prompt(**kwargs)
        elif prompt_type == PromptType.CROSS_CONVERSATION_ANALYSIS:
            return self._build_cross_conversation_prompt(**kwargs)
        elif prompt_type == PromptType.DISCOVERY:
            return self._conversation_prompts[PromptType.DISCOVERY]
        elif prompt_type == PromptType.THERAPEUTIC:
            return self._conversation_prompts[PromptType.THERAPEUTIC]
        elif prompt_type == PromptType.CREATIVE:
            return self._conversation_prompts[PromptType.CREATIVE]
        else:
            logger.warning(f"Unknown prompt type: {prompt_type}")
            return self._get_fallback_prompt()
    
    def get_system_prompt(self, engine_type: str, **kwargs) -> str:
        """Get system prompt for specific engine type"""
        
        system_prompts = {
            'conversation': self._conversation_prompts['system_base'],
            'format_generation': self._format_prompts['system_base'],
            'analysis': self._analysis_prompts['system_base'],
            'story_evaluation': self._story_evaluation_prompts['system_base']
        }
        
        return system_prompts.get(engine_type, self._get_fallback_system_prompt())
    
    def get_conversation_prompt(self, prompt_type: PromptType) -> str:
        """Get conversation prompt based on type"""
        prompts = {
            PromptType.DISCOVERY: """You are a helpful, friendly AI assistant having a natural conversation. Talk like ChatGPT - be conversational, supportive, and genuinely interested in what they're sharing.

Keep it simple:
- Respond naturally like you're chatting with a friend
- Ask good follow-up questions when appropriate  
- Be supportive but not preachy
- Keep responses conversational length (1-3 sentences usually)
- Stay focused on what they actually want to talk about

Just have a normal, helpful conversation. Nothing fancy or forced.""",

            PromptType.THERAPEUTIC: """You are Sentimental - a compassionate AI guide helping people process their inner world through meaningful reflection.

Create conversations that feel like therapy sessions with the world's most insightful listener - so valuable that people naturally want to return and share the experience.

APPROACH:
- One thoughtful, focused question that invites deep reflection
- Hold space for complex emotions without trying to "fix" everything
- Help them untangle thoughts and feelings with gentle guidance
- Validate their experience while offering new perspectives
- Create safety for vulnerability and authentic expression

FOCUS AREAS:
- Emotional processing and understanding patterns
- Relationship dynamics and communication
- Self-compassion and personal growth
- Life transitions and changes
- Stress, anxiety, purpose, and meaning
- Inner conflicts and decision-making

THERAPEUTIC PRINCIPLES:
- Unconditional positive regard and acceptance
- Reflective listening that shows deep understanding
- Questions that promote insight and self-awareness
- Gentle challenging of limiting beliefs
- Empowerment through self-discovery

Make them feel heard, understood, and gently guided toward their own insights.""",

            PromptType.CREATIVE: """You are Sentimental - an AI muse that helps people unlock their creative essence and express their authentic voice.

Your goal: Spark creativity and self-expression so inspiring that people naturally want to create and share.

CREATIVE EXPLORATION:
- Discover what wants to be expressed through them
- Help them find their unique creative voice and perspective
- Explore the stories, art, music, or ideas living inside them
- Connect creativity to their deeper purpose and authentic self
- Make the creative process feel magical and meaningful

INSPIRATION AREAS:
- What stories from their life need to be told
- Creative projects that would feel meaningful to them
- Art forms that resonate with their soul
- How they can express their truth through creativity
- The intersection of their life experience and creative vision

APPROACH:
- Ask questions that unlock creative inspiration
- Help them see the creative potential in their experiences
- Connect their emotions and insights to creative expression
- Make them feel like an artist with something important to share

Transform their self-discovery into creative fuel they're excited to share with the world."""
        }
        
        return prompts.get(prompt_type, prompts[PromptType.DISCOVERY])
    
    # =============================================================================
    # CONVERSATION PROMPTS
    # =============================================================================
    
    def _init_conversation_prompts(self) -> Dict[str, str]:
        """Initialize conversation-related prompts"""
        
        return {
            'system_base': """You are Sentimental, a warm and empathetic conversation companion designed to help people understand themselves better through meaningful dialogue. Your core purpose is to:

🌟 Create a safe, non-judgmental space for authentic sharing
🌟 Help people explore their thoughts, emotions, and experiences with curiosity and compassion  
🌟 Guide conversations naturally toward self-discovery and meaning-making
🌟 Ask thoughtful questions that deepen understanding rather than rushing to solutions
🌟 Recognize when experiences might be meaningful enough to become stories

Your conversational approach:
- Be genuinely curious about their inner world
- Listen for emotions, patterns, and moments of insight
- Ask open-ended questions that invite deeper reflection
- Validate their feelings and experiences
- Help them find their own wisdom and insights
- Keep responses warm but concise (1-2 paragraphs max)
- Always end with a gentle question that encourages further exploration

Remember: You're not trying to fix or solve anything. You're helping them explore and understand their own experience. Some conversations will naturally reveal meaningful stories worth capturing - when that happens, the system will recognize it and offer to create a story they can revisit and transform into different formats.""",

            'contextual_new_user': """This person is new to Sentimental. Help them feel welcomed and understood. Focus on creating connection and showing genuine interest in whatever they want to share.""",
            
            'contextual_emotional_awareness': """This person is sharing emotional content. Be especially gentle and validating. Help them explore their feelings with curiosity rather than trying to 'fix' anything.""",
            
            'contextual_relationships': """This person is sharing about relationships and connections. Help them explore the dynamics, their feelings, and what they're learning about themselves through these connections.""",
            
            'contextual_career': """This person is reflecting on work and career. Help them explore not just what happened, but how it connects to their values, growth, and sense of purpose.""",
            
            'contextual_growth': """This person is in a reflective, growth-oriented mindset. Help them dig deeper into their insights and what they're discovering about themselves.""",
            
            'contextual_story_potential': """This conversation has rich story potential. Instead of being obvious about it, weave gentle magic into your responses. Use phrases like 'I can feel something meaningful taking shape in what you're sharing' or 'Your words are painting a beautiful picture' to subtly indicate that something special is emerging. Continue exploring naturally but with an awareness that a story wants to be born.""",
            
            'contextual_developing_story': """A meaningful story is developing here. Use magical, poetic language to acknowledge this: 'There's something beautiful emerging from what you're sharing' or 'I can sense the story that wants to be told here.' Ask questions that help them explore the experience more fully while maintaining the sense of wonder and discovery.""",

            'opening_prompts': [
                "What's been stirring in your mind lately?",
                "I'm here to listen. What would you like to explore today?",
                "Tell me about something that's been meaningful to you recently.",
                "What's something you've been reflecting on?",
                "Share whatever feels important to you right now.",
                "What's on your heart today?"
            ],

            'exploration_questions': [
                "What was that experience like for you?",
                "How did that make you feel?",
                "What stands out most to you about that?",
                "What do you think that reveals about you?",
                "What patterns do you notice here?",
                "What wisdom are you finding in this experience?",
                "What does this tell you about what matters to you?",
                "How has this changed your perspective?",
                "What are you learning about yourself through this?",
                "What feels most significant about this to you?"
            ],

            'validation_responses': [
                "That sounds really meaningful.",
                "I can sense how important this is to you.",
                "Thank you for sharing something so personal.",
                "That takes courage to explore.",
                "It sounds like you're discovering something important about yourself.",
                "That's a beautiful insight.",
                "I appreciate your openness in sharing this."
            ],

            'openai_gpt4': """You are using GPT-4 - bring your full emotional intelligence and ability to understand nuance. This is about helping someone understand themselves better, not just providing information. Be deeply empathetic and ask questions that reveal insights.""",
            
            'claude': """You are using Claude - use your thoughtful, reflective approach to help this person explore their inner world with curiosity and compassion.""",
            
            'gemini': """You are using Gemini - bring your understanding of human emotion and connection to create a meaningful dialogue focused on self-discovery.""",
            
            'story_context': """While keeping the conversation natural and supportive, notice when someone shares experiences that have narrative depth, emotional significance, or personal insights. These might naturally become meaningful stories they can revisit and transform.""",
            
            'fallback_friendly': """I'm here to listen and explore whatever you'd like to share. What's been on your mind lately?""",
            
            'session_continuation': """Continue building on the trust and understanding we've developed. Reference what they've shared before and help them go deeper into their experiences and insights."""
        }
    
    def _build_conversation_system_prompt(self, user_context=None, domain_insights=None, story_analysis=None) -> str:
        """Build context-aware conversation system prompt"""
        
        base_prompt = self._conversation_prompts['system_base']
        
        # Always encourage conversational flow continuity
        base_prompt += ("\n\nGuideline: If the user has not indicated the conversation is over, "
                        "end your reply with an inviting follow-up question that naturally encourages them to share more.")
        
        # Add context-specific guidance
        context_additions = []
        
        if user_context and user_context.get('completeness', 0) < 0.3:
            context_additions.append(self._conversation_prompts['contextual_new_user'])
        
        if domain_insights:
            insight_areas = list(domain_insights.keys())
            if 'emotions' in insight_areas:
                context_additions.append(self._conversation_prompts['contextual_emotional_awareness'])
            if 'relationships' in insight_areas:
                context_additions.append(self._conversation_prompts['contextual_relationships'])
            if 'career' in insight_areas:
                context_additions.append(self._conversation_prompts['contextual_career'])
            if 'personal_growth' in insight_areas:
                context_additions.append(self._conversation_prompts['contextual_growth'])
        
        if story_analysis:
            score = story_analysis.get('story_readiness_score', 0)
            if score > 0.6:
                context_additions.append(self._conversation_prompts['contextual_story_potential'])
            elif score > 0.3:
                context_additions.append(self._conversation_prompts['contextual_developing_story'])
        
        if context_additions:
            base_prompt += "\n\nSpecific context for this conversation:\n" + "\n".join(f"- {addition}" for addition in context_additions)
        
        return base_prompt
    
    # =============================================================================
    # FORMAT GENERATION PROMPTS
    # =============================================================================
    
    def _init_format_prompts(self) -> Dict[str, Any]:
        """Initialize format generation prompts"""
        
        return {
            'system_base': "You are a content creation expert who transforms personal stories into engaging formats while preserving their authentic emotional core.",
            
            'system_specialized': {
                FormatType.X: "You are a social media expert who creates viral, authentic content for X (formerly Twitter) that resonates emotionally with readers while staying within character limits.",
                FormatType.LINKEDIN: "You are a professional content creator who helps people share meaningful insights in a way that builds genuine connections and encourages professional dialogue.",
                FormatType.INSTAGRAM: "You are an Instagram content specialist who creates short, engaging posts with visual storytelling that captures attention quickly.",
                FormatType.FACEBOOK: "You are a community-focused social media specialist who creates content that brings people together through shared experiences and meaningful conversations.",
                FormatType.POEM: "You are a poet who transforms personal experiences into beautiful, moving verse that captures the essence of human emotion and universal truths.",
                FormatType.SONG: "You are a viral hit songwriter creating lyrics that stick in people's heads and make them want to sing along.",
                FormatType.REEL: "You are a viral content creator who transforms personal stories into engaging short-form video scripts for social media reels, with hooks, visual cues, and compelling narratives.",
                FormatType.FAIRYTALE: "You are a skilled fairytale writer who expands personal experiences into magical, enchanting fairytales with whimsical characters, imaginative settings, and narrative depth.",
                FormatType.ARTICLE: "You are a professional magazine writer who transforms personal experiences into compelling, publication-ready articles with journalistic structure and storytelling excellence.",
                FormatType.BLOG_POST: "You are a professional content creator who writes clean, valuable blog posts that provide actionable insights while maintaining authentic personal storytelling.",
                FormatType.PRESENTATION: "You are a presentation specialist who transforms stories into compelling, structured presentations that engage audiences and deliver clear takeaways.",
                FormatType.NEWSLETTER: "You are a newsletter writer who creates personal, engaging content that builds relationships with readers through authentic storytelling and valuable insights.",
        FormatType.PODCAST: "You are a podcast content specialist who creates engaging episode outlines and talking points for intimate, conversational storytelling that would work well with AI-generated audio.",
                FormatType.INSIGHTS: "You are a therapeutic content specialist who helps people extract meaningful psychological insights from their experiences with practical, actionable guidance.",
                FormatType.REFLECTION: "You are a friendly journaling coach who helps people talk about their feelings in clear, everyday language. Keep the tone warm, simple and down-to-earth – no academic jargon.",
                FormatType.GROWTH_SUMMARY: "You are a personal development coach who helps people identify and articulate their growth journey with clear, actionable next steps.",
                FormatType.JOURNAL_ENTRY: "You are a journaling specialist who helps people process experiences through authentic, vulnerable self-expression and emotional exploration.",
                FormatType.BOOK_CHAPTER: "You are a skilled ghost-writer weaving multiple true personal stories into a single, flowing memoir chapter that feels like a page-turning narrative."
            },
            
            'generation_templates': {
                FormatType.X: """Write a single X post (formerly Tweet) inspired by this story.

Story: {content}

Rules:
- 1 tweet only (no thread)
- ≤ 280 characters total
- Start with a hook emoji or strong statement
- End with 2–3 relevant hashtags
- Make it sound like a real person tweeting, not marketing copy
- No quote blocks, no line-break lists""",

                FormatType.LINKEDIN: """Create a professional LinkedIn post that shares this personal insight:

Story: {content}

Requirements:
- Professional yet personal tone
- Share the key lesson or insight
- Encourage meaningful engagement
- Include a call-to-action question
- 1-3 paragraphs maximum
- Professional hashtags""",

                FormatType.INSTAGRAM: """Create a short, engaging Instagram post that tells this story:

Story: {content}

Requirements:
- Keep it concise and impactful (1-2 short paragraphs)
- Visual storytelling approach with emotional punch
- Include relevant hashtags (5-10)
- Include emojis where appropriate
- Hook readers in the first line
- Encourage engagement""",

                FormatType.FACEBOOK: """Transform this into a Facebook post that encourages meaningful discussion:

Story: {content}

Requirements:
- Conversational, friendly tone
- Tell the story in a relatable way
- Ask a question to encourage comments
- 2-4 paragraphs
- Include relevant hashtags (2-4)
- Focus on building community connection""",

                FormatType.POEM: """Transform this story into a beautiful free verse poem:

Story: {content}

Requirements:
- Capture the emotional essence and core meaning
- Use vivid imagery and metaphors
- 8-16 lines with natural rhythm and flow
- Artistic and moving language
- Express the deeper truth of the experience""",

                FormatType.SONG: """Create a viral song from this story:

Story: {content}

Requirements:
- Start with: TITLE: "Song Title"
- Write catchy, memorable lyrics with a repeating hook
- MAXIMUM 200 words total (for 2-minute song length)
- NO structural labels like (Verse 1), (Chorus) - just pure lyrics
- Use metaphors and vivid imagery, not literal explanations
- Make it rhythmic and easy to sing along to
- Keep it punchy and viral-worthy""",

                FormatType.REEL: """Create a viral social media reel script based on this story:

Story: {content}

Requirements:
- Write in short-form video script format with visual hooks
- Include on-screen text suggestions and scene directions
- Create a strong opening hook within first 3 seconds  
- Structure for 15-60 second video format
- Include trending audio/music suggestions
- Make it highly shareable and relatable
- Add clear call-to-action or engagement prompt
- Focus on visual storytelling and quick emotional impact""",

                FormatType.FAIRYTALE: """Expand this into a magical fairytale:

Story: {content}

Requirements:
- Transform into a whimsical, enchanting fairytale
- Develop magical characters and fantasy setting
- Use fairytale narrative techniques (dialogue, description, magical elements)
- Create a complete fairytale arc with beginning, middle, end
- 800-1500 words
- Include magical elements and enchanting atmosphere
- Show rather than tell the emotional journey
- Include "once upon a time" style opening and "happily ever after" style ending""",

                FormatType.ARTICLE: """Transform this personal story into a clear, engaging magazine-style article:

Story: {content}

Headline that hooks readers (≤ 12 words)
Engaging intro paragraph that sets the scene
3–4 short sections with sub-heads (## style) guiding the flow
Blend the personal story with at least one expert insight or statistic
Use concrete details and quotes where natural
600-900 words total – concise, conversational magazine tone (think Wired / Atlantic)
Finish with a takeaway that circles back to the opening
Avoid academic jargon and verbose sentences""",

                FormatType.BLOG_POST: """Create a professional blog post from this personal experience:

Story: {content}

Requirements:
- Start directly with a compelling opening that hooks readers immediately
- NO title at the beginning - jump straight into the content
- Structure the content with clear H2 subheadings (## format)
- Mix personal storytelling with actionable insights
- Include practical takeaways readers can apply
- End with an engaging question or call-to-action
- 600-1000 words total
- Write in clean, professional blog format
- NO meta-information like word counts, labels, or structural notes
- Focus on valuable, shareable content that provides real value to readers""",

                FormatType.PRESENTATION: """Create a presentation outline based on this story:

Story: {content}

Requirements:
- 5-7 slide titles with key points
- Opening hook slide
- Story progression slides
- Key insights and takeaways
- Closing call-to-action
- Speaking notes for each slide
- Audience engagement elements""",

                FormatType.NEWSLETTER: """Create a complete newsletter featuring this personal story:

Story: {content}

Requirements:
- Write an engaging subject line in the format: "Subject: [Your Title]"
- Open with a warm, personal greeting to readers
- Tell the story in an engaging, newsletter-style narrative
- Include 2-3 key insights or takeaways clearly highlighted
- Add a thoughtful reflection section connecting to universal themes
- End with a clear, engaging call-to-action question for readers
- Close with a warm sign-off (like "Until next time" or "With gratitude")
- 500-700 words total
- Write in complete, polished newsletter format
- Ensure the newsletter has a clear beginning, middle, and complete ending
- NO abrupt cut-offs - always finish the final thought completely""",

                FormatType.PODCAST: """Create a podcast episode outline and talking points based on this story:

Story: {content}

Requirements:
- Compelling episode title and description
- 3-5 main talking points with natural conversation flow
- Opening hook and closing thoughts
- Questions for audience engagement
- Personal anecdotes and reflections woven throughout
- Conversational tone suitable for AI audio generation
- 15-30 minute episode structure
- Include suggested transition phrases and natural pauses""",

                FormatType.INSIGHTS: """Extract the key psychological and personal growth insights from this story:

Story: {content}

Requirements:
- 3-5 key insights clearly stated
- Actionable takeaways
- Reflection questions for deeper thinking
- Growth opportunities identified
- Therapeutic value and practical application
- Connection to broader life patterns""",

                FormatType.REFLECTION: """Write a short, honest reflection about this experience.

Story: {content}

Guidelines:
- First-person ("I") voice, friendly and conversational
- Everyday words, short sentences – no fancy vocabulary
- 150-250 words total
- Start with how the moment felt in the body or heart
- Describe one key thing you realised or learned
- Finish with one gentle, open question to yourself
""",

                FormatType.GROWTH_SUMMARY: """Create a personal growth summary from this experience:

Story: {content}

Requirements:
- Identify the key growth moment and what triggered it
- Compare before and after perspectives clearly
- List specific lessons learned and skills developed
- Explain how this growth can be applied in future situations
- Suggest ways to measure or track this progress
- Provide 2-3 concrete action steps for continued development
- Write in a structured, coaching-style format
- Focus on empowerment and forward momentum
- 300-500 words of practical personal development insights""",

                FormatType.JOURNAL_ENTRY: """Transform this into a reflective journal entry:

Story: {content}

Requirements:
- Start directly with personal, intimate thoughts - NO "Journal Entry" or date headers
- Stream-of-consciousness style
- Emotional honesty and vulnerability
- Questions and wonderings
- Personal insights and realizations
- Raw, authentic voice
- Write as if someone is writing in their private journal""",

                FormatType.BOOK_CHAPTER: """Write a cohesive chapter (~1500 words) that combines the following personal stories into one engaging narrative. Maintain first-person voice, chronological flow and emotional arc. Use scene transitions where necessary, but avoid obvious headings.

Stories:

{stories_markdown}

Requirements:
– 1400-1700 words
– One clear protagonist ("I")
– Smooth transitions; no bullet lists
– Title on first line inside **bold**
"""
            }
        }
    
    def _build_format_generation_prompt(self, content: str, format_type: FormatType, user_context=None, domain_insights=None) -> str:
        """Build format-specific generation prompt with context"""
        
        base_template = self._format_prompts['generation_templates'].get(format_type, "Transform this story into {format_type} format:\n\n{content}")
        prompt = base_template.format(content=content, format_type=format_type.value)
        
        # Add context if available
        context_additions = []
        if user_context:
            engagement = user_context.get('engagement_level', 'unknown')
            context_additions.append(f"User engagement level: {engagement}")
        
        if domain_insights:
            themes = domain_insights.get('themes', [])
            if themes:
                context_additions.append(f"Key themes: {', '.join(themes[:3])}")
            
            emotions = domain_insights.get('emotional_markers', [])
            if emotions:
                context_additions.append(f"Emotional tone: {', '.join(emotions[:2])}")
        
        if context_additions:
            prompt += "\n\nAdditional context:\n" + "\n".join(f"- {addition}" for addition in context_additions)
        
        return prompt
    
    def _get_format_system_prompt(self, format_type: FormatType = None) -> str:
        """Get system prompt for format generation"""
        
        if format_type and format_type in self._format_prompts['system_specialized']:
            return self._format_prompts['system_specialized'][format_type]
        
        return self._format_prompts['system_base']
    
    # =============================================================================
    # ANALYSIS PROMPTS
    # =============================================================================
    
    def _init_analysis_prompts(self) -> Dict[str, str]:
        """Initialize analysis-related prompts"""
        
        return {
            'system_base': "You are an expert content analyst who extracts meaningful insights from personal experiences and conversations with precision and empathy.",
            
            'story_analysis': """Analyze this personal story for narrative potential and emotional depth:

Story: {content}

Provide analysis in the following format:
1. Story Readiness Score (0.0-1.0): How ready this is to become a meaningful story
2. Key Themes: Primary themes and topics present
3. Emotional Markers: Emotional expressions and intensity
4. Narrative Elements: What story elements are present (conflict, resolution, growth, insight)
5. Gaps: What additional details would strengthen the narrative
6. Potential: What makes this story worth developing

Focus on identifying genuine story potential rather than forcing narratives where none exist.""",

            'domain_analysis': """Analyze this content for domain insights and categorization:

Content: {content}

Identify:
1. Primary domains (relationships, career, personal_growth, emotions, health_wellness, creativity)
2. Key themes and patterns
3. Emotional markers and intensity
4. Confidence level of analysis
5. Significant insights about the person's interests and focus areas

Provide structured analysis that helps understand the person's mental and emotional landscape.""",

            'cross_conversation': """Analyze these conversation patterns for deeper insights:

Conversations: {conversations}

Look for:
1. Recurring themes across conversations
2. Emotional patterns and growth over time
3. Relationship dynamics and social patterns
4. Personal development indicators
5. Areas of consistent focus or concern
6. Signs of growth, change, or stagnation

Provide insights that would help the person understand their own patterns and growth opportunities."""
        }
    
    def _build_story_analysis_prompt(self, content: str) -> str:
        """Build story analysis prompt"""
        return self._analysis_prompts['story_analysis'].format(content=content)
    
    def _build_story_creation_prompt(self, **kwargs) -> str:
        """Build story creation prompt that creates authentic, relatable stories"""
        conversation = kwargs.get('conversation', '')
        user_context = kwargs.get('user_context', {})
        domain_insights = kwargs.get('domain_insights', {})
        conversation_flow = kwargs.get('conversation_flow', [])
        
        # Build comprehensive context understanding
        context_details = []
        
        # User pattern context
        if user_context.get('primary_themes'):
            context_details.append(f"This person often reflects on: {', '.join(user_context['primary_themes'][:3])}")
        
        if user_context.get('emotional_expression_style'):
            context_details.append(f"Their emotional expression style: {user_context['emotional_expression_style']}")
        
        if user_context.get('engagement_level'):
            context_details.append(f"Their engagement level: {user_context['engagement_level']}")
        
        # Domain insights context
        if domain_insights.get('themes'):
            context_details.append(f"Key themes in this conversation: {', '.join(domain_insights['themes'][:3])}")
        
        if domain_insights.get('emotional_markers'):
            context_details.append(f"Emotional markers detected: {', '.join(domain_insights['emotional_markers'][:3])}")
        
        if domain_insights.get('domains'):
            primary_domains = list(domain_insights['domains'].keys())[:2]
            context_details.append(f"Primary life domains: {', '.join(primary_domains)}")
        
        # Conversation flow analysis
        message_count = len([msg for msg in conversation_flow if msg.get('role') == 'user'])
        if message_count > 5:
            context_details.append("This was a deep, extended conversation showing significant emotional investment")
        elif message_count > 3:
            context_details.append("This was a meaningful conversation with good emotional depth")
        else:
            context_details.append("This was a focused conversation touching on important themes")
        
        context_section = "\n".join([f"- {detail}" for detail in context_details]) if context_details else "- This person shared something meaningful"
        
        # Build the authentic, relatable prompt
        prompt = f"""Transform this personal conversation into a story that feels authentic and relatable - like something someone might actually write about themselves or share with a close friend.

CONVERSATION:
{conversation}

CONTEXT ABOUT THIS PERSON:
{context_section}

YOUR TASK:
Create a 300-500 word story that:

1. **Sounds Real and Authentic**: Write like a real person telling their story, not like a therapist or novelist

2. **Uses Natural Language**: Speak in the same tone they used - if they were casual, be casual. If they were thoughtful, be thoughtful. Mirror their energy.

3. **Captures Their Voice**: Use language they would actually use. Avoid overly fancy words or concepts.

4. **Focuses on the Human Experience**: What actually happened, how it felt, what they learned - keep it grounded and real

5. **Makes Them the Hero**: Help them see their growth and strength, but in their own words/style

6. **Stays Relatable**: Other people their age should read this and think "I totally get that" or "I've felt that way too"

7. **Only Use Provided Details**: Do NOT add any new events, characters, explanations, or factual details that the user did not explicitly mention in the conversation. If something is unclear or missing, simply omit it rather than inventing or assuming.

WRITING STYLE:
- Write in first person ("I realized..." "I found myself..." "I learned...")
- Use conversational, natural language - NOT poetic or literary
- Include the specific details they shared
- Keep insights simple and authentic, not overly philosophical
- End with something hopeful or forward-looking, but realistic

EXAMPLES OF GOOD TONE:
- "I never thought I'd be the type of person who..."
- "It's funny how you don't realize..."
- "Looking back, I can see that..."
- "I'm starting to understand that..."
- "The thing I'm learning about myself is..."

Write the story now - make it sound like THEY wrote it, not like someone else wrote it about them:"""
        
        return prompt
    
    def _build_domain_analysis_prompt(self, content: str) -> str:
        """Build domain analysis prompt"""
        return self._analysis_prompts['domain_analysis'].format(content=content)
    
    def _build_cross_conversation_prompt(self, conversations: str) -> str:
        """Build cross-conversation analysis prompt"""
        return self._analysis_prompts['cross_conversation'].format(conversations=conversations)
    
    # =============================================================================
    # CONTEXT & INSIGHTS PROMPTS
    # =============================================================================
    
    def _init_context_prompts(self) -> Dict[str, str]:
        """Initialize context gathering and insights prompts"""
        
        return {
            'deep_insights': """Generate deep psychological insights about this person based on their conversation patterns:

User Context: {user_context}
Conversation Patterns: {patterns}

Provide insights about:
1. Core personality patterns
2. Communication style and preferences
3. Emotional processing patterns
4. Relationship dynamics
5. Growth areas and strengths
6. Recommended approaches for meaningful engagement

Focus on actionable insights that help create better conversations and support their personal development.""",

            'context_gathering_general': [
                "What's been on your mind lately that you'd like to explore?",
                "I'm curious about what matters most to you right now.",
                "What experiences have been shaping your perspective recently?",
                "Is there something you've been thinking about that you'd like to talk through?",
                "What would be most helpful for you to reflect on today?"
            ],

            'context_gathering_emotions': [
                "How have you been feeling about things lately?",
                "What emotions have been coming up for you recently?",
                "I'm sensing there might be some feelings you're processing - would you like to explore that?",
                "What's your emotional world like right now?",
                "How do you usually process strong emotions when they come up?"
            ],

            'context_gathering_relationships': [
                "How are the important relationships in your life feeling right now?",
                "What's been happening in your connections with others?",
                "I'm curious about how you're experiencing your relationships lately.",
                "What patterns do you notice in how you connect with people?",
                "Are there any relationship dynamics you've been thinking about?"
            ],

            'context_gathering_growth': [
                "What areas of growth are you focusing on right now?",
                "What have you been learning about yourself lately?",
                "Where do you feel yourself evolving or changing?",
                "What would growth look like for you in this season of life?",
                "What insights about yourself have surprised you recently?"
            ]
        }
    
    def _build_deep_insights_prompt(self, user_context: Dict, patterns: List) -> str:
        """Build deep insights generation prompt"""
        return self._context_prompts['deep_insights'].format(
            user_context=str(user_context),
            patterns=str(patterns)
        )
    
    # =============================================================================
    # STORY EVALUATION PROMPTS
    # =============================================================================
    
    def _init_story_evaluation_prompts(self) -> Dict[str, str]:
        """Initialize story evaluation and conversation guidance prompts"""
        
        return {
            'system_base': "You are a conversation specialist who helps identify when personal sharing has genuine story potential and guides conversations toward meaningful narrative development.",
            
            'story_readiness': """Evaluate this conversation for story readiness:

Conversation: {conversation}

Assess the story potential on a scale of 0.0 to 1.0:
- 0.0-0.3: Just conversation, no clear story emerging
- 0.3-0.65: Story potential exists, needs development
- 0.65-1.0: Ready for story creation, has narrative elements

Consider:
1. Emotional depth and vulnerability
2. Clear narrative elements (beginning, conflict, resolution, insight)
3. Personal growth or realization
4. Universal themes others can relate to
5. Specific details that bring the experience to life

Provide score and brief explanation of assessment.""",

            'conversation_guidance': """Generate conversation guidance for developing story potential:

Current conversation: {conversation}
Story readiness score: {score}

Provide guidance for:
1. Strategy: What conversational approach would help develop this further
2. Suggested responses: 2-3 specific responses that would encourage deeper sharing
3. Next steps: What information or emotional depth is needed
4. Questions to ask: Specific questions that would unlock more story potential

Focus on natural, empathetic guidance that feels supportive rather than extractive."""
        }
    
    def _build_story_readiness_prompt(self, conversation: List[Dict]) -> str:
        """Build story readiness evaluation prompt"""
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
        return self._story_evaluation_prompts['story_readiness'].format(conversation=conversation_text)
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _get_fallback_prompt(self) -> str:
        """Fallback prompt when specific prompt type not found"""
        return "Please analyze the provided content and respond thoughtfully based on the context given."
    
    def _get_fallback_system_prompt(self) -> str:
        """Fallback system prompt"""
        return "You are a helpful AI assistant that provides thoughtful, contextual responses to user requests."
    
    def get_prompt_statistics(self) -> Dict[str, Any]:
        """Get statistics about available prompts for monitoring"""
        
        return {
            'total_prompt_types': len(PromptType),
            'conversation_prompts': len(self._conversation_prompts),
            'format_prompts': len(self._format_prompts['generation_templates']),
            'analysis_prompts': len(self._analysis_prompts),
            'context_prompts': len(self._context_prompts),
            'story_evaluation_prompts': len(self._story_evaluation_prompts),
            'initialized_at': datetime.now().isoformat()
        }
    


class AIProviderManager:
    """
    Manages different GPT model versions for user selection
    Focuses on OpenAI GPT models only
    """
    
    SUPPORTED_PROVIDERS = {
        'gpt4': {
            'name': 'GPT-4',
            'description': 'Most advanced reasoning and knowledge',
            'model': 'gpt-4',
            'capabilities': ['general_chat', 'analysis', 'creative', 'technical', 'emotional_support']
        },
        'gpt4_turbo': {
            'name': 'GPT-4 Turbo',
            'description': 'Faster responses with latest training',
            'model': 'gpt-4-turbo-preview',
            'capabilities': ['general_chat', 'analysis', 'creative', 'technical', 'faster_responses']
        },
        'gpt35_turbo': {
            'name': 'GPT-3.5 Turbo',
            'description': 'Quick and efficient for most conversations',
            'model': 'gpt-3.5-turbo',
            'capabilities': ['general_chat', 'creative', 'quick_responses']
        }
    }
    
    def __init__(self):
        self.default_provider = 'gpt4'
        self.user_preferences = {}  # user_id -> preferred_provider
    
    def get_available_providers(self) -> Dict[str, Dict]:
        """Get list of available GPT models"""
        return self.SUPPORTED_PROVIDERS
    
    def set_user_preference(self, user_id: str, provider: str) -> bool:
        """Set user's preferred GPT model"""
        if provider in self.SUPPORTED_PROVIDERS:
            self.user_preferences[user_id] = provider
            return True
        return False
    
    def get_user_provider(self, user_id: str) -> str:
        """Get user's preferred provider or default"""
        return self.user_preferences.get(user_id, self.default_provider)
    
    def get_provider_model(self, provider: str) -> str:
        """Get the actual model name for API calls"""
        return self.SUPPORTED_PROVIDERS.get(provider, {}).get('model', 'gpt-4')
    
    def get_provider_prompt(self, provider: str, prompts_engine) -> str:
        """Get specific prompt for the GPT model"""
        # All GPT models use the same conversation prompts
        return prompts_engine.get_conversation_prompt('openai_gpt4') 