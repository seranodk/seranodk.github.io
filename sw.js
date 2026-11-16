/* Spillehal: gør det muligt at spille alle spil uden net.
   Siden selv lægger filerne i cachen "spillehal-offline", når man trykker "Hent alle spil".
   Her hentes altid fra nettet først; uden net bruges den gemte kopi. */
const CACHE = 'spillehal-offline';
const UDEN_OM = /goatcounter\.com|gc\.zgo\.at|api\.github\.com|raw\.githubusercontent\.com|firebasedatabase|firebaseio/;

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

function medTidsgraense(p, ms) {
  return new Promise((ok, fejl) => {
    const t = setTimeout(() => fejl(new Error('tidsgrænse')), ms);
    p.then(r => { clearTimeout(t); ok(r); }, e => { clearTimeout(t); fejl(e); });
  });
}

async function fraCache(req) {
  const c = await caches.open(CACHE);
  let r = await c.match(req, { ignoreSearch: true, ignoreVary: true });
  if (r) return r;
  const u = new URL(req.url);
  if (req.mode === 'navigate') {
    if (u.pathname.endsWith('/')) r = await c.match(u.origin + u.pathname + 'index.html', { ignoreSearch: true });
    else r = await c.match(u.origin + u.pathname + '/', { ignoreSearch: true });
    if (!r) r = await c.match(u.origin + '/', { ignoreSearch: true });
  }
  return r || Response.error();
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || UDEN_OM.test(req.url)) return;
  e.respondWith((async () => {
    try {
      const net = fetch(req);
      const res = req.mode === 'navigate' ? await medTidsgraense(net, 6000) : await net;
      // hold gemte filer friske, når der er net
      if (res.ok && (res.type === 'basic' || res.type === 'cors')) {
        const c = await caches.open(CACHE);
        const key = req.url.split('?')[0].split('#')[0];
        if (await c.match(key, { ignoreSearch: true })) c.put(key, res.clone()).catch(() => {});
      }
      return res;
    } catch (err) {
      return fraCache(req);
    }
  })());
});
