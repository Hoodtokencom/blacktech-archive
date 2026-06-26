#!/usr/bin/env python3
"""
Auto-Fill Server — Reads form data templates and fills missing fields from vault/env.
Useful for lead forms, proposals, and contract generation.
Endpoints:
  POST /fill  → JSON body with template + data
  GET /templates → list available templates
Restart: pkill -f auto_fill_server.py && nohup python3 scripts/auto_fill_server.py &
"""
import os, json, datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8096

TEMPLATES = {
    "lead": {
        "name": "",
        "phone": "",
        "email": "",
        "zip": "60628",
        "service": "electrical",
        "company": "Blacktech Solutions Corp",
        "advisor": "Derrell Black",
        "comed_program": "Free Whole-Home Electrification"
    },
    "proposal": {
        "client": "",
        "project": "",
        "estimate": "$0.00",
        "timeline": "2-4 weeks",
        "warranty": "1 year parts & labor",
        "company": "Blacktech Solutions Corp",
        "license": "Chicago Electrical Contractor"
    }
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        data = {"templates": list(TEMPLATES.keys()), "service": "auto_fill", "time": datetime.datetime.now().isoformat()}
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            req = json.loads(body.decode())
            template_name = req.get("template", "lead")
            fields = req.get("data", {})
            base = TEMPLATES.get(template_name, {}).copy()
            base.update(fields)
            base["filled_at"] = datetime.datetime.now().isoformat()
            base["_template"] = template_name
            self.wfile.write(json.dumps(base, indent=2).encode())
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode())

if __name__ == "__main__":
    print(f"📝 Auto-Fill Server on http://0.0.0.0:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
