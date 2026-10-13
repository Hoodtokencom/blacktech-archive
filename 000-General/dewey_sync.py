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

import json, os, re, sys, subprocess, hashlib
from datetime import datetime

BRAIN = "/home/allenai/blacktech_brain"
# Interpreter that can import googleapiclient — NEVER a bare `python`. With no `python`
# on PATH the Drive calls return nothing, and a silent "nothing to upload" is worse than
# an error (same landmine class as the pull's false-green listing).
GAPI_PY = sys.executable
if subprocess.run([GAPI_PY, "-c", "import googleapiclient"],
                  capture_output=True).returncode != 0:
    _venv = "/home/allenai/.hermes/hermes-agent/venv/bin/python"
    if os.path.exists(_venv) and subprocess.run([_venv, "-c", "import googleapiclient"],
                                                capture_output=True).returncode == 0:
        GAPI_PY = _venv
    else:
        print("❌ No interpreter with googleapiclient available — refusing to run blind.")
        sys.exit(3)
GAPI = f"{GAPI_PY} {BRAIN}/../.hermes/profiles/derrell-black/skills/productivity/google-workspace/scripts/google_api.py"
GITHUB_REPO = "/home/allenai/blacktech_archive"
BLOCKCHAIN = f"python3 {BRAIN}/000-General/dewey_blockchain.py"

# ── Section definitions: SINGLE SOURCE OF TRUTH ─────────────────────
# Do NOT hardcode a section list here. Edit dewey_manifest.json instead —
# every script (sync, pull, router, pipeline) reads it through this module.
sys.path.insert(0, os.path.join(BRAIN, "000-General"))
from dewey_manifest import drive_folders as _drive_folders
from dewey_manifest import sections as _sections

DRIVE_FOLDERS = _drive_folders()   # {folder_name: drive_folder_id}
SECTIONS = _sections()             # {dewey_code: display name}

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
        # Never index/upload bytecode caches — each sync re-uploaded them as NEW
        # Drive files (no overwrite), creating endless duplicate copies.
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            # dewey_blockchain.py writes chain.json atomically (chain.json.tmp then
            # rename); indexing that transient file made every run flag a phantom
            # NEW entry and fail the Drive upload for it. The puller already skips
            # .tmp — this scanner must too.
            if f.startswith('.') or f.endswith('.pyc') or f.endswith('.tmp'):
                continue
            # Never push a puller collision artifact ('<stem>__<section><ext>') up to
            # Drive. The router strips that suffix on the way into Body, so the name is
            # not content — a Drive copy re-downloads forever as a no-op duplicate.
            _stem, _ext = os.path.splitext(f)
            if "__" in _stem and os.path.isdir(os.path.join(BRAIN, _stem.rpartition("__")[2])):
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
            # 'updated' = Drive-side same-name overwrite (google_api.py line ~657),
            # every bit as successful as 'uploaded'. Treating it as failure made
            # healthy re-uploads report 🔴 FAILED.
            ok = status in ('uploaded', 'updated')
            results.append(f"  {'🟢' if ok else '🔴'} {e['file']}: {status}")
        except:
            results.append(f"  🔴 {e['file']}: FAILED")
    
    return results

