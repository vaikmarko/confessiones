#!/usr/bin/env python3
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

def fix_fairytale_format():
    """Fix the fairytale format loading issue"""
    
    stories = db.collection('stories').stream()
    
    for story_doc in stories:
        story_data = story_doc.to_dict()
        if 'Accidentally Starting a Tech Company' in story_data.get('title', ''):
            print(f"✅ Found story: {story_data['title']}")
            
            formats = story_data.get('formats', {})
            
            # Check if fairytale format exists
            if 'fairytale' not in formats:
                print("❌ No fairytale format found - creating one")
                
                # Create fairytale format
                fairytale_content = """Once upon a time, in the magical kingdom of Silicon Valley, there lived a young dreamer named Marko. Unlike the other villagers who toiled in ordinary trades, Marko possessed a mysterious gift - the ability to weave enchantments with glowing rectangles called "computers."

One fateful morning, while tinkering in his humble workshop (which he called his "garage"), Marko accidentally spilled a potion of creativity onto his magical coding stones. To his amazement, the stones began to glow and dance, creating wonderful spells that could help people far and wide.

"By the beard of Steve Jobs!" exclaimed Marko, watching as his creation took on a life of its own. What had started as simple magic tricks for friends had transformed into something far more powerful.

Soon, word of Marko's enchanted creation spread throughout the land. Merchants with heavy purses came knocking, offering chests of gold coins for his magical services. Before he knew it, Marko had accidentally founded the most successful spell-crafting guild in all the realm.

And though he never intended to become a merchant-wizard, Marko learned that sometimes the greatest adventures begin with the smallest accidents. He lived happily ever after, casting digital spells and changing the world one line of code at a time.

The End."""

                formats['fairytale'] = {
                    'content': fairytale_content,
                    'created_at': '2025-06-12T16:52:00.000Z',
                    'updated_at': '2025-06-12T16:52:00.000Z'
                }
                
                # Update in database
                db.collection('stories').document(story_doc.id).update({
                    'formats': formats
                })
                
                print("✅ Created fairytale format successfully!")
                return True
            else:
                print("✅ Fairytale format already exists")
                return True
    
    print("❌ Story not found")
    return False

if __name__ == '__main__':
    fix_fairytale_format() 