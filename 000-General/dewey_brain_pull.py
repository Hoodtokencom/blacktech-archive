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

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
BRAIN_DIR = "/home/allenai/blacktech_brain"
INBOX_DIR = "/home/allenai/blacktech_inbox"
GAPI_SCRIPT = f"{BRAIN_DIR}/../.hermes/profiles/derrell-black/skills/productivity/google-workspace/scripts/google_api.py"


def _pick_gapi_python():
    """Interpreter that can actually import googleapiclient.

    A bare `python` here was a silent-failure landmine: with no `python` on PATH the
    Drive listing returns nothing, every section then looks 'in sync', and the pull
    reports a false green. Probe, and refuse to run blind.
    """
    for cand in (sys.executable, "/home/allenai/.hermes/hermes-agent/venv/bin/python"):
        if cand and os.path.exists(cand):
            probe = subprocess.run([cand, "-c", "import googleapiclient"],
                                   capture_output=True, text=True)
            if probe.returncode == 0:
                return cand
    return None


PYEXE = _pick_gapi_python()
if not PYEXE:
    print("❌ No interpreter with googleapiclient available (tried sys.executable and the "
          "Hermes venv). Refusing to run blind — that would report a false 'in sync'.")
    sys.exit(3)
GAPI = f"{PYEXE} {GAPI_SCRIPT}"
ROUTER = os.path.join(BRAIN_DIR, "000-General", "dewey_inbox_router.py")
BLOCKCHAIN = f"python3 {BRAIN_DIR}/000-General/dewey_blockchain.py"
CHANGE_LOG = os.path.join(BRAIN_DIR, "999-Decisions_Logs", "change_history.md")

# ── Section definitions: SINGLE SOURCE OF TRUTH ─────────────────────
# Do NOT hardcode a section list here. Edit dewey_manifest.json instead.
sys.path.insert(0, os.path.join(BRAIN_DIR, "000-General"))
from dewey_manifest import drive_folders as _drive_folders

DRIVE_FOLDERS = _drive_folders()   # {folder_name: drive_folder_id}


# ── Drive-side collision artifacts ─────────────────────────────────
# download_file namespaces same-named files as '<stem>__<section><ext>' when a name
# collides in the FLAT inbox. Those names are not canonical content: the router strips
# the suffix on the way into Body, so an artifact name can never be a Body filename.
# Left on Drive, it name-diffs against Body's real file and re-downloads on EVERY pull
# as a no-op (Sept 20 leftovers were 'INDEX__<section>.md' — 11 of them, trashed Oct 11).
def is_collision_artifact(name):
    """True for the puller's own '<stem>__<section><ext>' namespace names."""
    stem, _ext = os.path.splitext(name)
    _head, sep, tail = stem.rpartition("__")
    return bool(sep) and tail in DRIVE_FOLDERS


# ── exFAT-unsafe names ─────────────────────────────────────────────
# exFAT (the Body drive's filesystem) cannot store ':' — rsync fails with
# "Invalid argument (22)" on every attempt. Drive happily accepts colons, so a
# colon-named file there diffs against nothing in Body and re-downloads into the
# Brain on every pull, then fails every Brain→Body rsync forever (the Jul 29
# 'Wealth Architecture:' quartet did exactly this for 6+ weeks). Sanitize the
# name at the pull boundary using the established ' — ' convention (the Sep 22
# sanitized copies already on Drive/Body use it).
import re as _re
_INVALID_EXFAT = _re.compile(r'[:*?"<>|]')

def exfat_safe_name(name):
    """Return (safe_name, changed). Colon and friends → ' — ' style names."""
    safe = _INVALID_EXFAT.sub("—", name)
    return safe, safe != name


