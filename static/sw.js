const CACHE_NAME = 'fikir-v1';

self.addEventListener('install', function(e) {
    e.waitUntil(
        caches.open(CACHE_NAME).then(function(c) {
            return c.addAll(['/', '/assets/logo.png']).catch(function() {});
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', function(e) {
    e.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(keys.filter(function(k) { return k !== CACHE_NAME; }).map(function(k) { return caches.delete(k); }));
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', function(e) {
    if (e.request.method !== 'GET') return;
    e.respondWith(
        fetch(e.request).catch(function() {
            return caches.match(e.request);
        })
    );
});
