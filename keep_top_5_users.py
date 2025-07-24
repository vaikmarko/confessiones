#!/usr/bin/env python3
"""
Keep Top 5 Users Script:
Analyze all users and keep only the 5 with most engaging Gen Z stories and longest chats
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json

# Initialize Firebase (only once)
if not firebase_admin._apps:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)
db = firestore.client()

def analyze_user_engagement():
    """Analyze all users to find the most engaging ones for Gen Z"""
    
    print("🔍 ANALYZING USER ENGAGEMENT FOR GEN Z APPEAL")
    print("=" * 60)
    
    users = db.collection('test_users').get()
    stories = db.collection('stories').get()
    chats = db.collection('chats').get()
    
    user_analysis = []
    
    for user_doc in users:
        user_data = user_doc.to_dict()
        user_id = user_doc.id
        user_name = user_data.get('name', 'Unknown')
        
        # Get user's stories and chats
        user_stories = [s for s in stories if s.to_dict().get('user_id') == user_id]
        user_chats = [c for c in chats if c.to_dict().get('user_id') == user_id]
        
        if not user_stories:
            continue  # Skip users without stories
        
        story_data = user_stories[0].to_dict()  # Get the story
        title = story_data.get('title', '')
        content = story_data.get('content', '')
        
        # Calculate engagement score based on Gen Z appeal
        engagement_score = calculate_gen_z_engagement(title, content, len(user_chats))
        
        user_analysis.append({
            'user_id': user_id,
            'name': user_name,
            'title': title,
            'content_length': len(content),
            'chat_count': len(user_chats),
            'engagement_score': engagement_score,
            'story_data': story_data
        })
        
        print(f"📊 {user_name}")
        print(f"   Title: {title}")
        print(f"   Chats: {len(user_chats)} | Content: {len(content)} chars")
        print(f"   Engagement Score: {engagement_score:.2f}")
        print()
    
    # Sort by engagement score (highest first)
    user_analysis.sort(key=lambda x: x['engagement_score'], reverse=True)
    
    return user_analysis

def calculate_gen_z_engagement(title, content, chat_count):
    """Calculate engagement score based on Gen Z appeal factors"""
    
    score = 0
    content_lower = content.lower()
    title_lower = title.lower()
    
    # Chat count factor (more chats = more engaging conversations)
    chat_score = min(chat_count * 2, 30)  # Max 30 points for chats
    score += chat_score
    
    # Content length factor (substantial stories score higher)
    length_score = min(len(content) / 100, 20)  # Max 20 points for length
    score += length_score
    
    # Gen Z relevant themes (high appeal topics)
    gen_z_themes = {
        'career_anxiety': ['job', 'career', 'first day', 'work', 'interview', 'employment', 'boss'],
        'mental_health': ['anxiety', 'depression', 'therapy', 'stress', 'mental health', 'panic'],
        'relationships': ['dating', 'relationship', 'breakup', 'love', 'friendship', 'friend'],
        'identity': ['figuring out', 'who i am', 'identity', 'authentic', 'real me', 'discovering'],
        'social_media': ['social media', 'instagram', 'online', 'fake', 'image'],
        'family_pressure': ['parents', 'family', 'expectations', 'pressure', 'disappoint'],
        'college_life': ['college', 'university', 'student', 'grad', 'graduation'],
        'creativity': ['art', 'creative', 'artist', 'music', 'writing', 'passion'],
        'burnout': ['burnout', 'exhausted', 'overwhelmed', 'tired', 'workaholic'],
        'life_direction': ['direction', 'path', 'future', 'goals', 'lost', 'confused']
    }
    
    # Score based on relevant themes
    for theme, keywords in gen_z_themes.items():
        if any(keyword in content_lower or keyword in title_lower for keyword in keywords):
            score += 15  # High bonus for relevant themes
    
    # Title appeal (authentic, relatable titles score higher)
    title_appeal_words = [
        'navigating', 'figuring out', 'discovering', 'my journey', 'first day',
        'dealing with', 'learning to', 'why i', 'how i', 'the truth about'
    ]
    
    for appeal_word in title_appeal_words:
        if appeal_word in title_lower:
            score += 10
    
    # Authenticity markers (personal, vulnerable language)
    authenticity_markers = [
        'i realized', 'i learned', 'i discovered', 'honestly', 'real talk',
        'not gonna lie', 'tbh', 'i felt', 'it hit me', 'i understood'
    ]
    
    for marker in authenticity_markers:
        if marker in content_lower:
            score += 5
    
    # Penalize overly formal or poetic language (less Gen Z appeal)
    formal_words = ['furthermore', 'moreover', 'subsequently', 'henceforth', 'magnificent']
    for word in formal_words:
        if word in content_lower:
            score -= 10
    
    return score

def keep_top_5_users(user_analysis):
    """Keep only the top 5 users and delete the rest"""
    
    print("🏆 TOP 5 MOST ENGAGING USERS FOR GEN Z")
    print("=" * 50)
    
    top_5 = user_analysis[:5]
    users_to_delete = user_analysis[5:]
    
    print("✅ KEEPING THESE 5 USERS:")
    for i, user in enumerate(top_5, 1):
        print(f"{i}. {user['name']} (Score: {user['engagement_score']:.1f})")
        print(f"   📖 \"{user['title']}\"")
        print(f"   💬 {user['chat_count']} chats | 📝 {user['content_length']} chars")
        print()
    
    print(f"🗑️  DELETING {len(users_to_delete)} OTHER USERS:")
    for user in users_to_delete:
        print(f"   ❌ {user['name']} (Score: {user['engagement_score']:.1f})")
    
    # Confirm deletion
    print(f"\n🚨 This will delete {len(users_to_delete)} users and their content.")
    confirm = input("Proceed? (yes/no): ").lower().strip()
    
    if confirm != 'yes':
        print("❌ Operation cancelled")
        return
    
    # Delete users, stories, and chats for non-top-5 users
    deleted_users = 0
    deleted_stories = 0 
    deleted_chats = 0
    
    for user in users_to_delete:
        user_id = user['user_id']
        
        try:
            # Delete user's stories
            stories = db.collection('stories').where('user_id', '==', user_id).get()
            for story in stories:
                story.reference.delete()
                deleted_stories += 1
            
            # Delete user's chats
            chats = db.collection('chats').where('user_id', '==', user_id).get()
            for chat in chats:
                chat.reference.delete()
                deleted_chats += 1
            
            # Delete user
            db.collection('test_users').document(user_id).delete()
            deleted_users += 1
            
            print(f"🗑️  Deleted: {user['name']}")
            
        except Exception as e:
            print(f"❌ Error deleting {user['name']}: {e}")
    
    print(f"\n📊 CLEANUP COMPLETE:")
    print(f"   🗑️  Users deleted: {deleted_users}")
    print(f"   📖 Stories deleted: {deleted_stories}")
    print(f"   💬 Chats deleted: {deleted_chats}")
    print(f"   ✅ Top 5 users kept with highest Gen Z engagement!")

def verify_final_state():
    """Verify the final state"""
    
    print(f"\n🔍 FINAL DATABASE STATE")
    print("=" * 30)
    
    users = db.collection('test_users').get()
    stories = db.collection('stories').get()
    chats = db.collection('chats').get()
    
    print(f"👥 Users: {len(users)}")
    print(f"📖 Stories: {len(stories)}")
    print(f"💬 Chats: {len(chats)}")
    
    print(f"\n👥 REMAINING USERS:")
    for user_doc in users:
        user_data = user_doc.to_dict()
        user_name = user_data.get('name', 'Unknown')
        
        user_stories = [s for s in stories if s.to_dict().get('user_id') == user_doc.id]
        user_chats = [c for c in chats if c.to_dict().get('user_id') == user_doc.id]
        
        if user_stories:
            story_title = user_stories[0].to_dict().get('title', 'No title')
            print(f"  ✓ {user_name} - {len(user_stories)} stories, {len(user_chats)} chats")
            print(f"    📖 \"{story_title}\"")
        else:
            print(f"  ✓ {user_name} - No stories, {len(user_chats)} chats")

def main():
    print("🎯 KEEP TOP 5 MOST ENGAGING USERS")
    print("=" * 50)
    print("This will analyze all users and keep only the 5 most")
    print("engaging for Gen Z with longest chats and best stories.")
    print()
    
    # Analyze all users
    user_analysis = analyze_user_engagement()
    
    if len(user_analysis) <= 5:
        print(f"⚠️  Only {len(user_analysis)} users found. Nothing to delete.")
        return
    
    # Keep top 5
    keep_top_5_users(user_analysis)
    
    # Verify final state
    verify_final_state()
    
    print("\n🎉 SUCCESS! Database now contains the 5 most engaging users for Gen Z!")

if __name__ == "__main__":
    main() 