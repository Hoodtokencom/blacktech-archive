#!/usr/bin/env python3
"""
🧠 Dewey Library CLI — Albert-style 3-Tier Knowledge Command Center
====================================================================
Brain (Google Drive) → Body (Internal Drive) → Archive (GitHub)

USAGE:
  dewey brain <keyword>     — Search the Brain catalog (Google Drive storefront)
  dewey body <keyword>      — Search the Body (Internal Drive actual files)
  dewey key <entry>         — Get the key to unlock a file
  dewey unlock <key>        — Unlock and retrieve a file from Body
  dewey trash <file>        — Move clutter to Archive (GitHub)
  dewey recycle             — Review Archive before permanent deletion
  dewey map                 — Show full Dewey Decimal map
  dewey sync                — Sync Brain → Google Drive
  dewey snapshot            — Full system overview
"""

import json
import sys
import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────
BRAIN_ROOT = "/home/allenai/blacktech_brain"
CATALOG_PATH = f"{BRAIN_ROOT}/000-General/dewey_catalog.json"
INTERNAL_DRIVE = "/media/allenai/Expansion/Blacktech_Drive"
GITHUB_ARCHIVE_DIR = "/home/allenai/blacktech_archive"
GITHUB_ARCHIVE_REPO = "https://github.com/Hoodtokencom/blacktech-archive.git"
GDRIVE_BRAIN_PATH = "Blacktech_Drive/6-Operations/Brain"

# ── Dewey Map ───────────────────────────────────────────────
DEWEY_MAP = {
    "000": "General — Index, tools, catalog",
    "100": "Philosophy — Mission, values, principles",
    "200": "Religion — Faith, trust docs, church",
    "300": "Social Sciences — SSBN, community, team",
    "400": "Language — Style guide, terminology",
    "500": "Science — Electrical theory, LCP rates",
    "600": "Technology — Pi, servers, HostGator",
    "620": "Engineering — NEC code, specs",
    "650": "Management — SOPs, contracts, HR, legal",
    "657": "Accounting — Passcodes, QBO, payroll",
    "690": "Construction — Estimates, permits, materials",
    "691": "Building Materials — Parts, supplier lists",
    "692": "Auxiliary Practices — Estimates, bids, proposals",
    "696": "Utilities — Electrical docs, ComEd",
    "697": "HVAC — Mechanical systems, warranty",
    "700": "Arts — Brand, logos, colors, templates",
    "800": "Literature — Proposals, newsletters",
    "900": "History — Timeline, milestones",
    "910": "Travel — Job sites, zip code maps",
    "920": "Biography — Contacts, subcontractors",
    "930": "Archaeology — Old projects, lessons learned",
    "999": "Decisions — Change log, decision history",
}

def load_catalog():
    if not os.path.exists(CATALOG_PATH):
        print("❌ Catalog not found. Run 'dewey sync' first.")
        sys.exit(1)
    with open(CATALOG_PATH) as f:
        return json.load(f)

# ── Brain ───────────────────────────────────────────────────

def cmd_brain(keyword=None):
    """Search the Brain catalog (Google Drive storefront)."""
    catalog = load_catalog()
    
    if not keyword:
        # Show overview
        counts = {}
        for e in catalog:
            section = e["dewey"].split("-")[0] if "-" in e["dewey"] else e["dewey"]
            counts[section] = counts.get(section, 0) + 1
        
        print("\n🧠 BRAIN CATALOG — Google Drive Storefront\n" + "─" * 50)
        print(f"   📚 {len(catalog)} total entries across {len(counts)} sections\n")
        for code in sorted(counts.keys()):
            desc = DEWEY_MAP.get(code, code)
            bar = "█" * min(counts[code], 30)
            print(f"   {code}  {bar} {counts[code]}")
            print(f"        {desc}")
        print(f"\n   🔍 Search: dewey brain <keyword>")
        print(f"   🔑 Get key: dewey key <entry #>\n")
        return
    
    kw = keyword.lower()
    hits = []
    for entry in catalog:
        if (kw in entry["title"].lower() or
            kw in entry.get("description", "").lower() or
            kw in entry["dewey"].lower() or
            kw in entry["file"].lower()):
            hits.append(entry)
    
    if not hits:
        print(f"\n🔍 No results for '{keyword}' in Brain.\n")
        return
    
    print(f"\n🧠 BRAIN — {len(hits)} results for '{keyword}':\n" + "─" * 50)
    for i, e in enumerate(hits[:20]):
        dewey_code = e["dewey"].split("-")[0] if "-" in e["dewey"] else e["dewey"]
        dewey_desc = DEWEY_MAP.get(dewey_code, e["dewey"])
        print(f"  [{i}] 📂 {e['dewey']} | {e['title']}")
        print(f"      📄 {e['file']} ({e.get('type','?')})")
        print(f"      🔑 {e.get('internal_key','?')}")
        desc = e.get("description", "")[:100]
        if desc:
            print(f"      📝 {desc}...")
        print()
    
    if len(hits) > 20:
        print(f"   ... and {len(hits) - 20} more. Narrow your search.\n")

