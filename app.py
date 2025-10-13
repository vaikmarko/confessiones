import os
import json
import logging
import requests
import hashlib
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import query as firestore_query
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import stripe

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin SDK
try:
    # Try multiple possible locations for credentials file
    import os
    possible_paths = [
        "firebase-credentials.json",
        "/app/firebase-credentials.json",
        os.path.join(os.path.dirname(__file__), "firebase-credentials.json")
    ]
    
    cred_file = None
    for path in possible_paths:
        if os.path.exists(path):
            cred_file = path
            logger.info(f"Found Firebase credentials at: {path}")
            break
    
    if cred_file:
        cred = credentials.Certificate(cred_file)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firebase Firestore initialized successfully.")
    else:
        logger.error("Firebase credentials file not found in any expected location")
        logger.warning(f"Checked paths: {possible_paths}")
        db = None
except Exception as e:
    logger.error(f"Could not initialize Firebase Admin SDK: {e}")
    logger.warning("Falling back to in-memory storage. THIS IS NOT SUITABLE FOR PRODUCTION.")
    db = None

# In-memory storage is now a fallback for local development without credentials.
confessions = [] # This will only be used if Firestore fails to initialize.
conversations = {}

# Value-first user tracking system
user_sessions = {}  # Track user subscription status (in-memory cache)
conversation_depth = {}  # Track conversation engagement
from datetime import datetime, timedelta
import calendar
import json

def get_user_tier(session_id):
    """Get user subscription tier: 'free' or 'unlimited'"""
    return user_sessions.get(session_id, {}).get('tier', 'free')

def get_conversation_depth(session_id):
    """Get current conversation depth (number of messages)"""
    return conversation_depth.get(session_id, 0)

def increment_conversation_depth(session_id):
    """Increment conversation depth counter"""
    conversation_depth[session_id] = conversation_depth.get(session_id, 0) + 1

def should_suggest_upgrade(session_id):
    """Suggest upgrade after 4 meaningful messages (value demonstration)"""
    depth = get_conversation_depth(session_id)
    tier = get_user_tier(session_id)
    
    # Suggest upgrade after 4 messages for free users
    return tier == 'free' and depth >= 4

def set_user_tier(session_id, tier, customer_id=None, subscription_id=None):
    """Set user subscription tier (for testing and webhook handling)"""
    if session_id not in user_sessions:
        user_sessions[session_id] = {}
    user_sessions[session_id]['tier'] = tier
    user_sessions[session_id]['updated_at'] = datetime.now()
    if customer_id:
        user_sessions[session_id]['customer_id'] = customer_id
    if subscription_id:
        user_sessions[session_id]['subscription_id'] = subscription_id
    
    # Also store in Firestore for persistence
    try:
        if db:
            subscription_data = {
                'tier': tier,
                'session_id': session_id,
                'updated_at': datetime.now(),
                'created_at': user_sessions[session_id].get('created_at', datetime.now())
            }
            if customer_id:
                subscription_data['customer_id'] = customer_id
            if subscription_id:
                subscription_data['subscription_id'] = subscription_id
                
            subscription_ref = db.collection('subscriptions').document(session_id)
            subscription_ref.set(subscription_data)
            logger.info(f"Stored subscription {tier} for session {session_id} in Firestore")
    except Exception as e:
        logger.error(f"Failed to store subscription in Firestore: {e}")

def load_user_subscriptions():
    """Load user subscriptions from Firestore on startup"""
    try:
        if db:
            subscriptions = db.collection('subscriptions').stream()
            for sub in subscriptions:
                data = sub.to_dict()
                session_id = data.get('session_id', sub.id)
                user_sessions[session_id] = {
                    'tier': data.get('tier', 'free'),
                    'updated_at': data.get('updated_at', datetime.now()),
                    'created_at': data.get('created_at', datetime.now())
                }
            logger.info(f"Loaded {len(user_sessions)} subscriptions from Firestore")
    except Exception as e:
        logger.error(f"Failed to load subscriptions from Firestore: {e}")

def get_subscription_from_stripe_session(stripe_session_id):
    """Get subscription details from Stripe session"""
    try:
        session = stripe.checkout.Session.retrieve(stripe_session_id)
        if session.payment_status == 'paid':
            return {
                'customer_id': session.customer,
                'subscription_id': session.subscription,
                'session_id': session.metadata.get('user_session_id', 'anonymous'),
                'tier': session.metadata.get('tier', 'unlimited')
            }
    except Exception as e:
        logger.error(f"Failed to get Stripe session: {e}")
    return None

