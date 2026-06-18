#!/usr/bin/env python3
"""
🔐 Dewey Security Guard — Access Control Engine
=================================================
Commands:
  guard <key> <who>         Check if access is allowed → JSON {allowed, level, reason}
  request <key> <who> <why> Create an access request
  approve <request_id>      Approve a pending request
  deny <request_id>         Deny a pending request
  check <key> <who>         Check permission level for a key
  classify <key>            Classify a file's security level
"""

import json
import os
import sys
import uuid
from datetime import datetime

BRAIN_ROOT = "/home/allenai/blacktech_brain"
REQUESTS_PATH = f"{BRAIN_ROOT}/000-General/access_requests.json"
AUDIT_PATH = f"{BRAIN_ROOT}/000-General/audit_log.json"
PERMISSIONS_PATH = f"{BRAIN_ROOT}/000-General/permissions.json"

# ── Helpers ─────────────────────────────────────────────────

def load_json(path, default=None):
    if default is None:
        default = [] if path.endswith("requests.json") or path.endswith("audit_log.json") else {}
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def audit(action, key, who, result, detail=""):
    log = load_json(AUDIT_PATH, [])
    log.append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "key": key,
        "who": who,
        "result": result,
        "detail": detail
    })
    save_json(AUDIT_PATH, log)

# ── Classify ───────────────────────────────────────────────

def classify_key(key):
    """Determine security level for a key based on permission rules."""
    perms = load_json(PERMISSIONS_PATH, {"rules": [], "default": "key"})
    rules = perms.get("rules", [])
    
    # Normalize key — strip "internal:" prefix
    clean_key = key.replace("internal:", "", 1) if key.startswith("internal:") else key
    
    for rule in rules:
        pattern = rule["pattern"]
        # Simple glob matching
        if pattern == "*":
            return rule["level"], rule.get("reason", "Default")
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            if clean_key.startswith(prefix + "/") or clean_key.startswith(prefix + "-"):
                return rule["level"], rule.get("reason", "")
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            if clean_key.startswith(prefix):
                return rule["level"], rule.get("reason", "")
        if pattern == clean_key:
            return rule["level"], rule.get("reason", "")
    
    return perms.get("default", "key"), "Default"

# ── Guard ──────────────────────────────────────────────────

def cmd_guard(key, who="unknown"):
    """Check if access is allowed. Returns JSON."""
    level, reason = classify_key(key)
    
    if level == "public":
        audit("check", key, who, "granted", "public access")
        print(json.dumps({"allowed": True, "level": "public", "reason": "Open access"}))
        return
    
    if level == "key":
        audit("check", key, who, "granted", "key-level access")
        print(json.dumps({"allowed": True, "level": "key", "reason": "Key required — granted"}))
        return
    
    if level == "approval":
        # Check if there's an existing approved request
        requests = load_json(REQUESTS_PATH, [])
        approved = [r for r in requests 
                    if r["key"] == key and r["who"] == who and r["status"] == "approved"]
        if approved:
            audit("check", key, who, "granted", f"pre-approved: {approved[0]['id']}")
            print(json.dumps({"allowed": True, "level": "approval", "reason": "Previously approved"}))
            return
        
        audit("blocked", key, who, "denied", "no approval")
        print(json.dumps({
            "allowed": False, 
            "level": "approval", 
            "reason": f"Requires Derrell's approval — {reason}",
            "action": f"python3 dewey_security.py request {key} {who} '<why>'"
        }))
        return
    
    if level == "vault":
        audit("blocked", key, who, "denied", "vault locked")
        print(json.dumps({
            "allowed": False,
            "level": "vault",
            "reason": f"Vault-locked — {reason}",
            "action": "Use passcode_vault.py to decrypt"
        }))
        return
    
    # Unknown level
    audit("blocked", key, who, "denied", f"unknown level: {level}")
    print(json.dumps({"allowed": False, "level": level, "reason": "Unknown security level"}))

# ── Request ────────────────────────────────────────────────

