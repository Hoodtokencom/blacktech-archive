#!/usr/bin/env python3
"""
Dewey 3-Way Mirror Sync Pipeline
=================================
Internal Drive (Body) → Google Drive (Brain) → GitHub (Archive)

Usage:
  python3 dewey_sync.py              — Full sync: catalog + Drive + GitHub
  python3 dewey_sync.py --catalog     — Rebuild catalog only
  python3 dewey_sync.py --drive       — Sync to Google Drive only
  python3 dewey_sync.py --github      — Sync to GitHub only
  python3 dewey_sync.py --status      — Show mirror status
"""

import json, os, sys, subprocess, hashlib
from datetime import datetime

BRAIN = "/home/allenai/blacktech_brain"
GAPI = f"python {BRAIN}/../.hermes/profiles/derrell-black/skills/productivity/google-workspace/scripts/google_api.py"
GITHUB_REPO = "/home/allenai/blacktech_archive"
BLOCKCHAIN = f"python3 {BRAIN}/000-General/dewey_blockchain.py"

# ── Google Drive folder IDs ─────────────────────────────────────────
DRIVE_FOLDERS = {
    "000-General": "1iTbhx4Z509FRe0f1IUr98vvsQ-k2LH2Y",
    "100-Philosophy": "10-ISAnwVb-KuOrUz-YJvuvgaMBjfciJ-",
    "200-Religion": "1ZdajMN6QbLSU5s2T0mcepDAXcrGizOCv",
    "300-Social_Sciences": "1jFCRmP-SJFF19_ZTnrB65Z11KAjUby27",
    "400-Language": "1r_JqN2EqZrVB6pyWoYbLtgI16JAXz0W5",
    "500-Science": "1wiI7HMW7YDawBLlMluC-PLjuwjsgr-1d",
    "600-Technology": "1MUeahJmJ2MApRp_3Oqqt28iHaFArlDb7",
    "640-Household_Favorites": "1LPqXyggWUkmvLCUzqqJp_4gDBJbtGbS8",
    "657-Accounting_Finance": "1n0s_WdzrOKQLxcRhxahh5dlMS-ZslyeV",
    "700-Arts_Recreation": "173QcDBFQ0DHqI9uuATUmKr7rDuHC4Rxl",
    "800-Literature": "13KcU3vGRc8LuVMq7x4Q8ZETb2-FJHPSk",
    "900-History_Geography": "17rTzX9WK-7o6uqdMT2OXqcMX5XeS1ZIj",
    "999-Decisions_Logs": "1UXERaufqG88H2Dtq1GjTEfLX7zpfWedx"
}

SECTIONS = {
    "000": "General", "100": "Philosophy", "200": "Religion",
    "300": "Social Sciences", "400": "Language", "500": "Science",
    "600": "Technology", "620": "Engineering", "640": "Household Favorites",
    "650": "Management & Business", "657": "Accounting & Finance",
    "690": "Construction", "700": "Arts", "800": "Literature",
    "900": "History & Geography", "910": "Travel", "920": "Biography",
    "930": "Genealogy", "999": "Decisions & Logs"
}

