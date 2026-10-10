# ═══════════════════════════════════════════════
# FIKIR — POS (Point of Sale)
# Blueprint: /pos/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, hashlib, requests
from datetime import datetime, timezone

pos_bp = Blueprint("pos", __name__, url_prefix="/pos")

SUPABASE_URL = "https://skswircyorzpbcioljcs.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrc3dpcmN5b3J6cGJjaW9samNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MjMyMzQsImV4cCI6MjEwMzQ5OTIzNH0.ntS52ih33wprDiQ4YGrNzWchuuWqfzc1iyv7_xi_qPM"

def _headers(prefer=None):
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    if prefer: h["Prefer"] = prefer
    return h

def _current_staff():
    if "staff_id" not in session: return None
    return {"id": session.get("staff_id"), "username": session.get("staff_username"),
            "full_name": session.get("staff_name"), "role": session.get("staff_role")}

def _require(fn):
    def inner(*a, **kw):
        s = _current_staff()
        if not s:
            return redirect(url_for("staff.login"))
        if s["role"] not in ("owner","manager","cashier","barista"):
            return "403 Forbidden", 403
        return fn(*a, **kw)
    inner.__name__ = fn.__name__
    return inner

def _get_products():
    url = f"{SUPABASE_URL}/rest/v1/fikir_products?select=*&order=name.asc"
    try:
        r = requests.get(url, headers=_headers(), timeout=30)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print("[PRODUCTS ERROR]", e)
        return []

def _get_open_shift(user_id):
    url = f"{SUPABASE_URL}/rest/v1/fikir_shifts?user_id=eq.{user_id}&status=eq.open&order=opened_at.desc&limit=1"
    try:
        r = requests.get(url, headers=_headers(), timeout=30)
        return r.json()[0] if (r.status_code==200 and r.json()) else None
    except Exception as e:
        print("[SHIFT ERROR]", e)
        return None

def _cart():
    return session.get("pos_cart", {})

def _save_cart(c): session["pos_cart"] = c

def _cart_total():
    c = _cart()
    return sum(float(i["price"]) * int(i["qty"]) for i in c.values())

