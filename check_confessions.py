#!/usr/bin/env python3
"""
Quick script to check confession statistics from Firestore
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

print("=" * 60)
print("PIHTIMUSTE STATISTIKA / CONFESSION STATISTICS")
print("=" * 60)

# Get all confessions
confessions_ref = db.collection('confessions')
all_confessions = list(confessions_ref.stream())

print(f"\n📊 ÜLDINE ÜLEVAADE:")
print(f"   Kokku pihtimusi: {len(all_confessions)}")

if len(all_confessions) == 0:
    print("\n❌ Ühtegi pihtimust ei ole veel salvestatud!")
    print("\nVõimalikud põhjused:")
    print("   1. Külastajad ei jõudnud pihtida (lahkusid enne)")
    print("   2. Pihtisid, aga ei salvestanud (vajutasid 'Continue Chatting')")
    print("   3. Tehniline viga takistas salvestamist")
else:
    print(f"\n✅ {len(all_confessions)} pihtimust on andmebaasis!\n")
    
    public_count = 0
    private_count = 0
    
    for doc in all_confessions:
        confession = doc.to_dict()
        if confession.get('is_public', False):
            public_count += 1
        else:
            private_count += 1
    
    print(f"📢 Avalikud (jagatud): {public_count}")
    print(f"🔒 Privaatsed (ainult Jumalale): {private_count}")
    
    print("\n" + "=" * 60)
    print("VIIMASED PIHTIMUSED:")
    print("=" * 60)
    
    # Show last 5 confessions (without revealing private content)
    recent_confessions = sorted(
        [(doc.id, doc.to_dict()) for doc in all_confessions],
        key=lambda x: x[1].get('created_at', datetime.min),
        reverse=True
    )[:5]
    
    for doc_id, confession in recent_confessions:
        created_at = confession.get('created_at')
        if created_at:
            if hasattr(created_at, 'strftime'):
                date_str = created_at.strftime('%Y-%m-%d %H:%M')
            else:
                date_str = str(created_at)
        else:
            date_str = "N/A"
        
        title = confession.get('title', 'Pealkiri puudub')
        is_public = "📢 Avalik" if confession.get('is_public', False) else "🔒 Privaatne"
        upvotes = confession.get('upvotes', 0)
        
        print(f"\n{is_public} | {date_str}")
        print(f"   Pealkiri: {title}")
        print(f"   Upvotes: {upvotes}")
        if confession.get('is_public', False):
            text_preview = confession.get('text', '')[:100]
            print(f"   Tekst: {text_preview}...")

# Check chat sessions
print("\n" + "=" * 60)
print("VESTLUSTE STATISTIKA:")
print("=" * 60)

# Get all users who registered
users_ref = db.collection('users')
all_users = list(users_ref.stream())

print(f"\n👥 Registreeritud kasutajaid: {len(all_users)}")

# Check subscriptions
subscriptions_ref = db.collection('subscriptions')
all_subscriptions = list(subscriptions_ref.stream())

free_tier = 0
premium_tier = 0

for sub_doc in all_subscriptions:
    sub_data = sub_doc.to_dict()
    tier = sub_data.get('tier', 'free')
    if tier == 'unlimited':
        premium_tier += 1
    else:
        free_tier += 1

print(f"\n💎 TELLIMUSSTATISTIKA:")
print(f"   Tasuta kasutajad: {free_tier}")
print(f"   Premium kasutajad: {premium_tier}")

if premium_tier == 0:
    print("\n⚠️  KEEGI EI OLE VEEL PREMIUM LIITUNUD")
    print("\nVõimalikud põhjused:")
    print("   1. Hind ($9.99/kuus) võib olla liiga kõrge")
    print("   2. Väärtuspakkumine pole piisavalt selge")
    print("   3. Usaldus ei ole veel üles ehitatud (liiga vara)")
    print("   4. Tasuta versioon (4 vestlust) on piisav")

print("\n" + "=" * 60)
print("SOOVITUSED:")
print("=" * 60)
print("\n1. 📈 30 külastajat on HEA algus!")
print("2. 🎯 Fookus peaks olema VÄÄRTUSE näitamisel, mitte müügil")
print("3. 💡 Eesmärk: inimesed peavad esmalt PIHTIMA (see on väärtus)")
print("4. 🔄 Alles siis, kui nad näevad väärtust, nad kaaluvad Premium")
print("5. ⏰ Konversioon Premium'sse võib võtta nädalaid/kuid")

print("\n" + "=" * 60)

