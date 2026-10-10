# ═══════════════════════════════════════════════
# FIKIR — Product & Category Management (Owner only)
# Blueprint: /products-admin/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, requests
from datetime import datetime, timezone

products_admin_bp = Blueprint("products_admin", __name__, url_prefix="/products-admin")

SUPABASE_URL = "https://skswircyorzpbcioljcs.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrc3dpcmN5b3J6cGJjaW9samNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MjMyMzQsImV4cCI6MjEwMzQ5OTIzNH0.ntS52ih33wprDiQ4YGrNzWchuuWqfzc1iyv7_xi_qPM"

ICON_OPTIONS = ["☕","🍵","🥛","🧊","🍫","🥤","🍯","🥯","🍰","🧁","🍪","🧃","🍶","🍷","📦","⭕"]

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
            return "403 — Owner/Manager only", 403
        return fn(*a, **kw)
    inner.__name__ = fn.__name__
    return inner

def _get(url):
    try:
        r = requests.get(url, headers=_headers(), timeout=15)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print("[PROD-ADMIN GET ERR]", e)
        return []

def _audit(user_id, action, entity=None, entity_id=None, extra=None):
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/fikir_audit_logs",
            json={"user_id": user_id, "action": action, "entity": entity,
                  "entity_id": str(entity_id) if entity_id else None,
                  "new_value": extra or {}},
            headers=_headers(), timeout=10)
    except Exception:
        pass

