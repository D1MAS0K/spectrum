// Service Worker for Rosh Naki PWA
const CACHE_NAME = 'rosh-naki-v1';
const urlsToCache = [
    '/',
    '/app',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/dashboard.js',
    '/static/manifest.json',
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request);
        })
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(names =>
            Promise.all(
                names.filter(name => name !== CACHE_NAME).map(name => caches.delete(name))
            )
        )
    );
});
