#!/usr/bin/env python3
"""
Dewey Brain Pull — Google Drive → Inbox → Router → 3-Way Sync
=============================================================
Scans Google Drive Dewey section folders for files that don't exist
in the Internal Drive (Body), downloads them to the inbox, then
triggers the inbox router for classification + full mirror sync.

Usage:
  python3 dewey_brain_pull.py              — Full pull: scan → download → route → sync
  python3 dewey_brain_pull.py --dry-run    — Preview only, no downloads
  python3 dewey_brain_pull.py --no-route   — Download only, skip router
  python3 dewey_brain_pull.py --status     — Show Brain vs Body comparison
  python3 dewey_brain_pull.py --section 696  — Pull from one section only
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
BRAIN_DIR = "/home/allenai/blacktech_brain"
INBOX_DIR = "/home/allenai/blacktech_inbox"
GAPI = f"python {BRAIN_DIR}/../.hermes/profiles/derrell-black/skills/productivity/google-workspace/scripts/google_api.py"
ROUTER = os.path.join(BRAIN_DIR, "000-General", "dewey_inbox_router.py")
BLOCKCHAIN = f"python3 {BRAIN_DIR}/000-General/dewey_blockchain.py"
CHANGE_LOG = os.path.join(BRAIN_DIR, "999-Decisions_Logs", "change_history.md")

# ── Google Drive folder IDs (mirrors dewey_sync.py DRIVE_FOLDERS) ──
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
    "999-Decisions_Logs": "1UXERaufqG88H2Dtq1GjTEfLX7zpfWedx",
    "691-Building_Materials": "1ANvkl8Ch41m_ZGF-riMYR1T2t4qwe2vN",
    "692-Auxiliary_Practices": "17d8iYEnE1xtGQpz2a4eNLUilDSi7WXkd",
    "696-Utilities": "1iTnImXhY8cvuet3MBEEyBGpiyV6A_1oH",
    "697-HVAC": "1108yebvK8GxxxoLdnNRG6TXMZHkkmv3u",
}


def run_cmd(cmd, timeout=60):
    """Run a shell command, return (stdout, exit_code)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", 124


def list_drive_files(folder_id):
    """List all files in a Google Drive folder. Returns list of {id, name, mimeType, modifiedTime}."""
    cmd = f'{GAPI} drive search "\'{folder_id}\' in parents" --raw-query --max 1000'
    stdout, code = run_cmd(cmd, timeout=30)
    if code != 0:
        print(f"  ⚠️  Drive search failed for folder {folder_id}: {stdout}")
        return []
    try:
        return json.loads(stdout) if stdout else []
    except json.JSONDecodeError:
        print(f"  ⚠️  Could not parse Drive results: {stdout[:200]}")
        return []


def list_body_files(section_dir):
    """List all filenames in a Body section directory."""
    section_path = os.path.join(BRAIN_DIR, section_dir)
    if not os.path.isdir(section_path):
        return set()
    files = set()
    for f in os.listdir(section_path):
        full = os.path.join(section_path, f)
        if os.path.isfile(full) and not f.startswith('.'):
            files.add(f)
    return files


def download_file(file_id, name, dest_dir):
    """Download a Drive file to dest_dir. Returns True on success."""
    dest = os.path.join(dest_dir, name)
    cmd = f'{GAPI} drive download {file_id} --output "{dest}"'
    stdout, code = run_cmd(cmd, timeout=120)
    if code == 0 and os.path.exists(dest):
        return True
    print(f"  ⚠️  Download failed for {name}: {stdout[:200]}")
    return False


