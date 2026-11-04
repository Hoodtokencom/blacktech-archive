#!/usr/bin/env python3
"""Dewey Drive Mirror Backfill — repairs stranded mirror debt.

The daily change-based sync has a documented landmine (dewey_sync.py,
audit_drive docstring): a run that dies mid-upload AFTER the catalog is
committed leaves files that never retry — every future run sees "no
changes". audit_drive() finds those gaps (2026-10-13: 2,931 files;
2026-11-04: 2,910). This script is the repair half of that retry path:
it uploads every cataloged file that is missing from its section's Drive
folder, using the exact same flat-name mirror convention the audit checks.

Idempotent: re-lists Drive at start, so a partial run can simply be
re-run — files that already landed are skipped.

Usage:
  python3 dewey_drive_backfill.py --dry-run   — list what would be uploaded
  python3 dewey_drive_backfill.py             — upload the missing files
Exit codes: 0 = clean/no gaps, 2 = some uploads failed (mirror not current).
"""
import argparse
import concurrent.futures
import importlib.util
import json
import mimetypes
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

BRAIN = "/home/allenai/blacktech_brain"
HERE = os.path.join(BRAIN, "000-General")
sys.path.insert(0, HERE)
from dewey_manifest import drive_folders  # noqa: E402
import dewey_sync  # noqa: E402  (scan_brain; module-level venv check passes here)

DRIVE_FOLDERS = drive_folders()
BLOCKCHAIN = f"python3 {HERE}/dewey_blockchain.py"

# ── Google API module (same import pattern as dewey_sync.audit_drive) ──
spec = importlib.util.spec_from_file_location("gapi_mod", os.path.join(
    HERE, "..", "..", ".hermes", "profiles", "derrell-black", "skills",
    "productivity", "google-workspace", "scripts", "google_api.py"))
assert spec and spec.loader, "google_api.py spec not found"
gapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gapi)

_tls = threading.local()


def get_service():
    """One Drive service per worker thread (httplib2 is not thread-safe)."""
    svc = getattr(_tls, "service", None)
    if svc is None:
        svc = gapi.build_service("drive", "v3")
        _tls.service = svc
    return svc


def drive_names(service, folder_id):
    """All non-folder names directly in a folder — audit_drive's exact query
    (same semantics, so this script fixes exactly what the audit flags)."""
    names, token = set(), None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder'",
            pageSize=1000, fields="nextPageToken, files(id, name)",
            pageToken=token).execute(num_retries=3)
        names.update(f["name"] for f in resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            return names


def upload_one(item):
    """Upload a single Body file into its section's Drive folder (flat name)."""
    section, rel, name, folder_id = item
    fpath = os.path.join(BRAIN, rel)
    try:
        from googleapiclient.http import MediaFileUpload
        size = os.path.getsize(fpath)
        # Small files: single multipart request (1 round trip). Big files:
        # resumable session, same as google_api.py's drive upload.
        resumable = size > 5 * 1024 * 1024
        mime = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
        media = MediaFileUpload(fpath, mimetype=mime, resumable=resumable)
        service = get_service()
        create_kwargs = dict(
            body={"name": name, "parents": [folder_id]},
            media_body=media,
            fields="id, name",
        )
        if resumable:
            # Chunked: next_chunk() lives on the request object, not the media.
            request = service.files().create(**create_kwargs)
            result = None
            while result is None:
                _, result = request.next_chunk(num_retries=3)
        else:
            result = service.files().create(**create_kwargs).execute(num_retries=3)
        return (item, None, result.get("id"))
    except Exception as exc:  # noqa: BLE001 — capture per-file, never kill the batch
        return (item, f"{type(exc).__name__}: {str(exc)[:160]}", None)


def build_worklist(service, verbose=True):
    """Cataloged files missing from their section's Drive folder."""
    entries = dewey_sync.scan_brain()
    by_section = {}
    for e in entries:
        by_section.setdefault(e["section"], {})[e["title"]] = e["file"]

    work, skipped = [], []
    for section, files in sorted(by_section.items()):
        folder_id = DRIVE_FOLDERS.get(section)
        if not folder_id:
            continue  # sections without Drive folders are out of scope (same as audit)
        remote = drive_names(service, folder_id)
        missing = sorted(t for t in files if t not in remote)
        for t in missing:
            work.append((section, files[t], t, folder_id))
        if verbose:
            state = "🔴" if missing else "🟢"
            print(f"  {state} {section}: {len(missing)} missing / {len(files)} cataloged")
        if not missing and section not in by_section:
            skipped.append(section)
    return work


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()

    print(f"🧠 Dewey Drive Backfill — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    service = get_service()

    print("\n📂 Gap scan (audit semantics):")
    work = build_worklist(service)
    total_bytes = sum(os.path.getsize(os.path.join(BRAIN, w[1])) for w in work)
    print(f"\nTotal missing: {len(work)} files, {total_bytes / 1048576:.1f} MB")

    if args.dry_run:
        for section, rel, name, _ in work[:25]:
            print(f"  would upload: {rel}")
        if len(work) > 25:
            print(f"  ... and {len(work) - 25} more")
        print("\n[DRY RUN] nothing uploaded.")
        return 0

    if not work:
        print("\n✅ No gaps — Drive mirror is current.")
        return 0

    print(f"\n☁️  Uploading with {args.workers} workers...")
    t0 = time.time()
    results, failed = [], []
    done_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for res in pool.map(upload_one, work):
            item, err, fid = res
            done_count += 1
            if err:
                failed.append((item, err))
            else:
                results.append(item)
            if done_count % 250 == 0:
                rate = done_count / (time.time() - t0)
                print(f"  {done_count}/{len(work)} ({rate:.0f}/s, "
                      f"{len(failed)} failed)")

    dt = time.time() - t0
    print(f"\nUploaded {len(results)} ok, {len(failed)} failed, in {dt:.0f}s "
          f"({len(results) / max(dt, 1):.1f} files/s)")

    # Retry failures once, sequentially (transient 4xx/5xx with backoff).
    if failed:
        print(f"\n🔁 Retrying {len(failed)} failure(s) once...")
        still_failed = []
        for item, err in failed:
            print(f"  retry {item[1]} (was: {err})")
            _, err2, _ = upload_one(item)
            if err2:
                still_failed.append((item, err2))
            else:
                results.append(item)
        failed = still_failed

    # Per-section summary
    print("\n📊 Per-section result:")
    secs = {}
    for item in results:
        secs.setdefault(item[0], 0)
        secs[item[0]] += 1
    for s, n in sorted(secs.items()):
        print(f"  🟢 {s}: {n} uploaded")
    if failed:
        print(f"  🔴 {len(failed)} still failing:")
        for item, err in failed[:10]:
            print(f"     {item[1]} — {err}")

    # One SYNC block for the repair run (files already carry their own
    # CREATE/MODIFY blocks from when they entered the Body — mirror repair
    # is a sync event, not a body change).
    if results:
        subprocess.run(
            f"{BLOCKCHAIN} log SYNC '{HERE}/dewey_drive_backfill.py' --trigger sync",
            shell=True, capture_output=True, timeout=30)

    if failed:
        print(f"\n❌ {len(failed)} upload(s) FAILED — mirror is NOT current.")
        return 2
    print(f"\n✅ Backfill complete — {len(results)} files repaired to Drive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())