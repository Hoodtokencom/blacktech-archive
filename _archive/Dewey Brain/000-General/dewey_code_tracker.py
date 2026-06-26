#!/usr/bin/env python3
"""
Dewey Code Tracker — Automatic Code Change Documentation
=========================================================
Every code edit in the Dewey system is logged with:
  - Timestamp (ISO8601)
  - Who made the change
  - What file was changed
  - Diff summary (lines added/removed, key changes)
  - SHA256 hashes (before/after)
  - Trigger (manual/pipeline/cron/sync)
  - Blockchain block index (linked to immutable audit trail)

This is the CODE DEPARTMENT — the system that documents itself.
All changelogs sync through the 3-part system:
  Brain (catalog) → Body (Internal Drive) → GitHub (archive backup)

USAGE:
  python3 dewey_code_tracker.py log <file> [--who NAME] [--trigger TYPE]
      Record a code change. Computes diff against last known hash.

  python3 dewey_code_tracker.py history [--limit N] [--file PATTERN]
      View code change history.

  python3 dewey_code_tracker.py diff <entry_id>
      Show full diff for a specific changelog entry.

  python3 dewey_code_tracker.py verify [--file PATH]
      Check code integrity — hashes match? files unchanged?

  python3 dewey_code_tracker.py status
      Summary stats: total changes, files tracked, last change.

INTEGRATION:
  Called automatically by dewey_pipeline.py on:
    - sync (code files backed up → logged)
    - trash (code moved to archive → logged)
    - Any operation touching 000-General/*.py files
"""

import json
import os
import sys
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
BRAIN_ROOT = "/home/allenai/blacktech_brain"
GENERAL_DIR = f"{BRAIN_ROOT}/000-General"
CHANGELOG_PATH = f"{GENERAL_DIR}/dewey_code_changelog.json"
CHAIN_FILE = f"{GENERAL_DIR}/dewey_blockchain.json"
BLOCKCHAIN_SCRIPT = f"{GENERAL_DIR}/dewey_blockchain.py"
INTERNAL_DRIVE = "/media/allenai/Expansion/Blacktech_Drive"
INTERNAL_CODE_BACKUP = f"{INTERNAL_DRIVE}/6-Operations/Brain/code_backups"

# ── Files we track (Dewey system code) ─────────────────────────────
TRACKED_PATTERNS = [
    "dewey_*.py",
    "dewey_*.json",
    "dewey_*.md",
    "find_brain.py",
    "passcode_vault.py",
    "dewey-constitutional.md",
    "dewey_library_schematic.html",
]

def get_tracked_files():
    """Return list of all tracked code files in 000-General."""
    files = []
    for pattern in TRACKED_PATTERNS:
        for p in Path(GENERAL_DIR).glob(pattern):
            if p.is_file():
                files.append(str(p))
    return sorted(set(files))


