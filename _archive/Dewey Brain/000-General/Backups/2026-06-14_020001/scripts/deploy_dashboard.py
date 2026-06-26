#!/usr/bin/env python3
"""
Blacktech Deploy Dashboard
Shows: CI/CD status, Pipeline results, Service health, AI Toll Meter
Auto-refreshes every 10 seconds.

Access: http://pi.blacktechsolutionscorp.com:8096 or http://10.0.0.100:8096
"""
import os, sys, json, sqlite3, subprocess, time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

DB_PATH = "/home/allenai/data/blacktech.db"
CICD_STATE = "/home/allenai/data/.cicd_state.json"
TOLL_FILE = "/home/allenai/data/ai_toll_meter.txt"
CICD_LOG = "/home/allenai/data/cicd.log"
LISTENER_LOG = "/home/allenai/data/blockchain_listener.log"
PORT = 8096

# ── DATA FETCHERS ────────────────────────────────────
def get_cicd_status():
    try:
        with open(CICD_STATE, "r") as f:
            state = json.load(f)
        last_sha = state.get("last_sha", "N/A")[:7]
        # Get timestamp from log
        ts = "Unknown"
        try:
            with open(CICD_LOG, "r") as f:
                lines = f.readlines()
                for line in reversed(lines[-20:]):
                    if "New commit:" in line:
                        ts = line.split("]")[0].replace("[", "")
                        break
        except:
            pass
        return {"sha": last_sha, "time": ts, "status": "Active"}
    except:
        return {"sha": "N/A", "time": "Never", "status": "Idle"}

