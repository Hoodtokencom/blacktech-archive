#!/usr/bin/env python3
"""Money / Budget server — port 8091. Serves dashboard + lead data API."""
import http.server, socketserver, os, json, uuid
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = 8091
DIRECTORY = "/home/allenai"
JOBS_FILE     = Path("/home/allenai/data/jobs.json")
INVOICES_FILE = Path("/home/allenai/data/invoices.json")
VENDORS_FILE  = Path("/home/allenai/data/vendors.json")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.path = "/money_budget.html"
            return super().do_GET()

        # /api/jobs — return all jobs as JSON
        if self.path == "/api/jobs":
            jobs = json.loads(JOBS_FILE.read_text()) if JOBS_FILE.exists() else []
            body = json.dumps(jobs).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        # /api/invoices — return all invoices as JSON
        if self.path == "/api/invoices":
            invoices = json.loads(INVOICES_FILE.read_text()) if INVOICES_FILE.exists() else []
            body = json.dumps(invoices).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        # /api/vendors — return all vendor items
        if self.path == "/api/vendors":
            vendors = json.loads(VENDORS_FILE.read_text()) if VENDORS_FILE.exists() else []
            self._json(200, vendors)
            return

        super().do_GET()

    def _json(self, status, data):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        # /api/invoices — append a single invoice (upsert by id)
        if self.path == "/api/invoices":
            try:
                invoice = json.loads(body)
                invoices = json.loads(INVOICES_FILE.read_text()) if INVOICES_FILE.exists() else []
                updated = False
                for i, inv in enumerate(invoices):
                    if inv.get("id") == invoice.get("id"):
                        invoices[i] = invoice
                        updated = True
                        break
                if not updated:
                    invoices.append(invoice)
                INVOICES_FILE.parent.mkdir(parents=True, exist_ok=True)
                INVOICES_FILE.write_text(json.dumps(invoices, indent=2))
                resp = json.dumps({"status": "ok", "id": invoice.get("id"), "total": len(invoices)}).encode()
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                self.send_response(400)
                self.end_headers()
            return

        # /api/invoices/all — save entire invoices array at once
        if self.path == "/api/invoices/all":
            try:
                all_invoices = json.loads(body)
                INVOICES_FILE.parent.mkdir(parents=True, exist_ok=True)
                INVOICES_FILE.write_text(json.dumps(all_invoices, indent=2))
                resp = json.dumps({"status": "ok", "count": len(all_invoices)}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                self.send_response(400)
                self.end_headers()
            return

        # /api/jobs/all — save entire jobs array at once
        if self.path == "/api/jobs/all":
            try:
                all_jobs = json.loads(body)
                JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
                JOBS_FILE.write_text(json.dumps(all_jobs, indent=2))
                resp = json.dumps({"status": "ok", "count": len(all_jobs)}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                self.send_response(400)
                self.end_headers()
            return

        # /api/jobs — save a single job (upsert)
        if self.path == "/api/jobs":
            try:
                job = json.loads(body)
                jobs = json.loads(JOBS_FILE.read_text()) if JOBS_FILE.exists() else []
                updated = False
                for i, j in enumerate(jobs):
                    if j.get("id") == job.get("id"):
                        jobs[i] = job
                        updated = True
                        break
                if not updated:
                    jobs.append(job)
                JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
                JOBS_FILE.write_text(json.dumps(jobs, indent=2))
                resp = json.dumps({"status": "ok", "id": job.get("id")}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                self.send_response(400)
                self.end_headers()
            return

        # /api/vendors — add or update a vendor item (upsert by id)
        if self.path == "/api/vendors":
            try:
                item = json.loads(body)
                if not item.get("id"):
                    item["id"] = str(uuid.uuid4())
                vendors = json.loads(VENDORS_FILE.read_text()) if VENDORS_FILE.exists() else []
                updated = False
                for i, v in enumerate(vendors):
                    if v.get("id") == item.get("id"):
                        vendors[i] = item
                        updated = True
                        break
                if not updated:
                    vendors.append(item)
                VENDORS_FILE.parent.mkdir(parents=True, exist_ok=True)
                VENDORS_FILE.write_text(json.dumps(vendors, indent=2))
                self._json(201, {"status": "ok", "id": item["id"], "total": len(vendors)})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        # /api/vendors/all — replace entire vendor catalog
        if self.path == "/api/vendors/all":
            try:
                all_vendors = json.loads(body)
                VENDORS_FILE.parent.mkdir(parents=True, exist_ok=True)
                VENDORS_FILE.write_text(json.dumps(all_vendors, indent=2))
                self._json(200, {"status": "ok", "count": len(all_vendors)})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        # DELETE /api/vendors/<id>
        if self.path.startswith("/api/vendors/"):
            item_id = self.path.split("/api/vendors/")[1]
            try:
                vendors = json.loads(VENDORS_FILE.read_text()) if VENDORS_FILE.exists() else []
                vendors = [v for v in vendors if v.get("id") != item_id]
                VENDORS_FILE.write_text(json.dumps(vendors, indent=2))
                self._json(200, {"status": "deleted", "id": item_id})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args): pass

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"✅ Money/Budget on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
