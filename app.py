from flask import Flask, request, redirect, url_for, session, render_template_string, jsonify
import os
import requests
import sqlite3
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
def get_supabase_headers():
    return {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
KITCHEN_PASSWORD = os.getenv("KITCHEN_PASSWORD", "kitchen2026")
WAITER_PASSWORD = os.getenv("WAITER_PASSWORD", "waiter2026")

TELEBIRR_NUMBER = os.getenv("TELEBIRR_NUMBER", "0912345678")
TELEBIRR_NAME = os.getenv("TELEBIRR_NAME", "FIKIR Coffee House")
CBE_ACCOUNT = os.getenv("CBE_ACCOUNT", "1000123456789")
CBE_NAME = os.getenv("CBE_NAME", "FIKIR Coffee House")

from datetime import datetime

app = Flask(__name__)
app.secret_key = "fikir-coffee-house-secret-key-change-later"

DB = "coffee.db"

PRODUCTS = [
    {"id": 1, "name": "Espresso", "desc": "Strong and rich coffee", "price": 40, "icon": "☕"},
    {"id": 2, "name": "Cappuccino", "desc": "Smooth and creamy", "price": 50, "icon": "☕"},
    {"id": 3, "name": "Latte", "desc": "Rich milk coffee", "price": 55, "icon": "🥛"},
    {"id": 4, "name": "Americano", "desc": "Classic black coffee", "price": 45, "icon": "☕"},
    {"id": 5, "name": "Mocha", "desc": "Chocolate & coffee blend", "price": 60, "icon": "🍫"},
    {"id": 6, "name": "Caramel Macchiato", "desc": "Sweet and rich", "price": 60, "icon": "🍮"},
    {"id": 7, "name": "Cold Coffee", "desc": "Refreshingly cold", "price": 55, "icon": "🧊"},
    {"id": 8, "name": "Hot Chocolate", "desc": "Rich chocolate drink", "price": 50, "icon": "🍫"},
]

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fikir_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            table_no TEXT NOT NULL,
            items TEXT NOT NULL,
            total INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'NEW',
            created_at TEXT NOT NULL,
            payment_method TEXT,
            payment_ref TEXT,
            payment_status TEXT DEFAULT 'UNPAID'
        )
    """)
    conn.commit()
    conn.close()

init_db()

def init_products_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fikir_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price INTEGER NOT NULL,
            icon TEXT NOT NULL DEFAULT '☕'
        )
    """)

    count = conn.execute(
        "SELECT COUNT(*) FROM fikir_products"
    ).fetchone()[0]

    if count == 0:
        for product in PRODUCTS:
            conn.execute(
                """
                INSERT INTO fikir_products
                (id, name, description, price, icon)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    product["id"],
                    product["name"],
                    product["desc"],
                    product["price"],
                    product["icon"]
                )
            )

    conn.commit()
    conn.close()

def send_telegram(message):
    """Send notification to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=5
        )
    except Exception as e:
        print(f"Telegram error: {e}")

# ═══════ AUTO-INIT DATABASE ON STARTUP ═══════
# _init_database removed

# _migrate_db removed

@app.route("/assets/<path:filename>")
def serve_asset(filename):
    from flask import send_from_directory
    return send_from_directory("assets", filename)

def get_products():
    # Supabase is the primary product database on Render
    if False:  # Supabase disabled
        try:
            r = requests.get(
                SUPABASE_URL.rstrip("/") + "/rest/v1/fikir_products",
                headers={
                    **get_supabase_headers(),
                    "Content-Type": "application/json"
                },
                params={
                    "select": "id,name,description,price,icon,stock,low_stock",
                    "order": "id.asc"
                },
                timeout=10
            )

            if r.ok:
                rows = r.json()
                return [
                    {
                        "id": x["id"],
                        "name": x["name"],
                        "desc": x["description"],
                        "price": x["price"],
                        "icon": x.get("icon") or "☕",
                        "stock": x.get("stock", 0),
                        "low_stock": x.get("low_stock", 5)
                    }
                    for x in rows
                ]

            print("Supabase products GET failed:", r.status_code, r.text)

        except Exception as e:
            print("Supabase products GET error:", e)

    # Local SQLite fallback
    conn = db()
    rows = conn.execute("""
        SELECT id, name, description, price, icon, stock, low_stock
        FROM fikir_products
        ORDER BY id
    """).fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "desc": r["description"],
            "price": r["price"],
            "icon": r["icon"],
            "stock": r["stock"],
            "low_stock": r["low_stock"]
        }
        for r in rows
    ]

init_products_db()

CSS = r"""
:root{
  --bg:#070707; --panel:#11100e; --panel2:#171411; --gold:#d99a32;
  --gold2:#f0b34e; --cream:#f5ead7; --muted:#aaa39a; --line:#4b3218;
  --green:#6f8f58; --danger:#a84b3f;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;background:
  radial-gradient(circle at 85% 10%,rgba(217,154,50,.12),transparent 28%),
  radial-gradient(circle at 10% 40%,rgba(100,65,25,.10),transparent 25%),var(--bg);
  color:var(--cream);font-family:Arial,Helvetica,sans-serif;
}
a{text-decoration:none;color:inherit}
button,input,select{font:inherit}
.nav{
  position:sticky;top:0;z-index:20;background:rgba(7,7,7,.94);
  border-bottom:1px solid #3a2917;backdrop-filter:blur(10px);
}
.navin{max-width:1250px;margin:auto;padding:14px 22px;display:flex;align-items:center;gap:22px}
.brand{display:flex;align-items:center;gap:10px;min-width:230px}
.logo{
  width:54px;height:54px;border:1px solid var(--gold);border-radius:50%;
  display:grid;place-items:center;font-size:29px;background:#0c0a08;
  box-shadow:0 0 20px rgba(217,154,50,.12);
}
.brand b{font-family:Georgia,serif;font-size:29px;color:var(--gold2);letter-spacing:1px}
.brand small{display:block;color:#c9bba7;font-size:12px;letter-spacing:2px}
.links{display:flex;gap:7px;align-items:center;flex:1;justify-content:center}
.links a{padding:11px 16px;border-radius:10px;color:#eee}
.links a:hover,.links .active{background:#3a2612;color:#f2b44f}
.cartbtn{border:1px solid var(--gold);padding:10px 14px;border-radius:12px;position:relative}
.badge{position:absolute;right:-7px;top:-8px;background:var(--gold2);color:#1b1005;border-radius:20px;padding:2px 7px;font-size:11px;font-weight:bold}
.wrap{max-width:1250px;margin:auto;padding:22px}
.hero{
  min-height:320px;border:1px solid #70491d;border-radius:24px;overflow:hidden;
  background:
  linear-gradient(90deg,rgba(5,5,5,.97) 0%,rgba(8,7,6,.82) 50%,rgba(8,7,6,.25) 100%),
  radial-gradient(circle at 82% 45%,#7b481d 0,transparent 28%),
  linear-gradient(135deg,#18120c,#080808);
  display:flex;align-items:center;padding:45px;
}
.hero h1{font:700 clamp(42px,7vw,78px)/.95 Georgia,serif;margin:7px 0;color:#f5ead7}
.hero h1 span{color:var(--gold2)}
.script{font:italic 27px Georgia,serif;color:var(--gold2)}
.tag{font-size:18px;color:#ddd;margin:18px 0 28px}
.btn{
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  border:0;border-radius:12px;padding:12px 18px;background:linear-gradient(135deg,#d9952e,#f1b34e);
  color:#1b1005;font-weight:800;cursor:pointer;box-shadow:0 7px 22px rgba(217,154,50,.14)
}
.btn.secondary{background:#21170d;color:#efb14b;border:1px solid #70491d;box-shadow:none}
.section{margin-top:34px}
.title{display:flex;align-items:end;justify-content:space-between;gap:15px;margin-bottom:18px}
.title h2{font:700 34px Georgia,serif;margin:0}
.title p{margin:6px 0;color:var(--muted)}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 315px;gap:22px}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px}
.card{
  background:linear-gradient(180deg,#15120f,#0d0d0d);border:1px solid #4b3218;
  border-radius:18px;overflow:hidden;box-shadow:0 8px 25px rgba(0,0,0,.25)
}
.productpic{height:155px;display:grid;place-items:center;background:
  radial-gradient(circle,#5b3417 0,transparent 40%),linear-gradient(135deg,#17120d,#090909);
  font-size:72px}
.pad{padding:15px}
.card h3{margin:0 0 7px;font-size:19px}
.desc{color:#aaa;font-size:13px;min-height:32px}
.price{color:#f0b34e;font-weight:800;font-size:18px;margin:13px 0}
.row{display:flex;justify-content:space-between;align-items:center;gap:8px}
.add{padding:9px 12px;border-radius:9px;border:1px solid #8a5a20;background:#2b1b0b;color:#f1b34e;font-weight:bold;cursor:pointer}
.side{display:flex;flex-direction:column;gap:15px}
.side .card{padding:18px}
.side h3{margin:0 0 14px;color:#f0b34e;font:700 21px Georgia,serif}
.empty{text-align:center;color:#aaa;padding:22px 5px}
.cartitem{border-top:1px solid #332619;padding:12px 0}
.qty{display:flex;align-items:center;gap:8px}
.qty a{width:28px;height:28px;border:1px solid #69471f;border-radius:8px;display:grid;place-items:center;color:#f0b34e}
.total{font-size:21px;font-weight:800;color:#f0b34e;border-top:1px solid #4b3218;padding-top:14px;margin-top:10px}
.formbox{max-width:650px;margin:35px auto}
label{display:block;color:#d8c9b5;margin:12px 0 6px}
input,select{
  width:100%;padding:13px;border-radius:10px;border:1px solid #49331e;background:#0e0d0c;color:#fff;outline:none
}
.notice{padding:13px 15px;border:1px solid #70491d;background:#21170d;border-radius:12px;margin:15px 0}
.order{padding:17px;border:1px solid #4b3218;border-radius:16px;background:#11100e;margin-bottom:14px}
.status{display:inline-block;padding:6px 10px;border-radius:20px;background:#3a2612;color:#f0b34e;font-size:12px;font-weight:bold}
.kitchen-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}
.kitchen-card{padding:18px;border:1px solid #4b3218;border-radius:16px;background:#11100e}
.kitchen-card h3{margin-top:0;color:#f0b34e}
footer{margin-top:50px;border-top:1px solid #3a2917;padding:25px;text-align:center;color:#9f978d}
@media(max-width:1050px){.grid{grid-template-columns:repeat(3,1fr)}}
@media(max-width:800px){
  .navin{padding:10px 14px}.brand{min-width:auto}.brand b{font-size:22px}.brand small{font-size:9px}
  .links{display:none;position:absolute;top:70px;left:14px;right:14px;flex-direction:column;background:#21150c;padding:10px;border-radius:14px;z-index:9999;box-shadow:0 10px 30px rgba(0,0,0,.35)}
  .links.mobile-open{display:flex}
  .links a{width:100%;box-sizing:border-box;text-align:left}
  .mobile-menu-btn{display:block;background:#3a2612;color:#f2b44f;border:1px solid #5a3b20;border-radius:10px;padding:10px 13px;font-size:20px;cursor:pointer}
  .wrap{padding:14px}.hero{padding:30px 22px;min-height:300px}
  .layout{grid-template-columns:1fr}.grid{grid-template-columns:repeat(2,1fr)}.kitchen-grid{grid-template-columns:1fr 1fr}
}
@media(max-width:500px){
  .brand img{width:48px;height:48px;border-radius:50%;object-fit:cover}.hero h1{font-size:45px}.script{font-size:21px}
  .grid{grid-template-columns:1fr}.kitchen-grid{grid-template-columns:1fr}.productpic{height:145px}
}
"""

BASE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" type="image/png" href="/static/favicon.png">
<link rel="apple-touch-icon" href="/static/favicon.png">
<title>FIKIR Coffee House</title>
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#d4af37">
<meta name="apple-mobile-web-app-capable" content="yes">

