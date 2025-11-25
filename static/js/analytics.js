// Analytics wrapper for Google Analytics 4, Google Tag Manager and Facebook Pixel
window.track = (eventName, params = {}) => {
  // Google Analytics 4 via gtag
  if (window.gtag) {
    window.gtag('event', eventName, params);
    console.log('GA4 Event:', eventName, params);
  }
  
  // Google Tag Manager - push to dataLayer
  if (window.dataLayer) {
    window.dataLayer.push({
      'event': eventName,
      ...params
    });
    console.log('GTM Event:', eventName, params);
  }
  
  // Facebook Pixel (if enabled)
  if (window.fbq) {
    // Map custom events to Facebook standard events where possible
    const fbEventMap = {
      'register_success': 'CompleteRegistration',
      'upgrade_button_clicked': 'InitiateCheckout',
      'page_view': 'PageView',
      'view_change': 'ViewContent'
    };
    
    const fbEvent = fbEventMap[eventName] || eventName;
    window.fbq('track', fbEvent, params);
  }
};

// Identify user once available
window.setAnalyticsUser = (userId) => {
  // Google Analytics 4 - set user ID
  if (window.gtag && userId) {
    window.gtag('set', 'user_properties', {
      user_id: userId
    });
  }
  
  // Google Tag Manager - push user ID to dataLayer
  if (window.dataLayer && userId) {
    window.dataLayer.push({
      'event': 'user_identified',
      'user_id': userId
    });
  }
  
  // Facebook Pixel user identification
  if (window.fbq && userId) {
    window.fbq('setUserID', userId);
  }
}; 