def log_change(message):
    """Append a human-readable line to the change history."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"- [{ts}] Brain Pull: {message}\n"
    try:
        with open(CHANGE_LOG, "a") as f:
            f.write(line)
    except Exception:
        pass


def log_blockchain(action, file_path, section_num, trigger="brain-pull"):
    """Log a CREATE block to the blockchain."""
    cmd = f'{BLOCKCHAIN} log {action} "{file_path}" --section "{section_num}" --trigger {trigger}'
    run_cmd(cmd, timeout=15)


def main():
    dry_run = "--dry-run" in sys.argv
    no_route = "--no-route" in sys.argv
    status_only = "--status" in sys.argv
    section_filter = None

    # Parse --section flag
    for i, arg in enumerate(sys.argv):
        if arg == "--section" and i + 1 < len(sys.argv):
            section_filter = sys.argv[i + 1]
            break

    # Ensure inbox exists
    os.makedirs(INBOX_DIR, exist_ok=True)

    # Build section list
    if section_filter:
        # Find matching section folder
        matching = [s for s in DRIVE_FOLDERS if s.startswith(section_filter)]
        if not matching:
            print(f"❌ No section matching '{section_filter}'")
            sys.exit(1)
        sections = {s: DRIVE_FOLDERS[s] for s in matching}
    else:
        sections = DRIVE_FOLDERS

    print(f"\n{'🔍 PREVIEW' if dry_run else '📥 PULLING'} — {len(sections)} section(s)")
    print("=" * 60)

    total_new = 0
    total_downloaded = 0
    new_files = []

    for section_dir, folder_id in sections.items():
        section_num = section_dir.split("-")[0]

        # Get Drive files
        drive_files = list_drive_files(folder_id)
        drive_names = {f["name"] for f in drive_files}

        # Get Body files
        body_names = list_body_files(section_dir)

        # Filter out junk: .pyc cache files, __pycache__, .DS_Store, temp files
        SKIP_PATTERNS = ('.pyc', '__pycache__', '.DS_Store', '~$', '.tmp')
        drive_names_clean = {n for n in drive_names if not any(p in n for p in SKIP_PATTERNS)}

        # Find files in Drive but NOT in Body
        missing = drive_names_clean - body_names

        if not missing:
            if not status_only:
                print(f"  ✅ {section_dir} — in sync ({len(drive_names)} files)")
            continue

        print(f"  📂 {section_dir} — {len(missing)} new file(s) in Brain:")
        for name in sorted(missing):
            drive_file = next((f for f in drive_files if f["name"] == name), None)
            fid = drive_file["id"] if drive_file else "?"
            mime = drive_file.get("mimeType", "?") if drive_file else "?"
            print(f"      • {name}  [{mime}]  (id: {fid})")

            if not dry_run and not status_only:
                if download_file(fid, name, INBOX_DIR):
                    total_downloaded += 1
                    new_files.append((name, section_dir, section_num))
                    log_change(f"Downloaded {name} from Drive ({section_dir}) → inbox")
                    log_blockchain("CREATE", f"{section_dir}/{name}", section_num)
                    print(f"        ✅ Downloaded → inbox")
                else:
                    print(f"        ❌ Download failed")

            total_new += 1

    print("=" * 60)

    if status_only:
        print(f"\n📊 STATUS: {total_new} file(s) in Brain not yet in Body")
        return

    if dry_run:
        print(f"\n🔍 DRY RUN — {total_new} file(s) would be pulled. No changes made.")
        return

    print(f"\n📊 Pulled {total_downloaded}/{total_new} file(s) to inbox.")

    if total_downloaded == 0:
        print("✅ Nothing to route. Done.")
        return

    # ── Trigger inbox router ────────────────────────────────────────
    if no_route:
        print("\n⏭️  Skipping router (--no-route). Files are in inbox for manual review.")
        return

    print("\n🔄 Triggering inbox router...")
    router_cmd = f"python3 {ROUTER}"
    stdout, code = run_cmd(router_cmd, timeout=300)
    print(stdout)

    if code == 0:
        print("\n✅ Brain Pull complete — files routed + 3-way mirror synced.")
    else:
        print(f"\n⚠️  Router exited with code {code}. Files may still be in inbox.")


if __name__ == "__main__":
    main()
