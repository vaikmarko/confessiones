import os
import json
import logging
import requests
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin SDK
try:
    # NOTE: You will need to create a 'firebase-credentials.json' file in your project root.
    # This file is your private service account key and should NOT be committed to git.
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase Firestore initialized successfully.")
except Exception as e:
    logger.error(f"Could not initialize Firebase Admin SDK: {e}")
    logger.warning("Falling back to in-memory storage. THIS IS NOT SUITABLE FOR PRODUCTION.")
    db = None

# In-memory storage is now a fallback for local development without credentials.
confessions = [] # This will only be used if Firestore fails to initialize.
conversations = {}

# Initialize OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key and openai_api_key.startswith('sk-'):
    logger.info("OpenAI API key found")
else:
    logger.warning("No valid OpenAI API key found")
    openai_api_key = None

# Christian Sacramental Confession Prompts
CONFESSION_INITIAL_PROMPT = """You are a wise and compassionate Catholic priest conducting the Sacrament of Confession.

FIRST MESSAGE ONLY – Responsibilities:
1. Offer a warm but succinct welcome (1 sentence)
2. Provide 1–2 short Scripture references that invite trust in God’s mercy (1–2 sentences)
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
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/app')
def app_view():
    """Main confession app"""
    return render_template('app.html', cache_bust=datetime.now().timestamp())

@app.route('/manifest.json')
def manifest():
    """Serve PWA manifest"""
    return app.send_static_file('manifest.json')

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

            # Add conversation history (keep last 10 messages for context)
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
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
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
            'created_at': datetime.now(), # Use Firestore server timestamp
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
            query = confessions_ref.order_by('upvotes', direction=firestore.Query.DESC)
        else: # 'latest'
            query = confessions_ref.order_by('created_at', direction=firestore.Query.DESC)
            
        results = query.stream()
        
        public_confessions = []
        for doc in results:
            confession = doc.to_dict()
            confession['id'] = doc.id
            # Firestore timestamp needs to be converted to a string
            confession['created_at'] = confession['created_at'].isoformat()
            public_confessions.append(confession)
            
        return jsonify(public_confessions)
        
    except Exception as e:
        logger.error(f"Error getting confessions: {e}")
        return jsonify([])

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8085))
    app.run(host='0.0.0.0', port=port, debug=True)
