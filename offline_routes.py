# ═══════════════════════════════════════════════
# FIKIR — Offline Mode (SQLite cache + sync)
# Blueprint: /offline/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, sqlite3, json, requests, threading, time
from datetime import datetime, timezone

offline_bp = Blueprint("offline", __name__, url_prefix="/offline")

SUPABASE_URL = "https://skswircyorzpbcioljcs.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrc3dpcmN5b3J6cGJjaW9samNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MjMyMzQsImV4cCI6MjEwMzQ5OTIzNH0.ntS52ih33wprDiQ4YGrNzWchuuWqfzc1iyv7_xi_qPM"

DB_PATH = os.path.expanduser("~/coffee/offline.db")

def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS pending_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            synced INTEGER NOT NULL DEFAULT 0,
            supabase_id INTEGER,
            error TEXT
        );
        CREATE TABLE IF NOT EXISTS pending_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            synced INTEGER NOT NULL DEFAULT 0,
            supabase_id INTEGER,
            error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_po_synced ON pending_orders(synced);
        CREATE INDEX IF NOT EXISTS idx_pe_synced ON pending_expenses(synced);
    """)
    con.commit()
    con.close()

def _headers(prefer=None):
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    if prefer: h["Prefer"] = prefer
    return h

def is_online(timeout=3):
    """Quick connectivity check to Supabase"""
    try:
        r = requests.head(SUPABASE_URL, timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False

def queue_order(payload):
    """Save an order to offline queue"""
    _init_db()
    con = sqlite3.connect(DB_PATH)
    cur = con.execute(
        "INSERT INTO pending_orders (payload, created_at, synced) VALUES (?, ?, 0)",
        (json.dumps(payload), datetime.now(timezone.utc).isoformat())
    )
    oid = cur.lastrowid
    con.commit()
    con.close()
    print(f"[OFFLINE] Order queued (local id={oid})")
    return oid

def queue_expense(payload):
    _init_db()
    con = sqlite3.connect(DB_PATH)
    cur = con.execute(
        "INSERT INTO pending_expenses (payload, created_at, synced) VALUES (?, ?, 0)",
        (json.dumps(payload), datetime.now(timezone.utc).isoformat())
    )
    eid = cur.lastrowid
    con.commit()
    con.close()
    return eid

def try_sync():
    """Attempt to push queued items to Supabase"""
    _init_db()
    if not is_online():
        return {"ok": False, "reason": "offline", "orders": 0, "expenses": 0}

    synced_orders = 0
    synced_expenses = 0

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # Orders
    rows = con.execute("SELECT * FROM pending_orders WHERE synced=0 ORDER BY id ASC LIMIT 50").fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload"])
            r = requests.post(f"{SUPABASE_URL}/rest/v1/fikir_orders",
                             json=payload, headers=_headers("return=representation"), timeout=20)
            if r.status_code in (200, 201):
                sb_id = r.json()[0]["id"]
                con.execute("UPDATE pending_orders SET synced=1, supabase_id=? WHERE id=?",
                            (sb_id, row["id"]))
                con.commit()
                synced_orders += 1
                print(f"[SYNC] Order {row['id']} → Supabase #{sb_id}")
            else:
                con.execute("UPDATE pending_orders SET error=? WHERE id=?",
                            (r.text[:200], row["id"]))
                con.commit()
        except Exception as e:
            print(f"[SYNC] Order {row['id']} error: {e}")

    # Expenses
    rows = con.execute("SELECT * FROM pending_expenses WHERE synced=0 ORDER BY id ASC LIMIT 50").fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload"])
            r = requests.post(f"{SUPABASE_URL}/rest/v1/fikir_expenses",
                             json=payload, headers=_headers("return=representation"), timeout=20)
            if r.status_code in (200, 201):
                sb_id = r.json()[0]["id"]
                con.execute("UPDATE pending_expenses SET synced=1, supabase_id=? WHERE id=?",
                            (sb_id, row["id"]))
                con.commit()
                synced_expenses += 1
                print(f"[SYNC] Expense {row['id']} → Supabase #{sb_id}")
            else:
                con.execute("UPDATE pending_expenses SET error=? WHERE id=?",
                            (r.text[:200], row["id"]))
                con.commit()
        except Exception as e:
            print(f"[SYNC] Expense {row['id']} error: {e}")

    con.close()
    return {"ok": True, "orders": synced_orders, "expenses": synced_expenses}

def pending_count():
    _init_db()
    con = sqlite3.connect(DB_PATH)
    oc = con.execute("SELECT COUNT(*) FROM pending_orders WHERE synced=0").fetchone()[0]
    ec = con.execute("SELECT COUNT(*) FROM pending_expenses WHERE synced=0").fetchone()[0]
    con.close()
    return {"orders": oc, "expenses": ec}

def pending_orders_list(limit=100):
    _init_db()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM pending_orders WHERE synced=0 ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    out = []
    for r in rows:
        try: p = json.loads(r["payload"])
        except Exception: p = {}
        out.append({
            "local_id": r["id"],
            "created_at": r["created_at"],
            "customer": p.get("customer"),
            "total": p.get("total"),
            "items": p.get("items"),
            "payment_method": p.get("payment_method"),
            "error": r["error"],
        })
    con.close()
    return out

def synced_log(limit=50):
    _init_db()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM pending_orders WHERE synced=1 ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    out = []
    for r in rows:
        try: p = json.loads(r["payload"])
        except Exception: p = {}
        out.append({
            "local_id": r["id"],
            "supabase_id": r["supabase_id"],
            "created_at": r["created_at"],
            "customer": p.get("customer"),
            "total": p.get("total"),
        })
    con.close()
    return out

# ═══════════════════════════════════════════════
# BACKGROUND SYNC THREAD (auto-retry every 30s)
# ═══════════════════════════════════════════════
_sync_started = False

def _start_background_sync():
    global _sync_started
    if _sync_started:
        return
    _sync_started = True
    def loop():
        while True:
            try:
                time.sleep(30)
                cnt = pending_count()
                if cnt["orders"] > 0 or cnt["expenses"] > 0:
                    result = try_sync()
                    if result.get("ok") and (result.get("orders") or result.get("expenses")):
                        print(f"[BG SYNC] {result}")
            except Exception as e:
                print("[BG SYNC ERR]", e)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    print("[OFFLINE] Background sync thread started")

# ═══════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════
@offline_bp.route("/status")
def status():
    online = is_online()
    cnt = pending_count()
    return jsonify({
        "online": online,
        "pending": cnt,
        "db_path": DB_PATH,
    })

@offline_bp.route("/sync", methods=["POST"])
def sync_now():
    result = try_sync()
    return jsonify(result)

OFFLINE_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline — FIKIR</title>
<style>
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:16px;max-width:640px;margin:0 auto}
  .status{background:#fff;border-radius:14px;padding:20px;margin-bottom:14px;box-shadow:0 2px 8px rgba(107,62,30,.06);text-align:center}
  .status .dot{width:14px;height:14px;border-radius:50%;display:inline-block;margin-right:8px;vertical-align:middle}
  .dot.green{background:#2a7d2a;box-shadow:0 0 0 4px rgba(42,125,42,.2)}
  .dot.red{background:#c0392b;box-shadow:0 0 0 4px rgba(192,57,43,.2)}
  .status .lbl{font-size:18px;font-weight:800}
  .status .sub{font-size:12px;color:#8a6a4a;margin-top:6px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}
  .card{background:#fff;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(107,62,30,.06);text-align:center}
  .card .num{font-size:32px;font-weight:800;color:#6b3e1e}
  .card .lbl{font-size:11px;text-transform:uppercase;color:#8a6a4a;font-weight:700;letter-spacing:.5px;margin-top:4px}
  .card.warn .num{color:#c0392b}
  h2{font-size:14px;color:#6b3e1e;text-transform:uppercase;letter-spacing:.5px;margin:20px 0 10px}
  .item{background:#fff;border-radius:12px;padding:14px;margin-bottom:8px;display:flex;justify-content:space-between;font-size:13px;box-shadow:0 1px 4px rgba(107,62,30,.05)}
  .item .l .nm{font-weight:700}
  .item .l .meta{font-size:11px;color:#8a6a4a;margin-top:3px}
  .item .amt{font-weight:800;color:#6b3e1e;white-space:nowrap}
  button{width:100%;padding:14px;background:#6b3e1e;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-top:6px}
  button:active{transform:scale(.98)}
  .empty{text-align:center;padding:24px;color:#8a6a4a;font-size:13px;background:#fff;border-radius:12px}
  .info{background:#fff3cd;border-left:4px solid #f0ad4e;padding:12px;border-radius:8px;font-size:12px;color:#8a6a4a;margin-bottom:14px;line-height:1.6}
</style></head><body>
<div class="top">
  <h1>🌐 Offline Status</h1>
  <a href="{{ url_for('staff.dashboard') }}">← Back</a>
</div>
<div class="wrap">

  <div class="status">
    <div class="lbl">
      <span class="dot {{ 'green' if online else 'red' }}"></span>
      {{ 'Online ነህ' if online else 'Offline ነህ' }}
    </div>
    <div class="sub">
      {% if online %}
        Supabase ጋር ግንኙነት አለ · Auto-sync ይሰራል
      {% else %}
        Internet የለም · Orders በስልክ ላይ ይቀመጣሉ
      {% endif %}
    </div>
  </div>

  {% if not online %}
  <div class="info">
    📵 Internet ሲመጣ — Orders በራስ-ሰር ወደ Supabase ይላካሉ። ምንም አያጡም።
  </div>
  {% endif %}

  <div class="grid">
    <div class="card {{ 'warn' if pending.orders > 0 else '' }}">
      <div class="num">{{ pending.orders }}</div>
      <div class="lbl">Pending Orders</div>
    </div>
    <div class="card {{ 'warn' if pending.expenses > 0 else '' }}">
      <div class="num">{{ pending.expenses }}</div>
      <div class="lbl">Pending Expenses</div>
    </div>
  </div>

  <form method="POST" action="{{ url_for('offline.sync_now') }}">
    <button type="submit" {{ 'disabled' if not online or (pending.orders + pending.expenses == 0) }}>
      🔄 {{ 'አሁን Sync አድርግ' if online else 'Internet ሲመጣ Sync ይሆናል' }}
    </button>
  </form>

  {% if queue %}
  <h2>⏳ ያልተላኩ ({{ queue|length }})</h2>
  {% for q in queue %}
  <div class="item">
    <div class="l">
      <div class="nm">{{ q.customer or 'Walk-in' }}</div>
      <div class="meta">Local #{{ q.local_id }} · {{ q.created_at[:16].replace('T',' ') }}</div>
      {% if q.error %}<div class="meta" style="color:#c00">{{ q.error[:60] }}</div>{% endif %}
    </div>
    <div class="amt">{{ "%.2f"|format(q.total or 0) }} ETB</div>
  </div>
  {% endfor %}
  {% endif %}

  {% if synced %}
  <h2>✅ የተላኩ ({{ synced|length }})</h2>
  {% for s in synced %}
  <div class="item">
    <div class="l">
      <div class="nm">{{ s.customer or 'Walk-in' }}</div>
      <div class="meta">Local #{{ s.local_id }} → Supabase #{{ s.supabase_id }}</div>
    </div>
    <div class="amt">{{ "%.2f"|format(s.total or 0) }} ETB</div>
  </div>
  {% endfor %}
  {% endif %}

</div>
</body></html>
"""

@offline_bp.route("/")
def dashboard():
    if session.get("staff_role") not in ("owner","manager","cashier"):
        return redirect(url_for("staff.login"))
    online = is_online()
    cnt = pending_count()
    queue = pending_orders_list()
    synced = synced_log()
    return render_template_string(OFFLINE_HTML,
        online=online, pending=cnt, queue=queue, synced=synced)
