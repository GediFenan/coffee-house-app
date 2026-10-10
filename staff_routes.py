# ═══════════════════════════════════════════════
# FIKIR — Staff Authentication & POS Routes
# Blueprint: /staff/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, hashlib, requests
from datetime import datetime, timezone

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")

SUPABASE_URL = "https://skswircyorzpbcioljcs.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrc3dpcmN5b3J6cGJjaW9samNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MjMyMzQsImV4cCI6MjEwMzQ5OTIzNH0.ntS52ih33wprDiQ4YGrNzWchuuWqfzc1iyv7_xi_qPM"

def _headers(prefer=None):
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h

def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

def _find_user(username: str):
    url = f"{SUPABASE_URL}/rest/v1/fikir_users?username=eq.{username}&is_active=eq.true&limit=1"
    try:
        r = requests.get(url, headers=_headers(), timeout=30)
        if r.status_code == 200 and r.json():
            return r.json()[0]
    except Exception as e:
        print("[FIND USER ERROR]", e)
    return None

def _get_shift_summary(shift_id):
    """Calculate cash reconciliation for a shift (offline-safe)"""
    try:
        # Orders in this shift
        o_url = (f"{SUPABASE_URL}/rest/v1/fikir_orders"
                 f"?shift_id=eq.{shift_id}&status=neq.CANCELLED"
                 f"&select=total,payment_method")
        r = requests.get(o_url, headers=_headers(), timeout=15)
        orders = r.json() if r.status_code == 200 else []

        total_sales = 0.0
        cash_sales = 0.0
        telebirr_sales = 0.0
        for o in orders:
            amt = float(o.get("total") or 0)
            total_sales += amt
            pm = (o.get("payment_method") or "").lower()
            if pm == "cash":
                cash_sales += amt
            elif pm == "telebirr":
                telebirr_sales += amt

        # Expenses in this shift (cash only affects Expected Cash)
        e_url = (f"{SUPABASE_URL}/rest/v1/fikir_expenses"
                 f"?shift_id=eq.{shift_id}&select=amount,paid_from")
        re_ = requests.get(e_url, headers=_headers(), timeout=15)
        expenses = re_.json() if re_.status_code == 200 else []
        cash_expenses = sum(
            float(e.get("amount") or 0)
            for e in expenses
            if (e.get("paid_from") or "cash") == "cash"
        )

        return {
            "orders_count": len(orders),
            "total_sales": total_sales,
            "cash_sales": cash_sales,
            "telebirr_sales": telebirr_sales,
            "cash_expenses": cash_expenses,
        }
    except Exception as e:
        print("[SHIFT SUMMARY ERR]", e)
        return {
            "orders_count": 0,
            "total_sales": 0.0,
            "cash_sales": 0.0,
            "telebirr_sales": 0.0,
            "cash_expenses": 0.0,
        }

def _get_open_shift(user_id):
    """Get currently open shift for a user, or None (offline-safe)"""
    url = (f"{SUPABASE_URL}/rest/v1/fikir_shifts"
           f"?user_id=eq.{user_id}&status=eq.open"
           f"&order=opened_at.desc&limit=1")
    try:
        r = requests.get(url, headers=_headers(), timeout=15)
        return r.json()[0] if (r.status_code == 200 and r.json()) else None
    except Exception as e:
        print("[SHIFT ERROR]", e)
        return None

def _audit(user_id, action, entity=None, entity_id=None, extra=None):
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/fikir_audit_logs",
            json={
                "user_id": user_id,
                "action": action,
                "entity": entity,
                "entity_id": str(entity_id) if entity_id else None,
                "new_value": extra or {},
                "ip_address": request.remote_addr,
                "device": request.headers.get("User-Agent", "")[:200],
            },
            headers=_headers(), timeout=30
        )
    except Exception as e:
        print("[AUDIT ERROR]", e)

def current_staff():
    """Return current logged-in staff dict from session, or None"""
    if "staff_id" not in session:
        return None
    return {
        "id": session.get("staff_id"),
        "username": session.get("staff_username"),
        "full_name": session.get("staff_name"),
        "role": session.get("staff_role"),
    }

def require_role(*roles):
    """Decorator: require login + one of roles"""
    def wrapper(fn):
        def inner(*a, **kw):
            s = current_staff()
            if not s:
                return redirect(url_for("staff.login"))
            if roles and s["role"] not in roles:
                return "403 Forbidden — Role: " + s["role"], 403
            return fn(*a, **kw)
        inner.__name__ = fn.__name__
        return inner
    return wrapper

