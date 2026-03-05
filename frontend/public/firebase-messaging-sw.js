self.addEventListener("push", (event) => {
  const payload = event.data ? event.data.json() : {};
  const title = payload.title || "Match Update";
  const body = payload.body || "Score update available.";
  const tag = payload.tag || "scoreboard-match";

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      tag,
      renotify: true,
      requireInteraction: true,
      data: {
        url: payload.url || "/"
      }
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/";

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if ("focus" in client) {
            client.focus();
            return;
          }
        }
        if (self.clients.openWindow) {
          return self.clients.openWindow(targetUrl);
        }
      })
  );
});
