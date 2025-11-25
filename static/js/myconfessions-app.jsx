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
  const [copiedPrayerId, setCopiedPrayerId] = useState(null);
  const [generatedSummary, setGeneratedSummary] = useState({ title: '', prayer: '' });
  
  // Analytics helper
  const track = (eventName, params = {}) => {
    if (window.track) {
      window.track(eventName, { ...params, user_tier: userTier });
    }
  };
  
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
  
  // Toast notification state
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  
  // Subscription info state
  const [subscriptionInfo, setSubscriptionInfo] = useState(null);

  const QUICK_STARTS = [
    { icon: "😟", label: "I feel anxious", message: "I'm feeling really anxious right now and I need some peace." },
    { icon: "🙏", label: "I need prayer", message: "I'm going through a hard time and I really need prayer." },
    { icon: "💔", label: "I'm grieving", message: "I'm struggling with grief and loss." },
    { icon: "😔", label: "I feel lonely", message: "I'm feeling very lonely and isolated." }
  ];

  // Load public confessions and stats
  useEffect(() => {
    fetchConfessions(confessionFilter);
  }, [confessionFilter]);
  
  // Track page view on mount
  useEffect(() => {
    track('page_view', { page: 'app' });
  }, []);
  
  // Track view changes
  useEffect(() => {
    track('view_change', { view: currentView });
  }, [currentView]);
  
  // Check for URL params (e.g. subscription cancelled/upgraded)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    
    if (urlParams.get('cancelled') === 'true') {
      setToastMessage("No worries! You can upgrade to Premium anytime. Your free tier is still available. 💙");
      setShowToast(true);
      setTimeout(() => setShowToast(false), 5000);
      window.history.replaceState({}, '', window.location.pathname);
    }
    
    if (urlParams.get('upgraded') === 'true') {
      setToastMessage("🎉 Welcome to Premium! Your unlimited spiritual guidance is now active. Enjoy your journey!");
      setShowToast(true);
      setTimeout(() => setShowToast(false), 6000);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);


  const fetchConfessions = async (filter) => {
    try {
      const response = await fetch(`/api/confessions?sort=${filter}`);
      if (response.ok) {
        const data = await response.json();
        setConfessions(data);
      } else {
        console.error('Confessions API error:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Error fetching confessions:', error);
    }
  };

  const sendMessage = async (msgOverride = null) => {
    const messageToSend = msgOverride || inputMessage;
    if (!messageToSend.trim()) return;
    
    setInputMessage('');
    setMessages(prev => [...prev, { role: 'user', content: messageToSend }]);
    setIsLoading(true);
    
    // Track message sent
    track('message_sent', { 
      message_count: messages.length / 2 + 1,
      conversation_depth: conversationDepth + 1
    });

    try {
      const currentSessionId = isLoggedIn ? userSessionId : sessionId;
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageToSend,
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
          track('upgrade_modal_shown', { 
            trigger: 'conversation_limit',
            conversation_depth: data.conversation_depth 
          });
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
    track('prayer_shared', { prayer_id: confession.id });
    
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
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-gray-100 p-3 md:p-4 shadow-sm z-10">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity text-decoration-none">
            <span className="text-2xl text-blue-800">✝</span>
            <h1 className="text-lg font-bold text-blue-900">My Confessions</h1>
          </a>

          {/* Mobile login buttons */}
          <div className="md:hidden">
            {!isLoggedIn ? (
              <div className="flex gap-2">
                <button
                  onClick={() => setShowLoginModal(true)}
                  className="text-blue-600 px-2 py-1 rounded text-xs font-medium"
                >
                  Sign In
                </button>
                <button
                  onClick={() => setShowRegisterModal(true)}
                  className="bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-semibold shadow-sm"
                >
                  Sign Up
                </button>
              </div>
            ) : (
              <span className="text-gray-600 text-xs">{userName || userEmail}</span>
            )}
          </div>
        </div>

        {/* Desktop login */}
        <div className="hidden md:flex justify-center mt-2">
          {!isLoggedIn ? (
            <div className="flex gap-2">
              <button onClick={() => setShowLoginModal(true)} className="text-blue-600 px-3 py-1 rounded text-sm font-medium hover:bg-blue-50">
                Sign In
              </button>
              <button onClick={() => setShowRegisterModal(true)} className="bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-semibold hover:bg-blue-700 transition-colors shadow-sm">
                Sign Up
              </button>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-gray-600 text-sm">{userName || userEmail}</p>
            </div>
          )}
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-h-0 bg-gray-50">
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{WebkitOverflowScrolling: 'touch'}}>

          {/* Mobile Premium CTA - Only show if no messages */}
          {messages.length === 0 && (
            <div className="bg-gradient-to-r from-blue-50 to-white border border-blue-100 p-4 rounded-xl mb-4 shadow-sm max-w-2xl mx-auto">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">✨</span>
                    <span className="font-bold text-blue-900">Premium Access</span>
                  </div>
                  <p className="text-xs text-gray-600">Unlimited guidance 24/7</p>
                </div>
                <button
                  onClick={() => setCurrentView('subscription')}
                  className="bg-blue-600 text-white px-4 py-2 rounded-full font-bold text-xs shadow-sm hover:bg-blue-700 transition-colors"
                >
                  $4.99/mo
                </button>
              </div>
            </div>
          )}

          {/* Chat content */}
          <div className="max-w-2xl mx-auto">

            {/* Welcome message */}
            {messages.length === 0 && (
              <div className="text-center py-6 mb-4">
                <h3 className="text-xl font-bold text-gray-800 mb-2">How can I help you today?</h3>
                <p className="text-gray-500 mb-6 text-sm">
                  I'm your biblical counselor. Everything you share here is private.
                </p>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {QUICK_STARTS.map((qs, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        sendMessage(qs.message);
                      }}
                      className="text-left p-4 rounded-xl bg-white border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all flex items-center gap-3 group"
                    >
                      <span className="text-2xl group-hover:scale-110 transition-transform duration-200">{qs.icon}</span>
                      <span className="font-medium text-gray-700 group-hover:text-blue-700 transition-colors">{qs.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Progress indicator for free users */}
            {userTier === 'free' && conversationDepth > 0 && (
              <div className="bg-white border border-gray-200 p-3 rounded-lg mb-4 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-gray-500">
                    Free Tier: {conversationDepth} / 20 messages
                  </span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-bold">
                    {Math.round((conversationDepth / 20) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-1.5 mb-2">
                  <div
                    className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min((conversationDepth / 20) * 100, 100)}%` }}
                  ></div>
                </div>
              </div>
            )}

            {/* Premium member status */}
            {userTier === 'unlimited' && (
              <div className="bg-green-50 border border-green-100 p-3 rounded-lg mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-green-600">💎</span>
                  <span className="text-green-800 text-sm font-medium">Premium Member</span>
                </div>
                <button
                  onClick={() => handleSubscriptionManagement()}
                  className="text-green-700 text-xs font-semibold hover:underline"
                >
                  Manage
                </button>
              </div>
            )}

            {/* Chat messages */}
            <div className="space-y-6">
              {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] px-5 py-3.5 rounded-2xl shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-white text-gray-800 border border-gray-100 rounded-bl-sm'
                  }`}>
                    <div className="text-[15px] leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-100 px-4 py-3 rounded-2xl rounded-bl-sm shadow-sm">
                    <div className="flex items-center space-x-1.5">
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.15s'}}></div>
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.3s'}}></div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Summarize CTA */}
            {messages.length >= 3 && !isLoading && (
              <div className="mt-8 text-center">
                <p className="text-gray-500 text-sm mb-3">Ready to bring this to prayer?</p>
                <button
                  onClick={handleSummarizeClick}
                  className="bg-white border border-blue-200 hover:bg-blue-50 text-blue-700 py-2.5 px-6 rounded-full font-semibold transition-colors shadow-sm text-sm"
                >
                  Summarize & Create Prayer
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Chat Input - Fixed at bottom */}
      <div className="flex-shrink-0 bg-white border-t border-gray-100 p-3 md:p-4" style={{
        paddingBottom: 'max(1rem, env(safe-area-inset-bottom))'
      }}>
        <div className="max-w-2xl mx-auto flex items-center gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !isLoading && sendMessage()}
            placeholder="Type your message..."
            className="flex-1 px-4 py-3 border border-gray-200 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50 text-gray-900 placeholder-gray-400"
            disabled={isLoading}
            style={{fontSize: '16px'}} // Prevent iOS zoom
          />
          <button
            onClick={() => sendMessage()}
            disabled={isLoading || !inputMessage.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 text-white p-3 rounded-full transition-colors shadow-sm flex-shrink-0 w-12 h-12 flex items-center justify-center"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 translate-x-0.5">
              <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );

  const renderReview = () => (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="flex-shrink-0 bg-white border-b border-gray-100 p-4 text-center">
        <h1 className="text-xl font-bold text-gray-900">Review Your Prayer</h1>
        <p className="text-xs text-gray-500 mt-1">Offer it to God privately, or share it anonymously.</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-lg mx-auto bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8">
          <h2 className="text-xl font-bold text-center text-gray-900 mb-6">{generatedSummary.title}</h2>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap font-serif text-lg">{generatedSummary.prayer}</p>
        </div>
      </div>

      <div className="flex-shrink-0 p-4 bg-white border-t border-gray-100">
        <div className="max-w-lg mx-auto space-y-3">
          <button
            onClick={() => handleSaveConfession(true)}
            disabled={isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3.5 px-4 rounded-xl transition-all shadow-sm disabled:opacity-50"
          >
            Share Anonymously to Help Others
          </button>
          <button
            onClick={() => handleSaveConfession(false)}
            disabled={isLoading}
            className="w-full bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 font-semibold py-3.5 px-4 rounded-xl transition-all disabled:opacity-50"
          >
            Keep Private (For God Alone)
          </button>
          <button
            onClick={() => setCurrentView('confess')}
            disabled={isLoading}
            className="w-full text-center text-sm text-gray-500 py-2 hover:text-gray-700"
          >
            Go back to chat
          </button>
        </div>
      </div>
    </div>
  );

  const renderConfession = () => (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="flex-1 p-6 overflow-y-auto flex items-center justify-center">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-3xl">✅</span>
          </div>
          
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Prayer Received</h2>
          <p className="text-gray-600 mb-8">
            {currentConfession?.is_public 
              ? "Your prayer has been shared anonymously to inspire others."
              : "Your prayer has been offered to God in privacy."}
          </p>

          <div className="space-y-3">
            <button
              onClick={() => setCurrentView('confess')}
              className="w-full px-6 py-3.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-semibold transition-colors shadow-sm"
            >
              Start New Conversation
            </button>
            <button
              onClick={() => setCurrentView('discover')}
              className="w-full px-6 py-3.5 bg-white border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-semibold transition-colors"
            >
              Read Community Prayers
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderDiscover = () => {
    // Check if user has premium access
    const isPremium = userTier === 'unlimited';
    
    // Freemium Teaser: Show top 3 confessions to free users
    const FREE_CONFESSION_LIMIT = 3;
    const visibleConfessions = isPremium 
      ? confessions 
      : confessions.slice(0, FREE_CONFESSION_LIMIT);
    const lockedCount = confessions.length - FREE_CONFESSION_LIMIT;

    return (
    <div className="flex flex-col h-full pb-20 bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-100 p-4 text-center sticky top-0 z-10">
        <h1 className="text-lg font-bold text-gray-900">Community Prayers</h1>
        <p className="text-xs text-gray-500">Real prayers from real people</p>
            </div>

        {confessions.length === 0 ? (
          /* Empty State - Loading or No Data */
          <div className="flex-1 flex items-center justify-center p-4">
            <div className="text-center text-gray-500">
              <div className="text-4xl mb-4 opacity-50">🙏</div>
              <p className="mb-4">Loading prayers...</p>
              <button
                onClick={() => fetchConfessions(confessionFilter)}
                className="text-blue-600 text-sm font-medium hover:underline"
              >
                Refresh
              </button>
            </div>
          </div>
        ) : (
          /* Content */
          <div className="flex-1 overflow-y-auto">
            {/* Filter */}
            <div className="flex justify-center py-4">
              <div className="bg-gray-200 p-1 rounded-lg inline-flex">
                <button
                  onClick={() => setConfessionFilter('latest')}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-all ${confessionFilter === 'latest' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                >
                  Latest
                </button>
                <button
                  onClick={() => setConfessionFilter('popular')}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-all ${confessionFilter === 'popular' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                >
                  Popular
                </button>
              </div>
            </div>

            <div className="px-4 pb-4 space-y-4 max-w-2xl mx-auto">
              {visibleConfessions.map((confession) => (
                <div key={confession.id} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                  <h3 className="font-bold text-gray-900 mb-2">{confession.title || "A Prayer"}</h3>
                  <p className="text-gray-600 text-sm leading-relaxed mb-4 whitespace-pre-wrap">{confession.text}</p>
                  <div className="flex justify-between items-center pt-3 border-t border-gray-50">
                    <button 
                      onClick={() => handleSharePrayer(confession)}
                      className="text-xs font-medium text-blue-600 hover:text-blue-700"
                    >
                      {copiedPrayerId === confession.id ? 'Copied!' : 'Share Prayer'}
                    </button>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      <span>{new Date(confession.created_at).toLocaleDateString()}</span>
                      <button
                        onClick={() => handleUpvoteClick(confession.id)}
                        disabled={upvotedConfessions.has(confession.id)}
                        className="flex items-center gap-1 hover:text-red-500 transition-colors disabled:opacity-50"
                      >
                        <span className={upvotedConfessions.has(confession.id) ? 'text-red-500' : ''}>❤️</span>
                        <span>{confession.upvotes || 0}</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              {/* Locked Preview for Free Users */}
              {!isPremium && lockedCount > 0 && (
                <div className="relative mt-6 py-8 text-center">
                  <div className="absolute inset-0 bg-gradient-to-t from-gray-50 via-gray-50/90 to-transparent z-10"></div>
                  
                  <div className="relative z-20 bg-white p-6 rounded-2xl shadow-lg border border-blue-100 max-w-sm mx-auto">
                    <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-4">
                      <span className="text-2xl">🔒</span>
                    </div>
                    <h3 className="font-bold text-gray-900 mb-2">
                      Unlock {lockedCount}+ More Prayers
                    </h3>
                    <p className="text-sm text-gray-600 mb-6">
                      Join our community to read all shared testimonies and prayers.
                    </p>
                    <button
                      onClick={() => {
                        track('unlock_prayers_clicked', { source: 'prayers_preview' });
                        setCurrentView('subscription');
                      }}
                      className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold shadow-md hover:bg-blue-700 transition-colors"
                    >
                      Unlock Full Access - $4.99/mo
                    </button>
                  </div>
                  
                  {/* Blurred placeholder content below */}
                  <div className="opacity-30 blur-sm pointer-events-none mt-4 space-y-4">
                    <div className="bg-white h-32 rounded-xl"></div>
                    <div className="bg-white h-32 rounded-xl"></div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      
      {/* Navigation */}
      <div className="bg-white border-t border-gray-100 p-4 sticky bottom-0 md:hidden">
        <button 
          onClick={() => setCurrentView('confess')}
          className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold shadow-sm"
        >
          Start Your Prayer
        </button>
      </div>
    </div>
    );
  };

  const renderSubscriptionPage = () => {
    return (
      <div className="flex flex-col h-full bg-gray-50 pb-20 overflow-y-auto">
        {/* Simple Header */}
        <div className="bg-white p-6 text-center border-b border-gray-100">
          <h1 className="text-2xl font-bold text-gray-900">Premium Membership</h1>
          <p className="text-gray-500 text-sm mt-1">Support the ministry & unlock unlimited guidance</p>
        </div>

        <div className="p-4 max-w-2xl mx-auto w-full space-y-6">
          {/* Current Status Card */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500 font-medium">YOUR STATUS</span>
              <span className={`px-3 py-1 rounded-full text-xs font-bold ${userTier === 'unlimited' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                {userTier === 'unlimited' ? 'PREMIUM' : 'FREE PLAN'}
              </span>
            </div>
            <p className="text-gray-900 font-medium">
              {userTier === 'unlimited' 
                ? 'You have unlimited access to all features.' 
                : `You have used ${conversationDepth} of 20 free messages.`}
            </p>
          </div>

          {/* Pricing Options */}
          {userTier === 'free' && (
            <div className="bg-white rounded-2xl shadow-lg border border-blue-100 overflow-hidden">
              <div className="bg-blue-600 p-2 text-center text-white text-xs font-bold tracking-wide">
                LIMITED TIME OFFER
              </div>
              
              <div className="p-6">
                <div className="flex justify-center mb-6">
                  <div className="bg-gray-100 p-1 rounded-lg flex text-sm font-medium">
                    <button
                      onClick={() => setSelectedPlan('monthly')}
                      className={`px-6 py-2 rounded-md transition-all ${
                        selectedPlan === 'monthly' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
                      }`}
                    >
                      Monthly
                    </button>
                    <button
                      onClick={() => setSelectedPlan('annual')}
                      className={`px-6 py-2 rounded-md transition-all flex items-center ${
                        selectedPlan === 'annual' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
                      }`}
                    >
                      Annual <span className="ml-1.5 text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">-33%</span>
                    </button>
                  </div>
                </div>

                <div className="text-center mb-8">
                  <div className="flex items-baseline justify-center gap-1">
                    <span className="text-4xl font-bold text-gray-900">
                      {selectedPlan === 'monthly' ? '$4.99' : '$39.99'}
                    </span>
                    <span className="text-gray-500">
                      /{selectedPlan === 'monthly' ? 'mo' : 'year'}
                    </span>
                  </div>
                  {selectedPlan === 'annual' && (
                    <p className="text-green-600 text-sm mt-2 font-medium">
                      Like paying just $3.33/month
                    </p>
                  )}
                </div>

                <ul className="space-y-4 mb-8">
                  {[
                    'Unlimited 24/7 Spiritual Guidance',
                    'Access Full Prayer Library',
                    'Save Your Spiritual Journey',
                    'Support the Ministry'
                  ].map((feature, i) => (
                    <li key={i} className="flex items-center gap-3 text-gray-700 text-sm">
                      <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                        <span className="text-green-600 text-xs">✓</span>
                      </div>
                      {feature}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleUpgrade()}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-bold text-lg shadow-lg transition-all transform hover:scale-[1.02]"
                >
                  {selectedPlan === 'monthly' ? 'Start Monthly Plan' : 'Get Annual Access'}
                </button>
                
                <p className="text-center text-xs text-gray-400 mt-4">
                  Secure payment via Stripe • Cancel anytime
                </p>
              </div>
            </div>
          )}

          {/* FAQ / Reassurance */}
          <div className="space-y-4">
            <div className="bg-white p-4 rounded-xl border border-gray-100">
              <h3 className="font-semibold text-gray-900 mb-1">Is this anonymous?</h3>
              <p className="text-sm text-gray-600">Yes, 100%. We don't require a login to start, and your conversations are private.</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-gray-100">
              <h3 className="font-semibold text-gray-900 mb-1">Why charge a fee?</h3>
              <p className="text-sm text-gray-600">The fee covers server costs and AI technology to keep this ministry running 24/7 for everyone.</p>
            </div>
          </div>
          
          <div className="text-center pt-4">
            <button onClick={() => setCurrentView('confess')} className="text-gray-500 text-sm hover:text-gray-700">
              Return to Chat
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Value-first upgrade modal component
  const UpgradeModal = () => (
    showUpgradeModal && (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[60] p-4 animate-fade-in">
        <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl relative overflow-hidden">
          
          <div className="absolute top-0 left-0 w-full h-1 bg-blue-500"></div>
          
          <button
            onClick={() => setShowUpgradeModal(false)}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
          
          <div className="text-center pt-2 pb-6">
            <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">💎</span>
            </div>
            
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Continue Your Journey
            </h2>
            
            <p className="text-gray-600 text-sm mb-6">
              You've reached the free limit. Unlock unlimited spiritual guidance for less than the price of a coffee.
            </p>
            
            <div className="bg-blue-50 rounded-xl p-4 mb-6 border border-blue-100">
              <div className="flex justify-between items-baseline mb-1">
                <span className="text-lg font-bold text-blue-900">$4.99</span>
                <span className="text-sm text-blue-700">/ month</span>
              </div>
              <p className="text-xs text-blue-600 text-left">Cancel anytime. Secure payment.</p>
            </div>
            
            <button
              onClick={() => handleUpgrade()}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3.5 rounded-xl font-bold shadow-lg transition-all"
            >
              Upgrade Now
            </button>
            
            <button
              onClick={() => setShowUpgradeModal(false)}
              className="mt-4 text-sm text-gray-400 hover:text-gray-600"
            >
              Not right now
            </button>
          </div>
        </div>
      </div>
    )
  );

  // Login modal component
  const LoginModal = () => (
    showLoginModal && (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[60] p-4">
        <div className="bg-white rounded-2xl max-w-md w-full p-8 shadow-xl">
          <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">Welcome Back</h2>
          <p className="text-gray-500 text-center mb-8">Sign in to continue your journey</p>
          
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            handleLogin(formData.get('email'), formData.get('password'));
          }} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1 uppercase tracking-wide">Email</label>
              <input
                type="email"
                name="email"
                required
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all outline-none"
                placeholder="name@example.com"
              />
            </div>
            
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1 uppercase tracking-wide">Password</label>
              <input
                type="password"
                name="password"
                required
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all outline-none"
                placeholder="••••••••"
              />
            </div>
            
            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3.5 rounded-xl font-bold shadow-md transition-all mt-2"
            >
              Sign In
            </button>
          </form>
          
          <div className="mt-6 text-center space-y-3">
            <button
              onClick={() => {
                setShowLoginModal(false);
                setShowRegisterModal(true);
              }}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Create an account
            </button>
            <div>
              <button
                onClick={() => setShowLoginModal(false)}
                className="text-gray-400 hover:text-gray-600 text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  );

  // Register modal component
  const RegisterModal = () => (
    showRegisterModal && (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[60] p-4">
        <div className="bg-white rounded-2xl max-w-md w-full p-8 shadow-xl">
          <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">Create Account</h2>
          <p className="text-gray-500 text-center mb-8">Join our supportive community</p>
          
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            handleRegister(formData.get('email'), formData.get('password'), formData.get('name'));
          }} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1 uppercase tracking-wide">Name</label>
              <input
                type="text"
                name="name"
                required
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all outline-none"
                placeholder="Your name"
              />
            </div>
            
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1 uppercase tracking-wide">Email</label>
              <input
                type="email"
                name="email"
                required
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all outline-none"
                placeholder="name@example.com"
              />
            </div>
            
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1 uppercase tracking-wide">Password</label>
              <input
                type="password"
                name="password"
                required
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all outline-none"
                placeholder="Create password"
              />
            </div>
            
            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3.5 rounded-xl font-bold shadow-md transition-all mt-2"
            >
              Create Account
            </button>
          </form>
          
          <div className="mt-6 text-center space-y-3">
            <button
              onClick={() => {
                setShowRegisterModal(false);
                setShowLoginModal(true);
              }}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Already have an account? Sign in
            </button>
            <div>
              <button
                onClick={() => setShowRegisterModal(false)}
                className="text-gray-400 hover:text-gray-600 text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  );

  const handleUpgrade = async () => {
    // Track upgrade button click
    track('upgrade_button_clicked', { 
      plan: selectedPlan,
      source: showUpgradeModal ? 'modal' : 'page',
      conversation_depth: conversationDepth
    });
    
    try {
      const currentSessionId = isLoggedIn ? userSessionId : sessionId;
      const response = await fetch('/api/stripe/create-checkout-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessionId,
          plan: selectedPlan // 'monthly' or 'annual'
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
    track('register_attempt');
    
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
        track('register_success', { tier: data.tier });
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
    track('login_attempt');
    
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
        track('login_success', { tier: data.tier });
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
    <div className="mobile-navigation md:hidden shadow-lg z-40 bg-white border-t border-gray-100">
      <div className="flex h-full">
          <button
          onClick={() => setCurrentView('confess')}
          className={`flex-1 py-3 text-center transition-colors ${
            currentView === 'confess' || currentView === 'review' || currentView === 'confession' ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'
          }`}
        >
          <div className="text-xl mb-1">✝️</div>
          <div className="text-[10px] font-bold uppercase tracking-wide">Chat</div>
          </button>
              <button
          onClick={() => setCurrentView('discover')}
          className={`flex-1 py-3 text-center transition-colors relative ${
            currentView === 'discover' ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'
          }`}
        >
          {userTier !== 'unlimited' && (
            <div className="absolute top-2 right-[25%] bg-yellow-400 w-2 h-2 rounded-full"></div>
          )}
          <div className="text-xl mb-1">🌍</div>
          <div className="text-[10px] font-bold uppercase tracking-wide">Community</div>
              </button>
                <button
            onClick={() => setCurrentView('subscription')}
          className={`flex-1 py-3 text-center transition-colors ${
            currentView === 'subscription' ? 'text-blue-600' : 'text-gray-400 hover:text-blue-600'
          }`}
        >
          <div className="text-xl mb-1">💎</div>
          <div className="text-[10px] font-bold uppercase tracking-wide">Premium</div>
                </button>
        </div>
      </div>
    );

    return (
    <div className="h-screen bg-gray-50 flex flex-col overflow-hidden relative font-sans">
      {/* Toast Notification */}
      {showToast && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-[70] animate-fade-in w-[90%] max-w-md">
          <div className="bg-blue-600 text-white px-4 py-3 rounded-xl shadow-xl flex items-start space-x-3">
            <div className="text-xl mt-0.5">💙</div>
            <div className="flex-1">
              <p className="text-sm font-medium leading-snug">{toastMessage}</p>
            </div>
            <button
              onClick={() => setShowToast(false)}
              className="text-white/80 hover:text-white"
            >
              ✕
            </button>
          </div>
        </div>
      )}
      
      {/* Desktop Navigation */}
      <div className="hidden md:block bg-white border-b border-gray-100 shadow-sm z-20">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-8">
              <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity text-decoration-none">
                <h1 className="text-xl font-bold text-blue-900 flex items-center gap-2">
                  <span className="text-blue-800">✝</span> My Confessions
                </h1>
              </a>
              <div className="flex bg-gray-50 p-1 rounded-lg">
                <button
                  onClick={() => setCurrentView('confess')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                    currentView === 'confess' ? 'bg-white text-blue-900 shadow-sm' : 'text-gray-500 hover:text-gray-900'
                  }`}
                >
                  Chat
                </button>
                <button
                  onClick={() => setCurrentView('discover')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                    currentView === 'discover' ? 'bg-white text-blue-900 shadow-sm' : 'text-gray-500 hover:text-gray-900'
                  }`}
                >
                  Community
                </button>
                <button
                  onClick={() => setCurrentView('subscription')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                    currentView === 'subscription' ? 'bg-white text-blue-900 shadow-sm' : 'text-gray-500 hover:text-gray-900'
                  }`}
                >
                  Premium
                </button>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {userTier !== 'unlimited' && (
                <button
                  onClick={() => setCurrentView('subscription')}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-full text-sm font-bold transition-all shadow-sm hover:shadow-md"
                >
                  Unlock Premium - $4.99
                </button>
              )}
              
              {isLoggedIn ? (
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-600">{userName}</span>
                  <button 
                    onClick={() => {
                      setIsLoggedIn(false);
                      setUserSessionId('');
                      setMessages([]);
                      // Reload anonymous session
                      window.location.reload();
                    }}
                    className="text-xs text-gray-400 hover:text-gray-600"
                  >
                    Sign Out
                  </button>
                </div>
              ) : (
                <button 
                  onClick={() => setShowLoginModal(true)}
                  className="text-sm font-medium text-gray-600 hover:text-blue-600"
                >
                  Sign In
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden relative">
        {currentView === 'confess' && renderConfess()}
        {currentView === 'review' && renderReview()}
        {currentView === 'confession' && renderConfession()}
        {currentView === 'discover' && renderDiscover()}
        {currentView === 'subscription' && renderSubscriptionPage()}
      </div>

      {/* Mobile Navigation */}
      <div className="md:hidden">
        {renderNavigation()}
      </div>
      
      {/* Value-first upgrade modal */}
      <UpgradeModal />
      <LoginModal />
      <RegisterModal />
    </div>
  );
};

// Make MyConfessionsApp available globally for browser
window.MyConfessionsApp = MyConfessionsApp;