def sync_to_github(entries):
    """Sync full brain to GitHub Archive — 45-DAY TRASH SAFETY NET.
    GitHub mirrors ALL sections so deleted files can be recovered within 45 days.
    This is the trash staging area — files sit here before permanent deletion."""
    import shutil
    
    # Ensure repo exists
    if not os.path.isdir(f"{GITHUB_REPO}/.git"):
        return ["🔴 GitHub repo not found at /home/allenai/blacktech_archive"]
    
    # ── FULL MIRROR: all sections copied for 45-day recovery window ──
    sections = set(e['section'] for e in entries)
    for section in sections:
        src = os.path.join(BRAIN, section)
        dst = os.path.join(GITHUB_REPO, section)
        if os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns('dewey_catalog_archive_*.json'))
    
    # Copy catalog to root (strip descriptions/hashes to avoid GitHub secret scanning)
    catalog_path = os.path.join(BRAIN, "000-General/dewey_catalog.json")
    with open(catalog_path) as f:
        catalog = json.load(f)
    for entry in catalog:
        entry.pop("description", None)
        entry.pop("hash", None)
    with open(os.path.join(GITHUB_REPO, "dewey_catalog.json"), "w") as f:
        json.dump(catalog, f, indent=2)
    
    # Copy sync script
    shutil.copy2(
        os.path.join(BRAIN, "000-General/dewey_sync.py"),
        os.path.join(GITHUB_REPO, "dewey_sync.py")
    )
    
    # Copy code changelog
    changelog_path = os.path.join(BRAIN, "000-General/dewey_code_changelog.json")
    if os.path.exists(changelog_path):
        shutil.copy2(changelog_path, os.path.join(GITHUB_REPO, "dewey_code_changelog.json"))
    
    # Copy code tracker
    tracker_path = os.path.join(BRAIN, "000-General/dewey_code_tracker.py")
    if os.path.exists(tracker_path):
        shutil.copy2(tracker_path, os.path.join(GITHUB_REPO, "dewey_code_tracker.py"))
    
    # ── PRUNE: drop archive dirs that no longer exist in the brain ──
    # Without this, a renamed/removed section folder lives in the archive
    # forever and keeps resurrecting stale paths in every snapshot.
    # NEVER prune these: archive-only dirs whose content has no brain counterpart.
    # `backups/` holds dated snapshots (dewey_catalog_*.json, dewey_security_*.py,
    # dewey_server_*.py) pushed by the 30-day backup job — the skill is explicit
    # that backup content must SURVIVE syncs. Only ever prune real Dewey section
    # dirs (3-digit prefix), so a renamed/removed section still can't linger.
    PRUNE_PROTECTED = {"backups", "trash", "trash_files", ".git", ".github", "scripts", "tools"}
    pruned = []
    for name in os.listdir(GITHUB_REPO):
        if name in PRUNE_PROTECTED:
            continue
        dst = os.path.join(GITHUB_REPO, name)
        if not os.path.isdir(dst):
            continue
        # Only a Dewey section (NNN-Name) is eligible for pruning.
        if not re.match(r"^\d{3}-", name):
            continue
        if not os.path.isdir(os.path.join(BRAIN, name)):
            shutil.rmtree(dst)
            pruned.append(name)

    # Remove files over 100MB before committing (GitHub limit)
    for section in sections:
        dst = os.path.join(GITHUB_REPO, section)
        if os.path.isdir(dst):
            for root, dirs, fnames in os.walk(dst):
                for f in fnames:
                    fpath = os.path.join(root, f)
                    if os.path.getsize(fpath) > 104857600:
                        os.remove(fpath)
    
    # Git commit and push.
    # Timeouts are generous: a full snapshot is ~3700 files, and a local Pi
    # needs longer than the old 10s/30s budget to stage, commit and upload.
    # The push is retried once — transient DNS/network blips on the Pi are
    # common and a retry turns a red sync into a green one.
    os.chdir(GITHUB_REPO)
    try:
        subprocess.run("git add -A", shell=True, capture_output=True, timeout=180)
    except subprocess.TimeoutExpired:
        return ["🔴 GitHub 'git add' timed out after 180s"]

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = f"🗑️ Dewey Archive: {ts} — {len(entries)} files, {len(sections)} sections (45-day safety net)"
    try:
        subprocess.run(f"git commit -m '{commit_msg}'", shell=True, capture_output=True, timeout=180)
    except subprocess.TimeoutExpired:
        return ["🔴 GitHub 'git commit' timed out after 180s"]

    push = None
    for attempt in (1, 2):
        try:
            push = subprocess.run("git push origin main 2>&1", shell=True,
                                  capture_output=True, text=True, timeout=600)
            if push.returncode == 0:
                note = f"🟢 GitHub Archive: pushed — {len(entries)} files ({len(sections)} sections)"
                if pruned:
                    note += f" | pruned {len(pruned)} stale dir(s): {', '.join(pruned[:4])}"
                if attempt > 1:
                    note += f" (attempt {attempt})"
                return [note]
        except subprocess.TimeoutExpired:
            push = None
            return ["🔴 GitHub push timed out after 600s — run 'git push' manually in "
                    f"{GITHUB_REPO}"]
    # `2>&1` merges stderr into stdout, so report STDOUT (stderr is always empty here).
    err = ((push.stdout or "") + (push.stderr or "")).strip()[:300]
    return [f"🔴 GitHub push failed (rc={push.returncode}): {err}"]

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

