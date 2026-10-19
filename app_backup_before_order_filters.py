from flask import Flask, request, redirect, url_for, session, render_template_string, jsonify
import os
import requests
import sqlite3
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
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
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

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
  .links{display:none}.wrap{padding:14px}.hero{padding:30px 22px;min-height:300px}
  .layout{grid-template-columns:1fr}.grid{grid-template-columns:repeat(2,1fr)}.kitchen-grid{grid-template-columns:1fr 1fr}
}
@media(max-width:500px){
  .brand .logo{width:44px;height:44px;font-size:23px}.hero h1{font-size:45px}.script{font-size:21px}
  .grid{grid-template-columns:1fr}.kitchen-grid{grid-template-columns:1fr}.productpic{height:145px}
}
"""

BASE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title or "FIKIR Coffee House" }}</title>
<style>""" + CSS + r"""</style>
</head>
<body>
<header class="nav"><div class="navin">
<a class="brand" href="/">
  <div class="logo">☕</div>
  <div><b>FIKIR</b><small>COFFEE HOUSE</small></div>
</a>
<nav class="links">
  <a href="/" class="{{ 'active' if page=='home' else '' }}">⌂ Home</a>
  <a href="/#menu">☕ Menu</a>
  <a href="/cart">🛒 Cart</a>
  <a href="/kitchen">👨‍🍳 Kitchen</a>
</nav>
<a class="cartbtn" href="/cart">🛒 <span class="badge">{{ cart_count }}</span></a>
</div></header>
<div class="wrap">
{{ body|safe }}
</div>
<footer>☕ <b>FIKIR Coffee House</b> &nbsp;—&nbsp; Taste the Difference</footer>
</body></html>
"""

def cart_data():
    raw = session.get("cart", {})
    items, total, count = [], 0, 0
    for pid, qty in raw.items():
        p = next((x for x in PRODUCTS if x["id"] == int(pid)), None)
        if not p: continue
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
""", products=PRODUCTS, items=cart_data()[0], total=cart_data()[1])
    return page(body)

@app.post("/add")
def add():
    pid = request.form.get("product_id", type=int)
    if not any(p["id"] == pid for p in PRODUCTS):
        return "Invalid product", 400
    cart = session.get("cart", {})
    key = str(pid)
    cart[key] = int(cart.get(key, 0)) + 1
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

        # Save locally for the existing Kitchen Dashboard
        conn = db()
        cur = conn.execute(
            "INSERT INTO fikir_orders(customer,table_no,items,total,status,created_at) VALUES(?,?,?,?,?,?)",
            (customer, table_no, item_text, total, "NEW", created_at)
        )
        order_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Also send the order to Supabase when Render environment variables are available
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                requests.post(
                    SUPABASE_URL.rstrip("/") + "/rest/v1/fikir_orders",
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": "Bearer " + SUPABASE_KEY,
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
      <button class="btn" style="width:100%">✅ PLACE ORDER</button>
    </form>
  </div>
</div>
""", items=items, total=total)

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
    <a class="btn" href="/">☕ New Order</a>
  </div>
</div>
""", order=order)
    return page(body)

@app.route("/kitchen")
def kitchen():
    conn=db()
    orders=conn.execute("SELECT * FROM fikir_orders ORDER BY id DESC").fetchall()
    conn.close()
    body = render_template_string(r"""
<div class="title">
  <div><h2>👨‍🍳 Kitchen Dashboard</h2><p>Live customer orders</p></div>
  <a class="btn secondary" href="/">← Customer Menu</a>
</div>
{% if orders %}
<div class="kitchen-grid">
{% for o in orders %}
<div class="kitchen-card">
  <div class="row"><h3>Order #{{ o.id }}</h3><span class="status">{{ o.status }}</span></div>
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
    if request.method == "POST":
        password = request.form.get("password", "")
        if ADMIN_PASSWORD and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        return render_template_string("""
        <div class="formbox">
          <div class="card" style="padding:30px">
            <h2>🔐 Admin Login</h2>
            <div class="notice">❌ Incorrect password</div>
            <form method="post">
              <label>Password</label>
              <input type="password" name="password" required autofocus>
              <button class="btn" style="width:100%">Login</button>
            </form>
          </div>
        </div>
        """)
    return render_template_string("""
    <div class="formbox">
      <div class="card" style="padding:30px">
        <h2>🔐 Admin Login</h2>
        <p>FIKIR Coffee House Admin</p>
        <form method="post">
          <label>Password</label>
          <input type="password" name="password" required autofocus>
          <button class="btn" style="width:100%">Login</button>
        </form>
      </div>
    </div>
    """)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = db()

    total_orders = conn.execute(
        "SELECT COUNT(*) FROM fikir_orders"
    ).fetchone()[0]

    total_sales = conn.execute(
        "SELECT COALESCE(SUM(total),0) FROM fikir_orders"
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

    recent_orders = conn.execute("""
        SELECT id, customer, table_no, items, total, status, created_at
        FROM fikir_orders
        ORDER BY id DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    body = render_template_string(r"""
    <div class="wrap">

      <div class="title">
        <div>
          <h1>📊 Admin Dashboard</h1>
          <p>FIKIR Coffee House — Order & Sales Overview</p>
        </div>
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

      <div class="formbox" style="margin-top:25px">
        <div class="title">
          <div>
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
              <th style="padding:12px;text-align:left">Date</th>
            </tr>

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
    recent_orders=recent_orders)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