# Initialize OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key and openai_api_key.startswith('sk-'):
    logger.info("OpenAI API key found")
else:
    logger.warning("No valid OpenAI API key found")
    openai_api_key = None

# Initialize Stripe
stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')

if stripe_secret_key:
    try:
        stripe.api_key = stripe_secret_key
        logger.info("Stripe API key found and configured")
    except Exception as e:
        logger.error(f"Stripe initialization error: {e}")
else:
    logger.warning("No Stripe API key found")

# Christian Sacramental Confession Prompts
CONFESSION_INITIAL_PROMPT = """You are a wise and compassionate Catholic priest conducting the Sacrament of Confession.

FIRST MESSAGE ONLY – Responsibilities:
1. Offer a warm but succinct welcome (1 sentence)
2. Provide 1–2 short Scripture references that invite trust in God's mercy (1–2 sentences)
3. Ask one gentle, open-ended question to help the penitent begin (1 sentence)

Keep the whole reply under 4 sentences.
"""

CONFESSION_FOLLOWUP_PROMPT = """You are a wise and compassionate Catholic priest continuing an ongoing confession. Your goal is to create a natural, reflective, and pastoral conversation, not an interrogation.

**Your Role in This Follow-Up Message:**
1.  **Acknowledge & Validate**: Start by acknowledging the user's last message with empathy (e.g., "That's a heavy burden to carry," "It's wonderful that you feel that way," "Thank you for sharing that.").
2.  **Offer Gentle Guidance**: Provide a *brief* spiritual insight or a *new, relevant* Scripture verse that directly addresses their specific concern (1-2 sentences). Do not repeat verses.
3.  **Decide How to Conclude**:
    -   **Option A (Ask a Question):** If the conversation needs prompting, ask a single, gentle, open-ended question to help them go deeper.
    -   **Option B (Make a Statement):** If the user has shared something positive or conclusive, it is often better to respond with a simple, affirming statement. (e.g., "That is a beautiful grace.", "May that peace remain with you.")

**Crucial Constraints:**
-   **VARY YOUR RESPONSES**: Do NOT ask a question every single time. A mix of questions and statements is more natural.
-   **Be Concise**: Never exceed 4 sentences.
-   **Be Pastoral**: Your tone should be gentle, patient, and merciful.
-   **No Repetition**: Do not repeat the initial welcome or previous scripture.
"""

CONFESSION_SUMMARY_PROMPT = """Transform this chat into a beautiful, first-person prayer and a short, thematic title.

**Your Task:**
1.  **Generate a Title**: Create a short, relatable title (3-5 words) that captures the core theme of the confession (e.g., "A Prayer for Patience," "Finding Hope in Loss," "Overcoming Envy"). The title should be engaging and hint at the prayer's content without revealing specifics.
2.  **Write the Prayer**: Write a beautiful, first-person prayer that is ready for the Sacrament of Reconciliation. It must:
    -   Adopt a humble, first-person voice ("I").
    -   Acknowledge the core struggle compassionately.
    -   Seamlessly integrate 1-2 relevant Scripture passages.
    -   Express sincere contrition and hope in God's mercy.
    -   Be poetic, prayerful, and concise (3-4 powerful sentences).

**Output Format:**
You MUST return the response in the following format, with "Title:" and "Prayer:" on separate lines:

Title: [Your Generated Title]
Prayer: [Your Generated Prayer]
"""

@app.route('/')
def index_redirect():
    """Redirect to main app"""
    return render_template('index.html')

@app.route('/app')
def app_view():
    """Main confession app"""
    # Firebase configuration for frontend
    firebase_config = {
        'apiKey': os.getenv('FIREBASE_API_KEY', ''),
        'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN', ''),
        'projectId': os.getenv('FIREBASE_PROJECT_ID', ''),
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', ''),
        'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID', ''),
        'appId': os.getenv('FIREBASE_APP_ID', '')
    }
    
    return render_template('app.html', 
                         cache_bust=datetime.now().timestamp(),
                         firebase_config=firebase_config)

