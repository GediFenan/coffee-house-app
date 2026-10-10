# ═══════════════════════════════════════════════
# FIKIR — Telegram Notifications
# Blueprint: /notify/*
# ═══════════════════════════════════════════════
from flask import Blueprint, request, redirect, url_for, session, render_template_string, jsonify
import os, requests
from datetime import datetime, timezone

notify_bp = Blueprint("notify", __name__, url_prefix="/notify")

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

def _get_setting(key, default=""):
    env_map = {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id":   os.getenv("TELEGRAM_CHAT_ID", ""),
    }
    if key in env_map and env_map[key]:
        return env_map[key]
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/fikir_settings?key=eq.{key}&limit=1",
                        headers=_headers(), timeout=10)
        if r.status_code == 200 and r.json():
            return r.json()[0].get("value", default)
    except Exception:
        pass
    return default

def _set_setting(key, value):
    try:
        r = requests.patch(f"{SUPABASE_URL}/rest/v1/fikir_settings?key=eq.{key}",
                          json={"value": value, "updated_at": datetime.now(timezone.utc).isoformat()},
                          headers=_headers("return=representation"), timeout=15)
        if r.status_code in (200, 204) and (r.status_code == 204 or r.json()):
            return True
        requests.post(f"{SUPABASE_URL}/rest/v1/fikir_settings",
                     json={"key": key, "value": value}, headers=_headers(), timeout=15)
        return True
    except Exception as e:
        print("[SETTING ERR]", e)
        return False

def send_telegram(message, parse_mode="HTML"):
    token = _get_setting("telegram_bot_token")
    chat_id = _get_setting("telegram_chat_id")
    if not token or not chat_id:
        return False, "Bot token or Chat ID አልተዘጋጀም"
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": parse_mode,
                  "disable_web_page_preview": True},
            timeout=15
        )
        if r.status_code == 200:
            return True, None
        return False, r.text[:200]
    except Exception as e:
        return False, str(e)[:200]

def notify_new_order(order_id, customer, items, total, method, cashier, base_url="", table_no=""):
    """Beautiful order notification for Telegram"""
    icons = {
        "cash":     ("💵", "CASH"),
        "telebirr": ("📱", "TELEBIRR"),
        "bank":     ("🏦", "BANK"),
        "cbe":      ("🏦", "CBE"),
        "card":     ("💳", "CARD"),
    }
    pm = (method or "cash").lower()
    icon, label = icons.get(pm, ("💳", pm.upper()))
    now = datetime.now(timezone.utc)
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%b %d, %Y")

    # Parse items into pretty lines
    item_lines = []
    total_items = 0
    raw = (items or "").replace("×", " x ")
    for part in raw.split(","):
        part = part.strip()
        if not part: continue
        # Try "1 x Espresso"
        if " x " in part:
            q, n = part.split(" x ", 1)
            try:
                qn = int(q.strip())
                total_items += qn
                item_lines.append(f"   ▪️ <b>{qn}×</b> {n.strip()}")
            except Exception:
                item_lines.append(f"   ▪️ {part}")
        else:
            item_lines.append(f"   ▪️ {part}")
    items_block = "\n".join(item_lines) if item_lines else "   —"

    header = "☕ <b>FIKIR COFFEE HOUSE</b>\n"
    divider = "━━━━━━━━━━━━━━━━━━━━"

    msg = (
        f"{header}"
        f"{divider}\n"
        f"🆕 <b>አዲስ ትዕዛዝ · NEW ORDER</b>\n"
        f"<b>#{order_id}</b>\n"
        f"{divider}\n"
        f"👤 <b>{customer}</b>"
    )
    if table_no:
        msg += f"  ·  🪑 Table {table_no}"
    msg += (
        f"\n👨‍💼 {cashier}\n"
        f"📅 {date_str}  🕐 {time_str}\n"
        f"{divider}\n"
        f"🛒 <b>Items ({total_items})</b>\n"
        f"{items_block}\n"
        f"{divider}\n"
        f"💰 <b>TOTAL:  {float(total):.2f} ETB</b>\n"
        f"{icon} Payment: <b>{label}</b>\n"
    )
    if base_url:
        msg += f"{divider}\n🔗 <a href=\'{base_url}/track/{order_id}\'>Track Order #{order_id}</a>"
    else:
        msg += f"{divider}\n✅ <i>እንኳን ደስ አለዎት!</i>"

    return send_telegram(msg)

def notify_low_stock(name, current, unit, reorder):
    status = "🔴 OUT" if current <= 0 else "🟡 LOW"
    msg = (f"{status} <b>የእቃ ማስጠንቀቂያ</b>\n"
           f"━━━━━━━━━━━━━━━━━\n📦 <b>{name}</b>\n"
           f"📊 ያለ: {current:.1f} {unit}\n"
           f"⚠️  ዝቅተኛ: {reorder:.0f} {unit}")
    return send_telegram(msg)

def notify_expense(category, amount, paid_from, note, user):
    msg = (f"💸 <b>አዲስ ወጪ</b>\n━━━━━━━━━━━━━━━━━\n"
           f"📂 {category}\n💰 <b>{float(amount):.2f} ETB</b>\n"
           f"💳 {paid_from.upper()}\n📝 {note or '-'}\n👤 {user}")
    return send_telegram(msg)