# ═══════════════════════════════════════════════
# PRODUCTS LIST PAGE
# ═══════════════════════════════════════════════
LIST_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Products — FIKIR</title>
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
  .stats{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px}
  .stats .c{background:#fff;border-radius:12px;padding:12px;text-align:center;box-shadow:0 2px 8px rgba(107,62,30,.06)}
  .stats .c .num{font-size:22px;font-weight:800;color:#6b3e1e}
  .stats .c .lbl{font-size:10px;text-transform:uppercase;color:#8a6a4a;font-weight:700;margin-top:2px}
  .p{background:#fff;border-radius:14px;padding:14px;margin-bottom:10px;box-shadow:0 2px 8px rgba(107,62,30,.06);display:flex;align-items:center;gap:12px}
  .p .ico{font-size:32px;width:44px;text-align:center;flex-shrink:0}
  .p .info{flex:1;min-width:0}
  .p .nm{font-weight:800;font-size:15px}
  .p .meta{font-size:11px;color:#8a6a4a;margin-top:3px}
  .p .price{font-weight:800;color:#6b3e1e;font-size:15px;white-space:nowrap}
  .p .actions{display:flex;gap:6px;flex-shrink:0}
  .p .actions form{margin:0}
  .p .actions button{padding:8px 10px;border:none;border-radius:8px;font-size:14px;cursor:pointer;background:#f5ece0}
  .p .actions button.edit{background:#f0e6d8}
  .p .actions button.del{background:#f8d7da;color:#a02020}
  .p.inactive{opacity:.5}
  .badge-inactive{background:#ccc;color:#666;font-size:9px;padding:2px 8px;border-radius:20px;font-weight:800;margin-left:6px;text-transform:uppercase}
  .add-btn{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#6b3e1e;color:#fff;border:none;font-size:28px;font-weight:800;cursor:pointer;box-shadow:0 8px 24px rgba(107,62,30,.4);z-index:100}
  .add-btn:active{transform:scale(.95)}
  .empty{text-align:center;padding:60px 20px;color:#8a6a4a;font-size:14px}
</style></head><body>
<div class="top">
  <h1>☕ ምርቶች</h1>
  <div>
    <a href="{{ url_for('products_admin.categories') }}">📂 Categories</a>
    <a href="{{ url_for('staff.dashboard') }}">←</a>
  </div>
</div>
<div class="wrap">

  {% if msg %}<div style="background:#d4edda;color:#1e7e34;padding:12px;border-radius:8px;margin-bottom:14px;font-weight:600">{{ msg }}</div>{% endif %}
  {% if error %}<div style="background:#ffe0e0;color:#c00;padding:12px;border-radius:8px;margin-bottom:14px">{{ error }}</div>{% endif %}

  <div class="stats">
    <div class="c"><div class="num">{{ products|length }}</div><div class="lbl">ሁሉም</div></div>
    <div class="c"><div class="num">{{ active_count }}</div><div class="lbl">ንቁ</div></div>
    <div class="c"><div class="num">{{ category_count }}</div><div class="lbl">Categories</div></div>
  </div>

  <div class="tabs">
    <a href="{{ url_for('products_admin.index') }}" class="{{ 'active' if not cat_filter }}">ሁሉም ({{ products|length }})</a>
    {% for c in categories %}
    <a href="{{ url_for('products_admin.index', cat=c.id) }}" class="{{ 'active' if cat_filter == c.id|string }}">{{ c.icon }} {{ c.name }} ({{ cat_counts.get(c.id, 0) }})</a>
    {% endfor %}
  </div>

  {% if products %}
    {% for p in products %}
    <div class="p {{ '' if p.is_active else 'inactive' }}">
      <div class="ico">{{ p.icon or '☕' }}</div>
      <div class="info">
        <div class="nm">{{ p.name }}{% if not p.is_active %}<span class="badge-inactive">off</span>{% endif %}</div>
        <div class="meta">
          {{ cat_labels.get(p.category_id, 'ምድብ የለም') }}
          {% if p.description %} · {{ p.description[:40] }}{% endif %}
        </div>
        <div class="price" style="color:#6b3e1e;font-size:14px;margin-top:4px">{{ "%.2f"|format(p.price|float) }} ETB</div>
      </div>
      <div class="actions">
        <form method="POST" action="{{ url_for('products_admin.toggle', product_id=p.id) }}">
          <button type="submit">{{ '👁️' if not p.is_active else '🚫' }}</button>
        </form>
        <form method="GET" action="{{ url_for('products_admin.edit', product_id=p.id) }}">
          <button type="submit" class="edit">✏️</button>
        </form>
        <form method="POST" action="{{ url_for('products_admin.delete', product_id=p.id) }}" onsubmit="return confirm('{{ p.name }} ን ማጥፋት?')">
          <button type="submit" class="del">🗑️</button>
        </form>
      </div>
    </div>
    {% endfor %}
  {% else %}
    <div class="empty">ምንም ምርት የለም<br><br>➕ ቁልፍ ተጭነው አዲስ ይጨምሩ</div>
  {% endif %}

</div>

<a href="{{ url_for('products_admin.create') }}" class="add-btn">+</a>
</body></html>
"""

@products_admin_bp.route("/")
@_require_owner
def index():
    s = _current()
    products = _get(f"{SUPABASE_URL}/rest/v1/fikir_products?select=*&order=category_id.asc,name.asc")
    categories = _get(f"{SUPABASE_URL}/rest/v1/fikir_categories?is_active=eq.true&select=*&order=sort_order.asc")

    cat_filter = request.args.get("cat")
    if cat_filter:
        try:
            cid = int(cat_filter)
            products = [p for p in products if p.get("category_id") == cid]
        except ValueError:
            pass

    cat_labels = {c["id"]: f"{c.get('icon','📦')} {c['name']}" for c in categories}

    # counts
    all_products = _get(f"{SUPABASE_URL}/rest/v1/fikir_products?select=id,category_id,is_active")
    cat_counts = {}
    for c in categories:
        cat_counts[c["id"]] = sum(1 for p in all_products if p.get("category_id") == c["id"])

    return render_template_string(LIST_HTML,
        products=products, categories=categories,
        cat_filter=cat_filter, cat_counts=cat_counts,
        cat_labels=cat_labels,
        active_count=sum(1 for p in all_products if p.get("is_active")),
        category_count=len(categories),
        msg=request.args.get("msg"), error=request.args.get("error"), **s)

# ═══════════════════════════════════════════════
# CREATE / EDIT FORM
# ═══════════════════════════════════════════════
FORM_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ 'አርትዕ' if product else 'አዲስ ምርት' }} — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:16px;max-width:520px;margin:0 auto}
  .card{background:#fff;border-radius:14px;padding:20px;box-shadow:0 2px 12px rgba(107,62,30,.06)}
  label{display:block;font-size:12px;font-weight:700;color:#5a3a1e;margin-bottom:6px;margin-top:14px}
  label:first-child{margin-top:0}
  input,select,textarea{width:100%;padding:13px;border:2px solid #e0d0c0;border-radius:10px;font-size:15px;outline:none;background:#fff;font-family:inherit;color:#3b1f0b}
  input:focus,select:focus{border-color:#6b3e1e}
  textarea{resize:vertical;min-height:70px}
  .icons-grid{display:grid;grid-template-columns:repeat(8,1fr);gap:4px;margin-top:6px}
  .icons-grid label{cursor:pointer;padding:8px;text-align:center;border:2px solid transparent;border-radius:8px;font-size:20px;margin:0}
  .icons-grid input{display:none}
  .icons-grid input:checked + span{background:#6b3e1e;color:#fff;border-radius:6px;padding:4px 8px;display:inline-block}
  .icons-grid label:has(input:checked){background:#6b3e1e;border-color:#6b3e1e;color:#fff}
  .preview{text-align:center;background:#f5ece0;border-radius:12px;padding:16px;margin-top:8px}
  .preview .ico{font-size:48px}
  .preview .nm{font-weight:800;font-size:16px;margin-top:6px}
  .preview .pr{color:#6b3e1e;font-weight:800;margin-top:4px}
  button{width:100%;padding:15px;background:#6b3e1e;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-top:20px}
  button:active{transform:scale(.98)}
  button.danger{background:#c0392b}
  .err{background:#ffe0e0;color:#c00;padding:10px;border-radius:8px;font-size:13px;margin-bottom:14px}
</style></head><body>
<div class="top">
  <h1>{{ '✏️ ምርት አርትዕ' if product else '➕ አዲስ ምርት' }}</h1>
  <a href="{{ url_for('products_admin.index') }}">← Back</a>
</div>
<div class="wrap">
  <div class="card">
    {% if error %}<div class="err">{{ error }}</div>{% endif %}

    <form method="POST" id="prodForm">
      <label>ስም *</label>
      <input name="name" required maxlength="80" value="{{ product.name if product else '' }}" placeholder="ለምሳሌ: Espresso" autofocus>

      <label>ምድብ</label>
      <select name="category_id">
        <option value="">— ምድብ የለም —</option>
        {% for c in categories %}
        <option value="{{ c.id }}" {% if product and product.category_id == c.id %}selected{% endif %}>{{ c.icon }} {{ c.name }}</option>
        {% endfor %}
      </select>

      <label>ዋጋ (ETB) *</label>
      <input name="price" type="number" step="0.01" min="0" required value="{{ product.price if product else '' }}" placeholder="0.00">

      <label>ማብራሪያ (optional)</label>
      <textarea name="description" maxlength="200" placeholder="ለምሳሌ: Strong and rich coffee">{{ product.description if product else '' }}</textarea>

      <label>Icon</label>
      <div class="icons-grid">
        {% for icon in icons %}
        <label>
          <input type="radio" name="icon" value="{{ icon }}" {% if product and product.icon == icon %}checked{% elif not product and icon == '☕' %}checked{% endif %} onchange="updatePreview()">
          <span>{{ icon }}</span>
        </label>
        {% endfor %}
      </div>

      <div class="preview">
        <div class="ico" id="pIcon">{{ product.icon if product else '☕' }}</div>
        <div class="nm" id="pName">{{ product.name if product else 'Espresso' }}</div>
        <div class="pr" id="pPrice">{{ product.price if product else '50' }} ETB</div>
      </div>

      <label>Stock (optional — ለ inventory)</label>
      <input name="stock" type="number" step="1" min="0" value="{{ product.stock if product and product.stock else 0 }}">

      <label>Low Stock Alert</label>
      <input name="low_stock" type="number" step="1" min="0" value="{{ product.low_stock if product and product.low_stock else 5 }}">

      <button type="submit">{{ '💾 አስቀምጥ' if product else '➕ ጨምር' }}</button>
    </form>
  </div>
</div>
<script>
  function updatePreview(){
    const icon = document.querySelector('input[name="icon"]:checked')?.value || '☕';
    const name = document.querySelector('input[name="name"]').value || 'Espresso';
    const price = document.querySelector('input[name="price"]').value || '50';
    document.getElementById('pIcon').textContent = icon;
    document.getElementById('pName').textContent = name;
    document.getElementById('pPrice').textContent = price + ' ETB';
  }
  document.querySelector('input[name="name"]').addEventListener('input', updatePreview);
  document.querySelector('input[name="price"]').addEventListener('input', updatePreview);
</script>
</body></html>
"""

@products_admin_bp.route("/create", methods=["GET", "POST"])
@_require_owner
def create():
    s = _current()
    categories = _get(f"{SUPABASE_URL}/rest/v1/fikir_categories?is_active=eq.true&select=*&order=sort_order.asc")

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()[:80]
        try:
            price = float(request.form.get("price") or 0)
        except ValueError:
            price = 0
        category_id = request.form.get("category_id") or None
        description = (request.form.get("description") or "").strip()[:200]
        icon = (request.form.get("icon") or "☕")[:4]
        try:
            stock = int(request.form.get("stock") or 0)
        except ValueError:
            stock = 0
        try:
            low_stock = int(request.form.get("low_stock") or 5)
        except ValueError:
            low_stock = 5

        if not name or price <= 0:
            return render_template_string(FORM_HTML, categories=categories, product=None,
                icons=ICON_OPTIONS, error="ስም እና ዋጋ ያስፈልጋሉ", **s)

        payload = {
            "name": name, "price": price,
            "description": description or "",
            "icon": icon, "stock": stock, "low_stock": low_stock,
            "is_active": True,
        }
        if category_id:
            try: payload["category_id"] = int(category_id)
            except ValueError: pass

        try:
            r = requests.post(f"{SUPABASE_URL}/rest/v1/fikir_products",
                             json=payload, headers=_headers("return=representation"), timeout=15)
            if r.status_code in (200, 201):
                new_id = r.json()[0]["id"]
                _audit(s["id"], "product.create", "fikir_products", new_id, payload)
                return redirect(url_for("products_admin.index") + f"?msg=✅+{name}+ተጨመረ")
            return render_template_string(FORM_HTML, categories=categories, product=None,
                icons=ICON_OPTIONS, error=f"ስህተት: {r.text[:150]}", **s)
        except Exception as e:
            return render_template_string(FORM_HTML, categories=categories, product=None,
                icons=ICON_OPTIONS, error=f"ስህተት: {str(e)[:100]}", **s)

    return render_template_string(FORM_HTML, categories=categories, product=None,
        icons=ICON_OPTIONS, error=None, **s)

@products_admin_bp.route("/edit/<int:product_id>", methods=["GET", "POST"])
@_require_owner
def edit(product_id):
    s = _current()
    categories = _get(f"{SUPABASE_URL}/rest/v1/fikir_categories?is_active=eq.true&select=*&order=sort_order.asc")
    rows = _get(f"{SUPABASE_URL}/rest/v1/fikir_products?id=eq.{product_id}&limit=1")
    if not rows:
        return redirect(url_for("products_admin.index") + "?error=ምርት+አልተገኘም")
    product = rows[0]

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()[:80]
        try:
            price = float(request.form.get("price") or 0)
        except ValueError:
            price = 0
        category_id = request.form.get("category_id") or None
        description = (request.form.get("description") or "").strip()[:200]
        icon = (request.form.get("icon") or "☕")[:4]
        try:
            stock = int(request.form.get("stock") or 0)
        except ValueError:
            stock = 0
        try:
            low_stock = int(request.form.get("low_stock") or 5)
        except ValueError:
            low_stock = 5

        if not name or price <= 0:
            return render_template_string(FORM_HTML, categories=categories, product=product,
                icons=ICON_OPTIONS, error="ስም እና ዋጋ ያስፈልጋሉ", **s)

        payload = {
            "name": name, "price": price,
            "description": description or "",
            "icon": icon, "stock": stock, "low_stock": low_stock,
        }
        if category_id:
            try: payload["category_id"] = int(category_id)
            except ValueError: pass
        else:
            payload["category_id"] = None

        try:
            r = requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_products?id=eq.{product_id}",
                             json=payload, headers=_headers("return=representation"), timeout=15)
            if r.status_code in (200, 204):
                _audit(s["id"], "product.update", "fikir_products", product_id,
                       {"old": product, "new": payload})
                return redirect(url_for("products_admin.index") + f"?msg=✅+{name}+ተሻሻለ")
            return render_template_string(FORM_HTML, categories=categories, product=product,
                icons=ICON_OPTIONS, error=f"ስህተት: {r.text[:150]}", **s)
        except Exception as e:
            return render_template_string(FORM_HTML, categories=categories, product=product,
                icons=ICON_OPTIONS, error=f"ስህተት: {str(e)[:100]}", **s)

    return render_template_string(FORM_HTML, categories=categories, product=product,
        icons=ICON_OPTIONS, error=None, **s)

@products_admin_bp.route("/toggle/<int:product_id>", methods=["POST"])
@_require_owner
def toggle(product_id):
    s = _current()
    rows = _get(f"{SUPABASE_URL}/rest/v1/fikir_products?id=eq.{product_id}&select=is_active,name&limit=1")
    if not rows:
        return redirect(url_for("products_admin.index"))
    p = rows[0]
    new_state = not p.get("is_active", True)
    try:
        requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_products?id=eq.{product_id}",
                      json={"is_active": new_state}, headers=_headers(), timeout=15)
        _audit(s["id"], "product.toggle", "fikir_products", product_id,
               {"name": p.get("name"), "is_active": new_state})
        action = "ነቅቷል" if new_state else "ተሰናክሏል"
        return redirect(url_for("products_admin.index") + f"?msg=✅+{p.get('name')}+{action}")
    except Exception as e:
        return redirect(url_for("products_admin.index") + f"?error={str(e)[:80]}")

@products_admin_bp.route("/delete/<int:product_id>", methods=["POST"])
@_require_owner
def delete(product_id):
    s = _current()
    rows = _get(f"{SUPABASE_URL}/rest/v1/fikir_products?id=eq.{product_id}&select=name&limit=1")
    name = rows[0]["name"] if rows else f"#{product_id}"
    try:
        r = requests.delete(f"{SUPABASE_URL}/rest/v1/fikir_products?id=eq.{product_id}",
                           headers=_headers(), timeout=15)
        if r.status_code in (200, 204):
            _audit(s["id"], "product.delete", "fikir_products", product_id, {"name": name})
            return redirect(url_for("products_admin.index") + f"?msg=🗑️+{name}+ተጠፋ")
        return redirect(url_for("products_admin.index") + f"?error={r.text[:100]}")
    except Exception as e:
        return redirect(url_for("products_admin.index") + f"?error={str(e)[:80]}")

# ═══════════════════════════════════════════════
# CATEGORIES MANAGEMENT
# ═══════════════════════════════════════════════
CATS_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Categories — FIKIR</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:14px;max-width:640px;margin:0 auto}
  .card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 8px rgba(107,62,30,.06);margin-bottom:14px}
  h2{margin:0 0 14px;font-size:15px;color:#6b3e1e;text-transform:uppercase;letter-spacing:.5px}
  label{display:block;font-size:12px;font-weight:700;color:#5a3a1e;margin-bottom:6px;margin-top:12px}
  input,select{width:100%;padding:12px;border:2px solid #e0d0c0;border-radius:10px;font-size:15px;outline:none;background:#fff;font-family:inherit}
  input:focus{border-color:#6b3e1e}
  button{padding:12px 20px;background:#6b3e1e;color:#fff;border:none;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;margin-top:14px}
  button.danger{background:#c0392b;padding:6px 12px;font-size:12px;margin:0}
  .grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
  .cat{background:#fff;border-radius:12px;padding:14px;margin-bottom:8px;display:flex;align-items:center;gap:12px;box-shadow:0 1px 4px rgba(107,62,30,.05)}
  .cat .ico{font-size:24px;width:36px;text-align:center}
  .cat .info{flex:1}
  .cat .nm{font-weight:700;font-size:14px}
  .cat .meta{font-size:11px;color:#8a6a4a;margin-top:3px}
  .ok{background:#d4edda;color:#1e7e34;padding:10px;border-radius:8px;font-size:13px;margin-bottom:14px}
  .err{background:#ffe0e0;color:#c00;padding:10px;border-radius:8px;font-size:13px;margin-bottom:14px}
</style></head><body>
<div class="top">
  <h1>📂 Categories</h1>
  <a href="{{ url_for('products_admin.index') }}">← Products</a>
</div>
<div class="wrap">

  {% if msg %}<div class="ok">{{ msg }}</div>{% endif %}
  {% if error %}<div class="err">{{ error }}</div>{% endif %}

  <div class="card">
    <h2>➕ አዲስ ምድብ</h2>
    <form method="POST" action="{{ url_for('products_admin.cat_create') }}">
      <label>ስም *</label>
      <input name="name" required maxlength="50" placeholder="ለምሳሌ: Hot Coffee" autofocus>

      <label>Icon</label>
      <div class="grid">
        {% for ic in icons %}
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer;background:#f5ece0;padding:8px;border-radius:8px;margin:0">
          <input type="radio" name="icon" value="{{ ic }}" {% if loop.first %}checked{% endif %} style="width:auto;margin:0">
          <span style="font-size:20px">{{ ic }}</span>
        </label>
        {% endfor %}
      </div>

      <label>Sort Order</label>
      <input name="sort_order" type="number" value="10" min="0">

      <button type="submit">➕ ጨምር</button>
    </form>
  </div>

  <h2 style="font-size:14px;color:#6b3e1e;text-transform:uppercase;letter-spacing:1px;margin:20px 0 10px">📋 ሁሉም Categories ({{ categories|length }})</h2>

  {% for c in categories %}
  <div class="cat">
    <div class="ico">{{ c.icon }}</div>
    <div class="info">
      <div class="nm">{{ c.name }}</div>
      <div class="meta">Slug: {{ c.slug }} · {{ cat_counts.get(c.id, 0) }} ምርቶች</div>
    </div>
    <form method="POST" action="{{ url_for('products_admin.cat_delete', cat_id=c.id) }}" onsubmit="return confirm('{{ c.name }} ማጥፋት?')">
      <button type="submit" class="danger">🗑️</button>
    </form>
  </div>
  {% endfor %}

</div>
</body></html>
"""

@products_admin_bp.route("/categories")
@_require_owner
def categories():
    s = _current()
    cats = _get(f"{SUPABASE_URL}/rest/v1/fikir_categories?select=*&order=sort_order.asc")
    products = _get(f"{SUPABASE_URL}/rest/v1/fikir_products?select=id,category_id")
    cat_counts = {}
    for c in cats:
        cat_counts[c["id"]] = sum(1 for p in products if p.get("category_id") == c["id"])
    return render_template_string(CATS_HTML,
        categories=cats, cat_counts=cat_counts, icons=ICON_OPTIONS,
        msg=request.args.get("msg"), error=request.args.get("error"), **s)

@products_admin_bp.route("/categories/create", methods=["POST"])
@_require_owner
def cat_create():
    s = _current()
    name = (request.form.get("name") or "").strip()[:50]
    icon = (request.form.get("icon") or "📦")[:4]
    try:
        sort_order = int(request.form.get("sort_order") or 10)
    except ValueError:
        sort_order = 10

    if not name:
        return redirect(url_for("products_admin.categories") + "?error=ስም+ያስፈልጋል")

    slug = name.lower().replace(" ", "-").replace("_", "-")[:40]
    payload = {"name": name, "slug": slug, "icon": icon, "sort_order": sort_order, "is_active": True}
    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/fikir_categories",
                         json=payload, headers=_headers("return=representation"), timeout=15)
        if r.status_code in (200, 201):
            return redirect(url_for("products_admin.categories") + f"?msg=✅+{name}+ተጨመረ")
        return redirect(url_for("products_admin.categories") + f"?error={r.text[:100]}")
    except Exception as e:
        return redirect(url_for("products_admin.categories") + f"?error={str(e)[:80]}")

@products_admin_bp.route("/categories/delete/<int:cat_id>", methods=["POST"])
@_require_owner
def cat_delete(cat_id):
    try:
        # Unlink products first
        requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_products?category_id=eq.{cat_id}",
                      json={"category_id": None}, headers=_headers(), timeout=15)
        # Delete category
        requests.delete(f"{SUPABASE_URL}/rest/v1/fikir_categories?id=eq.{cat_id}",
                       headers=_headers(), timeout=15)
        return redirect(url_for("products_admin.categories") + "?msg=🗑️+ተጠፋ")
    except Exception as e:
        return redirect(url_for("products_admin.categories") + f"?error={str(e)[:80]}")
