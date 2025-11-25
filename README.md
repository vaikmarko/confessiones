# ✝️ **My Confessions**

## Biblical Guidance for Your Spiritual Journey

A Christian spiritual guidance ministry providing 24/7 Scripture-based support to help believers examine their hearts, find Biblical wisdom, and grow in their walk with Christ.

---

## 🌟 **Features**

- **24/7 Biblical Guidance** - Scripture-based spiritual conversations anytime
- **AI-Powered** - Uses OpenAI to provide thoughtful, faith-centered responses
- **Prayer Generation** - Creates beautiful, personalized prayers from your conversations
- **Community Prayers** - Share and read prayers from fellow believers (Premium)
- **Value-First Model** - 4 free conversations before upgrade prompt
- **Secure Payments** - Stripe integration for premium membership
- **Anonymous & Safe** - No login required for basic use
- **Mobile Responsive** - Works perfectly on all devices

---

## 🚀 **Quick Start**

### **1. Install Dependencies**
```bash
pip3 install -r requirements.txt
```

### **2. Set Up Environment**
```bash
# Copy environment template
cp .env.example .env

# Add your API keys to .env:
# - OPENAI_API_KEY
# - STRIPE_SECRET_KEY  
# - STRIPE_PUBLISHABLE_KEY
# - STRIPE_PRICE_ID_UNLIMITED (optional for testing)
```

### **3. Add Firebase Credentials**
- Download service account JSON from Firebase Console
- Save as `firebase-credentials.json` in project root

### **4. Run the App**
```bash
python3 app.py
```

Open http://localhost:5000 in your browser!

---

## 📚 **Documentation**

- **[QUICK_START.md](QUICK_START.md)** - Get running in 10 minutes
- **[SOFTWARE_TEST_REPORT.md](SOFTWARE_TEST_REPORT.md)** - Complete test results
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Production deployment guide
- **[FINAL_CHECKLIST.md](FINAL_CHECKLIST.md)** - Pre-launch checklist
- **[CHRISTIAN_VALUE_POSITIONING.md](CHRISTIAN_VALUE_POSITIONING.md)** - Positioning strategy
- **[PSYCHOLOGY_CONVERSION_OPTIMIZATION.md](PSYCHOLOGY_CONVERSION_OPTIMIZATION.md)** - Conversion psychology

---

## 🛠 **Tech Stack**

### **Backend**
- **Flask** - Python web framework
- **OpenAI API** - AI-powered Biblical guidance
- **Stripe** - Payment processing
- **Firebase/Firestore** - Database & user management

### **Frontend**
- **React** - UI framework
- **Tailwind CSS** - Styling
- **Babel** - JSX transpiler

---

## 💎 **Premium Features**

Free users get:
- ✅ Up to 4 conversations per month
- ✅ Can write own prayers
- ❌ Cannot see shared community prayers
- ❌ Conversations not saved

Premium members get:
- ✅ **Unlimited Biblical guidance 24/7**
- ✅ **Access all community prayers**
- ✅ **Spiritual journey preserved**
- ✅ **Priority support**
- ✅ **Support faith-based ministry**

**Pricing:** $9.99/month or $99/year (save 17%)

---

## 🔒 **Security**

- Environment variables for sensitive data
- HTTPS required for production
- Stripe PCI-compliant payments
- Firebase security rules
- No credit card data touches our servers

---

## 📊 **Project Structure**

```
myconfessions/
├── app.py                      # Flask backend
├── static/
│   ├── js/
│   │   └── myconfessions-app.jsx # React frontend
│   └── css/
│       └── components.css      # Styles
├── templates/
│   ├── app.html               # Main app template
│   ├── terms.html             # Terms of Service
│   ├── privacy.html           # Privacy Policy
│   └── ...
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not in git!)
├── firebase-credentials.json  # Firebase key (not in git!)
├── Procfile                   # Heroku deployment
├── app.yaml                   # Google Cloud deployment
└── README.md                  # This file
```

---

## 🚀 **Deployment**

### **Heroku**
```bash
git push heroku main
```

### **Google Cloud**
```bash
gcloud app deploy
```

### **VPS (with Gunicorn)**
```bash
gunicorn -w 4 app:app
```

See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for detailed instructions.

---

## 🧪 **Testing**

### **Local Testing**
```bash
# Run app
python3 app.py

# Test API endpoints
curl http://localhost:5000/api/user/tier

# Test tier upgrade
curl http://localhost:5000/api/test/set-tier/unlimited
```

### **Stripe Testing**
Use test card: `4242 4242 4242 4242`
- Any future expiry date
- Any 3-digit CVC
- Any ZIP code

---

## 📈 **Analytics & Monitoring**

Track key metrics:
- Free tier usage (4 message limit)
- Upgrade conversion rate
- Monthly vs Annual split
- User retention
- Error rate

Recommended tools:
- Google Analytics (web traffic)
- Stripe Dashboard (payments)
- Firebase Console (database)
- Sentry (error tracking)

---

## 🤝 **Contributing**

This is a private ministry project. If you'd like to help:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

## 📄 **License**

Proprietary - All rights reserved

This software is for the exclusive use of My Confessions ministry. Unauthorized copying, modification, distribution, or use is strictly prohibited.

---

## 🙏 **Mission Statement**

**God has given us technology to draw closer to Him.**

We provide 24/7 Scripture-based spiritual guidance to help believers examine their hearts, find Biblical wisdom, and grow in their walk with Christ. Your partnership helps us serve thousands seeking God's truth and grace.

---

## 📞 **Support**

- **Email:** support@myconfessions.org
- **Website:** https://myconfessions.org
- **Stripe Support:** https://support.stripe.com/
- **Firebase Support:** https://firebase.google.com/support

---

## ✅ **Tested & Ready**

- ✅ **79/79 tests passing**
- ✅ **Backend fully functional**
- ✅ **Frontend optimized**
- ✅ **Christian positioning implemented**
- ✅ **Conversion psychology optimized**
- ✅ **Production ready**

See [SOFTWARE_TEST_REPORT.md](SOFTWARE_TEST_REPORT.md) for complete test results.

---

## 🎯 **Development Status**

```
Backend:        ✅ Complete (1,060 lines)
Frontend:       ✅ Complete (1,609 lines)
Stripe:         ✅ Integrated
Firebase:       ✅ Connected
OpenAI:         ✅ Working
Documentation:  ✅ Comprehensive
Testing:        ✅ 100% pass rate
Production:     ⚠️  Needs final setup
```

---

## 📅 **Version History**

- **v2.0** (Oct 2025) - Christian positioning, conversion optimization
- **v1.5** (Sep 2025) - Stripe subscription model
- **v1.0** (Jul 2025) - Initial release

---

**🎉 Built with ❤️ and 🙏 to serve God's kingdom through technology**

**Last Updated:** October 9, 2025  
**Version:** 2.0 - Production Ready
