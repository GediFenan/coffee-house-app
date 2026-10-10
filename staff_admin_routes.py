# ═══════════════════════════════════════════════
# FIKIR — Staff Management (Owner/Manager only)
# Blueprint: /staff-admin/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, hashlib, requests
from datetime import datetime, timezone

staff_admin_bp = Blueprint("staff_admin", __name__, url_prefix="/staff-admin")

SUPABASE_URL = "https://skswircyorzpbcioljcs.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrc3dpcmN5b3J6cGJjaW9samNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MjMyMzQsImV4cCI6MjEwMzQ5OTIzNH0.ntS52ih33wprDiQ4YGrNzWchuuWqfzc1iyv7_xi_qPM"

def _headers(prefer=None):
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    if prefer: h["Prefer"] = prefer
    return h

def _hash_pin(pin): return hashlib.sha256(pin.encode()).hexdigest()

def _current():
    if "staff_id" not in session: return None
    return {"id": session.get("staff_id"), "username": session.get("staff_username"),
            "full_name": session.get("staff_name"), "role": session.get("staff_role")}

def _require_admin(fn):
    def inner(*a, **kw):
        s = _current()
        if not s: return redirect(url_for("staff.login"))
        if s["role"] not in ("owner","manager"):
            return "403 — Owner/Manager only", 403
        return fn(*a, **kw)
    inner.__name__ = fn.__name__
    return inner

def _get(url):
    try:
        r = requests.get(url, headers=_headers(), timeout=30)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print("[STAFF-ADMIN GET ERR]", e)
        return []

def _audit(user_id, action, entity=None, entity_id=None, extra=None):
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/fikir_audit_logs",
            json={"user_id": user_id, "action": action, "entity": entity,
                  "entity_id": str(entity_id) if entity_id else None,
                  "new_value": extra or {}},
            headers=_headers(), timeout=30)
    except Exception:
        pass

ROLES = [("owner","👑 Owner"),("manager","📋 Manager"),("cashier","💰 Cashier"),
         ("barista","☕ Barista"),("kitchen","🍳 Kitchen")]