def file_hash(path):
    """SHA256 of file contents."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def scan_brain():
    """Scan all files in brain, return list of entries."""
    entries = []
    for root, dirs, files in os.walk(BRAIN):
        for f in files:
            if f.startswith('.'):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, BRAIN)
            section_dir = rel.split('/')[0]
            section_num = section_dir.split('-')[0] if '-' in section_dir else section_dir
            
            stat = os.stat(full)
            ext = os.path.splitext(f)[1].lower()
            ftype = {
                '.md': 'text', '.txt': 'text', '.py': 'code', '.sh': 'code',
                '.json': 'data', '.yaml': 'data', '.yml': 'data',
                '.html': 'web', '.css': 'web', '.js': 'web',
                '.enc': 'encrypted', '.salt': 'encrypted', '.pdf': 'pdf'
            }.get(ext, 'file')
            
            try:
                with open(full, 'r') as fh:
                    desc = fh.read(200).replace('\n', ' ').strip()
            except:
                desc = "(binary/encrypted)"
            
            entries.append({
                "title": f,
                "section": section_dir,
                "dewey": section_num,
                "dewey_desc": SECTIONS.get(section_num, "Unknown"),
                "file": rel,
                "type": ftype,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "hash": file_hash(full),
                "description": desc[:150],
                "internal_key": f"internal:{rel}"
            })
    
    entries.sort(key=lambda e: (e['section'], e['title']))
    return entries

def rebuild_catalog():
    """Rebuild dewey_catalog.json from brain scan."""
    entries = scan_brain()
    catalog_path = f"{BRAIN}/000-General/dewey_catalog.json"
    
    # Load old catalog for change detection
    old = {}
    if os.path.exists(catalog_path):
        with open(catalog_path) as f:
            old_entries = json.load(f)
            old = {e['file']: e.get('hash', '') for e in old_entries}
    
    changes = []
    for e in entries:
        old_hash = old.get(e['file'])
        if old_hash is None:
            changes.append(f"  + NEW: {e['file']}")
        elif old_hash != e['hash']:
            changes.append(f"  ~ MOD: {e['file']}")
    
    for path in old:
        if path not in {e['file'] for e in entries}:
            changes.append(f"  - DEL: {path}")
    
    with open(catalog_path, 'w') as f:
        json.dump(entries, f, indent=2)
    
    return entries, changes

def sync_to_drive(entries, changes=None):
    """Upload changed files to Google Drive."""
    if changes is None:
        # Full sync — upload everything
        to_upload = entries
    else:
        # Only upload new/modified
        changed_paths = set()
        for c in changes:
            # Format: "  + NEW: path" or "  ~ MOD: path"
            if c.startswith('  + ') or c.startswith('  ~ '):
                # Strip prefix: "  + NEW: " → 9 chars, "  ~ MOD: " → 9 chars
                path = c.split(': ', 1)[-1].strip() if ': ' in c else c[5:].strip()
                changed_paths.add(path)
        to_upload = [e for e in entries if e['file'] in changed_paths]
    
    results = []
    for e in to_upload:
        section = e['section']
        folder_id = DRIVE_FOLDERS.get(section)
        if not folder_id:
            results.append(f"  ⚠️  {e['file']}: no Drive folder for {section}")
            continue
        
        fpath = os.path.join(BRAIN, e['file'])
        cmd = f"{GAPI} drive upload '{fpath}' --parent {folder_id}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        try:
            data = json.loads(result.stdout)
            status = data.get('status', 'error')
            results.append(f"  {'🟢' if status == 'uploaded' else '🔴'} {e['file']}: {status}")
        except:
            results.append(f"  🔴 {e['file']}: FAILED")
    
    return results

def sync_to_github(entries):
    """Sync brain structure to GitHub repo — NON-DESTRUCTIVE.
    Only updates brain section directories + catalog. Does NOT touch trash_* files."""
    import shutil
    
    # Ensure repo exists
    if not os.path.isdir(f"{GITHUB_REPO}/.git"):
        return ["🔴 GitHub repo not found at /home/allenai/blacktech_archive"]
    
    # ── NON-DESTRUCTIVE: only update brain sections, leave trash alone ──
    sections = set(e['section'] for e in entries)
    for section in sections:
        src = os.path.join(BRAIN, section)
        dst = os.path.join(GITHUB_REPO, section)
        if os.path.isdir(src):
            # Remove old section dir if it exists, then copy fresh
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns('dewey_catalog_archive_*.json'))
    
    # Copy catalog to root (strip descriptions to avoid GitHub secret scanning false positives)
    catalog_path = os.path.join(BRAIN, "000-General/dewey_catalog.json")
    with open(catalog_path) as f:
        catalog = json.load(f)
    for entry in catalog:
        entry.pop("description", None)
        entry.pop("hash", None)  # also strip hashes — they change every sync
    with open(os.path.join(GITHUB_REPO, "dewey_catalog.json"), "w") as f:
        json.dump(catalog, f, indent=2)
    # Copy sync script
    shutil.copy2(
        os.path.join(BRAIN, "000-General/dewey_sync.py"),
        os.path.join(GITHUB_REPO, "dewey_sync.py")
    )
    # ── CODE DEPARTMENT: Copy code changelog to GitHub ──────────────
    changelog_path = os.path.join(BRAIN, "000-General/dewey_code_changelog.json")
    if os.path.exists(changelog_path):
        shutil.copy2(changelog_path, os.path.join(GITHUB_REPO, "dewey_code_changelog.json"))
    # Copy code tracker itself
    tracker_path = os.path.join(BRAIN, "000-General/dewey_code_tracker.py")
    if os.path.exists(tracker_path):
        shutil.copy2(tracker_path, os.path.join(GITHUB_REPO, "dewey_code_tracker.py"))
    
    # Git commit and push
    os.chdir(GITHUB_REPO)
    subprocess.run("git add -A", shell=True, capture_output=True, timeout=10)
    
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = f"🔄 Dewey Sync: {ts} — {len(entries)} files, {len(sections)} sections"
    subprocess.run(f"git commit -m '{commit_msg}'", shell=True, capture_output=True, timeout=10)
    
    push = subprocess.run("git push origin main 2>&1", shell=True, capture_output=True, text=True, timeout=30)
    if push.returncode == 0:
        return [f"🟢 GitHub: pushed — {len(entries)} files"]
    else:
        return [f"🔴 GitHub push failed: {push.stderr[:200]}"]

def show_status():
    """Show mirror status across all three systems."""
    entries = scan_brain()
    
    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║        🧠 DEWEY 3-WAY MIRROR STATUS                 ║")
    print(f"╠══════════════════════════════════════════════════════╣")
    print(f"║ Internal Drive: {len(entries)} files, {len(set(e['section'] for e in entries))} sections")
    
    # Google Drive status
    try:
        result = subprocess.run(
            f"{GAPI} drive search 'parent in '{DRIVE_FOLDERS['000-General']}'' --max 50",
            shell=True, capture_output=True, text=True, timeout=15
        )
        drive_files = len(json.loads(result.stdout)) if result.stdout.strip() else 0
        print(f"║ Google Drive:   {drive_files}+ files (in Dewey Brain/)")
    except:
        print(f"║ Google Drive:   ⚠️  check failed")
    
    # GitHub status
    try:
        os.chdir(GITHUB_REPO)
        result = subprocess.run("git log --oneline -1", shell=True, capture_output=True, text=True, timeout=5)
        last_commit = result.stdout.strip()
        print(f"║ GitHub:         {last_commit[:50]}")
    except:
        print(f"║ GitHub:         ⚠️  check failed")
    
    print(f"╚══════════════════════════════════════════════════════╝")
    
    # Section breakdown
    print(f"\n📂 Section breakdown:")
    for section in sorted(set(e['section'] for e in entries)):
        count = sum(1 for e in entries if e['section'] == section)
        print(f"  {section}: {count} files")

# ── Main ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
        sys.exit(0)
    
    print(f"🧠 Dewey Sync — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Always rebuild catalog first
    entries, changes = rebuild_catalog()
    print(f"📋 Catalog: {len(entries)} entries")
    if changes:
        print(f"   Changes detected:")
        for c in changes:
            print(c)
            # Log each change to the blockchain
            if c.startswith("  + "):
                fpath = os.path.join(BRAIN, c[5:].strip())
                subprocess.run(f"{BLOCKCHAIN} log CREATE '{fpath}' --trigger sync", shell=True, capture_output=True, timeout=5)
            elif c.startswith("  ~ "):
                fpath = os.path.join(BRAIN, c[5:].strip())
                subprocess.run(f"{BLOCKCHAIN} log MODIFY '{fpath}' --trigger sync", shell=True, capture_output=True, timeout=5)
            elif c.startswith("  - "):
                fpath = c[5:].strip()  # deleted file — no full path available
                subprocess.run(f"{BLOCKCHAIN} log DELETE '{fpath}' --trigger sync", shell=True, capture_output=True, timeout=5)
    else:
        print(f"   No changes")
    
    # Sync to Google Drive
    if "--catalog" not in sys.argv:
        print(f"\n☁️  Google Drive sync:")
        drive_results = sync_to_drive(entries, changes if not "--drive" in sys.argv else None)
        for r in drive_results:
            print(r)
    
    # Sync to GitHub
    if "--catalog" not in sys.argv and "--drive" not in sys.argv:
        print(f"\n📦 GitHub sync:")
        gh_results = sync_to_github(entries)
        for r in gh_results:
            print(r)
    
    print(f"\n✅ Sync complete.")
    
    # Log sync completion to blockchain
    subprocess.run(f"{BLOCKCHAIN} log SYNC '{BRAIN}/000-General/dewey_sync.py' --trigger sync", shell=True, capture_output=True, timeout=5)
