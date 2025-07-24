from flask import Flask, render_template, jsonify, request, send_from_directory, redirect
from datetime import datetime
import json
import re
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import logging
import requests
from typing import List, Dict, Optional, Any
import openai
import random
from werkzeug.utils import secure_filename
import uuid
from dotenv import load_dotenv, find_dotenv
import patch_ng
import json as _json
# JSON Schema validation (used for validating knowledge objects)
try:
    import jsonschema as _jsonschema
except ImportError:
    _jsonschema = None

# Load environment variables from nearest .env (only once)
load_dotenv(find_dotenv())

# Configure OpenAI for SentimentalApp only. Mental-OS switches key per request.
_sent_key = os.getenv('OPENAI_API_KEY', '')

openai.api_key = _sent_key if _sent_key.startswith('sk-') else None

if openai.api_key is None:
    print('WARNING: OPENAI_API_KEY missing or invalid – SentimentalApp AI endpoints will be disabled until a valid key is provided')

# (Removed automatic key mirroring – keeps Sentimental and MentalOS keys isolated.)

# --------------------------------------------------------------------

import random
from werkzeug.utils import secure_filename
import uuid

# Import our intelligent engines (these may touch openai during init, so do it *after* key sanitisation)
from smart_story_engine import SmartStoryEngine
from personal_context_mapper import PersonalContextMapper
from knowledge_engine import KnowledgeEngine
from formats_generation_engine import FormatsGenerationEngine
from format_types import FormatType
from prompts_engine import PromptsEngine, PromptType, AIProviderManager

# The logger isn't configured until now, replicate the earlier messages
if not openai.api_key:
    logging.warning('OPENAI_API_KEY not found in environment variables – OpenAI features disabled')
else:
    logging.info('OpenAI API key loaded from environment variables')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment detection
ENVIRONMENT = os.getenv('ENVIRONMENT', 'test')  # production, demo, test
IS_DEMO = ENVIRONMENT == 'demo'
IS_TEST = ENVIRONMENT == 'test'

logger.info(f"Starting application in {ENVIRONMENT} environment")

app = Flask(__name__)

# Add CORS support for local development
try:
    from flask_cors import CORS
    CORS(app)
    logger.info("CORS enabled for local development")
except ImportError:
    logger.warning("flask-cors not installed, skipping CORS setup")

# Initialize db variable
db = None

# Firebase configuration
try:
    # Check if we're in Cloud Run environment
    if os.getenv('K_SERVICE') or os.getenv('GOOGLE_CLOUD_PROJECT'):
        logger.info("Initializing Firebase in Cloud Run environment")
        # In Cloud Run environment we use automatic authentication
        firebase_admin.initialize_app()
    else:
        logger.info("Initializing Firebase in local environment")
        # In local environment we use credentials file
        if os.path.exists('firebase-credentials.json'):
            cred = credentials.Certificate('firebase-credentials.json')
            firebase_admin.initialize_app(cred)
        else:
            logger.warning("No firebase-credentials.json found, trying default credentials")
            firebase_admin.initialize_app()
    logger.info("Firebase initialized successfully")
    if db is None:
        db = firestore.client()
    
    # Initialize Firebase Storage with fallback
    try:
        bucket = storage.bucket('sentimental-audio-uploads')
        logger.info("Firebase Storage initialized successfully")
    except Exception as storage_error:
        logger.warning(f"Firebase Storage initialization failed: {storage_error}")
        bucket = None
    
except Exception as e:
    logger.error(f"Error initializing Firebase: {str(e)}")
    # In demo mode, we can continue without Firebase since we use mock data
    if IS_DEMO:
        logger.info("Demo mode: continuing without Firebase connection")
        db = None
        bucket = None
    else:
        raise

# Download NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

# Add after app configuration
app.config['UPLOAD_FOLDER'] = 'public/static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
# Extend allowed extensions for image uploads
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'jpg', 'jpeg', 'png', 'webp'}

# MentalOS file system base directory
BASE_MENTALOS_DIR = os.path.join(os.getcwd(), 'MentalOS', 'user_data')
os.makedirs(BASE_MENTALOS_DIR, exist_ok=True)

# allowed_file function moved to utils.py

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def is_anonymous_user(user_id):
    """Check if user is anonymous"""
    return user_id and (user_id.startswith('anon_') or user_id == 'anonymous')

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_access_code(code):
    """Check if access code is valid"""
    valid_codes = ['ALPHA2024', 'BETA2024', 'DEMO2024']
    return code in valid_codes

def is_demo_user(user_id):
    """Check if user is demo user"""
    return user_id and user_id.startswith('demo_')

def analyze_text(text):
    """Analyzes text and finds themes, emotions and connections"""
    # Tokenize text
    try:
        tokens = word_tokenize(text.lower())
    except LookupError:
        # Attempt to download punkt on the fly once, then retry
        try:
            nltk.download('punkt', quiet=True)
            tokens = word_tokenize(text.lower())
        except Exception:
            # Fallback to simple split if tokenizer still unavailable
            tokens = text.lower().split()
    
    # Remove stopwords - use English as fallback if Estonian not available
    try:
        stop_words = set(stopwords.words('estonian'))
    except OSError:
        logger.warning("Estonian stopwords not available, using English stopwords")
        stop_words = set(stopwords.words('english'))
    tokens = [word for word in tokens if word not in stop_words and len(word) > 2]
    
    # Find most frequent words (themes)
    word_freq = Counter(tokens)
    themes = [word for word, freq in word_freq.most_common(5)]
    
    # Analyze emotions
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(text)
    
    emotions = []
    if sentiment['pos'] > 0.5:
        emotions.append('positive')
    if sentiment['neg'] > 0.5:
        emotions.append('negative')
    if sentiment['neu'] > 0.5:
        emotions.append('neutral')
    
    return {
        'themes': themes,
        'emotions': emotions,
        'sentiment_score': sentiment['compound']
    }

def find_connections(story_id):
    """Finds connections between stories"""
    if db is None:
        return []
        
    story_ref = db.collection('stories').document(str(story_id))
    story = story_ref.get()
    
    if not story.exists:
        return []
    
    story_data = story.to_dict()
    connections = []
    
    # Search for all other stories
    other_stories = db.collection('stories').where('id', '!=', story_id).stream()
    
    for other_story in other_stories:
        other_data = other_story.to_dict()
        # Simple connection finding based on similar words
        story_words = set(word_tokenize(story_data['content'].lower()))
        other_words = set(word_tokenize(other_data['content'].lower()))
        common_words = story_words.intersection(other_words)
        
        if len(common_words) > 3:  # If there are more than 3 common words
            connection = {
                'id': other_data['id'],
                'title': other_data['title'],
                'description': f"Similar themes: {', '.join(list(common_words)[:3])}",
                'strength': len(common_words) / 10  # Normalize strength to 0-1 range
            }
            connections.append(connection)
            
            # Save connection to database
            db.collection('connections').add({
                'story_id': story_id,
                'connected_story_id': other_data['id'],
                'common_words': list(common_words),
                'strength': connection['strength'],
                'created_at': firestore.SERVER_TIMESTAMP
            })
    
    return connections

class IntelligentConversationEngine:
    """
    Full ChatGPT-like conversation engine with multi-AI provider support
    Handles general knowledge, world topics, and personal conversations
    """
    
    def __init__(self):
        self.client = None
        # Prefer an already configured key (e.g. MENTALOS_OPENAI_API_KEY was set at module load).
        # Only fall back to OPENAI_API_KEY if it looks valid **and** no key is currently active.
        if openai.api_key and openai.api_key.startswith('sk-'):
            self.client = openai
            logger.info("OpenAI client initialized successfully with pre-configured API key")
        elif os.getenv('OPENAI_API_KEY', '').startswith('sk-'):
            # Legacy environment variable support
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.client = openai
            logger.info("OpenAI client initialized successfully using legacy OPENAI_API_KEY")
        else:
            logger.warning("Valid OpenAI API key not found – using fallback responses")
        
        self.conversation_history = {}
    
    def generate_response(self, message: str, user_id: str, context: Dict = None) -> str:
        """
        Generate intelligent response using selected AI provider
        Full conversational AI mode with story detection in background
        """
        try:
            # Get user's preferred AI provider
            preferred_provider = ai_provider_manager.get_user_provider(user_id)
            
            # Build comprehensive system prompt
            system_prompt = self._build_system_prompt(preferred_provider, context)
            
            # Get conversation history
            history = self.conversation_history.get(user_id, [])
            
            if self.client:
                # Use OpenAI for full ChatGPT-like experience
                response = self._openai_chat_completion(message, user_id, system_prompt, history)
            else:
                # Use enhanced fallback with full capabilities
                response = self._intelligent_fallback(message, context)
            
            # Update conversation history
            self._update_conversation_history(user_id, message, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in conversation generation: {e}")
            return prompts_engine.get_fallback_response(message, context)
    
    def _build_system_prompt(self, provider: str, context: Dict = None) -> str:
        """Build comprehensive system prompt for empathetic conversation"""
        try:
            # Use the new context-aware prompt building
            system_prompt = prompts_engine.get_prompt(
                PromptType.CONVERSATION_SYSTEM,
                user_context=context,
                domain_insights=None,  # Will be passed when available
                story_analysis=None    # Will be passed when available
            )
            
            # Add provider-specific guidance
            provider_guidance = prompts_engine.get_conversation_prompt(f'openai_{provider}')
            if provider_guidance and provider_guidance != prompts_engine.get_conversation_prompt('system_base'):
                system_prompt += f"\n\n{provider_guidance}"
            
            # Add story context guidance
            story_context = prompts_engine.get_conversation_prompt('story_context')
            system_prompt += f"\n\n{story_context}"
            
            return system_prompt
            
        except Exception as e:
            logger.warning(f"Error building system prompt: {e}")
            return prompts_engine.get_conversation_prompt('system_base')
    
    def _openai_chat_completion(self, message: str, user_id: str, system_prompt: str, history: List) -> str:
        """Generate response using OpenAI with user's selected GPT model"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 10 exchanges to stay within token limits)
        for exchange in history[-10:]:
            messages.append({"role": "user", "content": exchange["user"]})
            messages.append({"role": "assistant", "content": exchange["assistant"]})
        
        messages.append({"role": "user", "content": message})
        
        # Get user's preferred model
        user_provider = ai_provider_manager.get_user_provider(user_id)
        model = ai_provider_manager.get_provider_model(user_provider)
        
        response = self.client.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=500,
            temperature=0.8,  # More creative and natural
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        
        return response.choices[0].message.content.strip()
    
    def _intelligent_fallback(self, message: str, context: Dict = None) -> str:
        """Enhanced fallback that attempts to handle general topics naturally"""
        # Use the centralized fallback from PromptsEngine
        return prompts_engine.get_fallback_response(message, context)
    
    def _update_conversation_history(self, user_id: str, user_message: str, response: str):
        """Update conversation history for context continuity"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        self.conversation_history[user_id].append({
            "user": user_message,
            "assistant": response,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 20 exchanges per user
        if len(self.conversation_history[user_id]) > 20:
            self.conversation_history[user_id] = self.conversation_history[user_id][-20:]

# Initialize the intelligent conversation engine
intelligent_conversation_engine = IntelligentConversationEngine()

# Initialize all intelligent engines with database integration
prompts_engine = PromptsEngine()
ai_provider_manager = AIProviderManager()
personal_context_mapper = PersonalContextMapper(db=db)
knowledge_engine = KnowledgeEngine(db=db)
formats_generation_engine = FormatsGenerationEngine(db=db)

# Connect the prompts engine to the formats generation engine
formats_generation_engine.prompts_engine = prompts_engine

# Initialize smart story engine with all dependencies
smart_story_engine = SmartStoryEngine(
    knowledge_engine=knowledge_engine,
    personal_context_mapper=personal_context_mapper,
    conversation_planner=None  # Will implement later if needed
)

logger.info("All intelligent engines initialized successfully")

@app.route('/')
def index():
    return render_template('index.html', environment=ENVIRONMENT)

@app.route('/app')
def app_view():
    """Render the main React-powered application shell.

    Historically we showed a marketing landing page in production and only
    served the full app in testing. Now the app itself is the product, so we
    always return the compiled `app.html` template regardless of environment.
    A cache-busting query string is appended to force browsers to pull the
    latest static assets after each deploy.
    """
    import time
    # Build Firebase client (web) config from environment variables
    firebase_client_config = json.dumps({
        "apiKey": os.getenv("FIREBASE_API_KEY", ""),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.getenv("FIREBASE_APP_ID", ""),
        "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", "")
    })
    return render_template('app.html', environment=ENVIRONMENT, cache_bust=int(time.time()), firebase_config=firebase_client_config)

@app.route('/landing')
def landing():
    return render_template('index.html', environment=ENVIRONMENT)

@app.route('/manifest.json')
def manifest():
    """Serve web-app manifest.json.
    Preference order:
    1. static/manifest.json (production build)
    2. project-root manifest.json (development fallback)
    This avoids 404s in local dev when file only exists at repo root.
    """
    if os.path.exists(os.path.join('static', 'manifest.json')):
        return send_from_directory('static', 'manifest.json')
    # Fallback to project root manifest.json
    return send_from_directory('.', 'manifest.json')

@app.route('/cosmos')
def cosmos():
    # Only allow cosmos access in demo and test environments
    if ENVIRONMENT == 'production':
        return render_template('index.html', environment=ENVIRONMENT)
    return render_template('cosmos.html', environment=ENVIRONMENT)

@app.route('/chat')
def chat():
    # Only allow chat access in demo and test environments
    if ENVIRONMENT == 'production':
        return render_template('index.html', environment=ENVIRONMENT)
    return render_template('chat.html', environment=ENVIRONMENT)

@app.route('/deck')
def deck():
    # Only allow deck access in demo and test environments
    if ENVIRONMENT == 'production':
        return render_template('index.html', environment=ENVIRONMENT)
    return render_template('deck.html', environment=ENVIRONMENT)

@app.route('/story')
def story():
    # Only allow story access in demo and test environments
    if ENVIRONMENT == 'production':
        return render_template('index.html', environment=ENVIRONMENT)
    return render_template('story.html', environment=ENVIRONMENT)

@app.route('/inner-space')
def inner_space():
    # Only allow inner-space access in demo and test environments
    if ENVIRONMENT == 'production':
        return render_template('index.html', environment=ENVIRONMENT)
    return render_template('inner-space.html', environment=ENVIRONMENT)

@app.route('/api/stories', methods=['GET'])
def get_stories():
    if IS_DEMO:
        # Use mock data in demo environment
        stories = get_mock_stories()
        logger.info(f"Returning {len(stories)} mock stories for demo environment")
        return jsonify(stories)
    
    # Regular database query
    if db is None:
        return jsonify([])
        
    stories = []
    # Try to fetch ordered by created_at (newest first) when field present
    try:
        story_query = db.collection('stories').order_by('created_at', direction=firestore.Query.DESCENDING)
        story_iter = story_query.stream()
    except Exception:
        # Fallback to unordered stream if created_at not indexed / missing
        story_iter = db.collection('stories').stream()

    for story in story_iter:
        story_data = story.to_dict()
        # Add the Firestore document ID as the story ID
        story_data['id'] = story.id
        # Ensure compatibility with React component
        story_data['author'] = story_data.get('author', 'Anonymous')
        story_data['content'] = story_data.get('content', story_data.get('text', ''))
        story_data['timestamp'] = story_data.get('timestamp', '1h ago')
        story_data['format'] = story_data.get('format', 'text')
        story_data['public'] = story_data.get('public', True)
        story_data['reactions'] = story_data.get('reactions', 0)
        story_data['inCosmos'] = story_data.get('inCosmos', False)
        story_data['createdFormats'] = story_data.get('createdFormats', [])
        story_data['cosmic_insights'] = story_data.get('analysis', {}).get('themes', [])
        stories.append(story_data)
    return jsonify(stories)

