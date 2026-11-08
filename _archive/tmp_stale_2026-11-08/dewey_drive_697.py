#!/usr/bin/env python3
"""List files in the Drive 697-HVAC and 690-Building_Construction Dewey folders."""
import importlib.util, os

spec = importlib.util.spec_from_file_location("gapi_mod", os.path.join(
    "/home/allenai/.hermes/profiles/derrell-black/skills/productivity/google-workspace/scripts/google_api.py"))
gapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gapi)
service = gapi.build_service("drive", "v3")

def list_folder(folder_id, label):
    names, token = [], None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed=false",
            pageSize=1000, fields="nextPageToken, files(id, name, size, modifiedTime)",
            pageToken=token).execute()
        names += resp.get("files", [])
        token = resp.get("nextPageToken")
        if not token:
            break
    print(f"=== {label} ({folder_id}): {len(names)} files ===")
    for f in sorted(names, key=lambda x: x["name"].lower()):
        print(f"  {f.get('size','?'):>9}B  {f['name']}  (id={f['id']}, mod={f.get('modifiedTime','?')[:10]})")

list_folder("1108yebvK8GxxxoLdnNRG6TXMZHkkmv3u", "697-HVAC")
list_folder("1hmlXFnyZDo26NzcHMve3OYApzo5tXNXV", "690-Building_Construction")