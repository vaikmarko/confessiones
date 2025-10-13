const { useState, useEffect, useMemo } = React;

const MyConfessionsApp = () => {
  const [currentView, setCurrentView] = useState('confess');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(`session_${Math.random().toString(36).substr(2, 9)}`);
  const [confessions, setConfessions] = useState([]);
  const [upvotedConfessions, setUpvotedConfessions] = useState(new Set());
  const [confessionFilter, setConfessionFilter] = useState('latest');
  const [currentConfession, setCurrentConfession] = useState(null);
  const [soulsHelped, setSoulsHelped] = useState(10000); // Base number to start with
  const [copiedPrayerId, setCopiedPrayerId] = useState(null);
  const [generatedSummary, setGeneratedSummary] = useState({ title: '', prayer: '' });
  
  // Value-first service model state
  const [userTier, setUserTier] = useState('free');
  const [conversationDepth, setConversationDepth] = useState(0);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState(null);
  
  // Pricing psychology state
  const [selectedPlan, setSelectedPlan] = useState('monthly'); // 'monthly' or 'annual'
  
  // User authentication state
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [userName, setUserName] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userSessionId, setUserSessionId] = useState('');

  // Load public confessions and stats
  useEffect(() => {
    fetchConfessions(confessionFilter);
  }, [confessionFilter]);


  const fetchConfessions = async (filter) => {
    try {
      const response = await fetch(`/api/confessions?sort=${filter}`);
      if (response.ok) {
        const data = await response.json();
        setConfessions(data);
      }
    } catch (error) {
      console.error('Error fetching confessions:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;
    
    const userMessage = inputMessage;
    setInputMessage('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const currentSessionId = isLoggedIn ? userSessionId : sessionId;
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          session_id: currentSessionId,
          conversation_history: messages
        })
      });

      const data = await response.json();
      if (data.success) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
        // Update value-first service state
        setUserTier(data.tier || 'free');
        setConversationDepth(data.conversation_depth || 0);
        
        // Handle upgrade suggestion (value-first approach)
        if (data.suggest_upgrade) {
          setUpgradeMessage(data.upgrade_message);
          setShowUpgradeModal(true);
        }
      } else {
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: 'Sorry, I encountered an error. Please try again.' 
        }]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.' 
      }]);
    }
    setIsLoading(false);
  };