@app.route('/api/stories', methods=['POST'])
def add_story():
    if IS_DEMO:
        # Don't allow adding new stories in demo environment
        return jsonify({
            'error': 'Cannot add new stories in demo environment',
            'message': 'This is a demo version. Use the full version to add new stories.'
        }), 403
    
    # In test environment, require authentication
    if IS_TEST:
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please register or login to create stories in test environment.'
            }), 401
        
        # Verify user exists
        try:
            user_doc = db.collection('test_users').document(user_id).get()
            if not user_doc.exists:
                return jsonify({'error': 'Invalid user'}), 401
        except Exception as e:
            return jsonify({'error': 'Authentication failed'}), 401
    
    if db is None:
        return jsonify({'error': 'Database not available'}), 500
        
    story = request.json
    story['id'] = str(len(list(db.collection('stories').stream())) + 1)
    story['timestamp'] = datetime.now().isoformat()
    story['author'] = story.get('author', 'You')
    story['public'] = story.get('public', True)
    story['reactions'] = 0
    story['inCosmos'] = False
    story['createdFormats'] = []
    
    # Analüüsi lugu
    analysis = analyze_text(story['content'])
    story['emotional_intensity'] = abs(analysis['sentiment_score'])
    story['analysis'] = analysis
    
    # Salvesta andmebaasi
    db.collection('stories').document(story['id']).set(story)
    
    # Update user statistics in test environment
    if IS_TEST and 'user_id' in locals():
        try:
            user_ref = db.collection('test_users').document(user_id)
            user_ref.update({'stories_created': firestore.Increment(1)})
        except Exception as e:
            logger.warning(f"Failed to update user statistics: {str(e)}")
    
    # Loo seosed teiste lugudega
    connections = find_connections(story['id'])
    
    return jsonify(story), 201

@app.route('/api/stories/<string:story_id>', methods=['DELETE'])
def delete_story(story_id):
    """Delete a story by ID"""
    if IS_DEMO:
        return jsonify({
            'error': 'Cannot delete stories in demo environment',
            'message': 'This is a demo version. Use the full version to delete stories.'
        }), 403
    
    # In test environment, require authentication
    if IS_TEST:
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please register or login to delete stories in test environment.'
            }), 401
        
        # Verify user exists
        try:
            user_doc = db.collection('test_users').document(user_id).get()
            if not user_doc.exists:
                return jsonify({'error': 'Invalid user'}), 401
        except Exception as e:
            return jsonify({'error': 'Authentication failed'}), 401
    
    if db is None:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        # Get the story to check if it exists and get owner info
        story_ref = db.collection('stories').document(story_id)
        story = story_ref.get()
        
        if not story.exists:
            return jsonify({'error': 'Story not found'}), 404
        
        story_data = story.to_dict()
        
        # In test environment, verify user owns the story (optional security check)
        if IS_TEST and 'user_id' in locals():
            story_user_id = story_data.get('user_id')
            if story_user_id and story_user_id != user_id:
                return jsonify({
                    'error': 'Permission denied',
                    'message': 'You can only delete your own stories.'
                }), 403
        
        # Delete the story
        story_ref.delete()
        
        # Also delete any connections related to this story
        connections_query = db.collection('connections').where('story_id', '==', story_id)
        for conn in connections_query.stream():
            conn.reference.delete()
        
        # Update user statistics in test environment
        if IS_TEST and 'user_id' in locals():
            try:
                user_ref = db.collection('test_users').document(user_id)
                user_ref.update({'stories_deleted': firestore.Increment(1)})
            except Exception as e:
                logger.warning(f"Failed to update user statistics: {str(e)}")
        
        logger.info(f"Story {story_id} deleted successfully")
        return jsonify({
            'message': 'Story deleted successfully',
            'story_id': story_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting story {story_id}: {str(e)}")
        return jsonify({'error': 'Failed to delete story'}), 500

@app.route('/api/stories/<string:story_id>', methods=['PUT'])
def update_story(story_id):
    """Update an existing story (partial update)"""
    if IS_DEMO:
        return jsonify({
            'error': 'Cannot update stories in demo environment',
            'message': 'This is a demo version. Use the full version to update stories.'
        }), 403
    
    # In test environment, require authentication
    if IS_TEST:
        user_id = request.headers.get('X-User-ID')
        user_email = request.headers.get('X-User-Email', '')
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please register or login to update stories in test environment.'
            }), 401
        
        # Verify user exists
        try:
            user_doc = db.collection('test_users').document(user_id).get()
            if not user_doc.exists:
                return jsonify({'error': 'Invalid user'}), 401
        except Exception:
            return jsonify({'error': 'Authentication failed'}), 401
    else:
        # In production environment we still grab the headers for potential super-user bypass
        user_id = request.headers.get('X-User-ID')
        user_email = request.headers.get('X-User-Email', '')
    
    if db is None:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        story_ref = db.collection('stories').document(story_id)
        story_doc = story_ref.get()
        
        if not story_doc.exists:
            return jsonify({'error': 'Story not found'}), 404
        
        story_data = story_doc.to_dict()
        story_owner_id = story_data.get('user_id') or story_data.get('author_id')
        
        # Permission check (test env or otherwise) – allow super user override
        if story_owner_id and user_id and story_owner_id != user_id and not is_super_user(user_id, user_email):
            return jsonify({
                'error': 'Permission denied',
                'message': 'You can only update your own stories.'
            }), 403
        
        # Validate payload
        update_payload = request.get_json() or {}
        if not update_payload:
            return jsonify({'error': 'No update data provided'}), 400
        
        # Only allow specific fields to be updated
        allowed_fields = ['title', 'content', 'author', 'public', 'format']
        update_fields = {field: update_payload[field] for field in allowed_fields if field in update_payload}
        
        # If content was updated, re-compute analysis and emotional intensity
        if 'content' in update_fields:
            try:
                analysis = analyze_text(update_fields['content'])
            except LookupError as le:
                # Likely missing NLTK data in local dev; log and fallback
                logger.warning(f"NLTK resource missing while analyzing text: {le}. Using fallback analysis.")
                analysis = {
                    'themes': [],
                    'emotions': [],
                    'sentiment_score': 0
                }
            except Exception as e:
                logger.error(f"Unexpected error in analyze_text: {e}")
                analysis = {
                    'themes': [],
                    'emotions': [],
                    'sentiment_score': 0
                }
            update_fields['analysis'] = analysis
            update_fields['emotional_intensity'] = abs(analysis.get('sentiment_score', 0))
        
        # Always update the timestamp
        update_fields['updated_at'] = datetime.now().isoformat()
        
        if not update_fields:
            return jsonify({'error': 'Nothing to update'}), 400
        
        # Perform partial update (avoids large document rewrite & keeps firestore limits)
        story_ref.update(update_fields)
        
        # Build response (merge existing data with updates for the client)
        updated_story = {**story_data, **update_fields, 'id': story_id}
        
        logger.info(f"Story {story_id} updated successfully by {user_id or 'unknown user'}")
        return jsonify(updated_story), 200
        
    except Exception as e:
        logger.error(f"Error updating story {story_id}: {str(e)}")
        return jsonify({'error': 'Failed to update story'}), 500

@app.route('/api/connections/<string:story_id>', methods=['GET'])
def get_connections(story_id):
    if IS_DEMO:
        # Use mock connections in demo environment
        mock_connections = get_mock_connections()
        connections = [conn for conn in mock_connections if conn['story_id'] == story_id]
        logger.info(f"Returning {len(connections)} mock connections for story {story_id}")
        return jsonify(connections)
    
    # Regular database query
    if db is None:
        return jsonify([])
        
    connections = []
    for conn in db.collection('connections').where('story_id', '==', story_id).stream():
        connections.append(conn.to_dict())
    return jsonify(connections)

@app.route('/api/insights/<string:story_id>', methods=['GET'])
def get_insights(story_id):
    story_ref = db.collection('stories').document(story_id)
    story = story_ref.get()
    
    if not story.exists:
        return jsonify({'error': 'Story not found'}), 404
    
    story_data = story.to_dict()
    connections = find_connections(story_id)
    
    insights = {
        'themes': story_data['analysis']['themes'],
        'emotions': story_data['analysis']['emotions'],
        'connections': [f"Connection with story '{conn['title']}'" for conn in connections]
    }
    return jsonify(insights)

@app.route('/api/stories/<string:story_id>/like', methods=['POST', 'DELETE'])
def handle_story_likes(story_id):
    """Handle story likes/reactions"""
    # In test environment, require authentication
    if IS_TEST:
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please register or login to like stories.'
            }), 401
        
        # Verify user exists
        try:
            user_doc = db.collection('test_users').document(user_id).get()
            if not user_doc.exists:
                return jsonify({'error': 'Invalid user'}), 401
        except Exception as e:
            return jsonify({'error': 'Authentication failed'}), 401
    
    if db is None:
        return jsonify({'error': 'Database not available'}), 500
    
    # Get the story
    story_ref = db.collection('stories').document(story_id)
    story = story_ref.get()
    
    if not story.exists:
        return jsonify({'error': 'Story not found'}), 404
    
    story_data = story.to_dict()
    
    # Handle like/unlike
    if request.method == 'POST':
        # Check if user already liked this story
        if IS_TEST and 'user_id' in locals():
            existing_likes = db.collection('story_likes').where('user_id', '==', user_id).where('story_id', '==', story_id).limit(1).get()
            if len(list(existing_likes)) > 0:
                return jsonify({'error': 'You have already liked this story'}), 400
        
        # Add like
        new_reactions = (story_data.get('reactions', 0)) + 1
        story_ref.update({'reactions': new_reactions})
        
        # Track user like
        if IS_TEST and 'user_id' in locals():
            try:
                like_data = {
                    'user_id': user_id,
                    'story_id': story_id,
                    'reaction_type': 'like',
                    'timestamp': datetime.now().isoformat()
                }
                db.collection('story_likes').add(like_data)
            except Exception as e:
                logger.warning(f"Failed to track like: {str(e)}")
        
        return jsonify({'reactions': new_reactions, 'liked': True})
    
    else:  # DELETE
        # Remove like
        new_reactions = max(0, (story_data.get('reactions', 0)) - 1)
        story_ref.update({'reactions': new_reactions})
        
        # Remove user like tracking
        if IS_TEST and 'user_id' in locals():
            try:
                likes_query = db.collection('story_likes').where('user_id', '==', user_id).where('story_id', '==', story_id)
                for like_doc in likes_query.stream():
                    like_doc.reference.delete()
            except Exception as e:
                logger.warning(f"Failed to remove like tracking: {str(e)}")
        
        return jsonify({'reactions': new_reactions, 'liked': False})

@app.route('/api/stories/<string:story_id>/reactions', methods=['POST', 'DELETE'])
def handle_story_reactions(story_id):
    """Handle multiple reaction types (like, love, laugh, fire, handshake, mind_blown)"""
    # In test environment, require authentication
    if IS_TEST:
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please register or login to react to stories.'
            }), 401
        
        # Verify user exists
        try:
            user_doc = db.collection('test_users').document(user_id).get()
            if not user_doc.exists:
                return jsonify({'error': 'Invalid user'}), 401
        except Exception as e:
            return jsonify({'error': 'Authentication failed'}), 401
    
    if db is None:
        return jsonify({'error': 'Database not available'}), 500
    
    # Get the story
    story_ref = db.collection('stories').document(story_id)
    story = story_ref.get()
    
    if not story.exists:
        return jsonify({'error': 'Story not found'}), 404
    
    story_data = story.to_dict()
    
    if request.method == 'POST':
        data = request.json
        reaction_type = data.get('reaction_type', 'like')
        
        # Validate reaction type
        valid_reactions = ['like', 'love', 'laugh', 'fire', 'handshake', 'mind_blown']
        if reaction_type not in valid_reactions:
            return jsonify({'error': f'Invalid reaction type. Must be one of: {valid_reactions}'}), 400
        
        # Check if user already reacted to this story
        if IS_TEST and 'user_id' in locals():
            existing_reactions = db.collection('story_reactions').where('user_id', '==', user_id).where('story_id', '==', story_id).limit(1).get()
            existing_reactions_list = list(existing_reactions)
            
            if len(existing_reactions_list) > 0:
                # User already reacted, update their reaction
                existing_reaction = existing_reactions_list[0]
                existing_data = existing_reaction.to_dict()
                old_reaction_type = existing_data.get('reaction_type', 'like')
                
                # Update the reaction
                existing_reaction.reference.update({
                    'reaction_type': reaction_type,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Update story reaction counts
                reactions = story_data.get('reaction_counts', {})
                reactions[old_reaction_type] = max(0, reactions.get(old_reaction_type, 0) - 1)
                reactions[reaction_type] = reactions.get(reaction_type, 0) + 1
                
                story_ref.update({
                    'reaction_counts': reactions,
                    'reactions': sum(reactions.values())  # Total count for compatibility
                })
                
                return jsonify({
                    'reaction_counts': reactions,
                    'total_reactions': sum(reactions.values()),
                    'user_reaction': reaction_type
                })
        
        # Add new reaction
        reactions = story_data.get('reaction_counts', {})
        reactions[reaction_type] = reactions.get(reaction_type, 0) + 1
        
        story_ref.update({
            'reaction_counts': reactions,
            'reactions': sum(reactions.values())  # Total count for compatibility
        })
        
        # Track user reaction
        if IS_TEST and 'user_id' in locals():
            try:
                reaction_data = {
                    'user_id': user_id,
                    'story_id': story_id,
                    'reaction_type': reaction_type,
                    'timestamp': datetime.now().isoformat()
                }
                db.collection('story_reactions').add(reaction_data)
            except Exception as e:
                logger.warning(f"Failed to track reaction: {str(e)}")
        
        return jsonify({
            'reaction_counts': reactions,
            'total_reactions': sum(reactions.values()),
            'user_reaction': reaction_type
        })
    
    else:  # DELETE
        # Remove user's reaction
        if IS_TEST and 'user_id' in locals():
            try:
                reactions_query = db.collection('story_reactions').where('user_id', '==', user_id).where('story_id', '==', story_id)
                user_reactions = list(reactions_query.stream())
                
                if len(user_reactions) > 0:
                    user_reaction = user_reactions[0]
                    reaction_data = user_reaction.to_dict()
                    reaction_type = reaction_data.get('reaction_type', 'like')
                    
                    # Remove the reaction
                    user_reaction.reference.delete()
                    
                    # Update story reaction counts
                    reactions = story_data.get('reaction_counts', {})
                    reactions[reaction_type] = max(0, reactions.get(reaction_type, 0) - 1)
                    
                    story_ref.update({
                        'reaction_counts': reactions,
                        'reactions': sum(reactions.values())  # Total count for compatibility
                    })
                    
                    return jsonify({
                        'reaction_counts': reactions,
                        'total_reactions': sum(reactions.values()),
                        'user_reaction': None
                    })
                else:
                    return jsonify({'error': 'No reaction found to remove'}), 404
            except Exception as e:
                logger.warning(f"Failed to remove reaction: {str(e)}")
                return jsonify({'error': 'Failed to remove reaction'}), 500
        
        return jsonify({'error': 'Authentication required'}), 401

@app.route('/api/stories/<string:story_id>/comments', methods=['GET', 'POST'])
def handle_story_comments(story_id):
    """Get or add comments for a story"""
    if db is None:
        return jsonify({'error': 'Database not available'}), 500
    
    # Verify story exists
    story_ref = db.collection('stories').document(story_id)
    story = story_ref.get()
    
    if not story.exists:
        return jsonify({'error': 'Story not found'}), 404
    
    if request.method == 'GET':
        # Get comments
        comments = []
        try:
            comments_query = db.collection('story_comments').where('story_id', '==', story_id).order_by('timestamp')
            for comment_doc in comments_query.stream():
                comment_data = comment_doc.to_dict()
                comment_data['id'] = comment_doc.id
                comments.append(comment_data)
        except Exception as e:
            logger.error(f"Error fetching comments: {str(e)}")
        
        return jsonify({'comments': comments})
    
    else:  # POST
        # Add comment - require authentication
        if IS_TEST:
            user_id = request.headers.get('X-User-ID')
            if not user_id:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Please register or login to comment on stories.'
                }), 401
            
            # Verify user exists
            try:
                user_doc = db.collection('test_users').document(user_id).get()
                if not user_doc.exists:
                    return jsonify({'error': 'Invalid user'}), 401
            except Exception as e:
                return jsonify({'error': 'Authentication failed'}), 401
        
        data = request.json
        comment_text = data.get('comment', '').strip()
        author = data.get('author', 'Anonymous')
        
        if not comment_text:
            return jsonify({'error': 'Comment cannot be empty'}), 400
        
        # Create comment
        comment_data = {
            'story_id': story_id,
            'comment': comment_text,
            'author': author,
            'timestamp': datetime.now().isoformat()
        }
        
        if IS_TEST and 'user_id' in locals():
            comment_data['user_id'] = user_id
        
        try:
            comment_ref = db.collection('story_comments').add(comment_data)
            comment_data['id'] = comment_ref[1].id
            
            # Update user statistics in test environment
            if IS_TEST and 'user_id' in locals():
                try:
                    user_ref = db.collection('test_users').document(user_id)
                    user_ref.update({'comments_posted': firestore.Increment(1)})
                except Exception as e:
                    logger.warning(f"Failed to update user statistics: {str(e)}")
            
            return jsonify({'comment': comment_data, 'message': 'Comment added successfully'})
        
        except Exception as e:
            logger.error(f"Error adding comment: {str(e)}")
            return jsonify({'error': 'Failed to add comment'}), 500