<meta name="description" content="FIKIR Coffee House - Great Coffee, Good Mood, Better Together. Order online!">
<meta name="theme-color" content="#d4af37">
<meta property="og:title" content="FIKIR Coffee House">
<meta property="og:description" content="Order your favorite Ethiopian coffee online">
{{ title or "FIKIR Coffee House" }}</title>
<style>""" + CSS + r"""
/* ═══════ ANIMATIONS BY FIKIR ═══════ */
@keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
@keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.05); } }
@keyframes gradient { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
@keyframes float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes ripple { to { transform: scale(4); opacity: 0; } }
@keyframes slideIn { from { transform: translateX(-30px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

body { animation: fadeIn .6s ease-out; }
.hero { background: linear-gradient(-45deg,#0a0805,#2a2018,#0a0805,#3a2a18); background-size: 400% 400%; animation: gradient 15s ease infinite; }
.hero h1 { animation: fadeIn 1s ease-out .2s backwards; }
.hero p { animation: fadeIn 1s ease-out .4s backwards; }

.card, .product { animation: fadeIn .5s ease-out backwards; transition: all .4s cubic-bezier(.4,0,.2,1); }
.card:hover, .product:hover { transform: translateY(-8px) scale(1.02); box-shadow: 0 20px 40px rgba(212,175,55,.15), 0 0 0 1px rgba(212,175,55,.3); }

.productpic { transition: transform .5s cubic-bezier(.4,0,.2,1); animation: float 3s ease-in-out infinite; }

.add { position: relative; overflow: hidden; transition: all .3s cubic-bezier(.4,0,.2,1); animation: pulse 3s ease-in-out infinite; }
.add:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(212,175,55,.4); animation: none; }

.btn { position: relative; overflow: hidden; transition: all .3s cubic-bezier(.4,0,.2,1); }
.btn:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(212,175,55,.4); }

.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(212,175,55,.3); border-top-color: #d4af37; border-radius: 50%; animation: spin .8s linear infinite; vertical-align: middle; }

.cartitem { animation: slideIn .4s ease-out backwards; }
.notice { animation: slideIn .5s ease-out; }

</style>
</head>
<body>
<header class="nav"><div class="navin">
<a class="brand" href="/">
  <img src="/assets/logo.png" alt="FIKIR" style="width:48px;height:48px;border-radius:50%;object-fit:cover;box-shadow:0 0 15px rgba(212,175,55,.5);border:2px solid rgba(212,175,55,.3)">
  <div><b>FIKIR</b><small>COFFEE HOUSE</small></div>
</a>
<button class="mobile-menu-btn" onclick="toggleMobileMenu()">☰</button>
<nav class="links">
  <a href="/" class="{{ 'active' if page=='home' else '' }}">⌂ Home</a>
  <a href="/#menu">☕ Menu</a>
  <a href="/cart">🛒 Cart</a>
  <a href="/kitchen">👨‍🍳 Kitchen</a>
  <a href="/waiter/login">🍽️ Waiter</a>
  <a href="/admin/login">🔐 Admin</a>
</nav>
<a class="cartbtn" href="/cart">🛒 <span class="badge">{{ cart_count }}</span></a>
</div></header>
<div class="wrap">
{{ body|safe }}
</div>
<footer>☕ <b>FIKIR Coffee House</b> &nbsp;—&nbsp; Taste the Difference</footer>
<script>
function toggleMobileMenu(){
  const menu = document.querySelector('.links');
  menu.classList.toggle('mobile-open');
}


// ═══════ ADMIN AUTO-REFRESH + SOUND ═══════
if (window.location.pathname.startsWith('/admin')) {
    var lastLatest = null;
    function playDing() {
        try {
            var ctx = new (window.AudioContext || window.webkitAudioContext)();
            [880, 1100].forEach(function(freq, i) {
                var osc = ctx.createOscillator();
                var g = ctx.createGain();
                osc.connect(g); g.connect(ctx.destination);
                osc.frequency.value = freq;
                osc.type = 'sine';
                var t = ctx.currentTime + i * 0.15;
                g.gain.setValueAtTime(0, t);
                g.gain.linearRampToValueAtTime(0.3, t + 0.02);
                g.gain.exponentialRampToValueAtTime(0.001, t + 0.4);
                osc.start(t); osc.stop(t + 0.4);
            });
        } catch(e) {}
    }
    setInterval(function() {
        fetch('/admin/latest-order-id').then(function(r) { return r.json(); }).then(function(d) {
            if (lastLatest === null) { lastLatest = d.id; return; }
            if (d.id > lastLatest) {
                lastLatest = d.id;
                playDing();
                setTimeout(function() { location.reload(); }, 800);
            }
        }).catch(function(){});
    }, 20000);
}

// ═══════ ORDER STATUS CLICK ═══════
(function() {
    if (!window.location.pathname.startsWith('/admin') && !window.location.pathname.startsWith('/kitchen')) return;
    
    var STATUS_FLOW = ['NEW', 'PREPARING', 'READY', 'COMPLETED'];
    var STATUS_COLORS = {
        'NEW': '#5b9bd5',
        'PREPARING': '#f0b34e',
        'READY': '#4caf50',
        'COMPLETED': '#888',
        'CANCELLED': '#e74c3c'
    };
    
    function styleStatus(el, status) {
        var c = STATUS_COLORS[status] || '#f0b34e';
        el.style.background = c;
        el.style.color = '#000';
        el.style.padding = '4px 10px';
        el.style.borderRadius = '12px';
        el.style.fontWeight = 'bold';
        el.style.cursor = 'pointer';
        el.style.display = 'inline-block';
        el.title = 'Click to advance status';
    }
    
    function attachHandlers() {
        document.querySelectorAll('.status').forEach(function(el) {
            if (el.dataset.statusAttached) return;
            el.dataset.statusAttached = '1';
            var status = el.textContent.trim().toUpperCase();
            styleStatus(el, status);
            
            el.addEventListener('click', function(e) {
                e.preventDefault();
                var current = el.textContent.trim().toUpperCase();
                var idx = STATUS_FLOW.indexOf(current);
                if (idx === -1 || idx >= STATUS_FLOW.length - 1) return;
                var next = STATUS_FLOW[idx + 1];
                
                var row = el.closest('[data-order-id]') || el.closest('tr') || el.parentElement;
                var orderId = row ? row.dataset.orderId : null;
                if (!orderId) {
                    var idMatch = document.body.innerHTML.match(/Order #(\d+)/);
                    if (!idMatch) return;
                    orderId = idMatch[1];
                }
                
                el.textContent = '...';
                var fd = new FormData();
                fd.append('order_id', orderId);
                fd.append('status', next);
                
                fetch('/admin/update-status', { method: 'POST', body: fd })
                    .then(function(r) { return r.json(); })
                    .then(function(d) {
                        if (d.ok) {
                            el.textContent = next;
                            styleStatus(el, next);
                        } else {
                            el.textContent = current;
                        }
                    })
                    .catch(function() { el.textContent = current; });
            });
        });
    }
    
    attachHandlers();
    setInterval(attachHandlers, 3000);
})();

// ═══════ UI INTERACTIONS BY FIKIR (FIXED) ═══════
document.addEventListener('click', function(e) {
    var btn = e.target.closest('.add, .btn');
    if (!btn) return;
    var rect = btn.getBoundingClientRect();
    var size = Math.max(rect.width, rect.height);
    var ripple = document.createElement('span');
    var x = e.clientX - rect.left - size / 2;
    var y = e.clientY - rect.top - size / 2;
    ripple.style.cssText = 'position:absolute;width:' + size + 'px;height:' + size + 'px;border-radius:50%;background:rgba(255,255,255,.5);left:' + x + 'px;top:' + y + 'px;pointer-events:none;transform:scale(0);animation:ripple .6s ease-out;';
    btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.appendChild(ripple);
    setTimeout(function() { ripple.remove(); }, 600);
});

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(function(link) {
    link.addEventListener('click', function(e) {
        var target = document.querySelector(this.getAttribute('href'));
        if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
});

// ═══════ CART AJAX ═══════
function updateQty(id, delta) {
    var fd = new FormData();
    fd.append('product_id', id);
    fd.append('delta', delta);
    fetch('/cart/update', { method: 'POST', body: fd })
        .then(function(r) { return r.json(); })
        .then(function(d) { if (d.ok) location.reload(); })
        .catch(function() { location.reload(); });
}
function removeItem(id) {
    if (!confirm('Remove this item from cart?')) return;
    var fd = new FormData();
    fd.append('product_id', id);
    fetch('/cart/remove', { method: 'POST', body: fd })
        .then(function(r) { return r.json(); })
        .then(function(d) { if (d.ok) location.reload(); })
        .catch(function() { location.reload(); });
}

if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/sw.js').then(function(r) {
            console.log('SW:', r.scope);
        }).catch(function(e) { console.log('SW fail:', e); });
    });
}

</script>
</body></html>
"""

def cart_data():
    products = get_products()
    raw = session.get("cart", {})
    items, total, count = [], 0, 0

    for pid, qty in raw.items():
        p = next((x for x in products if x["id"] == int(pid)), None)

        if not p:
            continue

        subtotal = p["price"] * int(qty)
        items.append({**p, "qty": int(qty), "subtotal": subtotal})
        total += subtotal
        count += int(qty)

    return items, total, count

def page(body, page_name="home", title="FIKIR Coffee House"):
    _, _, count = cart_data()
    return render_template_string(BASE, body=body, page=page_name, title=title, cart_count=count)

@app.route("/")
def home():
    body = render_template_string(r"""
<section class="hero">
  <div>
    <div class="script">Welcome to</div>
    <h1><span>FIKIR</span> Coffee House</h1>
    <div class="tag">Great Coffee • Good Mood • Better Together</div>
    <a class="btn" href="#menu">☕ Order Now →</a>
  </div>
</section>

<section class="section" id="menu">
  <div class="title">
    <div><h2>☕ Our Coffee Menu</h2><p>Choose your favorite coffee and enjoy the best taste.</p></div>
  </div>
  <div class="layout">
    <div class="grid">
    {% for p in products %}
      <div class="card">
        <div class="productpic">{{ p.icon }}</div>
        <div class="pad">
          <h3>{{ p.name }}</h3><div class="desc">{{ p.desc }}</div>
          <div class="row"><div class="price">ETB {{ p.price }}</div>
          <form method="post" action="/add"><input type="hidden" name="product_id" value="{{ p.id }}"><button class="add">+ Add to Cart</button></form></div>
        </div>
      </div>
    {% endfor %}
    </div>
    <aside class="side">
      <div class="card">
        <h3>🛒 Your Cart</h3>
        {% if items %}
          {% for x in items %}
          <div class="cartitem"><div class="row"><b>{{ x.name }}</b><span>ETB {{ x.subtotal }}</span></div><small>{{ x.qty }} × ETB {{ x.price }}</small></div>
          {% endfor %}
          <div class="total">Total: ETB {{ total }}</div>
          <br><a class="btn" style="width:100%" href="/cart">View Cart →</a>
        {% else %}
          <div class="empty">🛒<br><br>Your cart is empty<br><small>Add your favorite items to get started.</small></div>
        {% endif %}
      </div>
      <div class="card">
        <h3>🔥 Popular Today</h3>
        <p>☕ Cappuccino <small>— smooth & creamy</small></p>
        <p>🥛 Latte <small>— rich milk coffee</small></p>
        <p>🍫 Mocha <small>— chocolate blend</small></p>
      </div>
      <div class="card">
        <h3>👨‍🍳 Kitchen Dashboard</h3>
        <p style="color:#aaa">New customer orders appear here.</p>
        <a class="btn secondary" href="/kitchen">Open Kitchen View →</a>
      </div>
    </aside>
  </div>
</section>
""", products=get_products(), items=cart_data()[0], total=cart_data()[1])
    return page(body)

@app.post("/add")
def add():
    pid = request.form.get("product_id", type=int)

    conn = db()
    product = conn.execute(
        "SELECT id, name, stock FROM fikir_products WHERE id=?",
        (pid,)
    ).fetchone()
    conn.close()

    if not product:
        return "Invalid product", 400

    cart = session.get("cart", {})
    key = str(pid)
    current_qty = int(cart.get(key, 0))
    stock = int(product["stock"])

    if stock <= 0:
        return f"{product['name']} is out of stock", 400

    if current_qty >= stock:
        return f"Only {stock} of {product['name']} available", 400

    cart[key] = current_qty + 1
    session["cart"] = cart

    return redirect(request.referrer or url_for("home"))

@app.post("/remove")
def remove():
    pid = request.form.get("product_id", type=int)
    cart = session.get("cart", {})
    key = str(pid)
    if key in cart:
        cart[key] -= 1
        if cart[key] <= 0: del cart[key]
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.post("/clear-cart")
def clear_cart():
    session["cart"] = {}
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    items, total, _ = cart_data()
    body = render_template_string(r"""
<div class="formbox">
  <div class="title"><div><h2>🛒 Your Cart</h2><p>Review your order before sending it to the kitchen.</p></div></div>
  {% if items %}
    {% for x in items %}
    <div class="order">
      <div class="row"><div><h3>{{ x.icon }} {{ x.name }}</h3><small>{{ x.qty }} × ETB {{ x.price }}</small></div><b>ETB {{ x.subtotal }}</b></div>
      <div class="qty" style="margin-top:10px">
        <form method="post" action="/remove"><input type="hidden" name="product_id" value="{{ x.id }}"><button class="add">−</button></form>
        <span>{{ x.qty }}</span>
        <form method="post" action="/add"><input type="hidden" name="product_id" value="{{ x.id }}"><button class="add">+</button></form>
      </div>
    </div>
    {% endfor %}
    <div class="total">Total: ETB {{ total }}</div>
    <br>
    <a class="btn secondary" href="/">← Continue Shopping</a>
    <form method="post" action="/clear-cart" style="display:inline"><button class="btn secondary">Clear Cart</button></form>
    <a class="btn" href="/checkout">Proceed to Order →</a>
  {% else %}
    <div class="card" style="padding:35px;text-align:center">🛒<h2>Your cart is empty</h2><a class="btn" href="/">Back to Menu</a></div>
  {% endif %}
</div>
""", items=items, total=total)
    return page(body, "cart")

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total, _ = cart_data()
    if not items:
        return redirect(url_for("home"))
    if request.method == "POST":
        customer = request.form.get("customer", "").strip()
        table_no = request.form.get("table_no", "").strip()
        if not customer or not table_no:
            body = render_template_string('<div class="notice">Please enter customer name and table number.</div>') + checkout_form(items,total)
            return page(body, "cart")
        item_text = ", ".join(f'{x["name"]} × {x["qty"]}' for x in items)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check stock before creating the order
        conn = db()

        for x in items:
            product = conn.execute(
                "SELECT name, stock FROM fikir_products WHERE id=?",
                (x["id"],)
            ).fetchone()

            if not product or int(product["stock"]) < int(x["qty"]):
                conn.close()
                return f"Not enough stock for {x['name']}", 400

        # Deduct stock
        for x in items:
            conn.execute(
                "UPDATE fikir_products SET stock = stock - ? WHERE id=?",
                (x["qty"], x["id"])
            )

        # Save locally for the existing Kitchen Dashboard
        cur = conn.execute(
            "INSERT INTO fikir_orders(customer,table_no,items,total,status,created_at) VALUES(?,?,?,?,?,?)",
            (customer, table_no, item_text, total, "NEW", created_at)
        )
        order_id = cur.lastrowid

        # Commit order + stock deduction together
        conn.commit()
        conn.close()

        send_telegram(f"🛒 New Order #{order_id} - {customer} - Table {table_no} - ETB {total} - {item_text}\n\n📍 Track: {{ BASE_URL }}/track/{order_id}\n\n📍 Track: http://127.0.0.1:5000/track/{order_id}")
    # Also send the order to Supabase when Render environment variables are available
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                requests.post(
                    SUPABASE_URL.rstrip("/") + "/rest/v1/fikir_orders",
                    headers={
                        **get_supabase_headers(),
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    },
                    json={
                        "customer": customer,
                        "table_no": table_no,
                        "items": item_text,
                        "total": total,
                        "status": "NEW",
                        "created_at": created_at
                    },
                    timeout=10
                )
            except requests.RequestException:
                pass
        session["cart"] = {}
        return redirect(url_for("success", order_id=order_id))
    body = checkout_form(items,total)
    return page(body, "cart")

def checkout_form(items,total):
    return render_template_string(r"""
<div class="formbox">
  <div class="title"><div><h2>📝 Customer Details</h2><p>Your order will be sent directly to the Kitchen Dashboard.</p></div></div>
  <div class="card" style="padding:22px">
    <form method="post">
      <label>Customer Name</label><input name="customer" placeholder="Enter customer name" required>
      <label>Table Number</label><input name="table_no" placeholder="e.g. 1" required>
      <div class="notice">Order total: <b>ETB {{ total }}</b></div>
      <div style="margin-top:15px;padding:15px;background:#0a0805;border:1px solid #2a2018;border-radius:10px">
      <p style="color:#f0b34e;font-size:13px;font-weight:bold;margin:0 0 10px">💳 Payment Method</p>
      <div style="display:flex;flex-direction:column;gap:8px">
        <label style="display:flex;align-items:center;gap:10px;padding:10px;background:#1a1410;border-radius:8px;cursor:pointer">
          <input type="radio" name="payment_method" value="telebirr" checked style="width:auto">
          <span style="color:#fff;font-size:14px">📱 Telebirr</span>
        </label>
        <label style="display:flex;align-items:center;gap:10px;padding:10px;background:#1a1410;border-radius:8px;cursor:pointer">
          <input type="radio" name="payment_method" value="cbebirr" style="width:auto">
          <span style="color:#fff;font-size:14px">🏦 CBE Birr</span>
        </label>
      </div>
      <div id="payment-info" style="margin-top:12px;padding:10px;background:#2a2018;border-radius:8px;font-size:12px;color:#f0b34e">
        <strong>Telebirr:</strong> Send ETB {{ total }} to <b>{{ telebirr_number }}</b><br>
        Name: {{ telebirr_name }}
      </div>
    </div>
    <button class="btn" style="width:100%;margin-top:15px">✅ PLACE ORDER</button>
    </form>
  </div>
</div>
""", items=items, total=total, telebirr_number=TELEBIRR_NUMBER, telebirr_name=TELEBIRR_NAME, cbe_account=CBE_ACCOUNT, cbe_name=CBE_NAME)

@app.route("/success")
def success():
    order_id = request.args.get("order_id", type=int)
    conn=db(); order=conn.execute("SELECT * FROM fikir_orders WHERE id=?", (order_id,)).fetchone(); conn.close()
    if not order: return redirect(url_for("home"))
    body = render_template_string(r"""
<div class="formbox">
  <div class="card" style="padding:30px;text-align:center">
    <div style="font-size:55px">✅</div><h2>Order Sent!</h2>
    <p>Order #: <b>{{ order.id }}</b></p>
    <p>Customer: <b>{{ order.customer }}</b></p>
    <p>Table: <b>{{ order.table_no }}</b></p>
    <p>Total: <b style="color:#f0b34e">ETB {{ order.total }}</b></p>
    <div class="notice">👨‍🍳 Your order has been sent to the kitchen.</div>
    <div style="background:#0a0805;border:2px solid #f0b34e;border-radius:12px;padding:20px;margin-top:20px;text-align:left">
      <h3 style="color:#f0b34e;margin:0 0 12px;font-size:16px">💳 Confirm Payment</h3>
      <p style="color:#aaa;font-size:12px;margin:0 0 12px">After sending payment, enter the transaction ID below:</p>
      <select id="pay-method" style="width:100%;padding:10px;background:#1a1410;border:1px solid #2a2018;color:#f0b34e;border-radius:8px;margin-bottom:10px;font-size:14px;box-sizing:border-box">
        <option value="telebirr">📱 Telebirr</option>
        <option value="cbebirr">🏦 CBE Birr</option>
      </select>
      <input type="text" id="tx-id" placeholder="Transaction ID (e.g. FT23ABC...)" style="width:100%;padding:12px;background:#1a1410;border:1px solid #2a2018;color:#fff;border-radius:8px;font-size:14px;margin-bottom:12px;box-sizing:border-box">
      <button onclick="submitPayment({{ order.id }})" style="width:100%;padding:12px;background:#4caf50;color:#fff;border:0;border-radius:8px;font-weight:bold;font-size:14px;cursor:pointer">✅ Payment Sent</button>
      <p id="pay-status" style="color:#4caf50;font-size:12px;margin:10px 0 0;text-align:center"></p>
    </div>
    
    <script>
    function submitPayment(orderId) {
      var txId = document.getElementById('tx-id').value.trim();
      var method = document.getElementById('pay-method').value;
      var status = document.getElementById('pay-status');
      if (!txId) { status.style.color='#e74c3c'; status.textContent='Please enter Transaction ID'; return; }
      status.style.color='#f0b34e';
      status.textContent='Submitting...';
      var fd = new FormData();
      fd.append('order_id', orderId);
      fd.append('tx_id', txId);
      fd.append('method', method);
      fetch('/payment/confirm', { method: 'POST', body: fd })
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.ok) {
            status.style.color='#4caf50';
            status.textContent='✅ Payment confirmed! Kitchen has been notified.';
          } else {
            status.style.color='#e74c3c';
            status.textContent='Error: ' + (d.error || 'Try again');
          }
        })
        .catch(function() {
          status.style.color='#e74c3c';
          status.textContent='Network error. Try again.';
        });
    }
    </script>
    
    <a class="btn" href="/track/{{ order.id }}" style="background:#4caf50;color:#fff;margin-right:8px;margin-top:15px">📍 Track Order</a>
        <a class="btn" href="/">🔄 New Order</a>
  </div>
