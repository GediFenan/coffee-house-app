# ═══════════════════════════════════════════════
# FIKIR — Customer QR Menu
# Customers scan QR at table → self-order
# Blueprint: /menu/*, /qr/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, requests, io, base64
from datetime import datetime, timezone

try:
    import qrcode
    from qrcode.image.pil import PilImage
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False
    print("[QR] qrcode library not installed — using fallback")

qr_menu_bp = Blueprint("qr_menu", __name__)

SUPABASE_URL = "https://skswircyorzpbcioljcs.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrc3dpcmN5b3J6cGJjaW9samNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MjMyMzQsImV4cCI6MjEwMzQ5OTIzNH0.ntS52ih33wprDiQ4YGrNzWchuuWqfzc1iyv7_xi_qPM"

def _headers(prefer=None):
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    if prefer: h["Prefer"] = prefer
    return h

def _get(url):
    try:
        r = requests.get(url, headers=_headers(), timeout=30)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []

def _qr_data_uri(url, size=200):
    """Generate QR as base64 data URI (works with print!)"""
    if not HAS_QRCODE:
        return None
    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#3b1f0b", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print("[QR GEN ERR]", e)
        return None

def _products(category_id=None):
    """Get active products, optionally filtered by category"""
    base = f"{SUPABASE_URL}/rest/v1/fikir_products?select=id,name,price,icon,description,category_id"
    if category_id:
        url = f"{base}&category_id=eq.{category_id}&order=name.asc"
    else:
        url = f"{base}&order=name.asc"
    result = _get(url)
    if not result:
        # Fallback — no is_active filter
        url2 = url.replace("&is_active=eq.true", "")
        result = _get(url2)
    return result

def _categories():
    """Get active categories for QR menu"""
    return _get(f"{SUPABASE_URL}/rest/v1/fikir_categories?is_active=eq.true&select=*&order=sort_order.asc")

def _tables():
    """Get list of tables (from a simple range 1-20)"""
    return list(range(1, 21))

def _cart_key(table_no):
    return f"qr_cart_{table_no}"

def _cart(table_no):
    return session.get(_cart_key(table_no), {})

def _cart_total(table_no):
    c = _cart(table_no)
    return sum(float(i["price"]) * int(i["qty"]) for i in c.values())