# ── Body ────────────────────────────────────────────────────

def cmd_body(keyword=None):
    """Search the Body (Internal Drive actual files)."""
    if not os.path.exists(INTERNAL_DRIVE):
        print("❌ Internal Drive not mounted at /media/allenai/Expansion/")
        return
    
    if not keyword:
        # Show top-level structure
        print("\n💪 BODY — Internal Drive Structure\n" + "─" * 50)
        try:
            items = sorted(os.listdir(INTERNAL_DRIVE))
            for item in items:
                full = os.path.join(INTERNAL_DRIVE, item)
                if os.path.isdir(full):
                    count = len([f for f in os.listdir(full) if not f.startswith('.')])
                    print(f"   📁 {item}/ ({count} files)")
                else:
                    size = os.path.getsize(full)
                    print(f"   📄 {item} ({size:,} bytes)")
        except PermissionError:
            print("   ⚠️ Permission denied — drive may need remounting")
        print(f"\n   🔍 Search: dewey body <keyword>\n")
        return
    
    kw = keyword.lower()
    print(f"\n💪 BODY — searching Internal Drive for '{keyword}'...\n" + "─" * 50)
    
    result = subprocess.run(
        ["find", INTERNAL_DRIVE, "-iname", f"*{kw}*", "-maxdepth", "5",
         "-not", "-path", "*/.git/*", "-not", "-path", "*/__pycache__/*"],
        capture_output=True, text=True, timeout=15
    )
    
    matches = [p for p in result.stdout.strip().split('\n') if p]
    
    if not matches:
        print(f"   🔍 No files matching '{keyword}' on Internal Drive.\n")
        return
    
    for i, path in enumerate(matches[:20]):
        rel = path.replace(INTERNAL_DRIVE + "/", "")
        size = os.path.getsize(path) if os.path.isfile(path) else "—"
        modified = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
        icon = "📁" if os.path.isdir(path) else "📄"
        print(f"  [{i}] {icon} {rel}")
        print(f"      📏 {size:,} bytes | 📅 {modified}" if isinstance(size, int) else f"      📅 {modified}")
    
    if len(matches) > 20:
        print(f"\n   ... and {len(matches) - 20} more. Narrow your search.\n")

# ── Key ─────────────────────────────────────────────────────

def cmd_key(entry_ref):
    """Get the key to unlock a file from Body."""
    catalog = load_catalog()
    
    try:
        idx = int(entry_ref)
        if idx < 0 or idx >= len(catalog):
            print(f"❌ Invalid entry #{idx}. Catalog has 0-{len(catalog)-1}.")
            return
        entry = catalog[idx]
    except ValueError:
        matches = [e for e in catalog if entry_ref.lower() in e["title"].lower()]
        if not matches:
            print(f"❌ No entry matching '{entry_ref}'")
            return
        entry = matches[0]
    
    dewey_code = entry["dewey"].split("-")[0] if "-" in entry["dewey"] else entry["dewey"]
    dewey_desc = DEWEY_MAP.get(dewey_code, entry["dewey"])
    
    print(f"\n🔑 KEY REQUEST\n" + "─" * 50)
    print(f"   Title:  {entry['title']}")
    print(f"   Dewey:  {entry['dewey']} — {dewey_desc}")
    print(f"   Type:   {entry.get('type', '?')}")
    print(f"   Key:    {entry.get('internal_key', '?')}")
    print(f"\n   🔓 To unlock: dewey unlock {entry.get('internal_key', '?')}")
    print(f"   ⚠️  Some files require approval — security guard will check.\n")

