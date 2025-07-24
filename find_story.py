#!/usr/bin/env python3
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

def find_stories():
    """Find all stories and their audio URLs"""
    
    stories = db.collection('stories').stream()
    
    print("All stories:")
    for story_doc in stories:
        story_data = story_doc.to_dict()
        title = story_data.get('title', 'No title')
        print(f"\n📖 {title}")
        
        formats = story_data.get('formats', {})
        if 'song' in formats:
            song_format = formats['song']
            if isinstance(song_format, dict):
                audio_url = song_format.get('audio_url', 'No audio URL')
                print(f"   🎵 Audio: {audio_url}")
            else:
                print(f"   🎵 Song format: {song_format}")
        else:
            print("   ❌ No song format")

if __name__ == '__main__':
    find_stories() 