#!/usr/bin/env python3
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

def fix_tech_company_audio():
    """Fix the Tech Company story audio URL directly"""
    
    stories = db.collection('stories').stream()
    
    for story_doc in stories:
        story_data = story_doc.to_dict()
        if 'Accidentally Starting a Tech Company' in story_data.get('title', ''):
            print(f"✅ Found story: {story_data['title']}")
            
            formats = story_data.get('formats', {})
            if 'song' in formats:
                # Update with a working audio URL - use the file that was uploaded earlier
                # Since we have Firebase Storage set up, let's point to that
                new_audio_url = "https://storage.googleapis.com/sentimental-audio-uploads/audio/UkZDy4mzTrlkivZgbkGZ_song_20250612_153935_f84ffab5-cc5d-4c76-b4c4-80217c8665ed.mp3"
                
                formats['song']['audio_url'] = new_audio_url
                formats['song']['storage_type'] = 'firebase'
                formats['song']['audio_uploaded_at'] = '2025-06-12T16:50:00.000Z'
                
                # Update in database
                db.collection('stories').document(story_doc.id).update({
                    'formats': formats
                })
                
                print(f"🎵 Fixed audio URL to Firebase Storage:")
                print(f"   {new_audio_url}")
                return True
    
    print("❌ Story not found")
    return False

if __name__ == '__main__':
    fix_tech_company_audio() 