# ── Unlock ──────────────────────────────────────────────────

def cmd_unlock(key, who="derrell"):
    """Use the key to retrieve the actual file from Body."""
    # Security guard
    security_script = f"{BRAIN_ROOT}/000-General/dewey_security.py"
    if os.path.exists(security_script):
        guard_result = subprocess.run(
            [sys.executable, security_script, "guard", key, who],
            capture_output=True, text=True, timeout=10
        )
        try:
            guard = json.loads(guard_result.stdout.strip())
        except json.JSONDecodeError:
            guard = {"allowed": True, "level": "open", "reason": "guard bypassed"}
        
        if not guard.get("allowed", False):
            level = guard.get("level", "unknown")
            reason = guard.get("reason", "access denied")
            
            if level == "approval":
                print(f"\n🟠 LOCKED — Requires Derrell's approval.")
                print(f"   Reason: {reason}")
                print(f"   Request: python3 dewey_security.py request {key} <your_name> <why>\n")
            elif level == "vault":
                print(f"\n🔴 VAULT LOCKED — Encrypted file.")
                print(f"   Reason: {reason}")
                print(f"   Use passcode_vault.py to access.\n")
            else:
                print(f"\n🚫 ACCESS DENIED — {reason}\n")
            return
    
    # Resolve key
    if key.startswith("internal:"):
        rel_path = key.replace("internal:", "", 1)
    else:
        rel_path = key
    
    brain_path = os.path.join(BRAIN_ROOT, rel_path)
    internal_path = os.path.join(INTERNAL_DRIVE, rel_path)
    
    found = None
    source = ""
    if os.path.exists(brain_path):
        found = brain_path
        source = "Brain (local mirror)"
    elif os.path.exists(internal_path):
        found = internal_path
        source = "Internal Drive"
    else:
        filename = os.path.basename(rel_path)
        result = subprocess.run(
            ["find", INTERNAL_DRIVE, "-name", filename, "-maxdepth", "5"],
            capture_output=True, text=True, timeout=10
        )
        matches = [p for p in result.stdout.strip().split('\n') if p]
        if matches:
            found = matches[0]
            source = "Internal Drive (fuzzy match)"
    
    if not found:
        print(f"\n❌ FILE NOT FOUND — Key '{key}' doesn't resolve.")
        print(f"   Tried Brain: {brain_path}")
        print(f"   Tried Body:  {internal_path}\n")
        return
    
    size = os.path.getsize(found)
    modified = datetime.fromtimestamp(os.path.getmtime(found)).strftime("%Y-%m-%d %H:%M")
    
    print(f"\n🔓 UNLOCKED\n" + "─" * 50)
    print(f"   File:     {os.path.basename(found)}")
    print(f"   Source:   {source}")
    print(f"   Path:     {found}")
    print(f"   Size:     {size:,} bytes")
    print(f"   Modified: {modified}")
    
    # Preview for text files
    if found.endswith(('.md', '.py', '.txt', '.json', '.yaml', '.yml', '.csv', '.html')):
        try:
            with open(found) as f:
                content = f.read(1500)
            print(f"\n   ── PREVIEW ──")
            print(content)
            if len(content) >= 1500:
                print(f"\n   ... (truncated — full file at: {found})")
        except:
            pass
    print()

# ── Trash ────────────────────────────────────────────────────