def file_sha256(path):
    """SHA256 hash of file contents."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_changelog():
    """Load the code changelog from disk."""
    if not os.path.exists(CHANGELOG_PATH):
        return []
    with open(CHANGELOG_PATH) as f:
        return json.load(f)


def save_changelog(log):
    """Save changelog to disk + backup to Internal Drive."""
    os.makedirs(os.path.dirname(CHANGELOG_PATH), exist_ok=True)
    with open(CHANGELOG_PATH, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    
    # Backup to Internal Drive
    os.makedirs(INTERNAL_CODE_BACKUP, exist_ok=True)
    backup_path = f"{INTERNAL_CODE_BACKUP}/dewey_code_changelog.json"
    with open(backup_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def compute_diff_summary(filepath, old_hash):
    """
    Compute a diff summary for a file.
    Returns: {lines_added, lines_removed, filesize_before, filesize_after, 
              key_changes: [list of significant change descriptions]}
    """
    summary = {
        "lines_added": 0,
        "lines_removed": 0,
        "filesize_before": 0,
        "filesize_after": 0,
        "key_changes": [],
    }
    
    if not os.path.exists(filepath):
        summary["key_changes"].append("FILE DELETED")
        return summary
    
    current_size = os.path.getsize(filepath)
    summary["filesize_after"] = current_size
    
    # Try to get git diff if available, otherwise basic line count
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", filepath],
            capture_output=True, text=True, timeout=5,
            cwd=BRAIN_ROOT
        )
        if result.stdout.strip():
            # Parse "1 file changed, X insertions(+), Y deletions(-)"
            stat_line = result.stdout.strip()
            if "insertions" in stat_line or "deletions" in stat_line:
                import re
                ins = re.search(r'(\d+)\s+insertion', stat_line)
                dels = re.search(r'(\d+)\s+deletion', stat_line)
                summary["lines_added"] = int(ins.group(1)) if ins else 0
                summary["lines_removed"] = int(dels.group(1)) if dels else 0
    except:
        pass
    
    # If no git, do basic line count
    if summary["lines_added"] == 0 and summary["lines_removed"] == 0:
        try:
            with open(filepath) as f:
                lines = f.readlines()
            summary["lines_added"] = len(lines)
            summary["key_changes"].append(f"File has {len(lines)} lines, {current_size} bytes")
        except:
            pass
    
    # Detect key changes by scanning for structural markers
    try:
        with open(filepath) as f:
            content = f.read()
        
        structural_markers = {
            "def ": "function",
            "class ": "class",
            "import ": "import",
            "DEWEY_MAP": "classification map",
            "BRAIN_ROOT": "path configuration",
            "CHANGELOG": "changelog reference",
            "BLOCKCHAIN": "blockchain reference",
            "TRACKED": "tracked files list",
            "#!/usr/bin/env": "shebang/executable",
        }
        
        for marker, label in structural_markers.items():
            count = content.count(marker)
            if count > 0:
                summary["key_changes"].append(f"Contains {count} {label}(s)")
    except:
        pass
    
    return summary


def log_to_blockchain(action, filepath, trigger):
    """Log a code event to the Dewey blockchain."""
    try:
        rel_path = os.path.relpath(filepath, BRAIN_ROOT)
        section = "000-General"
        dewey_class = "000"
        
        result = subprocess.run(
            [sys.executable, BLOCKCHAIN_SCRIPT, "log", action, rel_path,
             "--section", section, "--dewey", dewey_class, "--trigger", trigger],
            capture_output=True, text=True, timeout=10
        )
        # Parse block index from output
        for line in result.stdout.splitlines():
            if "Block #" in line or "index" in line.lower():
                import re
                m = re.search(r'#?(\d+)', line)
                if m:
                    return int(m.group(1))
        return None
    except Exception as e:
        print(f"  ⚠️  Blockchain log failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════════

def cmd_log(filepath, who="system", trigger="manual"):
    """Record a code change in the changelog + blockchain."""
    # Normalize to absolute path
    filepath = os.path.abspath(filepath)
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    changelog = load_changelog()
    current_hash = file_sha256(filepath)
    
    # Find last known hash for this file (match by normalized path)
    last_hash = None
    for entry in reversed(changelog):
        if os.path.abspath(entry["file"]) == filepath:
            last_hash = entry.get("hash_after")
            break
    
    # If hash unchanged, no change to log
    if last_hash and last_hash == current_hash:
        print(f"ℹ️  No changes detected for {os.path.basename(filepath)} (hash unchanged)")
        return
    
    # Compute diff summary
    diff_summary = compute_diff_summary(filepath, last_hash)
    
    # Log to blockchain
    action = "CREATE" if last_hash is None else "MODIFY"
    block_idx = log_to_blockchain(action, filepath, trigger)
    
    # Build changelog entry
    entry = {
        "id": len(changelog) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "who": who,
        "file": filepath,
        "action": action,
        "hash_before": last_hash,
        "hash_after": current_hash,
        "diff_summary": diff_summary,
        "trigger": trigger,
        "blockchain_block": block_idx,
    }
    
    changelog.append(entry)
    save_changelog(changelog)
    
    rel = os.path.relpath(filepath, BRAIN_ROOT)
    print(f"📝 CODE CHANGE LOGGED — Entry #{entry['id']}")
    print(f"   File:    {rel}")
    print(f"   Action:  {action}")
    print(f"   Who:     {who}")
    print(f"   Trigger: {trigger}")
    print(f"   Hash:    {current_hash[:16]}...")
    if block_idx is not None:
        print(f"   Chain:   Block #{block_idx}")
    print(f"   Diff:    +{diff_summary['lines_added']}/-{diff_summary['lines_removed']} lines")
    print(f"   Backup:  Internal Drive ✓")
    
    # ── Auto-log self-modifying system files ──────────────────────
    # The blockchain and changelog change every time we log — record their new state
    _auto_log_system_file(CHANGELOG_PATH, who, trigger)
    _auto_log_system_file(CHAIN_FILE, who, trigger)


def _auto_log_system_file(filepath, who, trigger):
    """Silently log a system file's current state without recursive logging."""
    if not os.path.exists(filepath):
        return
    changelog = load_changelog()
    current_hash = file_sha256(filepath)
    
    # Find last known hash
    last_hash = None
    for entry in reversed(changelog):
        if os.path.abspath(entry["file"]) == os.path.abspath(filepath):
            last_hash = entry.get("hash_after")
            break
    
    if last_hash and last_hash == current_hash:
        return  # No change
    
    action = "CREATE" if last_hash is None else "MODIFY"
    diff_summary = compute_diff_summary(filepath, last_hash)
    
    entry = {
        "id": len(changelog) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "who": who,
        "file": filepath,
        "action": action,
        "hash_before": last_hash,
        "hash_after": current_hash,
        "diff_summary": diff_summary,
        "trigger": f"{trigger} (auto)",
        "blockchain_block": None,  # Don't recurse into blockchain for system files
    }
    
    changelog.append(entry)
    # Save directly without calling save_changelog (which would trigger another auto-log)
    os.makedirs(os.path.dirname(CHANGELOG_PATH), exist_ok=True)
    with open(CHANGELOG_PATH, "w") as f:
        json.dump(changelog, f, indent=2, ensure_ascii=False)
    
    # Backup to Internal Drive
    os.makedirs(INTERNAL_CODE_BACKUP, exist_ok=True)
    with open(f"{INTERNAL_CODE_BACKUP}/dewey_code_changelog.json", "w") as f:
        json.dump(changelog, f, indent=2, ensure_ascii=False)


