const { useState, useEffect } = React;

const SentimentalApp = () => {
  const [currentView, setCurrentView] = useState('confess');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(`session_${Math.random().toString(36).substr(2, 9)}`);
  const [confessions, setConfessions] = useState([]);
  const [upvotedConfessions, setUpvotedConfessions] = useState(new Set());
  const [confessionFilter, setConfessionFilter] = useState('latest');
  const [currentConfession, setCurrentConfession] = useState(null);
  const [generatedSummary, setGeneratedSummary] = useState({ title: '', prayer: '' });
  const [donationAmount, setDonationAmount] = useState(25);
  const [donationFrequency, setDonationFrequency] = useState('one-time');

  // Load public confessions on mount
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
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
          conversation_history: messages
        })
      });

      const data = await response.json();
      if (data.success) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
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
      {/* Presidential Campaign Header */}
      <div className="relative overflow-hidden">
        <div className="bg-blue-600 text-white p-6 text-center relative">
          {/* Star pattern overlay */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-4 left-4 text-yellow-300">★</div>
            <div className="absolute top-8 right-8 text-yellow-300">★</div>
            <div className="absolute bottom-4 left-1/4 text-yellow-300">★</div>
            <div className="absolute bottom-8 right-1/4 text-yellow-300">★</div>
          </div>
          
          <div className="relative z-10">
            <div className="text-4xl mb-3">✝️</div>
            <h1 className="text-3xl font-bold mb-2 tracking-tight text-white drop-shadow-lg">Confessiones</h1>
            <p className="text-white font-medium text-lg drop-shadow-md">Sacrament of Reconciliation with Biblical Guidance</p>
            
            {/* Campaign-style stats */}
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
          </div>
        </div>
      </div>

      {/* Mission Statement */}
      <div className="bg-white mx-4 mt-4 rounded-lg shadow-lg p-6 border-l-4 border-blue-600">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Our Mission</h2>
        <p className="text-gray-600 leading-relaxed">
          We provide <strong>free spiritual guidance</strong> to help people find God's mercy and forgiveness. 
          Your donations help us reach more souls in need of spiritual support.
        </p>
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-500">
            <span className="font-semibold text-blue-600">Goal:</span> Help 100,000+ souls find peace
          </div>
          <button 
            onClick={() => setCurrentView('donation')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-bold text-sm transition-all duration-200 shadow-lg border-2 border-blue-600"
          >
            💝 Support Our Mission
          </button>
        </div>
      </div>

      {/* Chat Interface */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8 bg-white rounded-lg shadow-sm border border-gray-200 mx-4">
            <div className="text-4xl mb-4">🙏</div>
            <h3 className="text-xl font-bold text-gray-800 mb-3">Welcome to the Sacrament of Reconciliation</h3>
            <p className="text-gray-600 mb-4">
              I am here as your spiritual guide, drawing from Scripture and Christian tradition to help you examine your conscience and find God's mercy.
            </p>
            <p className="text-sm text-gray-500">
              <strong>What burdens your heart today?</strong>
            </p>
          </div>
        )}
        
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl ${
              msg.role === 'user' 
                ? 'bg-blue-600 text-white rounded-br-md' 
                : 'bg-white text-gray-800 border border-gray-200 rounded-bl-md shadow-sm'
            }`}>
              <div className="text-sm leading-relaxed">{msg.content}</div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white text-gray-800 border border-gray-200 rounded-2xl rounded-bl-md shadow-sm px-4 py-3">
              <div className="flex items-center space-x-2 text-sm">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
                <span>Processing your confession...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Finalise CTA */}
      {messages.length >= 3 && !isLoading && (
        <div className="mx-4 mb-4 bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg flex items-center justify-between space-x-4">
          <p className="text-sm text-gray-700 font-medium flex-1">
            Ready to bring this to prayer?
          </p>
          <button
            onClick={handleSummarizeClick}
            className="bg-yellow-400 hover:bg-yellow-500 text-black font-bold px-4 py-2 rounded-lg shadow-md border-2 border-yellow-300"
          >
            Summarize & Review
          </button>
        </div>
      )}

      {/* Chat Input - Fixed at Bottom */}
      <div className="bg-white border-t border-gray-200 p-4 mb-20">
        <div className="flex space-x-3">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Share your confession..."
            className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-800 font-medium"
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !inputMessage.trim()}
            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-full font-bold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg border-2 border-blue-600"
          >
            <span className="text-lg font-bold">Send</span>
          </button>
        </div>
      </div>
      



    </div>
  );

  const renderReview = () => (
    <div className="flex flex-col h-full bg-gray-50 pb-20">
      <div className="bg-blue-600 text-white p-6 text-center">
        <h1 className="text-2xl font-bold">An Act of Contrition</h1>
        <p className="text-sm opacity-90 mt-1">You have prepared your prayer. Offer it to God privately, or share it anonymously to help and inspire others.</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-xl font-bold text-center text-gray-800 mb-4">{generatedSummary.title}</h2>
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
          className="w-full text-center text-sm text-gray-500 py-2"
        >
          Continue Chatting
        </button>
      </div>
    </div>
  );

  const renderConfession = () => (
    <div className="flex flex-col h-full">
      <div className="bg-blue-600 text-white p-4 text-center">
        <h1 className="text-2xl font-bold">Peace Be With You</h1>
        <p className="text-sm opacity-90">You have completed your confession. Go in peace.</p>
      </div>
      <div className="flex-1 p-6 overflow-y-auto pb-24">
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="text-center mb-4">
            <div className="text-4xl mb-2">✅</div>
            <h2 className="text-xl font-semibold text-gray-800">Your Prayer Has Been Offered</h2>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <p className="text-gray-700 leading-relaxed">{currentConfession?.text}</p>
          </div>
          
          <div className="text-center text-sm text-gray-500 mb-6">
            {currentConfession?.is_public ? (
              <p>Your prayer has been shared anonymously to help and inspire others.</p>
            ) : (
              <p>Your prayer has been offered to God alone and was not shared publicly.</p>
            )}
          </div>
          
          <div className="flex flex-col space-y-3">
            <button
              onClick={() => setCurrentView('confess')}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold"
            >
              Start New Confession
            </button>
            <button
              onClick={() => setCurrentView('discover')}
              className="w-full px-4 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-semibold"
            >
              See Other Prayers
            </button>
            <button
              onClick={() => setCurrentView('donation')}
              className="w-full px-4 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-semibold"
            >
              💝 Support Our Mission
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderDiscover = () => (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4 text-center">
        <h1 className="text-2xl font-bold">✝️ Shared Prayers</h1>
        <p className="text-sm opacity-90">Read prayers shared anonymously by others from around the world.</p>
      </div>

      {/* Filter Buttons */}
      <div className="flex justify-center p-3 bg-gray-100 border-b">
        <div className="flex space-x-2 bg-gray-200 p-1 rounded-lg">
          <button
            onClick={() => setConfessionFilter('latest')}
            className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-colors ${confessionFilter === 'latest' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600'}`}
          >
            Latest
          </button>
          <button
            onClick={() => setConfessionFilter('popular')}
            className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-colors ${confessionFilter === 'popular' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600'}`}
          >
            Most Popular
          </button>
        </div>
      </div>

      {/* Confessions List */}
      <div className="flex-1 overflow-y-auto p-4">
        {confessions.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <p className="text-lg mb-2">No public prayers yet</p>
            <p className="text-sm">Be the first to share a prayer to help others.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {confessions.map((confession) => (
              <div key={confession.id} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm transition-all hover:shadow-md">
                <h3 className="font-bold text-gray-800 text-md mb-2">{confession.title || "A Prayer"}</h3>
                <p className="text-gray-700 leading-relaxed mb-4">{confession.text}</p>
                <div className="flex justify-between items-center text-xs text-gray-500">
                  <span>{new Date(confession.created_at).toLocaleDateString()}</span>
                  <button
                    onClick={() => handleUpvoteClick(confession.id)}
                    disabled={upvotedConfessions.has(confession.id)}
                    className="flex items-center space-x-1 p-1 rounded-md transition-colors disabled:opacity-70 disabled:cursor-not-allowed group hover:bg-red-100"
                  >
                    <span className={`transition-transform ${upvotedConfessions.has(confession.id) ? 'text-red-500' : 'text-gray-400 group-hover:text-red-400'}`}>❤️</span>
                    <span className="font-semibold">{confession.upvotes || 0}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="border-t bg-white p-4">
        <button
          onClick={() => setCurrentView('confess')}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold"
        >
          ✝️ Start Your Own Confession
        </button>
      </div>
    </div>
  );

  const renderDonationPage = () => (
    <div className="flex flex-col h-full bg-gray-50 pb-20">
      {/* 1. New Header */}
      <div className="relative bg-blue-600 text-white p-6 text-center overflow-hidden">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold tracking-tight text-white">Become a Beacon of Hope</h1>
          <p className="text-lg mt-2 opacity-90">Your generosity provides free, anonymous spiritual guidance to souls in need.</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* 2. Impact Section */}
        <div className="bg-white rounded-xl shadow-lg p-6 text-center">
          <h2 className="text-xl font-bold text-gray-800 mb-4">Why Your Support Matters</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
               <div className="text-3xl mb-2">✝️</div>
               <h3 className="font-semibold text-gray-700">Free Confession</h3>
               <p className="text-sm text-gray-600 mt-1">We are committed to keeping this service 100% free for everyone, forever.</p>
            </div>
            <div className="text-center">
               <div className="text-3xl mb-2">🌍</div>
               <h3 className="font-semibold text-gray-700">Global Reach</h3>
               <p className="text-sm text-gray-600 mt-1">Your gift helps us reach thousands of souls across the world seeking peace.</p>
            </div>
            <div className="text-center">
               <div className="text-3xl mb-2">🔒</div>
               <h3 className="font-semibold text-gray-700">Safe & Anonymous</h3>
               <p className="text-sm text-gray-600 mt-1">We maintain a secure, private, and anonymous platform for our users.</p>
            </div>
          </div>
        </div>

        {/* 3. Donation Form */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-bold text-gray-800 text-center mb-4">Choose Your Gift</h3>
          
          {/* Frequency */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            <button onClick={() => setDonationFrequency('one-time')} className={`p-3 rounded-lg border-2 font-semibold transition-all ${donationFrequency === 'one-time' ? 'bg-blue-600 border-blue-600 text-white' : 'bg-gray-100 border-gray-200 text-gray-700'}`}>One-Time</button>
            <button onClick={() => setDonationFrequency('monthly')} className={`p-3 rounded-lg border-2 font-semibold transition-all ${donationFrequency === 'monthly' ? 'bg-blue-600 border-blue-600 text-white' : 'bg-gray-100 border-gray-200 text-gray-700'}`}>Monthly</button>
          </div>
          
          {/* Amounts */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            {[10, 25, 50, 100, 250, 500].map((amount) => (
              <button
                key={amount}
                onClick={() => setDonationAmount(amount)}
                className={`py-3 px-2 rounded-lg border-2 font-semibold transition-all text-center ${donationAmount === amount ? 'border-blue-600 bg-blue-50 text-blue-600' : 'border-gray-300 text-gray-700 hover:border-blue-400'}`}
              >
                ${amount}
              </button>
            ))}
          </div>

          {/* Custom Amount */}
          <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Or enter a custom amount:</label>
              <input
                type="number"
                value={donationAmount}
                onChange={(e) => setDonationAmount(parseInt(e.target.value) || 0)}
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0"
              />
          </div>

          {/* Impact Statement */}
          <div className="bg-green-50 rounded-lg p-4 border border-green-200 text-center">
              <p className="text-sm text-green-800">
                Your <strong>${donationAmount} {donationFrequency === 'monthly' ? 'monthly' : 'one-time'}</strong> gift can help us guide <strong>{Math.round(donationAmount / 5)} souls</strong>.
              </p>
          </div>
        </div>

        {/* 4. Final CTA Buttons */}
        <div className="space-y-3 px-4">
            <button
              onClick={() => {
                alert(`Thank you for your generous heart! Stripe integration coming soon. You selected $${donationAmount} ${donationFrequency}.`);
                setCurrentView('confess');
              }}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-bold text-lg transition-all duration-200 shadow-lg"
            >
              Donate ${donationAmount} {donationFrequency === 'monthly' ? 'Monthly' : 'Now'}
            </button>
            
            <button
              onClick={() => setCurrentView('confess')}
              className="w-full text-gray-600 py-3 rounded-lg font-semibold hover:bg-gray-200 transition-colors"
            >
              Maybe Later
            </button>
        </div>

        <div className="text-center text-xs text-gray-500 pt-4 px-4">
          For questions or support, please contact us at <a href="mailto:support@confessiones.org" className="underline text-blue-600">support@confessiones.org</a>.
        </div>
      </div>
    </div>
  );

  const renderNavigation = () => (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 md:hidden shadow-lg">
      <div className="flex">
        <button
          onClick={() => setCurrentView('confess')}
          className={`flex-1 py-3 text-center transition-colors ${
            currentView === 'confess' ? 'text-blue-600 border-t-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <div className="text-xl mb-1">✝️</div>
          <div className="text-xs font-medium">Confess</div>
        </button>
        <button
          onClick={() => setCurrentView('discover')}
          className={`flex-1 py-3 text-center transition-colors ${
            currentView === 'discover' ? 'text-blue-600 border-t-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <div className="text-xl mb-1">🔍</div>
          <div className="text-xs font-medium">Shared Prayers</div>
        </button>
        <button
          onClick={() => setCurrentView('donation')}
          className={`flex-1 py-3 text-center transition-colors ${
            currentView === 'donation' ? 'text-blue-600 border-t-2 border-blue-600' : 'text-gray-500 hover:text-blue-600'
          }`}
        >
          <div className="text-xl mb-1">💝</div>
          <div className="text-xs font-medium">Donate</div>
        </button>
      </div>
    </div>
  );

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Desktop Navigation */}
      <div className="hidden md:block bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-8">
              <h1 className="text-xl font-bold text-gray-800">✝️ Confessiones</h1>
              <button
                onClick={() => setCurrentView('confess')}
                className={`px-3 py-2 rounded-lg ${
                  currentView === 'confess' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Confess
              </button>
              <button
                onClick={() => setCurrentView('discover')}
                className={`px-3 py-2 rounded-lg ${
                  currentView === 'discover' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Shared Prayers
              </button>
              <button
                onClick={() => setCurrentView('donation')}
                className={`px-3 py-2 rounded-lg ${
                  currentView === 'donation' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-blue-700'
                }`}
              >
                💝 Donate
              </button>
            </div>
            <button
              onClick={() => setCurrentView('donation')}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold transition-all duration-200"
            >
              💝 Support Mission
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {currentView === 'confess' && renderConfess()}
        {currentView === 'review' && renderReview()}
        {currentView === 'confession' && renderConfession()}
        {currentView === 'discover' && renderDiscover()}
        {currentView === 'donation' && renderDonationPage()}
      </div>

      {/* Mobile Navigation */}
      {renderNavigation()}
    </div>
  );
};

// Make SentimentalApp available globally for browser
window.SentimentalApp = SentimentalApp;