# ═══════════════════════════════════════════════
# CUSTOMER MENU PAGE
# ═══════════════════════════════════════════════
MENU_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#6b3e1e">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="manifest" href="/manifest.json">
<title>FIKIR Menu — Table {{ table_no }}</title>
<style>
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:120px}
  .top{background:linear-gradient(135deg,#3b1f0b,#6b3e1e);color:#fff;padding:16px 18px;position:sticky;top:0;z-index:10;box-shadow:0 4px 16px rgba(0,0,0,.2)}
  .top h1{margin:0;font-size:18px;display:flex;align-items:center;gap:8px}
  .top .table{background:rgba(255,255,255,.2);padding:4px 12px;border-radius:20px;font-size:12px;font-weight:800}
  .top .sub{font-size:11px;opacity:.85;margin-top:4px}
  .hero{padding:16px;text-align:center;background:linear-gradient(180deg,#fff8e8 0%,#f5ece0 100%)}
  .hero h2{margin:0;font-size:22px;color:#6b3e1e}
  .hero p{margin:6px 0 0;font-size:13px;color:#8a6a4a}
  .cat{padding:14px 16px 6px;font-size:14px;font-weight:800;color:#6b3e1e;text-transform:uppercase;letter-spacing:1px}
  .tabs-bar{display:flex;gap:6px;padding:12px 14px;overflow-x:auto;white-space:nowrap;background:#fff;border-bottom:1px solid #f0e6d8;position:sticky;top:0;z-index:9}
  .tabs-bar::-webkit-scrollbar{display:none}
  .tab{padding:8px 14px;background:#f5ece0;color:#6b3e1e;border-radius:20px;text-decoration:none;font-size:12px;font-weight:700;white-space:nowrap;flex-shrink:0}
  .tab.active{background:#6b3e1e;color:#fff}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:14px}
  .p{background:#fff;border-radius:14px;padding:14px;text-align:center;cursor:pointer;border:2px solid transparent;transition:.15s;position:relative}
  .p:active{transform:scale(.97);border-color:#6b3e1e}
  .p .ico{font-size:34px;display:block;margin-bottom:6px}
  .p .nm{font-size:13px;font-weight:700;line-height:1.3}
  .p .pr{font-size:15px;color:#6b3e1e;font-weight:800;margin-top:6px}
  .p .qty-badge{position:absolute;top:8px;right:8px;background:#2a7d2a;color:#fff;font-size:11px;font-weight:800;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center}
  .bar{position:fixed;bottom:0;left:0;right:0;background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 -4px 20px rgba(0,0,0,.25);padding-bottom:calc(14px + env(safe-area-inset-bottom))}
  .bar .cnt{font-size:11px;opacity:.85}
  .bar .tot{font-size:22px;font-weight:800}
  .bar a{background:#d4a24c;color:#3b1f0b;text-decoration:none;padding:12px 22px;border-radius:12px;font-weight:800;font-size:14px}
  .bar a:active{transform:scale(.97)}
  .empty{text-align:center;padding:60px 20px;color:#8a6a4a}
</style></head><body>
<div class="top">
  <h1>☕ FIKIR COFFEE HOUSE <span class="table">Table {{ table_no }}</span></h1>
  <div class="sub">ምናሌውን ይመልከቱ · ትዕዛዝዎን በራስዎ ይስጡ</div>
</div>
<div class="hero">
  <h2>እንኳን ደህና መጡ! 🙏</h2>
  <p>ምርቱን ተጭነው ወደ cart ይጨምሩ</p>
</div>
<div class="tabs-bar">
  <a class="tab {% if active_cat == 'all' %}active{% endif %}" href="{{ url_for('qr_menu.menu', table_no=table_no) }}">ሁሉም ({{ total_products }})</a>
  {% for c in categories %}
  <a class="tab {% if active_cat == c.id|string %}active{% endif %}" href="{{ url_for('qr_menu.menu', table_no=table_no, cat=c.id) }}">{{ c.icon }} {{ c.name }} ({{ cat_counts.get(c.id, 0) }})</a>
  {% endfor %}
</div>

<div class="grid">
  {% for p in products %}
  <form method="POST" action="{{ url_for('qr_menu.add', table_no=table_no) }}" style="margin:0">
    <input type="hidden" name="product_id" value="{{ p.id }}">
    <div class="p" onclick="this.parentElement.submit()">
      {% if cart.get(p.id|string) %}<span class="qty-badge">{{ cart[p.id|string].qty }}</span>{% endif %}
      <span class="ico">{{ p.icon or '☕' }}</span>
      <div class="nm">{{ p.name }}</div>
      <div class="pr">{{ p.price }} ETB</div>
    </div>
  </form>
  {% endfor %}
</div>
{% if not products %}
<div class="empty">😔 ምንም ምርት አልተገኘም</div>
{% endif %}

{% if cart_count > 0 %}
<div class="bar">
  <div>
    <div class="cnt">{{ cart_count }} item(s)</div>
    <div class="tot">{{ "%.2f"|format(cart_total) }} ETB</div>
  </div>
  <a href="{{ url_for('qr_menu.cart', table_no=table_no) }}">🛒 Cart →</a>
</div>
{% endif %}
</body></html>
"""

@qr_menu_bp.route("/menu/<int:table_no>")
def menu(table_no):
    if table_no < 1 or table_no > 50:
        return "Invalid table", 404
    categories = _categories()
    all_products = _products()
    cart = _cart(table_no)

    # Category filter
    active_cat = request.args.get("cat", "all")
    if active_cat == "all":
        products = all_products
    else:
        try:
            cid = int(active_cat)
            products = [p for p in all_products if p.get("category_id") == cid]
        except (ValueError, TypeError):
            products = all_products

    cat_counts = {}
    for c in categories:
        cat_counts[c["id"]] = sum(1 for p in all_products if p.get("category_id") == c["id"])

    return render_template_string(MENU_HTML,
        products=products, categories=categories,
        active_cat=active_cat, cat_counts=cat_counts,
        total_products=len(all_products),
        table_no=table_no, cart=cart,
        cart_count=sum(int(i["qty"]) for i in cart.values()),
        cart_total=_cart_total(table_no))

@qr_menu_bp.route("/menu/<int:table_no>/add", methods=["POST"])
def add(table_no):
    pid = str(request.form.get("product_id"))
    products = _products()
    prod = next((p for p in products if str(p["id"]) == pid), None)
    if not prod:
        return redirect(url_for("qr_menu.menu", table_no=table_no))
    cart = _cart(table_no)
    if pid in cart:
        cart[pid]["qty"] += 1
    else:
        cart[pid] = {"name": prod["name"], "price": float(prod["price"]),
                     "icon": prod.get("icon","☕"), "qty": 1}
    session[_cart_key(table_no)] = cart
    session.modified = True
    return redirect(url_for("qr_menu.menu", table_no=table_no))

# ═══════════════════════════════════════════════
# CART PAGE
# ═══════════════════════════════════════════════
CART_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#6b3e1e">
<title>Cart — Table {{ table_no }}</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:130px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:14px;max-width:560px;margin:0 auto}
  .card{background:#fff;border-radius:14px;padding:8px 16px;margin-bottom:12px;box-shadow:0 2px 8px rgba(107,62,30,.06)}
  .row{display:flex;justify-content:space-between;align-items:center;padding:14px 0;border-bottom:1px solid #f5ece0}
  .row:last-child{border-bottom:none}
  .row .nm{font-weight:700;font-size:14px}
  .row .pr{font-size:12px;color:#8a6a4a;margin-top:3px}
  .qty{display:flex;align-items:center;gap:8px}
  .qty button{width:32px;height:32px;border-radius:8px;border:none;font-size:18px;font-weight:700;cursor:pointer;background:#f5ece0;color:#6b3e1e}
  .qty span{min-width:20px;text-align:center;font-weight:800}
  .tot{display:flex;justify-content:space-between;font-size:20px;font-weight:800;color:#6b3e1e;padding:16px 0;border-top:2px solid #6b3e1e;margin-top:6px}
  .bar{position:fixed;bottom:0;left:0;right:0;background:#6b3e1e;color:#fff;padding:14px 18px;box-shadow:0 -4px 20px rgba(0,0,0,.25);padding-bottom:calc(14px + env(safe-area-inset-bottom))}
  .bar button{width:100%;padding:16px;background:#d4a24c;color:#3b1f0b;border:none;border-radius:12px;font-size:16px;font-weight:800;cursor:pointer}
  .bar button:active{transform:scale(.98)}
  .empty{text-align:center;padding:60px 20px;color:#8a6a4a}
  input[type=text]{width:100%;padding:14px;border:2px solid #e0d0c0;border-radius:10px;font-size:15px;outline:none;background:#fff;font-family:inherit;margin-bottom:10px}
  input[type=text]:focus{border-color:#6b3e1e}
  label{display:block;font-size:12px;font-weight:700;color:#5a3a1e;margin-bottom:6px;margin-top:10px}
</style></head><body>
<div class="top">
  <h1>🛒 Table {{ table_no }} — Cart</h1>
  <a href="{{ url_for('qr_menu.menu', table_no=table_no) }}">← Menu</a>
</div>
<div class="wrap">
  {% if items %}
  <div class="card">
    {% for key, item in items %}
    <div class="row">
      <div>
        <div class="nm">{{ item.icon }} {{ item.name }}</div>
        <div class="pr">{{ "%.2f"|format(item.price) }} ETB</div>
      </div>
      <div class="qty">
        <form method="POST" action="{{ url_for('qr_menu.remove', table_no=table_no) }}" style="margin:0">
          <input type="hidden" name="product_id" value="{{ key }}">
          <button type="submit">−</button>
        </form>
        <span>{{ item.qty }}</span>
        <form method="POST" action="{{ url_for('qr_menu.add', table_no=table_no) }}" style="margin:0">
          <input type="hidden" name="product_id" value="{{ key }}">
          <button type="submit">+</button>
        </form>
      </div>
      <div style="font-weight:800;min-width:80px;text-align:right">{{ "%.2f"|format(item.price * item.qty) }} ETB</div>
    </div>
    {% endfor %}
    <div class="tot"><span>Total</span><span>{{ "%.2f"|format(cart_total) }} ETB</span></div>
  </div>

  <form method="POST" action="{{ url_for('qr_menu.place', table_no=table_no) }}">
    <div class="card" style="padding:16px">
      <label>ስምዎ (optional)</label>
      <input type="text" name="customer" placeholder="ለምሳሌ: Abebe" autocomplete="off">
      <label>ማስታወሻ (optional)</label>
      <input type="text" name="note" placeholder="ለምሳሌ: sugar ያነሰ" autocomplete="off">
    </div>
    <div class="bar">
      <button type="submit">✅ ትዕዛዝ አረጋግጥ · {{ "%.2f"|format(cart_total) }} ETB</button>
    </div>
  </form>
  {% else %}
  <div class="empty">🛒 Cart ባዶ ነው</div>
  <div style="text-align:center;margin-top:20px">
    <a href="{{ url_for('qr_menu.menu', table_no=table_no) }}" style="display:inline-block;background:#6b3e1e;color:#fff;text-decoration:none;padding:14px 28px;border-radius:12px;font-weight:700">☕ Menu ተመለስ</a>
  </div>
  {% endif %}
</div>
</body></html>
"""

@qr_menu_bp.route("/menu/<int:table_no>/cart")
def cart(table_no):
    cart_data = _cart(table_no)
    items = list(cart_data.items())
    return render_template_string(CART_HTML,
        items=items, table_no=table_no,
        cart_total=_cart_total(table_no))

@qr_menu_bp.route("/menu/<int:table_no>/remove", methods=["POST"])
def remove(table_no):
    pid = str(request.form.get("product_id"))
    cart_data = _cart(table_no)
    if pid in cart_data:
        cart_data[pid]["qty"] -= 1
        if cart_data[pid]["qty"] <= 0:
            del cart_data[pid]
    session[_cart_key(table_no)] = cart_data
    session.modified = True
    return redirect(url_for("qr_menu.cart", table_no=table_no))

# ═══════════════════════════════════════════════
# PLACE ORDER
# ═══════════════════════════════════════════════
SUCCESS_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#6b3e1e">
<title>Order Placed — FIKIR</title>
<style>
  body{margin:0;font-family:system-ui,sans-serif;background:linear-gradient(135deg,#6b3e1e,#3b1f0b);color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
  .box{background:#fff;color:#3b1f0b;border-radius:20px;padding:32px 24px;max-width:380px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.4)}
  .ok{font-size:64px;margin-bottom:8px}
  h1{margin:0 0 8px;font-size:24px;color:#2a7d2a}
  .sub{color:#8a6a4a;font-size:14px;margin-bottom:20px;line-height:1.6}
  .order{background:#f5ece0;border-radius:12px;padding:16px;margin:20px 0}
  .order .row{display:flex;justify-content:space-between;padding:6px 0;font-size:13px}
  .order .id{font-weight:800;color:#6b3e1e;font-size:18px}
  .tot{display:flex;justify-content:space-between;padding-top:12px;border-top:2px solid #6b3e1e;margin-top:8px;font-weight:800;font-size:17px}
  .actions a{display:block;padding:14px;text-decoration:none;border-radius:12px;font-weight:700;font-size:15px;margin-top:10px}
  .actions .a1{background:#6b3e1e;color:#fff}
  .actions .a2{background:#fff;color:#6b3e1e;border:2px solid #6b3e1e}
</style></head><body>
<div class="box">
  <div class="ok">✅</div>
  <h1>ትዕዛዝ ተልኳል!</h1>
  <div class="sub">ትዕዛዝዎ ወደ ኩሽና ተልኳል።<br>በቅርብ ጊዜ ይደርስዎታል።</div>

  <div class="order">
    <div class="row"><span>Order #</span><span class="id">#{{ order.id }}</span></div>
    <div class="row"><span>Table</span><span><b>{{ table_no }}</b></span></div>
    <div class="row"><span>Customer</span><span>{{ order.customer }}</span></div>
    <div class="tot"><span>TOTAL</span><span>{{ "%.2f"|format(order.total|float) }} ETB</span></div>
  </div>

  <div class="actions">
    <a class="a1" href="{{ url_for('qr_menu.track', table_no=table_no, order_id=order.id) }}">📍 ትዕዛዜን ተከታተል</a>
    <a class="a2" href="{{ url_for('qr_menu.menu', table_no=table_no) }}">➕ ሌላ ጨምር</a>
  </div>
</div>
</body></html>
"""

@qr_menu_bp.route("/menu/<int:table_no>/place", methods=["POST"])
def place(table_no):
    cart_data = _cart(table_no)
    if not cart_data:
        return redirect(url_for("qr_menu.menu", table_no=table_no))

    customer = (request.form.get("customer") or f"Table {table_no}").strip()[:80]
    note = (request.form.get("note") or "").strip()[:200]
    items_text = ", ".join(f"{i['qty']}× {i['name']}" for i in cart_data.values())
    if note:
        items_text += f" ({note})"
    total = _cart_total(table_no)

    order_payload = {
        "customer": customer,
        "table_no": str(table_no),
        "items": items_text,
        "total": round(float(total), 2),
        "subtotal": round(float(total), 2),
        "discount": 0,
        "status": "NEW",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payment_method": "cash",
        "payment_status": "UNPAID",
    }

    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/fikir_orders",
                         json=order_payload, headers=_headers("return=representation"), timeout=30)
        if r.status_code not in (200, 201):
            return f"ስህተት: {r.text[:300]}", 500
        order = r.json()[0]

        # Telegram notify
        try:
            from notifications_routes import notify_new_order
            notify_new_order(
                order_id=order["id"],
                customer=customer,
                items=items_text,
                total=total,
                method="cash",
                cashier=f"QR · Table {table_no}",
                base_url=request.host_url.rstrip("/"),
                table_no=str(table_no)
            )
        except Exception as e:
            print("[QR TG ERR]", e)

    except Exception as e:
        return f"ስህተት: {str(e)[:200]}", 500

    # Clear cart
    session[_cart_key(table_no)] = {}
    session.modified = True

    return render_template_string(SUCCESS_HTML, order=order, table_no=table_no)

# ═══════════════════════════════════════════════
# TRACK ORDER
# ═══════════════════════════════════════════════
TRACK_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#6b3e1e">
<title>Track #{{ order.id }}</title>
<style>
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding:20px}
  .wrap{max-width:480px;margin:0 auto}
  .card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 4px 16px rgba(107,62,30,.08);margin-bottom:14px}
  h1{margin:0;font-size:20px}
  .sub{color:#8a6a4a;font-size:13px;margin-top:4px}
  .stage{display:flex;flex-direction:column;gap:0;margin-top:20px}
  .step{display:flex;gap:12px;align-items:flex-start;padding:12px 0}
  .step .dot{width:34px;height:34px;border-radius:50%;background:#f0e6d8;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;position:relative}
  .step.active .dot{background:#2a7d2a;color:#fff;box-shadow:0 0 0 4px rgba(42,125,42,.2)}
  .step.current .dot{background:#d4a24c;color:#3b1f0b;animation:pulse 1.5s infinite}
  @keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(212,162,76,.6)}50%{box-shadow:0 0 0 10px rgba(212,162,76,0)}}
  .step .info{flex:1;padding-top:4px}
  .step .nm{font-weight:700;font-size:14px}
  .step .desc{font-size:12px;color:#8a6a4a;margin-top:2px}
  .items{background:#f5ece0;border-radius:10px;padding:12px;font-size:13px;line-height:1.7;margin-top:12px}
  .tot{display:flex;justify-content:space-between;padding-top:12px;border-top:2px solid #6b3e1e;margin-top:12px;font-weight:800;font-size:17px}
  .act{margin-top:20px;text-align:center}
  .act a{display:inline-block;background:#6b3e1e;color:#fff;padding:14px 28px;border-radius:12px;text-decoration:none;font-weight:700}
  .status-badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:800;letter-spacing:.5px;text-transform:uppercase}
  .badge-NEW{background:#fff3cd;color:#8a6a00}
  .badge-PREPARING{background:#ffe0b2;color:#a05000}
  .badge-READY{background:#d4edda;color:#1e7e34}
  .badge-DELIVERED{background:#d4edda;color:#1e7e34}
  .badge-PAID{background:#d4edda;color:#1e7e34}
</style></head><body>
<div class="wrap">
  <div class="card">
    <h1>Order #{{ order.id }} <span class="status-badge badge-{{ order.status }}">{{ order.status }}</span></h1>
    <div class="sub">Table {{ table_no }} · {{ order.customer }}</div>
    <div class="stage">
      {% set active1 = order.status in ['NEW','PAID','PREPARING','READY','DELIVERED'] %}
      {% set active2 = order.status in ['PREPARING','READY','DELIVERED'] %}
      {% set active3 = order.status in ['READY','DELIVERED'] %}
      {% set active4 = order.status == 'DELIVERED' %}
      <div class="step {{ 'active' if active1 else '' }} {{ 'current' if order.status in ['NEW','PAID'] else '' }}">
        <div class="dot">📝</div>
        <div class="info"><div class="nm">ትዕዛዝ ተቀብሏል</div><div class="desc">ኩሽና ትዕዛዙን አይቷል</div></div>
      </div>
      <div class="step {{ 'active' if active2 else '' }} {{ 'current' if order.status == 'PREPARING' else '' }}">
        <div class="dot">👨‍🍳</div>
        <div class="info"><div class="nm">በመዘጋጀት ላይ</div><div class="desc">ባሪስታ እያዘጋጀ ነው</div></div>
      </div>
      <div class="step {{ 'active' if active3 else '' }} {{ 'current' if order.status == 'READY' else '' }}">
        <div class="dot">✅</div>
        <div class="info"><div class="nm">ዝግጁ ነው</div><div class="desc">ወደ ጠረጴዛዎ እየመጣ ነው</div></div>
      </div>
      <div class="step {{ 'active' if active4 else '' }}">
        <div class="dot">🎉</div>
        <div class="info"><div class="nm">ተላልፏል</div><div class="desc">እንደገና ይመጡ!</div></div>
      </div>
    </div>
    <div class="items">{{ order.items }}</div>
    <div class="tot"><span>TOTAL</span><span>{{ "%.2f"|format(order.total|float) }} ETB</span></div>
  </div>
  <div class="act">
    <a href="{{ url_for('qr_menu.track', table_no=table_no, order_id=order.id) }}">🔄 አድስ</a>
  </div>
</div>
<script>setTimeout(()=>location.reload(),15000);</script>
</body></html>
"""

@qr_menu_bp.route("/menu/<int:table_no>/track/<int:order_id>")
def track(table_no, order_id):
    r = _get(f"{SUPABASE_URL}/rest/v1/fikir_orders?id=eq.{order_id}&limit=1")
    if not r:
        return "Order አልተገኘም", 404
    return render_template_string(TRACK_HTML, order=r[0], table_no=table_no)

# ═══════════════════════════════════════════════
# QR CODE GENERATOR (for staff)
# ═══════════════════════════════════════════════
QR_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QR Codes — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding:14px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10;margin:-14px -14px 14px;border-radius:0 0 16px 16px}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{max-width:900px;margin:0 auto}
  .hint{background:#fff3cd;border-left:4px solid #f0ad4e;padding:12px;border-radius:8px;font-size:13px;color:#8a6a4a;margin-bottom:14px;line-height:1.6}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}
  .qr{background:#fff;border-radius:12px;padding:16px;text-align:center;box-shadow:0 2px 8px rgba(107,62,30,.08)}
  .qr h3{margin:0 0 8px;font-size:15px;color:#6b3e1e}
  .qr .qr-img{margin:8px auto;display:block;max-width:100%}
  .qr .qr-img img{display:block;width:180px;height:180px;margin:0 auto;image-rendering:pixelated}
  .qr .url{font-size:10px;color:#8a6a4a;word-break:break-all;margin-top:6px;font-family:monospace}
  .actions{text-align:center;margin:20px 0}
  .actions button{background:#6b3e1e;color:#fff;border:none;padding:14px 28px;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer}
  .actions button:active{transform:scale(.98)}
  @media print{
    body{background:#fff;padding:0}
    .top, .hint, .actions{display:none !important}
    .grid{grid-template-columns:repeat(2,1fr);gap:8px}
    .qr{box-shadow:none;border:1px dashed #999;page-break-inside:avoid;padding:10px}
    .qr h3{font-size:13px;margin-bottom:4px}
    .qr .qr-img img{width:160px;height:160px}
    .qr .url{font-size:8px;color:#666}
    @page{size:A4;margin:10mm}
  }
</style>
</head><body>
<div class="top">
  <h1>📱 Table QR Codes</h1>
  <a href="{{ url_for('staff.dashboard') }}">← Back</a>
</div>
<div class="wrap">
  <div class="hint">
    <b>📌 እንዴት እንደሚሰራ:</b><br>
    1️⃣ QR ኮዶቹን አትመው (🖨️ አትም) · 2️⃣ በእያንዳንዱ ጠረጴዛ ላይ ለጥፉ<br>
    3️⃣ ደንበኛው ስካን አድርጎ በራሱ ስልክ ትዕዛዝ ይሰጣል · 4️⃣ ወደ Kitchen + Telegram በራስ-ሰር ይሄዳል
  </div>
  <div class="actions">
    <button onclick="window.print()">🖨️ አትም / Print</button>
  </div>
  <div class="grid">
    {% for item in qr_items %}
    <div class="qr">
      <h3>🍽️ Table {{ item.table_no }}</h3>
      <div class="qr-img">
        {% if item.qr_data %}
          <img src="{{ item.qr_data }}" alt="QR Table {{ item.table_no }}">
        {% else %}
          <div style="color:#c00;font-size:11px;padding:30px 0">⚠️ QR አልተፈጠረም<br>qrcode library install ያስፈልጋል</div>
        {% endif %}
      </div>
      <div class="url">{{ item.url }}</div>
    </div>
    {% endfor %}
  </div>
</div>
</body></html>
"""

@qr_menu_bp.route("/qr/tables")
def qr_tables():
    if session.get("staff_role") not in ("owner","manager","cashier"):
        return redirect(url_for("staff.login"))
    base_url = request.host_url.rstrip("/")
    tables = _tables()
    qr_items = []
    for t in tables:
        url = f"{base_url}/menu/{t}"
        qr_items.append({
            "table_no": t,
            "url": url,
            "qr_data": _qr_data_uri(url),
        })
    return render_template_string(QR_HTML, qr_items=qr_items, base_url=base_url)

@qr_menu_bp.route("/qr/table/<int:table_no>")
def qr_one(table_no):
    base_url = request.host_url.rstrip("/")
    url = f"{base_url}/menu/{table_no}"
    qr_items = [{"table_no": table_no, "url": url, "qr_data": _qr_data_uri(url)}]
    return render_template_string(QR_HTML, qr_items=qr_items, base_url=base_url)
