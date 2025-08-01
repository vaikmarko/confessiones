# ✝️ Confessiones

A Christian sacramental confession app that provides biblical guidance and spiritual support for the Sacrament of Reconciliation. Experience confession with AI-powered spiritual counseling that draws from Scripture and Christian tradition.

## 🎯 Core Features

- **Sacramental Confession**: Experience the Sacrament of Reconciliation with proper Christian guidance
- **Biblical Counseling**: AI draws from Scripture and Christian tradition for spiritual wisdom
- **Theological Insight**: Deep spiritual understanding based on Church teaching
- **Prayerful Confessions**: Create formal confessions suitable for the sacrament
- **Divine Mercy**: Emphasis on God's infinite mercy and Christ's redemptive power
- **Anonymous & Private**: Keep confessions between you and God, or share to help others

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables** (optional):
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

3. **Run the app**:
   ```bash
   python app.py
   ```

4. **Open in browser**:
   ```
   http://localhost:8085
   ```

## 📱 How It Works

### 1. Sacramental Confession
- Begin with prayer and examination of conscience
- Share your burdens with AI spiritual guidance
- Receive biblical wisdom and theological insight
- Experience God's mercy through Scripture and prayer

### 2. Prepare Confession
- Click "Prepare My Confession" to create a formal confession
- AI crafts a prayerful confession suitable for the sacrament
- Includes biblical references and spiritual depth
- Choose private (between you and God) or share to help others

### 3. Discover Tab
- View public confessions shared by others
- Find spiritual connection and witness God's mercy
- All confessions are anonymous and dignified

## 🏗️ Architecture

### Backend (Flask)
- **Simple API**: Only 4 endpoints for core functionality
- **In-memory storage**: For demo purposes (easily replaceable with database)
- **OpenAI integration**: For AI chat and confession summarization
- **Anonymous sessions**: No user authentication required

### Frontend (React)
- **Clean, focused UI**: Only essential features
- **Mobile-responsive**: Works on all devices
- **Real-time chat**: Smooth conversation flow
- **Simple navigation**: Confess, Discover, and Confession views

## 🔧 API Endpoints

- `POST /api/chat/message` - Handle confession chat
- `POST /api/confessions/create` - Create confession summary
- `GET /api/confessions` - Get public confessions
- `GET /api/confessions/<id>` - Get specific confession

## 🎨 Design Philosophy

- **Sacramental**: Proper Christian confession experience
- **Biblical**: Rooted in Scripture and Christian tradition
- **Mercy**: Emphasizes God's infinite love and forgiveness
- **Dignity**: Maintains the sacred nature of confession
- **Community**: Optional sharing to witness God's mercy

## 🔮 Future Enhancements

- Database integration for persistent storage
- More sophisticated AI prompts
- Confession categories and tags
- Prayer request integration
- Mobile app version

## 📄 License

This project is for spiritual and religious purposes. Use responsibly and with respect for all faiths. 