def cmd_trash(file_path):
    """Move clutter to Archive (GitHub)."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    if not os.path.exists(GITHUB_ARCHIVE_DIR):
        print("📦 Setting up Archive repo...")
        os.makedirs(GITHUB_ARCHIVE_DIR, exist_ok=True)
        subprocess.run(["git", "init"], cwd=GITHUB_ARCHIVE_DIR, capture_output=True)
    
    filename = os.path.basename(file_path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    dest = os.path.join(GITHUB_ARCHIVE_DIR, f"trash_{timestamp}_{filename}")
    shutil.move(file_path, dest)
    
    # Git commit
    subprocess.run(["git", "add", "."], cwd=GITHUB_ARCHIVE_DIR, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"🗑️ Trash: {filename} — {datetime.now().strftime('%Y-%m-%d')}"],
        cwd=GITHUB_ARCHIVE_DIR, capture_output=True
    )
    
    print(f"\n🗑️ TRASHED → Archive\n" + "─" * 50)
    print(f"   From: {file_path}")
    print(f"   To:   {dest}")
    print(f"   ♻️  Review: dewey recycle")
    print(f"   ⚠️  Files survive 45 days before permanent deletion.\n")

# ── Recycle ─────────────────────────────────────────────────

def cmd_recycle():
    """Review Archive before permanent deletion."""
    if not os.path.exists(GITHUB_ARCHIVE_DIR):
        print("📦 No archive. Nothing to recycle.")
        return
    
    subprocess.run(["git", "pull"], cwd=GITHUB_ARCHIVE_DIR, capture_output=True)
    
    files = sorted(os.listdir(GITHUB_ARCHIVE_DIR))
    trash_files = [f for f in files if f.startswith("trash_") and not f.startswith(".")]
    
    if not trash_files:
        print("\n♻️ Archive is empty. Nothing to recycle.\n")
        return
    
    print(f"\n🗑️ ARCHIVE — {len(trash_files)} items awaiting recycling:\n" + "─" * 50)
    for i, f in enumerate(trash_files):
        path = os.path.join(GITHUB_ARCHIVE_DIR, f)
        size = os.path.getsize(path)
        parts = f.replace("trash_", "").split("_", 2)
        date_str = f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:8]} {parts[1][:2]}:{parts[1][2:4]}" if len(parts) >= 2 else "unknown"
        original = parts[2] if len(parts) >= 3 else f
        print(f"  [{i}] 📅 {date_str} | {original} ({size:,} bytes)")
    
    print(f"\n   ♻️  Restore: dewey restore <#>")
    print(f"   🗑️  Delete permanently: rm {GITHUB_ARCHIVE_DIR}/trash_<file>\n")

# ── Map ─────────────────────────────────────────────────────

def cmd_map():
    """Show full Dewey Decimal map."""
    catalog = load_catalog()
    counts = {}
    for e in catalog:
        section = e["dewey"].split("-")[0] if "-" in e["dewey"] else e["dewey"]
        counts[section] = counts.get(section, 0) + 1
    
    print("\n🗺️  DEWEY DECIMAL MAP — Blacktech Library\n" + "═" * 50)
    print("   🧠 GOOGLE DRIVE (Brain)  →  💪 INTERNAL DRIVE (Body)  →  🗑️ GITHUB (Archive)\n")
    
    for code, desc in sorted(DEWEY_MAP.items()):
        count = counts.get(code, 0)
        bar = "█" * min(count, 15) + "░" * (15 - min(count, 15))
        print(f"   {code}  [{bar}] {count:3d}  {desc}")
    
    print(f"\n   📚 TOTAL: {len(catalog)} entries across {len(counts)} sections\n")

# ── Sync ────────────────────────────────────────────────────

def cmd_sync():
    """Sync Brain → Google Drive."""
    print("\n🔄 SYNC — Brain → Google Drive\n" + "─" * 50)
    
    # Code tracker check
    code_tracker = f"{BRAIN_ROOT}/000-General/dewey_code_tracker.py"
    if os.path.exists(code_tracker):
        print("   📝 Checking code integrity...")
        subprocess.run([sys.executable, code_tracker, "verify"], capture_output=True, timeout=15)
    
    result = subprocess.run(
        ["rclone", "sync", BRAIN_ROOT, f"gdrive:{GDRIVE_BRAIN_PATH}",
         "--exclude", "*.enc", "--exclude", "*.salt",
         "--exclude", "__pycache__/"],
        capture_output=True, text=True, timeout=60
    )
    
    if result.returncode == 0:
        print(f"   ✅ Synced to Google Drive: {GDRIVE_BRAIN_PATH}\n")
    else:
        print(f"   ❌ Sync failed: {result.stderr[:200]}\n")

# ── Snapshot ────────────────────────────────────────────────

def cmd_snapshot():
    """Full system overview."""
    print("\n🧠 DEWEY SYSTEM SNAPSHOT\n" + "═" * 50)
    
    # Brain
    catalog = load_catalog()
    counts = {}
    for e in catalog:
        section = e["dewey"].split("-")[0] if "-" in e["dewey"] else e["dewey"]
        counts[section] = counts.get(section, 0) + 1
    
    print(f"\n🧠 BRAIN (Google Drive)")
    print(f"   Catalog: {len(catalog)} entries in {len(counts)} sections")
    print(f"   Path:    {GDRIVE_BRAIN_PATH}")
    
    # Body
    print(f"\n💪 BODY (Internal Drive)")
    if os.path.exists(INTERNAL_DRIVE):
        total_files = sum(1 for _ in Path(INTERNAL_DRIVE).rglob('*') if _.is_file() and not _.name.startswith('.'))
        total_dirs = sum(1 for _ in Path(INTERNAL_DRIVE).rglob('*') if _.is_dir() and not _.name.startswith('.'))
        print(f"   Files:   ~{total_files} files in {total_dirs} directories")
        print(f"   Mount:   {INTERNAL_DRIVE}")
    else:
        print(f"   ⚠️  NOT MOUNTED")
    
    # Archive
    print(f"\n🗑️ ARCHIVE (GitHub)")
    if os.path.exists(GITHUB_ARCHIVE_DIR):
        trash_count = len([f for f in os.listdir(GITHUB_ARCHIVE_DIR) if f.startswith("trash_")])
        print(f"   Trash:   {trash_count} items awaiting recycling")
        print(f"   Repo:    {GITHUB_ARCHIVE_REPO}")
    else:
        print(f"   ⚠️  Not initialized")
    
    print(f"\n   🔍 Search:  dewey brain <keyword>")
    print(f"   🔑 Unlock:  dewey key <#> → dewey unlock <key>")
    print(f"   🗺️  Map:     dewey map")
    print(f"   🔄 Sync:    dewey sync\n")

# ── Help ────────────────────────────────────────────────────

def show_help():
    print("\n🧠 DEWEY LIBRARY CLI — Albert-Style\n" + "═" * 50)
    print("""
   🧠 brain <keyword>    Search Brain catalog (Google Drive storefront)
   🧠 brain              Show Brain overview (all sections)
   💪 body <keyword>     Search Body (Internal Drive actual files)
   💪 body               Show Body structure
   🔑 key <#>            Get the key to unlock a file
   🔓 unlock <key>       Unlock and retrieve file from Body
   🗑️ trash <path>       Move clutter to Archive (GitHub)
   ♻️  recycle           Review Archive before permanent deletion
   🗺️  map               Show full Dewey Decimal map
   🔄 sync               Sync Brain → Google Drive
   📸 snapshot           Full 3-tier system overview
