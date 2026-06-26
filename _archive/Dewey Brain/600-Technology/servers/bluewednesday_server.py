#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, re, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

DATA_FILE = '/home/allenai/data/bfn_shared.json'
HTML_FILE = '/home/allenai/bfn.html'
BFN_FILE  = '/home/allenai/bluewednesday.html'
HOOD_FILE = '/home/allenai/hood.html'
BASE_DIR  = '/home/allenai'

# ── DATA LAYER ────────────────────────────────────────────
EMPTY = {
    'members':       [],
    'rsvp':          [],
    'funding':       {},
    'tformation':    {},
    'director':      None,
    'businesses':    [],
    'distributions': []
}

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return dict(EMPTY)

def save_db(db):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(db, f, indent=2)

# ── HANDLER ───────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def serve_html(self, path):
        with open(path, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length)) if length else {}

    # ── GET ──────────────────────────────────────────────
    def do_GET(self):
        p = self.path.split('?')[0]

        if p.startswith('/static/'):
            fname = p[len('/static/'):]
            fpath = os.path.join(BASE_DIR, 'static', fname)
            if os.path.isfile(fpath):
                ext = os.path.splitext(fname)[1].lower()
                mime = {'jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png','gif':'image/gif','webp':'image/webp'}.get(ext.lstrip('.'), 'application/octet-stream')
                with open(fpath, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404)
            return

        if p in ('/', '/index.html'):
            self.serve_html(HTML_FILE)

        elif p in ('/bfn', '/bfn.html'):
            self.serve_html(BFN_FILE)

        elif p in ('/electrification', '/pipeline', '/epi'):
            self.serve_html('/home/allenai/electrification_pipeline.html')

        elif p in ('/old', '/old.html'):
            self.serve_html(BFN_FILE)

        elif p in ('/hood', '/hood.html'):
            self.serve_html(HOOD_FILE)

        elif p in ('/shop', '/shop.html'):
            self.serve_html('/home/allenai/qbitme_shop.html')

        elif p in ('/shopify', '/shopify.html', '/store'):
            self.serve_html('/home/allenai/qbitme_shopify_mockup.html')

        elif p in ('/calculator', '/calculator.html'):
            self.serve_html('/home/allenai/static/energy_calculator.html')

        # Full DB snapshot — app loads this on start
        elif p == '/api/bfn':
            self.send_json(200, load_db())

        # Collection reads
        elif p == '/api/bfn/members':
            self.send_json(200, load_db()['members'])

        elif p == '/api/bfn/rsvp':
            self.send_json(200, load_db()['rsvp'])

        elif p == '/api/bfn/funding':
            self.send_json(200, load_db()['funding'])

        elif p == '/api/bfn/tformation':
            self.send_json(200, load_db()['tformation'])

        elif p == '/api/bfn/director':
            self.send_json(200, load_db()['director'])

        elif p == '/api/bfn/businesses':
            self.send_json(200, load_db()['businesses'])

        # Legacy
        elif p == '/api/bluewednesday':
            self.send_json(200, [])

        else:
            self.send_json(404, {'error': 'Not found'})

    # ── POST ─────────────────────────────────────────────
    def do_POST(self):
        p    = self.path.split('?')[0]
        body = self.read_body()
        db   = load_db()
        ts   = datetime.utcnow().isoformat() + 'Z'

        # Add member
        if p == '/api/bfn/members':
            body['added'] = ts
            db['members'].append(body)
            save_db(db)
            self.send_json(200, {'ok': True, 'count': len(db['members'])})

        # Add RSVP
        elif p == '/api/bfn/rsvp':
            body['date'] = ts
            db['rsvp'].insert(0, body)
            save_db(db)
            # Email notification to support@
            try:
                name    = body.get('name', 'Unknown')
                biz     = body.get('biz', 'N/A')
                contact = body.get('contact', 'N/A')
                status  = body.get('status', 'N/A')
                status_label = '✅ Going' if status == 'going' else '🤔 Maybe' if status == 'maybe' else '❌ Not Going'
                msg = MIMEMultipart()
                msg['Subject'] = f'BW3 RSVP — {name} ({status_label})'
                msg['From']    = 'support@blacktechsolutionscorp.com'
                msg['To']      = 'support@blacktechsolutionscorp.com'
                body_text = f"""New BW3 RSVP received!

Name:    {name}
Business: {biz}
Contact: {contact}
Status:  {status_label}
Time:    {ts}

Zoom Link: https://us02web.zoom.us/j/89142162003?pwd=MFVyVlFIZ3o0TVF1NDVlU25CVTQ1UT09

Total RSVPs so far: {len(db['rsvp'])}
"""
                msg.attach(MIMEText(body_text, 'plain'))
                srv = smtplib.SMTP_SSL('mail.blacktechsolutionscorp.com', 465)
                srv.login('support@blacktechsolutionscorp.com', 'Newproject26$')
                srv.sendmail('support@blacktechsolutionscorp.com', 'support@blacktechsolutionscorp.com', msg.as_string())
                srv.quit()
            except Exception as e:
                print(f'RSVP email error: {e}')
            self.send_json(200, {'ok': True, 'count': len(db['rsvp'])})

        # Update funding for a month
        elif p == '/api/bfn/funding':
            month = str(body.get('month'))
            if month:
                if month not in db['funding']:
                    db['funding'][month] = {'goal': 500, 'raised': 0, 'contributions': []}
                if 'raised' in body:
                    db['funding'][month]['raised'] = (db['funding'][month].get('raised',0)) + body['raised']
                    db['funding'][month]['contributions'].append({'amount': body['raised'], 'date': ts})
                if 'goal' in body:
                    db['funding'][month]['goal'] = body['goal']
                save_db(db)
                self.send_json(200, {'ok': True})
            else:
                self.send_json(400, {'error': 'month required'})

        # Save director
        elif p == '/api/bfn/director':
            body['set'] = ts
            db['director'] = body
            save_db(db)
            self.send_json(200, {'ok': True})

        # Add T-Formation member
        elif p == '/api/bfn/tformation':
            team = str(body.get('team'))
            name = body.get('name','').strip()
            if team and name:
                if team not in db['tformation']:
                    db['tformation'][team] = []
                entry = f"{name} ({body['phone']})" if body.get('phone') else name
                if entry not in db['tformation'][team]:
                    db['tformation'][team].append(entry)
                save_db(db)
                self.send_json(200, {'ok': True})
            else:
                self.send_json(400, {'error': 'team and name required'})

        # Add business to directory
        elif p == '/api/bfn/businesses':
            body['added'] = ts
            db['businesses'].append(body)
            save_db(db)
            self.send_json(200, {'ok': True, 'count': len(db['businesses'])})

        # Log a distribution
        elif p == '/api/bfn/distributions':
            body['date'] = ts
            if 'distributions' not in db:
                db['distributions'] = []
            db['distributions'].insert(0, body)
            save_db(db)
            self.send_json(200, {'ok': True, 'count': len(db['distributions'])})

        # Legacy
        elif p == '/api/bluewednesday':
            self.send_json(200, {'ok': True})

        else:
            self.send_json(404, {'error': 'Not found'})

    # ── DELETE ───────────────────────────────────────────
    def do_DELETE(self):
        p = self.path.split('?')[0]
        db = load_db()

        m = re.match(r'^/api/bfn/members/(\d+)$', p)
        if m:
            idx = int(m.group(1))
            if 0 <= idx < len(db['members']):
                db['members'].pop(idx)
                save_db(db)
            self.send_json(200, {'ok': True})
            return

        m = re.match(r'^/api/bfn/rsvp/(\d+)$', p)
        if m:
            idx = int(m.group(1))
            if 0 <= idx < len(db['rsvp']):
                db['rsvp'].pop(idx)
                save_db(db)
            self.send_json(200, {'ok': True})
            return

        m = re.match(r'^/api/bfn/businesses/(\d+)$', p)
        if m:
            idx = int(m.group(1))
            if 0 <= idx < len(db['businesses']):
                db['businesses'].pop(idx)
                save_db(db)
            self.send_json(200, {'ok': True})
            return

        self.send_json(404, {'error': 'Not found'})

    # ── OPTIONS (CORS preflight) ─────────────────────────
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8094), Handler)
    print('BFN server running on port 8094')
    server.serve_forever()