def cmd_history(limit=20, file_pattern=None):
    """View code change history."""
    changelog = load_changelog()
    
    if file_pattern:
        changelog = [e for e in changelog if file_pattern in os.path.abspath(e["file"])]
    
    if not changelog:
        print("📭 No code changes logged yet.")
        return
    
    recent = changelog[-limit:]
    print(f"📜 CODE CHANGELOG — {len(changelog)} total, showing last {len(recent)}:\n")
    
    for entry in reversed(recent):
        rel = os.path.relpath(entry["file"], BRAIN_ROOT)
        ts = entry["timestamp"][:19].replace("T", " ")
        chain = f" [Block #{entry['blockchain_block']}]" if entry.get("blockchain_block") else ""
        print(f"  #{entry['id']} | {ts} | {entry['action']:6} | {rel}")
        print(f"       by {entry['who']} ({entry['trigger']}){chain}")
        ds = entry.get("diff_summary", {})
        if ds.get("lines_added") or ds.get("lines_removed"):
            print(f"       +{ds['lines_added']}/-{ds['lines_removed']} lines")
        print()


def cmd_diff(entry_id):
    """Show full details for a specific changelog entry."""
    changelog = load_changelog()
    
    entry = None
    for e in changelog:
        if e["id"] == int(entry_id):
            entry = e
            break
    
    if not entry:
        print(f"❌ Entry #{entry_id} not found.")
        return
    
    rel = os.path.relpath(entry["file"], BRAIN_ROOT)
    print(f"🔍 CODE CHANGE #{entry['id']} — FULL DETAILS")
    print(f"   Timestamp:  {entry['timestamp']}")
    print(f"   File:       {rel}")
    print(f"   Action:     {entry['action']}")
    print(f"   Who:        {entry['who']}")
    print(f"   Trigger:    {entry['trigger']}")
    print(f"   Hash Before: {entry.get('hash_before', 'N/A (new file)')}")
    print(f"   Hash After:  {entry['hash_after']}")
    if entry.get("blockchain_block"):
        print(f"   Blockchain:  Block #{entry['blockchain_block']}")
    
    ds = entry.get("diff_summary", {})
    print(f"\n   📊 Diff Summary:")
    print(f"      Lines: +{ds.get('lines_added', 0)} / -{ds.get('lines_removed', 0)}")
    if ds.get("filesize_before"):
        print(f"      Size:  {ds['filesize_before']} → {ds.get('filesize_after', 0)} bytes")
    if ds.get("key_changes"):
        print(f"      Key Changes:")
        for kc in ds["key_changes"]:
            print(f"        • {kc}")


