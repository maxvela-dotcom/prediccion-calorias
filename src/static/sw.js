/*
 * Service Worker de la app compartida «Asistencias Escuela de Fútbol» (Willys_IA).
 * Guarda solo archivos estáticos (íconos, scripts, manifiesto).
 * NO cachea páginas ni APIs: con login y datos compartidos, cada apertura debe
 * ir al servidor para validar la sesión y leer la SQLite única.
 */
const CACHE_NAME = "escuela-ef-compartida-v2";

const ARCHIVOS_APP = [
  "/static/escuela_local.js",
  "/static/vendor/qrcode.js",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png"
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ARCHIVOS_APP))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((nombres) => Promise.all(
        nombres.filter((nombre) => nombre !== CACHE_NAME).map((nombre) => caches.delete(nombre))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (evento) => {
  const peticion = evento.request;
  const url = new URL(peticion.url);

  if (peticion.method !== "GET" || url.origin !== self.location.origin) return;

  // Navegaciones y APIs siempre al servidor (sesión + datos compartidos).
  if (peticion.mode === "navigate" || url.pathname.startsWith("/api/")) return;

  const esArchivoApp =
    url.pathname.startsWith("/static/") ||
    url.pathname.startsWith("/icons/") ||
    url.pathname === "/manifest.webmanifest";

  if (!esArchivoApp) return;

  evento.respondWith(
    caches.match(peticion).then((respuesta) => respuesta || fetch(peticion).then((network) => {
      if (network && network.ok) {
        const copia = network.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(peticion, copia));
      }
      return network;
    }))
  );
});