@app.route('/api/comments/<string:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    """Delete a specific comment by ID"""
    if db is None:
        return jsonify({'error': 'Database not available'}), 500
    
    # Require authentication
    if IS_TEST:
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please register or login to delete comments.'
            }), 401
        
        # Verify user exists
        try:
            user_doc = db.collection('test_users').document(user_id).get()
            if not user_doc.exists:
                return jsonify({'error': 'Invalid user'}), 401
        except Exception as e:
            return jsonify({'error': 'Authentication failed'}), 401
    
    try:
        # Get the comment to verify ownership
        comment_ref = db.collection('story_comments').document(comment_id)
        comment_doc = comment_ref.get()
        
        if not comment_doc.exists:
            return jsonify({'error': 'Comment not found'}), 404
        
        comment_data = comment_doc.to_dict()
        
        # In test environment, verify user owns the comment
        if IS_TEST and 'user_id' in locals():
            comment_user_id = comment_data.get('user_id')
            if comment_user_id and comment_user_id != user_id:
                return jsonify({
                    'error': 'Permission denied',
                    'message': 'You can only delete your own comments.'
                }), 403
        
        # Delete the comment
        comment_ref.delete()
        
        # Update user statistics in test environment
        if IS_TEST and 'user_id' in locals():
            try:
                user_ref = db.collection('test_users').document(user_id)
                user_ref.update({'comments_deleted': firestore.Increment(1)})
            except Exception as e:
                logger.warning(f"Failed to update user statistics: {str(e)}")
        
        logger.info(f"Comment {comment_id} deleted successfully by user {user_id if 'user_id' in locals() else 'unknown'}")
        return jsonify({
            'message': 'Comment deleted successfully',
            'comment_id': comment_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting comment {comment_id}: {str(e)}")
        return jsonify({'error': 'Failed to delete comment'}), 500

@app.route('/api/stories/<string:story_id>/formats/<string:format_type>', methods=['GET'])
def get_story_format(story_id, format_type):
    """Get a specific format for a story"""
    try:
        logger.info(f"Getting {format_type} format for story {story_id}")
        
        # Get story
        story_ref = db.collection('stories').document(story_id)
        story = story_ref.get()
        
        if not story.exists:
            return jsonify({'error': 'Story not found'}), 404
            
        story_data = story.to_dict()
        story_author = story_data.get('user_id')
        is_public = story_data.get('public', False)
        
        # Get requesting user ID
        user_id = request.headers.get('X-User-ID')
        
        # Check access permissions:
        # - Public stories: anyone can view formats
        # - Private stories: only the author can view formats
        if not is_public and story_author != user_id:
            logger.warning(f"Unauthorized format access attempt:")
            logger.warning(f"  - Story ID: {story_id}, Format: {format_type}")
            logger.warning(f"  - Story author: {story_author}")
            logger.warning(f"  - Requesting user: {user_id}")
            logger.warning(f"  - Story is public: {is_public}")
            return jsonify({
                'error': 'Access denied',
                'message': 'This story is private. Only the author can view its formats.'
            }), 403
        
        # Handle numeric format requests (frontend sometimes sends index)
        if format_type.isdigit():
            created_formats = story_data.get('createdFormats', [])
            if isinstance(created_formats, list) and len(created_formats) > int(format_type):
                format_type = created_formats[int(format_type)]
            else:
                return jsonify({'error': f'Format index {format_type} not found'}), 404
        
        # Get format
        formats = story_data.get('formats', {})
        if format_type not in formats:
            return jsonify({'error': f'Format {format_type} not found'}), 404
            
        format_data = formats[format_type]
        
        # Handle both string and dict format storage
        if isinstance(format_data, str):
            content = format_data
            audio_url = None
            title = None
            cover_url = None
        else:
            content = format_data.get('content', format_data)
            audio_url = format_data.get('audio_url')
            title = format_data.get('title')
            cover_url = format_data.get('cover_url')
        
        response_payload = {
            'format_type': format_type,
            'content': content,
            'audio_url': audio_url,
            'title': title,
            'story_id': story_id,
            'created_at': story_data.get('updated_at', story_data.get('created_at'))
        }
        if cover_url:
            response_payload['cover_url'] = cover_url
        
        return jsonify(response_payload), 200
        
    except Exception as e:
        logger.error(f"Error getting format: {e}")
        return jsonify({'error': 'Failed to get format'}), 500

@app.route('/api/stories/<string:story_id>/formats/<string:format_type>', methods=['PUT'])
def update_story_format(story_id, format_type):
    """Update/edit a specific format for a story"""
    try:
        data = request.json
        new_content = data.get('content', '')
        user_id = data.get('user_id') or request.headers.get('X-User-ID')
        
        logger.info(f"Updating {format_type} format for story {story_id}")
        logger.info(f"User ID: {user_id}")
        
        if not new_content.strip():
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        # Require authentication
        if is_anonymous_user(user_id):
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please sign in to edit formats.'
            }), 401
        
        # Get story
        story_ref = db.collection('stories').document(story_id)
        story = story_ref.get()
        
        if not story.exists:
            return jsonify({'error': 'Story not found'}), 404
            
        story_data = story.to_dict()
        story_author = story_data.get('user_id')
        
        user_email = request.headers.get('X-User-Email', '')
        # Check if the requesting user is the author of the story or super user
        if story_author != user_id and not is_super_user(user_id, user_email):
            logger.warning(f"Unauthorized format edit attempt:")
            logger.warning(f"  - Story ID: {story_id}")
            logger.warning(f"  - Story author: {story_author}")
            logger.warning(f"  - Requesting user: {user_id}")
            return jsonify({
                'error': 'Access denied',
                'message': 'Only the story author can edit formats.'
            }), 403
        
        # Update the format
        formats = story_data.get('formats', {})
        
        if format_type not in formats:
            return jsonify({'error': f'Format {format_type} not found'}), 404
        
        # Handle both string and dict format storage
        if isinstance(formats[format_type], dict):
            # Preserve existing metadata (like audio_url, created_at) but update content
            formats[format_type]['content'] = new_content
            formats[format_type]['updated_at'] = datetime.now().isoformat()
        else:
            # Simple string format, just update the content
            formats[format_type] = new_content
        
        # Update the story with new format content
        story_ref.update({
            'formats': formats,
            'updated_at': datetime.now().isoformat()
        })
        
        logger.info(f"Successfully updated {format_type} format for story {story_id}")
        
        return jsonify({
            'success': True,
            'message': 'Format updated successfully',
            'format_type': format_type,
            'content': new_content,
            'updated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating format: {e}")
        return jsonify({'error': 'Failed to update format'}), 500

@app.route('/api/stories/<string:story_id>/generate-format', methods=['POST'])
def generate_format_for_story(story_id):
    """Generate a new format for an existing story using the FormatsGenerationEngine"""
    try:
        data = request.json
        format_type_str = data.get('format_type', 'article')
        user_id = request.headers.get('X-User-ID')
        user_email = request.headers.get('X-User-Email', '')
        
        # Enhanced logging for debugging authentication issues
        logger.info(f"Format generation request for story {story_id}:")
        logger.info(f"  - Format type: {format_type_str}")
        logger.info(f"  - User ID from header: '{user_id}'")
        logger.info(f"  - User ID type: {type(user_id)}")
        logger.info(f"  - All headers: {dict(request.headers)}")
        
        # Require authentication for format generation
        if is_anonymous_user(user_id):
            logger.warning(f"Authentication failed for format generation:")
            logger.warning(f"  - User ID: '{user_id}'")
            logger.warning(f"  - Is None: {user_id is None}")
            logger.warning(f"  - Is anonymous: {is_anonymous_user(user_id)}")
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please sign in to generate story formats.',
                'debug_info': {
                    'user_id_received': user_id,
                    'user_id_type': str(type(user_id)),
                    'headers_received': list(request.headers.keys())
                }
            }), 401
        
        logger.info(f"Authentication successful - Generating {format_type_str} format for story {story_id}")
        
        # Validate format type
        try:
            from format_types import FormatType
            format_type = FormatType(format_type_str)
        except ValueError:
            return jsonify({'error': f'Invalid format type: {format_type_str}'}), 400
        
        # Get the original story
        if db is None:
            return jsonify({'error': 'Database not available'}), 500
            
        story_ref = db.collection('stories').document(story_id)
        story = story_ref.get()
        
        if not story.exists:
            return jsonify({'error': 'Story not found'}), 404
        
        story_data = story.to_dict()
        story_content = story_data.get('content', '')
        story_author = story_data.get('user_id')
        
        # Check if the requesting user is the author of the story or super user
        if story_author != user_id and not is_super_user(user_id, user_email):
            logger.warning(f"Unauthorized format generation attempt:")
            logger.warning(f"  - Story ID: {story_id}")
            logger.warning(f"  - Story author: {story_author}")
            logger.warning(f"  - Requesting user: {user_id}")
            return jsonify({
                'error': 'Access denied',
                'message': 'Only the story author can generate additional formats.',
                'debug_info': {
                    'story_author': story_author,
                    'requesting_user': user_id
                }
            }), 403
        
        if not story_content:
            return jsonify({'error': 'Story has no content to format'}), 400
        
        # Get user context for better generation
        user_context = None
        domain_insights = None
        
        try:
            # Try to get enhanced context if engines are available
            if 'personal_context_mapper' in globals():
                user_context = personal_context_mapper.get_user_context_profile(user_id)
            if 'knowledge_engine' in globals():
                domain_insights = knowledge_engine.analyze_story_for_insights(story_content, user_id)
        except Exception as e:
            logger.warning(f"Could not get enhanced context: {e}")
        
        # Generate the format using the engine
        result = formats_generation_engine.generate_format(
            story_content=story_content,
            format_type=format_type,
            user_context=user_context,
            domain_insights=domain_insights
        )
        
        if result.get('success'):
            # Save the format to the story
            formats = story_data.get('formats', {})
            
            # For song format, preserve existing audio_url if it exists
            if format_type_str == 'song' and format_type_str in formats:
                existing_format = formats[format_type_str]
                if isinstance(existing_format, dict) and 'audio_url' in existing_format:
                    # Preserve the uploaded audio when regenerating song content
                    song_title = result.get('title')
                    if not song_title:
                        # Generate a fallback title if none was extracted
                        song_title = "Finding Purpose in Work"  # Better fallback for now
                    
                    formats[format_type_str] = {
                        'content': result['content'],
                        'audio_url': existing_format['audio_url'],
                        'created_at': existing_format.get('created_at', datetime.now().isoformat()),
                        'title': song_title
                    }
                else:
                    # No existing audio, but still add title for song format
                    song_title = result.get('title', 'Generated Song')
                    formats[format_type_str] = {
                        'content': result['content'],
                        'title': song_title,
                        'created_at': datetime.now().isoformat()
                    }
            else:
                formats[format_type_str] = result['content']
            
            # Update createdFormats list - ensure it's always a list
            created_formats = story_data.get('createdFormats', [])
            if isinstance(created_formats, dict):
                # Convert dict to list if needed
                created_formats = list(created_formats.keys()) if created_formats else []
            elif not isinstance(created_formats, list):
                created_formats = []
                
            if format_type_str not in created_formats:
                # All therapeutic formats go at the very top of the list
                therapeutic_formats = ['reflection', 'insights', 'growth_summary', 'journal_entry']
                
                if format_type_str in therapeutic_formats:
                    # Find the position where this therapeutic format should be inserted
                    # We want to maintain order within therapeutic formats but keep them all at the top
                    insert_position = 0
                    
                    # Count existing therapeutic formats to maintain their relative order
                    for i, existing_format in enumerate(created_formats):
                        if existing_format in therapeutic_formats:
                            insert_position = i + 1
                        else:
                            # Hit first non-therapeutic format, stop counting
                            break
                    
                    created_formats.insert(insert_position, format_type_str)
                else:
                    # Regular formats go after all therapeutic formats
                    created_formats.append(format_type_str)
            
            # Update the story in database
            story_ref.update({
                'formats': formats,
                'createdFormats': created_formats,
                'updated_at': datetime.now().isoformat()
            })
            
            logger.info(f"Successfully generated {format_type_str} format for story {story_id}")
            
            return jsonify({
                'success': True,
                'format_type': format_type_str,
                'content': result['content'],
                'generation_method': result.get('generation_method', 'unknown'),
                'word_count': result.get('word_count', 0),
                'character_count': result.get('character_count', 0),
                'model_used': result.get('model_used'),
                'generated_at': result.get('generated_at')
            }), 200
        else:
            logger.error(f"Format generation failed: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result.get('error', 'Format generation failed'),
                'format_type': format_type_str
            }), 500
            
    except Exception as e:
        logger.error(f"Error in format generation endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/chat/message', methods=['POST'])
def process_chat_message():
    """Process a chat message with intelligent conversation summarization"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        user_id = data.get('user_id')
        conversation_history = data.get('conversation_history', [])
        
        if not message or not user_id:
            return jsonify({'error': 'Message and user_id are required'}), 400
        
        # Reject anonymous users - require authentication for chat
        if is_anonymous_user(user_id):
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please sign in to start chatting. Create an account to save your conversations and stories.'
            }), 401
        
        logger.info(f"Processing chat message for user {user_id}")
        
        # Calculate conversation length (needed for both OpenAI and fallback paths)
        conversation_length = len(conversation_history)
        
        # Ensure the SentimentalApp OpenAI key is active for this request (MentalOS may have changed it)
        _sent_key = os.getenv('OPENAI_API_KEY')
        if _sent_key and _sent_key.startswith('sk-') and openai.api_key != _sent_key:
            openai.api_key = _sent_key
        
        # Generate AI response
        if openai.api_key:
            try:
                # Build conversation context with intelligent summarization
                system_prompt = prompts_engine.get_conversation_prompt(PromptType.DISCOVERY)
                messages = [{"role": "system", "content": system_prompt}]
                
                # Enhanced conversation management with summarization
                max_context_tokens = 2000  # Reserve tokens for system prompt and response
                context_messages = []
                current_tokens = 0
                
                # Estimate tokens (rough: 1 token ≈ 4 characters)
                def estimate_tokens(text):
                    return len(str(text)) // 4
                
                # Apply intelligent conversation summarization for very long conversations
                if conversation_length > 30:
                    logger.info(f"Long conversation detected ({conversation_length} messages), applying summarization")
                    
                    try:
                        # Create a comprehensive conversation summary that maintains topic coherence
                        summary_messages = []
                        
                        # Always preserve the first few messages (conversation foundation)
                        foundation_messages = conversation_history[:3]
                        summary_messages.extend(foundation_messages)
                        
                        # Identify conversation phases for targeted summarization
                        middle_start = 3
                        middle_end = max(middle_start, conversation_length - 12)  # Keep last 12 messages intact
                        
                        if middle_end > middle_start:
                            # Split middle section into chunks for progressive summarization
                            middle_section = conversation_history[middle_start:middle_end]
                            chunk_size = 8  # Process 8 messages at a time
                            
                            for i in range(0, len(middle_section), chunk_size):
                                chunk = middle_section[i:i + chunk_size]
                                if len(chunk) >= 4:  # Only summarize substantial chunks
                                    chunk_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in chunk])
                                    
                                    # Create contextual summary that preserves topic flow
                                    summary_response = openai.ChatCompletion.create(
                                        model="gpt-3.5-turbo",
                                        messages=[
                                            {"role": "system", "content": """Create a flowing summary that captures:
1. Key topics and emotional themes discussed
2. Important insights or breakthroughs shared
3. Questions or concerns raised
4. The natural progression of the conversation

Keep the summary conversational and preserve the user's voice. Focus on continuity and topic coherence."""},
                                            {"role": "user", "content": f"Summarize this conversation section while maintaining topic flow:\n\n{chunk_text}"}
                                        ],
                                        max_tokens=120,
                                        temperature=0.2
                                    )
                                    
                                    summary_content = summary_response.choices[0].message.content.strip()
                                    summary_messages.append({
                                        "role": "system",
                                        "content": f"[Conversation summary]: {summary_content}"
                                    })
                                else:
                                    # Keep smaller chunks as-is
                                    summary_messages.extend(chunk)
                        
                        # Always include recent messages (last 12) to maintain immediate context
                        recent_messages = conversation_history[-12:]
                        summary_messages.extend(recent_messages)
                        
                        # Use summarized conversation as context
                        processed_history = summary_messages
                        
                        logger.info(f"Conversation summarized: {conversation_length} → {len(processed_history)} messages")
                        
                    except Exception as e:
                        logger.warning(f"Summarization failed, using recent messages only: {e}")
                        # Fallback: use recent messages only
                        processed_history = conversation_history[-15:]
                else:
                    # Standard processing for shorter conversations
                    processed_history = conversation_history
                
                # Apply token-based context management to processed history
                for msg in processed_history:
                    msg_tokens = estimate_tokens(msg.get('content', ''))
                    if current_tokens + msg_tokens < max_context_tokens:
                        context_messages.append(msg)
                        current_tokens += msg_tokens
                    else:
                        # If we run out of space, prioritize the most recent messages
                        context_messages = context_messages[-10:] + [msg]
                        break
                
                # Add context messages to prompt
                for msg in context_messages:
                    messages.append({
                        "role": msg.get('role', 'user'),
                        "content": msg.get('content', '')
                    })
                
                # Add current message
                messages.append({"role": "user", "content": message})
                
                # Generate response with enhanced context
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=300,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content.strip()
                
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                return jsonify({'error': 'Sorry, I cannot connect to the AI system right now. Please try again later.'}), 500
        else:
            return jsonify({'error': 'AI system is not available. Please try again later.'}), 500
        
        # Check if this conversation is ready for story generation
        full_conversation = conversation_history + [
            {'role': 'user', 'content': message, 'timestamp': datetime.now().isoformat()},
            {'role': 'assistant', 'content': ai_response, 'timestamp': datetime.now().isoformat()}
        ]
        
        # Detect if story should be generated - only when user explicitly requests it
        should_generate_story = False
        story_indicators = [
            "turn this into something",
            "turn this into a story",
            "create a story",
            "make this a story",
            "save this as a story",
            "story from this",
            "remember this conversation",
            "keep this conversation",
            "save this chat"
        ]
        
        if any(indicator in message.lower() for indicator in story_indicators):
            should_generate_story = True
        
        result = {
            'success': True,
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add summarization info for debugging/monitoring
        if conversation_length > 30:
            result['conversation_summarized'] = True
            result['original_length'] = conversation_length
            result['processed_length'] = len(context_messages)
        
        # Generate story if appropriate
        if should_generate_story:
            try:
                story_result = generate_story_from_conversation(user_id, full_conversation)
                if story_result:
                    result['story_created'] = True
                    result['story'] = story_result
                    logger.info(f"Story generated for user {user_id}")
            except Exception as e:
                logger.error(f"Story generation error: {e}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stories/generate', methods=['POST'])
def generate_story_endpoint():
    """Direct endpoint to generate a story from conversation data"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        conversation = data.get('conversation', [])
        title_suggestion = data.get('title')
        is_public = data.get('is_public', False)  # Default to private
        
        if not user_id or not conversation:
            return jsonify({'error': 'user_id and conversation are required'}), 400
        
        # Reject anonymous users - require authentication for story creation
        if is_anonymous_user(user_id):
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please sign in to create stories. Create an account to save your stories and access them later.'
            }), 401
        
        logger.info(f"Generating story from conversation for user {user_id}")
        
        story_result = generate_story_from_conversation(user_id, conversation, title_suggestion, is_public)
        
        if story_result:
            return jsonify({
                'success': True,
                'story': story_result
            })
        else:
            return jsonify({'error': 'Failed to generate story'}), 500
            
    except Exception as e:
        logger.error(f"Error in story generation endpoint: {e}")
        return jsonify({'error': str(e)}), 500

def generate_story_from_conversation(user_id, conversation, title_suggestion=None, is_public=False):
    """Generate a story from conversation data using sophisticated AI prompts"""
    try:
        # Extract user messages for story content
        user_messages = [msg for msg in conversation if msg.get('role') == 'user']
        if not user_messages:
            return None
        
        # Get user info - FIX: Look in test_users collection for test environment
        if IS_TEST:
            user_ref = db.collection('test_users').document(user_id)
        else:
            user_ref = db.collection('users').document(user_id)
            
        user_doc = user_ref.get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        
        # If user not found, use basic fallback
        if not user_data:
            logger.warning(f"User {user_id} not found in database, using fallback")
            user_data = {'name': 'Anonymous User', 'email': 'unknown@example.com'}
        
        # Filter out meta-instructions and bot feedback from user messages
        def is_meta_instruction(content):
            """Detect if a message is instruction to the bot rather than story content"""
            if not content:
                return True
                
            content_lower = content.lower().strip()
            
            # Common meta-instruction patterns
            meta_patterns = [
                'don\'t use the same',
                'don\'t repeat',
                'stop using',
                'please don\'t',
                'can you avoid',
                'try not to',
                'don\'t say',
                'be more specific',
                'be less',
                'change your tone',
                'speak differently',
                'respond with',
                'answer in',
                'use different words',
                'vary your language',
                'that sounds too',
                'make it more',
                'make it less',
                'write better',
                'improve your',
                'your response',
                'that response',
                'rephrase',
                'rewrite'
            ]
            
            # Check if message is giving feedback about bot behavior
            for pattern in meta_patterns:
                if pattern in content_lower:
                    return True
            
            # Very short messages that are likely feedback
            if len(content.strip()) < 10 and any(word in content_lower for word in ['ok', 'good', 'better', 'yes', 'no', 'thanks']):
                return True
                
            return False
        
        # Filter user messages to keep only actual story content
        story_content_messages = [
            msg for msg in user_messages 
            if not is_meta_instruction(msg.get('content', ''))
        ]
        
        # If we filtered out too much, fall back to all messages
        if len(story_content_messages) < len(user_messages) * 0.3:  # Keep at least 30% of messages
            story_content_messages = user_messages
        
        # Prepare conversation data for sophisticated analysis
        conversation_text = "\n".join([f"User: {msg.get('content', '')}" for msg in story_content_messages])
        
        # Get user context using PersonalContextMapper
        user_context = {}
        try:
            user_context = personal_context_mapper.get_user_context_profile(user_id)
        except Exception as e:
            logger.warning(f"Could not get user context: {e}")
            user_context = {
                'primary_themes': ['personal_growth'],
                'emotional_expression_style': 'conversational',
                'engagement_level': 'medium'
            }
        
        # Get domain insights using KnowledgeEngine
        domain_insights = {}
        try:
            domain_insights = knowledge_engine.analyze_story_for_insights(conversation_text, user_id)
        except Exception as e:
            logger.warning(f"Could not get domain insights: {e}")
            domain_insights = {
                'themes': ['self_reflection'],
                'emotional_markers': ['thoughtful'],
                'domains': {'personal_growth': 0.7},
                'confidence': 0.6
            }
        
        # Generate sophisticated story using PromptsEngine
        if openai.api_key:
            try:
                # Enhanced prompt for natural story generation
                story_creation_prompt = f"""Transform this conversation into an authentic personal story. Make it sound like a real person (aged 18-28) writing about their own experience.

CONVERSATION DATA:
{conversation_text}

USER CONTEXT:
- Name: {user_data.get('name', 'Anonymous')}
- Themes: {', '.join(domain_insights.get('themes', ['growth']))}
- Style: Natural, conversational, authentic

CRITICAL INSTRUCTIONS:
1. ONLY use the actual life experiences, emotions, and events mentioned
2. IGNORE any instructions the user gave to a chatbot (like "don't use the same words", "be more specific", etc.)
3. IGNORE any feedback about conversation quality or bot responses
4. Focus on the real experiences, feelings, and situations the person shared
5. Write in first person ("I", "my", "me")
6. Use natural, conversational language - never flowery or poetic
7. Include specific details and emotions from the actual experiences
8. Show growth or insight, but don't force a "lesson"
9. Make it feel like something a real Gen Z person would write
10. Keep it between 200-400 words
11. Structure: situation → challenge/conflict → reflection/insight

EXAMPLES OF GOOD TONE:
- "I remember thinking I had everything figured out..."
- "The weird thing about this whole experience was..."
- "Looking back, I realize I was just scared of..."

Generate a story that feels authentic and relatable, focusing ONLY on the real life experiences shared:"""
                
                # Generate story with natural, authentic tone
                story_response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You create authentic, relatable personal stories that sound like real people wrote them about their own experiences. Use natural, conversational language - never poetic or overly sophisticated. Focus on making the person the hero of their own story."
                        },
                        {"role": "user", "content": story_creation_prompt}
                    ],
                    max_tokens=600,
                    temperature=0.7,
                    presence_penalty=0.1
                )
                
                story_content = story_response.choices[0].message.content.strip()
                
                # Generate natural title
                if title_suggestion:
                    title = title_suggestion
                else:
                    title_prompt = f"""Create a natural, authentic title for this personal story. Make it sound like something a real person (age 18-30) would actually write about their own experience.

Story excerpt: {story_content[:200]}...

Key themes: {', '.join(domain_insights.get('themes', ['growth'])[:2])}

Create a title that feels personal and real - NOT poetic or literary. Examples:
- "Learning to Set Boundaries"
- "Why I Finally Quit That Job"
- "My Social Media Wake-Up Call"
- "Finding My Voice in College"

Make it conversational and authentic. Generate just the title:"""

                    title_response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": title_prompt}],
                        max_tokens=30,
                        temperature=0.8
                    )
                    
                    title = title_response.choices[0].message.content.strip().strip('"').strip("'")
                
            except Exception as e:
                logger.error(f"AI story generation error: {e}")
                # Improved fallback - create a basic story structure
                story_content = f"I've been thinking about {', '.join(domain_insights.get('themes', ['my life'])[:2])} lately.\n\n"
                story_content += "Here's what's been on my mind:\n\n"
                
                for i, msg in enumerate(user_messages):
                    content = msg.get('content', '').strip()
                    if content:
                        if i == 0:
                            story_content += f"It started when {content.lower()}\n\n"
                        elif i == len(user_messages) - 1:
                            story_content += f"What I've realized is that {content}\n\n"
                        else:
                            story_content += f"{content}\n\n"
                
                story_content += "I'm still figuring things out, but I feel like I understand myself a bit better now."
                title = title_suggestion or f"Thoughts on {domain_insights.get('themes', ['Life'])[0].title()}"
        else:
            # Improved fallback when no OpenAI
            story_content = f"I've been thinking about {', '.join(domain_insights.get('themes', ['my life'])[:2])} lately.\n\n"
            story_content += "Here's what's been on my mind:\n\n"
            
            for i, msg in enumerate(user_messages):
                content = msg.get('content', '').strip()
                if content:
                    if i == 0:
                        story_content += f"It started when {content.lower()}\n\n"
                    elif i == len(user_messages) - 1:
                        story_content += f"What I've realized is that {content}\n\n"
                    else:
                        story_content += f"{content}\n\n"
            
            story_content += "I'm still figuring things out, but I feel like I understand myself a bit better now."
            title = title_suggestion or f"Thoughts on {domain_insights.get('themes', ['Life'])[0].title()}"
        
        # Create story document with rich metadata
        story_data = {
            'title': title,
            'content': story_content,
            'author': user_data.get('name', 'Anonymous'),
            'author_id': user_id,
            'user_id': user_id,  # Add explicit user_id field
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'timestamp': datetime.now().isoformat(),  # For API compatibility
            'type': 'conversation',
            'public': is_public,  # Use the provided is_public parameter
            'metadata': {
                'source': 'chat_conversation',
                'message_count': len(user_messages),
                'conversation_length': len(conversation),
                'generated_at': datetime.now().isoformat(),
                'generation_method': 'ai_enhanced' if openai.api_key else 'basic'
            },
            'privacy': 'public' if is_public else 'private',  # Set privacy based on is_public parameter
            'tags': domain_insights.get('themes', [])[:3],  # Use first 3 themes as tags
            'formats': {},
            'stats': {
                'views': 0,
                'likes': 0,
                'comments': 0
            },
            'reactions': 0,  # For API compatibility
            'inCosmos': False,  # For API compatibility
            'createdFormats': [],  # For API compatibility
            'format': 'story',  # For API compatibility
            'cosmic_insights': domain_insights.get('themes', [])  # For API compatibility
        }
        
        # Add AI analysis using SmartStoryEngine conversation analysis
        try:
            analysis = smart_story_engine.analyze_conversation_for_story_potential(conversation, user_id)
            if analysis:
                story_data['analysis'] = {
                    'story_readiness_score': analysis.get('story_readiness_score', 0.5),
                    'emotional_themes': domain_insights.get('themes', []),
                    'key_insights': domain_insights.get('emotional_markers', []),
                    'reasoning': analysis.get('reasoning', 'Generated from meaningful conversation'),
                    'ai_generated': True,
                    'themes': domain_insights.get('themes', [])  # For cosmic_insights
                }
        except Exception as e:
            logger.error(f"Story analysis error: {e}")
            # Add basic analysis for compatibility
            story_data['analysis'] = {
                'story_readiness_score': 0.7,
                'emotional_themes': domain_insights.get('themes', ['growth']),
                'themes': domain_insights.get('themes', ['growth']),
                'ai_generated': True
            }
        
        # Save to database
        story_ref = db.collection('stories').add(story_data)
        story_id = story_ref[1].id
        
        # Update the document with its ID
        story_ref[1].update({'id': story_id})
        
        # Update user statistics in test environment
        if IS_TEST:
            try:
                user_ref.update({
                    'stories_created': firestore.Increment(1),
                    'last_story_created': datetime.now().isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to update user statistics: {str(e)}")
        
        logger.info(f"Story created with sophisticated prompts: {story_id} for user {user_id}")
        
        # Return story data
        return {
            'id': story_id,
            'title': title,
            'content': story_content,
            'author': story_data['author'],
            'created_at': story_data['created_at'],
            'type': story_data['type'],
            'metadata': story_data['metadata']
        }
        
    except Exception as e:
        logger.error(f"Error generating story from conversation: {e}")
        return None

@app.route('/api/debug/stories', methods=['GET'])
def debug_stories():
    """Debug endpoint to check database contents"""
    if db is None:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        debug_info = {
            'total_stories': 0,
            'stories_list': [],
            'collections_checked': [],
            'database_status': 'connected'
        }
        
        # Check stories collection
        stories_collection = db.collection('stories')
        stories = list(stories_collection.stream())
        debug_info['total_stories'] = len(stories)
        debug_info['collections_checked'].append('stories')
        
        for story in stories:
            data = story.to_dict()
            debug_info['stories_list'].append({
                'document_id': story.id,
                'title': data.get('title', 'No title'),
                'author': data.get('author', 'No author'),
                'user_id': data.get('user_id', 'No user_id'),
                'public': data.get('public', 'Not set'),
                'is_public': data.get('is_public', 'Not set'),
                'timestamp': data.get('timestamp', 'No timestamp'),
                'content_length': len(data.get('content', '')),
                'has_conversation': 'conversation' in data,
                'has_analysis': 'analysis' in data
            })
        
        # Check test_users
        try:
            users = list(db.collection('test_users').stream())
            debug_info['test_users_count'] = len(users)
            debug_info['collections_checked'].append('test_users')
        except Exception as e:
            debug_info['test_users_error'] = str(e)
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            'error': f'Debug failed: {str(e)}',
            'database_status': 'error'
        }), 500

@app.route('/api/debug/collections', methods=['GET'])
def debug_collections():
    """Debug endpoint to check all Firebase collections"""
    if db is None:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        collections_info = {}
        
        # List of known collections to check
        known_collections = [
            'stories', 'test_users', 'users', 'conversations', 
            'chat_messages', 'story_formats', 'connections',
            'waitlist', 'user_preferences', 'analytics'
        ]
        
        for collection_name in known_collections:
            try:
                collection_ref = db.collection(collection_name)
                docs = list(collection_ref.stream())
                collections_info[collection_name] = {
                    'count': len(docs),
                    'sample_ids': [doc.id for doc in docs[:3]]  # First 3 document IDs
                }
                
                # For users collections, show some sample data
                if collection_name in ['test_users', 'users'] and docs:
                    sample_data = []
                    for doc in docs[:3]:
                        data = doc.to_dict()
                        sample_data.append({
                            'id': doc.id,
                            'email': data.get('email', 'No email'),
                            'username': data.get('username', 'No username'),
                            'created': data.get('created_at', 'No date')
                        })
                    collections_info[collection_name]['sample_data'] = sample_data
                
                # For conversations, show structure
                if collection_name == 'conversations' and docs:
                    sample_data = []
                    for doc in docs[:3]:
                        data = doc.to_dict()
                        sample_data.append({
                            'id': doc.id,
                            'user_id': data.get('user_id', 'No user_id'),
                            'message_count': len(data.get('messages', [])),
                            'last_updated': data.get('last_updated', 'No date')
                        })
                    collections_info[collection_name]['sample_data'] = sample_data
                    
            except Exception as e:
                collections_info[collection_name] = {'error': str(e)}
        
        return jsonify({
            'collections': collections_info,
            'total_collections_checked': len(known_collections)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/store-conversation', methods=['POST'])
def store_conversation_directly():
    """Debug endpoint to store conversations directly in database"""
    if db is None:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        data = request.json
        user_id = data.get('user_id')
        messages = data.get('messages', [])
        scenario = data.get('scenario', 'Direct insert')
        
        if not user_id or not messages:
            return jsonify({'error': 'user_id and messages are required'}), 400
        
        # Store conversation in database
        conversation_doc = {
            'user_id': user_id,
            'messages': messages,
            'scenario': scenario,
            'created_at': data.get('created_at', datetime.now().isoformat()),
            'message_count': len([msg for msg in messages if msg.get('role') == 'user']),
            'last_updated': datetime.now().isoformat()
        }
        
        # Add to conversations collection
        db.collection('conversations').document(f"{user_id}_conversation").set(conversation_doc)
        
        return jsonify({
            'success': True,
            'conversation_id': f"{user_id}_conversation",
            'message_count': conversation_doc['message_count']
        })
        
    except Exception as e:
        print(f"Error storing conversation: {e}")
        return jsonify({'error': str(e)}), 500

# Authentication Endpoints for Test Environment
@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """Register/sync a new user from Firebase"""
    try:
        data = request.json
        uid = data.get('uid')  # Firebase UID
        email = data.get('email', '').strip().lower()
        name = data.get('name', '')
        email_verified = data.get('emailVerified', False)
        photo_url = data.get('photoURL')
        provider = data.get('provider', 'email')
        
        if not uid or not email:
            return jsonify({'error': 'Firebase UID and email are required'}), 400
        
        if db is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Check if user already exists by EMAIL first (prevent duplicates)
        existing_users_by_email = db.collection('test_users').where('email', '==', email).limit(1).get()
        users_by_email = list(existing_users_by_email)
        
        if len(users_by_email) > 0:
            # User with this email already exists, return existing account
            user_doc = users_by_email[0]
            user_data = user_doc.to_dict()
            
            logger.info(f"User with email {email} already exists: {user_doc.id}")
            
            return jsonify({
                'user_id': user_doc.id,
                'email': user_data['email'],
                'name': user_data['name'],
                'message': 'User already exists with this email'
            }), 200
        
        # Check if user already exists by UID
        existing_users = db.collection('test_users').where('firebase_uid', '==', uid).limit(1).get()
        users_list = list(existing_users)
        
        if len(users_list) > 0:
            # User exists, update their info and return
            user_doc = users_list[0]
            user_data = user_doc.to_dict()
            
            # Update user data
            updated_data = {
                'email': email,
                'name': name or user_data.get('name', email.split('@')[0]),
                'email_verified': email_verified,
                'photo_url': photo_url,
                'last_login': datetime.now().isoformat(),
                'provider': provider
            }
            
            user_doc.reference.update(updated_data)
            
            logger.info(f"User updated: {email} -> {user_doc.id}")
            
            return jsonify({
                'user_id': user_doc.id,
                'email': email,
                'name': updated_data['name'],
                'message': 'User updated successfully'
            }), 200
        else:
            # Create new user
            user_data = {
                'firebase_uid': uid,
                'email': email,
                'name': name or email.split('@')[0],
                'email_verified': email_verified,
                'photo_url': photo_url,
                'provider': provider,
                'created_at': datetime.now().isoformat(),
                'last_login': datetime.now().isoformat(),
                'stories_created': 0,
                'formats_generated': 0,
                'conversations_count': 0
            }
            
            # Add user to database
            user_ref = db.collection('test_users').add(user_data)
            user_id = user_ref[1].id
            
            logger.info(f"New user registered: {email} -> {user_id}")
            
            return jsonify({
                'user_id': user_id,
                'email': email,
                'name': user_data['name'],
                'message': 'User created successfully'
            }), 201
        
    except Exception as e:
        logger.error(f"Error in register endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    """Login user in test environment - DEPRECATED, use Firebase authentication"""
    if not IS_TEST:
        return jsonify({'error': 'Login only available in test environment'}), 403
    
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # This endpoint is deprecated - redirect to Firebase authentication
        return jsonify({
            'error': 'Local authentication disabled', 
            'message': 'Please use Firebase authentication. If you have an existing account, it has been migrated to Firebase.',
            'firebase_login_required': True
        }), 403
        
    except Exception as e:
        logger.error(f"Error in user login: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/auth/firebase-signup', methods=['POST'])
def firebase_signup():
    """Create Firebase user account"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        name = data.get('name', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # For now, return success - actual Firebase user creation will be handled by frontend
        return jsonify({
            'message': 'Firebase signup initiated',
            'email': email,
            'name': name
        }), 200
            
    except Exception as e:
        logger.error(f"Error in firebase signup: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/auth/firebase-signin', methods=['POST'])
def firebase_signin():
    """Sign in with Firebase"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # For now, return success - actual Firebase authentication will be handled by frontend
        return jsonify({
            'message': 'Firebase signin initiated',
            'email': email
        }), 200
            
    except Exception as e:
        logger.error(f"Error in firebase signin: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/auth/firebase-sync', methods=['POST'])
def firebase_sync():
    """Sync Firebase user with local database"""
    try:
        data = request.json
        firebase_uid = data.get('uid') or data.get('firebase_uid')  # Support both field names
        email = data.get('email', '').strip().lower()
        name = data.get('name', '')
        
        if not firebase_uid or not email:
            return jsonify({'error': 'Firebase UID and email are required'}), 400
        
        if db is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Check if user exists
        existing_users = db.collection('test_users').where('email', '==', email).limit(1).get()
        users_list = list(existing_users)
        
        if len(users_list) > 0:
            # User exists, return their info
            user_doc = users_list[0]
            user_data = user_doc.to_dict()
            return jsonify({
                'user_id': user_doc.id,
                'email': user_data['email'],
                'name': user_data['name']
            }), 200
        else:
            # Create new user
            user_data = {
                'email': email,
                'name': name or email.split('@')[0],
                'firebase_uid': firebase_uid,
                'created_at': datetime.now().isoformat(),
                'stories_created': 0,
                'formats_generated': 0
            }
            
            user_ref = db.collection('test_users').add(user_data)
            user_id = user_ref[1].id
            
            return jsonify({
                'user_id': user_id,
                'email': email,
                'name': user_data['name']
            }), 201
            
    except Exception as e:
        logger.error(f"Error in firebase sync: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/ai/providers', methods=['GET'])
def get_ai_providers():
    """Get available AI providers for the frontend"""
    try:
        providers = {
            'openai': {
                'name': 'OpenAI',
                'models': ['gpt-4', 'gpt-3.5-turbo'],
                'available': bool(os.getenv('OPENAI_API_KEY'))
            },
            'anthropic': {
                'name': 'Anthropic',
                'models': ['claude-3-sonnet', 'claude-3-haiku'],
                'available': bool(os.getenv('ANTHROPIC_API_KEY'))
            }
        }
        
        return jsonify({
            'providers': providers,
            'default': 'openai'
        })
        
    except Exception as e:
        logger.error(f"Error getting AI providers: {str(e)}")
        return jsonify({
            'providers': {
                'openai': {
                    'name': 'OpenAI',
                    'models': ['gpt-3.5-turbo'],
                    'available': False
                }
            },
            'default': 'openai'
        }), 500

@app.route('/api/formats/supported', methods=['GET'])
def get_supported_formats():
    """Get formats that are actually supported by the prompts engine"""
    try:
        # CACHE BUSTER: 2025-06-12 14:37 - Fixing Twitter->X issue
        # Only return formats that have prompts defined in prompts_engine
        # These are the formats that can actually be generated
        prompts_engine_formats = [
            'x', 'linkedin', 'instagram', 'facebook',
            'song', 'poem', 'reel', 'fairytale', 
            'reflection',
            'article', 'blog_post', 'presentation', 'newsletter', 'podcast',
            'insights', 'growth_summary', 'journal_entry', 'letter'
        ]
        
        return jsonify({
            'supported_formats': prompts_engine_formats,
            'total_count': len(prompts_engine_formats),
            'engine_available': bool(formats_generation_engine),
            'source': 'prompts_engine_FIXED',  # Cache buster
            'updated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting supported formats: {e}")
        return jsonify({'error': 'Failed to get supported formats'}), 500



@app.route('/api/admin/fix-reflection-order', methods=['POST'])
def fix_reflection_order():
    """Temporary endpoint to move all therapeutic formats to the top of the list"""
    try:
        # Get all stories from the correct collection
        stories_ref = db.collection('stories')
        stories = stories_ref.get()
        
        updated_count = 0
        total_count = 0
        
        therapeutic_formats = ['reflection', 'insights', 'growth_summary', 'journal_entry']
        
        for story_doc in stories:
            total_count += 1
            story_data = story_doc.to_dict()
            story_id = story_doc.id
            
            created_formats = story_data.get('createdFormats', [])
            
            # Check if story has any therapeutic formats
            has_therapeutic = any(f in created_formats for f in therapeutic_formats)
            
            if has_therapeutic:
                # Separate therapeutic and non-therapeutic formats
                therapeutic_in_story = [f for f in created_formats if f in therapeutic_formats]
                non_therapeutic = [f for f in created_formats if f not in therapeutic_formats]
                
                # Keep therapeutic formats in their current relative order
                therapeutic_ordered = [f for f in created_formats if f in therapeutic_formats]
                
                # New order: ALL therapeutic formats first, then other formats
                new_order = therapeutic_ordered + non_therapeutic
                
                if new_order != created_formats:
                    logger.info(f"Updating story {story_id}: {created_formats} -> {new_order}")
                    
                    # Update the story
                    story_doc.reference.update({
                        'createdFormats': new_order
                    })
                    updated_count += 1
        
        return jsonify({
            'success': True,
            'total_stories': total_count,
            'updated_stories': updated_count,
            'message': f'Moved therapeutic formats to top in {updated_count} stories'
        })
        
    except Exception as e:
        logger.error(f"Error moving therapeutic formats to top: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload/audio', methods=['POST'])
def upload_audio():
    """Upload an audio file (MP3) to Firebase Storage"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: MP3, WAV, OGG, M4A'}), 400
        
        # Get user authentication
        user_id = request.headers.get('X-User-ID')
        user_email = request.headers.get('X-User-Email', '')
        logger.info(f"Upload audio: user_id={user_id} email={user_email}")
        if is_anonymous_user(user_id):
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please sign in to upload audio files.'
            }), 401
        
        # Get story_id and format_type from form data
        story_id = request.form.get('story_id')
        format_type = request.form.get('format_type', 'song')
        
        if not story_id:
            return jsonify({'error': 'Story ID required'}), 400
        
        # Validate user owns this story
        stories_ref = db.collection('stories')
        story_doc = stories_ref.document(story_id).get()
        
        if not story_doc.exists:
            return jsonify({'error': 'Story not found'}), 404
            
        story_data = story_doc.to_dict()
        
        user_email = request.headers.get('X-User-Email', '')
        # Check if user owns this story or is super user
        if story_data.get('user_id') != user_id and story_data.get('author_id') != user_id and not is_super_user(user_id, user_email):
            return jsonify({'error': 'Permission denied - you can only upload audio to your own stories'}), 403
        
        # Generate unique filename with proper story ID
        unique_id = str(uuid.uuid4())
        original_extension = file.filename.rsplit('.', 1)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{story_id}_{format_type}_{timestamp}_{unique_id}.{original_extension}"
        
        # Upload to Firebase Storage (with fallback to local)
        try:
            if bucket is not None:
                # Firebase Storage upload
                blob = bucket.blob(f"audio/{filename}")
                
                # Upload file content
                file.seek(0)  # Reset file pointer to beginning
                blob.upload_from_file(file, content_type=f'audio/{original_extension}')
                
                # Make the blob publicly readable
                blob.make_public()
                
                # Get the public URL
                audio_url = blob.public_url
                storage_type = 'firebase'
                
                logger.info(f"Audio uploaded to Firebase Storage: {filename} by user {user_id} for story {story_id}")
                logger.info(f"Public URL: {audio_url}")
            else:
                # Fallback to local storage
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.seek(0)  # Reset file pointer to beginning
                file.save(filepath)
                audio_url = f'/static/uploads/{filename}'
                storage_type = 'local'
                
                logger.info(f"Audio uploaded to local storage (Firebase unavailable): {filename}")
            
        except Exception as storage_error:
            logger.error(f"Storage upload failed: {storage_error}")
            return jsonify({
                'error': 'Storage upload failed',
                'details': str(storage_error)
            }), 500
        
        # Update story format with Firebase Storage URL
        formats = story_data.get('formats', {})
        
        if format_type in formats:
            # Handle both string and dict format storage
            if isinstance(formats[format_type], str):
                # Convert string format to dict format
                formats[format_type] = {
                    'content': formats[format_type],
                    'audio_url': audio_url,
                    'audio_filename': filename,
                    'audio_uploaded_at': datetime.now().isoformat(),
                    'audio_uploaded_by': user_id,
                    'storage_type': storage_type,
                    'created_at': firestore.SERVER_TIMESTAMP
                }
            else:
                # Format is already a dict, update audio info
                formats[format_type]['audio_url'] = audio_url
                formats[format_type]['audio_filename'] = filename
                formats[format_type]['audio_uploaded_at'] = datetime.now().isoformat()
                formats[format_type]['audio_uploaded_by'] = user_id
                formats[format_type]['storage_type'] = storage_type
            
            # Update with user tracking
            update_data = {
                'formats': formats,
                'updated_at': datetime.now().isoformat(),
                'updated_by': user_id
            }
            stories_ref.document(story_id).update(update_data)
        else:
            # Format doesn't exist yet, create it with audio URL
            formats[format_type] = {
                'content': f'Generated {format_type} content',
                'audio_url': audio_url,
                'audio_filename': filename,
                'audio_uploaded_at': datetime.now().isoformat(),
                'audio_uploaded_by': user_id,
                'storage_type': storage_type,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            update_data = {
                'formats': formats,
                'updated_at': datetime.now().isoformat(),
                'updated_by': user_id
            }
            stories_ref.document(story_id).update(update_data)
        
        return jsonify({
            'success': True,
            'audio_url': audio_url,
            'filename': filename,
            'storage_type': storage_type,
            'message': f'Audio uploaded successfully to {storage_type.title()} Storage for {story_data.get("title", "story")}'
        })
        
    except Exception as e:
        logger.error(f"Error uploading audio: {str(e)}")
        return jsonify({'error': 'Upload failed', 'details': str(e)}), 500

@app.route('/api/stories/<string:story_id>/privacy', methods=['PUT'])
def update_story_privacy(story_id):
    """Update story privacy settings"""
    try:
        data = request.get_json()
        is_public = data.get('is_public', False)
        user_id = request.headers.get('X-User-ID')
        
        # Require authentication 
        if is_anonymous_user(user_id):
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please sign in to update story privacy.'
            }), 401
        
        if db is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get the story
        story_ref = db.collection('stories').document(story_id)
        story_doc = story_ref.get()
        
        if not story_doc.exists:
            return jsonify({'error': 'Story not found'}), 404
            
        story_data = story_doc.to_dict()
        
        # Check if user owns this story
        if story_data.get('user_id') != user_id and story_data.get('author_id') != user_id and not is_super_user(user_id, request.headers.get('X-User-Email','')):
            return jsonify({'error': 'Permission denied'}), 403
        
        # Update privacy settings
        update_data = {
            'public': is_public,
            'privacy': 'public' if is_public else 'private',
            'updated_at': datetime.now().isoformat()
        }
        
        story_ref.update(update_data)
        
        return jsonify({
            'success': True,
            'message': f"Story is now {'public' if is_public else 'private'}",
            'is_public': is_public
        })
        
    except Exception as e:
        logger.error(f"Error updating story privacy: {e}")
        return jsonify({'error': str(e)}), 500

