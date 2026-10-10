# ═══════════════════════════════════════════════
# FIKIR — Expenses (ወጪዎች)
# Blueprint: /expenses/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, requests
from datetime import datetime, timezone, timedelta

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")

SUPABASE_URL = "https://skswircyorzpbcioljcs.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrc3dpcmN5b3J6cGJjaW9samNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MjMyMzQsImV4cCI6MjEwMzQ5OTIzNH0.ntS52ih33wprDiQ4YGrNzWchuuWqfzc1iyv7_xi_qPM"

CATEGORIES = [
    ("milk",       "🥛 Milk"),
    ("sugar",      "🍬 Sugar"),
    ("coffee_bean","☕ Coffee Beans"),
    ("gas",        "🔥 Gas / Fuel"),
    ("water",      "💧 Water"),
    ("cups",       "🥤 Cups / Packaging"),
    ("salary",     "💰 Salary / Wages"),
    ("rent",       "🏠 Rent"),
    ("utilities",  "💡 Utilities"),
    ("transport",  "🚗 Transport"),
    ("maintenance","🔧 Maintenance"),
    ("other",      "📦 Other"),
]

PAY_FROM = [
    ("cash",     "💵 Cash"),
    ("telebirr", "📱 Telebirr"),
    ("bank",     "🏦 Bank"),
]

def _headers(prefer=None):
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    if prefer: h["Prefer"] = prefer
    return h

def _current():
    if "staff_id" not in session: return None
    return {"id": session.get("staff_id"), "username": session.get("staff_username"),
            "full_name": session.get("staff_name"), "role": session.get("staff_role")}

def _require_expense(fn):
    def inner(*a, **kw):
        s = _current()
        if not s: return redirect(url_for("staff.login"))
        if s["role"] not in ("owner","manager","cashier"):
            return "403 — Owner/Manager/Cashier only", 403
        return fn(*a, **kw)
    inner.__name__ = fn.__name__
    return inner

def _get(url):
    try:
        r = requests.get(url, headers=_headers(), timeout=30)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print("[EXPENSES GET ERR]", e)
        return []

def _get_open_shift(user_id):
    url = f"{SUPABASE_URL}/rest/v1/fikir_shifts?user_id=eq.{user_id}&status=eq.open&order=opened_at.desc&limit=1"
    try:
        r = requests.get(url, headers=_headers(), timeout=30)
        return r.json()[0] if (r.status_code==200 and r.json()) else None
    except Exception:
        return None

def _today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _today_expenses():
    today = _today_str()
    url = (f"{SUPABASE_URL}/rest/v1/fikir_expenses"
           f"?created_at=gte.{today}T00:00:00Z"
           f"&order=created_at.desc")
    return _get(url)

def _cat_label(code):
    for c, label in CATEGORIES:
        if c == code: return label
    return code

def _pay_label(code):
    for c, label in PAY_FROM:
        if c == code: return label
    return code