</div>
""", order=order)
    return page(body)



@app.route("/kitchen/login", methods=["GET", "POST"])
def kitchen_login():
    error = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == KITCHEN_PASSWORD:
            session["kitchen_logged_in"] = True
            return redirect(url_for("kitchen"))
        error = '<div style="background:#3a1a1a;border:1px solid #e74c3c;color:#ff9999;padding:10px;border-radius:8px;margin-bottom:15px;font-size:13px">Incorrect password</div>'
    
    body = '<div style="min-height:70vh;display:flex;align-items:center;justify-content:center;padding:20px">'
    body += '<div style="padding:35px;max-width:420px;width:100%;background:linear-gradient(135deg,#1a1410,#0a0805);border:1px solid #d4af37;border-radius:20px;box-shadow:0 20px 60px rgba(212,175,55,.2)">'
    body += '<div style="text-align:center;margin-bottom:25px">'
    body += '<div style="font-size:64px">CHEF</div>'
    body += '<h2 style="color:#f0b34e;margin:10px 0 5px;font-size:24px">Kitchen Login</h2>'
    body += '<p style="color:#888;font-size:12px;letter-spacing:2px;margin:0">FIKIR COFFEE HOUSE</p>'
    body += '</div>'
    body += error
    body += '<form method="post">'
    body += '<label style="display:block;color:#aaa;font-size:13px;margin-bottom:6px">Password</label>'
    body += '<input type="password" name="password" required autofocus placeholder="Enter password" style="width:100%;padding:12px;background:#0a0805;border:1px solid #2a2018;color:#fff;border-radius:10px;font-size:15px;margin-bottom:18px;box-sizing:border-box">'
    body += '<button type="submit" class="btn" style="width:100%;padding:14px;font-size:15px;font-weight:bold">Login</button>'
    body += '</form>'
    body += '<p style="text-align:center;color:#555;font-size:11px;margin-top:20px">For Kitchen Staff Only</p>'
    body += '</div></div>'
    
    return render_template_string(BASE, body=body, page="kitchen_login", title="Kitchen Login", cart_count=cart_data()[0])


@app.route("/kitchen/logout")
def kitchen_logout():
    session.pop("kitchen_logged_in", None)
    return redirect(url_for("kitchen_login"))



def kitchen_logout():
    session.pop("kitchen_logged_in", None)
    return redirect(url_for("kitchen_login"))


@app.route("/kitchen")
def kitchen():
    if not session.get("kitchen_logged_in"):
        return redirect(url_for("kitchen_login"))
    conn=db()
    orders=conn.execute("SELECT * FROM fikir_orders ORDER BY id DESC").fetchall()
    conn.close()
    body = render_template_string(r"""
<div class="title">
  <div><h2>👨‍🍳 Kitchen Dashboard</h2><p>Live customer orders</p></div>
  <a class="btn" href="/kitchen/logout" style="background:#e74c3c;color:#fff;margin-right:8px">🚪 Logout</a>
<a class="btn secondary" href="/">← Customer Menu</a>
</div>
{% if orders %}
<div class="kitchen-grid">
{% for o in orders %}
<div class="kitchen-card">
  <div class="row"><h3>Order #{{ o.id }}</h3><span class="status">{{ o.status }}</span>
    <button onclick="printReceipt({{ o.id }}, '{{ o.customer }}', '{{ o.table_no }}', '{{ o.items|replace("'", "\\'") }}', {{ o.total }}, '{{ o.created_at }}')" style="background:#f0b34e;color:#000;border:0;padding:4px 8px;border-radius:4px;font-size:11px;cursor:pointer;margin-left:8px">🖨️ Print</button>
  </div>
  <p>👤 <b>{{ o.customer }}</b></p><p>🪑 Table: <b>{{ o.table_no }}</b></p>
  <p>🕒 {{ o.created_at }}</p>
  <hr style="border-color:#332619">
  <p>☕ {{ o.items }}</p>
  <p class="price">ETB {{ o.total }}</p>
  <form method="post" action="/kitchen/status">
    <input type="hidden" name="order_id" value="{{ o.id }}">
    <select name="status">
      {% for s in ["NEW","PREPARING","READY","COMPLETED"] %}
      <option value="{{ s }}" {% if o.status==s %}selected{% endif %}>{{ s }}</option>
      {% endfor %}
    </select>
    <br><br><button class="btn" style="width:100%">Update Status</button>
  </form>
