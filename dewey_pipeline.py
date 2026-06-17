#!/usr/bin/env python3
"""
Dewey Pipeline — 3-Part Knowledge System
=========================================
Google Drive (Brain) → Internal Drive (Body) → GitHub (Trash/Archive)

GOOGLE DRIVE = BRAIN (Storefront/Catalog)
  - Stores title, description, metadata, Dewey classification
  - The file is LOCKED — you can see the cover but not the contents
  - Catalog lives at: blacktech_brain/000-General/dewey_catalog.json

INTERNAL DRIVE = BODY (The Actual Files)
  - /media/allenai/Expansion/Blacktech_Drive/
  - Files live here. You need a KEY to unlock them.
  - The key is the internal path, returned by this pipeline.

GITHUB = TRASH/ARCHIVE (Clutter Before Recycling)
  - github.com/Hoodtokencom/blacktech-archive
  - Misc files, old versions, clutter — staged before deletion
  - "Recycling" = review and either restore or permanently delete

USAGE:
  python3 dewey_pipeline.py search <keyword>     — Search Brain catalog (Google Drive storefront)
  python3 dewey_pipeline.py key <entry_id>        — Get the key to unlock a file
  python3 dewey_pipeline.py unlock <key>           — Retrieve the actual file from Internal Drive
  python3 dewey_pipeline.py trash <file_path>      — Move clutter to GitHub archive
  python3 dewey_pipeline.py recycle                — List GitHub archive for review
  python3 dewey_pipeline.py map                    — Show full Dewey map
  python3 dewey_pipeline.py sync                   — Sync Brain catalog to Google Drive
"""

import json
import os
import sys
import subprocess
import shutil
from datetime import datetime

BRAIN_ROOT = "/home/allenai/blacktech_brain"
CATALOG_PATH = f"{BRAIN_ROOT}/000-General/dewey_catalog.json"
INTERNAL_DRIVE = "/media/allenai/Expansion/Blacktech_Drive"
GITHUB_ARCHIVE_REPO = "https://github.com/Hoodtokencom/blacktech-archive.git"
GITHUB_ARCHIVE_DIR = "/home/allenai/blacktech_archive"
GDRIVE_BRAIN_PATH = "Blacktech_Drive/6-Operations/Brain"

# ── Dewey Section Map ─────────────────────────────────────────────
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
    "700": "Arts — Brand, logos, colors, templates",
    "800": "Literature — Proposals, newsletters",
    "900": "History — Timeline, milestones",
    "910": "Travel — Job sites, zip code maps",
    "920": "Biography — Contacts, subcontractors",
    "930": "Archaeology — Old projects, lessons learned",
    "999": "Decisions — Change log, decision history",
    "INTERNAL": "Internal Drive — Files not yet cataloged in Brain",
}


def load_catalog():
    """Load the Dewey catalog from the Brain storefront."""
    if not os.path.exists(CATALOG_PATH):
        print("❌ Catalog not found. Run 'python3 dewey_pipeline.py index' first.")
        sys.exit(1)
    with open(CATALOG_PATH) as f:
        return json.load(f)


def cmd_search(keyword):
    """Search the Brain catalog (Google Drive storefront)."""
    catalog = load_catalog()
    kw = keyword.lower()
    hits = []
    for entry in catalog:
        if (kw in entry["title"].lower() or
            kw in entry["description"].lower() or
            kw in entry["dewey"].lower() or
            kw in entry["file"].lower()):
            hits.append(entry)
    
    if not hits:
        print(f"🔍 No results for '{keyword}' in Brain catalog.")
        return
    
    print(f"🧠 BRAIN CATALOG — {len(hits)} results for '{keyword}':\n")
    for i, e in enumerate(hits):
        dewey_desc = DEWEY_MAP.get(e["dewey"].split("-")[0] if "-" in e["dewey"] else e["dewey"], e["dewey"])
        print(f"  [{i}] 📂 {e['dewey']} | {e['title']}")
        print(f"      📄 {e['file']} ({e['type']})")
        print(f"      🔑 Key: {e['internal_key']}")
        print(f"      📝 {e['description']}")
        print()


