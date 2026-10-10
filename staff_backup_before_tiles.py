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
<meta name="viewport" content="width=device-width,initial-scale=1">
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
      <a class="tile" href="#"><span class="ico">📊</span><span class="lbl">Reports</span></a>
      <a class="tile" href="#"><span class="ico">👥</span><span class="lbl">Staff</span></a>
    </div>
  {% elif role == 'cashier' %}
    <div class="grid">
      <a class="tile" href="{{ url_for('pos.index') }}"><span class="ico">🧾</span><span class="lbl">POS</span></a>
      <a class="tile" href="{{ url_for('staff.shift_open') }}"><span class="ico">💰</span><span class="lbl">Shift ክፈት</span></a>
    </div>
  {% elif role == 'barista' %}
    <div class="grid">
      <a class="tile" href="{{ url_for('pos.index') }}"><span class="ico">🧾</span><span class="lbl">Orders</span></a>
      <a class="tile" href="#"><span class="ico">🍵</span><span class="lbl">Kitchen</span></a>
    </div>
  {% elif role == 'kitchen' %}
    <div class="grid">
      <a class="tile" href="#"><span class="ico">🍳</span><span class="lbl">Kitchen Orders</span></a>
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
        return redirect(url_for("staff.dashboard"))
    return f"ስህተት: {r.text}", 500
