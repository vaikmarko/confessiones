#!/usr/bin/env python3
"""
Detailed analysis of confession and user activity with exact dates
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta

# Initialize Firebase
try:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)
except:
    pass  # Already initialized

db = firestore.client()

print("=" * 80)
print("DETAILNE ANALÜÜS - MILLAL TEGELIKULT KASUTAJAD AKTIIVSED OLID")
print("=" * 80)

# Get all confessions with full details
confessions_ref = db.collection('confessions')
all_confessions = list(confessions_ref.stream())

print(f"\n📅 KÕIK PIHTIMUSED KUUPÄEVADE JÄRGI:\n")
print("-" * 80)

confessions_by_date = []
for doc in all_confessions:
    confession = doc.to_dict()
    created_at = confession.get('created_at')
    
    if created_at:
        if hasattr(created_at, 'strftime'):
            date_obj = created_at
            date_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
        else:
            try:
                date_obj = datetime.fromisoformat(str(created_at))
                date_str = str(created_at)
            except:
                date_obj = datetime.min
                date_str = "Unknown date"
    else:
        date_obj = datetime.min
        date_str = "No date"
    
    confessions_by_date.append({
        'date': date_obj,
        'date_str': date_str,
        'title': confession.get('title', 'No title'),
        'is_public': confession.get('is_public', False),
        'session_id': confession.get('session_id', 'unknown'),
        'upvotes': confession.get('upvotes', 0)
    })

# Sort by date
confessions_by_date.sort(key=lambda x: x['date'], reverse=True)

# Categorize by time period
from datetime import timezone
now = datetime.now(timezone.utc)
today = []
last_week = []
last_month = []
older = []

for conf in confessions_by_date:
    if conf['date'] == datetime.min:
        age_days = 9999
    else:
        # Make both timezone aware for comparison
        conf_date = conf['date']
        if conf_date.tzinfo is None:
            conf_date = conf_date.replace(tzinfo=timezone.utc)
        age_days = (now - conf_date).days
    
    if age_days < 1:
        today.append(conf)
    elif age_days < 7:
        last_week.append(conf)
    elif age_days < 30:
        last_month.append(conf)
    else:
        older.append(conf)

print(f"📊 KOKKUVÕTE:")
print(f"   Täna (viimased 24h):     {len(today)} pihtimust")
print(f"   Viimane nädal:           {len(last_week)} pihtimust")
print(f"   Viimane kuu:             {len(last_month)} pihtimust")
print(f"   Vanemad (ilmselt testid): {len(older)} pihtimust")

print("\n" + "=" * 80)
print("TÄNA/HILJUTI (võimalikud päris kasutajad):")
print("=" * 80)
for conf in today:
    print(f"\n⏰ {conf['date_str']}")
    print(f"   📝 {conf['title']}")
    print(f"   {'📢 Avalik' if conf['is_public'] else '🔒 Privaatne'}")
    print(f"   Session: {conf['session_id'][:20]}...")

if last_week:
    print("\n" + "=" * 80)
    print("VIIMANE NÄDAL:")
    print("=" * 80)
    for conf in last_week:
        print(f"\n⏰ {conf['date_str']}")
        print(f"   📝 {conf['title']}")

print("\n" + "=" * 80)
print("VANAD TESTID/DEMOED (enne kampaaniat):")
print("=" * 80)
for conf in older:
    print(f"\n⏰ {conf['date_str']}")
    print(f"   📝 {conf['title']}")
    print(f"   ❤️ Upvotes: {conf['upvotes']}")

# Check users
print("\n" + "=" * 80)
print("KASUTAJAD JA NENDE REGISTREERIMISE AJAD:")
print("=" * 80)

users_ref = db.collection('users')
all_users = list(users_ref.stream())

users_by_date = []
for user_doc in all_users:
    user_data = user_doc.to_dict()
    created_at = user_data.get('created_at')
    
    if created_at:
        if hasattr(created_at, 'strftime'):
            date_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
            date_obj = created_at
        else:
            date_str = str(created_at)
            try:
                date_obj = datetime.fromisoformat(str(created_at))
            except:
                date_obj = datetime.min
    else:
        date_str = "No date"
        date_obj = datetime.min
    
    users_by_date.append({
        'date': date_obj,
        'date_str': date_str,
        'email': user_data.get('email', 'No email'),
        'name': user_data.get('name', 'No name'),
        'tier': user_data.get('tier', 'free')
    })

users_by_date.sort(key=lambda x: x['date'], reverse=True)

for user in users_by_date:
    tier_icon = "💎" if user['tier'] == 'unlimited' else "🆓"
    print(f"\n{tier_icon} {user['date_str']}")
    print(f"   {user['name']} ({user['email']})")
    print(f"   Tier: {user['tier']}")

# Check subscriptions
print("\n" + "=" * 80)
print("STRIPE SUBSCRIPTION INFO:")
print("=" * 80)

subscriptions_ref = db.collection('subscriptions')
all_subscriptions = list(subscriptions_ref.stream())

print(f"\nKokku subscription kirjeid: {len(all_subscriptions)}\n")

for sub_doc in all_subscriptions:
    sub_data = sub_doc.to_dict()
    updated_at = sub_data.get('updated_at')
    
    if updated_at and hasattr(updated_at, 'strftime'):
        date_str = updated_at.strftime('%Y-%m-%d %H:%M:%S')
    else:
        date_str = str(updated_at) if updated_at else "No date"
    
    print(f"Session ID: {sub_doc.id}")
    print(f"   Tier: {sub_data.get('tier', 'unknown')}")
    print(f"   Updated: {date_str}")
    print(f"   Customer ID: {sub_data.get('customer_id', 'None')}")
    print(f"   Subscription ID: {sub_data.get('subscription_id', 'None')}")
    print()

print("=" * 80)
print("🎯 JÄRELDUSED:")
print("=" * 80)

recent_real_users = len(today) + len(last_week)
print(f"\n1. PÄRIS KASUTAJAID (hiljutised): {recent_real_users}")
print(f"2. VANU TESTE/DEMOSID: {len(older)}")
print(f"3. REGISTREERITUD KASUTAJAID: {len(all_users)}")

premium_users = [u for u in users_by_date if u['tier'] == 'unlimited']
print(f"4. PREMIUM KASUTAJAID: {len(premium_users)}")

if len(premium_users) > 0 and all(sub_data.get('customer_id') == 'None' or not sub_data.get('customer_id') for sub_data in [s.to_dict() for s in all_subscriptions]):
    print("\n⚠️  TÄHELEPANU: Premium kasutajad ILMA Stripe customer ID-ta!")
    print("   → Need on ilmselt TEST kasutajad või webhook ei käivitunud")

print("\n" + "=" * 80)