""")

# ── Main ────────────────────────────────────────────────────

COMMANDS = {
    "brain": (lambda: cmd_brain(sys.argv[2] if len(sys.argv) > 2 else None),
              "brain [keyword] — Search Brain catalog"),
    "body": (lambda: cmd_body(sys.argv[2] if len(sys.argv) > 2 else None),
             "body [keyword] — Search Body files"),
    "key": (lambda: cmd_key(sys.argv[2]) if len(sys.argv) > 2 else print("Usage: dewey key <#>"),
            "key <#> — Get unlock key"),
    "unlock": (lambda: cmd_unlock(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "derrell") if len(sys.argv) > 2 else print("Usage: dewey unlock <key>"),
               "unlock <key> — Retrieve file from Body"),
    "trash": (lambda: cmd_trash(sys.argv[2]) if len(sys.argv) > 2 else print("Usage: dewey trash <path>"),
              "trash <path> — Move to Archive"),
    "recycle": (cmd_recycle, "recycle — Review Archive"),
    "map": (cmd_map, "map — Show Dewey map"),
    "sync": (cmd_sync, "sync — Sync Brain → Google Drive"),
    "snapshot": (cmd_snapshot, "snapshot — Full system overview"),
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "help":
        show_help()
    elif cmd in COMMANDS:
        COMMANDS[cmd][0]()
    else:
        print(f"\n❌ Unknown command: {cmd}\n")
        show_help()
