# 🚀 Simple Deployment Guide

## 🏗️ Clean Architecture

```
LOCAL DEVELOPMENT ─→ PRODUCTION
     ↓                    ↓
python app.py      sentimentalapp.com
(localhost:5000)   (Firebase + Cloud Run)
```

## 🔧 Two Commands Only

### 1. **Local Development**
```bash
python app.py
# Opens on http://localhost:5000
```

### 2. **Deploy to Production**
```bash
# Deploy backend
gcloud run deploy sentimentalapp \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY="$(python3 -c "import os; from dotenv import load_dotenv; load_dotenv('functions/.env'); load_dotenv(); print(os.getenv('OPENAI_API_KEY'))")"

# Deploy frontend
firebase deploy --only hosting
```

## 📁 What Each Service Does

### **Flask App (`app.py`)**
- **Local**: Python development server
- **Production**: Single Cloud Run service `sentimentalapp` 
- **Does**: API endpoints, story generation, format creation
- **Database**: Firebase Firestore
- **AI**: OpenAI GPT

### **Frontend**
- **Local**: Served by Flask (`/static/` and `/templates/`)
- **Production**: Firebase Hosting → routes API calls to Cloud Run
- **Files**: `public/` directory, `firebase.json` config

## 🌍 Production URLs

- **Main Site**: https://sentimentalapp.com (custom domain)
- **Firebase URL**: https://sentimental-f95e6.web.app (backup)
- **Backend API**: https://sentimentalapp-319737737925.europe-west1.run.app (direct)

## ✅ Current Status: CLEAN

- ❌ **Deleted**: 5 unnecessary services (test, demo, backend, duplicates)
- ✅ **Active**: 1 production service only
- ✅ **Domain**: sentimentalapp.com → Firebase → Cloud Run
- ✅ **Fixed**: Twitter→X migration complete

## 🔍 How to Check Everything Works

```bash
# Test API
curl "https://sentimentalapp.com/api/formats/supported" | grep -o '"x"'
# Should return: "x" (not "twitter")

# Test local
python app.py &
curl "http://localhost:5000/api/formats/supported" | grep -o '"x"'
```

## 🚨 If Something Breaks

1. **Local not working**: Check `functions/.env` has `OPENAI_API_KEY`
2. **Production not working**: Redeploy with the command above
3. **Still confused**: Only 1 service exists now! `sentimentalapp` in `europe-west1`

---
**That's it! No more multiple services, no more confusion!** 🎯 