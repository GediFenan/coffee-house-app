# ═══════════════════════════════════════════════
# FIKIR — Inventory (Ingredients, Recipes, Stock)
# Blueprint: /inventory/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, requests
from datetime import datetime, timezone

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")

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

def _require_inv(fn):
    def inner(*a, **kw):
        s = _current()
        if not s: return redirect(url_for("staff.login"))
        if s["role"] not in ("owner","manager","cashier","barista"):
            return "403 — Staff only", 403
        return fn(*a, **kw)
    inner.__name__ = fn.__name__
    return inner

def _require_manager(fn):
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
        print("[INV GET ERR]", e)
        return []

def _ingredients():
    return _get(f"{SUPABASE_URL}/rest/v1/fikir_ingredients?is_active=eq.true&select=*&order=name.asc")

def _products():
    return _get(f"{SUPABASE_URL}/rest/v1/fikir_products?select=id,name,price&order=name.asc")

def _recipes_map():
    """Return {product_id: [{ingredient_id, quantity, name, unit, icon}]}"""
    recipes = _get(f"{SUPABASE_URL}/rest/v1/fikir_recipes?select=*")
    ings = {i["id"]: i for i in _ingredients()}
    result = {}
    for r in recipes:
        pid = r["product_id"]
        ing = ings.get(r["ingredient_id"], {})
        if pid not in result: result[pid] = []
        result[pid].append({
            "ingredient_id": r["ingredient_id"],
            "quantity": float(r["quantity"]),
            "name": ing.get("name", "?"),
            "unit": ing.get("unit", ""),
            "icon": ing.get("icon", "📦"),
        })
    return result

def _stock_status(ing):
    cur = float(ing.get("current_stock") or 0)
    reorder = float(ing.get("reorder_level") or 0)
    if cur <= 0:
        return "critical"
    if cur <= reorder:
        return "warning"
    return "ok"

