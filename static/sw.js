// TechStock Service Worker — Cache estatico, network-first para HTML
var CACHE_NAME = 'techstock-v4';
var STATIC_ASSETS = [
  '/static/vendor/bootstrap/bootstrap.min.css',
  '/static/vendor/bootstrap/bootstrap.bundle.min.js',
  '/static/vendor/bootstrap-icons/bootstrap-icons.css',
  '/static/vendor/chartjs/chart.umd.min.js',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/js/chatbot.js',
  '/static/js/help.js'
];

// Instalar — cachear assets estaticos
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activar — limpiar caches viejos
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(
        names.filter(function(name) { return name !== CACHE_NAME; })
             .map(function(name) { return caches.delete(name); })
      );
    })
  );
  self.clients.claim();
});

// Fetch — network-first para HTML, cache-first para static
self.addEventListener('fetch', function(event) {
  var url = new URL(event.request.url);

  // Cache-first para assets estaticos
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(function(cached) {
        return cached || fetch(event.request).then(function(response) {
          if (response.ok) {
            var clone = response.clone();
            caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, clone); });
          }
          return response;
        });
      })
    );
    return;
  }

  // Network-first para todo lo demas (HTML, API)
  event.respondWith(
    fetch(event.request).catch(function() {
      return caches.match(event.request);
    })
  );
});