</div>
{% endfor %}
</div>
{% else %}
<div class="card" style="padding:35px;text-align:center"><h2>No orders yet ☕</h2><p style="color:#aaa">New customer orders will appear here.</p></div>
{% endif %}
""", orders=orders)
    return page(body, "kitchen", "Kitchen Dashboard — FIKIR")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        if ADMIN_PASSWORD and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        error = '<div style="background:#3a1a1a;border:1px solid #e74c3c;color:#ff9999;padding:10px;border-radius:8px;margin-bottom:15px;font-size:13px">Incorrect password</div>'
    
    body = '<div style="min-height:70vh;display:flex;align-items:center;justify-content:center;padding:20px">'
    body += '<div style="padding:35px;max-width:420px;width:100%;background:linear-gradient(135deg,#1a1410,#0a0805);border:1px solid #d4af37;border-radius:20px;box-shadow:0 20px 60px rgba(212,175,55,.2)">'
    body += '<div style="text-align:center;margin-bottom:25px">'
    body += '<div style="font-size:64px">ADMIN</div>'
    body += '<h2 style="color:#f0b34e;margin:10px 0 5px;font-size:24px">Admin Login</h2>'
    body += '<p style="color:#888;font-size:12px;letter-spacing:2px;margin:0">FIKIR COFFEE HOUSE</p>'
    body += '</div>'
    body += error
    body += '<form method="post">'
    body += '<label style="display:block;color:#aaa;font-size:13px;margin-bottom:6px">Password</label>'
    body += '<input type="password" name="password" required autofocus placeholder="Enter admin password" style="width:100%;padding:12px;background:#0a0805;border:1px solid #2a2018;color:#fff;border-radius:10px;font-size:15px;margin-bottom:18px;box-sizing:border-box">'
    body += '<button type="submit" class="btn" style="width:100%;padding:14px;font-size:15px;font-weight:bold">Login</button>'
    body += '</form>'
    body += '<p style="text-align:center;color:#555;font-size:11px;margin-top:20px">Owner Access Only</p>'
    body += '</div></div>'
    
    return render_template_string(BASE, body=body, page="admin_login", title="Admin Login", cart_count=cart_data()[0])


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

@app.post("/admin/products/add")
def admin_add_product():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    icon = request.form.get("icon", "☕").strip() or "☕"
    price = request.form.get("price", type=int)
    stock = request.form.get("stock", type=int)
    low_stock = request.form.get("low_stock", type=int)

    if stock is None:
        stock = 0

    if low_stock is None:
        low_stock = 5

    if not name or not description or not price or price <= 0:
        return redirect(url_for("admin"))


    # SQLite fallback
    conn = db()
    conn.execute(
        """
        INSERT INTO fikir_products
        (name, description, price, icon, stock, low_stock)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, description, price, icon, stock, low_stock)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


