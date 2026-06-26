#!/usr/bin/env python3
"""
HOOD API — Lightweight API for HOOD token / blockchain status.
Endpoints:
  GET /status  → wallet, balance, network
  GET /tx      → recent transactions (last 10 from DB)
  GET /health  → simple OK
Restart: pkill -f hood_api.py && nohup python3 scripts/hood_api.py &
"""
import os, json, sqlite3, datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8095
DB_PATH = "/home/allenai/data/blacktech.db"
WALLET = "0x312fC758b9e6C7F38Ee3E8563B45a9937eaf59B4"

def get_recent_tx(limit=10):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(
            "SELECT task_id, task_type, total_cost, created_at FROM pipeline_results ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cur.fetchall()
        conn.close()
        return [{"task_id": r[0], "type": r[1], "cost": r[2], "time": r[3]} for r in rows]
    except Exception as e:
        return [{"error": str(e)}]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silent

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if self.path == "/health":
            data = {"status": "ok", "service": "hood_api", "time": datetime.datetime.now().isoformat()}
        elif self.path == "/status":
            data = {
                "wallet": WALLET,
                "network": "sepolia",
                "balance_eth": 0.0993,
                "token": "HOOD1",
                "status": "testnet_active"
            }
        elif self.path == "/tx":
            data = {"transactions": get_recent_tx()}
        else:
            data = {"endpoints": ["/health", "/status", "/tx"]}

        self.wfile.write(json.dumps(data, indent=2).encode())

if __name__ == "__main__":
    print(f"🚀 HOOD API on http://0.0.0.0:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