def run_cmd(cmd, timeout=60):
    """Run a shell command, return (stdout, exit_code)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", 124


def list_drive_files(folder_id):
    """List all files in a Google Drive folder.

    Returns the file list, or None when the listing FAILED. An empty folder and a failed
    listing are not the same thing: treating a failure as 'no files' made every section
    look in-sync and the whole pull report a false green.
    """
    # 'and trashed = false' is REQUIRED: files.list happily returns trashed items when the
    # query omits the flag, so anything ever trashed on Drive stayed permanently "missing"
    # from Body and re-downloaded + re-routed on EVERY pull (the Sept 20 leftovers).
    cmd = f'{GAPI} drive search "\'{folder_id}\' in parents and trashed = false" --raw-query --max 1000'
    stdout, code = run_cmd(cmd, timeout=60)
    if code != 0:
        print(f"  ⚠️  Drive search failed for folder {folder_id}: {stdout[:200] or f'(exit {code})'}")
        return None
    try:
        return json.loads(stdout) if stdout else []
    except json.JSONDecodeError:
        print(f"  ⚠️  Could not parse Drive results: {stdout[:200]}")
        return None


def list_body_files(section_dir):
    """List all filenames in a Body section directory — RECURSIVELY.

    The sync flattens subfolder content to the Drive section ROOT
    (sync_to_drive uploads every file to DRIVE_FOLDERS[section]), so a file
    filed in Body at 690/jobs/<Job>/ sat on Drive at the 690 root and
    name-diffed as 'new' on EVERY pull — a daily re-download loop (the
    2026-10-15 BSC-SOW-2026-SCH001 pair). A file present in a Body SUBFOLDER
    is present in Body; count it so the root diff can't resurrect it.
    """
    section_path = os.path.join(BRAIN_DIR, section_dir)
    if not os.path.isdir(section_path):
        return set()
    files = set()
    for root, dirs, fnames in os.walk(section_path):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in fnames:
            if f.startswith('.') or f.endswith(('.pyc', '.tmp', '.part')):
                continue
            files.add(f)
    return files


def _sha(path):
    """SHA256 of a file, streamed."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(file_id, name, dest_dir, section_dir=None):
    """Download a Drive file to dest_dir. Returns 'written', 'skip' or 'fail'.

    The inbox is FLAT, but every section ships its own INDEX.md — a plain
    os.path.join(dest_dir, name) silently OVERWROTE the earlier ones, losing
    13 of 14 INDEX.md files on the Sept 20 pull. Namespace on collision — but only
    when the bytes actually DIFFER: a byte-identical same-name file is a no-op, not
    a new file. Returns 'skip' so callers never count it as new work.
    """
    dest = os.path.join(dest_dir, name)
    tmp = f"{dest}.part"
    cmd = f'{GAPI} drive download {file_id} --output "{tmp}"'
    stdout, code = run_cmd(cmd, timeout=120)
    if code != 0 or not os.path.exists(tmp):
        print(f"  ⚠️  Download failed for {name}: {stdout[:200]}")
        return "fail"
    if os.path.exists(dest):
        if _sha(tmp) == _sha(dest):
            os.remove(tmp)
            return "skip"
        stem, ext = os.path.splitext(name)
        dest = os.path.join(dest_dir, f"{stem}__{section_dir}{ext}")
    os.replace(tmp, dest)
    return "written"


