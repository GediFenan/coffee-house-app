# ═══════════════════════════════════════════════
# FIKIR — Kitchen Display System (KDS)
# Blueprint: /kitchen/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, requests
from datetime import datetime, timezone, timedelta

kitchen_bp = Blueprint("kitchen", __name__, url_prefix="/kitchen")

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

def _require_kitchen(fn):
    def inner(*a, **kw):
        s = _current()
        if not s: return redirect(url_for("staff.login"))
        if s["role"] not in ("owner","manager","kitchen","barista"):
            return "403 Forbidden", 403
        return fn(*a, **kw)
    inner.__name__ = fn.__name__
    return inner

def _recent_orders():
    """Get today's orders with active statuses"""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = (f"{SUPABASE_URL}/rest/v1/fikir_orders"
           f"?created_at=gte.{cutoff}"
           f"&status=in.(NEW,PAID,PREPARING,READY)"
           f"&order=created_at.asc")
    try:
        r = requests.get(url, headers=_headers(), timeout=30)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print("[KITCHEN ORDERS ERR]", e)
        return []

KDS_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kitchen — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#1a1a1a;color:#fff;padding-bottom:20px}
  .top{background:#2a2a2a;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10;border-bottom:2px solid #6b3e1e}
  .top h1{margin:0;font-size:18px}
  .top .meta{font-size:11px;color:#999;margin-top:2px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:#6b3e1e;padding:8px 14px;border-radius:8px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;padding:14px}
  .ord{background:#2a2a2a;border-radius:12px;padding:16px;border-left:5px solid #d4a24c;box-shadow:0 4px 12px rgba(0,0,0,.4)}
  .ord.preparing{border-left-color:#f0ad4e;background:#2e2519}
  .ord.ready{border-left-color:#2a7d2a;background:#19281a}
  .ord .hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
  .ord .num{font-size:20px;font-weight:800;color:#d4a24c}
  .ord .time{font-size:12px;color:#999}
  .ord .cust{font-size:13px;color:#ccc;margin-bottom:8px}
  .ord .items{background:#1a1a1a;border-radius:8px;padding:10px;font-size:14px;line-height:1.6;margin-bottom:12px;white-space:pre-line}
  .ord .total{font-size:13px;color:#999;margin-bottom:10px}
  .ord .actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .ord .actions button{padding:10px;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;color:#fff}
  .ord .actions .btn1{background:#f0ad4e}
  .ord .actions .btn2{background:#2a7d2a}
  .ord .actions .btn3{background:#888}
  .ord .actions button:active{transform:scale(.97)}
  .ord .actions.full{grid-template-columns:1fr}
  .empty{text-align:center;padding:60px 20px;color:#666;font-size:15px}
  .badge{display:inline-block;font-size:10px;padding:3px 8px;border-radius:20px;font-weight:700;letter-spacing:.5px}
  .badge.new{background:#d4a24c;color:#1a1a1a}
  .badge.paid{background:#d4a24c;color:#1a1a1a}
  .badge.preparing{background:#f0ad4e;color:#1a1a1a}
  .badge.ready{background:#2a7d2a;color:#fff}
  .stats{display:flex;gap:14px;padding:0 14px;font-size:12px;color:#999}
  .stats b{color:#d4a24c}
</style></head><body>
<div class="top">
  <div>
    <h1>🍳 Kitchen Display</h1>
    <div class="meta">{{ full_name }} · {{ role|upper }} · <span id="clock"></span></div>
  </div>
  <a href="{{ url_for('staff.dashboard') }}">← Back</a>
</div>
<div class="stats">
  <span>Orders: <b id="cnt">{{ orders|length }}</b></span>
  <span>Auto-refresh: <b>5s</b></span>
</div>
<div class="grid" id="grid">
{% if orders %}
  {% for o in orders %}
  <div class="ord {{ 'preparing' if o.status == 'PREPARING' else ('ready' if o.status == 'READY' else '') }}">
    <div class="hd">
      <span class="num">#{{ o.id }}</span>
      <span class="time">{{ o.created_at[11:19] if o.created_at else '' }}</span>
    </div>
    <div class="cust">
      <span class="badge {{ o.status|lower }}">{{ o.status }}</span>
      · {{ o.customer }}
    </div>
    <div class="items">{{ o["items"] }}</div>
    <div class="total">Total: {{ "%.2f"|format(o.total|float) }} ETB · {{ (o["payment_method"] or 'cash')|upper }}</div>
    <div class="actions {{ 'full' if o.status == 'READY' else '' }}">
      {% if o.status in ('NEW','PAID') %}
        <form method="POST" action="{{ url_for('kitchen.set_status') }}" style="margin:0">
          <input type="hidden" name="order_id" value="{{ o.id }}">
          <input type="hidden" name="status" value="PREPARING">
          <button type="submit" class="btn1" style="width:100%">▶️ ጀምር</button>
        </form>
        <form method="POST" action="{{ url_for('kitchen.set_status') }}" style="margin:0">
          <input type="hidden" name="order_id" value="{{ o.id }}">
          <input type="hidden" name="status" value="READY">
          <button type="submit" class="btn2" style="width:100%">✅ ተዘጋጅቷል</button>
        </form>
      {% elif o.status == 'PREPARING' %}
        <form method="POST" action="{{ url_for('kitchen.set_status') }}" style="margin:0">
          <input type="hidden" name="order_id" value="{{ o.id }}">
          <input type="hidden" name="status" value="READY">
          <button type="submit" class="btn2" style="width:100%">✅ ተዘጋጅቷል</button>
        </form>
      {% elif o.status == 'READY' %}
        <form method="POST" action="{{ url_for('kitchen.set_status') }}" style="margin:0">
          <input type="hidden" name="order_id" value="{{ o.id }}">
          <input type="hidden" name="status" value="DELIVERED">
          <button type="submit" class="btn2" style="width:100%">🚀 ተላልፏል</button>
        </form>
      {% endif %}
    </div>
  </div>
  {% endfor %}
{% else %}
  <div class="empty" style="grid-column:1/-1">
    🎉 ምንም የሚዘጋጅ ትዕዛዝ የለም<br>
    <span style="font-size:12px;color:#444">አዲስ ትዕዛዞች ሲመጡ እዚህ ይታያሉ</span>
  </div>
{% endif %}
</div>
<script>
  function tick(){
    const d = new Date();
    document.getElementById('clock').textContent = d.toLocaleTimeString();
  }
  tick(); setInterval(tick, 1000);
  setTimeout(() => location.reload(), 5000);
</script>
</body></html>
"""

@kitchen_bp.route("/")
@_require_kitchen
def index():
    s = _current()
    orders = _recent_orders()
    return render_template_string(KDS_HTML, orders=orders, **s)

@kitchen_bp.route("/api/orders")
@_require_kitchen
def api_orders():
    return jsonify(_recent_orders())

@kitchen_bp.route("/status", methods=["POST"])
@_require_kitchen
def set_status():
    s = _current()
    oid = request.form.get("order_id")
    status = request.form.get("status", "PREPARING")
    if status not in ("NEW","PREPARING","READY","DELIVERED","PAID"):
        return "Bad status", 400
    url = f"{SUPABASE_URL}/rest/v1/fikir_orders?id=eq.{oid}"
    try:
        requests.patch(url, json={"status": status}, headers=_headers(), timeout=30)
        # audit
        requests.post(f"{SUPABASE_URL}/rest/v1/fikir_audit_logs",
            json={"user_id": s["id"], "action": f"order.{status.lower()}",
                  "entity": "fikir_orders", "entity_id": str(oid)},
            headers=_headers(), timeout=30)
    except Exception as e:
        print("[KITCHEN STATUS ERR]", e)
    return redirect(url_for("kitchen.index"))
