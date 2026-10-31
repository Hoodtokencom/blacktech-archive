#!/usr/bin/env python3
"""
Dewey Security Dashboard — Visual Guard Station
================================================
Shows pending access requests, audit log, and permission map.
Derrell can approve/deny with one click.

Port: 8096
URL: https://dewey.blacktechsolutionscorp.com (via Cloudflare tunnel)
"""

import json
import os
import sys
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import urllib.request

SSO_COOKIE_NAME = "bt_sso_token"
SSO_VERIFY_URL = "http://127.0.0.1:8090/api/auth/verify"
SSO_LOGIN_URL = "https://bill.blacktechsolutionscorp.com/login"

def sso_get_user(headers):
    """Check bt_sso_token cookie against CC. Return user dict or None."""
    cookie = headers.get("Cookie", "")
    token = None
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith(f"{SSO_COOKIE_NAME}="):
            token = part[len(SSO_COOKIE_NAME)+1:]
            break
    if not token:
        auth = headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        return None
    try:
        req = urllib.request.Request(SSO_VERIFY_URL, headers={"Cookie": f"{SSO_COOKIE_NAME}={token}"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        if data.get("ok") and data.get("user"):
            return data["user"]
    except Exception:
        pass
    return None

PORT = 8096
BRAIN_ROOT = "/home/allenai/blacktech_brain"
SECURITY_SCRIPT = f"{BRAIN_ROOT}/000-General/dewey_security.py"
REQUESTS_PATH = f"{BRAIN_ROOT}/000-General/access_requests.json"
AUDIT_PATH = f"{BRAIN_ROOT}/000-General/audit_log.json"
PERMISSIONS_PATH = f"{BRAIN_ROOT}/000-General/permissions.json"

# ── Brand ──────────────────────────────────────────────────────────
NAVY = "#002244"
GREEN = "#69BE28"
BG = "#0a0e14"
CARD_BG = "#111820"
TEXT = "#e0e0e0"
MUTED = "#8899aa"

def load_json(path, default=None):
    if default is None:
        default = []
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)

def run_security(*args):
    """Run dewey_security.py and return stdout."""
    result = subprocess.run(
        [sys.executable, SECURITY_SCRIPT] + list(args),
        capture_output=True, text=True, timeout=10
    )
    return result.stdout

def get_pending():
    return [r for r in load_json(REQUESTS_PATH, []) if r["status"] == "pending"]

def get_audit(limit=50):
    log = load_json(AUDIT_PATH, [])
    return log[-limit:]

def get_permissions():
    return load_json(PERMISSIONS_PATH, {})

def get_catalog_stats():
    catalog = load_json(f"{BRAIN_ROOT}/000-General/dewey_catalog.json", [])
    sections = {}
    for e in catalog:
        dewey_val = str(e.get("dewey", ""))
        sec = dewey_val.split("-")[0] if "-" in dewey_val else (dewey_val if dewey_val else "???")
        sections[sec] = sections.get(sec, 0) + 1
    return {"total": len(catalog), "sections": sections}

def get_blockchain_stats():
    chain = load_json(f"{BRAIN_ROOT}/000-General/dewey_blockchain.json", [])
    if chain:
        last_block = chain[-1]
        last_action = last_block.get("action", last_block.get("type", "?"))
        return {"blocks": len(chain), "last": last_action}
    return {"blocks": 0, "last": "GENESIS"}

def get_contract_stats():
    contracts = load_json(f"{BRAIN_ROOT}/690-Building_Construction/contracts.json", {})
    stages = {}
    for cid, c in contracts.items():
        stage = c.get("stage", "unknown")
        stages[stage] = stages.get(stage, 0) + 1
    return {"total": len(contracts), "stages": stages}

def get_sync_status():
    """Check if Brain was synced recently."""
    catalog = load_json(f"{BRAIN_ROOT}/000-General/dewey_catalog.json", [])
    if catalog:
        last_mod = max(e.get("modified", "") for e in catalog)
        return last_mod[:16].replace("T", " ")
    return "never"

def get_ssbn_stats():
    """Get SSBN HOOD token stats for the Bridge tab."""
    import sqlite3
    SSBN_DB = "/home/allenai/data/ssbn.db"
    try:
        con = sqlite3.connect(SSBN_DB)
        member_count = con.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        token_entries = con.execute("SELECT COUNT(*) FROM hood_tokens").fetchone()[0]
        total_hood = con.execute("SELECT SUM(tokens) FROM hood_tokens").fetchone()[0] or 0
        # Top 10 leaderboard
        rows = con.execute(
            "SELECT member_name, SUM(tokens) as total FROM hood_tokens GROUP BY member_name ORDER BY total DESC LIMIT 10"
        ).fetchall()
        con.close()

        # Map tokens to Dewey tiers
        TIERS = [
            (0, "public", "🟢"),
            (10, "key", "🔵"),
            (50, "approval", "🟠"),
            (100, "vault", "🔴"),
            (250, "master", "👑"),
        ]
        leaderboard = []
        for name, tokens in rows:
            tier_name = "public"
            tier_emoji = "🟢"
            for t, tn, te in TIERS:
                if tokens >= t:
                    tier_name = tn
                    tier_emoji = te
            leaderboard.append({"name": name, "tokens": tokens, "tier": tier_name, "emoji": tier_emoji})

        return {
            "members": member_count,
            "token_entries": token_entries,
            "total_hood": total_hood,
            "leaderboard": leaderboard,
            "ok": True
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── HTML ───────────────────────────────────────────────────────────

def render_page(message=None):
    pending = get_pending()
    audit = get_audit(30)
    perms = get_permissions()
    catalog = get_catalog_stats()
    blockchain = get_blockchain_stats()
    contracts = get_contract_stats()
    sync_time = get_sync_status()
    ssbn = get_ssbn_stats()
    
    # Build pending cards
    pending_html = ""
    if pending:
        for r in pending:
            ts = r["timestamp"][:19].replace("T", " ")
            pending_html += f"""
            <div class="request-card">
                <div class="req-header">
                    <span class="req-id">#{r['id']}</span>
                    <span class="req-time">{ts}</span>
                </div>
                <div class="req-body">
                    <div class="req-file">📂 {r['key']}</div>
                    <div class="req-who">👤 {r['who']}</div>
                    <div class="req-why">💬 {r['why']}</div>
                </div>
                <div class="req-actions">
                    <button class="btn-approve" onclick="approve('{r['id']}')">🟢 APPROVE</button>
                    <button class="btn-deny" onclick="deny('{r['id']}')">🔴 DENY</button>
                </div>
            </div>"""
    else:
        pending_html = '<div class="empty-state">✅ No pending requests</div>'
    
    # Build audit table
    audit_html = ""
    emoji = {"request": "🟠", "approve": "🟢", "deny": "🔴", "unlock": "🔓", "blocked": "🚫", "check": "🔍", "classify": "🔒"}
    for e in reversed(audit):
        ts = e["timestamp"][:19].replace("T", " ")
        audit_html += f"""
            <tr>
                <td>{emoji.get(e['action'], '•')}</td>
                <td>{ts}</td>
                <td>{e['action']}</td>
                <td>{e['who']}</td>
                <td class="{'granted' if e['result'] == 'granted' else 'denied' if e['result'] == 'denied' else ''}">{e['result']}</td>
                <td class="key-cell">{e['key']}</td>
            </tr>"""
    
    # Build permission summary
    section_levels = {
        "000": "public", "100": "public", "200": "vault", "300": "key",
        "400": "public", "500": "key", "600": "key", "620": "key",
        "650": "approval", "657": "vault", "690": "approval", "700": "public",
        "800": "key", "900": "public", "910": "key", "920": "key",
        "930": "key", "999": "public"
    }
    level_emoji = {"public": "🟢", "key": "🔵", "approval": "🟠", "vault": "🔴"}
    
    perm_html = ""
    for section, level in sorted(section_levels.items()):
        overrides = [k for k, v in perms.items() if section in k]
        note = f" ({len(overrides)} overrides)" if overrides else ""
        perm_html += f"""
            <div class="perm-row">
                <span class="perm-section">{section}</span>
                <span class="perm-level">{level_emoji[level]} {level.upper()}{note}</span>
            </div>"""
    
    # Build SSBN Bridge content
    ssbn_html = ""
    if ssbn.get("ok"):
        # Tier threshold reference
        tier_ref = ""
        for t, tn, te in [(0, "public", "🟢"), (10, "key", "🔵"), (50, "approval", "🟠"), (100, "vault", "🔴"), (250, "master", "👑")]:
            tier_ref += f'<div class="perm-row"><span class="perm-section">{t}+ HOOD</span><span class="perm-level">{te} {tn.upper()}</span></div>'
        
        # Leaderboard
        lb_rows = ""
        for i, entry in enumerate(ssbn["leaderboard"], 1):
            lb_rows += f"""
                <tr>
                    <td>{i}</td>
                    <td>{entry['name'][:24]}</td>
                    <td style="color:{GREEN};font-weight:600;">{entry['tokens']}</td>
                    <td>{entry['emoji']} {entry['tier'].upper()}</td>
                </tr>"""
        
        ssbn_html = f"""
        <div class="stats">
            <div class="stat-card">
                <div class="stat-num">{ssbn['members']}</div>
                <div class="stat-label">SSBN Members</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">{ssbn['total_hood']}</div>
                <div class="stat-label">Total HOOD Circulating</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">{ssbn['token_entries']}</div>
                <div class="stat-label">Token Transactions</div>
            </div>
        </div>
        
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
            <div>
                <h4 style="color:{GREEN};margin-bottom:8px;">🏆 HOOD Leaderboard</h4>
                <table class="audit-table">
                    <thead><tr><th>#</th><th>Member</th><th>HOOD</th><th>Dewey Tier</th></tr></thead>
                    <tbody>{lb_rows if lb_rows else '<tr><td colspan="4" style="text-align:center;color:{MUTED};">No HOOD activity yet</td></tr>'}</tbody>
                </table>
            </div>
            <div>
                <h4 style="color:{GREEN};margin-bottom:8px;">🔑 Token → Tier Map</h4>
                <div class="perm-grid">{tier_ref}</div>
                <div style="margin-top:12px;padding:12px;background:{CARD_BG};border:1px solid #222;border-radius:6px;">
                    <p style="color:{MUTED};font-size:12px;line-height:1.5;">
                        💡 <b>Spend HOOD</b> for one-time access above your tier.<br>
                        Cost = tier gap × 5 HOOD (vault files ×2).<br>
                        CLI: <code style="color:{GREEN};">python3 dewey_ssbn_bridge.py spend "Name" "key"</code>
                    </p>
                </div>
            </div>
        </div>"""
    else:
        ssbn_html = f"""
        <div class="empty-state" style="padding:40px;">
            ⚠️ SSBN database not available<br>
            <span style="font-size:12px;color:{MUTED};">{ssbn.get('error', 'Unknown error')}</span>
        </div>"""
    
    msg_html = f'<div class="message">{message}</div>' if message else ""
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dewey Security — Guard Station</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: {BG}; color: {TEXT}; min-height: 100vh; }}
.header {{ background: {NAVY}; padding: 16px 24px; display: flex; align-items: center; gap: 12px; border-bottom: 3px solid {GREEN}; }}
.header h1 {{ font-size: 20px; color: {GREEN}; }}
.header .badge {{ background: {GREEN}; color: #000; padding: 2px 10px; border-radius: 12px; font-size: 13px; font-weight: 600; }}
.container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
.message {{ background: {GREEN}22; border: 1px solid {GREEN}; color: {GREEN}; padding: 10px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 14px; }}
.tabs {{ display: flex; gap: 4px; margin-bottom: 20px; }}
.tab {{ padding: 8px 20px; background: {CARD_BG}; border: 1px solid #222; border-radius: 6px 6px 0 0; cursor: pointer; font-size: 14px; color: {MUTED}; }}
.tab.active {{ background: {NAVY}; color: {GREEN}; border-color: {GREEN}; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}
.request-card {{ background: {CARD_BG}; border: 1px solid #222; border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
.request-card:hover {{ border-color: #ff880044; }}
.req-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
.req-id {{ color: {GREEN}; font-family: monospace; font-size: 13px; }}
.req-time {{ color: {MUTED}; font-size: 12px; }}
.req-body {{ margin-bottom: 12px; }}
.req-file {{ font-size: 14px; margin-bottom: 4px; word-break: break-all; }}
.req-who {{ color: {MUTED}; font-size: 13px; }}
.req-why {{ color: {MUTED}; font-size: 13px; font-style: italic; }}
.req-actions {{ display: flex; gap: 8px; }}
.btn-approve, .btn-deny {{ padding: 8px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: opacity 0.2s; }}
.btn-approve {{ background: {GREEN}; color: #000; }}
.btn-deny {{ background: #cc3333; color: #fff; }}
.btn-approve:hover, .btn-deny:hover {{ opacity: 0.85; }}
.empty-state {{ text-align: center; padding: 40px; color: {MUTED}; font-size: 16px; }}
.audit-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.audit-table th {{ background: {NAVY}; color: {GREEN}; padding: 8px 12px; text-align: left; font-size: 12px; text-transform: uppercase; }}
.audit-table td {{ padding: 8px 12px; border-bottom: 1px solid #1a1a2e; }}
.audit-table tr:hover {{ background: {CARD_BG}; }}
.key-cell {{ font-family: monospace; font-size: 11px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.granted {{ color: {GREEN}; }}
.denied {{ color: #cc3333; }}
.perm-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px; }}
.perm-row {{ background: {CARD_BG}; border: 1px solid #222; border-radius: 6px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; }}
.perm-section {{ font-family: monospace; font-size: 14px; }}
.perm-level {{ font-size: 13px; font-weight: 600; }}
.stats {{ display: flex; gap: 16px; margin-bottom: 20px; }}
.stat-card {{ background: {CARD_BG}; border: 1px solid #222; border-radius: 8px; padding: 14px 20px; text-align: center; flex: 1; }}
.stat-num {{ font-size: 28px; font-weight: 700; color: {GREEN}; }}
.stat-label {{ font-size: 12px; color: {MUTED}; margin-top: 4px; }}
.footer {{ text-align: center; padding: 20px; color: {MUTED}; font-size: 12px; }}
.system-card {{ background: {CARD_BG}; border: 1px solid #222; border-radius: 8px; padding: 20px; text-align: center; }}
.system-card:hover {{ border-color: {GREEN}44; }}
.sys-icon {{ font-size: 36px; margin-bottom: 8px; }}
.sys-title {{ font-size: 16px; font-weight: 700; color: {GREEN}; margin-bottom: 4px; }}
.sys-subtitle {{ font-size: 12px; color: {MUTED}; margin-bottom: 10px; }}
.sys-detail {{ font-size: 12px; color: {MUTED}; line-height: 1.5; margin-bottom: 10px; }}
.sys-status {{ font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 12px; display: inline-block; }}
.sys-status.on {{ background: {GREEN}22; color: {GREEN}; border: 1px solid {GREEN}44; }}
.sys-status.off {{ background: #cc333322; color: #cc3333; border: 1px solid #cc333344; }}
</style>
</head>
<body>
<div class="header">
    <h1>🔐 Dewey Security</h1>
    <span class="badge">GUARD STATION</span>
</div>
<div class="container">
    {msg_html}
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-num">{len(pending)}</div>
            <div class="stat-label">Pending Requests</div>
        </div>
        <div class="stat-card">
            <div class="stat-num">{len(audit)}</div>
            <div class="stat-label">Audit Events</div>
        </div>
        <div class="stat-card">
            <div class="stat-num">{len(perms)}</div>
            <div class="stat-label">Custom Permissions</div>
        </div>
    </div>
    
    <div class="tabs">
        <div class="tab active" onclick="switchTab('pending')">🟠 Pending</div>
        <div class="tab" onclick="switchTab('audit')">📋 Audit Log</div>
        <div class="tab" onclick="switchTab('permissions')">🔒 Permissions</div>
        <div class="tab" onclick="switchTab('bridge')">🌉 Bridge</div>
        <div class="tab" onclick="switchTab('system')">🏗️ System</div>
    </div>
    
    <div class="tab-content active" id="tab-pending">
        {pending_html}
    </div>
    
    <div class="tab-content" id="tab-audit">
        <table class="audit-table">
            <thead><tr><th></th><th>Time</th><th>Action</th><th>Who</th><th>Result</th><th>Key</th></tr></thead>
            <tbody>{audit_html}</tbody>
        </table>
    </div>
    
    <div class="tab-content" id="tab-permissions">
        <h3 style="margin-bottom:12px;color:{MUTED}">Section Defaults</h3>
        <div class="perm-grid">{perm_html}</div>
    </div>
    
    <div class="tab-content" id="tab-bridge">
        <h3 style="margin-bottom:16px;color:{GREEN}">🌉 SSBN HOOD → Dewey Access Bridge</h3>
        {ssbn_html}
    </div>
    
    <div class="tab-content" id="tab-system">
        <h3 style="margin-bottom:16px;color:{GREEN}">🏗️ 3-Part Dewey Architecture</h3>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">
            <div class="system-card">
                <div class="sys-icon">🧠</div>
                <div class="sys-title">Google Drive</div>
                <div class="sys-subtitle">BRAIN — Storefront/Catalog</div>
                <div class="sys-detail">{catalog['total']} items indexed<br>Last sync: {sync_time}<br>Files are LOCKED</div>
                <div class="sys-status on">✅ Synced</div>
            </div>
            <div class="system-card">
                <div class="sys-icon">💾</div>
                <div class="sys-title">Internal Drive</div>
                <div class="sys-subtitle">BODY — Actual Files</div>
                <div class="sys-detail">{blockchain['blocks']} blockchain blocks<br>Last: {blockchain['last']}<br>Security-gated access</div>
                <div class="sys-status on">✅ Online</div>
            </div>
            <div class="system-card">
                <div class="sys-icon">🗑️</div>
                <div class="sys-title">GitHub Archive</div>
                <div class="sys-subtitle">TRASH — Before Recycling</div>
                <div class="sys-detail">{contracts['total']} contracts tracked<br>Pipeline: estimate→contract→invoice<br>Review before delete</div>
                <div class="sys-status on">✅ Ready</div>
            </div>
        </div>
        <div style="margin-top:20px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
            <div class="stat-card">
                <div class="stat-num">{catalog['total']}</div>
                <div class="stat-label">🧠 Catalog Items</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">{blockchain['blocks']}</div>
                <div class="stat-label">⛓️ Blockchain Blocks</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">{contracts['total']}</div>
                <div class="stat-label">📋 Contracts</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">{len(pending)}</div>
                <div class="stat-label">🟠 Pending Approvals</div>
            </div>
        </div>
        <div style="margin-top:20px;padding:16px;background:{CARD_BG};border:1px solid #222;border-radius:8px;">
            <h4 style="color:{GREEN};margin-bottom:8px;">🔑 How It Works</h4>
            <p style="color:{MUTED};font-size:13px;line-height:1.6;">
                1. <b>Browse</b> the Brain catalog on Google Drive — see titles and descriptions<br>
                2. <b>Request</b> a key for any file you want to access<br>
                3. <b>Approval</b> — sensitive files (650, 657, 690, 200) require Derrell's approval<br>
                4. <b>Unlock</b> — the key retrieves the actual file from Internal Drive<br>
                5. <b>Trash</b> — clutter goes to GitHub archive for review before permanent deletion
            </p>
        </div>
    </div>
    
    <div class="footer">Dewey Security Guard • Blacktech Solutions Corp • {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>

<script>
function switchTab(name) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    const tabMap = {{'pending': 1, 'audit': 2, 'permissions': 3, 'bridge': 4, 'system': 5}};
    const idx = tabMap[name] || 1;
    document.querySelector(`.tab:nth-child(${{idx}})`).classList.add('active');
    document.getElementById(`tab-${{name}}`).classList.add('active');
}}

function approve(id) {{
    fetch('/approve?id=' + id)
        .then(r => r.text())
        .then(msg => {{
            document.querySelector('.container').insertAdjacentHTML('afterbegin', '<div class="message">' + msg + '</div>');
            setTimeout(() => location.reload(), 800);
        }});
}}

function deny(id) {{
    fetch('/deny?id=' + id)
        .then(r => r.text())
        .then(msg => {{
            document.querySelector('.container').insertAdjacentHTML('afterbegin', '<div class="message">' + msg + '</div>');
            setTimeout(() => location.reload(), 800);
        }});
}}
</script>
</body>
</html>"""

# ── HTTP Handler ───────────────────────────────────────────────────

class SecurityHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        if path == "/" or path == "/index.html":
            user = sso_get_user(self.headers)
            if not user:
                self.send_response(302)
                self.send_header('Location', SSO_LOGIN_URL)
                self.end_headers()
                return
            self.serve_html(render_page())
        elif path == "/approve":
            req_id = params.get("id", [None])[0]
            if req_id:
                output = run_security("approve", req_id)
                self.serve_text(output)
            else:
                self.serve_text("❌ Missing request ID")
        elif path == "/deny":
            req_id = params.get("id", [None])[0]
            if req_id:
                output = run_security("deny", req_id)
                self.serve_text(output)
            else:
                self.serve_text("❌ Missing request ID")
        elif path == "/refresh":
            self.serve_html(render_page())
        else:
            self.send_error(404)
    
    def serve_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_text(self, text):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode())
    
    def log_message(self, format, *args):
        pass  # Quiet

# ── Main ───────────────────────────────────────────────────────────

def main():
    print(f"🔐 Dewey Security Dashboard starting on port {PORT}")
    print(f"   Local:  http://127.0.0.1:{PORT}")
    print(f"   Cloudflare: https://dewey.blacktechsolutionscorp.com")
    
    server = HTTPServer(("127.0.0.1", PORT), SecurityHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        server.server_close()

if __name__ == "__main__":
    main()
