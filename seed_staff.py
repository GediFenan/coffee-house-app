#!/usr/bin/env python3
"""FIKIR — Seed staff users (owner + 3 workers)"""
import os, hashlib, requests
from datetime import datetime, timezone

SUPABASE_URL = "https://skswircyorzpbcioljcs.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or open("supabase_key.txt").read().strip() if os.path.exists("supabase_key.txt") else None

# Fallback to hardcoded anon key if env/file not found
if not SUPABASE_KEY:
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrc3dpcmN5b3J6cGJjaW9samNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MjMyMzQsImV4cCI6MjEwMzQ5OTIzNH0.ntS52ih33wprDiQ4YGrNzWchuuWqfzc1iyv7_xi_qPM"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def hash_pin(pin: str) -> str:
    """SHA-256 hash for PIN (simple, no bcrypt dep needed)"""
    return hashlib.sha256(pin.encode()).hexdigest()

def create_user(full_name, username, pin, role, phone=None):
    url = SUPABASE_URL + "/rest/v1/fikir_users"
    payload = {
        "full_name": full_name,
        "username": username,
        "pin_hash": hash_pin(pin),
        "role": role,
        "phone": phone,
        "is_active": True
    }
    r = requests.post(url, json=payload, headers=HEADERS, timeout=15)
    if r.status_code in (200, 201):
        print(f"✅ {username:10s} | {role:8s} | PIN: {pin}")
        return True
    elif r.status_code == 409 or "duplicate" in r.text.lower():
        print(f"⚠️  {username:10s} | አስቀድሞ አለ")
        return False
    else:
        print(f"❌ {username:10s} | Status: {r.status_code} | {r.text[:150]}")
        return False

USERS = [
    ("Fikir Owner",   "fikir",  "1234", "owner"),
    ("Hana Tesfaye",  "hana",   "1111", "cashier"),
    ("Dawit Bekele",  "dawit",  "2222", "barista"),
    ("Sara Ahmed",    "sara",   "3333", "kitchen"),
]

if __name__ == "__main__":
    print("=== FIKIR Staff Seeding ===")
    print(f"URL: {SUPABASE_URL}")
    print()
    for name, uname, pin, role in USERS:
        create_user(name, uname, pin, role)
    print()
    print("=== DONE ===")
    print()
    print("LOGIN CREDENTIALS:")
    print("  fikir / 1234  → Owner  (ሁሉንም ያያል)")
    print("  hana  / 1111  → Cashier")
    print("  dawit / 2222  → Barista")
    print("  sara  / 3333  → Kitchen")