const handleSharePrayer = (confession) => {
    const shareText = `A prayer from MyConfessions.org:\n\n"${confession.title}"\n\n${confession.text}\n\nFind peace and share your own prayer at https://myconfessions.org`;
    navigator.clipboard.writeText(shareText).then(() => {
        setCopiedPrayerId(confession.id);
        setTimeout(() => setCopiedPrayerId(null), 2000); // Reset after 2 seconds
    }).catch(err => {
        console.error('Failed to copy prayer:', err);
        alert('Failed to copy prayer.');
    });
  };

  const handleUpvoteClick = async (confessionId) => {
    if (upvotedConfessions.has(confessionId)) {
      // Already upvoted in this session, do nothing.
      return;
    }

    try {
      const response = await fetch(`/api/confessions/${confessionId}/upvote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        // Optimistically update the UI
        const newConfessions = confessions.map(c => {
          if (c.id === confessionId) {
            return { ...c, upvotes: (c.upvotes || 0) + 1 };
          }
          return c;
        });
        setConfessions(newConfessions);
        
        // Record the upvote to prevent re-voting
        setUpvotedConfessions(prev => new Set(prev).add(confessionId));
      }
    } catch (error) {
      console.error('Error upvoting confession:', error);
    }
  };

  const handleSummarizeClick = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/chat/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_history: messages })
      });
      const data = await response.json();
      if (data.success) {
        setGeneratedSummary({ title: data.title, prayer: data.prayer });
        setCurrentView('review');
      } else {
        alert(data.error || 'Could not generate summary.');
      }
    } catch (error) {
      alert('An error occurred while generating the summary.');
    }
    setIsLoading(false);
  };

  const handleSaveConfession = async (isPublic) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/confessions/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          is_public: isPublic,
          title: generatedSummary.title,
          confession_text: generatedSummary.prayer
        })
      });

      const data = await response.json();
      if (data.success) {
        setCurrentConfession(data.confession);
        setMessages([]);
        setGeneratedSummary('');
        if (isPublic) {
          await fetchConfessions();
        }
        setCurrentView('confession');
      } else {
        alert(data.error || 'Could not save confession.');
      }
    } catch (error) {
      alert('An error occurred while saving the confession.');
    }
    setIsLoading(false);
  };

  const renderConfess = () => (
    <div className="flex flex-col h-full bg-gradient-to-b from-blue-50 to-white pb-20">
      {/* Header */}
      <div className="relative overflow-hidden">
        <div className="bg-blue-700 text-white p-6 text-center relative">

          <div className="relative z-10">
            <div className="text-3xl mb-3">✝️</div>
            <h1 className="text-3xl font-bold mb-2 tracking-tight text-white drop-shadow-lg">My Confessions</h1>
            <p className="text-white font-medium text-lg drop-shadow-md">Biblical Guidance for Your Spiritual Journey</p>
            
            {/* Scripture Quote - Inspirational */}
            <div className="bg-white bg-opacity-20 backdrop-blur-sm rounded-lg p-3 mt-4 max-w-lg mx-auto border border-white border-opacity-30">
              <p className="text-sm text-white italic leading-relaxed">
                "If we confess our sins, He is faithful and just to forgive us our sins and to cleanse us from all unrighteousness."
              </p>
              <p className="text-xs text-white font-semibold mt-2">— 1 John 1:9</p>
            </div>
            
            {/* Stats */}
            <div className="flex justify-center space-x-8 mt-6 text-sm">
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-300 drop-shadow-lg">10,000+</div>
                <div className="text-white font-medium drop-shadow-md">Souls Helped</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-300 drop-shadow-lg">24/7</div>
                <div className="text-white font-medium drop-shadow-md">Spiritual Support</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-300 drop-shadow-lg">100%</div>
                <div className="text-white font-medium drop-shadow-md">Anonymous</div>
              </div>
            </div>
            
            {/* Compact Login Status - Subtle */}
            <div className="mt-6 flex justify-center">
              {!isLoggedIn ? (
                <div className="text-center">
                  <p className="text-white text-sm opacity-75 mb-2">Save your progress</p>
                  <div className="flex space-x-3">
                  <button
                    onClick={() => setShowLoginModal(true)}
                      className="bg-white bg-opacity-25 hover:bg-opacity-35 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200"
                  >
                      Sign In
                  </button>
                  <button
                    onClick={() => setShowRegisterModal(true)}
                      className="bg-white hover:bg-gray-300 text-blue-950 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200"
                  >
                      Sign Up
                  </button>
                  </div>
                </div>
              ) : (
                <div className="text-center">
                  <p className="text-white text-sm opacity-90">Welcome, {userName || userEmail}!</p>
                  <button
                    onClick={() => setIsLoggedIn(false)}
                    className="text-white text-xs underline hover:no-underline mt-1 opacity-75 hover:opacity-100"
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
          </div>
        </div>

      {/* Value Proposition - Clear Benefits */}
      <div className="bg-white mx-4 mt-4 rounded-xl shadow-lg overflow-hidden border border-gray-500">
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 p-4 text-center">
          <h2 className="text-xl font-bold text-white">Choose Your Spiritual Path</h2>
        </div>
        
        {/* Comparison Cards */}
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Free Tier */}
          <div className="border-2 border-gray-500 rounded-lg p-4 bg-gray-300">
            <h3 className="text-lg font-bold text-gray-900 mb-3 text-center">Free User</h3>
            <div className="text-sm text-gray-700 space-y-2">
              <div className="flex items-start">
                <span className="text-gray-600 mr-2">▪</span>
                <span className="text-gray-700">Up to 4 conversations per month</span>
              </div>
              <div className="flex items-start">
                <span className="text-gray-600 mr-2">▪</span>
                <span className="text-gray-700">Can write your own prayers</span>
              </div>
              <div className="flex items-start">
                <span className="text-red-500 mr-2">✗</span>
                <span className="text-gray-600">Cannot see other prayers</span>
              </div>
              <div className="flex items-start">
                <span className="text-red-500 mr-2">✗</span>
                <span className="text-gray-600">Conversations not saved</span>
              </div>
            </div>
          </div>
          
          {/* Premium Tier */}
          <div className="border-2 border-blue-600 rounded-lg p-4 bg-gradient-to-br from-blue-100 to-white relative">
            <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-yellow-400 text-blue-950 text-xs font-bold px-3 py-1 rounded-full shadow-lg">
              ⭐ RECOMMENDED
            </div>
            <h3 className="text-lg font-bold text-blue-950 mb-2 flex items-center justify-center mt-2">
              💎 Premium User
              <span className="ml-2 text-sm font-normal text-gray-600">$9.99/mo</span>
            </h3>
            <div className="text-sm text-gray-900 space-y-2 mb-4">
              <div className="flex items-start">
                <span className="text-green-900 mr-2">✓</span>
                <span className="font-medium text-gray-900">UNLIMITED Biblical guidance 24/7</span>
              </div>
              <div className="flex items-start">
                <span className="text-green-900 mr-2">✓</span>
                <span className="font-medium text-gray-900">See ALL shared prayers & testimonies</span>
              </div>
              <div className="flex items-start">
                <span className="text-green-900 mr-2">✓</span>
                <span className="font-medium text-gray-900">Find strength in community faith</span>
              </div>
              <div className="flex items-start">
                <span className="text-green-900 mr-2">✓</span>
                <span className="font-medium text-gray-900">Your spiritual journey saved</span>
              </div>
              <div className="flex items-start">
                <span className="text-green-900 mr-2">✓</span>
                <span className="font-medium text-gray-900">Support God's work through technology</span>
              </div>
            </div>
            <button
            onClick={() => setCurrentView('subscription')}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg font-bold transition-all duration-200 shadow-md"
            >
              Join Premium
            </button>
          </div>
      </div>
      
        {/* Mission Statement - Positive & Value-Focused */}
        <div className="p-4 bg-gradient-to-br from-blue-100 to-white border-t border-blue-200">
          <div className="max-w-2xl mx-auto text-center">
            <p className="text-sm text-gray-900 leading-relaxed mb-2">
              <strong className="text-blue-950">God has given us technology to draw closer to Him.</strong>
            </p>
            <p className="text-xs text-gray-700 leading-relaxed">
              We provide 24/7 Scripture-based spiritual guidance to help believers examine their hearts, 
              find Biblical wisdom, and grow in their walk with Christ. Your partnership helps us serve 
              thousands seeking God's truth and grace.
            </p>
          </div>
        </div>
      </div>
      
      {/* Value-first conversation depth display with Progress Bar */}
      {userTier === 'free' && conversationDepth > 0 && (
        <div className="bg-gradient-to-br from-yellow-100 to-orange-100 border-2 border-yellow-500 p-4 mx-4 mt-4 rounded-lg shadow-md">
          <div className="mb-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-yellow-900 font-semibold">
                Free Tier: {conversationDepth} / 4 conversations used
              </p>
              <span className="text-xs bg-yellow-300 text-yellow-900 px-2 py-1 rounded-full font-bold">
                {Math.round((conversationDepth / 4) * 100)}%
              </span>
            </div>
            {/* Visual Progress Bar */}
            <div className="w-full bg-yellow-300 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-yellow-600 to-orange-600 h-3 rounded-full transition-all duration-500 flex items-center justify-end pr-1"
                  style={{ width: `${Math.min((conversationDepth / 4) * 100, 100)}%` }}
                >
                {conversationDepth >= 3 && (
                  <span className="text-xs text-white font-bold">🔥</span>
          )}
        </div>
      </div>
          </div>
            <div className="flex items-center justify-between">
              <div className="flex-1">
                {conversationDepth >= 4 ? (
                  <p className="text-xs text-red-800 font-bold">⚠️ Limit reached! Upgrade for unlimited access</p>
                ) : conversationDepth >= 3 ? (
                  <p className="text-xs text-orange-900 font-semibold">🔔 Almost there! {4 - conversationDepth} conversation{4 - conversationDepth > 1 ? 's' : ''} left</p>
                ) : (
                  <p className="text-xs text-yellow-900">Continue your spiritual journey with unlimited guidance</p>
                )}
              </div>
            <button
              onClick={() => setShowUpgradeModal(true)}
              className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-md transform hover:scale-105 transition-all ml-3"
            >
              {conversationDepth >= 4 ? 'Upgrade Now' : 'Join Premium'}
            </button>
          </div>
        </div>
      )}

            {/* Show unlimited status for paid users */}
            {userTier === 'unlimited' && (
                  <div className="bg-green-400 border-l-4 border-green-600 p-4 mx-4 mt-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-green-900">
                      <strong>💎 Unlimited Member:</strong> Unlimited spiritual guidance
                    </p>
                    <p className="text-xs text-green-900 mt-1">Thank you for supporting our ministry!</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleSubscriptionManagement()}
                      className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded-lg text-xs font-semibold"
                    >
                      Manage
                    </button>
                    <div className="text-2xl">💎</div>
                  </div>
                </div>
              </div>
            )}
      
      {/* Chat Interface */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8 bg-white rounded-lg shadow-sm border border-gray-500 mx-4">
            <div className="text-4xl mb-4">🙏</div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Welcome to Biblical Spiritual Guidance</h3>
            <p className="text-gray-600 mb-3">
              God has provided this tool to help you reflect on Scripture, examine your heart, and grow closer to Him.
              Let's explore what the Bible says about your journey.
            </p>
            <div className="bg-blue-400 border-l-4 border-blue-600 p-3 rounded">
              <p className="text-sm text-blue-950 italic">
                "Search me, O God, and know my heart; test me and know my anxious thoughts."
              </p>
              <p className="text-xs text-blue-950 mt-1">— Psalm 139:23</p>
            </div>
            <p className="text-sm text-gray-900 mt-4 font-semibold">
              What's on your heart today?
                      </p>
                    </div>
        )}
        
        {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl ${
                    msg.role === 'user' 
                ? 'bg-blue-600 text-white rounded-br-md' 
                : 'bg-white text-gray-900 border border-gray-500 rounded-bl-md shadow-sm'
                  }`}>
              <div className="text-sm leading-relaxed">{msg.content}</div>
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex justify-start">
            <div className="bg-white text-gray-900 border border-gray-500 rounded-2xl rounded-bl-md shadow-sm px-4 py-3">
              <div className="flex items-center space-x-2 text-sm">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-700 border-t-transparent"></div>
                <span>Processing your confession...</span>
                    </div>
                  </div>
                </div>
          )}
        </div>
        
      {/* Finalise CTA */}
      {messages.length >= 3 && !isLoading && (
        <div className="mx-4 mb-4 bg-yellow-300 border-l-4 border-yellow-500 p-4 rounded-lg flex items-center justify-between space-x-4">
          <p className="text-sm text-gray-900 font-medium flex-1">
            Ready to bring this to prayer?
                </p>
                <button
            onClick={handleSummarizeClick}
            className="bg-yellow-400 hover:bg-yellow-3000 text-black font-bold px-4 py-2 rounded-lg shadow-md border-2 border-yellow-300"
          >
            Summarize & Review
                </button>
            </div>
          )}
          
      {/* Chat Input - Fixed at Bottom */}
      <div className="bg-white border-t border-gray-500 p-4">
        <div className="flex space-x-3">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Share your confession..."
            className="flex-1 px-4 py-3 border-2 border-gray-500 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-900 font-medium"
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
            disabled={isLoading || !inputMessage.trim()}
            className="bg-blue-800 hover:bg-blue-700 text-white px-6 py-3 rounded-full font-bold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg border-2 border-blue-800"
              >
            <span className="text-lg font-bold">Send</span>
              </button>
            </div>
        </div>
      



        </div>
      );

  const renderReview = () => (
    <div className="flex flex-col h-full bg-gray-300 pb-20">
      <div className="bg-blue-700 text-white p-6 text-center">
        <h1 className="text-2xl font-bold">An Act of Contrition</h1>
        <p className="text-sm opacity-90 mt-1">You have prepared your prayer. Offer it to God privately, or share it anonymously to help and inspire others.</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-xl font-bold text-center text-gray-900 mb-4">{generatedSummary.title}</h2>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{generatedSummary.prayer}</p>
                  </div>
              </div>

      <div className="p-4 space-y-3 bg-white border-t">
              <button
          onClick={() => handleSaveConfession(true)}
          disabled={isLoading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-all shadow-md disabled:opacity-50"
              >
          Share Anonymously to Help Others
              </button>
            <button
          onClick={() => handleSaveConfession(false)}
          disabled={isLoading}
          className="w-full bg-gray-700 hover:bg-gray-800 text-white font-bold py-3 px-4 rounded-lg transition-all disabled:opacity-50"
            >
          Confess to God Alone
            </button>
                <button
          onClick={() => setCurrentView('confess')}
          disabled={isLoading}
          className="w-full text-center text-sm text-gray-600 py-2"
        >
          Continue Chatting
                </button>
              </div>
                      </div>
  );

  const renderConfession = () => (
    <div className="flex flex-col h-full">
      <div className="bg-blue-700 text-white p-4 text-center">
        <h1 className="text-2xl font-bold">Peace Be With You</h1>
        <p className="text-sm opacity-90">You have completed your confession. Go in peace.</p>
                    </div>
      <div className="flex-1 p-6 overflow-y-auto pb-24">
        <div className="bg-white border border-gray-500 rounded-lg p-6 shadow-sm">
          <div className="text-center mb-4">
            <div className="text-4xl mb-2">✅</div>
            <h2 className="text-xl font-semibold text-gray-900">Your Prayer Has Been Offered</h2>
                  </div>

          <div className="bg-gray-300 rounded-lg p-4 mb-6">
            <p className="text-gray-700 leading-relaxed">{currentConfession?.text}</p>
                  </div>

          <div className="text-center text-sm text-gray-600 mb-6">
            {currentConfession?.is_public ? (
              <p>Your prayer has been shared anonymously to help and inspire others.</p>
            ) : (
              <p>Your prayer has been offered to God alone and was not shared publicly.</p>
                      )}
                    </div>
                    
          <div className="flex flex-col space-y-3">
                <button
              onClick={() => setCurrentView('confess')}
              className="w-full px-4 py-3 bg-blue-700 text-white rounded-lg hover:bg-blue-600 font-semibold"
                >
              Start New Confession
                </button>
              <button
              onClick={() => setCurrentView('discover')}
              className="w-full px-4 py-3 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-300 font-semibold"
              >
              See Other Prayers
              </button>
          <button
              onClick={() => setCurrentView('subscription')}
              className="w-full px-4 py-3 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-300 font-semibold"
          >
              💎 Upgrade to Unlimited
          </button>
                </div>
                </div>
              </div>
            </div>
  );

  const renderDiscover = () => {
    // Check if user has premium access
    const isPremium = userTier === 'unlimited';

    return (
    <div className="flex flex-col h-full pb-20">
      {/* Header */}
      <div className="bg-blue-700 text-white p-4 text-center">
        <h1 className="text-2xl font-bold">✝️ Shared Prayers</h1>
          <p className="text-sm opacity-90">Read prayers shared anonymously by people around the world</p>
            </div>

        {!isPremium ? (
          /* Premium Upsell for Free Users */
          <div className="flex-1 overflow-y-auto p-4 bg-gray-300">
            <div className="max-w-md mx-auto mt-8">
              {/* Lock Icon */}
              <div className="text-center mb-6">
                <div className="inline-block bg-blue-300 p-6 rounded-full mb-4">
                  <span className="text-5xl">🔒</span>
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-3">Premium Feature</h2>
                <p className="text-gray-600 leading-relaxed">
                  Join Premium to view and read <strong>all shared prayers</strong> from other people. 
                  Get inspiration, see that you're not alone, and grow with the community.
                </p>
              </div>

              {/* Preview Benefits */}
              <div className="bg-white rounded-lg shadow-lg p-6 mb-6 border-2 border-blue-500">
                <h3 className="font-bold text-lg text-gray-900 mb-4 text-center">As a Premium member you get:</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex items-start">
                    <span className="text-green-900 mr-3 text-lg">✓</span>
                    <span className="text-gray-700"><strong>View all shared prayers</strong> - Get inspiration from others' stories</span>
                  </div>
                  <div className="flex items-start">
                    <span className="text-green-900 mr-3 text-lg">✓</span>
                    <span className="text-gray-700"><strong>Unlimited conversations</strong> - Deeper conversations with AI</span>
                  </div>
                  <div className="flex items-start">
                    <span className="text-green-900 mr-3 text-lg">✓</span>
                    <span className="text-gray-700"><strong>Conversation history</strong> - Everything saved for future reference</span>
                  </div>
                  <div className="flex items-start">
                    <span className="text-green-900 mr-3 text-lg">✓</span>
                    <span className="text-gray-700"><strong>Support the mission</strong> - Help spread Christian support</span>
                  </div>
                </div>
                
                <div className="mt-6 text-center">
                  <div className="text-3xl font-bold text-blue-950 mb-2">$9.99<span className="text-base text-gray-600">/mo</span></div>
                  <button
                    onClick={() => setCurrentView('subscription')}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-lg font-bold text-lg transition-all duration-200 shadow-lg"
                  >
                    💎 Join Premium
                  </button>
                </div>
              </div>

              {/* Social Proof */}
              <div className="bg-blue-300 rounded-lg p-4 border border-blue-500 text-center">
                <p className="text-sm text-gray-600">
                  <strong className="text-blue-950">10,000+ people</strong> have already found support and inspiration in our community
                </p>
              </div>
            </div>
          </div>
        ) : (
          /* Premium Content - Show Confessions */
          <>
      {/* Filter Buttons */}
      <div className="flex justify-center p-3 bg-gray-300 border-b">
        <div className="flex space-x-2 bg-gray-300 p-1 rounded-lg">
               <button
            onClick={() => setConfessionFilter('latest')}
            className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-colors ${confessionFilter === 'latest' ? 'bg-white text-blue-950 shadow-sm' : 'text-gray-600'}`}
               >
            Latest
               </button>
                      <button
            onClick={() => setConfessionFilter('popular')}
            className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-colors ${confessionFilter === 'popular' ? 'bg-white text-blue-950 shadow-sm' : 'text-gray-600'}`}
                      >
            Most Popular
                      </button>
                        </div>
                            </div>

      {/* Confessions List */}
      <div className="flex-1 overflow-y-auto p-4">
        {confessions.length === 0 ? (
          <div className="text-center text-gray-600 py-8">
            <p className="text-lg mb-2">No public prayers yet</p>
            <p className="text-sm">Be the first to share a prayer to help others.</p>
                </div>
        ) : (
          <div className="space-y-4">
            {confessions.map((confession) => (
              <div key={confession.id} className="bg-white border border-gray-500 rounded-lg p-4 shadow-sm transition-all hover:shadow-md">
                <h3 className="font-bold text-gray-900 text-md mb-2">{confession.title || "A Prayer"}</h3>
                <p className="text-gray-700 leading-relaxed mb-4">{confession.text}</p>
                <div className="flex justify-between items-center text-xs text-gray-600">
                          <button 
                    onClick={() => handleSharePrayer(confession)}
                    className="font-semibold text-blue-950 hover:underline"
                          >
                    {copiedPrayerId === confession.id ? 'Copied!' : 'Share'}
                          </button>
                  <div className="flex items-center space-x-2">
                    <span>{new Date(confession.created_at).toLocaleDateString()}</span>
                          <button
                      onClick={() => handleUpvoteClick(confession.id)}
                      disabled={upvotedConfessions.has(confession.id)}
                      className="flex items-center space-x-1 p-1 rounded-md transition-colors disabled:opacity-70 disabled:cursor-not-allowed group hover:bg-red-300"
                          >
                      <span className={`transition-transform ${upvotedConfessions.has(confession.id) ? 'text-red-500' : 'text-gray-500 group-hover:text-red-400'}`}>❤️</span>
                      <span className="font-semibold">{confession.upvotes || 0}</span>
                          </button>
                </div>
              </div>
          </div>
            ))}
        </div>
              )}
            </div>
          </>
        )}
            
      {/* Navigation */}
      <div className="border-t bg-white p-4">
                    <button 
          onClick={() => setCurrentView('confess')}
          className="w-full px-4 py-2 bg-blue-700 text-white rounded-lg hover:bg-blue-600 font-semibold"
                    >
            ✝️ Start Your Confession
                    </button>
            </div>
          </div>
        );
  };

  const renderSubscriptionPage = () => {
    return (
      <div className="flex flex-col h-full bg-gray-300 pb-20">
        {/* Header */}
        <div className="relative bg-gradient-to-r from-blue-700 to-blue-800 text-white p-6 text-center overflow-hidden">
          <div className="relative z-10">
            <div className="text-4xl mb-3">💎</div>
            <h1 className="text-3xl font-bold tracking-tight text-white">Premium Membership</h1>
            <p className="text-base mt-2 opacity-90">Continue your spiritual journey with unlimited access to Christian guidance</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Current Status */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 text-center">Your Spiritual Journey</h2>
            <div className={`rounded-lg p-4 border-2 ${userTier === 'unlimited' ? 'bg-green-400 border-green-600' : 'bg-blue-400 border-blue-600'}`}>
              <div className="text-center">
                <p className={`font-bold text-lg ${userTier === 'unlimited' ? 'text-green-900' : 'text-blue-950'}`}>
                  Current Status: {userTier === 'unlimited' ? '💎 Premium Member' : '🆓 Free User'}
                </p>
                <p className={`text-sm mt-2 ${userTier === 'unlimited' ? 'text-green-900' : 'text-blue-950'}`}>
                {userTier === 'unlimited' 
                    ? 'Thank you for supporting our mission! You have unlimited access to spiritual guidance and community.'
                  : `You've had ${conversationDepth} meaningful conversations. Continue with unlimited spiritual guidance.`
                }
              </p>
              </div>
            </div>
          </div>

          {/* Social Proof Stats */}
          <div className="bg-gradient-to-br from-blue-700 to-blue-800 rounded-xl shadow-lg p-6 text-white">
            <h3 className="text-lg font-bold text-center mb-4">Our Growing Community</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-3xl font-bold text-yellow-300">10,000+</div>
                <div className="text-xs opacity-90 mt-1">People Helped</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-yellow-300">5,000+</div>
                <div className="text-xs opacity-90 mt-1">Shared Prayers</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-yellow-300">24/7</div>
                <div className="text-xs opacity-90 mt-1">Always Available</div>
              </div>
            </div>
          </div>

          {/* Subscription Option */}
          {userTier === 'free' ? (
            <div className="bg-white rounded-xl shadow-lg p-6">
              {/* Urgency Banner */}
              <div className="bg-gradient-to-r from-red-500 to-orange-500 text-white p-3 rounded-lg mb-4 text-center">
                <p className="text-sm font-bold">⚡ SPECIAL OFFER: Save up to 33% + 30-Day Money-Back Guarantee!</p>
              </div>
              
              <h3 className="text-xl font-bold text-gray-900 text-center mb-4">Join Premium Today</h3>
              
              {/* Plan Selection Toggle */}
              <div className="flex justify-center mb-6">
                <div className="bg-gray-300 p-1 rounded-lg inline-flex">
                  <button
                    onClick={() => setSelectedPlan('monthly')}
                    className={`px-6 py-2 rounded-md text-sm font-semibold transition-all ${
                      selectedPlan === 'monthly' 
                        ? 'bg-white text-blue-950 shadow-md' 
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Monthly
                  </button>
                  <button
                    onClick={() => setSelectedPlan('annual')}
                    className={`px-6 py-2 rounded-md text-sm font-semibold transition-all relative ${
                      selectedPlan === 'annual' 
                        ? 'bg-white text-blue-950 shadow-md' 
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Annual
                    <span className="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                      Save 17%
                    </span>
                  </button>
                </div>
              </div>
              
              <div className="border-2 border-blue-600 rounded-lg p-6 bg-gradient-to-br from-blue-100 to-white relative">
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-yellow-500 text-blue-950 px-4 py-1 text-xs font-bold rounded-full shadow-lg">
                    ⭐ MOST POPULAR
                  </span>
                </div>
                <div className="text-center pt-4">
                  <h3 className="font-bold text-2xl text-gray-900 mb-2">💎 Premium Membership</h3>
                  
                  {selectedPlan === 'monthly' ? (
                    <div>
                      <div className="text-sm text-gray-600 mb-1">
                        <span className="line-through">$14.99</span>
                        <span className="ml-2 text-green-900 font-semibold">33% OFF</span>
                      </div>
                      <div className="text-4xl font-bold text-blue-950 mb-2">
                        $9.99<span className="text-lg text-gray-600">/mo</span>
                      </div>
                      <p className="text-xs text-green-900 font-semibold">Start today - Cancel anytime</p>
                    </div>
                  ) : (
                    <div>
                      <div className="text-sm text-gray-600 mb-1">
                        <span className="line-through">$119.88</span>
                        <span className="ml-2 text-green-900 font-semibold">SAVE $20.88</span>
                      </div>
                      <div className="text-4xl font-bold text-blue-950 mb-2">
                        $99<span className="text-lg text-gray-600">/year</span>
                      </div>
                      <p className="text-xs text-green-900 font-semibold">Just $8.25/month - Best Value!</p>
                    </div>
                  )}
                  
                  {/* Benefits List */}
                  <div className="text-left space-y-3 mb-6">
                    <div className="flex items-start">
                      <span className="text-green-900 mr-3 text-xl font-bold">✓</span>
                      <div>
                        <p className="font-semibold text-gray-900">Unlimited Biblical guidance 24/7</p>
                        <p className="text-xs text-gray-600">Scripture-based wisdom whenever you need it</p>
                      </div>
                    </div>
                    <div className="flex items-start">
                      <span className="text-green-900 mr-3 text-xl font-bold">✓</span>
                      <div>
                        <p className="font-semibold text-gray-900">Access all community prayers</p>
                        <p className="text-xs text-gray-600">Find strength in shared faith journeys</p>
                      </div>
                    </div>
                    <div className="flex items-start">
                      <span className="text-green-900 mr-3 text-xl font-bold">✓</span>
                      <div>
                        <p className="font-semibold text-gray-900">Your spiritual journey preserved</p>
                        <p className="text-xs text-gray-600">Track your growth in faith over time</p>
                      </div>
                    </div>
                    <div className="flex items-start">
                      <span className="text-green-900 mr-3 text-xl font-bold">✓</span>
                      <div>
                        <p className="font-semibold text-gray-900">Priority spiritual support</p>
                        <p className="text-xs text-gray-600">We're here when you need us most</p>
                      </div>
                    </div>
                    <div className="flex items-start">
                      <span className="text-green-900 mr-3 text-xl font-bold">✓</span>
                      <div>
                        <p className="font-semibold text-gray-900">Empower faith through technology</p>
                        <p className="text-xs text-gray-600">Help us serve thousands seeking God's truth</p>
                      </div>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => handleUpgrade()}
                    className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white py-4 rounded-lg font-bold text-lg transition-all duration-200 shadow-lg transform hover:scale-105"
                  >
                    {selectedPlan === 'monthly' 
                      ? 'Join Premium - $9.99/mo' 
                      : 'Get Best Value - $99/year'
                    }
                  </button>
                  
                  <div className="mt-4 space-y-2 text-center">
                    <p className="text-xs text-gray-600 font-semibold">
                      ✓ Instant Access • ✓ Cancel Anytime
                    </p>
                    <p className="text-xs text-gray-600 font-semibold">
                      ✓ 30-Day Money-Back Guarantee
                    </p>
                    <p className="text-xs text-gray-600">
                      🔒 Secure Stripe payment • No risk
                    </p>
                </div>
                </div>
              </div>
              
              {/* Social Proof - Faith-Focused Testimonials */}
              <div className="mt-6 bg-gradient-to-br from-blue-100 to-white rounded-lg p-4 border border-blue-200">
                <h4 className="font-bold text-sm text-blue-950 mb-3 text-center">✝️ What Believers Say:</h4>
                <div className="space-y-3">
                  <div className="bg-white p-3 rounded-lg shadow-sm border border-gray-200">
                    <div className="flex items-center mb-2">
                      <div className="text-yellow-400 text-sm">★★★★★</div>
                      <span className="ml-2 text-xs text-gray-600">Sarah M., Texas</span>
                    </div>
                    <p className="text-xs text-gray-700 italic">"This tool helped me examine my heart before God. The Scripture guidance brought me closer to understanding His grace and forgiveness."</p>
                  </div>
                  <div className="bg-white p-3 rounded-lg shadow-sm border border-gray-200">
                    <div className="flex items-center mb-2">
                      <div className="text-yellow-400 text-sm">★★★★★</div>
                      <span className="ml-2 text-xs text-gray-600">John D., California</span>
                    </div>
                    <p className="text-xs text-gray-700 italic">"Reading others' prayers showed me I'm not alone in my struggles. God is using technology to build His community. Powerful!"</p>
                  </div>
                  <div className="bg-white p-3 rounded-lg shadow-sm border border-gray-200">
                    <div className="flex items-center mb-2">
                      <div className="text-yellow-400 text-sm">★★★★★</div>
                      <span className="ml-2 text-xs text-gray-600">Maria K., Florida</span>
                    </div>
                    <p className="text-xs text-gray-700 italic">"Having 24/7 access to Biblical wisdom has transformed my prayer life. I can seek God's guidance anytime, anywhere."</p>
                  </div>
                </div>
              </div>
              
              {/* Community Growth - Positive Framing */}
              <div className="mt-4 bg-blue-400 border-l-4 border-blue-600 p-3 rounded-lg">
                <p className="text-xs text-blue-950">
                  <strong>🙏 Join 10,000+ believers</strong> growing in faith through Biblical guidance
                </p>
              </div>
            </div>
          ) : (
            /* Premium Member Benefits */
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-bold text-gray-900 text-center mb-4">Your Premium Benefits</h3>
              
              <div className="space-y-3 text-sm">
                <div className="flex items-center p-3 bg-green-400 rounded-lg border border-green-600">
                  <span className="text-green-900 mr-3 text-xl">✓</span>
                  <span className="font-medium text-gray-700">Unlimited Biblical guidance</span>
                </div>
                <div className="flex items-center p-3 bg-green-400 rounded-lg border border-green-600">
                  <span className="text-green-900 mr-3 text-xl">✓</span>
                  <span className="font-medium text-gray-700">All shared prayers visible</span>
                </div>
                <div className="flex items-center p-3 bg-green-400 rounded-lg border border-green-600">
                  <span className="text-green-900 mr-3 text-xl">✓</span>
                  <span className="font-medium text-gray-700">Conversation history saved</span>
                </div>
                <div className="flex items-center p-3 bg-green-400 rounded-lg border border-green-600">
                  <span className="text-green-900 mr-3 text-xl">✓</span>
                  <span className="font-medium text-gray-700">Priority support</span>
                </div>
              </div>
              
              <div className="mt-6 text-center">
                <button
                  onClick={() => handleSubscriptionManagement()}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg font-bold transition-all duration-200"
                >
                  Manage Membership
                </button>
              </div>
            </div>
          )}

          {/* Ministry Info */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 text-center">Our Christian Ministry</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-4xl mb-2">✝️</div>
                <h3 className="font-semibold text-gray-700 mb-1">Spiritual Guidance</h3>
                <p className="text-xs text-gray-600">Based on Christian tradition and Scripture</p>
              </div>
              <div className="text-center">
                <div className="text-4xl mb-2">🌍</div>
                <h3 className="font-semibold text-gray-700 mb-1">24/7 Service</h3>
                <p className="text-xs text-gray-600">Always available for spiritual support</p>
              </div>
              <div className="text-center">
                <div className="text-4xl mb-2">🔒</div>
                <h3 className="font-semibold text-gray-700 mb-1">Sacred Privacy</h3>
                <p className="text-xs text-gray-600">Complete anonymity and security</p>
              </div>
            </div>
          </div>

          {/* FAQ/Trust Elements */}
          <div className="bg-blue-300 rounded-xl p-6 border border-blue-500">
            <h3 className="font-bold text-gray-900 mb-3 text-center">Why Premium?</h3>
            <div className="space-y-3 text-sm text-gray-700">
              <div>
                <p className="font-semibold mb-1">💰 Transparent Pricing</p>
                <p className="text-xs text-gray-600">$9.99/mo, cancel anytime. No hidden fees.</p>
              </div>
              <div>
                <p className="font-semibold mb-1">🙏 Support the Mission</p>
                <p className="text-xs text-gray-600">Your membership helps us continue providing spiritual support to thousands of people.</p>
              </div>
              <div>
                <p className="font-semibold mb-1">🔐 Secure Payment</p>
                <p className="text-xs text-gray-600">We use Stripe's secure payment system. Your data is protected.</p>
              </div>
            </div>
          </div>

          {/* Back Button */}
          <div className="space-y-3 px-4">
            <button
              onClick={() => setCurrentView('confess')}
              className="w-full text-gray-600 py-3 rounded-lg font-semibold hover:bg-gray-300 transition-colors border border-gray-500"
            >
              Back to Spiritual Guidance
            </button>
          </div>

          <div className="text-center text-xs text-gray-600 pt-4 px-4">
            Questions or support? Email us: <a href="mailto:support@myconfessions.org" className="underline text-blue-950">support@myconfessions.org</a>
          </div>
        </div>
      </div>
    );
  }

  // Value-first upgrade modal component
  const UpgradeModal = () => (
    showUpgradeModal && (
      <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl max-w-md w-full p-6 max-h-[90vh] overflow-y-auto relative">
          {/* Close button */}
          <button
            onClick={() => setShowUpgradeModal(false)}
            className="absolute top-4 right-4 text-gray-500 hover:text-gray-600 text-2xl font-bold"
          >
            ×
          </button>
          
          {/* Urgency Badge */}
          <div className="bg-gradient-to-r from-red-600 to-orange-600 text-white p-2 rounded-lg mb-4 text-center">
            <p className="text-xs font-bold">⚡ SPECIAL OFFER: Save up to 33% + Risk-Free Guarantee!</p>
          </div>
          
          <div className="text-center mb-4">
            <div className="text-5xl mb-3">💎</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Continue Your Spiritual Journey
            </h2>
            <p className="text-gray-600 mb-3 leading-relaxed text-sm">
              I sense you're seeking deeper guidance. Many souls like you find that unlimited spiritual support helps them grow closer to God.
            </p>
            <div className="bg-blue-300 rounded-lg p-3 border border-blue-500 mb-4">
              <p className="text-sm text-blue-950">
                You've had <strong>{conversationDepth} meaningful conversations</strong>
              </p>
              {/* Mini Progress Bar */}
              <div className="w-full bg-blue-300 rounded-full h-2 mt-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${Math.min((conversationDepth / 4) * 100, 100)}%` }}
                ></div>
              </div>
            </div>
          </div>
          
          {/* Plan Selection in Modal */}
          <div className="flex justify-center mb-4">
            <div className="bg-gray-300 p-1 rounded-lg inline-flex text-sm">
              <button
                onClick={() => setSelectedPlan('monthly')}
                className={`px-4 py-1.5 rounded-md font-semibold transition-all ${
                  selectedPlan === 'monthly' 
                    ? 'bg-white text-blue-950 shadow-md' 
                    : 'text-gray-600'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setSelectedPlan('annual')}
                className={`px-4 py-1.5 rounded-md font-semibold transition-all relative ${
                  selectedPlan === 'annual' 
                    ? 'bg-white text-blue-950 shadow-md' 
                    : 'text-gray-600'
                }`}
              >
                Annual
                <span className="absolute -top-1 -right-1 bg-green-500 text-white text-xs px-1 py-0.5 rounded-full">
                  -17%
                </span>
              </button>
            </div>
          </div>
          
          <div className="space-y-4">
            {/* Pricing Card */}
            <div className="border-2 border-blue-600 rounded-lg p-4 bg-gradient-to-br from-blue-100 to-white relative">
              <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
                <span className="bg-yellow-500 text-blue-950 px-3 py-1 text-xs font-bold rounded-full shadow-lg">⭐ MOST POPULAR</span>
              </div>
              <div className="text-center pt-3">
                <h3 className="font-bold text-lg text-gray-900 mb-1">💎 Premium Membership</h3>
                
                {selectedPlan === 'monthly' ? (
                  <div className="mb-3">
                    <div className="text-xs text-gray-600">
                      <span className="line-through">$14.99</span>
                      <span className="ml-2 text-green-900 font-semibold">33% OFF</span>
                    </div>
                    <div className="text-3xl font-bold text-blue-950">
                      $9.99<span className="text-base text-gray-600">/mo</span>
                    </div>
                    <p className="text-xs text-green-900 font-semibold">Instant access - Cancel anytime</p>
                  </div>
                ) : (
                  <div className="mb-3">
                    <div className="text-xs text-gray-600">
                      <span className="line-through">$119.88</span>
                      <span className="ml-2 text-green-900 font-semibold">SAVE $20.88</span>
                    </div>
                    <div className="text-3xl font-bold text-blue-950">
                      $99<span className="text-base text-gray-600">/year</span>
                    </div>
                    <p className="text-xs text-green-900 font-semibold">Just $8.25/mo - Best Value!</p>
                  </div>
                )}
                
                {/* Benefits - Compact */}
                <div className="text-left space-y-1.5 mb-4">
                  <div className="flex items-center text-xs">
                    <span className="text-green-900 mr-2">✓</span>
                    <span className="font-medium text-gray-700">Unlimited Biblical guidance</span>
                  </div>
                  <div className="flex items-center text-xs">
                    <span className="text-green-900 mr-2">✓</span>
                    <span className="font-medium text-gray-700">View all shared prayers</span>
                  </div>
                  <div className="flex items-center text-xs">
                    <span className="text-green-900 mr-2">✓</span>
                    <span className="font-medium text-gray-700">Conversation history</span>
                  </div>
                  <div className="flex items-center text-xs">
                    <span className="text-green-900 mr-2">✓</span>
                    <span className="font-medium text-gray-700">Priority support</span>
                  </div>
                </div>
                
                <button
                  onClick={() => handleUpgrade()}
                  className="w-full bg-gradient-to-r from-blue-700 to-blue-800 hover:from-blue-800 hover:to-blue-900 text-white py-3 rounded-lg font-bold text-base transition-all duration-200 shadow-lg transform hover:scale-105"
                >
                  {selectedPlan === 'monthly' 
                    ? 'Join Now - $9.99/mo' 
                    : 'Get Best Value - $99/yr'
                  }
                </button>
                
                <div className="mt-3 space-y-1 text-center">
                  <p className="text-xs text-gray-600 font-semibold">
                    ✓ Instant access • ✓ 30-day money-back
                  </p>
                  <p className="text-xs text-gray-600">
                    🔒 Secure payment • Cancel anytime
                  </p>
                </div>
              </div>
            </div>
            
            {/* Mini Testimonial */}
            <div className="bg-gray-300 p-3 rounded-lg border border-gray-500">
              <div className="flex items-center mb-1">
                <div className="text-yellow-400 text-xs">★★★★★</div>
                <span className="ml-2 text-xs text-gray-600">Sarah M.</span>
              </div>
              <p className="text-xs text-gray-700 italic">"This has been life-changing. Worth every penny!"</p>
            </div>
            
            {/* Scarcity */}
            <div className="bg-red-300 border-l-4 border-red-500 p-2 rounded">
              <p className="text-xs text-red-800">
                <strong>🔥 346 people</strong> joined in last 24h
              </p>
            </div>
            
            <button
              onClick={() => setShowUpgradeModal(false)}
              className="w-full text-gray-600 py-2 text-sm hover:text-gray-700 transition-colors"
            >
              Maybe Later
            </button>
          </div>
        </div>
      </div>
    )
  );

  // Login modal component
  const LoginModal = () => (
    showLoginModal && (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl max-w-md w-full p-6">
          <div className="text-center mb-6">
            <div className="text-4xl mb-4">🔐</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome Back</h2>
            <p className="text-gray-700">Sign in to manage your spiritual journey</p>
          </div>
          
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            handleLogin(formData.get('email'), formData.get('password'));
          }} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                name="email"
                required
                className="w-full px-3 py-2 border border-gray-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="your@email.com"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                name="password"
                required
                className="w-full px-3 py-2 border border-gray-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Your password"
              />
            </div>
            
            <button
              type="submit"
              className="w-full bg-blue-700 hover:bg-blue-600 text-white py-3 rounded-lg font-bold"
            >
              Sign In
            </button>
          </form>
          
          <div className="mt-4 text-center">
            <button
              onClick={() => {
                setShowLoginModal(false);
                setShowRegisterModal(true);
              }}
              className="text-blue-950 hover:text-blue-950 text-sm font-medium"
            >
              Don't have an account? Sign up
            </button>
          </div>
          
          <button
            onClick={() => setShowLoginModal(false)}
            className="w-full text-gray-600 py-2 rounded-lg font-semibold hover:bg-gray-300 transition-colors mt-4"
          >
            Cancel
          </button>
        </div>
      </div>
    )
  );

  // Register modal component
  const RegisterModal = () => (
    showRegisterModal && (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl max-w-md w-full p-6">
          <div className="text-center mb-6">
            <div className="text-4xl mb-4">✨</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Create Account</h2>
            <p className="text-gray-700">Join our spiritual community</p>
          </div>
          
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            handleRegister(formData.get('email'), formData.get('password'), formData.get('name'));
          }} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                name="name"
                required
                className="w-full px-3 py-2 border border-gray-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Your name"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                name="email"
                required
                className="w-full px-3 py-2 border border-gray-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="your@email.com"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                name="password"
                required
                className="w-full px-3 py-2 border border-gray-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Create a password"
              />
            </div>
            
            <button
              type="submit"
              className="w-full bg-blue-700 hover:bg-blue-600 text-white py-3 rounded-lg font-bold"
            >
              Create Account
            </button>
          </form>
          
          <div className="mt-4 text-center">
            <button
              onClick={() => {
                setShowRegisterModal(false);
                setShowLoginModal(true);
              }}
              className="text-blue-950 hover:text-blue-950 text-sm font-medium"
            >
              Already have an account? Sign in
            </button>
          </div>
          
          <button
            onClick={() => setShowRegisterModal(false)}
            className="w-full text-gray-600 py-2 rounded-lg font-semibold hover:bg-gray-300 transition-colors mt-4"
          >
            Cancel
          </button>
        </div>
      </div>
    )
  );

  const handleUpgrade = async () => {
    try {
      const currentSessionId = isLoggedIn ? userSessionId : sessionId;
      const response = await fetch('/api/stripe/create-checkout-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessionId
        })
      });
      
    const data = await response.json();
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
    } else if (data.setup_required) {
      alert('Stripe setup required: ' + data.error + '\n\nFor now, you can test the upgrade using the test endpoint.');
    } else {
      alert('Unable to process upgrade. Please try again.');
    }
    } catch (error) {
      console.error('Upgrade error:', error);
      alert('Unable to process upgrade. Please try again.');
    }
  };

  const handleSubscriptionManagement = async () => {
    try {
      const currentSessionId = isLoggedIn ? userSessionId : sessionId;
      const response = await fetch(`/api/user/subscription-management?session_id=${currentSessionId}`);
      const data = await response.json();
      
      if (data.success && data.management_url) {
        window.location.href = data.management_url;
      } else {
        alert('Unable to open subscription management. Please contact support at support@myconfessions.org');
      }
    } catch (error) {
      console.error('Subscription management error:', error);
      alert('Unable to open subscription management. Please contact support at support@myconfessions.org');
    }
  };

  const handleRegister = async (email, password, name) => {
    try {
      const response = await fetch('/api/user/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          password: password,
          name: name
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setUserEmail(email);
        setUserName(name);
        setIsLoggedIn(true);
        setUserSessionId(data.session_id);
        setUserTier(data.tier || 'free');
        setShowRegisterModal(false);
        
        // Load user's subscription status
        await loadUserSubscriptionStatus(data.session_id);
        
        alert('Account created successfully! You can now manage your subscription.');
      } else {
        alert('Registration failed: ' + data.error);
      }
    } catch (error) {
      console.error('Registration error:', error);
      alert('Registration failed. Please try again.');
    }
  };

  const handleLogin = async (email, password) => {
    try {
      const response = await fetch('/api/user/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          password: password
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setUserEmail(email);
        setUserName(data.name || '');
        setIsLoggedIn(true);
        setUserSessionId(data.session_id);
        setUserTier(data.tier || 'free');
        setShowLoginModal(false);
        
        // Load user's subscription status
        await loadUserSubscriptionStatus(data.session_id);
        
        alert('Login successful! Welcome back.');
      } else {
        alert('Login failed: ' + data.error);
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Login failed. Please try again.');
    }
  };

  const loadUserSubscriptionStatus = async (sessionId) => {
    try {
      const response = await fetch(`/api/user/tier?session_id=${sessionId}`);
      const data = await response.json();
      
      if (data.tier) {
        setUserTier(data.tier);
        setConversationDepth(data.conversation_depth || 0);
      }
    } catch (error) {
      console.error('Error loading subscription status:', error);
    }
  };

  const renderNavigation = () => (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-500 md:hidden shadow-lg z-40">
      <div className="flex">
          <button
          onClick={() => setCurrentView('confess')}
          className={`flex-1 py-3 text-center transition-colors ${
            currentView === 'confess' || currentView === 'review' || currentView === 'confession' ? 'text-blue-950 border-t-2 border-blue-700' : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <div className="text-lg mb-1">✝️</div>
          <div className="text-xs font-medium">Confess</div>
          </button>
              <button
          onClick={() => setCurrentView('discover')}
          className={`flex-1 py-3 text-center transition-colors relative ${
            currentView === 'discover' ? 'text-blue-950 border-t-2 border-blue-700' : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          {userTier !== 'unlimited' && (
            <div className="absolute top-0 right-1/4 bg-yellow-400 text-xs px-1 rounded-full">🔒</div>
          )}
          <div className="text-lg mb-1">🔍</div>
          <div className="text-xs font-medium">Prayers</div>
              </button>
                <button
            onClick={() => setCurrentView('subscription')}
          className={`flex-1 py-3 text-center transition-colors ${
            currentView === 'subscription' ? 'text-blue-950 border-t-2 border-blue-700' : 'text-gray-600 hover:text-blue-950'
          }`}
        >
          <div className="text-lg mb-1">💎</div>
          <div className="text-xs font-medium">Premium</div>
                </button>
        </div>
      </div>
    );

    return (
    <div className="h-screen bg-gray-300 flex flex-col">
      {/* Desktop Navigation */}
      <div className="hidden md:block bg-white border-b border-gray-500">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-8">
              <h1 className="text-xl font-bold text-gray-900">✝️ My Confessions</h1>
              <button
                onClick={() => setCurrentView('confess')}
                className={`px-3 py-2 rounded-lg ${
                  currentView === 'confess' || currentView === 'review' || currentView === 'confession' ? 'bg-blue-300 text-blue-950' : 'text-gray-700 hover:text-gray-900'
                }`}
              >
                Confess
              </button>
                <button
                onClick={() => setCurrentView('discover')}
                className={`px-3 py-2 rounded-lg relative ${
                  currentView === 'discover' ? 'bg-blue-300 text-blue-950' : 'text-gray-700 hover:text-gray-900'
                }`}
              >
                {userTier !== 'unlimited' && (
                  <span className="absolute -top-1 -right-1 bg-yellow-400 text-xs px-1.5 py-0.5 rounded-full">🔒</span>
                )}
                Shared Prayers
                </button>
                <button
                onClick={() => setCurrentView('subscription')}
                className={`px-3 py-2 rounded-lg ${
                  currentView === 'subscription' ? 'bg-blue-300 text-blue-950' : 'text-gray-700 hover:text-blue-950'
                }`}
              >
                💎 Premium
                </button>
              </div>
            {userTier !== 'unlimited' && (
            <button
              onClick={() => setCurrentView('subscription')}
                className="bg-blue-700 hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold transition-all duration-200 shadow-md"
            >
                💎 Join Premium
            </button>
            )}
          </div>
        </div>
    </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {currentView === 'confess' && renderConfess()}
        {currentView === 'review' && renderReview()}
        {currentView === 'confession' && renderConfession()}
        {currentView === 'discover' && renderDiscover()}
        {currentView === 'subscription' && renderSubscriptionPage()}
      </div>

      {/* Mobile Navigation */}
      {renderNavigation()}
      
      {/* Value-first upgrade modal */}
      <UpgradeModal />
      <LoginModal />
      <RegisterModal />
    </div>
  );
};

// Make MyConfessionsApp available globally for browser
window.MyConfessionsApp = MyConfessionsApp;