def notify_shift(shift_id, action, user, opening_cash=0, counted=0, expected=0, diff=0):
    if action == "open":
        msg = (f"🟢 <b>Shift ተከፍቷል</b>\n━━━━━━━━━━━━━━━━━\n"
               f"👤 {user}\n💵 Opening: <b>{float(opening_cash):.2f} ETB</b>\n"
               f"🕐 {datetime.now(timezone.utc).strftime('%H:%M')}")
    else:
        di = "✅" if abs(diff) < 1 else ("🔴" if diff < 0 else "🟡")
        msg = (f"🔴 <b>Shift ተዘግቷል</b>\n━━━━━━━━━━━━━━━━━\n"
               f"👤 {user}\n📊 Expected: {float(expected):.2f} ETB\n"
               f"💵 Counted: {float(counted):.2f} ETB\n"
               f"{di} ልዩነት: <b>{float(diff):+.2f} ETB</b>")
    return send_telegram(msg)

SETTINGS_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Telegram — FIKIR</title>
<style>
  body{margin:0;font-family:system-ui,sans-serif;background:#f5ece0;color:#3b1f0b;padding-bottom:30px}
  .top{background:#6b3e1e;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
  .top h1{margin:0;font-size:17px}
  .top a{color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
  .wrap{padding:16px;max-width:560px;margin:0 auto}
  .card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 8px rgba(107,62,30,.06);margin-bottom:14px}
  h2{margin:0 0 12px;font-size:15px;color:#6b3e1e;text-transform:uppercase}
  label{display:block;font-size:12px;font-weight:700;color:#5a3a1e;margin-bottom:6px;margin-top:14px}
  label:first-child{margin-top:0}
  input{width:100%;padding:13px;border:2px solid #e0d0c0;border-radius:10px;font-size:13px;outline:none;background:#fff;font-family:monospace;color:#3b1f0b}
  input:focus{border-color:#6b3e1e}
  button{width:100%;padding:14px;background:#6b3e1e;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-top:16px}
  button.test{background:#2a7d2a}
  .hint{font-size:12px;color:#8a6a4a;margin-top:6px}
  .ok{background:#d4edda;color:#1e7e34;padding:12px;border-radius:8px;font-size:13px;margin-bottom:14px;font-weight:600}
  .err{background:#ffe0e0;color:#c00;padding:12px;border-radius:8px;font-size:13px;margin-bottom:14px}
  .info{background:#fff3cd;border-left:4px solid #f0ad4e;padding:12px;border-radius:8px;font-size:12px;color:#8a6a4a;margin-bottom:14px;line-height:1.6}
  code{background:#f0e6d8;color:#6b3e1e;padding:2px 6px;border-radius:4px;font-size:12px;font-weight:700}
</style></head><body>
<div class="top">
  <h1>📱 Telegram</h1>
  <a href="{{ url_for('staff.dashboard') }}">← Back</a>
</div>
<div class="wrap">
  {% if msg %}<div class="ok">{{ msg }}</div>{% endif %}
  {% if error %}<div class="err">{{ error }}</div>{% endif %}

  <div class="info">
    <b>📌 Notifications የሚላኩላቸው:</b><br>
    ✅ አዲስ ትዕዛዝ · ✅ Low Stock · ✅ አዲስ ወጪ · ✅ Shift መክፈት/መዝጋት
  </div>

  <div class="card">
    <h2>🔑 Bot Settings</h2>
    <form method="POST" action="{{ url_for('notify.save_settings') }}">
      <label>Bot Token</label>
      <input name="token" value="{{ token }}" autocomplete="off">
      <label>Chat ID</label>
      <input name="chat_id" value="{{ chat_id }}" autocomplete="off">
      <button type="submit">💾 አስቀምጥ</button>
    </form>
    <form method="POST" action="{{ url_for('notify.test') }}">
      <button type="submit" class="test">📤 Test Notification</button>
    </form>
  </div>
</div>
</body></html>
"""

@notify_bp.route("/settings")
@_require_owner
def settings():
    s = _current()
    token = _get_setting("telegram_bot_token")
    chat_id = _get_setting("telegram_chat_id")
    return render_template_string(SETTINGS_HTML,
        token=token, chat_id=chat_id, msg=request.args.get("msg"), error=request.args.get("error"), **s)

@notify_bp.route("/save", methods=["POST"])
@_require_owner
def save_settings():
    token = (request.form.get("token") or "").strip()
    chat_id = (request.form.get("chat_id") or "").strip()
    _set_setting("telegram_bot_token", token)
    _set_setting("telegram_chat_id", chat_id)
    return redirect(url_for("notify.settings") + "?msg=✅+Settings+ተቀምጠዋል")

@notify_bp.route("/test", methods=["POST"])
@_require_owner
def test():
    ok, err = send_telegram("🧪 <b>FIKIR Test</b>\n✅ Telegram alerts ይሰራሉ!")
    if ok:
        return redirect(url_for("notify.settings") + "?msg=✅+Test+ተልኳል")
    return redirect(url_for("notify.settings") + f"?error=❌+{err}")

@notify_bp.route("/api/send", methods=["POST"])
def api_send():
    data = request.get_json() or {}
    msg = data.get("message", "")
    if not msg:
        return jsonify({"ok": False, "error": "message required"}), 400
    ok, err = send_telegram(msg)
    return jsonify({"ok": ok, "error": err})
