# ═══════════════════════════════════════════════
# FIKIR — Reports (Sales, Products, Staff, Payments)
# Blueprint: /reports/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify, Response
import os, requests, csv, io
from datetime import datetime, timezone, timedelta, date as dt_date

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

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

def _require_reports(fn):
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
        print("[REPORTS GET ERR]", e)
        return []

def _parse_range():
    """Return (from_date, to_date, from_iso, to_iso) — defaults to last 7 days"""
    today = datetime.now(timezone.utc).date()
    from_s = request.args.get("from") or (today - timedelta(days=6)).isoformat()
    to_s   = request.args.get("to") or today.isoformat()
    try:
        from_d = datetime.fromisoformat(from_s).date()
        to_d = datetime.fromisoformat(to_s).date()
    except Exception:
        from_d = today - timedelta(days=6)
        to_d = today
    from_iso = from_d.strftime("%Y-%m-%dT00:00:00Z")
    to_iso = (to_d + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    return from_d, to_d, from_iso, to_iso

def _fetch_data(from_iso, to_iso):
    orders = _get(f"{SUPABASE_URL}/rest/v1/fikir_orders?created_at=gte.{from_iso}&created_at=lt.{to_iso}&select=*&order=created_at.desc")
    expenses = _get(f"{SUPABASE_URL}/rest/v1/fikir_expenses?created_at=gte.{from_iso}&created_at=lt.{to_iso}&select=*&order=created_at.desc")
    users = _get(f"{SUPABASE_URL}/rest/v1/fikir_users?select=id,full_name,username,role")
    return orders, expenses, users

def _aggregate(orders, expenses, users):
    """Build the full report dict."""
    user_map = {u["id"]: u for u in users}

    paid = [o for o in orders if o.get("status") not in ("CANCELLED",)]
    cancelled = [o for o in orders if o.get("status") == "CANCELLED"]

    total_sales = sum(float(o.get("total") or 0) for o in paid)
    cash_sales = sum(float(o.get("total") or 0) for o in paid if (o.get("payment_method") or "").lower() == "cash")
    telebirr_sales = sum(float(o.get("total") or 0) for o in paid if (o.get("payment_method") or "").lower() == "telebirr")

    total_expenses = sum(float(e.get("amount") or 0) for e in expenses)

    # Product breakdown
    product_counts = {}
    for o in paid:
        items = (o.get("items") or "")
        for part in items.split(","):
            part = part.strip()
            if "×" not in part: continue
            qty_str, name = part.split("×", 1)
            try:
                qty = int(qty_str.strip())
            except ValueError:
                continue
            name = name.strip()
            if not name: continue
            if name not in product_counts:
                product_counts[name] = {"qty": 0, "revenue": 0.0}
            product_counts[name]["qty"] += qty

    # Distribute revenue proportionally by product share within each order
    for o in paid:
        items = (o.get("items") or "")
        parts = []
        total_qty = 0
        for part in items.split(","):
            part = part.strip()
            if "×" not in part: continue
            qty_str, name = part.split("×", 1)
            try:
                qty = int(qty_str.strip())
            except ValueError:
                continue
            name = name.strip()
            parts.append((name, qty))
            total_qty += qty
        if total_qty == 0: continue
        order_total = float(o.get("total") or 0)
        for name, qty in parts:
            share = order_total * (qty / total_qty)
            product_counts[name]["revenue"] += share

    # Staff breakdown
    staff_stats = {}
    for o in paid:
        uid = o.get("user_id")
        if not uid: continue
        if uid not in staff_stats:
            staff_stats[uid] = {"orders": 0, "sales": 0.0}
        staff_stats[uid]["orders"] += 1
        staff_stats[uid]["sales"] += float(o.get("total") or 0)

    staff_rows = []
    for uid, st in staff_stats.items():
        u = user_map.get(uid, {"full_name": f"User #{uid}", "role": "?"})
        staff_rows.append({
            "name": u["full_name"],
            "role": u.get("role", "?"),
            "orders": st["orders"],
            "sales": st["sales"],
        })
    staff_rows.sort(key=lambda x: -x["sales"])

    # Payment breakdown
    payments = {"cash": cash_sales, "telebirr": telebirr_sales}
    other = total_sales - cash_sales - telebirr_sales
    if other > 0.01:
        payments["other"] = other

    # Daily breakdown
    daily = {}
    for o in paid:
        d = (o.get("created_at") or "")[:10]
        if not d: continue
        if d not in daily:
            daily[d] = {"sales": 0.0, "orders": 0}
        daily[d]["sales"] += float(o.get("total") or 0)
        daily[d]["orders"] += 1

    daily_rows = [{"date": d, **v} for d, v in sorted(daily.items())]

    # Expense by category
    exp_by_cat = {}
    for e in expenses:
        c = e.get("category") or "other"
        if c not in exp_by_cat: exp_by_cat[c] = 0.0
        exp_by_cat[c] += float(e.get("amount") or 0)

    return {
        "total_sales": total_sales,
        "orders_count": len(paid),
        "cancelled_count": len(cancelled),
        "cancelled_value": sum(float(o.get("total") or 0) for o in cancelled),
        "avg_order": (total_sales / len(paid)) if paid else 0,
        "cash_sales": cash_sales,
        "telebirr_sales": telebirr_sales,
        "total_expenses": total_expenses,
        "profit": total_sales - total_expenses,
        "products": sorted([{"name": k, **v} for k, v in product_counts.items()], key=lambda x: -x["qty"]),
        "staff": staff_rows,
        "payments": payments,
        "daily": daily_rows,
        "exp_by_cat": sorted([{"cat": k, "amount": v} for k, v in exp_by_cat.items()], key=lambda x: -x["amount"]),
    }

REPORTS_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reports — FIKIR</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:14px;max-width:800px;margin:0 auto}
  .filters{background:#fff;border-radius:12px;padding:12px;display:grid;grid-template-columns:1fr 1fr auto auto;gap:8px;align-items:end;box-shadow:0 2px 8px rgba(107,62,30,.06);margin-bottom:14px}
  .filters label{font-size:11px;font-weight:700;color:#5a3a1e;display:block;margin-bottom:4px}
  .filters input{width:100%;padding:8px;border:2px solid #e0d0c0;border-radius:8px;font-size:13px;outline:none;background:#fff}
  .filters button{padding:9px 14px;background:#6b3e1e;color:#fff;border:none;border-radius:8px;font-weight:700;font-size:13px;cursor:pointer}
  .filters a{padding:9px 12px;background:#fff;color:#6b3e1e;border:2px solid #6b3e1e;border-radius:8px;text-decoration:none;font-size:12px;font-weight:700;text-align:center}
  .range-badge{background:#fff3cd;color:#8a6a00;padding:8px 14px;border-radius:10px;font-size:12px;font-weight:600;margin-bottom:14px;text-align:center}
  .hero{background:linear-gradient(135deg,#6b3e1e,#3b1f0b);color:#fff;border-radius:16px;padding:20px;margin-bottom:14px}
  .hero .lbl{font-size:11px;text-transform:uppercase;letter-spacing:1px;opacity:.85;font-weight:700}
  .hero .big{font-size:32px;font-weight:800;margin:4px 0}
  .hero .sub{font-size:12px;opacity:.9}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
  .card{background:#fff;border-radius:12px;padding:14px;box-shadow:0 2px 8px rgba(107,62,30,.06)}
  .card .lbl{font-size:11px;text-transform:uppercase;font-weight:700;color:#8a6a4a;letter-spacing:.5px}
  .card .val{font-size:22px;font-weight:800;margin-top:4px}
  .card.cash .val{color:#2a7d2a}.card.tele .val{color:#1e6fc4}.card.exp .val{color:#c0392b}.card.prof .val{color:#6b3e1e}
  h2{font-size:13px;color:#6b3e1e;text-transform:uppercase;letter-spacing:1px;margin:20px 0 10px}
  .chart-wrap{background:#fff;border-radius:12px;padding:14px;margin-bottom:14px;box-shadow:0 2px 8px rgba(107,62,30,.06);height:220px;position:relative}
  .tbl{width:100%;border-collapse:collapse;font-size:13px}
  .tbl th{text-align:left;color:#8a6a4a;font-size:11px;text-transform:uppercase;letter-spacing:.5px;padding:8px 6px;border-bottom:2px solid #f0e6d8}
  .tbl td{padding:10px 6px;border-bottom:1px solid #f5ece0}
  .tbl tr:last-child td{border-bottom:none}
  .tbl .num{text-align:right;font-weight:700}
  .rank{display:inline-block;width:24px;height:24px;line-height:24px;text-align:center;background:#6b3e1e;color:#fff;border-radius:50%;font-size:11px;font-weight:800;margin-right:8px}
  .rank.r1{background:#d4a24c}.rank.r2{background:#999}.rank.r3{background:#c08b5c}
  .empty{text-align:center;padding:24px;color:#8a6a4a;font-size:13px}
  .pill{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;background:#f0e6d8;color:#6b3e1e;text-transform:uppercase}
</style></head><body>
<div class="top">
  <h1>📊 Reports</h1>
  <a href="{{ url_for('staff.dashboard') }}">← Back</a>
</div>
<div class="wrap">

  <form class="filters" method="GET">
    <div><label>ከ</label><input type="date" name="from" value="{{ from_s }}"></div>
    <div><label>እስከ</label><input type="date" name="to" value="{{ to_s }}"></div>
    <button type="submit">🔍 አሳይ</button>
    <a href="{{ url_for('reports.export_csv', **{'from': from_s, 'to': to_s}) }}">⬇️ CSV</a>
  </form>

  <div class="range-badge">
    📅 {{ from_s }} — {{ to_s }} ({{ days }} days)
  </div>

  <div class="hero">
    <div class="lbl">ጠቅላላ ሽያጭ</div>
    <div class="big">{{ "%.2f"|format(r.total_sales) }} ETB</div>
    <div class="sub">{{ r.orders_count }} orders · avg {{ "%.2f"|format(r.avg_order) }} · {{ r.cancelled_count }} cancelled</div>
  </div>

  <div class="grid">
    <div class="card cash"><div class="lbl">💵 Cash</div><div class="val">{{ "%.0f"|format(r.cash_sales) }}</div></div>
    <div class="card tele"><div class="lbl">📱 Telebirr</div><div class="val">{{ "%.0f"|format(r.telebirr_sales) }}</div></div>
    <div class="card exp"><div class="lbl">💸 Expenses</div><div class="val">{{ "%.0f"|format(r.total_expenses) }}</div></div>
    <div class="card prof"><div class="lbl">📊 Profit</div><div class="val">{{ "%.0f"|format(r.profit) }}</div></div>
  </div>

  <h2>📈 የቀን ሽያጭ</h2>
  <div class="chart-wrap">
    {% if r.daily %}
    <canvas id="dailyChart"></canvas>
    {% else %}
    <div class="empty">ምንም ውሂብ የለም</div>
    {% endif %}
  </div>

  <h2>☕ ምርቶች (ብዛት)</h2>
  <div class="card" style="padding:8px 14px">
    {% if r.products %}
    <table class="tbl">
      <thead><tr><th>ምርት</th><th style="text-align:right">ብዛት</th><th style="text-align:right">ገቢ</th></tr></thead>
      <tbody>
      {% for p in r.products[:15] %}
      <tr>
        <td>{{ p.name }}</td>
        <td class="num">{{ p.qty }}</td>
        <td class="num">{{ "%.0f"|format(p.revenue) }} ETB</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}<div class="empty">ምንም ሽያጭ የለም</div>{% endif %}
  </div>

  <h2>👥 ሰራተኞች</h2>
  <div class="card" style="padding:8px 14px">
    {% if r.staff %}
    <table class="tbl">
      <thead><tr><th>ስም</th><th style="text-align:right">Orders</th><th style="text-align:right">ሽያጭ</th></tr></thead>
      <tbody>
      {% for s in r.staff %}
      <tr>
        <td><span class="rank {% if loop.index <= 3 %}r{{ loop.index }}{% endif %}">{{ loop.index }}</span>{{ s.name }} <span class="pill">{{ s.role }}</span></td>
        <td class="num">{{ s.orders }}</td>
        <td class="num">{{ "%.0f"|format(s.sales) }} ETB</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}<div class="empty">ምንም የሰራተኛ ሽያጭ የለም</div>{% endif %}
  </div>

  <h2>💸 ወጪዎች</h2>
  <div class="card" style="padding:8px 14px">
    {% if r.exp_by_cat %}
    <table class="tbl">
      {% for e in r.exp_by_cat %}
      <tr><td>{{ e.cat }}</td><td class="num" style="color:#c0392b">-{{ "%.0f"|format(e.amount) }} ETB</td></tr>
      {% endfor %}
    </table>
    {% else %}<div class="empty">ምንም ወጪ የለም</div>{% endif %}
  </div>

</div>

{% if r.daily %}
<script>
  const ctx = document.getElementById('dailyChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: {{ r.daily | map(attribute='date') | list | tojson }},
      datasets: [{
        label: 'Sales (ETB)',
        data: {{ r.daily | map(attribute='sales') | list | tojson }},
        backgroundColor: '#6b3e1e',
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { font: { size: 10 } } },
        x: { ticks: { font: { size: 10 } } }
      }
    }
  });
</script>
{% endif %}
</body></html>
"""

@reports_bp.route("/")
@_require_reports
def index():
    s = _current()
    from_d, to_d, from_iso, to_iso = _parse_range()
    orders, expenses, users = _fetch_data(from_iso, to_iso)
    r = _aggregate(orders, expenses, users)
    days = (to_d - from_d).days + 1
    return render_template_string(REPORTS_HTML,
        r=r, from_s=from_d.isoformat(), to_s=to_d.isoformat(), days=days, **s)

@reports_bp.route("/export.csv")
@_require_reports
def export_csv():
    s = _current()
    from_d, to_d, from_iso, to_iso = _parse_range()
    orders, expenses, users = _fetch_data(from_iso, to_iso)
    user_map = {u["id"]: u for u in users}

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["FIKIR COFFEE HOUSE — Report"])
    w.writerow([f"From: {from_d.isoformat()}", f"To: {to_d.isoformat()}"])
    w.writerow([])
    w.writerow(["Order ID","Date","Customer","Items","Total","Payment","Status","Staff"])
    for o in orders:
        w.writerow([
            o.get("id"),
            (o.get("created_at") or "")[:19].replace("T"," "),
            o.get("customer") or "",
            o.get("items") or "",
            o.get("total") or 0,
            o.get("payment_method") or "",
            o.get("status") or "",
            (user_map.get(o.get("user_id"), {}) or {}).get("full_name", ""),
        ])
    w.writerow([])
    w.writerow(["Expenses"])
    w.writerow(["Date","Category","Amount","Paid From","Note","User"])
    for e in expenses:
        w.writerow([
            (e.get("created_at") or "")[:19].replace("T"," "),
            e.get("category") or "",
            e.get("amount") or 0,
            e.get("paid_from") or "",
            e.get("note") or "",
            (user_map.get(e.get("user_id"), {}) or {}).get("full_name", ""),
        ])

    csv_data = buf.getvalue()
    filename = f"fikir_report_{from_d.isoformat()}_{to_d.isoformat()}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@reports_bp.route("/api")
@_require_reports
def api():
    from_d, to_d, from_iso, to_iso = _parse_range()
    orders, expenses, users = _fetch_data(from_iso, to_iso)
    r = _aggregate(orders, expenses, users)
    return jsonify(r)
