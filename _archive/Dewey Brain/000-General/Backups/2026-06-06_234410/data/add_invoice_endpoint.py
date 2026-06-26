#!/usr/bin/env python3
"""
add_invoice_endpoint.py
-----------------------
Checks whether POST /api/invoices exists on the Budget Dashboard server
(http://localhost:8091), and if not, patches money_budget_server.py to add it.

Usage:
    python3 /home/allenai/data/add_invoice_endpoint.py
"""

import subprocess
import json
import sys
import os
import re

SERVER_URL = "http://localhost:8091"
ENDPOINT   = "/api/invoices"

# ── 1. Probe the endpoint ──────────────────────────────────────────────────────
print("=" * 60)
print("Checking POST /api/invoices on", SERVER_URL)
print("=" * 60)

result = subprocess.run(
    [
        "curl", "-s", "-X", "POST",
        f"{SERVER_URL}{ENDPOINT}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"test": True}),
        "-w", "\nHTTP_STATUS:%{http_code}",
        "--max-time", "5"
    ],
    capture_output=True,
    text=True
)

output   = result.stdout
stderr   = result.stderr
lines    = output.strip().split("\n")
body     = "\n".join(lines[:-1])
status_line = lines[-1] if lines else "HTTP_STATUS:000"

try:
    http_code = int(status_line.replace("HTTP_STATUS:", ""))
except ValueError:
    http_code = 0

print(f"\nHTTP Status : {http_code}")
print(f"Body        : {body[:300]}")
if stderr:
    print(f"Stderr      : {stderr[:200]}")

# ── 2. Decide what to do ──────────────────────────────────────────────────────
if http_code in (200, 201):
    print("\n✅  POST /api/invoices already exists and is responding OK.")
    print("    No changes needed.")
    sys.exit(0)

elif http_code == 404:
    print("\n⚠️  POST /api/invoices returned 404 — endpoint does NOT exist.")
elif http_code == 0:
    print("\n❌  Could not reach the server at", SERVER_URL)
    print("    Make sure money_budget_server.py is running on port 8091.")
    sys.exit(1)
else:
    print(f"\n⚠️  Unexpected HTTP {http_code} — endpoint may exist but is broken.")

# ── 3. Find money_budget_server.py ───────────────────────────────────────────
SEARCH_DIRS = [
    "/home/allenai",
    "/home/allenai/command_center",
    "/opt/budget",
    "/srv",
]

server_file = None
for d in SEARCH_DIRS:
    candidate = os.path.join(d, "money_budget_server.py")
    if os.path.isfile(candidate):
        server_file = candidate
        break

# Also try a recursive find
if not server_file:
    find = subprocess.run(
        ["find", "/home/allenai", "-name", "money_budget_server.py", "-not",
         "-path", "*/.cache/*"],
        capture_output=True, text=True
    )
    matches = find.stdout.strip().splitlines()
    if matches:
        server_file = matches[0]

if not server_file:
    print("\n❌  Could not locate money_budget_server.py.")
    print("    Please manually add the following route to your Flask/FastAPI server:\n")
    print(PATCH_HINT)
    sys.exit(1)

print(f"\n📄  Found server file: {server_file}")

# ── 4. Check if route already exists in source ────────────────────────────────
with open(server_file, "r") as f:
    source = f.read()

if "/api/invoices" in source:
    print("\n✅  '/api/invoices' is already defined in", server_file)
    print("    The server may just need a restart. Skipping patch.")
    sys.exit(0)

# ── 5. Detect framework (Flask vs FastAPI) ────────────────────────────────────
is_flask   = "from flask"   in source or "import flask"   in source.lower()
is_fastapi = "from fastapi" in source or "import fastapi" in source.lower()

print(f"\n🔍  Framework detected: {'Flask' if is_flask else 'FastAPI' if is_fastapi else 'Unknown'}")

# ── 6. Build the patch snippet ────────────────────────────────────────────────
INVOICES_JSON = "/home/allenai/data/invoices.json"

