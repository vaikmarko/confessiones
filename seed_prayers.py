import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime

# Initial prayers to seed the database
INITIAL_PRAYERS = [
    {
        "title": "Finding Peace in Anxiety",
        "text": "Lord, I surrender my anxious thoughts to You. In the sleepless nights, remind me that You never slumber. Grant me the peace that transcends understanding as I trust in Your perfect timing.",
        "is_public": True,
        "upvotes": 12,
        "created_at": datetime.now()
    },
    {
        "title": "A Prayer for Forgiveness",
        "text": "Father, I carry a heavy heart today. I ask for the strength to forgive those who have hurt me, just as You have forgiven me. Let bitterness melt away and be replaced by Your grace.",
        "is_public": True,
        "upvotes": 8,
        "created_at": datetime.now()
    },
    {
        "title": "Gratitude for Small Blessings",
        "text": "Thank You, God, for the sunrise this morning and the breath in my lungs. In a world that chases more, teach me to be content with what I have and to see Your hand in every small detail of my life.",
        "is_public": True,
        "upvotes": 15,
        "created_at": datetime.now()
    },
    {
        "title": "Strength for the Weary",
        "text": "I am tired, Lord. The burdens of work and family feel too heavy to carry alone. I come to You for rest. Renew my strength like the eagle's, that I may run and not grow weary.",
        "is_public": True,
        "upvotes": 24,
        "created_at": datetime.now()
    },
    {
        "title": "Hope in Darkness",
        "text": "When I cannot see the path ahead, be my light. When hope feels distant, remind me of Your promises. I trust that You are working all things together for good, even when I cannot see it yet.",
        "is_public": True,
        "upvotes": 31,
        "created_at": datetime.now()
    }
]

def seed_database():
    try:
        # Try to initialize Firebase
        # In production (App Engine), credentials might be auto-discovered or loaded from env
        if not firebase_admin._apps:
            # Try local credentials file first
            cred_path = "firebase-credentials.json"
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("Initialized with local credentials")
            else:
                # If running in cloud, might use default credentials
                firebase_admin.initialize_app()
                print("Initialized with default credentials")
        
        db = firestore.client()
        
        # Check if collection is empty
        docs = db.collection('confessions').limit(1).get()
        if len(list(docs)) > 0:
            print("Database already has prayers. Skipping seed.")
            return

        print("Seeding database with initial prayers...")
        batch = db.batch()
        
        for prayer in INITIAL_PRAYERS:
            doc_ref = db.collection('confessions').document()
            batch.set(doc_ref, prayer)
            
        batch.commit()
        print(f"Successfully added {len(INITIAL_PRAYERS)} prayers!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")

if __name__ == "__main__":
    seed_database()