def audit_drive():
    """Name-set audit: every cataloged local file must exist in its section's
    Drive folder. The daily change-based upload has a known landmine: if a run
    dies mid-upload, the catalog is already committed, so future runs see 'no
    changes' and NEVER retry the stranded files (silent mirror debt — found
    2026-10-13 with 2,931 files missing). This audit is the retry path.
    Exit 0 = clean; exit 1 = gaps (prints them)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("gapi_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", ".hermes",
        "profiles", "derrell-black", "skills", "productivity",
        "google-workspace", "scripts", "google_api.py"))
    gapi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gapi)
    service = gapi.build_service("drive", "v3")

    def drive_names(folder_id):
        names, token = set(), None
        while True:
            resp = service.files().list(
                q=f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder'",
                pageSize=1000, fields="nextPageToken, files(id, name)",
                pageToken=token).execute()
            names.update(f["name"] for f in resp.get("files", []))
            token = resp.get("nextPageToken")
            if not token:
                return names

    entries = scan_brain()
    # group cataloged files by section, flat-name keyed (Drive mirror is flat)
    by_section = {}
    for e in entries:
        by_section.setdefault(e["section"], {})[e["title"]] = e["file"]

    total_missing = 0
    for section, files in sorted(by_section.items()):
        folder_id = DRIVE_FOLDERS.get(section)
        if not folder_id:
            continue  # sections without Drive folders are out of scope here
        remote = drive_names(folder_id)
        missing = [t for t in files if t not in remote]
        if missing:
            total_missing += len(missing)
            print(f"🔴 {section}: {len(missing)} file(s) missing on Drive:")
            for t in missing[:20]:
                print(f"     - {files[t]}")
            if len(missing) > 20:
                print(f"     ... and {len(missing) - 20} more")
        else:
            print(f"🟢 {section}: {len(files)} file(s) mirrored")
    print(f"\nAUDIT: {'CLEAN' if total_missing == 0 else str(total_missing) + ' MISSING'}")
    return 0 if total_missing == 0 else 1


# ── Main ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
        sys.exit(0)
    if "--audit" in sys.argv:
        print(f"🧠 Dewey Drive Audit — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        sys.exit(audit_drive())
    
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
    # --drive = Drive only; --github = GitHub only; neither = full sync.
    # (The docstring always promised --github but the flag was never parsed,
    # so "dewey_sync.py --drive --github" silently skipped GitHub entirely.)
    do_drive = "--github" not in sys.argv
    do_github = "--drive" not in sys.argv
    if "--drive" in sys.argv or "--github" in sys.argv:
        do_drive = "--drive" in sys.argv
        do_github = "--github" in sys.argv

    if "--catalog" not in sys.argv and do_drive:
        print(f"\n☁️  Google Drive sync:")
        drive_results = sync_to_drive(entries, changes)
        for r in drive_results:
            print(r)
        failed_uploads = [r for r in drive_results if r.startswith("  🔴")]
        if failed_uploads:
            # A red upload must stop the line — a silent failure here is how
            # 2,931 files of mirror debt accumulated unnoticed (2026-10-13).
            print(f"\n❌ {len(failed_uploads)} Drive upload(s) FAILED — mirror is NOT current.")
            sys.exit(2)
    
    # Sync to GitHub
    if "--catalog" not in sys.argv and do_github:
        print(f"\n📦 GitHub sync:")
        gh_results = sync_to_github(entries)
        for r in gh_results:
            print(r)
    
    print(f"\n✅ Sync complete.")
    
    # Log sync completion to blockchain
    subprocess.run(f"{BLOCKCHAIN} log SYNC '{BRAIN}/000-General/dewey_sync.py' --trigger sync", shell=True, capture_output=True, timeout=5)