# ─────────── STOCK LIST ───────────
STOCK_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inventory — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px;margin-left:6px}
  .wrap{padding:14px;max-width:720px;margin:0 auto}
  .tabs{display:flex;gap:6px;background:#fff;padding:6px;border-radius:12px;margin-bottom:14px;box-shadow:0 2px 8px rgba(107,62,30,.06);overflow-x:auto}
  .tabs a{padding:10px 16px;text-decoration:none;font-size:13px;font-weight:700;color:#8a6a4a;border-radius:8px;white-space:nowrap}
  .tabs a.active{background:#6b3e1e;color:#fff}
  .sum{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px}
  .sum .c{background:#fff;border-radius:12px;padding:12px;text-align:center;box-shadow:0 2px 8px rgba(107,62,30,.06)}
  .sum .lbl{font-size:10px;text-transform:uppercase;color:#8a6a4a;font-weight:700;letter-spacing:.5px}
  .sum .val{font-size:20px;font-weight:800;margin-top:2px}
  .sum .val.ok{color:#2a7d2a}.sum .val.warn{color:#f0ad4e}.sum .val.crit{color:#c0392b}
  .card{background:#fff;border-radius:14px;padding:14px;box-shadow:0 2px 8px rgba(107,62,30,.06);margin-bottom:12px}
  .ing{display:flex;align-items:center;padding:12px 0;border-bottom:1px solid #f5ece0;gap:12px}
  .ing:last-child{border-bottom:none}
  .ing .ico{font-size:26px;width:34px;text-align:center;flex-shrink:0}
  .ing .info{flex:1;min-width:0}
  .ing .nm{font-weight:700;font-size:14px}
  .ing .st{font-size:11px;color:#8a6a4a;margin-top:3px}
  .ing .cur{font-weight:800;font-size:15px;text-align:right;white-space:nowrap}
  .bar{height:5px;background:#f0e6d8;border-radius:3px;overflow:hidden;margin-top:6px}
  .bar > div{height:100%;border-radius:3px;transition:.3s}
  .bar .ok{background:#2a7d2a}.bar .warn{background:#f0ad4e}.bar .crit{background:#c0392b}
  .badge{display:inline-block;font-size:9px;padding:2px 7px;border-radius:20px;font-weight:800;margin-left:6px;text-transform:uppercase;letter-spacing:.3px}
  .badge.ok{background:#d4edda;color:#1e7e34}
  .badge.warn{background:#fff3cd;color:#8a6a00}
  .badge.crit{background:#f8d7da;color:#a02020}
  .prod{background:#fff;border-radius:12px;padding:14px;margin-bottom:10px;box-shadow:0 2px 8px rgba(107,62,30,.06)}
  .prod .hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
  .prod .nm{font-weight:800;font-size:15px}
  .prod .price{font-size:12px;color:#6b3e1e;font-weight:700;background:#f0e6d8;padding:3px 9px;border-radius:20px}
  .prod .rec{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
  .chip{background:#f5ece0;color:#6b3e1e;font-size:11px;padding:4px 10px;border-radius:20px;font-weight:600}
  .empty{text-align:center;padding:30px;color:#8a6a4a;font-size:13px}
</style></head><body>
<div class="top">
  <h1>📦 Inventory</h1>
  <div>
    <a href="{{ url_for('inventory.movements') }}">📋 ታሪክ</a>
    <a href="{{ url_for('staff.dashboard') }}">←</a>
  </div>
</div>
<div class="wrap">

  <div class="tabs">
    <a href="{{ url_for('inventory.index') }}" class="{{ 'active' if tab=='stock' }}">📦 Stock</a>
    <a href="{{ url_for('inventory.recipes') }}" class="{{ 'active' if tab=='recipes' }}">🧪 Recipes</a>
    {% if role in ('owner','manager') %}
    <a href="{{ url_for('inventory.purchase') }}" class="{{ 'active' if tab=='purchase' }}">🛒 ግዢ</a>
    <a href="{{ url_for('inventory.adjust') }}" class="{{ 'active' if tab=='adjust' }}">⚙️ Adjust</a>
    {% endif %}
  </div>

  <div class="sum">
    <div class="c"><div class="lbl">🟢 OK</div><div class="val ok">{{ ok_count }}</div></div>
    <div class="c"><div class="lbl">🟡 Low</div><div class="val warn">{{ warn_count }}</div></div>
    <div class="c"><div class="lbl">🔴 Out</div><div class="val crit">{{ crit_count }}</div></div>
  </div>

  <div class="card">
    {% if ingredients %}
      {% for i in ingredients %}
      {% set st = statuses[i.id] %}
      {% set pct = [100, (i.current_stock|float / (i.reorder_level|float * 3) * 100) if (i.reorder_level|float) > 0 else 100]|min %}
      <div class="ing">
        <div class="ico">{{ i.icon or '📦' }}</div>
        <div class="info">
          <div class="nm">{{ i.name }}
            <span class="badge {{ st }}">{{ {'ok':'OK','warning':'LOW','critical':'OUT'}[st] }}</span>
          </div>
          <div class="st">{{ "%.1f"|format(i.current_stock|float) }} {{ i.unit }} · min {{ "%.0f"|format(i.reorder_level|float) }}</div>
          <div class="bar"><div class="{{ st }}" style="width:{{ pct }}%"></div></div>
        </div>
        <div class="cur">{{ "%.0f"|format(i.current_stock|float) }}<br><span style="font-size:10px;color:#8a6a4a">{{ i.unit }}</span></div>
      </div>
      {% endfor %}
    {% else %}
      <div class="empty">ምንም ጥሬ እቃ የለም</div>
    {% endif %}
  </div>

</div>
</body></html>
"""

@inventory_bp.route("/")
@_require_inv
def index():
    s = _current()
    ings = _ingredients()
    statuses = {i["id"]: _stock_status(i) for i in ings}
    ok_count = sum(1 for st in statuses.values() if st == "ok")
    warn_count = sum(1 for st in statuses.values() if st == "warning")
    crit_count = sum(1 for st in statuses.values() if st == "critical")
    return render_template_string(STOCK_HTML,
        ingredients=ings, statuses=statuses,
        ok_count=ok_count, warn_count=warn_count, crit_count=crit_count,
        tab="stock", **s)

# ─────────── RECIPES ───────────
RECIPES_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Recipes — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px;margin-left:6px}
  .wrap{padding:14px;max-width:720px;margin:0 auto}
  .tabs{display:flex;gap:6px;background:#fff;padding:6px;border-radius:12px;margin-bottom:14px;box-shadow:0 2px 8px rgba(107,62,30,.06);overflow-x:auto}
  .tabs a{padding:10px 16px;text-decoration:none;font-size:13px;font-weight:700;color:#8a6a4a;border-radius:8px;white-space:nowrap}
  .tabs a.active{background:#6b3e1e;color:#fff}
  .prod{background:#fff;border-radius:12px;padding:16px;margin-bottom:12px;box-shadow:0 2px 8px rgba(107,62,30,.06)}
  .prod .hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
  .prod .nm{font-weight:800;font-size:15px}
  .prod .price{font-size:12px;color:#6b3e1e;font-weight:700;background:#f0e6d8;padding:3px 9px;border-radius:20px}
  .rec{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f5ece0;font-size:13px}
  .rec:last-child{border-bottom:none}
  .rec .amt{font-weight:700;color:#6b3e1e}
  .rec form{margin:0}
  .rec button{background:#f8d7da;color:#a02020;border:none;border-radius:6px;padding:4px 10px;font-size:11px;cursor:pointer;font-weight:700}
  .add-form{display:grid;grid-template-columns:1fr 80px auto;gap:6px;margin-top:10px;padding-top:10px;border-top:2px solid #f5ece0}
  .add-form select,.add-form input{padding:8px;border:2px solid #e0d0c0;border-radius:8px;font-size:13px;outline:none;background:#fff;width:100%}
  .add-form button{padding:8px 14px;background:#2a7d2a;color:#fff;border:none;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
  .empty{text-align:center;padding:30px;color:#8a6a4a;font-size:13px;background:#fff;border-radius:12px}
  .hint{font-size:11px;color:#8a6a4a;margin-top:6px;line-height:1.5}
</style></head><body>
<div class="top">
  <h1>🧪 Recipes</h1>
  <a href="{{ url_for('staff.dashboard') }}">←</a>
</div>
<div class="wrap">

  <div class="tabs">
    <a href="{{ url_for('inventory.index') }}">📦 Stock</a>
    <a href="{{ url_for('inventory.recipes') }}" class="active">🧪 Recipes</a>
    {% if role in ('owner','manager') %}
    <a href="{{ url_for('inventory.purchase') }}">🛒 ግዢ</a>
    <a href="{{ url_for('inventory.adjust') }}">⚙️ Adjust</a>
    {% endif %}
  </div>

  <div class="hint">
    📌 እያንዳንዱ ምርት ሲሸጥ Recipe መሰረት ጥሬ እቃ በራስ-ሰር ይቀነሳል።
  </div>

  {% if products %}
    {% for p in products %}
    <div class="prod">
      <div class="hd">
        <div class="nm">{{ p.name }}</div>
        <div class="price">{{ p.price }} ETB</div>
      </div>
      {% set items = recipes.get(p.id, []) %}
      {% if items %}
        {% for it in items %}
        <div class="rec">
          <span>{{ it.icon }} {{ it.name }}</span>
          <span>
            <span class="amt">{{ "%.1f"|format(it.quantity) }} {{ it.unit }}</span>
            {% if role in ('owner','manager') %}
            <form method="POST" action="{{ url_for('inventory.recipe_delete') }}" style="display:inline">
              <input type="hidden" name="product_id" value="{{ p.id }}">
              <input type="hidden" name="ingredient_id" value="{{ it.ingredient_id }}">
              <button type="submit">✕</button>
            </form>
            {% endif %}
          </span>
        </div>
        {% endfor %}
      {% else %}
        <div style="font-size:12px;color:#8a6a4a;padding:6px 0">ምንም ጥሬ እቃ አልተገናኘም</div>
      {% endif %}
      {% if role in ('owner','manager') %}
      <form class="add-form" method="POST" action="{{ url_for('inventory.recipe_add') }}">
        <input type="hidden" name="product_id" value="{{ p.id }}">
        <select name="ingredient_id" required>
          <option value="">➕ ጥሬ እቃ ምረጥ...</option>
          {% for i in ingredients %}
          <option value="{{ i.id }}">{{ i.icon or '📦' }} {{ i.name }} ({{ i.unit }})</option>
          {% endfor %}
        </select>
        <input name="quantity" type="number" step="any" min="0.01" placeholder="Qty" required>
        <button type="submit">➕</button>
      </form>
      {% endif %}
    </div>
    {% endfor %}
  {% else %}
    <div class="empty">ምንም ምርት የለም</div>
  {% endif %}

</div>
</body></html>
"""

@inventory_bp.route("/recipes")
@_require_inv
def recipes():
    s = _current()
    prods = _products()
    ings = _ingredients()
    recipes_map = _recipes_map()
    return render_template_string(RECIPES_HTML,
        products=prods, ingredients=ings, recipes=recipes_map,
        tab="recipes", **s)

@inventory_bp.route("/recipe/add", methods=["POST"])
@_require_manager
def recipe_add():
    s = _current()
    pid = request.form.get("product_id")
    iid = request.form.get("ingredient_id")
    try:
        qty = float(request.form.get("quantity") or 0)
    except ValueError:
        qty = 0
    if not pid or not iid or qty <= 0:
        return redirect(url_for("inventory.recipes"))

    payload = {"product_id": int(pid), "ingredient_id": int(iid), "quantity": round(qty, 3)}
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/fikir_recipes",
                     json=payload, headers=_headers("resolution=merge-duplicates"), timeout=30)
    except Exception as e:
        print("[RECIPE ADD ERR]", e)
    return redirect(url_for("inventory.recipes"))

@inventory_bp.route("/recipe/delete", methods=["POST"])
@_require_manager
def recipe_delete():
    pid = request.form.get("product_id")
    iid = request.form.get("ingredient_id")
    try:
        requests.delete(f"{SUPABASE_URL}/rest/v1/fikir_recipes?product_id=eq.{pid}&ingredient_id=eq.{iid}",
                       headers=_headers(), timeout=30)
    except Exception as e:
        print("[RECIPE DEL ERR]", e)
    return redirect(url_for("inventory.recipes"))

# ─────────── PURCHASE ───────────
PURCHASE_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Purchase — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:14px;max-width:520px;margin:0 auto}
  .tabs{display:flex;gap:6px;background:#fff;padding:6px;border-radius:12px;margin-bottom:14px;box-shadow:0 2px 8px rgba(107,62,30,.06);overflow-x:auto}
  .tabs a{padding:10px 16px;text-decoration:none;font-size:13px;font-weight:700;color:#8a6a4a;border-radius:8px;white-space:nowrap}
  .tabs a.active{background:#6b3e1e;color:#fff}
  .card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 8px rgba(107,62,30,.06)}
  label{display:block;font-size:12px;font-weight:700;color:#5a3a1e;margin-bottom:6px;margin-top:14px}
  label:first-child{margin-top:0}
  select,input{width:100%;padding:13px;border:2px solid #e0d0c0;border-radius:10px;font-size:15px;outline:none;background:#fff;font-family:inherit;color:#3b1f0b}
  select:focus,input:focus{border-color:#6b3e1e}
  button{width:100%;padding:15px;background:#2a7d2a;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-top:18px}
  button:active{transform:scale(.98)}
</style></head><body>
<div class="top">
  <h1>🛒 ግዢ</h1>
  <a href="{{ url_for('staff.dashboard') }}">←</a>
</div>
<div class="wrap">

  <div class="tabs">
    <a href="{{ url_for('inventory.index') }}">📦 Stock</a>
    <a href="{{ url_for('inventory.recipes') }}">🧪 Recipes</a>
    <a href="{{ url_for('inventory.purchase') }}" class="active">🛒 ግዢ</a>
    <a href="{{ url_for('inventory.adjust') }}">⚙️ Adjust</a>
  </div>

  <div class="card">
    <form method="POST" action="{{ url_for('inventory.purchase_add') }}">
      <label>ጥሬ እቃ</label>
      <select name="ingredient_id" required>
        {% for i in ingredients %}
        <option value="{{ i.id }}">{{ i.icon or '📦' }} {{ i.name }} ({{ i.unit }}) — {{ "%.0f"|format(i.current_stock|float) }} ያለ</option>
        {% endfor %}
      </select>

      <label>መጠን ({{ unit_hint or 'unit' }})</label>
      <input name="quantity" type="number" step="any" min="0.01" placeholder="ለምሳሌ 5000" required>

      <label>የነጠላ ዋጋ (ETB, optional)</label>
      <input name="unit_cost" type="number" step="0.01" min="0" placeholder="0.00">

      <label>ማስታወሻ (optional)</label>
      <input name="note" type="text" placeholder="ለምሳሌ: ከገበያ የተገዛ" maxlength="200">

      <button type="submit">🛒 ግዢ መዝግብ</button>
    </form>
  </div>

</div>
</body></html>
"""

@inventory_bp.route("/purchase")
@_require_manager
def purchase():
    s = _current()
    ings = _ingredients()
    return render_template_string(PURCHASE_HTML, ingredients=ings, tab="purchase", **s)

@inventory_bp.route("/purchase/add", methods=["POST"])
@_require_manager
def purchase_add():
    s = _current()
    iid = request.form.get("ingredient_id")
    try:
        qty = float(request.form.get("quantity") or 0)
        cost = float(request.form.get("unit_cost") or 0)
    except ValueError:
        qty = 0; cost = 0
    note = (request.form.get("note") or "")[:200]

    if not iid or qty <= 0:
        return redirect(url_for("inventory.purchase"))

    # Get current stock
    rows = _get(f"{SUPABASE_URL}/rest/v1/fikir_ingredients?id=eq.{iid}&limit=1")
    if not rows:
        return redirect(url_for("inventory.purchase"))
    ing = rows[0]
    new_stock = float(ing["current_stock"] or 0) + qty

    # Update ingredient
    upd = {"current_stock": round(new_stock, 3)}
    if cost > 0:
        # weighted average cost
        old_stock = float(ing["current_stock"] or 0)
        old_cost = float(ing.get("unit_cost") or 0)
        if old_stock + qty > 0:
            new_cost = (old_stock * old_cost + qty * cost) / (old_stock + qty)
            upd["unit_cost"] = round(new_cost, 4)
    try:
        requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_ingredients?id=eq.{iid}",
                      json=upd, headers=_headers(), timeout=30)
        # Log transaction
        requests.post(f"{SUPABASE_URL}/rest/v1/fikir_inventory_tx",
            json={"ingredient_id": int(iid), "type": "purchase",
                  "quantity": round(qty, 3), "user_id": s["id"], "note": note},
            headers=_headers(), timeout=30)
    except Exception as e:
        print("[PURCHASE ERR]", e)

    return redirect(url_for("inventory.index"))

# ─────────── ADJUST ───────────
ADJUST_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Adjust — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:14px;max-width:520px;margin:0 auto}
  .tabs{display:flex;gap:6px;background:#fff;padding:6px;border-radius:12px;margin-bottom:14px;box-shadow:0 2px 8px rgba(107,62,30,.06);overflow-x:auto}
  .tabs a{padding:10px 16px;text-decoration:none;font-size:13px;font-weight:700;color:#8a6a4a;border-radius:8px;white-space:nowrap}
  .tabs a.active{background:#6b3e1e;color:#fff}
  .card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 8px rgba(107,62,30,.06)}
  label{display:block;font-size:12px;font-weight:700;color:#5a3a1e;margin-bottom:6px;margin-top:14px}
  label:first-child{margin-top:0}
  select,input{width:100%;padding:13px;border:2px solid #e0d0c0;border-radius:10px;font-size:15px;outline:none;background:#fff;font-family:inherit;color:#3b1f0b}
  select:focus,input:focus{border-color:#6b3e1e}
  button{width:100%;padding:15px;background:#c0392b;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-top:18px}
  button:active{transform:scale(.98)}
  .info{background:#fff3cd;border-left:4px solid #f0ad4e;padding:10px 12px;border-radius:8px;font-size:12px;color:#8a6a4a;margin-bottom:14px;line-height:1.5}
</style></head><body>
<div class="top">
  <h1>⚙️ Adjust</h1>
  <a href="{{ url_for('staff.dashboard') }}">←</a>
</div>
<div class="wrap">

  <div class="tabs">
    <a href="{{ url_for('inventory.index') }}">📦 Stock</a>
    <a href="{{ url_for('inventory.recipes') }}">🧪 Recipes</a>
    <a href="{{ url_for('inventory.purchase') }}">🛒 ግዢ</a>
    <a href="{{ url_for('inventory.adjust') }}" class="active">⚙️ Adjust</a>
  </div>

  <div class="info">
    🗑️ የተበላሸ ወይስ የተሰረቀ እቃ ለማስተካከል ይህን ተጠቀሙ። አሉታዊ ቁጥር (-) ደግሞ ይቀበላል።
  </div>

  <div class="card">
    <form method="POST" action="{{ url_for('inventory.adjust_add') }}">
      <label>ጥሬ እቃ</label>
      <select name="ingredient_id" required>
        {% for i in ingredients %}
        <option value="{{ i.id }}">{{ i.icon or '📦' }} {{ i.name }} — {{ "%.0f"|format(i.current_stock|float) }} {{ i.unit }}</option>
        {% endfor %}
      </select>

      <label>ለውጥ (+/-)</label>
      <input name="quantity" type="number" step="any" placeholder="ለምሳሌ -50 ወይስ 100" required>

      <label>ምክንያት</label>
      <select name="reason" required>
        <option value="waste">🗑️ ተበላሽቷል</option>
        <option value="damage">💔 ተበላሽቷል (packaging)</option>
        <option value="count">📋 ቆጠራ ማስተካከያ</option>
        <option value="return">↩️ ተመላሽ</option>
        <option value="other">📝 ሌላ</option>
      </select>

      <label>ማስታወሻ (optional)</label>
      <input name="note" type="text" maxlength="200" placeholder="ዝርዝር...">

      <button type="submit">⚙️ አስተካክል</button>
    </form>
  </div>

</div>
</body></html>
"""

@inventory_bp.route("/adjust")
@_require_manager
def adjust():
    s = _current()
    ings = _ingredients()
    return render_template_string(ADJUST_HTML, ingredients=ings, tab="adjust", **s)

@inventory_bp.route("/adjust/add", methods=["POST"])
@_require_manager
def adjust_add():
    s = _current()
    iid = request.form.get("ingredient_id")
    try:
        qty = float(request.form.get("quantity") or 0)
    except ValueError:
        qty = 0
    reason = (request.form.get("reason") or "other")[:30]
    note = (request.form.get("note") or "")[:200]

    if not iid or qty == 0:
        return redirect(url_for("inventory.adjust"))

    rows = _get(f"{SUPABASE_URL}/rest/v1/fikir_ingredients?id=eq.{iid}&limit=1")
    if not rows:
        return redirect(url_for("inventory.adjust"))
    ing = rows[0]
    new_stock = max(0, float(ing["current_stock"] or 0) + qty)

    try:
        requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_ingredients?id=eq.{iid}",
                      json={"current_stock": round(new_stock, 3)},
                      headers=_headers(), timeout=30)
        requests.post(f"{SUPABASE_URL}/rest/v1/fikir_inventory_tx",
            json={"ingredient_id": int(iid), "type": reason,
                  "quantity": round(qty, 3), "user_id": s["id"], "note": note},
            headers=_headers(), timeout=30)
    except Exception as e:
        print("[ADJUST ERR]", e)

    return redirect(url_for("inventory.index"))

# ─────────── MOVEMENTS ───────────
MOVES_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>History — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:14px;max-width:640px;margin:0 auto}
  .mv{background:#fff;border-radius:12px;padding:14px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;font-size:13px;box-shadow:0 1px 4px rgba(107,62,30,.05)}
  .mv .l .nm{font-weight:700}
  .mv .l .meta{font-size:11px;color:#8a6a4a;margin-top:2px}
  .mv .qty{font-weight:800;font-size:15px;white-space:nowrap}
  .mv .qty.pos{color:#2a7d2a}
  .mv .qty.neg{color:#c0392b}
  .pill{display:inline-block;font-size:10px;padding:2px 8px;border-radius:20px;font-weight:700;margin-right:6px;background:#f0e6d8;color:#6b3e1e;text-transform:uppercase}
  .empty{text-align:center;padding:30px;color:#8a6a4a;font-size:13px;background:#fff;border-radius:12px}
</style></head><body>
<div class="top">
  <h1>📋 ታሪክ</h1>
  <a href="{{ url_for('inventory.index') }}">←</a>
</div>
<div class="wrap">
  {% if movements %}
    {% for m in movements %}
    <div class="mv">
      <div class="l">
        <div class="nm">{{ m.ing_name }}</div>
        <div class="meta">
          <span class="pill">{{ m.type }}</span>
          {{ m.created_at[:16].replace('T',' ') }}
          {% if m.note %}· {{ m.note }}{% endif %}
        </div>
      </div>
      <div class="qty {{ 'pos' if m.quantity > 0 else 'neg' }}">
        {{ '+' if m.quantity > 0 else '' }}{{ "%.1f"|format(m.quantity) }} {{ m.unit }}
      </div>
    </div>
    {% endfor %}
  {% else %}
    <div class="empty">ምንም እንቅስቃሴ የለም</div>
  {% endif %}
</div>
</body></html>
"""

@inventory_bp.route("/movements")
@_require_inv
def movements():
    s = _current()
    tx = _get(f"{SUPABASE_URL}/rest/v1/fikir_inventory_tx?select=*&order=created_at.desc&limit=100")
    ings = {i["id"]: i for i in _ingredients()}
    moves = []
    for t in tx:
        ing = ings.get(t["ingredient_id"], {})
        moves.append({
            "ing_name": ing.get("name", f"#{t['ingredient_id']}"),
            "unit": ing.get("unit", ""),
            "type": t.get("type", "?"),
            "quantity": float(t.get("quantity") or 0),
            "note": t.get("note") or "",
            "created_at": t.get("created_at") or "",
        })
    return render_template_string(MOVES_HTML, movements=moves, **s)

# ─────────── AUTO-DEDUCT (called by POS) ───────────
def deduct_for_order(order_id, cart_items, user_id):
    """Deduct ingredients based on recipes.
    cart_items: list of (product_id, qty)
    """
    recipes_map = _recipes_map()
    movements = []
    for pid, qty_sold in cart_items:
        recipe = recipes_map.get(int(pid), [])
        for r in recipe:
            total = r["quantity"] * qty_sold
            movements.append((r["ingredient_id"], -total, r["name"]))

    low_stock_alerts = []
    for iid, delta, name in movements:
        rows = _get(f"{SUPABASE_URL}/rest/v1/fikir_ingredients?id=eq.{iid}&limit=1")
        if not rows: continue
        ing = rows[0]
        new_stock = max(0, float(ing["current_stock"] or 0) + delta)
        reorder = float(ing.get("reorder_level") or 0)
        try:
            requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_ingredients?id=eq.{iid}",
                          json={"current_stock": round(new_stock, 3)},
                          headers=_headers(), timeout=30)
            requests.post(f"{SUPABASE_URL}/rest/v1/fikir_inventory_tx",
                json={"ingredient_id": iid, "type": "sale",
                      "quantity": round(delta, 3),
                      "ref_order_id": order_id, "user_id": user_id},
                headers=_headers(), timeout=30)
            # Track low stock
            old_stock = float(ing["current_stock"] or 0)
            if new_stock <= reorder and old_stock > reorder:
                # Crossed into low stock
                low_stock_alerts.append((ing.get("name"), new_stock, ing.get("unit"), reorder))
        except Exception as e:
            print("[DEDUCT ERR]", e)

    # Send low-stock Telegram alerts
    for name, cur, unit, reorder in low_stock_alerts:
        try:
            from notifications_routes import notify_low_stock
            notify_low_stock(name, cur, unit, reorder)
            print(f"[TG] Low stock alert: {name}")
        except Exception as e:
            print("[TG LOW STOCK ERR]", e)

    return movements
