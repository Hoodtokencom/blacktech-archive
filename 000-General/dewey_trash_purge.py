#!/usr/bin/env python3
"""
Dewey 45-Day Trash Purge
========================
GitHub Archive holds a full mirror of the Body. When files are deleted from
the Body, they stay in GitHub for 45 days as a safety net. After 45 days,
this script permanently removes them from GitHub.

Usage:
  python3 dewey_trash_purge.py              — Purge files deleted >45 days ago
  python3 dewey_trash_purge.py --dry-run    — Preview what would be purged
  python3 dewey_trash_purge.py --status     — Show trash age report
"""

import json, os, sys, subprocess, shutil
from datetime import datetime, timedelta

BRAIN = "/home/allenai/blacktech_brain"
GITHUB_REPO = "/home/allenai/blacktech_archive"
TRASH_LOG = f"{BRAIN}/000-General/dewey_trash_log.json"
PURGE_DAYS = 45

def load_trash_log():
    """Load or create the trash log tracking deleted files."""
    if os.path.exists(TRASH_LOG):
        with open(TRASH_LOG) as f:
            return json.load(f)
    return []

def save_trash_log(log):
    with open(TRASH_LOG, 'w') as f:
        json.dump(log, f, indent=2)

def scan_body():
    """Get set of all file paths currently in the Body."""
    files = set()
    for root, dirs, filenames in os.walk(BRAIN):
        for f in filenames:
            if f.startswith('.'):
                continue
            rel = os.path.relpath(os.path.join(root, f), BRAIN)
            files.add(rel)
    return files

def scan_github():
    """Get set of all file paths currently in GitHub Archive."""
    files = set()
    for root, dirs, filenames in os.walk(GITHUB_REPO):
        if '.git' in root.split(os.sep):
            continue
        for f in filenames:
            if f.startswith('.'):
                continue
            rel = os.path.relpath(os.path.join(root, f), GITHUB_REPO)
            files.add(rel)
    return files

def update_trash_log():
    """Compare Body vs GitHub — log newly deleted files with timestamp."""
    body_files = scan_body()
    github_files = scan_github()
    trash_log = load_trash_log()
    
    # Files in GitHub but NOT in Body = deleted from Body
    deleted = github_files - body_files
    
    # Filter out non-brain files (catalog, tools at root level)
    brain_deleted = {f for f in deleted if '/' in f}
    
    # Log new deletions
    existing_paths = {e['file'] for e in trash_log}
    now = datetime.now().isoformat()
    new_entries = 0
    
    for f in brain_deleted:
        if f not in existing_paths:
            trash_log.append({
                "file": f,
                "deleted_at": now,
                "purge_due": (datetime.now() + timedelta(days=PURGE_DAYS)).isoformat(),
                "status": "pending"
            })
            new_entries += 1
    
    # Mark files that reappeared in Body as restored
    for entry in trash_log:
        if entry['file'] in body_files and entry['status'] == 'pending':
            entry['status'] = 'restored'
            entry['restored_at'] = now
    
    save_trash_log(trash_log)
    return trash_log, new_entries

def purge_expired(dry_run=False):
    """Remove files from GitHub that have been deleted >45 days."""
    trash_log, _ = update_trash_log()
    now = datetime.now()
    purged = []
    
    for entry in trash_log:
        if entry['status'] != 'pending':
            continue
        
        purge_due = datetime.fromisoformat(entry['purge_due'])
        if now >= purge_due:
            gh_path = os.path.join(GITHUB_REPO, entry['file'])
            if os.path.exists(gh_path):
                if not dry_run:
                    os.remove(gh_path)
                purged.append(entry['file'])
                entry['status'] = 'purged'
                entry['purged_at'] = now.isoformat()
    
    if not dry_run and purged:
        save_trash_log(trash_log)
        # Commit and push the purge
        os.chdir(GITHUB_REPO)
        subprocess.run("git add -A", shell=True, capture_output=True, timeout=10)
        ts = now.strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            f"git commit -m '🗑️ 45-Day Purge: {ts} — {len(purged)} files permanently removed'",
            shell=True, capture_output=True, timeout=10
        )
        subprocess.run("git push origin main 2>&1", shell=True, capture_output=True, text=True, timeout=30)
    
    return purged

def show_status():
    """Display trash age report."""
    trash_log, _ = update_trash_log()
    now = datetime.now()
    
    pending = [e for e in trash_log if e['status'] == 'pending']
    restored = [e for e in trash_log if e['status'] == 'restored']
    purged = [e for e in trash_log if e['status'] == 'purged']
    
    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║        🗑️  DEWEY TRASH STATUS (45-Day Window)       ║")
    print(f"╠══════════════════════════════════════════════════════╣")
    print(f"║ Pending purge:  {len(pending)} files")
    print(f"║ Restored:       {len(restored)} files")
    print(f"║ Purged:         {len(purged)} files")
    print(f"║ Total tracked:  {len(trash_log)} files")
    print(f"╚══════════════════════════════════════════════════════╝")
    
    if pending:
        print(f"\n📋 Pending purge (in GitHub, deleted from Body):")
        for e in sorted(pending, key=lambda x: x['deleted_at']):
            due = datetime.fromisoformat(e['purge_due'])
            days_left = (due - now).days
            status = "🔴 DUE" if days_left <= 0 else f"🟡 {days_left}d left" if days_left <= 14 else f"🟢 {days_left}d left"
            print(f"  {status} | {e['file']} | deleted {e['deleted_at'][:10]}")
    
    if restored:
        print(f"\n♻️  Restored (was in trash, now back in Body):")
        for e in restored[-5:]:
            print(f"  {e['file']} | restored {e.get('restored_at', '?')[:10]}")

# ── Main ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
    elif "--dry-run" in sys.argv:
        trash_log, new = update_trash_log()
        print(f"📋 Trash log updated: {new} new deletions tracked")
        purged = purge_expired(dry_run=True)
        if purged:
            print(f"\n🔴 Would purge {len(purged)} files:")
            for f in purged:
                print(f"  - {f}")
        else:
            print(f"\n✅ Nothing due for purge. All files within 45-day window.")
    else:
        trash_log, new = update_trash_log()
        print(f"📋 Trash log: {new} new deletions tracked, {len(trash_log)} total")
        purged = purge_expired(dry_run=False)
        if purged:
            print(f"\n🗑️  Purged {len(purged)} files (deleted >{PURGE_DAYS} days ago):")
            for f in purged:
                print(f"  - {f}")
        else:
            print(f"\n✅ No files due for purge. 45-day window active.")
        print(f"\n📊 Summary: {len([e for e in trash_log if e['status']=='pending'])} pending, "
              f"{len([e for e in trash_log if e['status']=='restored'])} restored, "
              f"{len([e for e in trash_log if e['status']=='purged'])} purged")