# Code-based access control
VALID_ACCESS_CODES = {
    "UNICORN",             # Main access code
    "SENTI2025",           # Backup access code
}

# is_valid_access_code and is_demo_user functions moved to utils.py

@app.route('/api/auth/check-access-code', methods=['POST'])
def check_access_code():
    """Check if access code is valid"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        
        if is_valid_access_code(code):
            return jsonify({
                "valid": True, 
                "message": "Welcome to Sentimental! Access granted.",
                "code": code.upper()
            })
        else:
            return jsonify({
                "valid": False, 
                "message": "Invalid access code. Please contact us for early access."
            }), 403
            
    except Exception as e:
        logger.error(f"Error checking access code: {e}")
        return jsonify({"error": "Failed to check access code"}), 500

@app.route('/api/auth/verify-user-access', methods=['POST'])
def verify_user_access():
    """Verify if user has access (either valid code or demo user)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        access_code = data.get('access_code', '').strip()
        
        # Demo users always have access
        if is_demo_user(user_id):
            return jsonify({
                "access_granted": True,
                "message": "Demo user access granted",
                "user_type": "demo"
            })
        
        # Check access code
        if is_valid_access_code(access_code):
            return jsonify({
                "access_granted": True,
                "message": "Access code verified",
                "user_type": "invited"
            })
        
        return jsonify({
            "access_granted": False,
            "message": "Access code required. Sentimental is currently in early access."
        }), 403
            
    except Exception as e:
        logger.error(f"Error verifying user access: {e}")
        return jsonify({"error": "Failed to verify access"}), 500

