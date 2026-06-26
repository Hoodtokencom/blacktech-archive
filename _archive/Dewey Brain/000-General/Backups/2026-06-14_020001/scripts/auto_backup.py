#!/usr/bin/env python3
"""
Weekly Auto-Backup for Blacktech Pi
Copies scripts + data to Blacktech Drive, keeps last 4 weeks.
"""

import os
import shutil
import datetime
import sys

# ── CONFIG ─────────────────────────────────────────
SOURCE_DIRS = [
    "/home/allenai/scripts",
    "/home/allenai/data",
    "/home/allenai/.env.enc",
    "/home/allenai/.vault_pass",
]
BACKUP_BASE = "/media/allenai/Expansion/Blacktech_Drive/Backups"
KEEP_WEEKS = 4
# ───────────────────────────────────────────────────

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    # Also write to a log file
    log_path = os.path.join(BACKUP_BASE, "backup.log")
    os.makedirs(BACKUP_BASE, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(line + "\n")

def main():
    now = datetime.datetime.now()
    backup_dir = os.path.join(BACKUP_BASE, now.strftime("%Y-%m-%d_%H%M%S"))

    log("═══ Auto-backup started ═══")
    log(f"Destination: {backup_dir}")

    # Check drive is mounted (Expansion is the mount point)
    if not os.path.ismount("/media/allenai/Expansion"):
        log("❌ Expansion drive not mounted — aborting")
        sys.exit(1)

    os.makedirs(backup_dir, exist_ok=True)
    copied = 0

    for src in SOURCE_DIRS:
        if not os.path.exists(src):
            log(f"⚠️  Skip (not found): {src}")
            continue

        dst = os.path.join(backup_dir, os.path.basename(src))
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            log(f"✅ Copied: {src}")
            copied += 1
        except Exception as e:
            log(f"❌ Failed: {src} — {e}")

    # Clean up old backups (keep only last N weeks)
    old_backups = []
    for item in os.listdir(BACKUP_BASE):
        item_path = os.path.join(BACKUP_BASE, item)
        if os.path.isdir(item_path) and item[0:4].isdigit():
            old_backups.append((item, item_path))

    old_backups.sort(key=lambda x: x[0])
    while len(old_backups) > KEEP_WEEKS:
        old_name, old_path = old_backups.pop(0)
        try:
            shutil.rmtree(old_path)
            log(f"🗑️  Deleted old backup: {old_name}")
        except Exception as e:
            log(f"⚠️  Could not delete {old_name}: {e}")

    log(f"═══ Done. Copied {copied} items. ═══")

if __name__ == "__main__":
    main()
