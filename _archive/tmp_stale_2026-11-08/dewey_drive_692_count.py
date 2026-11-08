#!/usr/bin/env python3
"""Count files (flat, non-trashed) in the Drive 692-Auxiliary_Practices folder,
including how many SOWs, to size the mirror debt."""
import importlib.util, os

spec = importlib.util.spec_from_file_location("gapi_mod", os.path.join(
    "/home/allenai/.hermes/profiles/derrell-black/skills/productivity/google-workspace/scripts/google_api.py"))
gapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gapi)
service = gapi.build_service("drive", "v3")

folder_id = "17d8iYEnE1xtGQpz2a4eNLUilDSi7WXkd"
files, token = [], None
while True:
    resp = service.files().list(
        q=f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed=false",
        pageSize=1000, fields="nextPageToken, files(id, name, size)",
        pageToken=token).execute()
    files += resp.get("files", [])
    token = resp.get("nextPageToken")
    if not token:
        break

sows = [f for f in files if f["name"].startswith("BSC-SOW")]
print(f"692 folder: {len(files)} files total, {len(sows)} SOW files")
from collections import Counter
print("name-collisions (same name, multiple ids):",
      sum(1 for _, c in Counter(f['name'] for f in files).items() if c > 1))