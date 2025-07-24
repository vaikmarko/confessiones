#!/usr/bin/env python3
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

def fix_audio_url():
    """Fix the Soul-Tech Revolution audio URL directly"""
    
    # Find the Soul-Tech Revolution story
    stories = db.collection('stories').stream()
    
    for story_doc in stories:
        story_data = story_doc.to_dict()
        if 'Soul-Tech Revolution' in story_data.get('title', ''):
            print(f"Found story: {story_data['title']}")
            
            # Update with a working Firebase Storage URL
            formats = story_data.get('formats', {})
            if 'song' in formats:
                # Set to Firebase Storage URL that will work
                new_audio_url = "https://storage.googleapis.com/sentimental-audio-uploads/audio/UkZDy4mzTrlkivZgbkGZ_song_working.mp3"
                
                if isinstance(formats['song'], str):
                    formats['song'] = {
                        'content': formats['song'],
                        'audio_url': new_audio_url,
                        'storage_type': 'firebase'
                    }
                else:
                    formats['song']['audio_url'] = new_audio_url
                    formats['song']['storage_type'] = 'firebase'
                
                # Update in database
                db.collection('stories').document(story_doc.id).update({
                    'formats': formats
                })
                
                print(f"✅ Fixed audio URL to: {new_audio_url}")
                return True
    
    print("❌ Story not found")
    return False

if __name__ == '__main__':
    fix_audio_url() 