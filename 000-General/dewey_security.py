#!/usr/bin/env python3
"""
Dewey Security — The Guard at the Gate
======================================
Access control for the 3-part Dewey knowledge system.

PERMISSION LEVELS:
  public   — Anyone can browse the cover (Brain catalog visible)
  key      — Need the internal key to unlock (standard access)
  approval — Key + Derrell must approve before unlock
  vault    — Encrypted, master passphrase required

FLOW:
  unlock request → check permission → 
    public:  granted immediately
    key:     granted if key is valid
    approval: create request → notify Derrell → await approve/deny
    vault:   require master passphrase

USAGE:
  python3 dewey_security.py check <key>              — Check what level a file needs
  python3 dewey_security.py request <key> <who> <why> — Request access to approval-level file
  python3 dewey_security.py approve <request_id>      — Approve a pending request
  python3 dewey_security.py deny <request_id>         — Deny a pending request
  python3 dewey_security.py pending                   — List all pending requests
  python3 dewey_security.py audit                     — Show access audit log
  python3 dewey_security.py classify <key> <level>    — Set permission level for a file
  python3 dewey_security.py guard <key> <who>         — Full guard check (used by pipeline)
"""

import json
import os
import sys
import hashlib
import secrets
from datetime import datetime

BRAIN_ROOT = "/home/allenai/blacktech_brain"
SECURITY_DIR = f"{BRAIN_ROOT}/000-General"
REQUESTS_PATH = f"{SECURITY_DIR}/access_requests.json"
AUDIT_PATH = f"{SECURITY_DIR}/audit_log.json"
PERMISSIONS_PATH = f"{SECURITY_DIR}/permissions.json"
CATALOG_PATH = f"{BRAIN_ROOT}/000-General/dewey_catalog.json"

# ── Default permission map ────────────────────────────────────────
# Files inherit from their Dewey section, overridable per-file
SECTION_DEFAULTS = {
    "000": "public",      # General — index, tools, catalog
    "100": "public",      # Philosophy — mission, values
    "200": "vault",       # Religion — faith, trust docs (ENCRYPTED)
    "300": "key",         # Social Sciences — SSBN, community
    "400": "public",      # Language — style guide
    "500": "key",         # Science — electrical theory
    "600": "key",         # Technology — Pi, servers
    "620": "key",         # Engineering — NEC code
    "650": "approval",    # Management — SOPs, contracts, HR (SENSITIVE)
    "657": "vault",       # Accounting — passcodes, QBO, payroll (ENCRYPTED)
    "690": "approval",    # Construction — estimates, permits
    "700": "public",      # Arts — brand, logos
    "800": "key",         # Literature — proposals
    "900": "public",      # History — timeline
    "910": "key",         # Travel — job sites
    "920": "key",         # Biography — contacts
    "930": "key",         # Archaeology — old projects
    "999": "public",      # Decisions — change log
    "INTERNAL": "key",    # Uncataloged internal files
}

# ── Helpers ────────────────────────────────────────────────────────

def load_json(path, default=None):
    if default is None:
        default = []
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_catalog():
    return load_json(CATALOG_PATH, [])

def load_permissions():
    return load_json(PERMISSIONS_PATH, {})

def save_permissions(perms):
    save_json(PERMISSIONS_PATH, perms)

def load_requests():
    return load_json(REQUESTS_PATH, [])

def save_requests(reqs):
    save_json(REQUESTS_PATH, reqs)

def load_audit():
    return load_json(AUDIT_PATH, [])

def save_audit(log):
    save_json(AUDIT_PATH, log)

# ── Telegram Notification ─────────────────────────────────────────
TELEGRAM_BOT_TOKEN = None  # loaded from env
TELEGRAM_CHAT_ID = "5805015753"  # Derrell's DM