def cmd_request(key, who, why):
    """Create an access request for approval."""
    requests = load_json(REQUESTS_PATH, [])
    
    # Check for duplicates
    existing = [r for r in requests if r["key"] == key and r["who"] == who and r["status"] == "pending"]
    if existing:
        print(f"⚠️  Pending request already exists: #{existing[0]['id']}")
        return
    
    req_id = uuid.uuid4().hex[:8]
    req = {
        "id": req_id,
        "timestamp": datetime.now().isoformat(),
        "key": key,
        "who": who,
        "why": why,
        "status": "pending"
    }
    requests.append(req)
    save_json(REQUESTS_PATH, requests)
    audit("request", key, who, "pending", why)
    
    print(f"🟠 Request #{req_id} created")
    print(f"   Key:  {key}")
    print(f"   Who:  {who}")
    print(f"   Why:  {why}")
    print(f"   Status: PENDING — awaiting Derrell's approval")
    print(f"   Dashboard: http://localhost:8096")

# ── Approve ────────────────────────────────────────────────

def cmd_approve(req_id):
    """Approve a pending request."""
    requests = load_json(REQUESTS_PATH, [])
    
    for r in requests:
        if r["id"] == req_id and r["status"] == "pending":
            r["status"] = "approved"
            r["approved_by"] = "Derrell"
            r["approved_at"] = datetime.now().isoformat()
            save_json(REQUESTS_PATH, requests)
            audit("approve", r["key"], r["who"], "approved", f"Request {req_id}")
            print(f"🟢 Request #{req_id} APPROVED — {r['who']} can now unlock {r['key']}")
            return
    
    print(f"❌ Request #{req_id} not found or already resolved")

# ── Deny ───────────────────────────────────────────────────

def cmd_deny(req_id):
    """Deny a pending request."""
    requests = load_json(REQUESTS_PATH, [])
    
    for r in requests:
        if r["id"] == req_id and r["status"] == "pending":
            r["status"] = "denied"
            r["denied_by"] = "Derrell"
            r["denied_at"] = datetime.now().isoformat()
            save_json(REQUESTS_PATH, requests)
            audit("deny", r["key"], r["who"], "denied", f"Request {req_id}")
            print(f"🔴 Request #{req_id} DENIED — {r['who']} blocked from {r['key']}")
            return
    
    print(f"❌ Request #{req_id} not found or already resolved")

# ── Check ──────────────────────────────────────────────────

def cmd_check(key, who="unknown"):
    """Check permission level (non-blocking, no audit)."""
    level, reason = classify_key(key)
    print(f"🔍 {key}")
    print(f"   Level:  {level.upper()}")
    print(f"   Reason: {reason}")
    print(f"   Who:    {who}")
    
    if level == "approval":
        requests = load_json(REQUESTS_PATH, [])
        approved = [r for r in requests 
                    if r["key"] == key and r["who"] == who and r["status"] == "approved"]
        pending = [r for r in requests 
                   if r["key"] == key and r["who"] == who and r["status"] == "pending"]
        if approved:
            print(f"   ✅ Pre-approved: #{approved[0]['id']}")
        elif pending:
            print(f"   🟠 Pending: #{pending[0]['id']}")
        else:
            print(f"   ❌ No approval — request with: dewey_security.py request {key} {who} '<why>'")

# ── Main ───────────────────────────────────────────────────

COMMANDS = {
    "guard": (lambda: cmd_guard(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "unknown"),
              "guard <key> <who>"),
    "request": (lambda: cmd_request(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "No reason given"),
                "request <key> <who> <why>"),
    "approve": (lambda: cmd_approve(sys.argv[2]),
                "approve <request_id>"),
    "deny": (lambda: cmd_deny(sys.argv[2]),
             "deny <request_id>"),
    "check": (lambda: cmd_check(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "unknown"),
              "check <key> <who>"),
    "classify": (lambda: print(f"{classify_key(sys.argv[2])[0]}"),
                 "classify <key>"),
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🔐 Dewey Security Guard")
        print("Commands: guard | request | approve | deny | check | classify")
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    if cmd in COMMANDS:
        COMMANDS[cmd][0]()
    else:
        print(f"❌ Unknown command: {cmd}")
        print("Commands: guard | request | approve | deny | check | classify")