def cmd_key(entry_id):
    """Get the key to unlock a file from Internal Drive."""
    catalog = load_catalog()
    try:
        idx = int(entry_id)
        if idx < 0 or idx >= len(catalog):
            print(f"❌ Invalid entry ID: {entry_id}")
            return
        entry = catalog[idx]
    except ValueError:
        # Search by title match
        matches = [e for e in catalog if entry_id.lower() in e["title"].lower()]
        if not matches:
            print(f"❌ No entry matching '{entry_id}'")
            return
        entry = matches[0]
    
    print(f"🔑 KEY FOR: {entry['title']}")
    print(f"   Dewey: {entry['dewey']}")
    print(f"   Key:   {entry['internal_key']}")
    print(f"   Type:  {entry['type']}")
    print(f"\n   To unlock: python3 dewey_pipeline.py unlock {entry['internal_key']}")


def cmd_unlock(key):
    """Use the key to retrieve the actual file from Internal Drive."""
    # Parse the key: "internal:section/filename" or "internal:path/to/file"
    if key.startswith("internal:"):
        rel_path = key.replace("internal:", "", 1)
    else:
        rel_path = key
    
    # Try Brain first, then Internal Drive
    brain_path = os.path.join(BRAIN_ROOT, rel_path)
    internal_path = os.path.join(INTERNAL_DRIVE, rel_path)
    
    found = None
    if os.path.exists(brain_path):
        found = brain_path
        source = "Brain (local)"
    elif os.path.exists(internal_path):
        found = internal_path
        source = "Internal Drive"
    else:
        # Try fuzzy search on internal drive
        filename = os.path.basename(rel_path)
        result = subprocess.run(
            ["find", INTERNAL_DRIVE, "-name", filename, "-maxdepth", "5"],
            capture_output=True, text=True, timeout=10
        )
        matches = [p for p in result.stdout.strip().split('\n') if p]
        if matches:
            found = matches[0]
            source = "Internal Drive (fuzzy)"
    
    if not found:
        print(f"❌ FILE LOCKED — Key '{key}' does not resolve to any file.")
        print(f"   Tried: {brain_path}")
        print(f"   Tried: {internal_path}")
        print(f"   The file may need to be added to the system first.")
        return
    
    # Show file info
    size = os.path.getsize(found)
    modified = datetime.fromtimestamp(os.path.getmtime(found)).strftime("%Y-%m-%d %H:%M")
    
    print(f"🔓 UNLOCKED: {os.path.basename(found)}")
    print(f"   Source: {source}")
    print(f"   Path:   {found}")
    print(f"   Size:   {size:,} bytes")
    print(f"   Modified: {modified}")
    
    # For text files, show preview
    if found.endswith(('.md', '.py', '.txt', '.json', '.yaml', '.yml', '.csv')):
        try:
            with open(found) as f:
                content = f.read(2000)
            print(f"\n   ── PREVIEW (first 2000 chars) ──")
            print(content)
            if len(content) >= 2000:
                print(f"\n   ... (file truncated, full file at: {found})")
        except:
            print(f"   (binary or unreadable)")