@app.post("/admin/products/price")
def admin_update_product_price():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    product_id = request.form.get("product_id", type=int)
    price = request.form.get("price", type=int)

    if not product_id or not price or price <= 0:
        return redirect(url_for("admin"))


    conn = db()
    conn.execute(
        "UPDATE fikir_products SET price=? WHERE id=?",
        (price, product_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


@app.post("/admin/products/stock")
def admin_update_product_stock():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    product_id = request.form.get("product_id", type=int)
    stock = request.form.get("stock", type=int)

    if not product_id or stock is None or stock < 0:
        return redirect(url_for("admin"))


    conn = db()
    conn.execute(
        "UPDATE fikir_products SET stock=? WHERE id=?",
        (stock, product_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


@app.post("/admin/products/edit")
def admin_edit_product():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    product_id = request.form.get("product_id", type=int)
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    icon = request.form.get("icon", "☕").strip() or "☕"
    price = request.form.get("price", type=int)
    stock = request.form.get("stock", type=int)
    low_stock = request.form.get("low_stock", type=int)

    if not product_id or not name or not description or not price or price <= 0:
        return redirect(url_for("admin"))

    if stock is None:
        stock = 0

    if low_stock is None:
        low_stock = 5

    data = {
        "name": name,
        "description": description,
        "price": price,
        "icon": icon,
        "stock": stock,
        "low_stock": low_stock
    }


    conn = db()
    conn.execute(
        """
        UPDATE fikir_products
        SET name=?, description=?, price=?, icon=?, stock=?, low_stock=?
        WHERE id=?
        """,
        (
            name,
            description,
            price,
            icon,
            stock,
            low_stock,
            product_id
        )
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


@app.post("/admin/products/delete")
def admin_delete_product():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    product_id = request.form.get("product_id", type=int)

    if not product_id:
        return redirect(url_for("admin"))
    conn = db()
    conn.execute(
        "DELETE FROM fikir_products WHERE id=?",
        (product_id,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    conn = db()

    where = []
    params = []

    if search:
        where.append("(CAST(id AS TEXT) LIKE ? OR customer LIKE ? OR table_no LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term, term])

    if date_from:
        where.append("date(created_at) >= date(?)")
        params.append(date_from)

    if date_to:
        where.append("date(created_at) <= date(?)")
        params.append(date_to)

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    total_orders = conn.execute(
        "SELECT COUNT(*) FROM fikir_orders" + where_sql,
        params
    ).fetchone()[0]

    total_sales = conn.execute(
        "SELECT COALESCE(SUM(total),0) FROM fikir_orders" + where_sql,
        params
    ).fetchone()[0]

    new_orders = conn.execute(
        "SELECT COUNT(*) FROM fikir_orders WHERE status='NEW'"
    ).fetchone()[0]

    preparing_orders = conn.execute(
        "SELECT COUNT(*) FROM fikir_orders WHERE status='PREPARING'"
    ).fetchone()[0]

    ready_orders = conn.execute(
        "SELECT COUNT(*) FROM fikir_orders WHERE status='READY'"
    ).fetchone()[0]

    completed_orders = conn.execute(
        "SELECT COUNT(*) FROM fikir_orders WHERE status='COMPLETED'"
    ).fetchone()[0]

    today_orders = conn.execute(
        "SELECT COUNT(*) FROM fikir_orders WHERE date(created_at)=date('now','localtime')"
    ).fetchone()[0]

    today_sales = conn.execute(
        "SELECT COALESCE(SUM(total),0) FROM fikir_orders "
        "WHERE date(created_at)=date('now','localtime')"
    ).fetchone()[0]

    recent_orders = conn.execute(
        "SELECT id, customer, table_no, items, total, status, created_at, payment_method, payment_ref, payment_status "
        "FROM fikir_orders" + where_sql +
        " ORDER BY id DESC LIMIT 50",
        params
    ).fetchall()

    

    
    
    # ═══ Payment Stats ═══
    try:
        pending_payments = conn.execute(
            "SELECT COUNT(*) FROM fikir_orders WHERE payment_status='PENDING'"
        ).fetchone()[0]
        paid_amount = conn.execute(
            "SELECT COALESCE(SUM(total),0) FROM fikir_orders WHERE payment_status='PAID'"
        ).fetchone()[0]
        unpaid_amount = conn.execute(
            "SELECT COALESCE(SUM(total),0) FROM fikir_orders WHERE payment_status IN ('PENDING','UNPAID')"
        ).fetchone()[0]
    except Exception:
        pending_payments = 0
        paid_amount = 0
        unpaid_amount = 0
    conn.close()

    body = render_template_string(r"""
    <div class="wrap">

      <div class="title">
        <div>
          <h1>📊 Admin Dashboard</h1>
          <p>FIKIR Coffee House — Order & Sales Overview</p>
        </div>
        <a class="btn" href="/admin/reports" style="background:#5b9bd5;color:#fff;margin-right:8px">📊 Reports</a>
        <a class="btn secondary" href="/">← Back to Menu</a>
      </div>

      <div class="grid">

        <div class="card">
          <h3>📦 Total Orders</h3>
          <div style="font-size:32px;font-weight:bold;color:#f0b34e">
            {{ total_orders }}
          </div>
        </div>

        <div class="card">
          <h3>💰 Total Sales</h3>
          <div style="font-size:32px;font-weight:bold;color:#f0b34e">
            ETB {{ total_sales }}
          </div>
        </div>

        <div class="card">
          <h3>🆕 New</h3>
          <div style="font-size:32px;font-weight:bold">
            {{ new_orders }}
          </div>
        </div>

        <div class="card">
          <h3>👨‍🍳 Preparing</h3>
          <div style="font-size:32px;font-weight:bold">
            {{ preparing_orders }}
          </div>
        </div>

        <div class="card">
          <h3>☕ Ready</h3>
          <div style="font-size:32px;font-weight:bold">
            {{ ready_orders }}
          </div>
        </div>

        <div class="card">
          <h3>✅ Completed</h3>
          <div style="font-size:32px;font-weight:bold">
            {{ completed_orders }}
          </div>
        </div>

      </div>

      <div class="grid" style="margin-top:20px">

        <div class="card">
          <h3>📅 Today's Orders</h3>
          <div style="font-size:30px;font-weight:bold;color:#f0b34e">
            {{ today_orders }}
          </div>
        </div>

        <div class="card">
          <h3>💵 Today's Sales</h3>
          <div style="font-size:30px;font-weight:bold;color:#f0b34e">
            ETB {{ today_sales }}
          </div>
        </div>

      </div>

        <div class="formbox" style="margin-top:25px;padding:20px">
          <h3>🔎 Search & Filter Orders</h3>
          <form method="get" action="/admin" style="display:flex;gap:10px;flex-wrap:wrap">
            <input name="search" value="{{ search }}" placeholder="Order / Customer / Table" style="flex:1;min-width:180px">
            <input type="date" name="date_from" value="{{ date_from }}">
            <input type="date" name="date_to" value="{{ date_to }}">
            <button class="btn" type="submit">🔍 Filter</button>
            <a class="btn secondary" href="/admin">↻ Clear</a>
          </form>
        </div>

      <div class="formbox" style="margin-top:25px">
        <div class="title">
          <div>
        <div class="formbox" style="margin-top:25px">
          <div class="title">
            <div>
              <h2>☕ Product Management</h2>
          <p>Add, edit and delete coffee products</p>

          <!-- ADD PRODUCT -->
          <div class="card" style="padding:20px;margin-bottom:20px">
            <h3>➕ Add New Product</h3>

            <form method="post"
                  action="/admin/products/add"
                  style="display:grid;gap:10px">

              <input name="name"
                     placeholder="Product name"
                     required>

              <input name="description"
                     placeholder="Description"
                     required>

              <input name="price"
                     type="number"
                     min="1"
                     placeholder="Price (ETB)"
                     required>

              <input name="stock"
                     type="number"
                     min="0"
                     value="20"
                     placeholder="Initial Stock"
                     required>

              <input name="low_stock"
                     type="number"
                     min="0"
                     value="5"
                     placeholder="Low Stock Alert"
                     required>

              <input name="icon"
                     placeholder="Icon e.g. ☕"
                     value="☕">

              <button class="btn" type="submit">
                ➕ Add Product
              </button>

            </form>
          </div>


          <!-- PRODUCTS -->
          <h3>📋 Products</h3>

          {% for p in products %}

          <div class="card"
               style="padding:18px;margin-top:12px">

            <div style="display:flex;
                        justify-content:space-between;
                        gap:15px;
                        flex-wrap:wrap;
                        align-items:center">

              <div style="flex:1;min-width:180px">

                <div style="font-size:20px;font-weight:bold">
                  {{ p.icon }} {{ p.name }}
                </div>

                <div style="color:#aaa;margin-top:5px">
                  {{ p.desc }}
                </div>

                <div style="margin-top:8px">
                  <b style="color:#f0b34e">
                    ETB {{ p.price }}
                  </b>

                  &nbsp; | &nbsp;

                  📦 Stock:
                  <b>{{ p.stock }}</b>

                  &nbsp; | &nbsp;

                  ⚠️ Low:
                  <b>{{ p.low_stock }}</b>
                </div>

              </div>


              <!-- EDIT -->
              <details style="min-width:280px;flex:1">

                <summary class="btn"
                         style="display:inline-block;
                                cursor:pointer">
                  ✏️ Edit
                </summary>

                <form method="post"
                      action="/admin/products/edit"
                      style="display:grid;
                             gap:8px;
                             margin-top:12px">

                  <input type="hidden"
                         name="product_id"
                         value="{{ p.id }}">

                  <input name="name"
                         value="{{ p.name }}"
                         placeholder="Product name"
                         required>

                  <input name="description"
                         value="{{ p.desc }}"
                         placeholder="Description"
                         required>

                  <input name="price"
                         type="number"
                         min="1"
                         value="{{ p.price }}"
                         placeholder="Price"
                         required>

                  <input name="stock"
                         type="number"
                         min="0"
                         value="{{ p.stock }}"
                         placeholder="Stock"
                         required>

                  <input name="low_stock"
                         type="number"
                         min="0"
                         value="{{ p.low_stock }}"
                         placeholder="Low stock"
                         required>

                  <input name="icon"
                         value="{{ p.icon }}"
                         placeholder="Icon">

                  <button class="btn"
                          type="submit">
                    💾 Save Changes
                  </button>

                </form>

              </details>


              <!-- DELETE -->
              <form method="post"
                    action="/admin/products/delete"
                    onsubmit="return confirm('Delete {{ p.name }}?');">

                <input type="hidden"
                       name="product_id"
                       value="{{ p.id }}">

                <button class="btn"
                        type="submit"
                        style="background:#8b2f2f">
                  🗑️ Delete
                </button>

              </form>

            </div>

          </div>

          {% endfor %}

        </div>

            <h2>🧾 Recent Orders</h2>
            <p>Latest 20 customer orders</p>
          </div>
          <a class="btn secondary" href="/kitchen">👨‍🍳 Kitchen</a>
        </div>

        {% if recent_orders %}

        <div style="overflow-x:auto">
          <table style="width:100%;border-collapse:collapse">

            <tr style="border-bottom:1px solid #4b3218">
              <th style="padding:12px;text-align:left">Order</th>
              <th style="padding:12px;text-align:left">Customer</th>
              <th style="padding:12px;text-align:left">Table</th>
              <th style="padding:12px;text-align:left">Items</th>
              <th style="padding:12px;text-align:left">Total</th>
              <th style="padding:12px;text-align:left">Status</th>
              <th style="padding:12px;text-align:left">Payment</th>
              <th style="padding:12px;text-align:left">Date</th>
            </tr>

            <!-- ═══ TOP PRODUCTS ═══ -->
{% if top_products %}
<div class="formbox" style="margin-top:25px;padding:20px">
  <h3>🏆 Top Selling Products</h3>
  <div style="display:flex;flex-direction:column;gap:10px;margin-top:15px">
  {% for name, count in top_products %}
    <div style="display:flex;align-items:center;gap:12px;padding:10px;background:#0a0805;border:1px solid #2a2018;border-radius:8px">
      <div style="font-size:24px;font-weight:bold;color:#f0b34e;min-width:40px">
        {% if loop.index == 1 %}🥇{% elif loop.index == 2 %}🥈{% elif loop.index == 3 %}🥉{% else %}{{ loop.index }}{% endif %}
      </div>
      <div style="flex:1">
        <div style="font-weight:bold">{{ name }}</div>
      </div>
      <div style="color:#f0b34e;font-weight:bold">{{ count }} sold</div>
    </div>
  {% endfor %}
  </div>
</div>
{% endif %}

<!-- ═══ REVENUE CHART ═══ -->
{% if revenue_days %}
<div class="formbox" style="margin-top:25px;padding:20px">
  <h3>📊 Revenue (Last 7 Days)</h3>
  <div style="display:flex;flex-direction:column;gap:12px;margin-top:15px">
  {% for day, rev in revenue_days %}
    <div>
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="color:#aaa;font-size:13px">{{ day }}</span>
        <span style="color:#f0b34e;font-weight:bold">ETB {{ rev }}</span>
      </div>
      <div style="background:#1a1410;height:8px;border-radius:4px;overflow:hidden">
        <div style="background:linear-gradient(90deg,#f0b34e,#d4af37);height:100%;width:{{ (rev / max_rev * 100)|int }}%;border-radius:4px;transition:width .5s"></div>
      </div>
    </div>
  {% endfor %}
  </div>
</div>
{% endif %}

<!-- ═══ PRINT RECEIPT BUTTON (per order) ═══ -->
<script>
function printReceipt(id, customer, table, items, total, date) {
    var w = window.open('', '', 'width=350,height=600');
    w.document.write('<html><head><title>Receipt</title>');
    w.document.write('<style>body{font-family:monospace;padding:20px;max-width:300px}');
    w.document.write('h2{text-align:center;margin:5px 0}');
    w.document.write('.line{border-top:1px dashed #000;margin:10px 0}');
    w.document.write('.row{display:flex;justify-content:space-between;margin:5px 0}');
    w.document.write('.total{font-weight:bold;font-size:18px}
/* ═══════ MOBILE OPTIMIZATION ═══════ */
@media (max-width: 768px) {
    body { font-size: 15px; }
    
    /* Header */
    header, .topbar, nav { padding: 10px 12px !important; }
    .brand { font-size: 20px !important; }
    .brand small { font-size: 9px !important; }
    nav a { padding: 8px 6px !important; font-size: 12px !important; }
    nav { gap: 4px !important; }
    
    /* Hero */
    .hero { padding: 20px 16px !important; }
    .hero h1 { font-size: 32px !important; line-height: 1.1; }
    .hero p { font-size: 13px !important; }
    .hero .btn { padding: 8px 16px !important; font-size: 13px !important; }
    
    /* Layout */
    .layout { grid-template-columns: 1fr !important; gap: 16px !important; padding: 0 12px !important; }
    .grid { grid-template-columns: repeat(2, 1fr) !important; gap: 10px !important; padding: 0 !important; }
    .aside, .side { position: static !important; width: 100% !important; }
    
    /* Product Cards */
    .product, .card { padding: 12px !important; }
    .productpic { font-size: 40px !important; }
    .product h3 { font-size: 15px !important; }
    .product .desc { font-size: 11px !important; min-height: auto !important; }
    .price { font-size: 16px !important; }
    .add, .btn { padding: 8px 14px !important; font-size: 13px !important; }
    
    /* Cart */
    .order { padding: 10px !important; }
    .cartitem { font-size: 13px !important; }
    
    /* Tables */
    table { font-size: 12px !important; }
    th, td { padding: 6px 4px !important; }
    
    /* Forms */
    input, select, textarea, button { font-size: 15px !important; padding: 10px !important; }
    
    /* Stats grid */
    .grid[style*="repeat(auto"] { grid-template-columns: repeat(2, 1fr) !important; }
    .card h3 { font-size: 12px !important; }
    .card div[style*="font-size:32px"] { font-size: 22px !important; }
    
    /* Section titles */
    h2 { font-size: 22px !important; }
    h3 { font-size: 17px !important; }
}

@media (max-width: 480px) {
    .grid { grid-template-columns: 1fr !important; }
    .hero h1 { font-size: 26px !important; }
    nav a { padding: 6px 4px !important; font-size: 11px !important; }
}


/* ═══════ LOADING SCREEN ═══════ */
#loading-screen {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: #0a0805; z-index: 99999;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    transition: opacity 0.6s ease, visibility 0.6s;
}
#loading-screen.hidden { opacity: 0; visibility: hidden; }
#loading-screen .logo-text {
    font-family: 'Playfair Display', serif;
    font-size: 42px; font-weight: 900; letter-spacing: 4px;
    background: linear-gradient(135deg, #d4af37, #f0b34e, #d4af37);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: glow 2s ease-in-out infinite;
}
#loading-screen .cup {
    font-size: 72px;
    animation: float 1.5s ease-in-out infinite;
    margin-bottom: 20px;
}
#loading-screen .subtitle {
    color: #666; font-size: 11px; letter-spacing: 6px;
    margin-top: 10px; text-transform: uppercase;
}
@keyframes glow {
    0%,100% { filter: drop-shadow(0 0 5px rgba(212,175,55,.3)); }
    50% { filter: drop-shadow(0 0 20px rgba(212,175,55,.7)); }
}
</style></head><body>');
    w.document.write('<h2>FIKIR COFFEE HOUSE</h2>');
    w.document.write('<p style="text-align:center;font-size:12px;margin:0">Taste the Difference</p>');
    w.document.write('<div class="line"></div>');
    w.document.write('<div class="row"><span>Order #' + id + '</span><span>' + date + '</span></div>');
    w.document.write('<div class="row"><span>Customer:</span><span>' + customer + '</span></div>');
    w.document.write('<div class="row"><span>Table:</span><span>' + table + '</span></div>');
    w.document.write('<div class="line"></div>');
    w.document.write('<div style="font-size:13px">' + items.replace(/,/g, '<br>') + '</div>');
    w.document.write('<div class="line"></div>');
    w.document.write('<div class="row total"><span>TOTAL:</span><span>ETB ' + total + '</span></div>');
    w.document.write('<div class="line"></div>');
    w.document.write('<p style="text-align:center;font-size:12px">Thank you! ☕</p>');
    w.document.write('</body></html>');
    w.document.close();
    setTimeout(function(){ w.print(); }, 500);
}

// ═══════ ADMIN STATS LOADER ═══════
if (window.location.pathname.startsWith('/admin')) {
    setTimeout(function() {
        fetch('/admin/stats').then(function(r) { return r.json(); }).then(function(d) {
            var h = '';
            if (d.top && d.top.length) {
                h += '<div class="formbox" style="margin-top:25px;padding:20px"><h3>🏆 Top Selling Products</h3>';
                d.top.forEach(function(p, i) {
                    var medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : (i+1);
                    h += '<div style="display:flex;align-items:center;gap:12px;padding:10px;background:#0a0805;border:1px solid #2a2018;border-radius:8px;margin-top:8px">';
                    h += '<div style="font-size:24px;font-weight:bold;color:#f0b34e;min-width:40px">' + medal + '</div>';
                    h += '<div style="flex:1;font-weight:bold">' + p.name + '</div>';
                    h += '<div style="color:#f0b34e;font-weight:bold">' + p.count + ' sold</div>';
                    h += '</div>';
                });
                h += '</div>';
            }
            if (d.revenue && d.revenue.length) {
                var max = Math.max.apply(null, d.revenue.map(function(x) { return x.rev; })) || 1;
                h += '<div class="formbox" style="margin-top:25px;padding:20px"><h3>📊 Revenue (Last 7 Days)</h3>';
                d.revenue.forEach(function(r) {
                    var pct = Math.round(r.rev / max * 100);
                    h += '<div style="margin-top:12px"><div style="display:flex;justify-content:space-between;margin-bottom:4px">';
                    h += '<span style="color:#aaa;font-size:13px">' + r.day + '</span>';
                    h += '<span style="color:#f0b34e;font-weight:bold">ETB ' + r.rev + '</span></div>';
                    h += '<div style="background:#1a1410;height:8px;border-radius:4px;overflow:hidden"><div style="background:linear-gradient(90deg,#f0b34e,#d4af37);height:100%;width:' + pct + '%;border-radius:4px"></div></div></div>';
                });
                h += '</div>';
            }
            if (h) {
                var target = document.querySelector('h2#product-mgmt') || document.querySelectorAll('h2')[1];
                if (target) {
                    var wrap = target.closest('div.formbox') || target.parentElement;
                    if (wrap) wrap.insertAdjacentHTML('beforebegin', h);
                }
            }
        }).catch(function(){});
    }, 500);
}
</script>

{% for o in recent_orders %}
            <tr style="border-bottom:1px solid #332619">

              <td style="padding:12px">
                #{{ o.id }}
              </td>

              <td style="padding:12px">
                {{ o.customer }}
              </td>

              <td style="padding:12px">
                {{ o.table_no }}
              </td>

              <td style="padding:12px">
                {{ o.items }}
              </td>

              <td style="padding:12px;font-weight:bold;color:#f0b34e">
                ETB {{ o.total }}
              </td>

              <td style="padding:12px">
                <span class="status">{{ o.status }}</span>
              </td>
          <td style="padding:12px">
            {% if o.payment_status == 'PAID' %}
              <span style="background:#1a3a1a;color:#4caf50;padding:4px 8px;border-radius:8px;font-size:11px;font-weight:bold">PAID</span>
            {% elif o.payment_status == 'PENDING' %}
              <div style="display:flex;flex-direction:column;gap:4px">
                <span style="background:#3a2a1a;color:#f0b34e;padding:4px 8px;border-radius:8px;font-size:11px;font-weight:bold">PENDING</span>
                <div style="display:flex;gap:4px">
                  <button onclick="verifyPayment({{ o.id }}, true)" style="background:#4caf50;color:#fff;border:0;padding:4px 8px;border-radius:6px;font-size:10px;cursor:pointer;font-weight:bold">Paid</button>
                  <button onclick="verifyPayment({{ o.id }}, false)" style="background:#e74c3c;color:#fff;border:0;padding:4px 8px;border-radius:6px;font-size:10px;cursor:pointer;font-weight:bold">Reject</button>
                </div>
              </div>
            {% elif o.payment_status == 'REJECTED' %}
              <span style="background:#3a1a1a;color:#e74c3c;padding:4px 8px;border-radius:8px;font-size:11px;font-weight:bold">REJECTED</span>
            {% else %}
              <span style="color:#888;font-size:11px">UNPAID</span>
            {% endif %}
          </td>

              <td style="padding:12px">
                {{ o.created_at }}
              </td>

            </tr>
            {% endfor %}

          </table>
        </div>

        {% else %}

        <div class="card" style="padding:30px;text-align:center">
          <h3>No orders yet ☕</h3>
        </div>

        {% endif %}

      </div>

    </div>
    """,
    total_orders=total_orders,
    total_sales=total_sales,
    new_orders=new_orders,
    preparing_orders=preparing_orders,
    ready_orders=ready_orders,
    completed_orders=completed_orders,
    today_orders=today_orders,
    today_sales=today_sales,
    recent_orders=recent_orders,
    search=search,
    date_from=date_from,
    date_to=date_to,
    products=get_products(), pending_payments=pending_payments, paid_amount=paid_amount, unpaid_amount=unpaid_amount)

    return page(body, "admin", "Admin Dashboard — FIKIR")

@app.post("/kitchen/status")
def kitchen_status():
    order_id = request.form.get("order_id", type=int)
    status = request.form.get("status", "NEW")
    if status not in {"NEW","PREPARING","READY","COMPLETED"}:
        status = "NEW"
    conn=db()
    conn.execute("UPDATE fikir_orders SET status=? WHERE id=?", (status, order_id))
    conn.commit(); conn.close()
    return redirect(url_for("kitchen"))

@app.route("/api/orders")
def api_orders():
    conn=db()
    rows=conn.execute("SELECT * FROM fikir_orders ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])



@app.route("/admin/stats")
def admin_stats():
    """Return top products + revenue as JSON"""
    from collections import Counter
    conn = db()
    # Top products
    counts = Counter()
    for row in conn.execute("SELECT items FROM fikir_orders"):
        items = row["items"] or ""
        for part in items.split(","):
            part = part.strip()
            if "\u00d7" in part:
                name = part.rsplit("\u00d7", 1)[0].strip()
                try:
                    qty = int(part.rsplit("\u00d7", 1)[1].strip())
                except:
                    qty = 1
                counts[name] += qty
    top = [{"name": n, "count": c} for n, c in counts.most_common(5)]
    
    # Revenue last 7 days
    revs = []
    for row in conn.execute(
        "SELECT DATE(created_at) as day, COALESCE(SUM(total),0) as rev "
        "FROM fikir_orders WHERE created_at >= DATE('now','-7 days') "
        "GROUP BY DATE(created_at) ORDER BY day DESC"
    ):
        revs.append({"day": row["day"], "rev": row["rev"]})
    
    conn.close()
    return jsonify({"top": top, "revenue": revs})



@app.route("/admin/update-status", methods=["POST"])
def admin_update_status():
    if not session.get("admin_logged_in"):
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    order_id = request.form.get("order_id", type=int)
    new_status = request.form.get("status", "").strip().upper()
    if not order_id or new_status not in ("NEW", "PREPARING", "READY", "COMPLETED", "CANCELLED"):
        return jsonify({"ok": False, "error": "invalid input"}), 400
    conn = db()
    conn.execute("UPDATE fikir_orders SET status=? WHERE id=?", (new_status, order_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "status": new_status})



@app.route("/track/<int:order_id>")
def track_order(order_id):
    conn = db()
    row = conn.execute(
        "SELECT id, customer, table_no, items, total, status, created_at "
        "FROM fikir_orders WHERE id=?", (order_id,)
    ).fetchone()
    conn.close()
    if not row:
        return "<h2>Order not found</h2>", 404
    
    status = (row["status"] or "NEW").upper()
    steps = ["NEW", "PREPARING", "READY", "COMPLETED"]
    labels = {"NEW": "Received", "PREPARING": "Preparing", "READY": "Ready", "COMPLETED": "Completed"}
    current_idx = steps.index(status) if status in steps else 0
    
    timeline = ""
    for i, s in enumerate(steps):
        done = i <= current_idx
        active = i == current_idx
        color = "#f0b34e" if done else "#333"
        bg = "#1a1410" if done else "#0a0805"
        text_color = "#fff" if done else "#555"
        glow = "box-shadow:0 0 15px #f0b34e;" if active else ""
        icon = "OK" if i < current_idx else ("NOW" if active else "o")
        timeline = timeline + '<div style="display:flex;align-items:center;gap:15px;padding:15px;margin-bottom:8px;background:' + bg + ';border-left:4px solid ' + color + ';border-radius:8px;' + glow + '">'
        timeline = timeline + '<div style="font-size:20px;font-weight:bold;color:' + color + '">' + icon + '</div>'
        timeline = timeline + '<div style="flex:1;font-weight:bold;color:' + text_color + '">' + labels[s] + '</div>'
        timeline = timeline + '</div>'
    
    items_html = (row["items"] or "").replace(",", "<br>")
    
    body = '<div style="max-width:600px;margin:20px auto;padding:20px">'
    body = body + '<div style="background:linear-gradient(135deg,#1a1410,#0a0805);border:1px solid #f0b34e;border-radius:16px;padding:25px;text-align:center;margin-bottom:25px">'
    body = body + '<h1 style="color:#f0b34e;margin:0">FIKIR COFFEE HOUSE</h1>'
    body = body + '<p style="color:#aaa;margin:5px 0">Order Tracking</p>'
    body = body + '<div style="font-size:42px;font-weight:bold;color:#fff;margin:15px 0">#' + str(row["id"]) + '</div>'
    body = body + '<div style="color:#f0b34e;font-size:16px">FIK-' + str(row["id"]).zfill(4) + '</div>'
    body = body + '</div>'
    body = body + '<div style="background:#0a0805;border:1px solid #2a2018;border-radius:12px;padding:20px;margin-bottom:20px">'
    body = body + '<p style="color:#aaa;margin:5px 0">Customer: <b style="color:#fff">' + str(row["customer"]) + '</b></p>'
    body = body + '<p style="color:#aaa;margin:5px 0">Table: <b style="color:#fff">' + str(row["table_no"]) + '</b></p>'
    body = body + '<p style="color:#aaa;margin:5px 0">Time: <b style="color:#fff">' + str(row["created_at"]) + '</b></p>'
    body = body + '</div>'
    body = body + '<h3 style="color:#f0b34e;margin:20px 0 15px">Order Status</h3>'
    body = body + timeline
    body = body + '<h3 style="color:#f0b34e;margin:25px 0 15px">Items</h3>'
    body = body + '<div style="background:#0a0805;border:1px solid #2a2018;border-radius:12px;padding:20px;color:#fff;line-height:1.8">'
    body = body + items_html
    body = body + '<div style="border-top:1px solid #2a2018;margin-top:15px;padding-top:15px;font-size:20px;font-weight:bold;color:#f0b34e">TOTAL: ETB ' + str(row["total"]) + '</div>'
    body = body + '</div>'
    body = body + '<p style="text-align:center;color:#666;font-size:13px;margin-top:30px">Page refreshes every 10 seconds</p>'
    body = body + '<script>setTimeout(function(){location.reload();},10000);</script>'
    body = body + '</div>'
    
    return render_template_string(BASE, body=body, page="track", title="Track Order", cart_count=cart_data()[0])



@app.route("/cart/update", methods=["POST"])
def cart_update():
    pid = request.form.get("product_id", type=int)
    delta = request.form.get("delta", type=int)
    if not pid or delta not in (-1, 1):
        return jsonify({"ok": False, "error": "invalid"}), 400
    cart = session.get("cart", {})
    key = str(pid)
    current = int(cart.get(key, 0))
    new_qty = current + delta
    if new_qty <= 0:
        cart.pop(key, None)
    else:
        cart[key] = new_qty
    session["cart"] = cart
    return jsonify({"ok": True, "qty": new_qty})

@app.route("/cart/remove", methods=["POST"])
def cart_remove():
    pid = request.form.get("product_id", type=int)
    if not pid:
        return jsonify({"ok": False}), 400
    cart = session.get("cart", {})
    cart.pop(str(pid), None)
    session["cart"] = cart
    return jsonify({"ok": True})



@app.route("/admin/reports")
def admin_reports():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    
    from datetime import datetime, timedelta
    now = datetime.now()
    
    # Custom date range
    custom_from = request.args.get("from", "").strip()
    custom_to = request.args.get("to", "").strip()
    period = request.args.get("period", "today")
    
    if custom_from and custom_to:
        start = custom_from
        end = custom_to
        label = f"{custom_from} → {custom_to}"
    else:
        end = now.strftime("%Y-%m-%d")
        if period == "today":
            start = now.strftime("%Y-%m-%d")
            label = "Today"
        elif period == "week":
            start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            label = "Last 7 Days"
        elif period == "month":
            start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            label = "Last 30 Days"
        elif period == "year":
            start = (now - timedelta(days=365)).strftime("%Y-%m-%d")
            label = "Last 365 Days"
        else:
            start = "1970-01-01"
            label = "All Time"
    
    conn = db()
    
    # Stats
    total_orders = conn.execute(
        "SELECT COUNT(*) FROM fikir_orders WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?", (start, end)
    ).fetchone()[0]
    total_revenue = conn.execute(
        "SELECT COALESCE(SUM(total),0) FROM fikir_orders WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?", (start, end)
    ).fetchone()[0]
    avg_order = round(total_revenue / total_orders, 0) if total_orders else 0
    
    # Top customers
    top_customers = conn.execute(
        "SELECT customer, COUNT(*) as orders, SUM(total) as spent "
        "FROM fikir_orders WHERE DATE(created_at) >= ? AND DATE(created_at) <= ? "
        "GROUP BY customer ORDER BY spent DESC LIMIT 5", (start, end)
    ).fetchall()
    
    # Busiest hours
    busiest_hours = conn.execute(
        "SELECT substr(created_at, 12, 2) as hour, COUNT(*) as count "
        "FROM fikir_orders WHERE DATE(created_at) >= ? AND DATE(created_at) <= ? "
        "GROUP BY hour ORDER BY count DESC LIMIT 5", (start, end)
    ).fetchall()
    
    # Revenue by product (parse from items)
    from collections import Counter
    product_revenue = Counter()
    for r in conn.execute(
        "SELECT items, total FROM fikir_orders WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?",
        (start, end)
    ):
        for part in (r["items"] or "").split(","):
            part = part.strip()
            if "\u00d7" in part:
                n = part.rsplit("\u00d7", 1)[0].strip()
                try: q = int(part.rsplit("\u00d7", 1)[1].strip())
                except: q = 1
                product_revenue[n] += q
    
    # Top products
    from collections import Counter
    counts = Counter()
    for r in conn.execute(
        "SELECT items FROM fikir_orders WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?",
        (start, end)
    ):
        for p in (r["items"] or "").split(","):
            p = p.strip()
            if "\u00d7" in p:
                n = p.rsplit("\u00d7", 1)[0].strip()
                try: q = int(p.rsplit("\u00d7", 1)[1].strip())
                except: q = 1
                counts[n] += q
    top = counts.most_common(10)
    
    # All orders
    orders = conn.execute(
        "SELECT id, customer, table_no, items, total, status, created_at "
        "FROM fikir_orders WHERE DATE(created_at) >= ? AND DATE(created_at) <= ? "
        "ORDER BY id DESC LIMIT 100", (start, end)
    ).fetchall()
    conn.close()
    
    # Build HTML
    body = '<div class="formbox" style="padding:20px">'
    body += '<h1 style="color:#f0b34e;margin:0">\U0001f4ca Reports</h1>'
    body += '<p style="color:#aaa;margin:5px 0 20px">' + label + ' - Sales Overview</p>'
    
    # Period buttons
    body += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px">'
    for p, pl in [("today","Today"),("week","7 Days"),("month","30 Days"),("year","1 Year"),("all","All Time")]:
        active = "background:#f0b34e;color:#000" if p == period else "background:#1a1410;color:#f0b34e"
        body += '<a href="/admin/reports?period=' + p + '" style="padding:8px 16px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:13px;' + active + '">' + pl + '</a>'
    body += '</div>'
    
    # Custom date range
    body += '<form method="get" action="/admin/reports" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;align-items:center;background:#0a0805;border:1px solid #2a2018;border-radius:10px;padding:12px">'
    body += '<span style="color:#aaa;font-size:12px">Custom Range:</span>'
    body += '<input type="date" name="from" value="" style="padding:6px 10px;background:#1a1410;border:1px solid #2a2018;color:#f0b34e;border-radius:6px;font-size:12px">'
    body += '<span style="color:#666">to</span>'
    body += '<input type="date" name="to" value="" style="padding:6px 10px;background:#1a1410;border:1px solid #2a2018;color:#f0b34e;border-radius:6px;font-size:12px">'
    body += '<button type="submit" style="padding:6px 14px;background:#f0b34e;color:#000;border:0;border-radius:6px;font-weight:bold;font-size:12px;cursor:pointer">Apply</button>'
    body += '</form>'
    
    # Stats cards
    body += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:25px">'
    body += '<div style="background:#0a0805;border:1px solid #2a2018;border-radius:12px;padding:15px;text-align:center">'
    body += '<div style="color:#aaa;font-size:12px">Total Orders</div>'
    body += '<div style="color:#f0b34e;font-size:28px;font-weight:bold">' + str(total_orders) + '</div></div>'
    body += '<div style="background:#0a0805;border:1px solid #2a2018;border-radius:12px;padding:15px;text-align:center">'
    body += '<div style="color:#aaa;font-size:12px">Total Revenue</div>'
    body += '<div style="color:#f0b34e;font-size:28px;font-weight:bold">ETB ' + str(total_revenue) + '</div></div>'
    body += '<div style="background:#0a0805;border:1px solid #2a2018;border-radius:12px;padding:15px;text-align:center">'
    body += '<div style="color:#aaa;font-size:12px">Avg Order</div>'
    body += '<div style="color:#f0b34e;font-size:28px;font-weight:bold">ETB ' + str(int(avg_order)) + '</div></div>'
    body += '</div>'
    
    # Top products
    if top:
        body += '<h3 style="color:#f0b34e;margin:20px 0 15px">\U0001f3c6 Top Products</h3>'
        max_count = top[0][1] if top else 1
        for i, (name, cnt) in enumerate(top):
            medal = ["\U0001f947","\U0001f948","\U0001f949"][i] if i < 3 else str(i+1)
            pct = round(cnt / max_count * 100)
            body += '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;padding:8px;background:#0a0805;border-radius:8px">'
            body += '<div style="min-width:30px;text-align:center;font-size:18px">' + medal + '</div>'
            body += '<div style="flex:1"><div style="color:#fff;font-size:13px">' + name + '</div>'
            body += '<div style="background:#1a1410;height:6px;border-radius:3px;margin-top:4px;overflow:hidden"><div style="background:linear-gradient(90deg,#f0b34e,#d4af37);height:100%;width:' + str(pct) + '%"></div></div></div>'
            body += '<div style="color:#f0b34e;font-weight:bold;min-width:40px;text-align:right">' + str(cnt) + '</div>'
            body += '</div>'
    
    # Export button
    body += '<div style="display:flex;gap:8px;margin:25px 0 15px;flex-wrap:wrap">'
    body += '<a href="/admin/reports/export?period=' + period + '" style="padding:10px 20px;background:#4caf50;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold;font-size:13px">\U0001f4e5 Export CSV</a>'
    body += '<a href="/admin/reports/telegram?period=' + period + '" style="padding:10px 20px;background:#5b9bd5;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold;font-size:13px">\U0001f4f1 Send to Telegram</a>'
    body += '<a href="/admin" style="padding:10px 20px;background:#2a2018;color:#f0b34e;border-radius:8px;text-decoration:none;font-weight:bold;font-size:13px">\u2190 Back</a>'
    body += '</div>'
    
    # Orders table
    body += '<h3 style="color:#f0b34e;margin:20px 0 15px">\U0001f4cb Orders (' + str(len(orders)) + ')</h3>'
    body += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">'
    body += '<tr style="background:#1a1410;color:#f0b34e"><th style="padding:8px;text-align:left">#</th><th style="padding:8px;text-align:left">Customer</th><th style="padding:8px;text-align:left">Table</th><th style="padding:8px;text-align:left">Items</th><th style="padding:8px;text-align:right">Total</th><th style="padding:8px;text-align:left">Status</th><th style="padding:8px;text-align:left">Payment</th><th style="padding:8px;text-align:left">Date</th></tr>'
    for o in orders:
        body += '<tr style="border-bottom:1px solid #1a1410">'
        body += '<td style="padding:8px;color:#aaa">#' + str(o["id"]) + '</td>'
        body += '<td style="padding:8px;color:#fff">' + str(o["customer"]) + '</td>'
        body += '<td style="padding:8px;color:#aaa">' + str(o["table_no"]) + '</td>'
        body += '<td style="padding:8px;color:#aaa;font-size:11px">' + str(o["items"]) + '</td>'
        body += '<td style="padding:8px;color:#f0b34e;text-align:right;font-weight:bold">ETB ' + str(o["total"]) + '</td>'
        body += '<td style="padding:8px"><span style="background:#2a2018;color:#f0b34e;padding:2px 8px;border-radius:10px;font-size:10px">' + str(o["status"]) + '</span></td>'
        body += '<td style="padding:8px;color:#666;font-size:11px">' + str(o["created_at"])[:16] + '</td>'
        body += '</tr>'
    body += '</table></div>'
    
    body += '</div>'
    
    return render_template_string(BASE, body=body, page="reports", title="Reports", cart_count=cart_data()[0])


@app.route("/admin/reports/export")
def admin_reports_export():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    
    from datetime import datetime, timedelta
    import csv, io
    period = request.args.get("period", "today")
    now = datetime.now()
    if period == "today":
        start = now.strftime("%Y-%m-%d")
    elif period == "week":
        start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period == "month":
        start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        start = "1970-01-01"
    
    conn = db()
    orders = conn.execute(
        "SELECT id, customer, table_no, items, total, status, created_at "
        "FROM fikir_orders WHERE DATE(created_at) >= ? ORDER BY id DESC", (start,)
    ).fetchall()
    conn.close()
    
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(["Order ID", "Customer", "Table", "Items", "Total (ETB)", "Status", "Date"])
    for o in orders:
        writer.writerow([o["id"], o["customer"], o["table_no"], o["items"], o["total"], o["status"], o["created_at"]])
    
    output = si.getvalue()
    return output, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": "attachment; filename=fikir-report-" + start + ".csv"
    }


@app.route("/admin/reports/telegram")
def admin_reports_telegram():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    
    from datetime import datetime, timedelta
    from collections import Counter
    period = request.args.get("period", "today")
    now = datetime.now()
    if period == "today":
        start = now.strftime("%Y-%m-%d")
        label = "\U0001f4c5 Today"
    elif period == "week":
        start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        label = "\U0001f4c5 Last 7 Days"
    elif period == "month":
        start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        label = "\U0001f4c5 Last 30 Days"
    else:
        start = "1970-01-01"
        label = "\U0001f4c5 All Time"
    
    conn = db()
    total_orders = conn.execute("SELECT COUNT(*) FROM fikir_orders WHERE DATE(created_at) >= ?", (start,)).fetchone()[0]
    total_rev = conn.execute("SELECT COALESCE(SUM(total),0) FROM fikir_orders WHERE DATE(created_at) >= ?", (start,)).fetchone()[0]
    counts = Counter()
    for r in conn.execute("SELECT items FROM fikir_orders WHERE DATE(created_at) >= ?", (start,)):
        for p in (r["items"] or "").split(","):
            p = p.strip()
            if "\u00d7" in p:
                n = p.rsplit("\u00d7", 1)[0].strip()
                try: q = int(p.rsplit("\u00d7", 1)[1].strip())
                except: q = 1
                counts[n] += q
    conn.close()
    top = counts.most_common(3)
    
    msg = "\U0001f4ca FIKIR COFFEE - REPORT\n"
    msg += label + "\n"
    msg += "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    msg += "\U0001f6d2 Orders: " + str(total_orders) + "\n"
    msg += "\U0001f4b0 Revenue: ETB " + str(total_rev) + "\n"
    if total_orders:
        msg += "\U0001f4c8 Avg: ETB " + str(int(total_rev / total_orders)) + "\n"
    if top:
        msg += "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        msg += "\U0001f3c6 Top Items:\n"
        for i, (n, c) in enumerate(top):
            medal = ["\U0001f947","\U0001f948","\U0001f949"][i]
            msg += medal + " " + n + " - " + str(c) + "\n"
    
    send_telegram(msg)
    
    return redirect(url_for("admin_reports", period=period))



@app.route("/static/sw.js")
def serve_sw():
    from flask import send_from_directory
    response = send_from_directory("static", "sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response

@app.route("/static/manifest.json")
def serve_manifest():
    from flask import send_from_directory
    response = send_from_directory("static", "manifest.json")
    response.headers["Content-Type"] = "application/manifest+json"
    return response

@app.route("/static/logo.png")
def serve_static_logo():
    from flask import send_from_directory
    return send_from_directory("static", "logo.png")



@app.route("/favicon.ico")
def favicon():
    from flask import send_from_directory
    return send_from_directory("static", "favicon.png", mimetype="image/png")



# ═══════ PAYMENT VERIFICATION ROUTE ═══════

@app.route("/payment/confirm", methods=["POST"])
def payment_confirm():
    order_id = request.form.get("order_id", type=int)
    tx_id = request.form.get("tx_id", "").strip()
    method = request.form.get("method", "telebirr").strip()
    
    if not order_id or not tx_id:
        return jsonify({"ok": False, "error": "Missing fields"}), 400
    
    conn = db()
    order = conn.execute("SELECT * FROM fikir_orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"ok": False, "error": "Order not found"}), 404
    
    conn.execute(
        "UPDATE fikir_orders SET payment_method=?, payment_ref=?, payment_status='PENDING' WHERE id=?",
        (method, tx_id, order_id)
    )
    conn.commit()
    conn.close()
    
    method_name = "Telebirr" if method == "telebirr" else "CBE Birr"
    send_telegram(
        "PAYMENT RECEIVED\n"
        "Order #" + str(order_id) + "\n"
        "Customer: " + str(order["customer"]) + "\n"
        "Method: " + method_name + "\n"
        "Amount: ETB " + str(order["total"]) + "\n"
        "Ref: " + tx_id
    )
    
    return jsonify({"ok": True})



@app.route("/admin/mark-paid", methods=["POST"])
def admin_mark_paid():
    if not session.get("admin_logged_in"):
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    order_id = request.form.get("order_id", type=int)
    if not order_id:
        return jsonify({"ok": False, "error": "invalid"}), 400
    conn = db()
    conn.execute("UPDATE fikir_orders SET payment_status='PAID' WHERE id=?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})



# ═══════ WAITER MODE ═══════

@app.route("/waiter/login", methods=["GET", "POST"])
def waiter_login():
    error = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == WAITER_PASSWORD:
            session["waiter_logged_in"] = True
            return redirect(url_for("waiter_dashboard"))
        error = '<div style="background:#3a1a1a;border:1px solid #e74c3c;color:#ff9999;padding:10px;border-radius:8px;margin-bottom:15px;font-size:13px">Incorrect password</div>'
    
    body = '<div style="min-height:70vh;display:flex;align-items:center;justify-content:center;padding:20px">'
    body += '<div style="padding:35px;max-width:420px;width:100%;background:linear-gradient(135deg,#1a1410,#0a0805);border:1px solid #d4af37;border-radius:20px;box-shadow:0 20px 60px rgba(212,175,55,.2)">'
    body += '<div style="text-align:center;margin-bottom:25px">'
    body += '<div style="font-size:64px">WAITER</div>'
    body += '<h2 style="color:#f0b34e;margin:10px 0 5px;font-size:24px">Waiter Login</h2>'
    body += '<p style="color:#888;font-size:12px;letter-spacing:2px;margin:0">FIKIR COFFEE HOUSE</p>'
    body += '</div>'
    body += error
    body += '<form method="post">'
    body += '<label style="display:block;color:#aaa;font-size:13px;margin-bottom:6px">Password</label>'
    body += '<input type="password" name="password" required autofocus placeholder="Enter waiter password" style="width:100%;padding:12px;background:#0a0805;border:1px solid #2a2018;color:#fff;border-radius:10px;font-size:15px;margin-bottom:18px;box-sizing:border-box">'
    body += '<button type="submit" class="btn" style="width:100%;padding:14px;font-size:15px;font-weight:bold">Login</button>'
    body += '</form>'
    body += '<p style="text-align:center;color:#555;font-size:11px;margin-top:20px">Waiters Only</p>'
    body += '</div></div>'
    
    return render_template_string(BASE, body=body, page="waiter_login", title="Waiter Login", cart_count=cart_data()[0])


@app.route("/waiter/logout")
def waiter_logout():
    session.pop("waiter_logged_in", None)
    session.pop("waiter_table", None)
    session.pop("waiter_cart", None)
    return redirect(url_for("waiter_login"))


@app.route("/waiter")
def waiter_dashboard():
    if not session.get("waiter_logged_in"):
        return redirect(url_for("waiter_login"))
    
    body = '<div class="formbox" style="padding:25px">'
    body += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    body += '<div><h1 style="color:#f0b34e;margin:0">Waiter Dashboard</h1>'
    body += '<p style="color:#aaa;margin:5px 0 0;font-size:13px">Select a table to take order</p></div>'
    body += '<a class="btn" href="/waiter/logout" style="background:#e74c3c;color:#fff">Logout</a>'
    body += '</div>'
    
    # Table grid 1-20
    body += '<h3 style="color:#f0b34e;margin:20px 0 15px">Select Table</h3>'
    body += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:12px">'
    for i in range(1, 21):
        body += '<a href="/waiter/table/' + str(i) + '" style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px 10px;background:#0a0805;border:2px solid #2a2018;border-radius:12px;text-decoration:none;transition:all .3s">'
        body += '<div style="font-size:32px;margin-bottom:5px">TABLE</div>'
        body += '<div style="color:#f0b34e;font-size:24px;font-weight:bold">' + str(i) + '</div>'
        body += '</a>'
    body += '</div>'
    
    body += '</div>'
    
    return render_template_string(BASE, body=body, page="waiter_dashboard", title="Waiter", cart_count=cart_data()[0])


@app.route("/waiter/table/<int:table_no>")
def waiter_table(table_no):
    if not session.get("waiter_logged_in"):
        return redirect(url_for("waiter_login"))
    
    session["waiter_table"] = table_no
    session["waiter_cart"] = {}  # Reset cart for new table
    
    return redirect(url_for("waiter_menu"))


@app.route("/waiter/menu")
def waiter_menu():
    if not session.get("waiter_logged_in"):
        return redirect(url_for("waiter_login"))
    
    table_no = session.get("waiter_table")
    if not table_no:
        return redirect(url_for("waiter_dashboard"))
    
    cart = session.get("waiter_cart", {})
    products = get_products()
    cart_count = sum(cart.values())
    
    body = '<div class="formbox" style="padding:25px">'
    body += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px">'
    body += '<div><h1 style="color:#f0b34e;margin:0">Table ' + str(table_no) + '</h1>'
    body += '<p style="color:#aaa;margin:5px 0 0;font-size:13px">Tap items to add to cart</p></div>'
    body += '<div style="display:flex;gap:8px">'
    body += '<a class="btn" href="/waiter/cart" style="background:#4caf50;color:#fff">Cart (' + str(cart_count) + ')</a>'
    body += '<a class="btn secondary" href="/waiter">Change Table</a>'
    body += '</div>'
    body += '</div>'
    
    body += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px">'
    for p in products:
        qty = cart.get(str(p["id"]), 0)
        border = "2px solid #4caf50" if qty > 0 else "2px solid #2a2018"
        body += '<form method="post" action="/waiter/add" style="display:contents">'
        body += '<input type="hidden" name="product_id" value="' + str(p["id"]) + '">'
        body += '<button type="submit" style="padding:15px 10px;background:#0a0805;border:' + border + ';border-radius:12px;text-align:center;cursor:pointer;transition:all .3s;color:inherit">'
        body += '<div style="font-size:36px;margin-bottom:8px">' + (p.get("icon") or "CUP") + '</div>'
        body += '<div style="color:#fff;font-weight:bold;font-size:14px;margin-bottom:4px">' + p["name"] + '</div>'
        body += '<div style="color:#f0b34e;font-weight:bold;font-size:16px">ETB ' + str(p["price"]) + '</div>'
        if qty > 0:
            body += '<div style="background:#4caf50;color:#fff;padding:3px 8px;border-radius:10px;font-size:12px;margin-top:6px;font-weight:bold">x' + str(qty) + '</div>'
        body += '</button>'
        body += '</form>'
    body += '</div>'
    body += '</div>'
    
    return render_template_string(BASE, body=body, page="waiter_menu", title="Table " + str(table_no), cart_count=cart_count)


@app.route("/waiter/add", methods=["POST"])
def waiter_add():
    if not session.get("waiter_logged_in"):
        return redirect(url_for("waiter_login"))
    pid = request.form.get("product_id", type=int)
    if not pid:
        return redirect(url_for("waiter_menu"))
    cart = session.get("waiter_cart", {})
    key = str(pid)
    cart[key] = int(cart.get(key, 0)) + 1
    session["waiter_cart"] = cart
    return redirect(url_for("waiter_menu"))


@app.route("/waiter/remove", methods=["POST"])
def waiter_remove():
    if not session.get("waiter_logged_in"):
        return redirect(url_for("waiter_login"))
    pid = request.form.get("product_id", type=int)
    cart = session.get("waiter_cart", {})
    if pid and str(pid) in cart:
        del cart[str(pid)]
    session["waiter_cart"] = cart
    return redirect(url_for("waiter_cart"))


@app.route("/waiter/cart")
def waiter_cart():
    if not session.get("waiter_logged_in"):
        return redirect(url_for("waiter_login"))
    table_no = session.get("waiter_table")
    if not table_no:
        return redirect(url_for("waiter_dashboard"))
    
    cart = session.get("waiter_cart", {})
    products = get_products()
    pmap = {str(p["id"]): p for p in products}
    
    items = []
    total = 0
    for pid, qty in cart.items():
        if pid in pmap:
            p = pmap[pid]
            sub = p["price"] * qty
            total += sub
            items.append({"id": pid, "name": p["name"], "price": p["price"], "qty": qty, "icon": p.get("icon") or "CUP", "subtotal": sub})
    
    body = '<div class="formbox" style="padding:25px">'
    body += '<h1 style="color:#f0b34e;margin:0 0 5px">Table ' + str(table_no) + ' Cart</h1>'
    body += '<p style="color:#aaa;margin:0 0 20px;font-size:13px">Review order before sending to kitchen</p>'
    
    if not items:
        body += '<div style="text-align:center;padding:40px;color:#888">'
        body += '<div style="font-size:48px;margin-bottom:10px">CART</div>'
        body += '<p>Cart is empty</p>'
        body += '<a class="btn" href="/waiter/menu">Add Items</a>'
        body += '</div>'
    else:
        for it in items:
            body += '<div style="display:flex;align-items:center;gap:12px;padding:12px;background:#0a0805;border:1px solid #2a2018;border-radius:10px;margin-bottom:8px">'
            body += '<div style="font-size:28px">' + it["icon"] + '</div>'
            body += '<div style="flex:1"><div style="color:#fff;font-weight:bold">' + it["name"] + '</div>'
            body += '<div style="color:#aaa;font-size:12px">ETB ' + str(it["price"]) + ' each</div></div>'
            body += '<div style="color:#f0b34e;font-weight:bold;font-size:18px;margin-right:10px">x' + str(it["qty"]) + '</div>'
            body += '<div style="color:#f0b34e;font-weight:bold;min-width:70px;text-align:right">ETB ' + str(it["subtotal"]) + '</div>'
            body += '<form method="post" action="/waiter/remove" style="margin:0">'
            body += '<input type="hidden" name="product_id" value="' + it["id"] + '">'
            body += '<button type="submit" style="background:transparent;border:0;color:#e74c3c;font-size:20px;cursor:pointer;padding:4px">X</button>'
            body += '</form>'
            body += '</div>'
        
        body += '<div style="display:flex;justify-content:space-between;padding:15px;background:#1a1410;border-radius:10px;margin:15px 0;font-size:20px;font-weight:bold">'
        body += '<span style="color:#aaa">TOTAL:</span>'
        body += '<span style="color:#f0b34e">ETB ' + str(total) + '</span>'
        body += '</div>'
        
        body += '<form method="post" action="/waiter/place-order">'
        body += '<button type="submit" class="btn" style="width:100%;padding:16px;font-size:16px;font-weight:bold;background:#4caf50;color:#fff">Send to Kitchen</button>'
        body += '</form>'
        
        body += '<div style="display:flex;gap:8px;margin-top:10px">'
        body += '<a class="btn secondary" href="/waiter/menu" style="flex:1;text-align:center">Add More</a>'
        body += '<a class="btn secondary" href="/waiter" style="flex:1;text-align:center">Change Table</a>'
        body += '</div>'
    
    body += '</div>'
    
    return render_template_string(BASE, body=body, page="waiter_cart", title="Cart", cart_count=len(cart))


@app.route("/waiter/place-order", methods=["POST"])
def waiter_place_order():
    if not session.get("waiter_logged_in"):
        return redirect(url_for("waiter_login"))
    table_no = session.get("waiter_table")
    if not table_no:
        return redirect(url_for("waiter_dashboard"))
    
    cart = session.get("waiter_cart", {})
    if not cart:
        return redirect(url_for("waiter_cart"))
    
    products = get_products()
    pmap = {str(p["id"]): p for p in products}
    
    items = []
    total = 0
    for pid, qty in cart.items():
        if pid in pmap:
            p = pmap[pid]
            sub = p["price"] * qty
            total += sub
            items.append(p["name"] + " x " + str(qty))
    
    item_text = ", ".join(items)
    customer = "Waiter"
    created_at = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = db()
    cur = conn.execute(
        "INSERT INTO fikir_orders (customer, table_no, items, total, status, created_at) VALUES (?,?,?,?,?,?)",
        (customer, str(table_no), item_text, total, "NEW", created_at)
    )
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    # Send notification
    try:
        send_telegram("NEW ORDER #" + str(order_id) + " - Table " + str(table_no) + " - ETB " + str(total) + " - " + item_text)
    except Exception:
        pass
    
    session["waiter_cart"] = {}
    
    return redirect(url_for("waiter_success", order_id=order_id))


@app.route("/waiter/success/<int:order_id>")
def waiter_success(order_id):
    if not session.get("waiter_logged_in"):
        return redirect(url_for("waiter_login"))
    
    body = '<div class="formbox" style="padding:30px;text-align:center;max-width:500px;margin:50px auto">'
    body += '<div style="font-size:64px;margin-bottom:15px">OK</div>'
    body += '<h1 style="color:#4caf50;margin:0 0 10px">Order Sent!</h1>'
    body += '<p style="color:#f0b34e;font-size:20px;font-weight:bold;margin:10px 0">Order #' + str(order_id) + '</p>'
    body += '<p style="color:#aaa;margin:15px 0">Kitchen has been notified</p>'
    body += '<div style="display:flex;gap:10px;justify-content:center;margin-top:20px;flex-wrap:wrap">'
    body += '<a class="btn" href="/waiter" style="background:#4caf50;color:#fff">New Table</a>'
    body += '<a class="btn secondary" href="/waiter/menu">Same Table</a>'
    body += '</div>'
    body += '</div>'
    
    return render_template_string(BASE, body=body, page="waiter_success", title="Order Sent", cart_count=0)



def _init_sqlite():
    """Create tables if using SQLite fallback"""
    if SUPABASE_URL and SUPABASE_KEY:
        return  # Skip - using Supabase
    try:
        conn = sqlite3.connect("coffee.db")
        conn.execute("""CREATE TABLE IF NOT EXISTS fikir_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price INTEGER NOT NULL,
            icon TEXT NOT NULL DEFAULT 'CUP',
            stock INTEGER NOT NULL DEFAULT 0,
            low_stock INTEGER NOT NULL DEFAULT 5
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS fikir_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            table_no TEXT NOT NULL,
            items TEXT NOT NULL,
            total INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'NEW',
            created_at TEXT NOT NULL,
            payment_method TEXT,
            payment_ref TEXT,
            payment_status TEXT DEFAULT 'UNPAID'
        )""")
        # Seed only if empty
        cnt = conn.execute("SELECT COUNT(*) FROM fikir_products").fetchone()[0]
        if cnt == 0:
            seed = [
                ("Espresso", "Strong and rich coffee", 50, "☕", 50, 5),
                ("Cappuccino", "Smooth and creamy", 50, "☕", 50, 5),
                ("Latte", "Rich milk coffee", 55, "🥛", 50, 5),
                ("Americano", "Classic black coffee", 45, "☕", 50, 5),
                ("Mocha", "Chocolate & coffee blend", 60, "🍫", 50, 5),
                ("Caramel Macchiato", "Sweet and rich", 60, "🍮", 50, 5),
                ("Cold Coffee", "Refreshingly cold", 55, "🧊", 50, 5),
                ("Hot Chocolate", "Rich chocolate drink", 50, "🍫", 50, 5),
                ("Macchiato", "Rich espresso with milk", 70, "☕", 50, 5),
                ("ጥቁር", "ጥቁር ቡና", 300, "☕", 50, 5),
                ("Tea", "Ethiopian traditional tea", 30, "🍵", 50, 5),
                ("Coffee", "Steam coffee", 40, "☕", 50, 5),
                ("Milk", "Pure milk", 50, "🥛", 50, 5),
            ]
            for p in seed:
                conn.execute("INSERT INTO fikir_products (name, description, price, icon, stock, low_stock) VALUES (?,?,?,?,?,?)", p)
        conn.commit()
        conn.close()
        print("[INIT] SQLite ready")
    except Exception as e:
        print("[INIT ERROR]", e)

# Call on startup
_init_sqlite()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