if is_flask:
    NEW_ROUTE = f'''

# ── Auto-added by add_invoice_endpoint.py ──────────────────────────────────
import pathlib as _pathlib

_INVOICES_FILE = _pathlib.Path("{INVOICES_JSON}")

def _load_invoices():
    if _INVOICES_FILE.exists():
        import json as _json
        return _json.loads(_INVOICES_FILE.read_text())
    return []

def _save_invoices(data):
    import json as _json
    _INVOICES_FILE.write_text(_json.dumps(data, indent=2))

@app.route("/api/invoices", methods=["GET"])
def get_invoices():
    from flask import jsonify
    return jsonify(_load_invoices())

@app.route("/api/invoices", methods=["POST"])
def create_invoice():
    from flask import request, jsonify
    invoice = request.get_json(force=True)
    invoices = _load_invoices()
    invoices.append(invoice)
    _save_invoices(invoices)
    return jsonify({{"ok": True, "id": invoice.get("id"), "total": len(invoices)}}), 201

@app.route("/api/invoices/all", methods=["GET"])
def get_all_invoices():
    from flask import jsonify
    return jsonify(_load_invoices())

@app.route("/api/invoices/all", methods=["POST"])
def replace_all_invoices():
    from flask import request, jsonify
    data = request.get_json(force=True)
    if isinstance(data, list):
        _save_invoices(data)
        return jsonify({{"ok": True, "total": len(data)}}), 200
    return jsonify({{"error": "Expected a JSON array"}}), 400
# ── End auto-added routes ─────────────────────────────────────────────────────
'''
elif is_fastapi:
    NEW_ROUTE = f'''

# ── Auto-added by add_invoice_endpoint.py ──────────────────────────────────
import pathlib as _pathlib
from fastapi import Request as _Request
from fastapi.responses import JSONResponse as _JSONResponse

_INVOICES_FILE = _pathlib.Path("{INVOICES_JSON}")

def _load_invoices():
    if _INVOICES_FILE.exists():
        import json as _json
        return _json.loads(_INVOICES_FILE.read_text())
    return []

def _save_invoices(data):
    import json as _json
    _INVOICES_FILE.write_text(_json.dumps(data, indent=2))

@app.get("/api/invoices")
async def get_invoices():
    return _load_invoices()

@app.post("/api/invoices")
async def create_invoice(req: _Request):
    invoice = await req.json()
    invoices = _load_invoices()
    invoices.append(invoice)
    _save_invoices(invoices)
    return {{"ok": True, "id": invoice.get("id"), "total": len(invoices)}}

@app.get("/api/invoices/all")
async def get_all_invoices():
    return _load_invoices()

@app.post("/api/invoices/all")
async def replace_all_invoices(req: _Request):
    data = await req.json()
    if isinstance(data, list):
        _save_invoices(data)
        return {{"ok": True, "total": len(data)}}
    return _JSONResponse(status_code=400, content={{"error": "Expected a JSON array"}})
# ── End auto-added routes ─────────────────────────────────────────────────────
'''
else:
    print("\n⚠️  Could not detect Flask or FastAPI. Printing generic patch hint:\n")
    print("Add a POST /api/invoices route that:")
    print("  1. Reads JSON body")
    print("  2. Appends to /home/allenai/data/invoices.json")
    print("  3. Returns {ok: true} with HTTP 201")
    sys.exit(0)

# ── 7. Append the new routes to the end of the file ──────────────────────────
backup_path = server_file + ".bak"
with open(server_file, "r") as f:
    original = f.read()

with open(backup_path, "w") as f:
    f.write(original)

with open(server_file, "a") as f:
    f.write(NEW_ROUTE)

print(f"\n✅  Patch applied to: {server_file}")
print(f"📦  Backup saved to:  {backup_path}")
print(f"💾  Invoices will be stored in: {INVOICES_JSON}")
print("\n⚡  NEXT STEP: Restart money_budget_server.py for changes to take effect.")
print("    Example:  sudo systemctl restart money-budget  OR  pkill -f money_budget_server && python3", server_file, "&")