STAFF_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Staff — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:16px;max-width:680px;margin:0 auto}
  .card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 8px rgba(107,62,30,.06);margin-bottom:14px}
  .card h2{margin:0 0 14px;font-size:15px;color:#6b3e1e;text-transform:uppercase;letter-spacing:.5px}
  label{display:block;font-size:12px;font-weight:700;color:#5a3a1e;margin-bottom:6px;margin-top:12px}
  label:first-child{margin-top:0}
  input,select{width:100%;padding:12px;border:2px solid #e0d0c0;border-radius:10px;font-size:15px;outline:none;font-family:inherit;background:#fff}
  input:focus,select:focus{border-color:#6b3e1e}
  button{width:100%;padding:14px;background:#6b3e1e;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-top:16px}
  button:active{transform:scale(.98)}
  button.danger{background:#c0392b}
  button.small{width:auto;padding:8px 14px;font-size:12px;margin:0;border-radius:8px}
  .row{display:flex;justify-content:space-between;align-items:center;padding:14px 0;border-bottom:1px solid #f0e6d8}
  .row:last-child{border-bottom:none}
  .info{flex:1}
  .info .nm{font-weight:700;font-size:15px}
  .info .un{font-size:12px;color:#8a6a4a;margin-top:3px}
  .badge{display:inline-block;font-size:10px;padding:3px 9px;border-radius:20px;font-weight:800;letter-spacing:.5px;text-transform:uppercase;margin-left:6px}
  .badge.owner{background:#6b3e1e;color:#fff}
  .badge.manager{background:#1e6fc4;color:#fff}
  .badge.cashier{background:#2a7d2a;color:#fff}
  .badge.barista{background:#d4a24c;color:#3b1f0b}
  .badge.kitchen{background:#f0ad4e;color:#3b1f0b}
  .badge.inactive{background:#ccc;color:#666}
  .actions{display:flex;gap:6px;flex-wrap:wrap}
  .empty{text-align:center;padding:30px 20px;color:#8a6a4a;font-size:14px}
  .err{background:#ffe0e0;color:#c00;padding:10px;border-radius:8px;font-size:13px;margin-bottom:14px}
  .ok{background:#d4edda;color:#1e7e34;padding:10px;border-radius:8px;font-size:13px;margin-bottom:14px;font-weight:600}
  .hint{font-size:11px;color:#8a6a4a;margin-top:4px}
</style></head><body>
<div class="top">
  <h1>👥 Staff Management</h1>
  <a href="{{ url_for('staff.dashboard') }}">← Back</a>
</div>
<div class="wrap">

  {% if msg %}<div class="ok">{{ msg }}</div>{% endif %}
  {% if error %}<div class="err">{{ error }}</div>{% endif %}

  <div class="card">
    <h2>➕ አዲስ ሰራተኛ</h2>
    <form method="POST" action="{{ url_for('staff_admin.create') }}">
      <label>ሙሉ ስም</label>
      <input name="full_name" required maxlength="80" placeholder="ለምሳሌ: ሀና ተስፋዬ" autocomplete="off">

      <label>Username (login ስም)</label>
      <input name="username" required maxlength="30" pattern="[A-Za-z0-9_]+" placeholder="ለምሳሌ: hana" autocomplete="off" oninput="this.value = this.value.toLowerCase()">
      <div class="hint">🔡 ትንንሽ ፊደላት ብቻ (a-z, 0-9, _)</div>

      <label>PIN (4-6 አሃዝ)</label>
      <input name="pin" required pattern="[0-9]{4,6}" inputmode="numeric" maxlength="6" placeholder="1111" autocomplete="off">

      <label>Role</label>
      <select name="role" required>
        {% for code, label in roles %}
        <option value="{{ code }}" {% if code == 'cashier' %}selected{% endif %}>{{ label }}</option>
        {% endfor %}
      </select>

      <label>ስልክ (optional)</label>
      <input name="phone" maxlength="20" placeholder="+251..." autocomplete="off">

      <button type="submit">➕ ሰራተኛ ጨምር</button>
    </form>
  </div>

  <div class="card">
    <h2>📋 ሁሉም ሰራተኞች ({{ users|length }})</h2>
    {% if users %}
      {% for u in users %}
      <div class="row">
        <div class="info">
          <div class="nm">{{ u.full_name }}
            <span class="badge {{ u.role }}">{{ u.role }}</span>
            {% if not u.is_active %}<span class="badge inactive">INACTIVE</span>{% endif %}
          </div>
          <div class="un">@{{ u.username }}{% if u.phone %} · {{ u.phone }}{% endif %}</div>
        </div>
        <div class="actions">
          {% if u.role != 'owner' or current.id == u.id %}
          <form method="POST" action="{{ url_for('staff_admin.reset_pin') }}" style="margin:0" onsubmit="return promptPin(this)">
            <input type="hidden" name="user_id" value="{{ u.id }}">
            <input type="hidden" name="new_pin" id="pin-{{ u.id }}">
            <button type="submit" class="small">🔑 PIN</button>
          </form>
          {% endif %}
          {% if u.is_active and u.role != 'owner' %}
          <form method="POST" action="{{ url_for('staff_admin.deactivate') }}" style="margin:0" onsubmit="return confirm('{{ u.full_name }} ን ማሰናከል?')">
            <input type="hidden" name="user_id" value="{{ u.id }}">
            <button type="submit" class="small danger">🚫 አሰናክል</button>
          </form>
          {% elif not u.is_active %}
          <form method="POST" action="{{ url_for('staff_admin.activate') }}" style="margin:0">
            <input type="hidden" name="user_id" value="{{ u.id }}">
            <button type="submit" class="small">✅ አስነሳ</button>
          </form>
          {% endif %}
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div class="empty">ምንም ሰራተኛ የለም</div>
    {% endif %}
  </div>

</div>
<script>
  function promptPin(form){
    const pin = prompt("አዲስ PIN ያስገቡ (4-6 አሃዝ):");
    if(!pin || !/^[0-9]{4,6}$/.test(pin)){ alert("❌ 4-6 አሃዝ ቁጥር ብቻ"); return false; }
    form.querySelector('input[name="new_pin"]').value = pin;
    return true;
  }
</script>
</body></html>
"""

@staff_admin_bp.route("/")
@_require_admin
def index():
    s = _current()
    users = _get(f"{SUPABASE_URL}/rest/v1/fikir_users?select=*&order=role.asc,full_name.asc")
    return render_template_string(STAFF_HTML, users=users, roles=ROLES,
                                  current=s, msg=request.args.get("msg"), error=None, **s)

@staff_admin_bp.route("/create", methods=["POST"])
@_require_admin
def create():
    s = _current()
    full_name = (request.form.get("full_name") or "").strip()[:80]
    username = (request.form.get("username") or "").strip().lower()[:30]
    pin = (request.form.get("pin") or "").strip()
    role = (request.form.get("role") or "cashier")[:20]
    phone = (request.form.get("phone") or "").strip()[:20] or None

    if not full_name or not username or not pin:
        return redirect(url_for("staff_admin.index") + "?msg=❌+ሁሉንም+ያስፈልጋሉ")
    if not pin.isdigit() or len(pin) < 4 or len(pin) > 6:
        return redirect(url_for("staff_admin.index") + "?msg=❌+PIN+4-6+አሃዝ")
    if role not in [c for c,_ in ROLES]:
        role = "cashier"

    payload = {
        "full_name": full_name,
        "username": username,
        "pin_hash": _hash_pin(pin),
        "role": role,
        "phone": phone,
        "is_active": True,
    }
    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/fikir_users",
                          json=payload, headers=_headers("return=representation"), timeout=30)
        if r.status_code in (200, 201):
            uid = r.json()[0]["id"]
            _audit(s["id"], "staff.create", "fikir_users", uid, {"username": username, "role": role})
            return redirect(url_for("staff_admin.index") + f"?msg=✅+{full_name}+ተጨመረ")
        else:
            body = r.text.lower()
            if "duplicate" in body and "username" in body:
                msg = f"❌ '{username}' አስቀድሞ አለ — ሌላ username ይምረጡ"
            elif "duplicate" in body:
                msg = "❌ ይህ መረጃ አስቀድሞ አለ"
            else:
                msg = "❌ " + r.text[:120]
            return redirect(url_for("staff_admin.index") + f"?msg={msg}")
    except Exception as e:
        return redirect(url_for("staff_admin.index") + f"?msg=❌+{str(e)[:60]}")

@staff_admin_bp.route("/reset-pin", methods=["POST"])
@_require_admin
def reset_pin():
    s = _current()
    uid = request.form.get("user_id")
    new_pin = (request.form.get("new_pin") or "").strip()
    if not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 6:
        return redirect(url_for("staff_admin.index") + "?msg=❌+PIN+4-6+አሃዝ")

    try:
        r = requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_users?id=eq.{uid}",
                          json={"pin_hash": _hash_pin(new_pin)},
                          headers=_headers(), timeout=30)
        _audit(s["id"], "staff.reset_pin", "fikir_users", uid)
        return redirect(url_for("staff_admin.index") + "?msg=🔑+PIN+ተቀይሯል")
    except Exception as e:
        return redirect(url_for("staff_admin.index") + f"?msg=❌+{str(e)[:60]}")

@staff_admin_bp.route("/deactivate", methods=["POST"])
@_require_admin
def deactivate():
    s = _current()
    uid = request.form.get("user_id")
    try:
        requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_users?id=eq.{uid}",
                      json={"is_active": False}, headers=_headers(), timeout=30)
        _audit(s["id"], "staff.deactivate", "fikir_users", uid)
        return redirect(url_for("staff_admin.index") + "?msg=🚫+ተሰናክሏል")
    except Exception as e:
        return redirect(url_for("staff_admin.index") + f"?msg=❌+{str(e)[:60]}")

@staff_admin_bp.route("/activate", methods=["POST"])
@_require_admin
def activate():
    s = _current()
    uid = request.form.get("user_id")
    try:
        requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_users?id=eq.{uid}",
                      json={"is_active": True}, headers=_headers(), timeout=30)
        _audit(s["id"], "staff.activate", "fikir_users", uid)
        return redirect(url_for("staff_admin.index") + "?msg=✅+ተነስቷል")
    except Exception as e:
        return redirect(url_for("staff_admin.index") + f"?msg=❌+{str(e)[:60]}")
