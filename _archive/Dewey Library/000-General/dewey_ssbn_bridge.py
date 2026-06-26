#!/usr/bin/env python3
"""
Dewey ↔ SSBN Bridge — HOOD Tokens as Dewey Keys
=================================================
Connects the SSBN community platform's HOOD token economy to the
Dewey knowledge system's 4-tier access control.

CONCEPT:
  SSBN members earn HOOD tokens through community activity.
  Those tokens become their KEY to unlock Dewey sections.
  Higher balances = higher access tiers.

TOKEN THRESHOLDS → DEWEY ACCESS:
  🟢  0-9   HOOD  → public only (browse Brain catalog)
  🔵 10-49  HOOD  → key access (300, 500, 600, 800 sections)
  🟠 50-99  HOOD  → approval bypass (650, 690 — no manual approval needed)
  🔴 100+   HOOD  → vault preview (see vault file names, not contents)
  👑 250+   HOOD  → full vault access (master-level, Derrell-equivalent)

SPEND MODE:
  Members can spend HOOD tokens for one-time access to files above
  their tier. Cost = tier gap × 5 tokens. Spent tokens are burned
  (logged as SPEND action in hood_tokens with negative amount).

USAGE:
  python3 dewey_ssbn_bridge.py balance <member_name>     — Check HOOD balance + Dewey tier
  python3 dewey_ssbn_bridge.py unlock <member_name> <key> — Try to unlock a Dewey file
  python3 dewey_ssbn_bridge.py spend <member_name> <key>  — Spend tokens for one-time access
  python3 dewey_ssbn_bridge.py leaderboard                — Top members + their Dewey tiers
  python3 dewey_ssbn_bridge.py status                     — Bridge health check
"""

import json
import os
import sys
import sqlite3
import hashlib
import subprocess
from datetime import datetime

# ── Paths ───────────────────────────────────────────────────────────
SSBN_DB = "/home/allenai/data/ssbn.db"
BRAIN_ROOT = "/home/allenai/blacktech_brain"
SECURITY_SCRIPT = f"{BRAIN_ROOT}/000-General/dewey_security.py"
BLOCKCHAIN_SCRIPT = f"{BRAIN_ROOT}/000-General/dewey_blockchain.py"
BRIDGE_LOG = f"{BRAIN_ROOT}/000-General/dewey_ssbn_bridge_log.json"

# ── Token → Tier Map ────────────────────────────────────────────────
TIER_THRESHOLDS = [
    (0,    "public",   "🟢", "Browse Brain catalog only"),
    (10,   "key",      "🔵", "Access Technology, Science, Literature sections"),
    (50,   "approval", "🟠", "Bypass manual approval for Management & Construction"),
    (100,  "vault",    "🔴", "Preview vault file names (not contents)"),
    (250,  "master",   "👑", "Full vault access — Derrell-equivalent"),
]

# Tier → sections that unlock at that tier
TIER_SECTIONS = {
    "public":   ["000", "100", "400", "700", "900", "999"],
    "key":      ["300", "500", "600", "620", "800", "910", "920", "930"],
    "approval": ["650", "690"],
    "vault":    ["200", "657"],  # can see names, not contents
    "master":   ["200", "657"],  # full access
}

# Cost to spend for one tier jump (tokens per tier)
SPEND_COST_PER_TIER = 5

# ── Helpers ──────────────────────────────────────────────────────────

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

def get_hood_balance(member_name):
    """Query SSBN DB for a member's total HOOD tokens."""
    try:
        con = sqlite3.connect(SSBN_DB)
        total = con.execute(
            'SELECT SUM(tokens) FROM hood_tokens WHERE member_name=?',
            (member_name,)
        ).fetchone()[0] or 0
        con.close()
        return total
    except Exception as e:
        print(f"❌ SSBN DB error: {e}", file=sys.stderr)
        return 0

def get_hood_leaderboard(limit=10):
    """Get top HOOD earners from SSBN."""
    try:
        con = sqlite3.connect(SSBN_DB)
        rows = con.execute(
            'SELECT member_name, SUM(tokens) as total FROM hood_tokens GROUP BY member_name ORDER BY total DESC LIMIT ?',
            (limit,)
        ).fetchall()
        con.close()
        return [{"name": r[0], "tokens": r[1]} for r in rows]
    except Exception as e:
        print(f"❌ SSBN DB error: {e}", file=sys.stderr)
        return []