@app.route('/terms')
def terms_view():
    """Terms of Service page"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy_view():
    """Privacy Policy page"""
    return render_template('privacy.html')

@app.route('/disclaimer')
def disclaimer_view():
    """Disclaimer page"""
    return render_template('disclaimer.html')

@app.route('/donation-success')
def donation_success():
    """Donation success page"""
    return render_template('donation-success.html')

@app.route('/donation-cancel')
def donation_cancel():
    """Donation cancel page"""
    return render_template('donation-cancel.html')

@app.route('/subscription-success')
def subscription_success():
    """Handle successful subscription"""
    stripe_session_id = request.args.get('session_id')
    user_session = request.args.get('user_session', 'anonymous')
    
    # Get subscription details from Stripe
    subscription_data = get_subscription_from_stripe_session(stripe_session_id)
    
    if subscription_data:
        # Upgrade user based on actual Stripe data
        session_id = subscription_data['session_id']
        tier = subscription_data['tier']
        customer_id = subscription_data.get('customer_id')
        subscription_id = subscription_data.get('subscription_id')
        
        set_user_tier(session_id, tier, customer_id, subscription_id)
        
        # Also update the user's account in the users collection if it exists
        if db:
            try:
                user_ref = db.collection('users').document(session_id)
                user_doc = user_ref.get()
                
                if user_doc.exists:
                    # Update existing user account with subscription info
                    user_ref.update({
                        'tier': tier,
                        'customer_id': customer_id,
                        'subscription_id': subscription_id,
                        'updated_at': datetime.now()
                    })
                    logger.info(f"Updated user account {session_id} with subscription info")
                else:
                    # Check if this session_id corresponds to a registered user by email
                    # This handles cases where user registered but session_id doesn't match
                    users_ref = db.collection('users')
                    users_query = users_ref.where('session_id', '==', session_id).limit(1).get()
                    
                    if users_query:
                        user_ref = users_ref.document(users_query[0].id)
                        user_ref.update({
                            'tier': tier,
                            'customer_id': customer_id,
                            'subscription_id': subscription_id,
                            'updated_at': datetime.now()
                        })
                        logger.info(f"Updated user account {users_query[0].id} with subscription info")
            except Exception as e:
                logger.error(f"Failed to update user account: {e}")
        
        logger.info(f"User {session_id} upgraded to {tier} via Stripe session {stripe_session_id}")
        
        return render_template('subscription-success.html', 
                             tier=tier, 
                             session_id=session_id,
                             subscription_id=subscription_id,
                             customer_id=customer_id)
    else:
        # Fallback: upgrade the user session from URL parameter
        set_user_tier(user_session, 'unlimited')
        
        # Also update user account if it exists
        if db:
            try:
                user_ref = db.collection('users').document(user_session)
                user_doc = user_ref.get()
                
                if user_doc.exists:
                    user_ref.update({
                        'tier': 'unlimited',
                        'updated_at': datetime.now()
                    })
                    logger.info(f"Updated user account {user_session} with unlimited tier (fallback)")
            except Exception as e:
                logger.error(f"Failed to update user account (fallback): {e}")
        
        logger.info(f"User {user_session} upgraded to unlimited (fallback)")
        
        return render_template('subscription-success.html', tier='unlimited', session_id=user_session)

@app.route('/subscription-cancel')
def subscription_cancel():
    """Handle cancelled subscription"""
    return render_template('subscription-cancel.html')

@app.route('/api/user/tier', methods=['GET'])
def get_user_tier_api():
    """Get current user tier and usage"""
    session_id = request.args.get('session_id', 'anonymous')
    return jsonify({
        'tier': get_user_tier(session_id),
        'conversation_depth': get_conversation_depth(session_id),
        'limit': 999 if get_user_tier(session_id) == 'unlimited' else 4
    })

@app.route('/api/user/tier', methods=['POST'])
def set_user_tier_api():
    """Set user tier (for testing purposes)"""
    data = request.get_json()
    session_id = data.get('session_id', 'anonymous')
    tier = data.get('tier', 'free')
    
    if tier not in ['free', 'unlimited']:
        return jsonify({'error': 'Invalid tier'}), 400
    
    set_user_tier(session_id, tier)
    return jsonify({'success': True, 'tier': tier})

@app.route('/manifest.json')
def manifest():
    """Serve PWA manifest"""
    return app.send_static_file('manifest.json')

@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt"""
    return app.send_static_file('robots.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    """Serve sitemap.xml"""
    return app.send_static_file('sitemap.xml')

@app.route('/api/stripe/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe checkout session for unlimited spiritual guidance"""
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'anonymous')
        
        if not stripe_secret_key:
            return jsonify({'error': 'Payment processing is not available'}), 503
            
        # Get price ID from environment (single unlimited product)
        price_id = os.getenv('STRIPE_PRICE_ID_UNLIMITED')
        if not price_id:
            # For testing purposes, use a placeholder
            # In production, you need to create the actual Stripe product
            return jsonify({
                'error': 'Stripe product not set up yet. Please create "Unlimited Spiritual Guidance" product in Stripe Dashboard and add STRIPE_PRICE_ID_UNLIMITED to your .env file.',
                'setup_required': True,
                'stripe_dashboard': 'https://dashboard.stripe.com/products'
            }), 500
            
        # Create checkout session
        try:
            logger.info(f"Creating Stripe unlimited subscription checkout")
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.host_url + f'subscription-success?session_id={{CHECKOUT_SESSION_ID}}&user_session={session_id}',
                cancel_url=request.host_url + 'subscription-cancel',
                metadata={
                    'tier': 'unlimited',
                    'user_session_id': session_id,
                    'source': 'myconfessions_unlimited'
                },
                allow_promotion_codes=True,
            )
            logger.info(f"Stripe checkout session created: {checkout_session.id}")
        except Exception as stripe_error:
            logger.error(f"Stripe checkout error: {stripe_error}")
            return jsonify({'error': 'Unable to create payment session'}), 500
        
        return jsonify({'checkout_url': checkout_session.url})
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return jsonify({'error': 'Unable to process subscription'}), 500