def cmd_trash(file_path):
    """Move clutter to GitHub archive (trash before recycling)."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    # Ensure GitHub archive repo exists
    if not os.path.exists(GITHUB_ARCHIVE_DIR):
        print("📦 Cloning GitHub archive repo...")
        result = subprocess.run(
            ["git", "clone", GITHUB_ARCHIVE_REPO, GITHUB_ARCHIVE_DIR],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to clone archive repo: {result.stderr}")
            print("   Creating local archive instead...")
            os.makedirs(GITHUB_ARCHIVE_DIR, exist_ok=True)
            subprocess.run(["git", "init"], cwd=GITHUB_ARCHIVE_DIR, capture_output=True)
    
    # Move file to archive
    filename = os.path.basename(file_path)
    dest = os.path.join(GITHUB_ARCHIVE_DIR, f"trash_{datetime.now().strftime('%Y%m%d_%H%M')}_{filename}")
    shutil.move(file_path, dest)
    
    # Commit to GitHub
    subprocess.run(["git", "add", "."], cwd=GITHUB_ARCHIVE_DIR, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"🗑️ Trash: {filename} — {datetime.now().strftime('%Y-%m-%d')}"],
        cwd=GITHUB_ARCHIVE_DIR, capture_output=True
    )
    result = subprocess.run(["git", "push"], cwd=GITHUB_ARCHIVE_DIR, capture_output=True, text=True)
    
    print(f"🗑️ TRASHED → GitHub Archive")
    print(f"   From: {file_path}")
    print(f"   To:   {dest}")
    print(f"   Status: {'✅ Pushed' if result.returncode == 0 else '⚠️ Local only (push failed)'}")
    print(f"   To recycle: python3 dewey_pipeline.py recycle")


def cmd_recycle():
    """List GitHub archive for review before permanent deletion."""
    if not os.path.exists(GITHUB_ARCHIVE_DIR):
        print("📦 No archive repo cloned. Nothing to recycle.")
        return
    
    # Pull latest
    subprocess.run(["git", "pull"], cwd=GITHUB_ARCHIVE_DIR, capture_output=True)
    
    files = sorted(os.listdir(GITHUB_ARCHIVE_DIR))
    trash_files = [f for f in files if f.startswith("trash_") and not f.startswith(".")]
    
    if not trash_files:
        print("♻️ Archive is empty. Nothing to recycle.")
        return
    
    print(f"🗑️ GITHUB ARCHIVE — {len(trash_files)} items awaiting recycling:\n")
    for i, f in enumerate(trash_files):
        path = os.path.join(GITHUB_ARCHIVE_DIR, f)
        size = os.path.getsize(path)
        # Parse date from filename: trash_YYYYMMDD_HHMM_originalname
        parts = f.replace("trash_", "").split("_", 2)
        date_str = f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:8]} {parts[1][:2]}:{parts[1][2:4]}" if len(parts) >= 2 else "unknown"
        original = parts[2] if len(parts) >= 3 else f
        print(f"  [{i}] 📅 {date_str} | {original} ({size:,} bytes)")
    
    print(f"\n  Actions:")
    print(f"    Restore: python3 dewey_pipeline.py restore <index>")
    print(f"    Delete permanently: rm {GITHUB_ARCHIVE_DIR}/trash_<filename>")


def cmd_map():
    """Show the full Dewey Decimal map."""
    print("🗺️  DEWEY DECIMAL MAP — Blacktech Library Brain\n")
    print("   GOOGLE DRIVE (Brain/Storefront)  →  INTERNAL DRIVE (Body/Files)  →  GITHUB (Trash/Archive)\n")
    for code, desc in sorted(DEWEY_MAP.items()):
        if code == "INTERNAL":
            continue
        print(f"   {code}  {desc}")
    
    # Count entries per section
    catalog = load_catalog()
    counts = {}
    for e in catalog:
        section = e["dewey"].split("-")[0] if "-" in e["dewey"] else e["dewey"]
        counts[section] = counts.get(section, 0) + 1
    
    print(f"\n   📊 CATALOG: {len(catalog)} total entries")
    for code in sorted(counts.keys()):
        if code != "INTERNAL":
            print(f"      {code}: {counts[code]} files")
    if "INTERNAL" in counts:
        print(f"      INTERNAL (uncataloged): {counts['INTERNAL']} files")


def cmd_sync():
    """Sync Brain catalog to Google Drive."""
    print("🔄 Syncing Brain → Google Drive...")
    result = subprocess.run(
        ["rclone", "sync", BRAIN_ROOT, f"gdrive:{GDRIVE_BRAIN_PATH}",
         "--exclude", "*.enc", "--exclude", "*.salt",
         "--exclude", "__pycache__/"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        print(f"✅ Synced to Google Drive: {GDRIVE_BRAIN_PATH}")
    else:
        print(f"❌ Sync failed: {result.stderr}")


def cmd_index():
    """Rebuild the catalog index."""
    print("Rebuilding catalog...")
    # This calls the catalog builder logic
    subprocess.run([sys.executable, f"{BRAIN_ROOT}/000-General/find_brain.py", "map"], 
                   capture_output=True)
    print("✅ Catalog rebuilt. Run 'map' to verify.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Commands: search | key | unlock | trash | recycle | map | sync | index")
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    commands = {
        "search": lambda: cmd_search(arg),
        "key": lambda: cmd_key(arg),
        "unlock": lambda: cmd_unlock(arg),
        "trash": lambda: cmd_trash(arg),
        "recycle": cmd_recycle,
        "map": cmd_map,
        "sync": cmd_sync,
        "index": cmd_index,
    }
    
    if cmd in commands:
        commands[cmd]()
    else:
        print(f"❌ Unknown command: {cmd}")
        print("Commands: search | key | unlock | trash | recycle | map | sync | index")


if __name__ == "__main__":
    main()
