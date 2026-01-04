const CACHE_NAME = 'bilingual-tutor-v1';
const OFFLINE_CACHE = 'offline-cache-v1';

const CRITICAL_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/js/learning.js',
    '/static/js/progress.js',
    '/static/js/mobile.js',
    '/templates/base.html',
    '/templates/index.html'
];

const OFFLINE_PAGE = '/static/errors/offline.html';

self.addEventListener('install', (event) => {
    console.log('[SW] Installing Service Worker...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching critical assets');
                return cache.addAll(CRITICAL_ASSETS);
            })
            .then(() => {
                return self.skipWaiting();
            })
    );
});

self.addEventListener('activate', (event) => {
    console.log('[SW] Activating Service Worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== CACHE_NAME && cacheName !== OFFLINE_CACHE) {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                return self.clients.claim();
            })
    );
});

self.addEventListener('fetch', (event) => {
    if (event.request.method === 'POST') {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                if (response) {
                    console.log('[SW] Serving from cache:', event.request.url);
                    return response;
                }

                return fetch(event.request)
                    .then((response) => {
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }

                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME)
                            .then((cache) => {
                                cache.put(event.request, responseToCache);
                            });

                        return response;
                    })
                    .catch((error) => {
                        console.log('[SW] Fetch failed:', error);
                        
                        if (event.request.mode === 'navigate') {
                            return caches.match(OFFLINE_PAGE) || caches.match('/');
                        }

                        if (event.request.destination === 'image') {
                            return new Response(
                                '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="#f1f5f9" width="100%" height="100%"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="#64748b">离线</text></svg>',
                                { headers: { 'Content-Type': 'image/svg+xml' } }
                            );
                        }
                    });
            })
    );
});

self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'CLEAR_CACHE') {
        clearAllCaches();
    }
});

async function clearAllCaches() {
    const cacheNames = await caches.keys();
    await Promise.all(
        cacheNames.map(cacheName => caches.delete(cacheName))
    );
    console.log('[SW] All caches cleared');
}

self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync:', event.tag);
    
    if (event.tag === 'sync-learning-data') {
        event.waitUntil(syncLearningData());
    }
});

async function syncLearningData() {
    try {
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_STATUS',
                status: 'syncing'
            });
        });

        console.log('[SW] Syncing learning data...');
        
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_STATUS',
                status: 'completed'
            });
        });
    } catch (error) {
        console.error('[SW] Sync failed:', error);
        
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_STATUS',
                status: 'failed',
                error: error.message
            });
        });
    }
}

self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');
    
    const options = {
        body: event.data ? event.data.text() : '您有新的学习提醒',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        vibrate: [200, 100, 200],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: '开始学习',
                icon: '/static/icons/play.png'
            },
            {
                action: 'close',
                title: '关闭',
                icon: '/static/icons/close.png'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('双语导师系统', options)
    );
});

self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked:', event.notification.data);
    
    event.notification.close();
    
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

self.addEventListener('periodicsync', (event) => {
    if (event.tag === 'daily-reminder') {
        event.waitUntil(showDailyReminder());
    }
});

async function showDailyReminder() {
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
        client.postMessage({
            type: 'DAILY_REMINDER',
            message: '今天的学习任务还未完成,快去学习吧!'
        });
    });
}