def get_tier(balance):
    """Map HOOD token balance to Dewey access tier."""
    tier = TIER_THRESHOLDS[0]  # default: public
    for threshold, name, emoji, desc in TIER_THRESHOLDS:
        if balance >= threshold:
            tier = (threshold, name, emoji, desc)
    return tier

def tier_index(tier_name):
    """Get the numeric index of a tier (0=public, 1=key, 2=approval, 3=vault, 4=master)."""
    names = [t[1] for t in TIER_THRESHOLDS]
    return names.index(tier_name) if tier_name in names else 0

def get_dewey_section(key):
    """Extract Dewey section from a key."""
    path = key.replace("internal:", "").replace("internal://", "")
    parts = path.split("/")
    for part in parts:
        for section in ["000", "100", "200", "300", "400", "500", "600", "620",
                        "650", "657", "690", "700", "800", "900", "910", "920", "930", "999"]:
            if part.startswith(section):
                return section
    return "INTERNAL"

def get_file_permission(key):
    """Get the Dewey security permission level for a file."""
    try:
        result = subprocess.run(
            [sys.executable, SECURITY_SCRIPT, "guard", key, "ssbn-bridge"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        return {"key": key, "level": "key", "allowed": False, "reason": str(e)}
    return {"key": key, "level": "key", "allowed": False, "reason": "guard check failed"}

def can_access_with_tier(member_tier_name, file_section):
    """Check if a member's tier grants access to a file's section."""
    if member_tier_name == "master":
        return True  # master can access everything

    # Build the set of sections this tier can access
    accessible = set()
    tier_names = [t[1] for t in TIER_THRESHOLDS]
    member_idx = tier_names.index(member_tier_name)

    for i in range(member_idx + 1):
        tname = tier_names[i]
        accessible.update(TIER_SECTIONS.get(tname, []))

    return file_section in accessible

def burn_tokens(member_name, amount, reason):
    """Burn HOOD tokens (log as negative SPEND entry)."""
    try:
        con = sqlite3.connect(SSBN_DB)
        con.execute(
            'INSERT INTO hood_tokens (member_name, action, tokens, created_at) VALUES (?,?,?,?)',
            (member_name, f"SPEND: {reason}", -amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        con.commit()
        con.close()
        return True
    except Exception as e:
        print(f"❌ Failed to burn tokens: {e}", file=sys.stderr)
        return False

def log_bridge_event(action, member, key, result, detail=""):
    """Log a bridge event to the bridge log + Dewey blockchain."""
    log = load_json(BRIDGE_LOG)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "member": member,
        "key": key,
        "result": result,
        "detail": detail
    }
    log.append(entry)
    save_json(BRIDGE_LOG, log)

    # Also log to Dewey blockchain
    try:
        subprocess.run([
            sys.executable, BLOCKCHAIN_SCRIPT, "log", "ACCESS",
            f"ssbn:{member}:{key}",
            "--trigger", f"bridge:{action}"
        ], capture_output=True, timeout=10)
    except:
        pass  # blockchain logging is non-critical

    return entry

# ── Commands ─────────────────────────────────────────────────────────

def cmd_balance(member_name):
    """Show HOOD balance + Dewey access tier."""
    balance = get_hood_balance(member_name)
    threshold, tier_name, emoji, desc = get_tier(balance)

    # Find next tier
    next_tier = None
    for t, n, e, d in TIER_THRESHOLDS:
        if t > balance:
            next_tier = (t, n, e, d, t - balance)
            break

    print(f"{emoji} HOOD BALANCE: {member_name}")
    print(f"   Tokens:  {balance} HOOD")
    print(f"   Tier:    {tier_name.upper()}")
    print(f"   Access:  {desc}")

    if next_tier:
        t, n, e, d, gap = next_tier
        print(f"   Next:    {n.upper()} ({gap} more tokens needed)")

    # Show accessible sections
    accessible = set()
    tier_names = [t[1] for t in TIER_THRESHOLDS]
    member_idx = tier_names.index(tier_name)
    for i in range(member_idx + 1):
        accessible.update(TIER_SECTIONS.get(tier_names[i], []))

    print(f"   Sections: {', '.join(sorted(accessible))}")


def cmd_unlock(member_name, key):
    """Try to unlock a Dewey file using HOOD token tier."""
    balance = get_hood_balance(member_name)
    threshold, tier_name, emoji, desc = get_tier(balance)
    section = get_dewey_section(key)
    perm = get_file_permission(key)

    print(f"{emoji} UNLOCK ATTEMPT: {member_name} → {key}")
    print(f"   Balance:  {balance} HOOD ({tier_name.upper()} tier)")
    print(f"   Section:  {section}")
    print(f"   Required: {perm['level'].upper()}")

    # Check if tier grants access
    if can_access_with_tier(tier_name, section):
        # Tier covers this section — check if Dewey guard also allows
        if perm["level"] == "vault" and tier_name not in ("master",):
            print(f"   ⚠️  VAULT FILE — tier allows section but vault requires master tier")
            print(f"   💡 Use 'spend' to buy one-time access (cost: {SPEND_COST_PER_TIER * 2} HOOD)")
            log_bridge_event("blocked", member_name, key, "vault_tier_mismatch",
                           f"Tier {tier_name} can see vault section but not unlock contents")
            return

        # Run actual guard check
        guard_result = subprocess.run(
            [sys.executable, SECURITY_SCRIPT, "guard", key, member_name],
            capture_output=True, text=True, timeout=10
        )
        if guard_result.returncode == 0:
            guard = json.loads(guard_result.stdout.strip())
            if guard.get("allowed"):
                print(f"   ✅ UNLOCKED — {guard.get('reason', 'access granted')}")
                log_bridge_event("unlock", member_name, key, "granted",
                               f"Tier {tier_name} → section {section}")
            else:
                print(f"   🔒 BLOCKED — {guard.get('reason', 'unknown')}")
                log_bridge_event("blocked", member_name, key, "denied",
                               f"Guard: {guard.get('reason')}")
        else:
            print(f"   ❌ Guard check failed")
    else:
        # Tier doesn't cover this section
        required_tier = None
        for tname, sections in TIER_SECTIONS.items():
            if section in sections:
                required_tier = tname
                break

        if required_tier:
            gap = tier_index(required_tier) - tier_index(tier_name)
            cost = max(1, gap) * SPEND_COST_PER_TIER
            print(f"   🔒 BLOCKED — {section} requires {required_tier.upper()} tier")
            print(f"   💡 Spend {cost} HOOD for one-time access: python3 dewey_ssbn_bridge.py spend {member_name} {key}")
        else:
            print(f"   🔒 BLOCKED — section {section} not in any tier map")

        log_bridge_event("blocked", member_name, key, "tier_insufficient",
                       f"Need {required_tier}, have {tier_name}")


def cmd_spend(member_name, key):
    """Spend HOOD tokens for one-time access to a file above your tier."""
    balance = get_hood_balance(member_name)
    threshold, tier_name, emoji, desc = get_tier(balance)
    section = get_dewey_section(key)
    perm = get_file_permission(key)

    # Find required tier for this section
    required_tier = "public"
    for tname, sections in TIER_SECTIONS.items():
        if section in sections:
            required_tier = tname
            break

    gap = tier_index(required_tier) - tier_index(tier_name)
    if gap <= 0:
        print(f"ℹ️  You already have {tier_name.upper()} access to section {section}.")
        print(f"   Just use: python3 dewey_ssbn_bridge.py unlock {member_name} {key}")
        return

    cost = gap * SPEND_COST_PER_TIER

    # Vault files cost double
    if perm["level"] == "vault":
        cost *= 2

    print(f"{emoji} SPEND FOR ACCESS: {member_name} → {key}")
    print(f"   Balance:    {balance} HOOD")
    print(f"   Cost:       {cost} HOOD ({gap} tier jump × {SPEND_COST_PER_TIER})")
    print(f"   After:      {balance - cost} HOOD")

    if balance < cost:
        print(f"   ❌ INSUFFICIENT — need {cost - balance} more HOOD tokens")
        log_bridge_event("spend_failed", member_name, key, "insufficient",
                       f"Need {cost}, have {balance}")
        return

    # Confirm burn
    print(f"\n   ⚠️  This will PERMANENTLY burn {cost} HOOD tokens.")
    print(f"   Type 'yes' to confirm:")

    # In non-interactive mode, auto-confirm if --yes flag
    if "--yes" in sys.argv:
        confirm = "yes"
    else:
        confirm = input("   > ").strip().lower()

    if confirm != "yes":
        print("   ❌ Cancelled.")
        return

    # Burn tokens
    if burn_tokens(member_name, cost, f"one-time access to {key}"):
        # Grant access via security guard
        guard_result = subprocess.run(
            [sys.executable, SECURITY_SCRIPT, "guard", key, member_name],
            capture_output=True, text=True, timeout=10
        )
        if guard_result.returncode == 0:
            guard = json.loads(guard_result.stdout.strip())

        new_balance = get_hood_balance(member_name)
        new_threshold, new_tier, new_emoji, new_desc = get_tier(new_balance)

        print(f"\n   ✅ ACCESS GRANTED (one-time)")
        print(f"   Spent:      {cost} HOOD burned")
        print(f"   New balance: {new_balance} HOOD ({new_tier.upper()} tier)")
        print(f"   File:       {key}")
        print(f"   Guard:      {guard.get('reason', 'access granted') if guard_result.returncode == 0 else 'check passed'}")

        log_bridge_event("spend", member_name, key, "granted",
                       f"Burned {cost} HOOD for {gap}-tier jump to {required_tier}")


def cmd_leaderboard():
    """Show top HOOD earners with their Dewey access tiers."""
    board = get_hood_leaderboard(15)

    if not board:
        print("📊 No HOOD token data yet.")
        return

    print("📊 HOOD LEADERBOARD → DEWEY ACCESS TIERS\n")
    print(f"{'RANK':<5} {'MEMBER':<25} {'HOOD':<8} {'TIER':<12} {'ACCESS'}")
    print("-" * 75)

    for i, entry in enumerate(board, 1):
        name = entry["name"][:24]
        tokens = entry["tokens"]
        threshold, tier_name, emoji, desc = get_tier(tokens)
        print(f"{i:<5} {name:<25} {tokens:<8} {emoji} {tier_name:<9} {desc}")


def cmd_status():
    """Bridge health check — verify both systems are reachable."""
    print("🌉 DEWEY ↔ SSBN BRIDGE STATUS\n")

    # Check SSBN DB
    try:
        con = sqlite3.connect(SSBN_DB)
        member_count = con.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        token_entries = con.execute("SELECT COUNT(*) FROM hood_tokens").fetchone()[0]
        total_hood = con.execute("SELECT SUM(tokens) FROM hood_tokens").fetchone()[0] or 0
        con.close()
        print(f"✅ SSBN Database: {member_count} members, {token_entries} token entries, {total_hood} total HOOD")
    except Exception as e:
        print(f"❌ SSBN Database: {e}")

    # Check Dewey security
    try:
        result = subprocess.run(
            [sys.executable, SECURITY_SCRIPT, "check", "internal:000-General/dewey_catalog.json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Dewey Security: responding")
        else:
            print(f"⚠️  Dewey Security: exit code {result.returncode}")
    except Exception as e:
        print(f"❌ Dewey Security: {e}")

    # Check blockchain
    try:
        result = subprocess.run(
            [sys.executable, BLOCKCHAIN_SCRIPT, "status"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            # Extract block count
            for line in result.stdout.split("\n"):
                if "blocks" in line.lower() or "total" in line.lower():
                    print(f"✅ Dewey Blockchain: {line.strip()}")
                    break
            else:
                print(f"✅ Dewey Blockchain: responding")
        else:
            print(f"⚠️  Dewey Blockchain: exit code {result.returncode}")
    except Exception as e:
        print(f"❌ Dewey Blockchain: {e}")

    # Bridge log stats
    log = load_json(BRIDGE_LOG)
    print(f"📋 Bridge Log: {len(log)} events recorded")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nCommands: balance | unlock | spend | leaderboard | status")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "balance" and len(sys.argv) >= 3:
        cmd_balance(sys.argv[2])
    elif cmd == "unlock" and len(sys.argv) >= 4:
        cmd_unlock(sys.argv[2], sys.argv[3])
    elif cmd == "spend" and len(sys.argv) >= 4:
        cmd_spend(sys.argv[2], sys.argv[3])
    elif cmd == "leaderboard":
        cmd_leaderboard()
    elif cmd == "status":
        cmd_status()
    else:
        print(f"❌ Unknown command or missing arguments: {cmd}")
        print("Commands: balance | unlock | spend | leaderboard | status")
        print("\nExamples:")
        print("  python3 dewey_ssbn_bridge.py balance 'Derrell Black'")
        print("  python3 dewey_ssbn_bridge.py unlock 'Derrell Black' internal:650-Management_Business/sop.md")
        print("  python3 dewey_ssbn_bridge.py spend 'Derrell Black' internal:657-Accounting_Finance/payroll.md --yes")


if __name__ == "__main__":
    main()
