#!/usr/bin/env python3
"""
🧠 Dewey Library Dashboard — 3-Tier Knowledge System
Port 8096 — Brain (Google Drive) → Body (Internal Drive) → Archive (GitHub)
"""

import json
import os
import subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

CATALOG_PATH = "/home/allenai/blacktech_brain/000-General/dewey_catalog.json"
INTERNAL_DRIVE = "/media/allenai/Expansion/Blacktech_Drive"
ARCHIVE_DIR = "/home/allenai/blacktech_archive"

DEWEY_MAP = {
    "000": "General", "100": "Philosophy", "200": "Religion",
    "300": "Social Sciences", "400": "Language", "500": "Science",
    "600": "Technology", "620": "Engineering", "640": "Household",
    "650": "Management", "657": "Accounting", "690": "Construction",
    "691": "Building Materials", "692": "Auxiliary Practices",
    "696": "Utilities", "697": "HVAC", "700": "Arts",
    "800": "Literature", "900": "History", "910": "Travel",
    "920": "Biography", "930": "Archaeology", "999": "Decisions"
}

def load_catalog():
    if os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH) as f:
            return json.load(f)
    return []

def get_body_stats():
    if not os.path.exists(INTERNAL_DRIVE):
        return {"mounted": False, "files": 0, "dirs": 0}
    files = sum(1 for _ in Path(INTERNAL_DRIVE).rglob('*') if _.is_file() and not _.name.startswith('.'))
    dirs = sum(1 for _ in Path(INTERNAL_DRIVE).rglob('*') if _.is_dir() and not _.name.startswith('.'))
    return {"mounted": True, "files": files, "dirs": dirs}

def get_archive_stats():
    if not os.path.exists(ARCHIVE_DIR):
        return {"exists": False, "trash": 0}
    trash = len([f for f in os.listdir(ARCHIVE_DIR) if f.startswith("trash_")])
    return {"exists": True, "trash": trash}

def get_banking_stats():
    """Get Albert banking stats for dashboard tile."""
    db_path = "/home/allenai/albert_banking.db"
    if not os.path.exists(db_path):
        return {"connected": False, "banks": 0, "accounts": 0, "transactions": 0}
    import sqlite3
    conn = sqlite3.connect(db_path)
    banks = conn.execute("SELECT COUNT(*) FROM plaid_items WHERE status='connected'").fetchone()[0]
    accounts = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    txns = conn.execute("SELECT COUNT(*) FROM transactions WHERE plaid_tx_id IS NOT NULL").fetchone()[0]
    conn.close()
    return {"connected": banks > 0, "banks": banks, "accounts": accounts, "transactions": txns}

