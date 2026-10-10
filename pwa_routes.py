# ═══════════════════════════════════════════════
# FIKIR — PWA (Progressive Web App)
# Blueprint: /
# ═══════════════════════════════════════════════
from flask import Blueprint, Response, send_from_directory, url_for, render_template_string
import os

pwa_bp = Blueprint("pwa", __name__)

MANIFEST = {
  "name": "FIKIR Coffee House",
  "short_name": "FIKIR",
  "description": "FIKIR Coffee House — POS, Kitchen & Management System",
  "start_url": "/staff/login",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#6b3e1e",
  "theme_color": "#6b3e1e",
  "categories": ["business", "food", "productivity"],
  "lang": "am",
  "icons": [
    {"src": "/pwa/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
    {"src": "/pwa/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
  ],
  "shortcuts": [
    {"name": "POS", "url": "/pos/", "description": "Point of Sale"},
    {"name": "Kitchen", "url": "/kitchen/", "description": "Kitchen Display"},
    {"name": "Owner", "url": "/owner/", "description": "Owner Dashboard"}
  ]
}

SERVICE_WORKER = r'''
// FIKIR Coffee House — Service Worker
const CACHE_NAME = 'fikir-v1';
const STATIC_ASSETS = [
  '/staff/login',
  '/pwa/icon-192.png',
  '/pwa/icon-512.png'
];

// Install
self.addEventListener('install', (e) => {
  console.log('[SW] Installing...');
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS).catch(()=>{}))
  );
  self.skipWaiting();
});

// Activate
self.addEventListener('activate', (e) => {
  console.log('[SW] Activating...');
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  return self.clients.claim();
});

// Fetch — network-first for API, cache-first for static
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // Never cache POST/PUT/DELETE or API calls
  if (e.request.method !== 'GET' || url.pathname.startsWith('/staff-admin') ||
      url.pathname.startsWith('/inventory') || url.pathname.startsWith('/reports')) {
    return;
  }
  // Cache-first for icons & manifest
  if (url.pathname.startsWith('/pwa/') || url.pathname === '/manifest.json') {
    e.respondWith(
      caches.match(e.request).then(cached => cached || fetch(e.request).then(res => {
        const clone = res.clone();
        caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
        return res;
      }))
    );
    return;
  }
  // Network-first for pages
  e.respondWith(
    fetch(e.request).then(res => {
      const clone = res.clone();
      if (res.status === 200) caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
      return res;
    }).catch(() => caches.match(e.request))
  );
});

// Message handler
self.addEventListener('message', (e) => {
  if (e.data === 'SKIP_WAITING') self.skipWaiting();
});
'''

# Minimal 1x1 PNG fallback (base64) — will be served if no custom icon
ICON_FALLBACK = bytes.fromhex(
    '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489'
    '0000000d49444154789c6360606060000000050001a5f645400000000049454e44ae426082'
)

@pwa_bp.route("/manifest.json")
def manifest():
    import json
    return Response(
        json.dumps(MANIFEST, ensure_ascii=False),
        mimetype="application/manifest+json",
        headers={"Cache-Control": "public, max-age=86400"}
    )

@pwa_bp.route("/sw.js")
def service_worker():
    return Response(
        SERVICE_WORKER,
        mimetype="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"}
    )

@pwa_bp.route("/pwa/icon-192.png")
def icon_192():
    # Serve existing logo if available
    for candidate in ["static/pwa/icon-192.png", "static/logo.png", "static/pwa/icon.png"]:
        if os.path.exists(candidate):
            return send_from_directory(os.path.dirname(candidate), os.path.basename(candidate), mimetype="image/png")
    return Response(ICON_FALLBACK, mimetype="image/png")

@pwa_bp.route("/pwa/icon-512.png")
def icon_512():
    for candidate in ["static/pwa/icon-512.png", "static/logo.png", "static/pwa/icon.png"]:
        if os.path.exists(candidate):
            return send_from_directory(os.path.dirname(candidate), os.path.basename(candidate), mimetype="image/png")
    return Response(ICON_FALLBACK, mimetype="image/png")

@pwa_bp.route("/pwa/status")
def status():
    return {"pwa": True, "manifest": "/manifest.json", "sw": "/sw.js"}