@app.route('/api/admin/fix-story-authors', methods=['POST'])
def fix_story_authors():
    """Admin endpoint to fix story author names without authentication requirements"""
    try:
        if db is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Manual mapping of stories to correct authors
        story_author_fixes = [
            {
                'title_contains': 'My Career Reflection Journey',
                'new_author': 'Merike Sisask',
                'reason': 'Created by Merike'
            },
            {
                'title_contains': 'Thoughts on Challenge',
                'new_author': 'Lars-Erik Hion',
                'reason': 'Created by Lars-Erik'
            },
            {
                'title_contains': 'Embracing the Shadows Within',
                'new_author': 'Debug User',
                'reason': 'Test/debug story'
            },
            {
                'title_contains': 'From Confusion to Hilarity',
                'new_author': 'Demo User',
                'reason': 'Demo story'
            }
        ]
        
        # Get all stories
        stories = []
        for doc in db.collection('stories').stream():
            story_data = doc.to_dict()
            story_data['id'] = doc.id
            stories.append(story_data)
        
        updated_count = 0
        updates_made = []
        
        for fix in story_author_fixes:
            # Find matching story
            matching_story = None
            for story in stories:
                if fix['title_contains'] in story.get('title', ''):
                    matching_story = story
                    break
            
            if matching_story:
                current_author = matching_story.get('author', 'No author')
                
                # Only update if needed
                if current_author != fix['new_author']:
                    try:
                        story_ref = db.collection('stories').document(matching_story['id'])
                        update_data = {
                            'author': fix['new_author'],
                            'updated_at': datetime.now().isoformat()
                        }
                        story_ref.update(update_data)
                        
                        updates_made.append({
                            'title': matching_story['title'],
                            'old_author': current_author,
                            'new_author': fix['new_author'],
                            'reason': fix['reason']
                        })
                        updated_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to update story {matching_story['id']}: {e}")
        
        logger.info(f"Admin fix: Updated {updated_count} story authors")
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'updates_made': updates_made,
            'message': f'Successfully updated {updated_count} story authors'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in admin fix endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/fix-marko-user', methods=['POST'])
