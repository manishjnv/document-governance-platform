// ponytail: no Workbox — cache-first for static assets, network-first for API calls covers T-3062/T-3063.
const STATIC_CACHE = 'edgp-static-v2';
const API_CACHE = 'edgp-api-v2';

// No auto skipWaiting on install: staying in "waiting" state until the client
// acks (T-3065) is what lets service-worker-register.tsx show an update banner.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE && key !== API_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  const isApi = url.pathname.startsWith('/api/');
  // HTML page navigations (request.mode === 'navigate') were previously
  // served cache-first alongside JS/CSS/images -- since Next.js re-renders
  // the SAME URL (e.g. /dashboard) on every deploy, a stale cached page
  // was served FOREVER after the first visit, silently masking every
  // future code change (branding, new columns, bug fixes -- all of it)
  // until a user manually cleared site data. Page navigations now go
  // network-first like API calls; only content-hashed static assets
  // (/_next/static/*, images, fonts) stay cache-first, since those are
  // safe to cache indefinitely (a new build gets a new hashed filename).
  const isNavigation = request.mode === 'navigate' || request.destination === 'document';

  if (isApi || isNavigation) {
    // Network-first: try live data/page, fall back to last-known-good cache when offline.
    const cacheName = isApi ? API_CACHE : STATIC_CACHE;
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(cacheName).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Cache-first for content-hashed static assets (JS/CSS/images/fonts).
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(STATIC_CACHE).then((cache) => cache.put(request, clone));
        }
        return response;
      });
    })
  );
});
