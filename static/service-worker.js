const CACHE_NAME = 'placar-v1';
const urlsToCache = [
  '/',
  '/static/css/placar.css',
  '/static/css/placar_mesa.css',
  '/static/js/placar.js',
  '/static/js/placar_mesa.js'
];

// Instalar service worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache).catch(() => {}))
      .catch(() => {})
  );
  self.skipWaiting();
});

// Ativar service worker
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Interceptar requisições
self.addEventListener('fetch', event => {
  // Sempre tenta rede primeiro para dados dinâmicos
  if (event.request.url.includes('/api/') || event.request.url.includes('/placar')) {
    event.respondWith(
      fetch(event.request)
        .catch(() => caches.match(event.request))
    );
  } else {
    // Para assets estáticos, tenta cache primeiro
    event.respondWith(
      caches.match(event.request)
        .then(response => response || fetch(event.request))
        .catch(() => new Response('Offline', { status: 503 }))
    );
  }
});
