// Offline support: the page shell is cached; stories.json is always fetched fresh
// when online, with the last copy kept for offline reading.
const CACHE = "kgn-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/icon.svg", "icons/icon-192.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  // Network first for the stories and the page, so updates show up straight away.
  if (url.pathname.endsWith("stories.json") || e.request.mode === "navigate") {
    const key = url.pathname.endsWith("stories.json") ? "stories.json" : e.request;
    e.respondWith(
      fetch(e.request)
        .then(res => { const copy = res.clone(); caches.open(CACHE).then(c => c.put(key, copy)); return res; })
        .catch(() => caches.match(key).then(r => r || caches.match("index.html")))
    );
    return;
  }

  // Cache first for everything else (icons, manifest).
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
