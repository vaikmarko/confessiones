// Basic GA4 wrapper for Sentimental
window.track = (eventName, params = {}) => {
  if (window.gtag) {
    window.gtag('event', eventName, params);
  }
};

// Identify user once available
window.setAnalyticsUser = (userId) => {
  if (window.gtag && userId) {
    window.gtag('set', 'user_properties', { user_id: userId });
  }
}; 