@app.route('/api/stripe/config')
def get_stripe_config():
    """Get Stripe publishable key for frontend"""
    return jsonify({
        'publishable_key': stripe_publishable_key
    })

@app.route('/api/chat/message', methods=['POST'])
def process_chat_message():
    """Handle chat messages for confession guidance"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('session_id', 'anonymous')
        conversation_history = data.get('conversation_history', [])
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        logger.info(f"Processing confession chat for session {session_id}")
        
        # Generate AI response - ONLY use real AI, no fallbacks
        if not openai_api_key:
            return jsonify({'error': 'AI service is not available. Please try again later.'}), 503
        
        try:
            # Decide which system prompt to use based on whether we already have conversation history
            if conversation_history:
                system_prompt = CONFESSION_FOLLOWUP_PROMPT
            else:
                system_prompt = CONFESSION_INITIAL_PROMPT

            # Build conversation context
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history (unlimited for all users - we want to show value)
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
                
            for msg in recent_history:
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })
            
            # Add current message
            messages.append({"role": "user", "content": message})
                
            # Make direct API call
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 120,
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return jsonify({'error': 'Sorry, I cannot connect to the AI system right now. Please try again later.'}), 500
                
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return jsonify({'error': 'Sorry, I cannot connect to the AI system right now. Please try again later.'}), 500
        
        # Store conversation in memory
        if session_id not in conversations:
            conversations[session_id] = []
        
        conversations[session_id].extend([
            {'role': 'user', 'content': message, 'timestamp': datetime.now().isoformat()},
            {'role': 'assistant', 'content': ai_response, 'timestamp': datetime.now().isoformat()}
        ])
        
        # INCREMENT CONVERSATION DEPTH
        increment_conversation_depth(session_id)
        
        # CHECK IF WE SHOULD SUGGEST UPGRADE (value-first approach)
        suggest_upgrade = should_suggest_upgrade(session_id)
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'timestamp': datetime.now().isoformat(),
            'tier': get_user_tier(session_id),
            'conversation_depth': get_conversation_depth(session_id),
            'suggest_upgrade': suggest_upgrade,  # NEW: Suggest upgrade instead of blocking
            'upgrade_message': {
                'title': 'Continue Your Spiritual Journey',
                'message': 'I sense you\'re seeking deeper guidance. Many souls like you find unlimited spiritual support helps them grow closer to God.',
                'cta': 'Continue with Unlimited Guidance - $9.99/month'
            } if suggest_upgrade else None
        })
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        return jsonify({'error': 'Sorry, something went wrong. Please try again.'}), 500

@app.route('/api/chat/summarize', methods=['POST'])
def summarize_chat():
    """Generate a confession summary from a chat conversation without saving it."""
    try:
        data = request.get_json()
        conversation_history = data.get('conversation_history', [])
        
        if not conversation_history:
            return jsonify({'error': 'Conversation history is required'}), 400
            
        if not openai_api_key:
            return jsonify({'error': 'AI service is not available.'}), 503

        # Prepare conversation for summary
        conversation_text = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
            for msg in conversation_history
        ])
        
        # Make direct API call to OpenAI
        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        }
        api_data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": CONFESSION_SUMMARY_PROMPT},
                {"role": "user", "content": f"Create a confession summary from this conversation:\n\n{conversation_text}"}
            ],
            "max_tokens": 200,
            "temperature": 0.3
        }
        
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=api_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            raw_summary = result['choices'][0]['message']['content'].strip()
            
            # Parse the title and prayer from the raw response
            title = "A Prayer" # Default title
            prayer = raw_summary
            
            if "Title:" in raw_summary and "Prayer:" in raw_summary:
                try:
                    title_part = raw_summary.split("Title:")[1].split("Prayer:")[0].strip()
                    prayer_part = raw_summary.split("Prayer:")[1].strip()
                    title = title_part
                    prayer = prayer_part
                except IndexError:
                    logger.warning("Could not parse title and prayer, using raw summary.")

            return jsonify({'success': True, 'title': title, 'prayer': prayer})
        else:
            logger.error(f"OpenAI API error during summarization: {response.status_code} - {response.text}")
            return jsonify({'error': 'Sorry, I cannot generate your summary right now.'}), 500
        
    except Exception as e:
        logger.error(f"Error summarizing chat: {e}")
        return jsonify({'error': 'Sorry, something went wrong.'}), 500

@app.route('/api/confessions/save', methods=['POST'])
def save_confession():
    """Save a new confession to Firestore."""
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'anonymous')
        is_public = data.get('is_public', False)
        title = data.get('title', 'A Prayer')
        confession_text = data.get('confession_text', '')

        if not confession_text:
            return jsonify({'error': 'Confession text is required.'}), 400

        # Create confession object for Firestore
        confession_data = {
            'title': title,
            'text': confession_text,
            'is_public': is_public,
            'upvotes': 0,
            'created_at': datetime.now(),
            'session_id': session_id
        }

        if db:
            # Add a new document with a generated ID
            doc_ref = db.collection('confessions').add(confession_data)
            # Fetch the newly created document to return its data, including the ID
            new_confession = doc_ref.get().to_dict()
            new_confession['id'] = doc_ref.id
            logger.info(f"Saved confession {doc_ref.id} to Firestore.")
        else:
            # Fallback to in-memory list (for local dev)
            new_confession = confession_data
            new_confession['id'] = f"confession_{len(confessions) + 1}"
            confessions.append(new_confession)
            logger.info(f"Saved confession {new_confession['id']} to in-memory list.")

        # Clear the original conversation now that it's saved
        if session_id in conversations:
            conversations[session_id] = []
        
        return jsonify({
            'success': True,
            'confession': new_confession
        })
        
    except Exception as e:
        logger.error(f"Error creating confession: {e}")
        return jsonify({'error': 'Sorry, something went wrong.'}), 500

@app.route('/api/confessions', methods=['GET'])
def get_confessions():
    """Get public confessions from Firestore, with sorting options."""
    try:
        sort_by = request.args.get('sort', 'latest')
        
        if not db:
            # Fallback for local development
            logger.warning("DB not initialized. Returning in-memory confessions.")
            public_confessions = [c for c in confessions if c.get('is_public', False)]
            if sort_by == 'popular':
                public_confessions.sort(key=lambda x: x.get('upvotes', 0), reverse=True)
            else:
                public_confessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return jsonify(public_confessions)

        # Production logic: Fetch from Firestore
        confessions_ref = db.collection('confessions').where('is_public', '==', True)
        
        if sort_by == 'popular':
            query = confessions_ref.order_by('upvotes', direction=firestore_query.Query.Direction.DESCENDING)
        else: # 'latest'
            query = confessions_ref.order_by('created_at', direction=firestore_query.Query.Direction.DESCENDING)
            
        results = query.stream()
        
        public_confessions = []
        for doc in results:
            confession = doc.to_dict()
            confession['id'] = doc.id
            # Firestore timestamp needs to be converted to a string
            if 'created_at' in confession and hasattr(confession['created_at'], 'isoformat'):
                confession['created_at'] = confession['created_at'].isoformat()
            public_confessions.append(confession)
            
        return jsonify(public_confessions)
            
    except Exception as e:
        logger.error(f"Error getting confessions: {e}")
        return jsonify([])

@app.route('/api/stats/souls_helped', methods=['GET'])
def get_souls_helped():
    """Get the total number of confessions created."""
    try:
        if not db:
            # Fallback for local development
            logger.warning("DB not initialized. Returning in-memory confession count.")
            return jsonify({'count': len(confessions)})

        # Production logic: Fetch count from Firestore
        # This gets the count of all documents in the collection.
        count = db.collection('confessions').get()
        return jsonify({'count': len(count)})
                        
    except Exception as e:
        logger.error(f"Error getting souls helped count: {e}")
        return jsonify({'count': 0}) # Return 0 on error

@app.route('/api/confessions/<confession_id>/upvote', methods=['POST'])
def upvote_confession(confession_id):
    """Upvote a specific confession in Firestore."""
    try:
        if not db:
            # Fallback for local development
            confession = next((c for c in confessions if c['id'] == confession_id), None)
            if confession:
                confession['upvotes'] = confession.get('upvotes', 0) + 1
                return jsonify({'success': True, 'upvotes': confession['upvotes']})
            else:
                return jsonify({'error': 'Confession not found'}), 404
        
        # Production logic: Update in Firestore
        confession_ref = db.collection('confessions').document(confession_id)
        # Use a transaction to safely increment the upvote count
        confession_ref.update({'upvotes': firestore.Increment(1)})
        
        # We don't need to return the new count, a success message is enough.
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error upvoting confession: {e}")
        return jsonify({'error': 'Sorry, something went wrong.'}), 500

@app.route('/api/confessions/<confession_id>', methods=['GET'])
def get_confession(confession_id):
    """Get a specific confession from Firestore."""
    try:
        if not db:
            # Fallback for local development
            confession = next((c for c in confessions if c['id'] == confession_id), None)
            if confession:
                return jsonify(confession)
            else:
                return jsonify({'error': 'Confession not found'}), 404

        # Production logic: Fetch from Firestore
        doc_ref = db.collection('confessions').document(confession_id)
        doc = doc_ref.get()
        if doc.exists:
            confession = doc.to_dict()
            confession['id'] = doc.id
            confession['created_at'] = confession['created_at'].isoformat()
            return jsonify(confession)
        else:
            return jsonify({'error': 'Confession not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting confession: {e}")
        return jsonify({'error': 'Sorry, something went wrong.'}), 500

@app.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks for subscription events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Verify webhook signature (in production, use your webhook secret)
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET', '')
        )
    except ValueError:
        logger.error("Invalid payload")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session['metadata'].get('user_session_id', 'anonymous')
        tier = session['metadata'].get('tier', 'unlimited')
        
        # Upgrade user
        set_user_tier(session_id, tier)
        logger.info(f"Webhook: User {session_id} upgraded to {tier}")
        
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Handle subscription cancellation
        logger.info(f"Webhook: Subscription {subscription['id']} cancelled")
        
    return jsonify({'status': 'success'})

@app.route('/api/user/register', methods=['POST'])
def handle_register():
    """Register a new user with email and password"""
    if not db:
        return jsonify({'error': 'Database not available'}), 503

    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Check if user already exists
        users_ref = db.collection('users')
        existing_user = users_ref.where('email', '==', email).limit(1).get()

        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400

        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Create new user
        user_ref = users_ref.document()
        session_id = user_ref.id
        user_ref.set({
            'session_id': session_id,
            'email': email,
            'name': name,
            'password_hash': password_hash,
            'tier': 'free',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })

        logger.info(f"Registered new user with email {email}")

        return jsonify({
            'success': True,
            'message': 'Account created successfully',
            'session_id': session_id,
            'tier': 'free'
        })

    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return jsonify({'error': 'Failed to create account'}), 500


@app.route('/api/user/login', methods=['POST'])
def handle_login():
    """Login user with email and password"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        if db:
            # Find user by email
            users_ref = db.collection('users')
            user_query = users_ref.where('email', '==', email).limit(1).get()
            
            if not user_query:
                return jsonify({'error': 'Invalid email or password'}), 401
            
            user_doc = user_query[0]
            user_data = user_doc.to_dict()
            
            # Verify password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if user_data.get('password_hash') != password_hash:
                return jsonify({'error': 'Invalid email or password'}), 401
            
            # Return user session
            session_id = user_data.get('session_id')
            tier = user_data.get('tier', 'free')
            
            logger.info(f"User {email} logged in successfully")
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'session_id': session_id,
                'tier': tier,
                'email': email,
                'name': user_data.get('name', '')
            })
        else:
            return jsonify({'error': 'Database not available'}), 500
            
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        return jsonify({'error': 'Failed to login'}), 500