def render_dashboard():
    catalog = load_catalog()
    body = get_body_stats()
    archive = get_archive_stats()
    banking = get_banking_stats()
    
    # Section counts
    counts = {}
    for e in catalog:
        section = e["dewey"].split("-")[0] if "-" in e["dewey"] else e["dewey"]
        counts[section] = counts.get(section, 0) + 1
    
    # Section cards
    sections_html = ""
    for code in sorted(counts.keys()):
        desc = DEWEY_MAP.get(code, code)
        count = counts[code]
        pct = min(count / max(counts.values()) * 100, 100) if counts else 0
        sections_html += f"""
            <div class="section-card">
                <div class="section-code">{code}</div>
                <div class="section-desc">{desc}</div>
                <div class="section-count">{count} files</div>
                <div class="bar-bg"><div class="bar-fill" style="width:{pct}%"></div></div>
            </div>
        """
    
    # Recent entries
    recent = sorted(catalog, key=lambda e: e.get("modified", ""), reverse=True)[:10]
    recent_html = ""
    for e in recent:
        dewey_code = e["dewey"].split("-")[0] if "-" in e["dewey"] else e["dewey"]
        mod = e.get("modified", "?")[:10]
        recent_html += f"""
            <div class="recent-item">
                <span class="recent-dewey">{dewey_code}</span>
                <span class="recent-title">{e['title']}</span>
                <span class="recent-date">{mod}</span>
            </div>
        """
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Dewey Library — 3-Tier Knowledge System</title>
    <meta charset="utf-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1e 100%);
            color: #e0e0e0;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #69be28; margin-bottom: 5px; text-align: center; font-size: 24px; }}
        .subtitle {{ text-align: center; color: #888; margin-bottom: 30px; font-size: 13px; }}
        
        /* Tier cards */
        .tiers {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }}
        .tier-card {{
            background: #16213e;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border: 1px solid #333;
        }}
        .tier-card.brain {{ border-top: 3px solid #69be28; }}
        .tier-card.body {{ border-top: 3px solid #4dd0e1; }}
        .tier-card.archive {{ border-top: 3px solid #ff9800; }}
        .tier-card.banking {{ border-top: 3px solid #ffd700; }}
        .tier-icon {{ font-size: 32px; margin-bottom: 10px; }}
        .tier-label {{ font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
        .tier-value {{ font-size: 28px; font-weight: bold; margin: 8px 0; }}
        .tier-detail {{ font-size: 12px; color: #888; }}
        .brain .tier-value {{ color: #69be28; }}
        .body .tier-value {{ color: #4dd0e1; }}
        .archive .tier-value {{ color: #ff9800; }}
        .banking .tier-value {{ color: #ffd700; }}
        
        /* Sections */
        .section-title {{ color: #69be28; margin: 30px 0 15px; font-size: 18px; }}
        .sections-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 10px;
            margin-bottom: 30px;
        }}
        .section-card {{
            background: #16213e;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 12px;
        }}
        .section-code {{ font-weight: bold; color: #4dd0e1; font-size: 16px; }}
        .section-desc {{ font-size: 11px; color: #888; margin: 4px 0; }}
        .section-count {{ font-size: 13px; color: #69be28; }}
        .bar-bg {{ background: #0f0f1e; height: 4px; border-radius: 2px; margin-top: 6px; }}
        .bar-fill {{ background: #69be28; height: 4px; border-radius: 2px; }}
        
        /* Recent */
        .recent-list {{
            background: #16213e;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
        }}
        .recent-item {{
            display: flex;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #222;
            font-size: 13px;
        }}
        .recent-item:last-child {{ border-bottom: none; }}
        .recent-dewey {{
            background: #0f0f1e;
            color: #4dd0e1;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: bold;
            margin-right: 10px;
            min-width: 40px;
            text-align: center;
        }}
        .recent-title {{ flex: 1; color: #e0e0e0; }}
        .recent-date {{ color: #888; font-size: 11px; }}
        
        /* Search */
        .search-bar {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .search-bar input {{
            flex: 1;
            padding: 12px;
            background: #16213e;
            border: 1px solid #333;
            color: #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
        }}
        .search-bar input:focus {{ outline: none; border-color: #69be28; }}
        .search-bar button {{
            background: #69be28;
            color: #000;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
        }}
        .search-bar button:hover {{ background: #7ec93f; }}
        
        .search-results {{
            background: #16213e;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            display: none;
        }}
        .result-item {{
            padding: 10px;
            border-bottom: 1px solid #222;
            cursor: pointer;
        }}
        .result-item:hover {{ background: #1a2744; }}
        .result-dewey {{ color: #4dd0e1; font-weight: bold; font-size: 12px; }}
        .result-title {{ color: #e0e0e0; font-size: 14px; margin: 3px 0; }}
        .result-key {{ color: #888; font-size: 11px; font-family: monospace; }}
        
        /* Pipeline flow */
        .pipeline {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            margin: 30px 0;
            padding: 20px;
            background: #16213e;
            border-radius: 8px;
            border: 1px solid #333;
        }}
        .pipeline-step {{
            text-align: center;
            padding: 15px 25px;
            background: #0f0f1e;
            border-radius: 6px;
            border: 1px solid #333;
        }}
        .pipeline-arrow {{ color: #69be28; font-size: 24px; }}
        .pipeline-step .step-icon {{ font-size: 24px; }}
        .pipeline-step .step-name {{ font-weight: bold; color: #e0e0e0; margin-top: 5px; }}
        .pipeline-step .step-desc {{ font-size: 11px; color: #888; margin-top: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 Dewey Library</h1>
        <div class="subtitle">3-Tier Knowledge System — Brain → Body → Archive</div>
        
        <!-- Pipeline -->
        <div class="pipeline">
            <div class="pipeline-step">
                <div class="step-icon">🧠</div>
                <div class="step-name">Brain</div>
                <div class="step-desc">Google Drive<br>Catalog & Index</div>
            </div>
            <div class="pipeline-arrow">→</div>
            <div class="pipeline-step">
                <div class="step-icon">💪</div>
                <div class="step-name">Body</div>
                <div class="step-desc">Internal Drive<br>Actual Files</div>
            </div>
            <div class="pipeline-arrow">→</div>
            <div class="pipeline-step">
                <div class="step-icon">🗑️</div>
                <div class="step-name">Archive</div>
                <div class="step-desc">GitHub<br>45-Day Safety Net</div>
            </div>
        </div>
        
        <!-- Tier stats -->
        <div class="tiers">
            <div class="tier-card brain">
                <div class="tier-icon">🧠</div>
                <div class="tier-label">Brain — Google Drive</div>
                <div class="tier-value">{len(catalog)}</div>
                <div class="tier-detail">catalog entries in {len(counts)} sections</div>
            </div>
            <div class="tier-card body">
                <div class="tier-icon">💪</div>
                <div class="tier-label">Body — Internal Drive</div>
                <div class="tier-value">{body['files'] if body['mounted'] else '⚠️'}</div>
                <div class="tier-detail">{'files in ' + str(body['dirs']) + ' dirs' if body['mounted'] else 'Drive not mounted'}</div>
            </div>
            <div class="tier-card archive">
                <div class="tier-icon">🗑️</div>
                <div class="tier-label">Archive — GitHub</div>
                <div class="tier-value">{archive['trash']}</div>
                <div class="tier-detail">items awaiting recycling</div>
            </div>
            <div class="tier-card banking">
                <div class="tier-icon">🏦</div>
                <div class="tier-label">Albert Banking — Plaid</div>
                <div class="tier-value">{banking['accounts']}</div>
                <div class="tier-detail">{banking['banks']} bank(s) · {banking['transactions']} txns · {'🟢 Connected' if banking['connected'] else '🔴 Offline'}</div>
            </div>
        </div>
        
        <!-- Search -->
        <div class="search-bar">
            <input type="text" id="searchInput" placeholder="🔍 Search Brain catalog... (title, keyword, Dewey code)" onkeyup="if(event.key==='Enter')doSearch()">
            <button onclick="doSearch()">Search</button>
        </div>
        <div class="search-results" id="searchResults"></div>
        
        <!-- Sections -->
        <div class="section-title">📂 Dewey Sections</div>
        <div class="sections-grid">
            {sections_html}
        </div>
        
        <!-- Recent -->
        <div class="section-title">🕐 Recently Modified</div>
        <div class="recent-list">
            {recent_html if recent_html else '<div style="color:#888;padding:10px;">No entries yet.</div>'}
        </div>
    </div>
    
    <script>
        async function doSearch() {{
            const q = document.getElementById('searchInput').value.trim();
            const results = document.getElementById('searchResults');
            
            if (!q) {{
                results.style.display = 'none';
                return;
            }}
            
            const resp = await fetch('/api/search?q=' + encodeURIComponent(q));
            const data = await resp.json();
            
            if (data.hits.length === 0) {{
                results.innerHTML = '<div style="padding:15px;color:#888;">🔍 No results for "' + q + '"</div>';
            }} else {{
                results.innerHTML = data.hits.map((h, i) => `
                    <div class="result-item" onclick="alert('Key: ' + this.querySelector('.result-key').textContent)">
                        <div class="result-dewey">${{h.dewey}} — ${{h.dewey_desc}}</div>
                        <div class="result-title">📄 ${{h.title}}</div>
                        <div class="result-key">🔑 ${{h.key}}</div>
                    </div>
                `).join('');
            }}
            results.style.display = 'block';
        }}
    </script>
</body>
</html>"""

class DeweyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(render_dashboard().encode())
        
        elif path == "/api/search":
            q = params.get("q", [""])[0].lower()
            catalog = load_catalog()
            hits = []
            for e in catalog:
                if (q in e["title"].lower() or
                    q in e.get("description", "").lower() or
                    q in e["dewey"].lower()):
                    dewey_code = e["dewey"].split("-")[0] if "-" in e["dewey"] else e["dewey"]
                    hits.append({
                        "title": e["title"],
                        "dewey": e["dewey"],
                        "dewey_desc": DEWEY_MAP.get(dewey_code, e["dewey"]),
                        "key": e.get("internal_key", "?"),
                        "type": e.get("type", "?"),
                    })
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"query": q, "hits": hits[:30]}).encode())
        
        elif path == "/api/stats":
            catalog = load_catalog()
            body = get_body_stats()
            archive = get_archive_stats()
            
            counts = {}
            for e in catalog:
                section = e["dewey"].split("-")[0] if "-" in e["dewey"] else e["dewey"]
                counts[section] = counts.get(section, 0) + 1
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "brain": {"entries": len(catalog), "sections": len(counts)},
                "body": body,
                "archive": archive,
                "section_counts": counts
            }).encode())
        
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8106), DeweyHandler)
    print("🧠 Dewey Library Dashboard — http://0.0.0.0:8106")
    server.serve_forever()