def log_change(message):
    """Append a human-readable line to the change history.

    NEVER silent. The change log is part of the audit trail, so a dropped entry has to be
    visible — a failed write used to vanish into a bare `except Exception: pass`.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"- [{ts}] Brain Pull: {message}\n"
    try:
        with open(CHANGE_LOG, "a") as f:
            f.write(line)
        return True
    except OSError as exc:
        print(f"  ⚠️  CHANGE LOG WRITE FAILED ({CHANGE_LOG}): {exc}\n"
              f"      entry NOT recorded: {message}", file=sys.stderr)
        return False


def log_blockchain(action, file_path, section_num, trigger="brain-pull"):
    """Log a CREATE block to the blockchain. Reports a failed write instead of dropping it."""
    cmd = f'{BLOCKCHAIN} log {action} "{file_path}" --section "{section_num}" --trigger {trigger}'
    stdout, code = run_cmd(cmd, timeout=15)
    if code != 0:
        print(f"  ⚠️  BLOCKCHAIN LOG FAILED for {file_path}: {stdout[:200] or f'(exit {code})'}",
              file=sys.stderr)
        return False
    return True


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
    skipped_noop = 0
    new_files = []
    unverified = []   # sections whose Drive listing FAILED — never report these in-sync

    for section_dir, folder_id in sections.items():
        section_num = section_dir.split("-")[0]

        # Get Drive files. None means the listing FAILED — a failed listing is NOT an
        # empty folder, and must never be scored as "in sync".
        drive_files = list_drive_files(folder_id)
        if drive_files is None:
            unverified.append(section_dir)
            continue
        # Folders are not downloadable as files — they landed in the inbox as
        # 0-byte placeholders and had to be cleaned out after every pull.
        folders = [f for f in drive_files
                   if f.get("mimeType") == "application/vnd.google-apps.folder"]
        drive_files = [f for f in drive_files
                       if f.get("mimeType") != "application/vnd.google-apps.folder"]
        if folders:
            print(f"  📁 {section_dir} — {len(folders)} subfolder(s) skipped (not downloadable)")
        drive_names = {f["name"] for f in drive_files}

        # Sanitize exFAT-unsafe names BEFORE diffing against Body: a colon name can
        # never exist in Body, so it would diff as 'new' forever. The safe name is
        # what Body actually holds, so that's what must be compared — and it's what
        # the file gets named on the way down.
        renames = {}
        for f in drive_files:
            safe, changed = exfat_safe_name(f["name"])
            if changed:
                renames[f["name"]] = safe
        if renames:
            print(f"  🔧 {section_dir} — {len(renames)} exFAT-unsafe name(s) sanitized:")
            for old, new in sorted(renames.items()):
                print(f"      '{old}' → '{new}'")
                f = next(x for x in drive_files if x["name"] == old)
                f["name"] = renames[old]
        drive_names = {f["name"] for f in drive_files}

        # Get Body files
        body_names = list_body_files(section_dir)

        # Filter out junk: .pyc cache files, __pycache__, .DS_Store, temp files
        SKIP_PATTERNS = ('.pyc', '__pycache__', '.DS_Store', '~$', '.tmp')
        drive_names_clean = {n for n in drive_names if not any(p in n for p in SKIP_PATTERNS)}
        # Drop the puller's own collision artifacts ('<stem>__<section><ext>'). They are
        # duplicates by construction and name-diff forever against Body's real file.
        artifacts = sorted(n for n in drive_names_clean if is_collision_artifact(n))
        if artifacts:
            print(f"  🗑️  {section_dir} — {len(artifacts)} collision artifact(s) ignored "
                  f"(duplicates of the stripped name): {', '.join(artifacts)}")
        drive_names_clean = {n for n in drive_names_clean if not is_collision_artifact(n)}

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
                status = download_file(fid, name, INBOX_DIR, section_dir)
                if status == "written":
                    total_downloaded += 1
                    new_files.append((name, section_dir, section_num))
                    log_change(f"Downloaded {name} from Drive ({section_dir}) → inbox")
                    log_blockchain("CREATE", f"{section_dir}/{name}", section_num)
                    print(f"        ✅ Downloaded → inbox")
                elif status == "skip":
                    skipped_noop += 1
                    print(f"        ⏭️  byte-identical to inbox copy — skipped (no-op)")
                else:
                    print(f"        ❌ Download failed")

            total_new += 1

    print("=" * 60)

    if unverified:
        print(f"\n⚠️  UNVERIFIED — {len(unverified)} of {len(sections)} section(s) could not be "
              f"listed on Drive: {', '.join(unverified)}")
        print("   A failed Drive listing is not an empty folder — refusing to report 'in sync'.")
        sys.exit(2)

    if status_only:
        print(f"\n📊 STATUS: {total_new} file(s) in Brain not yet in Body")
        return

    if dry_run:
        print(f"\n🔍 DRY RUN — {total_new} file(s) would be pulled. No changes made.")
        return

    print(f"\n📊 Pulled {total_downloaded}/{total_new} file(s) to inbox."
          + (f"  ⏭️  {skipped_noop} byte-identical no-op(s) skipped." if skipped_noop else ""))

    if total_downloaded == 0:
        print("✅ Nothing to route. Done.")
        return

    # ── Trigger inbox router ────────────────────────────────────────
    if no_route:
        print("\n⏭️  Skipping router (--no-route). Files are in inbox for manual review.")
        return

    print("\n🔄 Triggering inbox router...")
    router_cmd = f"{PYEXE} {ROUTER}"
    stdout, code = run_cmd(router_cmd, timeout=300)
    print(stdout)

    if code == 0:
        print("\n✅ Brain Pull complete — files routed + 3-way mirror synced.")
    else:
        print(f"\n⚠️  Router exited with code {code}. Files may still be in inbox.")


if __name__ == "__main__":
    main()