EXP_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Expenses — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:16px;max-width:640px;margin:0 auto}
  .card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 8px rgba(107,62,30,.06);margin-bottom:14px}
  .card h2{margin:0 0 14px;font-size:15px;color:#6b3e1e;text-transform:uppercase;letter-spacing:.5px}
  label{display:block;font-size:12px;font-weight:700;color:#5a3a1e;margin-bottom:6px;margin-top:12px}
  label:first-child{margin-top:0}
  select,input[type=number],input[type=text],input[type=date]{width:100%;padding:12px;border:2px solid #e0d0c0;border-radius:10px;font-size:15px;outline:none;background:#fff;color:#3b1f0b;font-family:inherit}
  select:focus,input:focus{border-color:#6b3e1e}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  button{width:100%;padding:15px;background:#6b3e1e;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-top:18px}
  button:active{transform:scale(.98)}
  .sum{display:flex;justify-content:space-between;padding:14px 18px;background:#6b3e1e;color:#fff;border-radius:14px;margin-bottom:14px}
  .sum .lbl{font-size:11px;text-transform:uppercase;letter-spacing:1px;opacity:.85}
  .sum .val{font-size:26px;font-weight:800;margin-top:4px}
  .exp{background:#fff;border-radius:12px;padding:14px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:flex-start;box-shadow:0 1px 4px rgba(107,62,30,.05)}
  .exp .nm{font-weight:700;font-size:14px}
  .exp .meta{font-size:11px;color:#8a6a4a;margin-top:4px}
  .exp .amt{font-weight:800;color:#c0392b;font-size:16px;white-space:nowrap}
  .empty{text-align:center;padding:30px 20px;color:#8a6a4a;font-size:14px}
  .err{background:#ffe0e0;color:#c00;padding:10px;border-radius:8px;font-size:13px;margin-bottom:14px}
  .shift-info{background:#e8f5e9;border-left:4px solid #2a7d2a;padding:10px 12px;border-radius:8px;font-size:12px;color:#3b1f0b;margin-bottom:14px;line-height:1.5}
  .shift-info.warn{background:#fff3cd;border-left-color:#f0ad4e}
  .chip{display:inline-block;background:#f0e6d8;color:#6b3e1e;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:700;margin-right:6px}
</style></head><body>
<div class="top">
  <h1>💸 Expenses</h1>
  <a href="{{ url_for('staff.dashboard') }}">← Back</a>
</div>
<div class="wrap">

  <div class="sum">
    <div>
      <div class="lbl">የዛሬ ወጪ</div>
      <div class="val">{{ "%.2f"|format(total_today) }} ETB</div>
    </div>
    <div style="text-align:right">
      <div class="lbl">Count</div>
      <div class="val">{{ expenses|length }}</div>
    </div>
  </div>

  {% if open_shift %}
  <div class="shift-info">
    🟢 ክፍት Shift — Cash ወጪዎች በራስ-ሰር ከ Expected Cash ይቀነሳሉ
  </div>
  {% else %}
  <div class="shift-info warn">
    🟡 ምንም ክፍት Shift የለም — ወጪ ማስገባት ይቻላል ግን ከ shift ጋር አይገናኝም
  </div>
  {% endif %}

  <div class="card">
    <h2>➕ አዲስ ወጪ</h2>
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
    <form method="POST" action="{{ url_for('expenses.add') }}">
      <label>Category</label>
      <select name="category" required>
        {% for code, label in categories %}
        <option value="{{ code }}">{{ label }}</option>
        {% endfor %}
      </select>

      <div class="grid2">
        <div>
          <label>Amount (ETB)</label>
          <input name="amount" type="number" step="0.01" min="0.01" required inputmode="decimal" placeholder="0.00" autofocus>
        </div>
        <div>
          <label>Paid From</label>
          <select name="paid_from" required>
            {% for code, label in pay_from %}
            <option value="{{ code }}">{{ label }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <label>Note (optional)</label>
      <input name="note" type="text" placeholder="ለምሳሌ: 5L ወተት ከገበያ" maxlength="200">

      <button type="submit">💸 ወጪ መዝግብ</button>
    </form>
  </div>

  <h2 style="font-size:14px;color:#6b3e1e;text-transform:uppercase;letter-spacing:1px;margin:20px 0 10px">📋 የዛሬ ወጪዎች</h2>
  {% if expenses %}
    {% for e in expenses %}
    <div class="exp">
      <div>
        <div class="nm">{{ cat_labels[e.category] if e.category in cat_labels else e.category }}</div>
        <div class="meta">
          <span class="chip">{{ pay_labels[e.paid_from] if e.paid_from in pay_labels else e.paid_from }}</span>
          {{ e.created_at[11:16] }}
          {% if e.note %}· {{ e.note }}{% endif %}
        </div>
      </div>
      <div class="amt">-{{ "%.2f"|format(e.amount|float) }} ETB</div>
    </div>
    {% endfor %}
  {% else %}
    <div class="card empty">ምንም የዛሬ ወጪ የለም</div>
  {% endif %}

</div>
</body></html>
"""

@expenses_bp.route("/", methods=["GET"])
@_require_expense
def index():
    s = _current()
    expenses = _today_expenses()
    total_today = sum(float(e.get("amount") or 0) for e in expenses)
    open_shift = _get_open_shift(s["id"])
    return render_template_string(EXP_HTML,
        expenses=expenses,
        total_today=total_today,
        open_shift=open_shift,
        categories=CATEGORIES,
        pay_from=PAY_FROM,
        cat_labels=dict(CATEGORIES),
        pay_labels=dict(PAY_FROM),
        error=None,
        **s)

@expenses_bp.route("/add", methods=["POST"])
@_require_expense
def add():
    s = _current()
    try:
        amount = float(request.form.get("amount") or 0)
    except ValueError:
        amount = 0

    if amount <= 0:
        expenses = _today_expenses()
        total_today = sum(float(e.get("amount") or 0) for e in expenses)
        return render_template_string(EXP_HTML,
            expenses=expenses, total_today=total_today,
            open_shift=_get_open_shift(s["id"]),
            categories=CATEGORIES, pay_from=PAY_FROM,
            cat_labels=dict(CATEGORIES), pay_labels=dict(PAY_FROM),
            error="ትክክለኛ ቁጥር ያስገቡ", **s)

    category = (request.form.get("category") or "other")[:40]
    paid_from = (request.form.get("paid_from") or "cash")[:20]
    note = (request.form.get("note") or "")[:300]

    open_shift = _get_open_shift(s["id"])
    payload = {
        "user_id": s["id"],
        "category": category,
        "amount": round(amount, 2),
        "paid_from": paid_from,
        "note": note,
    }
    if open_shift:
        payload["shift_id"] = open_shift["id"]

    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/fikir_expenses",
                          json=payload, headers=_headers("return=representation"), timeout=30)
        if r.status_code in (200, 201):
            # Audit
            try:
                requests.post(f"{SUPABASE_URL}/rest/v1/fikir_audit_logs",
                    json={"user_id": s["id"], "action": "expense.create",
                          "entity": "fikir_expenses", "entity_id": str(r.json()[0]["id"]),
                          "new_value": payload},
                    headers=_headers(), timeout=30)
            except Exception:
                pass
            # Telegram notify
            try:
                from notifications_routes import notify_expense
                notify_expense(category, amount, paid_from, note, s.get("full_name",""))
            except Exception as e:
                print("[TG EXPENSE ERR]", e)
    except Exception as e:
        print("[EXPENSE ADD ERR]", e)

    return redirect(url_for("expenses.index"))

@expenses_bp.route("/api/today")
@_require_expense
def api_today():
    expenses = _today_expenses()
    return jsonify({
        "count": len(expenses),
        "total": sum(float(e.get("amount") or 0) for e in expenses),
        "expenses": expenses,
    })
