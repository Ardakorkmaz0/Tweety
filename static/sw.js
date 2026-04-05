// Tweety Service Worker - Push Notifications
self.addEventListener('push', function(event) {
    let data = { title: 'Tweety', body: 'You have a new message!', url: '/tweetapp/chat/' };

    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body,
        icon: '/static/tweetapp/favicon.png',
        badge: '/static/tweetapp/favicon.png',
        vibrate: [100, 50, 100],
        data: { url: data.url || '/tweetapp/chat/' },
        actions: [
            { action: 'open', title: 'Open' },
            { action: 'close', title: 'Close' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'Tweety', options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    if (event.action === 'close') return;

    const url = event.notification.data.url || '/tweetapp/chat/';
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            for (const client of clientList) {
                if (client.url.includes('/tweetapp/') && 'focus' in client) {
                    client.navigate(url);
                    return client.focus();
                }
            }
            return clients.openWindow(url);
        })
    );
});
