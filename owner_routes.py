# ═══════════════════════════════════════════════
# FIKIR — Owner Live Dashboard (mobile-first)
# Blueprint: /owner/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, requests
from datetime import datetime, timezone, timedelta

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")

SUPABASE_URL = "https://skswircyorzpbcioljcs.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrc3dpcmN5b3J6cGJjaW9samNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MjMyMzQsImV4cCI6MjEwMzQ5OTIzNH0.ntS52ih33wprDiQ4YGrNzWchuuWqfzc1iyv7_xi_qPM"

def _headers(prefer=None):
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    if prefer: h["Prefer"] = prefer
    return h

def _current():
    if "staff_id" not in session: return None
    return {"id": session.get("staff_id"), "username": session.get("staff_username"),
            "full_name": session.get("staff_name"), "role": session.get("staff_role")}

def _require_owner(fn):
    def inner(*a, **kw):
        s = _current()
        if not s: return redirect(url_for("staff.login"))
        if s["role"] not in ("owner","manager"):
            return "403 — Owner only", 403
        return fn(*a, **kw)
    inner.__name__ = fn.__name__
    return inner

def _today_range():
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return (start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            now.strftime("%Y-%m-%dT%H:%M:%SZ"))

def _get(url):
    try:
        r = requests.get(url, headers=_headers(), timeout=30)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print("[OWNER GET ERR]", e)
        return []

def _low_stock_alerts():
    """Return list of {name, icon, unit, current, reorder, status}"""
    ings = _get(f"{SUPABASE_URL}/rest/v1/fikir_ingredients?is_active=eq.true&select=*&order=current_stock.asc")
    alerts = []
    for i in ings:
        cur = float(i.get("current_stock") or 0)
        reorder = float(i.get("reorder_level") or 0)
        if cur <= 0:
            st = "critical"
        elif cur <= reorder:
            st = "warning"
        else:
            continue
        alerts.append({
            "name": i.get("name"),
            "icon": i.get("icon") or "📦",
            "unit": i.get("unit"),
            "current": cur,
            "reorder": reorder,
            "status": st,
        })
    return alerts

def _today_stats():
    """Calculate stats. If shift is open, use shift-scope (opening → now).
    Otherwise use calendar today."""
    # 1. Look for open shift
    open_shifts = _get(f"{SUPABASE_URL}/rest/v1/fikir_shifts?status=eq.open&order=opened_at.desc&limit=1")
    open_shift = open_shifts[0] if open_shifts else None

    # 2. Determine time range
    if open_shift:
        # Shift scope: from shift opened_at → now
        start = open_shift["opened_at"]  # already ISO with TZ
        # Normalize to strftime pattern for URL safety
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            start = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            start = start[:19] + "Z"
    else:
        # Calendar today
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 3. Fetch data from start time
    orders = _get(f"{SUPABASE_URL}/rest/v1/fikir_orders?created_at=gte.{start}&select=*&order=created_at.desc")
    expenses = _get(f"{SUPABASE_URL}/rest/v1/fikir_expenses?created_at=gte.{start}&select=*&order=created_at.desc")
    users = _get(f"{SUPABASE_URL}/rest/v1/fikir_users?select=id,full_name,username,role")

    total_sales = 0
    cash_sales = 0
    telebirr_sales = 0
    cancelled = 0
    cups = 0
    by_staff = {}

    for o in orders:
        if o.get("status") == "CANCELLED":
            cancelled += 1
            continue
        amt = float(o.get("total") or 0)
        total_sales += amt
        pm = (o.get("payment_method") or "cash").lower()
        if pm == "cash":
            cash_sales += amt
        elif pm == "telebirr":
            telebirr_sales += amt
        items = (o.get("items") or "")
        try:
            cups += sum(int(part.strip().split("×")[0].strip()) for part in items.split(",") if "×" in part)
        except Exception:
            pass
        uid = o.get("user_id")
        if uid:
            by_staff[uid] = by_staff.get(uid, 0) + amt

    total_expenses = sum(float(e.get("amount") or 0) for e in expenses)
    cash_expenses = sum(float(e.get("amount") or 0) for e in expenses if (e.get("paid_from") or "cash") == "cash")

    expected_cash = 0
    if open_shift:
        expected_cash = float(open_shift.get("opening_cash") or 0) + cash_sales - cash_expenses

    staff_map = {u["id"]: u for u in users}

    return {
        "total_sales": total_sales,
        "cash_sales": cash_sales,
        "telebirr_sales": telebirr_sales,
        "cancelled": cancelled,
        "orders_count": len([o for o in orders if o.get("status") != "CANCELLED"]),
        "cups": cups,
        "total_expenses": total_expenses,
        "cash_expenses": cash_expenses,
        "profit": total_sales - total_expenses,
        "expected_cash": expected_cash,
        "open_shift": open_shift,
        "by_staff": [(staff_map.get(uid, {"full_name": f"#{uid}"})["full_name"], amt)
                     for uid, amt in sorted(by_staff.items(), key=lambda x: -x[1])],
        "recent_orders": sorted(orders, key=lambda x: x.get("created_at", ""), reverse=True)[:10],
        "scope": "shift" if open_shift else "today",
        "low_stock": _low_stock_alerts(),
    }

