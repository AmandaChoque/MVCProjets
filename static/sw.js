/**
 * Service Worker — SOBOTEC Offline Checklist Support
 * Permite marcar tareas sin conexión; se sincronizan al reconectar.
 */

const CACHE_NAME = 'sobotec-v2';

// Rutas que se cachean para uso offline básico
const URLS_TO_CACHE = [
  '/mi-trabajo/',
  '/proyectos/',
];

// ── Instalación: pre-caché de rutas clave ──────────────────────────────────
self.addEventListener('install', function(event) {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(URLS_TO_CACHE).catch(function() {
        // Silenciar errores si las rutas no están disponibles en install
      });
    })
  );
});

// ── Activación: limpiar caches viejos ─────────────────────────────────────
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE_NAME; })
            .map(function(k) { return caches.delete(k); })
      );
    }).then(function() { return self.clients.claim(); })
  );
});

// ── Fetch: Network-first con fallback a cache ─────────────────────────────
self.addEventListener('fetch', function(event) {
  // Solo interceptar GETs del mismo origen
  if (event.request.method !== 'GET') return;
  if (!event.request.url.startsWith(self.location.origin)) return;

  event.respondWith(
    fetch(event.request)
      .then(function(response) {
        // Cachear respuestas exitosas de páginas HTML
        if (response && response.status === 200 && response.type === 'basic') {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(event.request, clone);
          });
        }
        return response;
      })
      .catch(function() {
        // Sin red: servir desde cache
        return caches.match(event.request).then(function(cached) {
          if (cached) return cached;
          // Fallback genérico para navegación
          if (event.request.mode === 'navigate') {
            return caches.match('/mi-trabajo/');
          }
        });
      })
  );
});

// ── Background Sync: procesar cola offline al reconectar ──────────────────
self.addEventListener('sync', function(event) {
  if (event.tag === 'sync-tareas') {
    event.waitUntil(syncOfflineQueue());
  }
});

async function syncOfflineQueue() {
  const clients = await self.clients.matchAll();
  // Notificar al cliente que procese su cola localStorage
  clients.forEach(function(client) {
    client.postMessage({ type: 'SYNC_OFFLINE_QUEUE' });
  });
}