def cmd_verify(filepath=None):
    """Check code integrity — do current hashes match last logged?"""
    changelog = load_changelog()
    
    # System files that self-modify — skip integrity check
    SELF_MODIFYING = {CHANGELOG_PATH, CHAIN_FILE}
    
    if filepath:
        files_to_check = [filepath]
    else:
        files_to_check = [f for f in get_tracked_files() if f not in SELF_MODIFYING]
    
    print(f"🔒 CODE INTEGRITY CHECK — {len(files_to_check)} files:\n")
    
    all_ok = True
    for fp in files_to_check:
        rel = os.path.relpath(fp, BRAIN_ROOT)
        current_hash = file_sha256(fp)
        
        # Find last logged hash
        last_logged = None
        for entry in reversed(changelog):
            if os.path.abspath(entry["file"]) == os.path.abspath(fp):
                last_logged = entry.get("hash_after")
                break
        
        if current_hash is None:
            print(f"  ❌ {rel} — FILE MISSING")
            all_ok = False
        elif last_logged is None:
            print(f"  ⚠️  {rel} — NOT YET LOGGED (hash: {current_hash[:16]}...)")
        elif current_hash == last_logged:
            print(f"  ✅ {rel} — VERIFIED (hash: {current_hash[:16]}...)")
        else:
            print(f"  🔴 {rel} — MODIFIED SINCE LAST LOG!")
            print(f"      Logged: {last_logged[:16]}...")
            print(f"      Current: {current_hash[:16]}...")
            all_ok = False
    
    if all_ok:
        print(f"\n✅ All tracked files verified — no unauthorized changes.")
    else:
        print(f"\n⚠️  Integrity issues found. Run 'log' to record changes or investigate.")


def cmd_status():
    """Summary stats for the code department."""
    changelog = load_changelog()
    tracked = get_tracked_files()
    
    print(f"🏛️  DEWEY CODE DEPARTMENT — Status")
    print(f"   Tracked files:     {len(tracked)}")
    print(f"   Changes logged:    {len(changelog)}")
    
    if changelog:
        last = changelog[-1]
        rel = os.path.relpath(last["file"], BRAIN_ROOT)
        ts = last["timestamp"][:19].replace("T", " ")
        print(f"   Last change:       {ts} — {last['action']} {rel} by {last['who']}")
    
    # Count by action type
    actions = {}
    for e in changelog:
        actions[e["action"]] = actions.get(e["action"], 0) + 1
    if actions:
        print(f"   By action:         {', '.join(f'{k}: {v}' for k,v in sorted(actions.items()))}")
    
    # Count by trigger
    triggers = {}
    for e in changelog:
        triggers[e["trigger"]] = triggers.get(e["trigger"], 0) + 1
    if triggers:
        print(f"   By trigger:        {', '.join(f'{k}: {v}' for k,v in sorted(triggers.items()))}")
    
    # Integrity quick check
    unlogged = 0
    for fp in tracked:
        last_logged = None
        for entry in reversed(changelog):
            if entry["file"] == fp:
                last_logged = entry.get("hash_after")
                break
        if last_logged is None:
            unlogged += 1
    
    if unlogged > 0:
        print(f"   ⚠️  Unlogged files:  {unlogged} — run 'log' to record them")
    else:
        print(f"   Integrity:         ✅ All files logged")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "log":
        if len(sys.argv) < 3:
            print("Usage: dewey_code_tracker.py log <file> [--who NAME] [--trigger TYPE]")
            sys.exit(1)
        filepath = sys.argv[2]
        who = "system"
        trigger = "manual"
        # Parse optional flags
        args = sys.argv[3:]
        for i, arg in enumerate(args):
            if arg == "--who" and i+1 < len(args):
                who = args[i+1]
            elif arg == "--trigger" and i+1 < len(args):
                trigger = args[i+1]
        cmd_log(filepath, who, trigger)
    
    elif cmd == "history":
        limit = 20
        file_pattern = None
        args = sys.argv[2:]
        for i, arg in enumerate(args):
            if arg == "--limit" and i+1 < len(args):
                limit = int(args[i+1])
            elif arg == "--file" and i+1 < len(args):
                file_pattern = args[i+1]
        cmd_history(limit, file_pattern)
    
    elif cmd == "diff":
        if len(sys.argv) < 3:
            print("Usage: dewey_code_tracker.py diff <entry_id>")
            sys.exit(1)
        cmd_diff(sys.argv[2])
    
    elif cmd == "verify":
        filepath = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_verify(filepath)
    
    elif cmd == "status":
        cmd_status()
    
    elif cmd == "track-all":
        # Log all currently untracked files as initial CREATE
        changelog = load_changelog()
        tracked = get_tracked_files()
        logged_count = 0
        for fp in tracked:
            already_logged = any(e["file"] == fp for e in changelog)
            if not already_logged:
                cmd_log(fp, who="system", trigger="initial-setup")
                logged_count += 1
        if logged_count == 0:
            print("✅ All files already tracked.")
        else:
            print(f"✅ {logged_count} files newly logged.")
    
    else:
        print(f"❌ Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)
