#!/usr/bin/env python3
"""
Blacktech Command Center — Lightweight HTTP server for Pi
Serves dashboard on port 8090
Also provides /health endpoint for internal status checks (bypasses CORS)
"""

import http.server
import socketserver
import os
import urllib.request
import json

PORT = 8090
DIRECTORY = "/home/allenai"

# Ports to health-check server-side (avoids browser CORS issues)
CHECK_PORTS = {
    "5678": "n8n Auto",
    "8080": "Energy Experts Board",
    "8081": "File Manager",
    "8088": "Think Energy Leads",
    "8090": "Command Center",
    "8091": "Money / Budget",
    "8092": "CRM / Lead Portal",
    "80":   "Web Server",
}

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # ── Root → serve index.html with no-cache headers ──
        if self.path == '/' or self.path == '/index.html':
            filepath = os.path.join(DIRECTORY, 'index.html')
            with open(filepath, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('CF-Cache-Status', 'BYPASS')
            self.end_headers()
            self.wfile.write(body)
            return
        # /health?port=XXXX — server-side port check, no CORS
        if self.path.startswith('/health'):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            port = qs.get("port", [""])[0]
            result = {"port": port, "status": "offline", "ms": 0}
            if port:
                import time, socket
                t0 = time.time()
                try:
                    s = socket.create_connection(("127.0.0.1", int(port)), timeout=2)
                    s.close()
                    result["status"] = "online"
                    result["ms"] = round((time.time() - t0) * 1000)
                except Exception:
                    pass
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/restart-bfn':
            import subprocess, json as _json
            try:
                subprocess.Popen(
                    ['bash', '-c',
                     'pkill -f bluewednesday_server.py; sleep 1; cd /home/allenai && python3 bluewednesday_server.py &'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                body = _json.dumps({'ok': True, 'msg': 'BFN server restarting'}).encode()
            except Exception as e:
                body = _json.dumps({'ok': False, 'msg': str(e)}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress request logs

# ── Start server ────────────────────────────────────────────────
if __name__ == "__main__":
    os.chdir(DIRECTORY)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"✅ Blacktech Command Center running on http://0.0.0.0:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n⏹️  Command Center stopped")