def get_pipeline_results(limit=5):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(
            "SELECT task_id, task_type, priority, total_cost, gemini_status, ollama_status, claude_status, substr(final_output,1,80), created_at FROM pipeline_results ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cur.fetchall()
        conn.close()
        results = []
        for r in rows:
            results.append({
                "task_id": r[0], "type": r[1], "priority": r[2],
                "cost": r[3], "gemini": r[4], "ollama": r[5], "claude": r[6],
                "preview": r[7], "time": r[8]
            })
        return results
    except Exception as e:
        return []

def get_services():
    services = [
        ("Kanban Board", "energy_board_server.py", 8080),
        ("BFN Watchdog", "bfn_watchdog.py", 8094),
        ("HOOD API", "hood_api.py", None),
        ("Auto-Fill", "auto_fill_server.py", None),
        ("Pipeline", "triple_play_pipeline.py", None),
        ("Monitor", "pipeline_monitor.py", 8094),
        ("Blockchain", "blockchain_listener.py", None),
        ("Budget", "money_budget_server.py", 8091),
        ("ComEd", "comed_server.py", 8095),
        ("Leads", "lead_intake_bot.py", None),
        ("Command", "command_center_server.py", 8090),
        ("Finance", "finance_server.py", 8093),
        ("BlueWed", "bluewednesday_server.py", 8093),
        ("CI/CD", "cicd_deploy.py", None),
        ("Watchdog", "blacktech_watchdog.py", None),
    ]
    out = []
    for name, script, port in services:
        try:
            result = subprocess.run(["pgrep", "-f", script], capture_output=True, text=True)
            running = result.returncode == 0
            pid = result.stdout.strip().split("\n")[0] if running else ""
            out.append({"name": name, "script": script, "running": running, "pid": pid, "port": port})
        except:
            out.append({"name": name, "script": script, "running": False, "pid": "", "port": port})
    return out

def get_toll_meter():
    try:
        with open(TOLL_FILE, "r") as f:
            lines = f.readlines()
        total = 0.0
        for line in lines:
            if "|" in line and "$" in line:
                try:
                    parts = line.split("|")
                    for p in parts:
                        p = p.strip()
                        if p.startswith("$"):
                            total += float(p.replace("$", "").strip())
                except:
                    pass
        session_total = 0.0
        for line in lines:
            if "Session Total" in line and "$" in line:
                try:
                    session_total = float(line.split("$")[-1].strip().split()[0])
                except:
                    pass
        return {"total": round(total, 6), "session": round(session_total, 6), "lines": len(lines)}
    except:
        return {"total": 0.0, "session": 0.0, "lines": 0}

# ── HTML DASHBOARD ───────────────────────────────────
DASHBOARD_HTML = ""  # Built dynamically by build_html() per request

# ── HTTP HANDLER ─────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            # Fetch fresh data
            cicd = get_cicd_status()
            results = get_pipeline_results(5)
            services = get_services()
            toll = get_toll_meter()
            
            # Build HTML with fresh data
            html = build_html(cicd, results, services, toll)
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(html.encode())
        elif self.path == "/api/status":
            data = {
                "cicd": get_cicd_status(),
                "services_up": sum(1 for s in get_services() if s["running"]),
                "services_total": len(get_services()),
                "pipeline_count": len(get_pipeline_results()),
                "toll_total": get_toll_meter()["total"],
                "time": datetime.now().isoformat()
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Silent

def build_html(cicd, results, services, toll):
    """Build the dashboard HTML with fresh data."""
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="10">
<title>Blacktech Deploy Dashboard</title>
<style>
:root {{ --bg:#0d1117; --card:#161b22; --border:#30363d; --text:#c9d1d9; --green:#3fb950; --red:#f85149; --yellow:#d29922; --blue:#58a6ff; --purple:#a371f7; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; padding:20px; }}
h1 {{ color:var(--blue); font-size:28px; margin-bottom:5px; }}
.sub {{ color:#8b949e; font-size:14px; margin-bottom:20px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:15px; margin-bottom:20px; }}
.card {{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:18px; }}
.card h2 {{ font-size:16px; color:var(--blue); margin-bottom:12px; display:flex; align-items:center; gap:8px; }}
.status-badge {{ display:inline-block; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }}
.status-active {{ background:rgba(63,185,80,0.15); color:var(--green); }}
.status-idle {{ background:rgba(139,148,158,0.15); color:#8b949e; }}
.status-running {{ background:rgba(63,185,80,0.15); color:var(--green); }}
.status-down {{ background:rgba(248,81,73,0.15); color:var(--red); }}
.sha {{ font-family:monospace; background:rgba(88,166,255,0.1); color:var(--blue); padding:2px 8px; border-radius:4px; font-size:13px; }}
.table {{ width:100%; border-collapse:collapse; font-size:13px; }}
.table th {{ text-align:left; padding:8px; color:#8b949e; font-weight:500; border-bottom:1px solid var(--border); }}
.table td {{ padding:8px; border-bottom:1px solid var(--border); }}
.table tr:hover {{ background:rgba(88,166,255,0.05); }}
.preview {{ color:#8b949e; font-style:italic; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.toll-big {{ font-size:32px; font-weight:700; color:var(--yellow); }}
.toll-label {{ font-size:12px; color:#8b949e; }}
.footer {{ text-align:center; color:#484f58; font-size:12px; margin-top:30px; }}
.refresh {{ color:#8b949e; font-size:12px; }}
.pipe-status {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:4px; }}
.pipe-ok {{ background:var(--green); }}
.pipe-fail {{ background:var(--red); }}
.pipe-skip {{ background:#8b949e; }}
</style>
</head>
<body>
<h1>🔥 Blacktech Deploy Dashboard</h1>
<p class="sub">Hybrid Orchestrator — Phase 3 Live | Auto-refresh: 10s | Updated: {datetime.now().strftime("%H:%M:%S")}</p>

<div class="grid">
  <div class="card">
    <h2>🚀 CI/CD Auto-Deploy</h2>
    <p>Status: <span class="status-badge status-{'active' if cicd['status']=='Active' else 'idle'}">{cicd['status']}</span></p>
    <p style="margin-top:8px">Last Commit: <span class="sha">{cicd['sha']}</span></p>
    <p style="margin-top:4px; font-size:12px; color:#8b949e;">Deployed: {cicd['time']}</p>
    <p style="margin-top:8px; font-size:12px;">Checks GitHub every 5 minutes. Auto-restarts 13 services on deploy.</p>
  </div>

  <div class="card">
    <h2>💰 AI Toll Meter</h2>
    <div class="toll-big">${toll['total']}</div>
    <p class="toll-label">Total AI spend across all sessions</p>
    <p style="margin-top:10px; font-size:13px;">Session: <b>${toll['session']}</b> | Entries: {toll['lines']}</p>
  </div>

  <div class="card">
    <h2>⚡ Services ({sum(1 for s in services if s['running'])}/{len(services)})</h2>
    <table class="table">
      <tr><th>Service</th><th>Status</th><th>PID</th></tr>
      {''.join(f'<tr><td>{s["name"]}</td><td><span class="status-badge status-{"running" if s["running"] else "down"}">{"UP" if s["running"] else "DOWN"}</span></td><td style="font-family:monospace; font-size:11px;">{s["pid"] or "-"}</td></tr>' for s in services)}
    </table>
  </div>
</div>

<div class="card" style="margin-bottom:20px;">
  <h2>🤖 Latest Pipeline Results (Blockchain → AI)</h2>
  <table class="table">
    <tr><th>ID</th><th>Type</th><th>Priority</th><th>Gemini</th><th>Ollama</th><th>Claude</th><th>Cost</th><th>Output Preview</th></tr>
    {''.join(f'<tr><td>#{r["task_id"]}</td><td>{r["type"].upper()}</td><td>{r["priority"].upper()}</td><td><span class="pipe-status pipe-{r["gemini"][:3]}"></span>{r["gemini"].upper()}</td><td><span class="pipe-status pipe-{r["ollama"][:3]}"></span>{r["ollama"].upper()}</td><td><span class="pipe-status pipe-{r["claude"][:3]}"></span>{r["claude"].upper()}</td><td>${r["cost"]:.6f}</td><td class="preview">{(r["preview"] or "N/A").replace("<", "&lt;").replace(">", "&gt;")}</td></tr>' for r in results)}
  </table>
  <p style="margin-top:10px; font-size:12px; color:#8b949e;">Results saved to /home/allenai/data/blacktech.db | Auto-refresh every 10s</p>
</div>

<div class="footer">
  <p>Blacktech Solutions Corp | Think Energy | Hybrid Orchestrator v3.0</p>
  <p class="refresh">Dashboard refreshes automatically every 10 seconds</p>
</div>
</body>
</html>'''

# ── MAIN ─────────────────────────────────────────────
if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"🚀 Deploy Dashboard running on http://0.0.0.0:{PORT}")
    print(f"   Local: http://10.0.0.100:{PORT}")
    print(f"   Public: https://pi.blacktechsolutionscorp.com (if mapped)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped.")
        sys.exit(0)