OWNER_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Owner Dashboard — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:linear-gradient(135deg,#3b1f0b,#6b3e1e);color:#fff;padding:18px 20px}
  .top h1{margin:0;font-size:18px}
  .top .meta{font-size:12px;opacity:.85;margin-top:4px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px;float:right;margin-top:-32px}
  .wrap{padding:16px;max-width:720px;margin:0 auto}
  .hero{background:#fff;border-radius:16px;padding:20px;margin-bottom:14px;box-shadow:0 4px 16px rgba(107,62,30,.08)}
  .hero .lbl{font-size:12px;color:#8a6a4a;text-transform:uppercase;letter-spacing:1px;font-weight:700}
  .hero .big{font-size:36px;font-weight:800;color:#6b3e1e;margin:4px 0 2px}
  .hero .sub{font-size:13px;color:#8a6a4a}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}
  .grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:14px}
  .card{background:#fff;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(107,62,30,.06)}
  .card .lbl{font-size:11px;color:#8a6a4a;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
  .card .val{font-size:22px;font-weight:800;color:#3b1f0b;margin-top:4px}
  .card.cash .val{color:#2a7d2a}
  .card.tele .val{color:#1e6fc4}
  .card.exp .val{color:#c0392b}
  .card.prof .val{color:#6b3e1e}
  h2{font-size:14px;color:#6b3e1e;margin:20px 0 10px;text-transform:uppercase;letter-spacing:1px}
  .shift-live{background:#e8f5e9;border-left:4px solid #2a7d2a;padding:12px;border-radius:10px;margin-bottom:14px;font-size:13px;line-height:1.7}
  .shift-live.none{background:#fff3cd;border-left-color:#f0ad4e}
  .shift-live b{color:#2a7d2a}
  .ord{background:#fff;border-radius:10px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;font-size:13px;box-shadow:0 1px 4px rgba(107,62,30,.05)}
  .ord .id{font-weight:800;color:#6b3e1e}
  .ord .amt{font-weight:800}
  .ord .st{font-size:10px;padding:3px 8px;border-radius:20px;background:#f0e6d8;color:#6b3e1e;font-weight:700;margin-left:6px}
  .ord .st.PAID{background:#d4edda;color:#1e7e34}
  .ord .st.CANCELLED{background:#f8d7da;color:#a02020}
  .ord .st.PREPARING{background:#fff3cd;color:#8a6a00}
  .ord .st.READY{background:#d4edda;color:#1e7e34}
  .staff-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f0e6d8;font-size:13px}
  .staff-row:last-child{border-bottom:none}
  .staff-row .nm{font-weight:600}
  .staff-row .amt{font-weight:800;color:#6b3e1e}
  .alerts{background:#fff;border-radius:14px;padding:14px;margin-bottom:14px}
  .alert-row{display:flex;align-items:center;gap:8px;padding:8px 0;font-size:13px;border-bottom:1px solid #f5ece0}
  .alert-row:last-child{border-bottom:none}
  .dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
  .dot.g{background:#2a7d2a}.dot.y{background:#f0ad4e}.dot.r{background:#c0392b}
  .actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}
  .actions a{padding:14px;border-radius:12px;text-align:center;text-decoration:none;font-weight:700;font-size:14px}
  .actions .a1{background:#6b3e1e;color:#fff}
  .actions .a2{background:#fff;color:#6b3e1e;border:2px solid #6b3e1e}
</style></head><body>
<div class="top">
  <h1>👑 Owner Dashboard</h1>
  <div class="meta">{{ full_name }} · Live · <span id="clock"></span></div>
  <a href="{{ url_for('staff.dashboard') }}">Staff →</a>
</div>
<div class="wrap">

  <div class="hero">
    <div class="lbl">{% if stats.scope == "shift" %}የ Shift ሽያጭ · Shift Sales{% else %}የዛሬ ሽያጭ · Today's Sales{% endif %}</div>
    <div class="big">{{ "%.2f"|format(stats.total_sales) }} ETB</div>
    <div class="sub">{{ stats.orders_count }} orders · {{ stats.cups }} cups · {{ stats.cancelled }} cancelled</div>
  </div>

  <div class="grid3">
    <div class="card cash"><div class="lbl">💵 Cash</div><div class="val">{{ "%.0f"|format(stats.cash_sales) }}</div></div>
    <div class="card tele"><div class="lbl">📱 Telebirr</div><div class="val">{{ "%.0f"|format(stats.telebirr_sales) }}</div></div>
    <div class="card exp"><div class="lbl">💸 Expenses</div><div class="val">{{ "%.0f"|format(stats.total_expenses) }}</div></div>
  </div>

  <div class="grid2">
    <div class="card prof"><div class="lbl">📊 Profit (est.)</div><div class="val">{{ "%.0f"|format(stats.profit) }} ETB</div></div>
    <div class="card"><div class="lbl">🏦 Expected Cash</div><div class="val">{{ "%.0f"|format(stats.expected_cash) }} ETB</div></div>
  </div>

  {% if stats.open_shift %}
  <div class="shift-live">
    🟢 <b>Shift ተከፍቷል</b> · ከ {{ stats.open_shift.opened_at[:19].replace('T',' ') }}<br>
    Opening Cash: <b>{{ "%.2f"|format(stats.open_shift.opening_cash|float) }} ETB</b><br>
    Cash ወጪዎች: <b>-{{ "%.2f"|format(stats.cash_expenses) }} ETB</b>
  </div>
  {% else %}
  <div class="shift-live none">
    🟡 <b>ምንም ክፍት Shift የለም</b> — ሽያጭ ከመጀመሩ በፊት Shift ይክፈቱ
  </div>
  {% endif %}

  {% if stats.low_stock %}
  <h2>⚠️ የእቃ ማስጠንቀቂያ</h2>
  <div class="card" style="padding:8px 14px">
    {% for a in stats.low_stock %}
    <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid #f5ece0">
      <div>
        <div style="font-weight:700;font-size:14px">
          {{ a.icon }} {{ a.name }}
          <span class="st {{ 'critical' if a.status=='critical' else 'warning' }}" style="font-size:9px;padding:2px 8px;border-radius:20px;font-weight:800;margin-left:6px;{% if a.status=='critical' %}background:#f8d7da;color:#a02020{% else %}background:#fff3cd;color:#8a6a00{% endif %}">
            {{ 'OUT' if a.status=='critical' else 'LOW' }}
          </span>
        </div>
        <div style="font-size:11px;color:#8a6a4a;margin-top:3px">
          {{ "%.0f"|format(a.current) }} {{ a.unit }} · min {{ "%.0f"|format(a.reorder) }}
        </div>
      </div>
      {% if role in ('owner','manager') %}
      <a href="{{ url_for('inventory.purchase') }}" style="background:#6b3e1e;color:#fff;text-decoration:none;padding:8px 14px;border-radius:8px;font-size:12px;font-weight:700">🛒 ግዛ</a>
      {% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <h2>🕐 የቅርብ ትዕዛዞች</h2>
  <div class="card" style="padding:8px">
    {% if stats.recent_orders %}
      {% for o in stats.recent_orders %}
      <div class="ord">
        <div>
          <span class="id">#{{ o.id }}</span>
          <span class="st {{ o.status }}">{{ o.status }}</span>
          <div style="font-size:11px;color:#8a6a4a;margin-top:2px">{{ o.customer }} · {{ (o.payment_method or 'cash')|upper }}</div>
        </div>
        <div class="amt">{{ "%.2f"|format(o.total|float) }} ETB</div>
      </div>
      {% endfor %}
    {% else %}
      <div style="text-align:center;padding:24px;color:#8a6a4a;font-size:13px">ምንም ትዕዛዝ የለም</div>
    {% endif %}
  </div>

  {% if stats.by_staff %}
  <h2>👥 የሰራተኛ ሽያጭ</h2>
  <div class="card">
    {% for name, amt in stats.by_staff %}
    <div class="staff-row"><span class="nm">{{ name }}</span><span class="amt">{{ "%.2f"|format(amt) }} ETB</span></div>
    {% endfor %}
  </div>
  {% endif %}

  <div class="actions">
    <a class="a1" href="{{ url_for('pos.index') }}">🧾 POS ክፈት</a>
    <a class="a2" href="{{ url_for('kitchen.index') }}">🍳 Kitchen</a>
    <a class="a2" href="{{ url_for('expenses.index') }}">💸 ወጪዎች</a>
    <a class="a2" href="{{ url_for('staff_admin.index') }}">👥 Staff</a>
    <a class="a2" href="{{ url_for('reports.index') }}">📊 ሪፖርቶች</a>
    <a class="a2" href="{{ url_for('inventory.index') }}">📦 Inventory</a>
  </div>

</div>
<script>
  function tick(){ document.getElementById('clock').textContent = new Date().toLocaleTimeString(); }
  tick(); setInterval(tick, 1000);
  setTimeout(() => location.reload(), 30000);  // auto-refresh 30s
</script>
</body></html>
"""

@owner_bp.route("/")
@_require_owner
def dashboard():
    s = _current()
    stats = _today_stats()
    return render_template_string(OWNER_HTML, stats=stats, **s)

@owner_bp.route("/api/stats")
@_require_owner
def api_stats():
    return jsonify(_today_stats())