def fix_marko_user():
    """Temporary endpoint to fix Marko's user authentication"""
    try:
        return jsonify({
            'success': True,
            'user_id': '4wySrfiOLvZeGXCGJ85Z',
            'email': 'marko@sentimental.app',
            'name': 'Marko Vaik',
            'message': 'Use this user data'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug')
def debug_page():
    """Debug page to test user authentication"""
    return send_from_directory('.', 'debug_user_state.html')

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded audio files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# locate helper functions near line 30 maybe after imports
SUPER_USER_ID = os.getenv('SUPER_USER_ID', 'TCoWwyV0sMlNiFQgLuXR')
SUPER_USER_EMAIL = os.getenv('SUPER_USER_EMAIL', 'vaikmarko@gmail.com')

def is_super_user(user_id: str, user_email: str | None = None) -> bool:
    if user_id == SUPER_USER_ID:
        return True
    if user_email and user_email.lower() == SUPER_USER_EMAIL.lower():
        return True
    return False

@app.route('/api/users/<string:user_id>/generate-book-chapter', methods=['POST'])
def generate_book_chapter(user_id):
    """Generate a book chapter once user has at least 5 stories."""
    try:
        requester_id = request.headers.get('X-User-ID')
        requester_email = request.headers.get('X-User-Email', '')

        if is_anonymous_user(requester_id):
            return jsonify({'error': 'Authentication required'}), 401

        # Only the user themselves or super user can trigger
        if requester_id != user_id and not is_super_user(requester_id, requester_email):
            return jsonify({'error': 'Access denied'}), 403

        if db is None:
            return jsonify({'error': 'Database unavailable'}), 500

        # Fetch user stories
        stories_query = db.collection('stories').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        stories_list = [doc.to_dict() for doc in stories_query]

        if len(stories_list) < 5:
            return jsonify({'error': 'Need at least 5 stories to unlock'}), 403

        top_stories = stories_list[:5]
        stories_markdown = "\n\n".join([f"### {s.get('title','Story')}\n{s.get('content','')}" for s in top_stories])

        from format_types import FormatType
        result = formats_generation_engine.generate_format(
            story_content='',
            format_type=FormatType.BOOK_CHAPTER,
            stories_markdown=stories_markdown
        )

        if not result.get('success'):
            return jsonify(result), 500

        # Save into user_compilations collection
        db.collection('user_compilations').document(user_id).set({
            'book_chapter': result['content'],
            'updated_at': datetime.now().isoformat()
        }, merge=True)

        return jsonify({'success': True, 'content': result['content']}), 200

    except Exception as e:
        logger.error(f"Error generating book chapter: {e}")
        return jsonify({'error': str(e)}), 500

# -------------------------------------------------------
# Public share short-links (redirect to SPA with query params)
# e.g.  /s/123           → /app?story=123
#       /s/123/podcast   → /app?story=123&format=podcast
# -------------------------------------------------------


@app.route('/s/<string:story_id>', defaults={'format_type': None})
@app.route('/s/<string:story_id>/<string:format_type>')
def short_link(story_id, format_type):
    """Generate a simple, share-friendly URL that redirects to the SPA with the
    required query parameters so the front-end can open the story (and format)."""
    target = f"/app?story={story_id}"
    if format_type:
        target += f"&format={format_type}"
    return redirect(target, code=302)

# ------------------ New Image Upload Endpoint ------------------

@app.route('/api/upload/image', methods=['POST'])
def upload_image():
    """Upload an image (JPG/PNG/WEBP) and optionally attach it to an Instagram format."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: JPG, JPEG, PNG, WEBP'}), 400

        # Auth check
        user_id = request.headers.get('X-User-ID')
        user_email = request.headers.get('X-User-Email', '')
        logger.info(f"Upload image: user_id={user_id} email={user_email}")
        if is_anonymous_user(user_id):
            return jsonify({'error': 'Authentication required', 'message': 'Please sign in to upload images.'}), 401

        story_id = request.form.get('story_id')
        format_type = request.form.get('format_type', 'instagram')

        # Generate filename
        unique_id = str(uuid.uuid4())
        original_extension = file.filename.rsplit('.', 1)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{story_id or 'standalone'}_{format_type}_{timestamp}_{unique_id}.{original_extension}"

        # Upload to Firebase Storage or local
        try:
            if bucket is not None:
                blob = bucket.blob(f"images/{filename}")
                file.seek(0)
                blob.upload_from_file(file, content_type=f'image/{original_extension}')
                blob.make_public()
                image_url = blob.public_url
                storage_type = 'firebase'
            else:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.seek(0)
                file.save(filepath)
                image_url = f'/static/uploads/{filename}'
                storage_type = 'local'
        except Exception as storage_error:
            logger.error(f"Image storage failed: {storage_error}")
            return jsonify({'error': 'Storage upload failed', 'details': str(storage_error)}), 500

        # Optionally attach to story format
        if story_id:
            try:
                story_ref = db.collection('stories').document(story_id)
                story_doc = story_ref.get()
                if story_doc.exists:
                    story_data = story_doc.to_dict()

                    # Permission: owner or super user
                    if story_data.get('user_id') != user_id and story_data.get('author_id') != user_id and not is_super_user(user_id, user_email):
                        return jsonify({'error': 'Permission denied - you can only update your own stories'}), 403

                    formats = story_data.get('formats', {})
                    if format_type not in formats or not isinstance(formats[format_type], dict):
                        formats[format_type] = {'content': formats.get(format_type, '')}

                    formats[format_type]['cover_url'] = image_url
                    formats[format_type]['updated_at'] = datetime.now().isoformat()

                    story_ref.update({'formats': formats, 'updated_at': datetime.now().isoformat()})
                else:
                    logger.warning(f"Story {story_id} not found while attaching image")
            except Exception as e:
                logger.error(f"Failed to attach image to story {story_id}: {e}")

        return jsonify({'success': True, 'image_url': image_url, 'storage_type': storage_type}), 200

    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return jsonify({'error': 'Upload failed', 'details': str(e)}), 500

# =============================================================================
# MentalOS – File helper utilities
# =============================================================================

BASE_MENTALOS_DIR = os.path.join('MentalOS', 'user_data')
os.makedirs(BASE_MENTALOS_DIR, exist_ok=True)


def _sanitize_subpath(path: str) -> str:
    """Sanitize a relative file path so it cannot escape the user directory."""
    if path is None:
        raise ValueError("Path cannot be None")
    # Normalize and strip leading slashes
    normalized = os.path.normpath(path).lstrip(os.sep)
    # Disallow parent traversal
    if normalized.startswith('..') or '..' + os.sep in normalized:
        raise ValueError("Invalid path")
    return normalized


def _get_user_dir(user_id: str) -> str:
    """Return (and create if absent) the directory for a MentalOS user."""
    user_safe = secure_filename(str(user_id)) or 'anonymous'
    user_dir = os.path.join(BASE_MENTALOS_DIR, user_safe)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def open_file_fs(user_id: str, path: str) -> str:
    """Open and return the contents of a MentalOS file. Returns empty string if not found."""
    rel = _sanitize_subpath(path)
    abs_path = os.path.join(_get_user_dir(user_id), rel)
    if not os.path.exists(abs_path):
        return ""
    with open(abs_path, 'r', encoding='utf-8') as f:
        return f.read()


def append_file_fs(user_id: str, path: str, text: str) -> str:
    """Append text to a MentalOS file (creates it and parent dirs if needed)."""
    rel = _sanitize_subpath(path)
    abs_path = os.path.join(_get_user_dir(user_id), rel)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, 'a', encoding='utf-8') as f:
        f.write(text)
        if not text.endswith('\n'):
            f.write('\n')
    return "OK"


def overwrite_file_fs(user_id: str, path: str, text: str) -> str:
    """Overwrite (or create) a MentalOS file with provided text."""
    rel = _sanitize_subpath(path)
    abs_path = os.path.join(_get_user_dir(user_id), rel)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(text)
    return "OK"


# =============================================================================
# MentalOS – Chat endpoint (AI-powered with function calling)
# =============================================================================

@app.route('/api/mental-os/files/<path:filename>', methods=['GET'])
def get_mental_os_file(filename):
    """Get the content of a MentalOS file without triggering AI processing."""
    try:
        user_id = request.headers.get('X-User-ID') or request.args.get('user_id') or 'anonymous'
        content = open_file_fs(user_id, filename)
        return jsonify({'content': content, 'path': filename})
    except Exception as e:
        logger.error(f"Error reading MentalOS file {filename}: {e}")
        return jsonify({'error': str(e), 'content': ''}), 500

def build_user_knowledge_model(user_id: str) -> dict:
    """Aggregate all user files into a unified knowledge model: {filename: content}"""
    user_dir = _get_user_dir(user_id)
    knowledge = {}
    for root, _, files in os.walk(user_dir):
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), user_dir)
            try:
                with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                    content = file.read()
                    knowledge[rel_path] = content
            except Exception as e:
                knowledge[rel_path] = f"ERROR: {e}"
    return knowledge

# Add a utility to generate a patch prompt and apply a minimal patch

def propose_patch_with_llm(user_message, file_content):
    """Ask the LLM to propose a minimal patch (find/replace) for the file given the user message."""
    system_prompt = (
        "You are a context-aware agent. Given the following file and the user's message, propose a minimal patch to update only the new information. "
        "Return ONLY a JSON object with 'find' (the exact string to replace) and 'replace' (the new string), or an empty object if no change is needed. Do not return the full file."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"User message: {user_message}\n\nFile content:\n{file_content}"}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-1106",
            messages=messages,
            max_tokens=200,
            temperature=0.3,
        )
        import json
        patch = json.loads(response.choices[0].message.content.strip())
        return patch
    except Exception as e:
        return {}

def propose_unified_diff_with_llm(user_message, file_content):
    """Ask the LLM to propose a unified diff for the file given the user message."""
    system_prompt = (
        "You are a context-aware agent. Given the following file and the user's message, propose a minimal unified diff (in standard unified diff format) to update only the new information. "
        "Return ONLY the unified diff as plain text. Do not return the full file or any explanation."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"User message: {user_message}\n\nFile content:\n{file_content}"}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-1106",
            messages=messages,
            max_tokens=400,
            temperature=0.3,
        )
        diff = response.choices[0].message.content.strip()
        return diff
    except Exception as e:
        return ""

@app.route('/api/mental-os/chat/message', methods=['POST'])
def process_mental_chat_message():
    """Endpoint for MentalOS Therapist Bot that can read/write user markdown files."""
    try:
        data = request.get_json(force=True)
        # Front-end now sends the currently active file and list of open files for richer context
        active_file = data.get('active_file')
        open_files_ctx = data.get('open_files') or []
        missing_fields = data.get('missing_fields') or []
        # Compute missing fields here if front-end did not supply them
        if (not missing_fields) and active_file:
            current_content = file_contents.get(active_file, '')
            if not current_content:
                try:
                    current_content = open_file_fs(user_id, active_file)
                except Exception:
                    pass
            missing_fields = compute_missing_fields(active_file, current_content)

        user_id = data.get('user_id') or request.headers.get('X-User-ID') or 'anonymous'
        if 'messages' in data:
            messages = data['messages']
        else:
            history = data.get('conversation_history', [])
            messages = history.copy()
            incoming = data.get('message')
            if incoming:
                messages.append({"role": "user", "content": incoming})
        if not messages:
            return jsonify({'error': 'No messages provided'}), 400

        mental_api_key = os.getenv('MENTALOS_OPENAI_API_KEY')
        if mental_api_key:
            openai.api_key = mental_api_key
        elif not openai.api_key:
            return jsonify({
                'error': 'OpenAI API key not configured',
                'ai_response': '🔑 **API Key Missing**\n\nI need a valid OpenAI API key to operate. Please add your key to the `.env` file as `MENTALOS_OPENAI_API_KEY=<your-key>` and restart the server.',
                'setup_required': True
            }), 200

        user_dir = _get_user_dir(user_id)
        logger.info(f"MentalOS: User directory for {user_id}: {user_dir}")
        existing_files = []
        file_contents = {}
        for root, _, files in os.walk(user_dir):
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), user_dir)
                existing_files.append(rel_path)
                try:
                    with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                        content = file.read()
                        file_contents[rel_path] = content
                except:
                    file_contents[rel_path] = ''
        logger.info(f"MentalOS: Found files for user {user_id}: {existing_files}")

        user_message = ''
        for m in reversed(messages):
            if m.get('role') == 'user':
                user_message = m.get('content', '')
                break

        # If the user just answered a placeholder question, patch it directly instead of relying on the LLM diff
        diffs_applied = []
        direct_patch_done = False
        if active_file and missing_fields:
            # Try each missing field until we manage to extract a plausible value
            for candidate_field in missing_fields:
                entry = KNOWLEDGE_MAP.get(active_file, {})
                placeholder = entry.get('fields', {}).get(candidate_field)
                if not placeholder:
                    continue
                if active_file not in file_contents:
                    continue

                from patch_engine import replace_placeholder
                import re as _re

                value: str | None = None
                lowered_field = candidate_field.lower()

                if lowered_field == 'name':
                    # Only capture the name when the user explicitly states it to avoid mis-classifying locations.
                    m_val = _re.search(r"\b(?:my\s+name\s+is|i(?:'|\s*a)?m)\s+([A-Z][a-zA-Z]+)\b", user_message, flags=_re.IGNORECASE)
                    if m_val:
                        value = m_val.group(1).strip()
                    # No fallback – skip updating Name if we don't have a clear signal

                elif 'age' in lowered_field:
                    m_age = _re.search(r"\b(\d{1,3})\b", user_message)
                    if m_age and 0 < int(m_age.group(1)) < 120:
                        value = m_age.group(1)
                elif 'location' in lowered_field:
                    # Look for a phrase like "in Paris" or just a capitalised city/country combo
                    m_loc = _re.search(r"\b(?:in|at|from)\s+([A-Z][A-Za-z\s,]{2,40})", user_message)
                    if m_loc:
                        cand = m_loc.group(1).strip().strip('.')
                        # collapse extra spaces
                        cand = _re.sub(r"\s{2,}", " ", cand)
                        value = cand if 1 <= len(cand.split()) <= 6 else None
                    else:
                        # Fallback: use last capitalised phrase if it contains a comma (City, Country)
                        caps = _re.findall(r"[A-Z][A-Za-z]+(?:,\s*[A-Z][A-Za-z]+)+", user_message)
                        if caps:
                            value = caps[-1]
                elif 'current role' in lowered_field or 'role' == lowered_field:
                    m_role = _re.search(r"\b(?:i\s+am|i'm|im)\s+(?:a|an)?\s*([^.,;]+)", user_message, flags=_re.IGNORECASE)
                    if m_role:
                        raw = m_role.group(1).strip()
                        clean = raw.split(' in ')[0].title()
                        # basic sanity: 1-5 words, no digits
                        if 1 <= len(clean.split()) <= 5 and not _re.search(r"\d", clean):
                            value = clean
                elif 'relationship' in lowered_field:
                    rel_words = {'single','married','partnered','dating','engaged','divorced','separated'}
                    m_rel = _re.search(r"\b(single|married|partnered|engaged|dating|divorced|separated)\b", user_message, flags=_re.IGNORECASE)
                    if m_rel:
                        value = m_rel.group(1).capitalize()
                else:
                    # Generic fallback – use raw trimmed message.
                    value = user_message.strip() if user_message.strip() else None

                # Only patch if we extracted a plausible value and actual replacement occurred.
                if value:
                    original_content = file_contents[active_file]
                    new_content_active = replace_placeholder(original_content, placeholder, value)
                    if new_content_active != original_content:
                        overwrite_file_fs(user_id, active_file, new_content_active)
                        file_contents[active_file] = new_content_active  # keep in-memory copy fresh
                        diffs_applied.append({
                            "operation": "overwrite_file",
                            "path": active_file,
                            "snippet": new_content_active,
                            "reason": f"Filled {candidate_field}"
                        })
                        direct_patch_done = True
                        # Recompute missing fields so the follow-up question targets the next empty placeholder
                        missing_fields = compute_missing_fields(active_file, new_content_active)
                        break

        # Decide which files to patch – prioritise active_file if provided (LLM diff)
        if active_file and active_file in file_contents and not direct_patch_done:
            files_iter = [(active_file, file_contents[active_file])]
        else:
            files_iter = file_contents.items()

        for file_path, file_content in files_iter:
            diff = propose_unified_diff_with_llm(user_message, file_content)
            if diff and diff.startswith('---'):
                patch_set = patch_ng.fromstring(diff)
                patched = patch_ng.patch(file_content, patch_set)
                if patched is not None and patched != file_content:
                    overwrite_file_fs(user_id, file_path, patched)
                    diffs_applied.append({
                        "operation": "overwrite_file",
                        "path": file_path,
                        "snippet": patched,
                        "diff": diff
                    })
        # Always generate a conversational reply
        ai_reply = None
        try:
            user_name = None
            if active_file and '**Name**' in file_contents.get(active_file, ''):
                import re as _re
                m_name = _re.search(r"\*\*Name\*\*\s*\|\s*([^|\n]+)", file_contents[active_file])
                if m_name:
                    name_candidate = m_name.group(1).strip().strip('*_')
                    if name_candidate and '[' not in name_candidate:
                        user_name = name_candidate

            if active_file and missing_fields:
                # Build context-aware prompt
                chat_prompt = (
                    f"You are a therapist assistant helping a user fill out {active_file}. "
                    + (f"The user's name is {user_name}. " if user_name else "") +
                    f"The field **{missing_fields[0]}** is still empty. Ask ONE empathetic, open-ended question to learn that field. "
                    "If the user just provided that value, briefly acknowledge and then ask for the next missing field."
                )
            elif active_file:
                chat_prompt = (
                    f"You are a world-class therapist helping a user fill out their personal file: {active_file}. "
                    + (f"The user's name is {user_name}. " if user_name else "") +
                    "Respond with empathy, briefly reflect what the user said, then ask ONE open-ended follow-up question that will elicit new useful information for that file. "
                    "If the user already provided new concrete facts, incorporate them into the appropriate section when proposing a diff."
                )
            else:
                chat_prompt = "You are a friendly, thoughtful assistant. Respond conversationally and empathetically."
            chat_prompt += " When you learn a concrete fact that belongs in a field, call the knowledge_object function with the appropriate 'placeholder_update'. For therapist insights, call knowledge_object with 'therapist_note'."
            chat_messages = [{"role": "system", "content": chat_prompt}, {"role": "user", "content": user_message}]
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-1106",
                messages=chat_messages,
                functions=EXTRACTION_FUNCTIONS,
                function_call="auto",
                max_tokens=200,
                temperature=0.7,
            )
            ai_reply = response.choices[0].message.content.strip()
            # If the model returned any function calls, apply them
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "function_call":
                func_call = response.choices[0].message.function_call
                try:
                    obj = _json.loads(func_call.arguments)
                    if isinstance(obj, dict):
                        objects = [obj]
                    else:
                        objects = obj
                    fc_diffs = _apply_knowledge_objects(user_id, objects)
                    diffs_applied.extend(fc_diffs)
                except Exception as _e:
                    logger.warning(f"Could not parse function-call arguments: {_e}")
        except Exception as e:
            logger.error(f"OpenAI ChatCompletion failed: {e}")
            ai_reply = "Hi! How can I help you today? (AI system unavailable)"
        if diffs_applied:
            diff_chunks = [d['diff'] for d in diffs_applied if 'diff' in d]
            return {
                "message": ai_reply,
                "sources": diffs_applied,
                "diff_preview": '\n\n'.join(diff_chunks) if diff_chunks else ''
            }

        # ------------------------------
        # Deterministic fallback: append goal
        # ------------------------------
        lowered = user_message.lower()
        if 'goal' in lowered and 'add' in lowered:
            import re as _re
            m = _re.search(r"'([^']+)'", user_message)
            if m:
                goal_line = m.group(1).strip()
                if goal_line:
                    goals_path = 'goals.md'
                    existing = open_file_fs(user_id, goals_path)
                    if goal_line not in existing:
                        new_content = (existing.rstrip() + '\n' if existing.strip() else '') + f"- {goal_line}.\n"
                        overwrite_file_fs(user_id, goals_path, new_content)
                        return {
                            "message": ai_reply,
                            "sources": [{"operation": "append_goal", "path": goals_path, "text": goal_line}],
                            "diff_preview": f"Appended '- {goal_line}.' to {goals_path}"
                        }

        # Fallback 2 – detect explicit "my name is ..." introduction only.
        # This prevents mistaking locations like "Tallinn" for the user's name.
        name_match = None
        import re as _re
        if "name" in user_message.lower():
            m2 = _re.search(r"my\s+name\s+is\s+([A-Z][a-zA-Z]+)", user_message, flags=_re.IGNORECASE)
            if m2:
                name_match = m2.group(1).strip()

        if name_match:
            about_path = 'AboutMe.md'
            about_content = open_file_fs(user_id, about_path)
            # Attempt direct placeholder replace first
            variants = ["[Your name here]", "*[Your name here]*", "**[Your name here]**"]
            for var in variants:
                if var in about_content:
                    about_content = about_content.replace(var, name_match, 1)
                    break
            # If Name row exists but placeholder not found, update row value
            if _re.search(r"\*\*Name\*\*\s*\|", about_content):
                new_about = _re.sub(r"\*\*Name\*\*\s*\|[^\n]*", f"**Name** | {name_match}", about_content)
            else:
                # Append a Name row to the end of first table
                lines = about_content.split('\n')
                insert_idx = 0
                for i,l in enumerate(lines):
                    if l.strip().startswith('|') and '|' in l:
                        insert_idx = i
                lines.insert(insert_idx+1, f"| **Name** | {name_match} |")
                new_about = '\n'.join(lines)
            overwrite_file_fs(user_id, about_path, new_about)
            return {
                "message": ai_reply,
                "sources": [{"operation": "overwrite_file", "path": about_path, "snippet": new_about}],
                "diff_preview": f"Set Name to {name_match} in {about_path}"
            }

        return {"message": ai_reply, "sources": []}

    except Exception as e:
        logger.error(f"Error processing MentalOS chat message: {e}")
        return jsonify({'error': str(e)}), 500

def patch_aboutme_field(user_id: str, field: str, value: str) -> str:
    """Patch a single field in AboutMe.md, replacing only the relevant line."""
    path = 'AboutMe.md'
    content = open_file_fs(user_id, path)
    # Map field to regex pattern and replacement
    field_map = {
        'name': (r'(\*\*Name\*\*\s*\|\s*)\*?[^|\n]*\*?', f'**Name** | {value}'),
        'age': (r'(\*\*Age & Life Stage\*\*\s*\|\s*)\*?[^|\n]*\*?', f'**Age & Life Stage** | {value}'),
        'location': (r'(\*\*Location\*\*\s*\|\s*)\*?[^|\n]*\*?', f'**Location** | {value}'),
        'role': (r'(\*\*Current Role\*\*\s*\|\s*)\*?[^|\n]*\*?', f'**Current Role** | {value}'),
        'relationship': (r'(\*\*Relationship Status\*\*\s*\|\s*)\*?[^|\n]*\*?', f'**Relationship Status** | {value}'),
    }
    if field not in field_map:
        return 'ERROR: Unknown field'
    pattern, replacement = field_map[field]
    new_content, n = re.subn(pattern, replacement, content)
    if n > 0:
        overwrite_file_fs(user_id, path, new_content)
        return 'OK'
    else:
        return 'ERROR: Field not found in file'

# Load Knowledge Map (single source of truth for MentalOS file schemas)
KNOWLEDGE_MAP_PATH = os.path.join(os.getcwd(), 'MentalOS', 'knowledge_map.json')
try:
    with open(KNOWLEDGE_MAP_PATH, 'r', encoding='utf-8') as _km:
        KNOWLEDGE_MAP = _json.load(_km)
        logger.info(f"Loaded knowledge map with {len(KNOWLEDGE_MAP)} entries from {KNOWLEDGE_MAP_PATH}")
except Exception as _e:
    logger.warning(f"Could not load knowledge map at {KNOWLEDGE_MAP_PATH}: {_e}")
    KNOWLEDGE_MAP = {}


def compute_missing_fields(file_name: str, content: str):
    """Return list of field names whose placeholder is still present in content, according to KNOWLEDGE_MAP."""
    entry = KNOWLEDGE_MAP.get(file_name) or {}
    fields = entry.get('fields', {})
    missing = []
    def _strip(s: str):
        return s.replace('*', '').replace('_', '').strip()
    norm_content = _strip(content)
    for field, placeholder in fields.items():
        if _strip(placeholder) in norm_content:
            missing.append(field)
    return missing

# ------------------------------------------------------------------
# PUT /api/mental-os/files/<filename>
# Save raw markdown coming from the front-end so templates remain intact.
# ------------------------------------------------------------------
@app.route('/api/mental-os/files/<path:filename>', methods=['PUT'])
def save_mental_os_file(filename):
    """Overwrite or create a MentalOS file with the content provided by the UI."""
    try:
        data = request.get_json(force=True)
        if not data or 'content' not in data:
            return jsonify({'error': 'Missing content field'}), 400

        user_id = request.headers.get('X-User-ID') \
                  or request.args.get('user_id') \
                  or 'anonymous'

        overwrite_file_fs(user_id, filename, data['content'])
        return jsonify({'status': 'ok', 'path': filename})
    except Exception as e:
        logger.error(f"Error saving MentalOS file {filename}: {e}")
        return jsonify({'error': str(e)}), 500

# ------------------------------------------------------------------
# Unified schema – future-proof replacement of KNOWLEDGE_MAP
# ------------------------------------------------------------------
MENTAL_SCHEMA_PATH = os.path.join(os.getcwd(), 'MentalOS', 'mental_model_schema.json')
try:
    with open(MENTAL_SCHEMA_PATH, 'r', encoding='utf-8') as _ms:
        import json as _json2
        MENTAL_SCHEMA = _json2.load(_ms)
        logger.info(f"Loaded MentalOS unified schema from {MENTAL_SCHEMA_PATH}")
except Exception as _e:
    logger.warning(f"Could not load mental model schema at {MENTAL_SCHEMA_PATH}: {_e}")
    MENTAL_SCHEMA = {}

# Compile schema validator once for fast reuse
if _jsonschema and MENTAL_SCHEMA:
    try:
        MENTAL_VALIDATOR = _jsonschema.Draft7Validator(MENTAL_SCHEMA)
    except Exception as _e:
        logger.warning(f"Could not compile JSON schema validator: {_e}")
        MENTAL_VALIDATOR = None
else:
    MENTAL_VALIDATOR = None

# -----------------------
# Function-calling extraction helpers
# -----------------------

# OpenAI function-call parameter schema must **NOT** contain oneOf / anyOf at the top level (client 1.x restriction).
# Therefore we expose a minimal permissive schema to OpenAI, while still validating rich objects with
# MENTAL_VALIDATOR after the call succeeds.

_SIMPLE_KNOWLEDGE_OBJECT_SCHEMA = {
    "type": "object",
    "description": "Lightweight schema only used for OpenAI function-calling. Real validation happens server-side.",
    "properties": {
        "kind": {"type": "string", "description": "Type of knowledge object (e.g. placeholder_update, therapist_note, summary_update, conclusion, cross_link)"},
        "file": {"type": "string"},
        "field": {"type": "string"},
        "value": {"type": "string"},
        "note": {"type": "string"},
        "section": {"type": "string"},
        "markdown": {"type": "string"},
        "tag": {"type": "string"},
        "text": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "from_file": {"type": "string"},
        "to_file": {"type": "string"},
        "reason": {"type": "string"},
        "confidence": {"type": "number"}
    },
    "required": ["kind"],
    "additionalProperties": True
}

EXTRACTION_FUNCTIONS = [
    {
        "name": "knowledge_object",
        "description": "Emit a knowledge object describing how to update the user's markdown knowledge base.",
        "parameters": _SIMPLE_KNOWLEDGE_OBJECT_SCHEMA
    }
]

def _apply_knowledge_objects(user_id: str, objects: list[dict]):
    """Apply objects returned by the LLM to markdown files, returning diff metadata list."""
    diffs = []
    for obj in objects:
        # ------------------------------------------------------------------
        # 1) Validate structure and skip low-confidence proposals
        # ------------------------------------------------------------------
        if MENTAL_VALIDATOR:
            try:
                MENTAL_VALIDATOR.validate(obj)
            except Exception as _ve:
                logger.warning(f"Invalid knowledge object skipped: {_ve}")
                continue

        if isinstance(obj.get('confidence'), (int, float)) and obj['confidence'] < 0.3:
            logger.info(f"Skipping very low-confidence object: {obj}")
            continue

        kind = obj.get("kind")
        if kind == "placeholder_update":
            file = obj.get("file")
            field = obj.get("field")
            value = obj.get("value")
            if not (file and field and value):
                continue
            # naive: use patch_aboutme_field for AboutMe, else simple replace
            if file == "AboutMe.md":
                res = patch_aboutme_field(user_id, field.lower().split()[0], value)
                if res == 'OK':
                    content = open_file_fs(user_id, file)
                    diffs.append({"operation": "overwrite_file", "path": file, "snippet": content})
            else:
                # generic: replace placeholder string if exists
                placeholder = KNOWLEDGE_MAP.get(file, {}).get('fields', {}).get(field)
                if placeholder:
                    content = open_file_fs(user_id, file)
                    new_content = content.replace(placeholder, value, 1)
                    if new_content != content:
                        overwrite_file_fs(user_id, file, new_content)
                        diffs.append({"operation": "overwrite_file", "path": file, "snippet": new_content})
        elif kind == "therapist_note":
            file = obj.get("file", "TherapistNotes/private.md")
            note = obj.get("note")
            if note:
                append_file_fs(user_id, file, f"- {note}\n")
                diffs.append({"operation": "append", "path": file, "snippet": note})
        elif kind == "summary_update":
            file = obj.get("file")
            section = obj.get("section")
            markdown_body = obj.get("markdown")
            if not (file and section and markdown_body):
                continue
            try:
                content = open_file_fs(user_id, file)
            except Exception:
                content = ""
            lines = content.split('\n') if content else []
            heading_idx = None
            heading_level = 0
            import re as _re
            for i, l in enumerate(lines):
                if l.lstrip().startswith('#'):
                    stripped = l.lstrip('#').strip()
                    if stripped.lower() == section.lower():
                        heading_idx = i
                        heading_level = len(l) - len(l.lstrip('#'))
                        break
            if heading_idx is not None:
                end_idx = len(lines)
                for j in range(heading_idx + 1, len(lines)):
                    if lines[j].startswith('#') and (len(lines[j]) - len(lines[j].lstrip('#'))) <= heading_level:
                        end_idx = j
                        break
                new_lines = lines[:heading_idx + 1] + markdown_body.split('\n') + lines[end_idx:]
            else:
                new_lines = lines + [f"## {section}"] + markdown_body.split('\n')
            new_content = '\n'.join(new_lines)
            overwrite_file_fs(user_id, file, new_content)
            diffs.append({"operation": "overwrite_file", "path": file, "snippet": new_content})

        elif kind == "conclusion":
            file = obj.get("file")
            tag = obj.get("tag") or obj.get("title")
            text = obj.get("text")
            evidence = obj.get("evidence", [])
            if not (file and tag and text):
                continue
            try:
                content = open_file_fs(user_id, file)
            except Exception:
                content = ""
            appendix = f"\n### Conclusion: {tag}\n\n{text}\n"
            if evidence:
                appendix += "\nEvidence:\n" + '\n'.join(f"- {e}" for e in evidence) + '\n'
            new_content = content.rstrip() + appendix
            overwrite_file_fs(user_id, file, new_content)
            diffs.append({"operation": "append", "path": file, "snippet": appendix.strip()})

        elif kind == "cross_link":
            from_file = obj.get("from_file")
            to_file = obj.get("to_file")
            reason = obj.get("reason", "related")
            if not (from_file and to_file):
                continue
            try:
                content = open_file_fs(user_id, from_file)
            except Exception:
                content = ""
            link_line = f"- Linked to [{to_file}]({to_file}): {reason}"
            if link_line not in content:
                new_content = (content.rstrip() + '\n' if content else '') + link_line + '\n'
                overwrite_file_fs(user_id, from_file, new_content)
                diffs.append({"operation": "append", "path": from_file, "snippet": link_line})

# --------------------------------------------------------------------
# === MentalOS Share-link & Folder Index helpers ===

from pathlib import Path
import uuid
from functools import lru_cache

# In-memory token store – fine for dev; can be swapped for Firestore later
SHARE_TOKEN_MAP: dict[str, dict] = {}

VOICES_DIR_NAME = "voices"

@lru_cache(maxsize=1024)
def _scan_user_folders(user_id: str) -> list[dict]:
    """Ensure the ⚡ VOICES folder exists and return all folder metadata (even empty ones)."""
    user_dir = Path(BASE_MENTALOS_DIR) / user_id
    # Guarantee base user directory and an (initially empty) voices/ folder exist
    voices_path = user_dir / VOICES_DIR_NAME
    voices_path.mkdir(parents=True, exist_ok=True)
    # Ensure an instruction file exists so users immediately understand this folder
    info_path = voices_path / "ABOUT_THIS_FOLDER.md"
    if not info_path.exists():
        info_path.write_text(
            """# 🗣️ Voices – how it works\n\nInvite trusted people to share how they see you.\n\n1. Click the ➕ icon or the Share button to create a *voice* file.\n2. A unique link is copied to your clipboard – send it to your friend.\n3. They can write directly in that file; you'll see it update live.\n\nCreate as many voices as you like. Each file is private between you and the person you invited.\n""",
            encoding="utf-8")

    if not user_dir.exists():
        return []

    folders = []
    for folder_path in user_dir.iterdir():
        if not folder_path.is_dir():
            continue
        # Collect .md files (may be empty)
        files = [
            {"name": f.name, "label": f.stem.replace('-', ' ').replace('_', ' ').title()} for f in folder_path.glob("*.md")
        ]
        folders.append({"name": folder_path.name, "files": files})
    return folders

@app.route('/api/mental-os/folders', methods=['GET'])
def list_mental_folders():
    """Return dynamic folder list for a user (used to augment sidebar)."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    folders = _scan_user_folders(user_id)
    return jsonify({"folders": folders})

# ---------------- Share token flow ----------------

@app.route('/api/mental-os/share', methods=['POST'])
def create_share_link():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    label = data.get('label', '').strip()
    role = (data.get('role') or 'friend').strip().lower()
    if not user_id or not label:
        return jsonify({"error": "user_id and label required"}), 400

    # Create voices folder
    user_dir = Path(BASE_MENTALOS_DIR) / user_id / VOICES_DIR_NAME
    user_dir.mkdir(parents=True, exist_ok=True)

    # Build filename
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', label.lower()).strip("_")
    filename = f"{slug}.md"
    file_path = user_dir / filename

    # Generate token and share URL first so we can embed it
    token = uuid.uuid4().hex
    relative_url = f"/share/{token}"
    full_url = request.host_url.rstrip('/') + relative_url  # e.g. http://localhost:8080/share/<token>

    if not file_path.exists():
        questions_by_role = {
            'partner': [
                f"How would you describe {label}'s love language?",
                "When do you feel you connect the most?",
                "What habits of mine help our relationship?",
                "What could I do to better support you?"
            ],
            'friend': [
                f"What's your favourite memory with {label}?",
                "When have you seen me happiest?",
                "When have you seen me struggle?",
                "How can I be a better friend to you?"
            ],
            'family': [
                "What family traits do you see in me?",
                "When do I shine around family?",
                "Where do I clash with family expectations?",
                "How can our relationship grow?"
            ],
            'coworker': [
                f"How would you describe {label}'s working style?",
                "What strengths do I bring to the team?",
                "Where could I improve professionally?",
                "How can we collaborate better?"
            ]
        }
        interview = questions_by_role.get(role, questions_by_role['friend'])
        interview_block = "\n  - " + "\n  - ".join(interview)

        template = (
            f"<!--\ninterview:{interview_block}\n-->\n"
            f"# Perspective from {label} ({role.title()})\n\n"
            f"> **Share link**: {full_url}\n\n"
            "*Write freely; bullet points are welcome.*\n"
        )
        file_path.write_text(template, encoding='utf-8')

    # Store mapping after file is ensured
    SHARE_TOKEN_MAP[token] = {
        "owner": user_id,
        "file": str(file_path.relative_to(BASE_MENTALOS_DIR)),
    }

    return jsonify({"token": token, "url": relative_url, "full_url": full_url, "file": filename})

@app.route('/api/mental-os/share/<string:token>', methods=['GET', 'PUT'])
def handle_share_token(token):
    info = SHARE_TOKEN_MAP.get(token)
    if not info:
        return jsonify({"error": "invalid token"}), 404
    owner = info['owner']
    rel_path = info['file']
    abs_path = Path(BASE_MENTALOS_DIR) / rel_path
    if request.method == 'GET':
        if not abs_path.exists():
            return jsonify({"error": "file missing"}), 404
        return abs_path.read_text(encoding='utf-8')
    else:  # PUT
        content = request.get_data(as_text=True)
        abs_path.write_text(content, encoding='utf-8')
        # Invalidate folder scan cache so owner sees new file updated counters
        _scan_user_folders.cache_clear()
        return jsonify({"status": "saved"})

if __name__ == '__main__':
    # Run without Flask auto-reloader so long-running chat sessions aren't interrupted
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False, use_reloader=False) 