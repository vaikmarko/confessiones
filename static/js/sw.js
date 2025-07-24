const CACHE_NAME = 'sentimental-app-v1';
const urlsToCache = ['/app', '/static/js/sentimental-app.jsx', 'https://cdn.tailwindcss.com/', 'https://unpkg.com/react@18/umd/react.development.js', 'https://unpkg.com/react-dom@18/umd/react-dom.development.js', 'https://unpkg.com/@babel/standalone/babel.min.js', 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'];
self.addEventListener('install', function (event) {
  event.waitUntil(caches.open(CACHE_NAME).then(function (cache) {
    console.log('Opened cache');
    return cache.addAll(urlsToCache);
  }));
});
self.addEventListener('fetch', function (event) {
  event.respondWith(caches.match(event.request).then(function (response) {
    // Cache hit - return response
    if (response) {
      return response;
    }
    return fetch(event.request).then(function (response) {
      // Check if we received a valid response
      if (!response || response.status !== 200 || response.type !== 'basic') {
        return response;
      }

      // IMPORTANT: Clone the response. A response is a stream
      // and because we want the browser to consume the response
      // as well as the cache consuming the response, we need
      // to clone it so we have two streams.
      var responseToCache = response.clone();
      caches.open(CACHE_NAME).then(function (cache) {
        cache.put(event.request, responseToCache);
      });
      return response;
    });
  }));
});
self.addEventListener('activate', function (event) {
  event.waitUntil(caches.keys().then(function (cacheNames) {
    return Promise.all(cacheNames.map(function (cacheName) {
      if (cacheName !== CACHE_NAME) {
        return caches.delete(cacheName);
      }
    }));
  }));
});