# ─────────── LOGIN PAGE ───────────
LOGIN_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#6b3e1e">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="FIKIR">
<meta name="mobile-web-app-capable" content="yes">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="/pwa/icon-192.png">
<link rel="icon" type="image/png" href="/pwa/icon-192.png">
<title>FIKIR Staff Login</title>
<style>
  body{margin:0;font-family:system-ui,sans-serif;background:linear-gradient(135deg,#3b1f0b,#6b3e1e);color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
  .card{background:#fff;color:#3b1f0b;border-radius:20px;padding:32px;max-width:380px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,.4)}
  h1{margin:0 0 4px;font-size:22px;text-align:center}
  .sub{text-align:center;color:#8a6a4a;font-size:13px;margin-bottom:24px}
  label{display:block;font-size:12px;font-weight:600;margin-bottom:6px;color:#5a3a1e}
  input{width:100%;padding:14px;border:2px solid #e0d0c0;border-radius:12px;font-size:16px;box-sizing:border-box;margin-bottom:14px;outline:none;transition:.2s}
  input:focus{border-color:#6b3e1e}
  button{width:100%;padding:14px;background:#6b3e1e;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer}
  button:active{transform:scale(.98)}
  .err{background:#ffe0e0;color:#c00;padding:10px;border-radius:8px;font-size:13px;margin-bottom:14px;text-align:center}
  .pin-display{text-align:center;font-size:28px;letter-spacing:8px;margin-bottom:14px;color:#6b3e1e;min-height:36px}
  .numpad{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}
  .numpad button{background:#f5ece0;color:#3b1f0b;font-size:20px;padding:16px 0}
  .numpad button.del{background:#e0d0c0;font-size:14px}
</style></head><body>
<div class="card">
  <h1>☕ FIKIR Staff</h1>
  <div class="sub">Login በ Username + PIN</div>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST" id="loginForm">
    <label>Username</label>
    <input name="username" id="username" autocomplete="off" autofocus required value="{{ last_user or '' }}">
    <label>PIN</label>
    <input type="password" name="pin" id="pin" inputmode="numeric" pattern="[0-9]*" maxlength="6" required>
    <div class="numpad">
      {% for n in '123456789' %}<button type="button" onclick="addDigit('{{n}}')">{{n}}</button>{% endfor %}
      <button type="button" class="del" onclick="delDigit()">⌫ DEL</button>
      <button type="button" onclick="addDigit('0')">0</button>
      <button type="submit">➜</button>
    </div>
  </form>
</div>
<script>
  const pin = document.getElementById('pin');
  function addDigit(d){ if(pin.value.length<6) pin.value += d; }
  function delDigit(){ pin.value = pin.value.slice(0,-1); }
  // PWA Service Worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js', {scope:'/'})
      .then(r => console.log('[PWA] SW registered'))
      .catch(e => console.log('[PWA] SW error:', e));
  }
</script>
</body></html>
"""

@staff_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    last_user = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        pin = (request.form.get("pin") or "").strip()
        last_user = username
        if not username or not pin:
            error = "Username እና PIN ያስፈልጋሉ"
        else:
            user = _find_user(username)
            if not user:
                error = "Username አልተገኘም"
            elif user["pin_hash"] != _hash_pin(pin):
                error = "PIN ትክክል አይደለም"
            else:
                session["staff_id"] = user["id"]
                session["staff_username"] = user["username"]
                session["staff_name"] = user["full_name"]
                session["staff_role"] = user["role"]
                session.permanent = True
                try:
                    requests.patch(
                        f"{SUPABASE_URL}/rest/v1/fikir_users?id=eq.{user['id']}",
                        json={"last_login_at": datetime.now(timezone.utc).isoformat()},
                        headers=_headers(), timeout=5
                    )
                except: pass
                _audit(user["id"], "staff.login", "fikir_users", user["id"])
                return redirect(url_for("staff.dashboard"))
    return render_template_string(LOGIN_HTML, error=error, last_user=last_user)

@staff_bp.route("/logout")
def logout():
    s = current_staff()
    if s:
        _audit(s["id"], "staff.logout", "fikir_users", s["id"])
    session.clear()
    return redirect(url_for("staff.login"))

# ─────────── STAFF DASHBOARD (role-based) ───────────
DASH_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FIKIR — {{ role|upper }}</title>
<style>
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b}
  .top{background:#6b3e1e;color:#fff;padding:16px 20px;display:flex;justify-content:space-between;align-items:center}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;opacity:.9}
  .wrap{padding:20px;max-width:640px;margin:0 auto}
  .card{background:#fff;border-radius:16px;padding:20px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.05)}
  .card h2{margin:0 0 8px;font-size:15px;color:#6b3e1e}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .tile{background:#fff;border-radius:14px;padding:18px;text-align:center;text-decoration:none;color:#3b1f0b;box-shadow:0 2px 8px rgba(0,0,0,.05)}
  .tile .ico{font-size:32px;display:block;margin-bottom:6px}
  .tile .lbl{font-size:13px;font-weight:600}
  .pill{display:inline-block;background:#e6d5c0;color:#6b3e1e;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.5px}
</style></head><body>
<div class="top">
  <h1>☕ FIKIR — {{ full_name }}</h1>
  <a href="{{ url_for('staff.logout') }}">Logout</a>
</div>
<div class="wrap">
  <div class="card">
    <span class="pill">{{ role|upper }}</span>
    <div style="margin-top:10px;font-size:13px;color:#8a6a4a">
      @{{ username }} — እንኳን ደህና መጡ
    </div>
  </div>

  {% if role in ['owner','manager'] %}
    <div class="grid">
      <a class="tile" href="{{ url_for('pos.index') }}"><span class="ico">🧾</span><span class="lbl">POS</span></a>
      <a class="tile" href="{{ url_for('staff.shift_open') }}"><span class="ico">💰</span><span class="lbl">Shift ክፈት</span></a>
      <a class="tile" href="{{ url_for('expenses.index') }}"><span class="ico">💸</span><span class="lbl">Expenses</span></a>
      <a class="tile" href="{{ url_for('products_admin.index') }}"><span class="ico">☕</span><span class="lbl">ምርቶች</span></a>
      <a class="tile" href="{{ url_for('inventory.index') }}"><span class="ico">📦</span><span class="lbl">Inventory</span></a>
      <a class="tile" href="{{ url_for('notify.settings') }}"><span class="ico">📱</span><span class="lbl">Telegram</span></a>
      <a class="tile" href="{{ url_for('qr_menu.qr_tables') }}"><span class="ico">🔗</span><span class="lbl">QR Codes</span></a>
      <a class="tile" href="{{ url_for('offline.dashboard') }}"><span class="ico">🌐</span><span class="lbl">Offline</span></a>
      <a class="tile" href="{{ url_for('reports.index') }}"><span class="ico">📊</span><span class="lbl">Reports</span></a>
      <a class="tile" href="{{ url_for('kitchen.index') }}"><span class="ico">🍳</span><span class="lbl">Kitchen</span></a>
      </div>
  {% elif role == 'cashier' %}
    <div class="grid">
      <a class="tile" href="{{ url_for('pos.index') }}"><span class="ico">🧾</span><span class="lbl">POS</span></a>
      <a class="tile" href="{{ url_for('staff.shift_open') }}"><span class="ico">💰</span><span class="lbl">Shift ክፈት</span></a>
      
    </div>
  {% elif role == 'barista' %}
    <div class="grid">
      <a class="tile" href="{{ url_for('pos.index') }}"><span class="ico">🧾</span><span class="lbl">Orders</span></a>
      <a class="tile" href="{{ url_for('kitchen.index') }}"><span class="ico">🍵</span><span class="lbl">Kitchen</span></a>
    </div>
  {% elif role == 'kitchen' %}
    <div class="grid">
      <a class="tile" href="{{ url_for('kitchen.index') }}"><span class="ico">🍳</span><span class="lbl">Kitchen Orders</span></a>
    </div>
  {% endif %}

  <div class="card" style="margin-top:20px">
    <h2>ℹ️ ማስታወሻ</h2>
    <div style="font-size:13px;color:#8a6a4a;line-height:1.6">
      ይህ የ Phase 1 መጀመሪያ ነው። POS፣ Shift፣ Reports እና Inventory በቀጣይ ደረጃዎች ይጨመራሉ።
    </div>
  </div>
</div>
</body></html>
"""

@staff_bp.route("/")
@require_role()
def dashboard():
    s = current_staff()
    return render_template_string(DASH_HTML, **s)



# ═══════════════════════════════════════════════
# SHIFT TEMPLATES
# ═══════════════════════════════════════════════
SHIFT_OPEN_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Shift ክፈት — FIKIR</title>
<style>
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b}
  .top{background:#6b3e1e;color:#fff;padding:16px 20px;display:flex;justify-content:space-between;align-items:center}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px}
  .wrap{padding:20px;max-width:480px;margin:0 auto}
  .card{background:#fff;border-radius:16px;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.06)}
  h2{margin:0 0 6px;font-size:20px;color:#6b3e1e}
  .sub{color:#8a6a4a;font-size:13px;margin-bottom:20px}
  label{display:block;font-size:13px;font-weight:600;margin-bottom:6px;color:#5a3a1e}
  input{width:100%;padding:16px;border:2px solid #e0d0c0;border-radius:12px;font-size:22px;box-sizing:border-box;margin-bottom:16px;outline:none;text-align:center;font-weight:700;color:#6b3e1e}
  input:focus{border-color:#6b3e1e}
  button{width:100%;padding:16px;background:#6b3e1e;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:700;cursor:pointer}
  button:active{transform:scale(.98)}
  .info{background:#fff8e8;border-left:4px solid #d4a24c;padding:12px;border-radius:8px;font-size:13px;color:#8a6a4a;margin-bottom:18px;line-height:1.5}
  .err{background:#ffe0e0;color:#c00;padding:10px;border-radius:8px;font-size:13px;margin-bottom:14px;text-align:center}
</style></head><body>
<div class="top">
  <h1>☕ FIKIR — Shift ክፈት</h1>
  <a href="{{ url_for('staff.dashboard') }}">← Back</a>
</div>
<div class="wrap">
  <div class="card">
    <h2>🟢 አዲስ Shift ክፈት</h2>
    <div class="sub">{{ full_name }} — {{ role|upper }}</div>
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
    <div class="info">
      በ cash drawer ውስጥ ያለውን <b>የመክፈቻ ገንዘብ</b> ያስገቡ። ይህ በ shift መጨረሻ ላይ ለ cash reconciliation ይጠቅማል።
    </div>
    <form method="POST" action="{{ url_for('staff.shift_open') }}">
      <label>Opening Cash (ETB)</label>
      <input name="opening_cash" type="number" step="0.01" min="0" inputmode="decimal" required autofocus value="0">
      <button type="submit">🟢 Shift ክፈት</button>
    </form>
  </div>
</div>
</body></html>
"""

SHIFT_VIEW_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Shift — FIKIR</title>
<style>
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b}
  .top{background:#6b3e1e;color:#fff;padding:16px 20px;display:flex;justify-content:space-between;align-items:center}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px}
  .wrap{padding:20px;max-width:520px;margin:0 auto}
  .card{background:#fff;border-radius:16px;padding:22px;margin-bottom:14px;box-shadow:0 2px 12px rgba(0,0,0,.06)}
  h2{margin:0 0 4px;font-size:18px;color:#6b3e1e}
  .sub{color:#8a6a4a;font-size:12px;margin-bottom:16px}
  .row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f0e6d8;font-size:14px}
  .row:last-child{border-bottom:none}
  .row .lbl{color:#8a6a4a}
  .row .val{font-weight:700;color:#3b1f0b}
  .row .val.red{color:#c00}
  .row .val.green{color:#2a7d2a}
  .pill{display:inline-block;background:#d4edda;color:#1e7e34;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.5px}
  input[type=number]{width:100%;padding:14px;border:2px solid #e0d0c0;border-radius:12px;font-size:20px;box-sizing:border-box;margin:8px 0;outline:none;text-align:center;font-weight:700;color:#6b3e1e}
  button{width:100%;padding:14px;background:#c0392b;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-top:8px}
  button:active{transform:scale(.98)}
  .warn{background:#fff3cd;border-left:4px solid #f0ad4e;padding:12px;border-radius:8px;font-size:13px;color:#8a6a4a;margin-bottom:14px;line-height:1.5}
</style></head><body>
<div class="top">
  <h1>☕ FIKIR — Shift</h1>
  <a href="{{ url_for('staff.dashboard') }}">← Back</a>
</div>
<div class="wrap">
  <div class="card">
    <span class="pill">🟢 OPEN</span>
    <h2 style="margin-top:10px">የአሁኑ Shift</h2>
    <div class="sub">ተከፍቷል: {{ shift.opened_at[:19].replace('T',' ') if shift.opened_at else '-' }}</div>
    <div class="row"><span class="lbl">የመክፈቻ ገንዘብ</span><span class="val">{{ "%.2f"|format(shift.opening_cash|float) }} ETB</span></div>
    <div class="row"><span class="lbl">Orders</span><span class="val">{{ summary.orders_count }}</span></div>
    <div class="row"><span class="lbl">ጠቅላላ ሽያጭ</span><span class="val">{{ "%.2f"|format(summary.total_sales) }} ETB</span></div>
    <div class="row"><span class="lbl">Cash ሽያጭ</span><span class="val">{{ "%.2f"|format(summary.cash_sales) }} ETB</span></div>
    <div class="row"><span class="lbl">Telebirr ሽያጭ</span><span class="val">{{ "%.2f"|format(summary.telebirr_sales) }} ETB</span></div>
    <div class="row"><span class="lbl">Cash ወጪዎች</span><span class="val red">-{{ "%.2f"|format(summary.cash_expenses) }} ETB</span></div>
    <div class="row" style="padding-top:14px;border-top:2px solid #6b3e1e">
      <span class="lbl" style="font-weight:700;color:#6b3e1e">Expected Cash</span>
      <span class="val green">{{ "%.2f"|format(expected_cash) }} ETB</span>
    </div>
  </div>

  <div class="card">
    <h2>🔴 Shift ዝጋ</h2>
    <div class="warn">
      በ cash drawer ውስጥ ያለውን ጠቅላላ ገንዘብ ይቁጠሩና ያስገቡ።
    </div>
    <form method="POST" action="{{ url_for('staff.shift_close') }}">
      <label style="font-size:13px;font-weight:600;color:#5a3a1e">Counted Cash (ETB)</label>
      <input name="counted_cash" type="number" step="0.01" min="0" inputmode="decimal" required placeholder="0.00">
      <input name="note" placeholder="ማስታወሻ (optional)" style="font-size:14px;text-align:left;padding:12px;font-weight:400">
      <button type="submit">🔴 Shift ዝጋ</button>
    </form>
  </div>
</div>
</body></html>
"""


@staff_bp.route("/shift", methods=["GET", "POST"])
@require_role("owner", "manager", "cashier")
def shift_open():
    s = current_staff()
    open_shift = _get_open_shift(s["id"])

    # If already has open shift → show it
    if open_shift:
        summary = _get_shift_summary(open_shift["id"])
        expected = float(open_shift["opening_cash"] or 0) + summary["cash_sales"] - summary["cash_expenses"]
        return render_template_string(SHIFT_VIEW_HTML,
                                      shift=open_shift, summary=summary,
                                      expected_cash=expected, **s)

    # POST → create new shift
    if request.method == "POST":
        try:
            opening = float(request.form.get("opening_cash") or 0)
        except ValueError:
            return render_template_string(SHIFT_OPEN_HTML, error="ቁጥር ብቻ ያስገቡ", **s)

        payload = {
            "user_id": s["id"],
            "opening_cash": opening,
            "status": "open",
        }
        r = requests.post(f"{SUPABASE_URL}/rest/v1/fikir_shifts",
                          json=payload, headers=_headers("return=representation"), timeout=30)
        if r.status_code in (200, 201):
            _audit(s["id"], "shift.open", "fikir_shifts", None, {"opening_cash": opening})
            try:
                from notifications_routes import notify_shift
                notify_shift(None, "open", s.get("full_name",""), opening_cash=opening)
            except Exception as e:
                print("[TG SHIFT OPEN ERR]", e)
            return redirect(url_for("staff.shift_open"))
        return render_template_string(SHIFT_OPEN_HTML, error=f"ስህተት: {r.text[:120]}", **s)

    # GET without open shift → show open form
    return render_template_string(SHIFT_OPEN_HTML, error=None, **s)

@staff_bp.route("/shift/close", methods=["POST"])
@require_role("owner", "manager", "cashier")
def shift_close():
    s = current_staff()
    open_shift = _get_open_shift(s["id"])
    if not open_shift:
        return redirect(url_for("staff.shift_open"))

    try:
        counted = float(request.form.get("counted_cash") or 0)
    except ValueError:
        counted = 0

    summary = _get_shift_summary(open_shift["id"])
    expected = float(open_shift["opening_cash"] or 0) + summary["cash_sales"] - summary["cash_expenses"]
    difference = counted - expected

    payload = {
        "closed_at": datetime.now(timezone.utc).isoformat(),
        "counted_cash": counted,
        "expected_cash": expected,
        "difference": difference,
        "status": "closed",
        "note": (request.form.get("note") or "")[:500],
    }
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_shifts?id=eq.{open_shift['id']}",
                       json=payload, headers=_headers(), timeout=30)
    if r.status_code in (200, 204):
        _audit(s["id"], "shift.close", "fikir_shifts", open_shift["id"],
               {"expected": expected, "counted": counted, "difference": difference})
        try:
            from notifications_routes import notify_shift
            notify_shift(open_shift["id"], "close", s.get("full_name",""),
                         opening_cash=float(open_shift.get("opening_cash") or 0),
                         counted=counted, expected=expected, diff=difference)
        except Exception as e:
            print("[TG SHIFT CLOSE ERR]", e)
        return redirect(url_for("staff.dashboard"))
    return f"ስህተት: {r.text}", 500