def _get_bot_token():
    global TELEGRAM_BOT_TOKEN
    if TELEGRAM_BOT_TOKEN:
        return TELEGRAM_BOT_TOKEN
    # Try to load from passcode vault
    try:
        result = subprocess.run(
            [sys.executable, f"{BRAIN_ROOT}/000-General/passcode_vault.py", "get", "telegram_bot_token"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            TELEGRAM_BOT_TOKEN = result.stdout.strip()
            return TELEGRAM_BOT_TOKEN
    except:
        pass
    # Fallback: try env
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return TELEGRAM_BOT_TOKEN

def notify_derrell(title, body):
    """Send a Telegram notification to Derrell."""
    token = _get_bot_token()
    if not token:
        return False
    msg = f"🔐 *{title}*\n{body}"
    try:
        subprocess.run([
            "curl", "-s", "-X", "POST",
            f"https://api.telegram.org/bot{token}/sendMessage",
            "-d", f"chat_id={TELEGRAM_CHAT_ID}",
            "-d", f"text={msg}",
            "-d", "parse_mode=Markdown"
        ], capture_output=True, timeout=10)
        return True
    except:
        return False

def get_dewey_section(key):
    """Extract Dewey section from a key like 'internal:650-Management_Business/file.md'"""
    path = key.replace("internal:", "").replace("internal://", "")
    # Try to match Dewey section from path
    parts = path.split("/")
    for part in parts:
        for section in SECTION_DEFAULTS:
            if part.startswith(section):
                return section
    return "INTERNAL"

def get_permission(key):
    """Get the permission level for a file key."""
    # Check per-file override first
    perms = load_permissions()
    if key in perms:
        return perms[key]
    
    # Fall back to section default
    section = get_dewey_section(key)
    return SECTION_DEFAULTS.get(section, "key")

def log_audit(action, key, who, result, detail=""):
    """Log an access event to the audit trail."""
    log = load_audit()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "key": key,
        "who": who,
        "result": result,
        "detail": detail
    }
    log.append(entry)
    save_audit(log)
    return entry

# ── Commands ───────────────────────────────────────────────────────

def cmd_check(key):
    """Check what permission level a file requires."""
    level = get_permission(key)
    section = get_dewey_section(key)
    
    emoji = {"public": "🟢", "key": "🔵", "approval": "🟠", "vault": "🔴"}
    desc = {
        "public": "Anyone can browse — no key needed",
        "key": "Key required — standard access",
        "approval": "Key + Derrell's approval required",
        "vault": "Encrypted — master passphrase required"
    }
    
    print(f"{emoji.get(level, '⚪')} SECURITY CHECK: {key}")
    print(f"   Level:    {level.upper()}")
    print(f"   Section:  {section} ({SECTION_DEFAULTS.get(section, 'unknown')})")
    print(f"   Meaning:  {desc.get(level, 'Unknown')}")
    
    # Check for pending requests on this key
    reqs = load_requests()
    pending = [r for r in reqs if r["key"] == key and r["status"] == "pending"]
    if pending:
        print(f"   ⏳ {len(pending)} pending request(s) for this file")


def cmd_request(key, who, why):
    """Request access to an approval-level file."""
    level = get_permission(key)
    
    if level not in ("approval", "vault"):
        print(f"ℹ️  File is {level.upper()} level — no approval needed.")
        print(f"   Just use: python3 dewey_pipeline.py unlock {key}")
        return
    
    # Check for duplicate pending request
    reqs = load_requests()
    existing = [r for r in reqs if r["key"] == key and r["who"] == who and r["status"] == "pending"]
    if existing:
        print(f"⏳ You already have a pending request for this file (ID: {existing[0]['id']})")
        return
    
    # Create request
    request_id = secrets.token_hex(4)
    request = {
        "id": request_id,
        "timestamp": datetime.now().isoformat(),
        "key": key,
        "who": who,
        "why": why,
        "status": "pending",
        "approved_by": None,
        "approved_at": None
    }
    reqs.append(request)
    save_requests(reqs)
    
    log_audit("request", key, who, "pending", why)
    
    # ── Notify Derrell via Telegram ──────────────────────────────
    notify_derrell(
        "Access Requested",
        f"*Who:* {who}\n*File:* `{key}`\n*Why:* {why}\n*ID:* `{request_id}`\n\nApprove: `/approve {request_id}`\nDeny: `/deny {request_id}`"
    )
    
    print(f"🟠 ACCESS REQUESTED")
    print(f"   ID:      {request_id}")
    print(f"   File:    {key}")
    print(f"   Who:     {who}")
    print(f"   Why:     {why}")
    print(f"   Status:  PENDING — awaiting Derrell's approval")
    print(f"\n   Derrell can approve with:")
    print(f"   python3 dewey_security.py approve {request_id}")


def cmd_approve(request_id):
    """Approve a pending access request."""
    reqs = load_requests()
    for r in reqs:
        if r["id"] == request_id:
            if r["status"] != "pending":
                print(f"❌ Request {request_id} is already {r['status']}")
                return
            r["status"] = "approved"
            r["approved_by"] = "Derrell"
            r["approved_at"] = datetime.now().isoformat()
            save_requests(reqs)
            
            log_audit("approve", r["key"], r["who"], "approved", f"Request {request_id}")
            
            print(f"🟢 APPROVED: Request {request_id}")
            print(f"   File: {r['key']}")
            print(f"   Who:  {r['who']}")
            print(f"   Why:  {r['why']}")
            print(f"\n   They can now unlock with:")
            print(f"   python3 dewey_pipeline.py unlock {r['key']}")
            return
    
    print(f"❌ Request {request_id} not found")


def cmd_deny(request_id):
    """Deny a pending access request."""
    reqs = load_requests()
    for r in reqs:
        if r["id"] == request_id:
            if r["status"] != "pending":
                print(f"❌ Request {request_id} is already {r['status']}")
                return
            r["status"] = "denied"
            r["approved_by"] = "Derrell"
            r["approved_at"] = datetime.now().isoformat()
            save_requests(reqs)
            
            log_audit("deny", r["key"], r["who"], "denied", f"Request {request_id}")
            
            print(f"🔴 DENIED: Request {request_id}")
            print(f"   File: {r['key']}")
            print(f"   Who:  {r['who']}")
            return
    
    print(f"❌ Request {request_id} not found")


def cmd_pending():
    """List all pending access requests."""
    reqs = load_requests()
    pending = [r for r in reqs if r["status"] == "pending"]
    
    if not pending:
        print("✅ No pending access requests.")
        return
    
    print(f"🟠 PENDING ACCESS REQUESTS — {len(pending)} awaiting approval:\n")
    for r in pending:
        print(f"  [{r['id']}] 📂 {r['key']}")
        print(f"      👤 {r['who']}")
        print(f"      💬 {r['why']}")
        print(f"      📅 {r['timestamp'][:16]}")
        print(f"      → approve: python3 dewey_security.py approve {r['id']}")
        print(f"      → deny:    python3 dewey_security.py deny {r['id']}")
        print()


def cmd_audit(limit=50):
    """Show the access audit log."""
    log = load_audit()
    if not log:
        print("📋 Audit log is empty.")
        return
    
    recent = log[-limit:]
    print(f"📋 ACCESS AUDIT LOG — last {len(recent)} events:\n")
    
    emoji = {
        "request": "🟠", "approve": "🟢", "deny": "🔴",
        "unlock": "🔓", "blocked": "🚫", "check": "🔍"
    }
    
    for e in reversed(recent):
        ts = e["timestamp"][:19].replace("T", " ")
        print(f"  {emoji.get(e['action'], '•')} {ts} | {e['action']:8s} | {e['who']:20s} | {e['result']:8s} | {e['key']}")
        if e.get("detail"):
            print(f"     └─ {e['detail']}")


def cmd_classify(key, level):
    """Set a custom permission level for a file."""
    if level not in ("public", "key", "approval", "vault"):
        print(f"❌ Invalid level: {level}")
        print("   Valid: public | key | approval | vault")
        return
    
    perms = load_permissions()
    old = perms.get(key, "(section default)")
    perms[key] = level
    save_permissions(perms)
    
    log_audit("classify", key, "admin", level, f"Changed from {old}")
    
    print(f"🔒 CLASSIFIED: {key}")
    print(f"   Level: {level.upper()} (was: {old})")


def cmd_guard(key, who="unknown"):
    """
    Full guard check — called by dewey_pipeline.py before unlock.
    Returns JSON on stdout for programmatic use.
    """
    level = get_permission(key)
    
    result = {
        "key": key,
        "level": level,
        "who": who,
        "allowed": False,
        "reason": "",
        "request_id": None
    }
    
    if level == "public":
        result["allowed"] = True
        result["reason"] = "public — no restrictions"
        log_audit("unlock", key, who, "granted", "public access")
    
    elif level == "key":
        result["allowed"] = True
        result["reason"] = "key access — standard unlock"
        log_audit("unlock", key, who, "granted", "key access")
    
    elif level == "approval":
        # Check for any approved request for this key
        reqs = load_requests()
        approved = [r for r in reqs if r["key"] == key and r["status"] == "approved"]
        
        if approved:
            result["allowed"] = True
            result["reason"] = f"pre-approved (request {approved[0]['id']} by {approved[0]['who']})"
            log_audit("unlock", key, who, "granted", f"approved request {approved[0]['id']}")
        else:
            result["allowed"] = False
            result["reason"] = "approval required — use 'request' command first"
            log_audit("blocked", key, who, "denied", "no approval")
    
    elif level == "vault":
        result["allowed"] = False
        result["reason"] = "vault — encrypted, master passphrase required"
        log_audit("blocked", key, who, "denied", "vault level")
    
    print(json.dumps(result))


def cmd_init():
    """Initialize security system — create default files if missing."""
    created = []
    
    if not os.path.exists(PERMISSIONS_PATH):
        save_permissions({})
        created.append("permissions.json")
    
    if not os.path.exists(REQUESTS_PATH):
        save_requests([])
        created.append("access_requests.json")
    
    if not os.path.exists(AUDIT_PATH):
        save_audit([])
        created.append("audit_log.json")
    
    if created:
        print(f"🔐 Security system initialized: {', '.join(created)}")
    else:
        print("🔐 Security system already initialized.")


# ── Main ───────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nCommands: check | request | approve | deny | pending | audit | classify | guard | init")
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "check" and len(sys.argv) >= 3:
        cmd_check(sys.argv[2])
    elif cmd == "request" and len(sys.argv) >= 5:
        cmd_request(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
    elif cmd == "approve" and len(sys.argv) >= 3:
        cmd_approve(sys.argv[2])
    elif cmd == "deny" and len(sys.argv) >= 3:
        cmd_deny(sys.argv[2])
    elif cmd == "pending":
        cmd_pending()
    elif cmd == "audit":
        limit = int(sys.argv[2]) if len(sys.argv) >= 3 else 50
        cmd_audit(limit)
    elif cmd == "classify" and len(sys.argv) >= 4:
        cmd_classify(sys.argv[2], sys.argv[3])
    elif cmd == "guard" and len(sys.argv) >= 3:
        who = sys.argv[3] if len(sys.argv) >= 4 else "unknown"
        cmd_guard(sys.argv[2], who)
    elif cmd == "init":
        cmd_init()
    else:
        print(f"❌ Unknown command or missing arguments: {cmd}")
        print("Commands: check | request | approve | deny | pending | audit | classify | guard | init")


if __name__ == "__main__":
    main()