# ─────────── POS MAIN UI ───────────
POS_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>POS — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:80px}
  .top{background:#6b3e1e;color:#fff;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:16px}
  .top .shift{font-size:11px;opacity:.9}
  .top a{color:#fff;text-decoration:none;font-size:13px}
  .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;padding:14px}
  .p{background:#fff;border-radius:14px;padding:14px;text-align:center;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.06);border:2px solid transparent;transition:.1s}
  .p:active{transform:scale(.97);border-color:#6b3e1e}
  .p .ico{font-size:26px}
  .p .nm{font-size:13px;font-weight:700;margin-top:6px}
  .p .pr{font-size:14px;color:#6b3e1e;font-weight:800;margin-top:2px}
  .bar{position:fixed;bottom:0;left:0;right:0;background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 -4px 20px rgba(0,0,0,.2)}
  .bar .cnt{font-size:12px;opacity:.85}
  .bar .tot{font-size:22px;font-weight:800}
  .bar a{background:#d4a24c;color:#3b1f0b;text-decoration:none;padding:12px 22px;border-radius:12px;font-weight:800;font-size:14px}
  .bar a:active{transform:scale(.97)}
</style></head><body>
<div class="top">
  <div>
    <h1>🧾 POS</h1>
    <div class="shift">{{ full_name }} · {{ role|upper }}</div>
  </div>
  <a href="{{ url_for('staff.dashboard') }}">← Back</a>
</div>
<div class="grid">
  {% for p in products %}
  <form method="POST" action="{{ url_for('pos.add') }}" style="margin:0">
    <input type="hidden" name="product_id" value="{{ p.id }}">
    <div class="p" onclick="this.parentElement.submit()">
      <div class="ico">{{ p.icon or '☕' }}</div>
      <div class="nm">{{ p.name }}</div>
      <div class="pr">{{ p.price }} ETB</div>
    </div>
  </form>
  {% endfor %}
</div>

<div class="bar">
  <div>
    <div class="cnt">{{ cart_count }} item(s)</div>
    <div class="tot">{{ "%.2f"|format(cart_total) }} ETB</div>
  </div>
  <a href="{{ url_for('pos.checkout') }}">💳 Checkout →</a>
</div>
</body></html>
"""

@pos_bp.route("/")
@_require
def index():
    s = _current_staff()
    shift = _get_open_shift(s["id"])
    products = _get_products()
    cart = _cart()
    return render_template_string(POS_HTML,
        products=products, full_name=s["full_name"], role=s["role"],
        cart_count=sum(int(i["qty"]) for i in cart.values()),
        cart_total=_cart_total(),
        has_shift=bool(shift))

@pos_bp.route("/add", methods=["POST"])
@_require
def add():
    pid = request.form.get("product_id")
    products = _get_products()
    prod = next((p for p in products if str(p["id"]) == str(pid)), None)
    if not prod: return redirect(url_for("pos.index"))
    cart = _cart()
    key = str(prod["id"])
    if key in cart:
        cart[key]["qty"] += 1
    else:
        cart[key] = {"name": prod["name"], "price": float(prod["price"]),
                     "icon": prod.get("icon","☕"), "qty": 1}
    _save_cart(cart)
    return redirect(url_for("pos.index"))

@pos_bp.route("/remove", methods=["POST"])
@_require
def remove():
    pid = str(request.form.get("product_id"))
    cart = _cart()
    if pid in cart:
        cart[pid]["qty"] -= 1
        if cart[pid]["qty"] <= 0: del cart[pid]
    _save_cart(cart)
    return redirect(url_for("pos.checkout"))

@pos_bp.route("/clear", methods=["POST"])
@_require
def clear():
    session["pos_cart"] = {}
    return redirect(url_for("pos.index"))

# ─────────── CHECKOUT ───────────
CHECKOUT_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Checkout — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:20px}
  .top{background:#6b3e1e;color:#fff;padding:12px 16px;display:flex;justify-content:space-between;align-items:center}
  .top h1{margin:0;font-size:16px}
  .top a{color:#fff;text-decoration:none;font-size:13px}
  .wrap{padding:14px;max-width:560px;margin:0 auto}
  .card{background:#fff;border-radius:14px;padding:16px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.05)}
  .row{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #f0e6d8}
  .row:last-child{border-bottom:none}
  .row .nm{font-size:14px;font-weight:600}
  .row .pr{font-size:13px;color:#8a6a4a;margin-top:2px}
  .qty{display:flex;align-items:center;gap:8px}
  .qty button{width:32px;height:32px;border-radius:8px;border:none;font-size:18px;font-weight:700;cursor:pointer;background:#f5ece0;color:#6b3e1e}
  .qty span{min-width:22px;text-align:center;font-weight:700}
  .tot{display:flex;justify-content:space-between;font-size:20px;font-weight:800;color:#6b3e1e;padding-top:14px;border-top:2px solid #6b3e1e;margin-top:6px}
  .empty{text-align:center;color:#8a6a4a;padding:30px 0;font-size:14px}
  h3{margin:0 0 10px;font-size:14px;color:#6b3e1e}
  .pay{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
  .pay button{padding:16px;border:none;border-radius:12px;font-size:15px;font-weight:800;cursor:pointer;color:#fff}
  .pay .cash{background:#2a7d2a}
  .pay .tele{background:#1e6fc4}
  .pay button:active{transform:scale(.97)}
  .pay button:disabled{background:#ccc;cursor:not-allowed}
  input[type=text]{width:100%;padding:12px;border:2px solid #e0d0c0;border-radius:10px;font-size:14px;box-sizing:border-box;margin-top:8px}
  .clear-btn{width:100%;padding:10px;background:transparent;border:1px dashed #c00;color:#c00;border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;margin-top:10px}
</style></head><body>
<div class="top">
  <h1>💳 Checkout</h1>
  <a href="{{ url_for('pos.index') }}">← Add more</a>
</div>
<div class="wrap">
  <div class="card">
    <h3>🛒 Cart ({{ cart_count }})</h3>
    {% if cart_items %}
      {% for key, item in cart_items %}
      <div class="row">
        <div>
          <div class="nm">{{ item.icon }} {{ item.name }}</div>
          <div class="pr">{{ "%.2f"|format(item.price) }} × {{ item.qty }}</div>
        </div>
        <div class="qty">
          <form method="POST" action="{{ url_for('pos.remove') }}" style="margin:0">
            <input type="hidden" name="product_id" value="{{ key }}">
            <button type="submit">−</button>
          </form>
          <span>{{ item.qty }}</span>
          <form method="POST" action="{{ url_for('pos.add') }}" style="margin:0">
            <input type="hidden" name="product_id" value="{{ key }}">
            <button type="submit">+</button>
          </form>
        </div>
        <div style="font-weight:800;min-width:70px;text-align:right">{{ "%.2f"|format(item.price * item.qty) }} ETB</div>
      </div>
      {% endfor %}
      <div class="tot"><span>Total</span><span>{{ "%.2f"|format(cart_total) }} ETB</span></div>
      <form method="POST" action="{{ url_for('pos.clear') }}">
        <button class="clear-btn" type="submit" onclick="return confirm('Cart ሙሉ በሙሉ ይሰረዝ?')">🗑️ Cart አጽዳ</button>
      </form>
    {% else %}
      <div class="empty">🛒 Cart ባዶ ነው<br>ምርቶችን ለመጨመር <a href="{{ url_for('pos.index') }}">POS ተመለስ</a></div>
    {% endif %}
  </div>

  {% if cart_items %}
  <div class="card">
    <h3>💳 Payment</h3>
    <label style="font-size:13px;font-weight:600;color:#5a3a1e">Customer ስም (optional)</label>
    <form method="POST" action="{{ url_for('pos.pay') }}" id="payForm">
      <input type="text" name="customer" placeholder="ለምሳሌ: አበበ" autocomplete="off">
      <input type="hidden" name="method" id="payMethod">
      <div class="pay">
        <button type="button" class="cash" onclick="pay('cash')">💵 Cash</button>
        <button type="button" class="tele" onclick="pay('telebirr')">📱 Telebirr</button>
      </div>
    </form>
  </div>
  {% endif %}
</div>
<script>
  function pay(m){ document.getElementById('payMethod').value = m; document.getElementById('payForm').submit(); }
</script>
</body></html>
"""

@pos_bp.route("/checkout")
@_require
def checkout():
    s = _current_staff()
    cart = _cart()
    items = list(cart.items())
    return render_template_string(CHECKOUT_HTML,
        cart_items=items,
        cart_count=sum(int(i["qty"]) for i in cart.values()),
        cart_total=_cart_total(),
        full_name=s["full_name"], role=s["role"])

@pos_bp.route("/pay", methods=["POST"])
@_require
def pay():
    s = _current_staff()
    shift = _get_open_shift(s["id"])
    if not shift:
        return redirect(url_for("staff.shift_open"))

    method = request.form.get("method", "cash")
    customer = (request.form.get("customer") or "Walk-in")[:100]
    cart = _cart()
    if not cart:
        return redirect(url_for("pos.index"))

    items_text = ", ".join(f"{i['qty']}× {i['name']}" for i in cart.values())
    total = _cart_total()

    # Create order
    order_payload = {
        "customer": customer,
        "table_no": "POS",
        "items": items_text,
        "total": round(float(total), 2),
        "subtotal": round(float(total), 2),
        "discount": 0,
        "status": "PAID",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payment_method": method,
        "payment_status": "PAID",
        "shift_id": shift["id"],
        "user_id": s["id"],
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/fikir_orders",
                     json=order_payload, headers=_headers("return=representation"), timeout=30)
    if r.status_code not in (200, 201):
        return f"ስህተት: {r.text}", 500
    order = r.json()[0]
    order_id = order["id"]

    # Audit
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/fikir_audit_logs",
            json={"user_id": s["id"], "action": "order.create", "entity": "fikir_orders",
                  "entity_id": str(order_id),
                  "new_value": {"total": total, "method": method, "items": items_text},
                  "ip_address": request.remote_addr, "device": request.headers.get("User-Agent","")[:200]},
            headers=_headers(), timeout=30)
    except: pass

    # Save items for receipt, then clear cart
    session["last_receipt_items"] = cart
    session["pos_cart"] = {}

    # Redirect to receipt
    return redirect(url_for("pos.receipt", order_id=order_id))

# ─────────── RECEIPT ───────────
RECEIPT_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Receipt #{{ order.id }} — FIKIR</title>
<style>
  body{margin:0;font-family:'Courier New',monospace;background:#e0d0c0;padding:20px}
  .r{max-width:340px;margin:0 auto;background:#fff;padding:24px 20px;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.15)}
  .h{text-align:center;border-bottom:2px dashed #333;padding-bottom:12px;margin-bottom:12px}
  .h h1{margin:0;font-size:18px;letter-spacing:2px}
  .h .sub{font-size:11px;color:#666;margin-top:4px}
  .line{font-size:13px;padding:4px 0;display:flex;justify-content:space-between}
  .tot{border-top:2px solid #333;margin-top:12px;padding-top:12px;font-size:16px;font-weight:800;display:flex;justify-content:space-between}
  .meta{font-size:11px;color:#666;margin-top:14px;line-height:1.6;text-align:center;border-top:1px dashed #ccc;padding-top:12px}
  .ok{background:#2a7d2a;color:#fff;text-align:center;padding:10px;border-radius:8px;font-weight:700;margin-bottom:14px;font-size:14px}
  .act{display:flex;gap:8px;margin-top:14px}
  .act a{flex:1;text-align:center;padding:12px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px}
  .act .a1{background:#6b3e1e;color:#fff}
  .act .a2{background:#f5ece0;color:#6b3e1e;border:2px solid #6b3e1e}
</style></head><body>
<div class="r">
  <div class="ok">✅ ተከፍሏል</div>
  <div class="h">
    <h1>☕ FIKIR</h1>
    <div class="sub">COFFEE HOUSE<br>Addis Ababa, Ethiopia</div>
  </div>
  <div class="line"><span>Receipt #</span><span><b>{{ order.id }}</b></span></div>
  <div class="line"><span>Customer</span><span>{{ order.customer }}</span></div>
  <div class="line"><span>Cashier</span><span>{{ order.user_id and full_name or 'Staff' }}</span></div>
  <div class="line"><span>Date</span><span>{{ order.created_at[:19].replace('T',' ') }}</span></div>
  <div style="border-top:1px dashed #999;margin:10px 0"></div>
  {% for key, item in items %}
  <div class="line"><span>{{ item.qty }}× {{ item.name }}</span><span>{{ "%.2f"|format(item.price * item.qty) }}</span></div>
  {% endfor %}
  <div class="tot"><span>TOTAL</span><span>{{ "%.2f"|format(order.total) }} ETB</span></div>
  <div class="line" style="margin-top:8px"><span>Payment</span><span><b>{{ order.payment_method|upper }}</b></span></div>
  <div class="meta">
    አመሰግናለን! 🙏<br>
    እንደገና ይመጡ።<br><br>
    ☕ FIKIR COFFEE HOUSE
  </div>
</div>
<div class="act" style="max-width:340px;margin:14px auto 0">
  <a class="a1" href="{{ url_for('pos.index') }}">➕ አዲስ ትዕዛዝ</a>
  <a class="a2" onclick="window.print()">🖨️ Print</a>
</div>
</body></html>
"""

@pos_bp.route("/receipt/<int:order_id>")
@_require
def receipt(order_id):
    s = _current_staff()
    url = f"{SUPABASE_URL}/rest/v1/fikir_orders?id=eq.{order_id}&limit=1"
    r = requests.get(url, headers=_headers(), timeout=30)
    if r.status_code != 200 or not r.json():
        return "Order አልተገኘም", 404
    order = r.json()[0]
    # Parse items from cart snapshot stored in session? We cleared it — need to re-derive
    # Simplest: keep last order items in session before clear
    items = session.get("last_receipt_items", {})
    return render_template_string(RECEIPT_HTML,
        order=order, items=list(items.items()),
        full_name=s["full_name"])