@app.route('/api/user/create-account', methods=['POST'])
def create_user_account():
    """Create a user account linked to their session (for existing subscribers)"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        email = data.get('email')
        name = data.get('name', '')
        
        if not session_id or not email:
            return jsonify({'error': 'Session ID and email are required'}), 400
        
        # Check if user already has a subscription
        current_tier = get_user_tier(session_id)
        
        # Create user account in Firestore
        if db:
            user_ref = db.collection('users').document(session_id)
            user_ref.set({
                'session_id': session_id,
                'email': email,
                'name': name,
                'tier': current_tier,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            
            logger.info(f"Created user account for session {session_id} with email {email}")
            
            return jsonify({
                'success': True,
                'message': 'Account created successfully',
                'tier': current_tier,
                'session_id': session_id
            })
        else:
            return jsonify({'error': 'Database not available'}), 500
            
    except Exception as e:
        logger.error(f"Error creating user account: {e}")
        return jsonify({'error': 'Failed to create account'}), 500

@app.route('/api/user/subscription-management', methods=['GET'])
def get_subscription_management():
    """Get subscription management URL for user"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        # Get user's subscription from Firestore
        if db:
            subscription_ref = db.collection('subscriptions').document(session_id)
            subscription_doc = subscription_ref.get()
            
            if subscription_doc.exists:
                subscription_data = subscription_doc.to_dict()
                customer_id = subscription_data.get('customer_id')
                
                if customer_id:
                    # Create Stripe customer portal session
                    try:
                        portal_session = stripe.billing_portal.Session.create(
                            customer=customer_id,
                            return_url=request.host_url + 'app'
                        )
                        
                        return jsonify({
                            'success': True,
                            'management_url': portal_session.url,
                            'message': 'Subscription management portal created'
                        })
                    except Exception as e:
                        logger.error(f"Failed to create portal session: {e}")
                        return jsonify({
                            'error': 'Unable to create management portal. Please contact support.',
                            'contact_email': 'support@myconfessions.org'
                        }), 500
                else:
                    return jsonify({
                        'error': 'No customer ID found. Please contact support.',
                        'contact_email': 'support@myconfessions.org'
                    }), 400
            else:
                return jsonify({
                    'error': 'No subscription found for this session'
                }), 404
        else:
            return jsonify({'error': 'Database not available'}), 500
            
    except Exception as e:
        logger.error(f"Error getting subscription management: {e}")
        return jsonify({'error': 'Failed to get subscription management'}), 500

@app.route('/api/user/account', methods=['GET'])
def get_user_account():
    """Get user account information"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        if db:
            user_ref = db.collection('users').document(session_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                return jsonify({
                    'success': True,
                    'account': {
                        'email': user_data.get('email'),
                        'name': user_data.get('name'),
                        'tier': user_data.get('tier', 'free'),
                        'created_at': user_data.get('created_at').isoformat() if user_data.get('created_at') else None
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'No account found for this session'
                })
        else:
            return jsonify({'error': 'Database not available'}), 500
            
    except Exception as e:
        logger.error(f"Error getting user account: {e}")
        return jsonify({'error': 'Failed to get account'}), 500

if __name__ == '__main__':
    # Load existing subscriptions on startup
    load_user_subscriptions()
    
    port = int(os.environ.get('PORT', 8085))
    app.run(host='0.0.0.0', port=port, debug=True)