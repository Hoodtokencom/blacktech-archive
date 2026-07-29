#!/usr/bin/env python3
"""
Blacktech Finance Dashboard — Server on port 8093
Serves finance.html + Pi-side data API so all devices sync
"""
import http.server
import socketserver
import os
import json
import re

PORT      = 8093
DIRECTORY = "/home/allenai"
DATA_FILE = "/home/allenai/data/finance_data.json"

# ── Ensure data file exists ──────────────────────────────
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({
            "biz": [], "per": [],
            "bizBudget": 0, "perBudget": 0,
            "bizCatBudget": {}, "perCatBudget": {}
        }, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # ── API: load all finance data ──
        if self.path == '/api/finance':
            self._json(load_data())
            return

        # ── Root → finance.html ──
        if self.path == '/' or self.path == '':
            self.path = '/finance.html'

        super().do_GET()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except Exception:
            self._json({"error": "invalid json"}, 400)
            return

        # ── API: save all finance data ──
        if self.path == '/api/finance':
            save_data(payload)
            self._json({"ok": True})
            return

        self._json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        pass  # suppress logs

if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Finance server running on port {PORT}")
        httpd.serve_forever()
