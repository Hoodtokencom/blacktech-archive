#!/usr/bin/env python3
"""
ComEd Electrification Pipeline — Full System Server
Port 8095 | comed.blacktechsolutionscorp.com
Handles: Lead capture, CRM, Photo uploads, Notifications
"""
import http.server, socketserver, os, json, urllib.request, cgi, uuid
from datetime import datetime
from urllib.parse import urlparse

PORT      = 8095
DATA_FILE  = '/home/allenai/data/comed_leads.json'
PHOTOS_DIR = '/home/allenai/data/comed_photos'
DOCS_DIR   = '/home/allenai/data/comed_docs'

# Load from env
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID   = os.environ.get('TELEGRAM_HOME_CHANNEL', '5805015753')

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# ── DATA HELPERS ──────────────────────────────────────────────────────────────
def load_leads():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return []

def save_leads(leads):
    with open(DATA_FILE, 'w') as f:
        json.dump(leads, f, indent=2)

def tg_notify(msg):
    """Send Telegram message to Derrell."""
    if not BOT_TOKEN:
        return
    try:
        payload = json.dumps({'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            data=payload, headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f'TG error: {e}')

# ── HTML PAGES ─────────────────────────────────────────────────────────────────
SIGNUP_HTML = '/home/allenai/comed_signup.html'
DASHBOARD_HTML = '/home/allenai/comed_dashboard.html'
PIPELINE_HTML = '/home/allenai/electrification_pipeline.html'

# ── REQUEST HANDLER ───────────────────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def serve_html(self, path):
        try:
            with open(path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.cors()
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404)

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.cors()
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length) if length else b''

    # ── GET ──────────────────────────────────────────────────────────────────
    def do_GET(self):
        p = urlparse(self.path).path.rstrip('/')

        if p in ('', '/', '/signup', '/apply'):
            self.serve_html(SIGNUP_HTML)

        elif p in ('/dashboard', '/crm', '/admin'):
            self.serve_html(DASHBOARD_HTML)

        elif p in ('/pipeline', '/flow'):
            self.serve_html(PIPELINE_HTML)

        elif p == '/api/leads':
            self.send_json(load_leads())

        elif p.startswith('/api/leads/') and not any(p.endswith(s) for s in ('/status','/note','/delete','/closeout','/photos')):
            lid = p.split('/')[-1]
            if lid.isdigit():
                leads = load_leads()
                lead = next((l for l in leads if str(l.get('id')) == lid), None)
                if lead:
                    self.send_json(lead)
                else:
                    self.send_json({'error': 'not found'}, 404)
            else:
                self.send_json({'error': 'not found'}, 404)

        elif p.startswith('/api/lien-waiver/'):
            lid = p.split('/')[-1]
            leads = load_leads()
            lead = next((l for l in leads if str(l.get('id')) == lid), None)
            if lead:
                try:
                    import fitz as _fitz
                    import math

                    def _num_to_words(n):
                        ones = ['','One','Two','Three','Four','Five','Six','Seven','Eight','Nine',
                                'Ten','Eleven','Twelve','Thirteen','Fourteen','Fifteen','Sixteen',
                                'Seventeen','Eighteen','Nineteen']
                        tens = ['','','Twenty','Thirty','Forty','Fifty','Sixty','Seventy','Eighty','Ninety']
                        if n == 0: return 'Zero'
                        if n < 20: return ones[n]
                        if n < 100: return tens[n//10] + ('' if n%10==0 else ' '+ones[n%10])
                        if n < 1000: return ones[n//100]+' Hundred'+('' if n%100==0 else ' '+_num_to_words(n%100))
                        if n < 1000000: return _num_to_words(n//1000)+' Thousand'+('' if n%1000==0 else ' '+_num_to_words(n%1000))
                        return str(n)

                    amount_str = lead.get('closeout',{}).get('lw_amount','0').replace(',','').replace('$','').strip()
                    try:
                        amt = float(amount_str)
                        dollars = int(amt)
                        cents = int(round((amt - dollars)*100))
                        amount_words = _num_to_words(dollars) + (' and %d/100' % cents if cents else '')
                        amount_num = f"{amt:,.2f}"
                    except:
                        amount_words = amount_str
                        amount_num = amount_str

                    owner   = lead.get('name','')
                    address = lead.get('address','') + (', '+lead.get('city','') if lead.get('city') else '')
                    date    = lead.get('closeout',{}).get('insp_date','') or datetime.now().strftime('%m/%d/%Y')
                    date_fmt = date if '/' in date else datetime.strptime(date,'%Y-%m-%d').strftime('%m/%d/%Y') if date else datetime.now().strftime('%m/%d/%Y')

                    # Notary date parts
                    try:
                        dt = datetime.strptime(date,'%Y-%m-%d') if '-' in date else datetime.strptime(date,'%m/%d/%Y')
                    except:
                        dt = datetime.now()
                    day_suffix = {1:'1st',2:'2nd',3:'3rd'}.get(dt.day if dt.day <= 3 else 0, f'{dt.day}th')
                    notary_month = dt.strftime('%B')
                    notary_year  = str(dt.year)

                    TEMPLATE = '/home/allenai/data/Final-Waiver-of-Lien-Blacktech-7414-S-Drexel.pdf'
                    doc = _fitz.open(TEMPLATE)
                    page = doc[0]
                    BLACK = (0,0,0)
                    F,SZ,SM = 'helv',8.5,7.5

                    def txt(x,y,t,sz=SZ):
                        page.insert_text((x,y), str(t), fontname=F, fontsize=sz, color=BLACK)

                    txt(270,122, 'Elevate Energy')
                    txt(97, 139, 'ComEd Electrification Program - Electrical Service')
                    txt(175,155, address)
                    txt(125,172, owner)
                    txt(312,188, amount_words)
                    txt(75, 199, amount_num)
                    txt(72, 269, date_fmt)
                    txt(330,269, 'Blacktech Solutions Corp')
                    txt(268,285, '14076 Lincoln Ave, Dolton, IL 60419')
                    txt(215,382, 'Derrell Black')
                    txt(270,395, 'Owner')
                    txt(170,408, 'Blacktech Solutions Corp')
                    txt(260,421, 'Electrical Services')
                    txt(108,434, address)
                    txt(105,447, owner)
                    txt(390,460, amount_num)
                    txt(100,471, amount_num)
                    txt(49, 560, 'Blacktech Solutions Corp', SM)
                    txt(49, 571, '14076 Lincoln Ave, Dolton, IL 60419', SM)
                    txt(255,560, 'Electrical Services', SM)
                    txt(322,560, amount_num, SM)
                    txt(400,560, amount_num, SM)
                    txt(455,560, amount_num, SM)
                    txt(510,560, '0.00', SM)
                    txt(322,612, amount_num, SM)
                    txt(400,612, amount_num, SM)
                    txt(455,612, amount_num, SM)
                    txt(510,612, '0.00', SM)
                    txt(73, 656, date_fmt)
                    txt(400,716, day_suffix)
                    txt(430,716, notary_month)
                    txt(510,716, notary_year)

                    out_name = f"Lien-Waiver-{owner.replace(' ','-')}-{lead.get('address','').replace(' ','-')[:20]}.pdf"
                    out_path = f'/home/allenai/data/{out_name}'
                    doc.save(out_path)
                    doc.close()

                    with open(out_path,'rb') as f: pdf_data = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type','application/pdf')
                    self.send_header('Content-Disposition', f'attachment; filename="{out_name}"')
                    self.send_header('Content-Length', len(pdf_data))
                    self.cors()
                    self.end_headers()
                    self.wfile.write(pdf_data)
                except Exception as e:
                    self.send_json({'error': str(e)}, 500)
            else:
                self.send_json({'error': 'not found'}, 404)

        elif p.startswith('/api/photos/'):
            lid = p.split('/')[-1]
            photo_dir = os.path.join(PHOTOS_DIR, str(lid))
            if os.path.isdir(photo_dir):
                photos = []
                for fn in sorted(os.listdir(photo_dir)):
                    if fn.endswith('.meta'): continue
                    meta_file = os.path.join(photo_dir, fn + '.meta')
                    ptype, uploaded = 'other', ''
                    if os.path.exists(meta_file):
                        try:
                            with open(meta_file) as mf:
                                m = json.load(mf)
                                ptype = m.get('type', 'other')
                                uploaded = m.get('uploaded', '')
                        except: pass
                    photos.append({'path': f'{lid}/{fn}', 'type': ptype, 'uploaded': uploaded, 'filename': fn})
                self.send_json(photos)
            else:
                self.send_json([])

        elif p.startswith('/api/photo-file/'):
            rel = p[len('/api/photo-file/'):]
            fpath = os.path.join(PHOTOS_DIR, rel)
            try:
                with open(fpath, 'rb') as f: data = f.read()
                ext = fpath.rsplit('.', 1)[-1].lower()
                ct = {'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','heic':'image/heic','webp':'image/webp'}.get(ext,'application/octet-stream')
                self.send_response(200)
                self.send_header('Content-Type', ct)
                self.send_header('Content-Length', len(data))
                self.cors()
                self.end_headers()
                self.wfile.write(data)
            except: self.send_error(404)

        elif p == '/api/stats':
            leads = load_leads()
            stats = {
                'total': len(leads),
                'by_status': {},
                'by_trade': {}
            }
            for l in leads:
                s = l.get('status', 'lead')
                stats['by_status'][s] = stats['by_status'].get(s, 0) + 1
                for t in l.get('services', []):
                    stats['by_trade'][t] = stats['by_trade'].get(t, 0) + 1
            self.send_json(stats)

        elif p.startswith('/static/'):
            fname = p[8:]
            fpath = f'/home/allenai/static/{fname}'
            try:
                with open(fpath, 'rb') as f:
                    data = f.read()
                ext = fname.rsplit('.', 1)[-1].lower()
                ct = {'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg',
                      'pdf':'application/pdf','svg':'image/svg+xml'}.get(ext, 'application/octet-stream')
                self.send_response(200)
                self.send_header('Content-Type', ct)
                self.send_header('Content-Length', len(data))
                self.end_headers()
                self.wfile.write(data)
            except:
                self.send_error(404)
        else:
            self.send_error(404)

    # ── POST ─────────────────────────────────────────────────────────────────
    def do_POST(self):
        p = urlparse(self.path).path.rstrip('/')
        body = self.read_body()

        try:
            data = json.loads(body)
        except:
            data = {}

        # ── NEW LEAD ────────────────────────────────────────────────────────
        if p == '/api/leads':
            leads = load_leads()
            lead = {
                'id': int(datetime.now().timestamp() * 1000),
                'name':     data.get('name', '').strip(),
                'address':  data.get('address', '').strip(),
                'city':     data.get('city', '').strip(),
                'phone':    data.get('phone', '').strip(),
                'email':    data.get('email', '').strip(),
                'services': data.get('services', []),
                'notes':    data.get('notes', '').strip(),
                'source':   data.get('source', 'web-form'),
                'status':   'new',
                'created':  datetime.now().strftime('%Y-%m-%d %H:%M'),
                'updated':  datetime.now().strftime('%Y-%m-%d %H:%M'),
                'docs':     []
            }
            leads.insert(0, lead)
            save_leads(leads)

            # Telegram alert
            trades = ', '.join(lead['services']) if lead['services'] else 'Not specified'
            msg = (
                f"🔔 <b>NEW ELECTRIFICATION LEAD</b>\n\n"
                f"👤 <b>{lead['name']}</b>\n"
                f"📍 {lead['address']}{', ' + lead['city'] if lead['city'] else ''}\n"
                f"📞 {lead['phone']}\n"
                f"✉️ {lead['email']}\n"
                f"🔧 Services: {trades}\n"
                f"📝 Notes: {lead['notes'] or '—'}\n\n"
                f"👉 View: comed.blacktechsolutionscorp.com/dashboard"
            )
            tg_notify(msg)

            self.send_json({'ok': True, 'id': lead['id']})

        # ── UPDATE LEAD STATUS ───────────────────────────────────────────────
        elif p.startswith('/api/leads/') and p.endswith('/status'):
            lid = p.split('/')[-2]
            leads = load_leads()
            lead = next((l for l in leads if str(l.get('id')) == lid), None)
            if lead:
                old_status = lead.get('status', 'new')
                lead['status'] = data.get('status', lead['status'])
                lead['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                if data.get('notes'):
                    lead['notes'] = data['notes']
                save_leads(leads)

                status_emoji = {
                    'new': '🆕', 'contacted': '📞', 'walkthrough': '🚶',
                    'contract': '📋', 'active': '🔨', 'complete': '✅', 'cancelled': '❌'
                }
                em = status_emoji.get(lead['status'], '🔄')
                tg_notify(
                    f"{em} <b>Lead Status Update</b>\n"
                    f"👤 {lead['name']}\n"
                    f"📍 {lead['address']}\n"
                    f"{old_status.upper()} → <b>{lead['status'].upper()}</b>"
                )
                self.send_json({'ok': True})
            else:
                self.send_json({'error': 'not found'}, 404)

        # ── ADD NOTE ─────────────────────────────────────────────────────────
        elif p.startswith('/api/leads/') and p.endswith('/note'):
            lid = p.split('/')[-2]
            leads = load_leads()
            lead = next((l for l in leads if str(l.get('id')) == lid), None)
            if lead:
                note = data.get('note', '').strip()
                existing = lead.get('notes', '')
                ts = datetime.now().strftime('%m/%d %H:%M')
                lead['notes'] = f"[{ts}] {note}\n{existing}".strip()
                lead['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                save_leads(leads)
                self.send_json({'ok': True})
            else:
                self.send_json({'error': 'not found'}, 404)

        # ── CLOSEOUT ─────────────────────────────────────────────────────────────
        elif p.startswith('/api/leads/') and p.endswith('/closeout'):
            lid = p.split('/')[-2]
            leads = load_leads()
            lead = next((l for l in leads if str(l.get('id')) == lid), None)
            if lead:
                lead['closeout'] = data.get('closeout', {})
                lead['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                save_leads(leads)
                self.send_json({'ok': True})
            else:
                self.send_json({'error': 'not found'}, 404)

        # ── DELETE LEAD ──────────────────────────────────────────────────────
        elif p.startswith('/api/leads/') and p.endswith('/delete'):
            lid = p.split('/')[-2]
            leads = load_leads()
            leads = [l for l in leads if str(l.get('id')) != lid]
            save_leads(leads)
            self.send_json({'ok': True})

        else:
            self.send_json({'error': 'not found'}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.cors()
        self.end_headers()

# ── START ──────────────────────────────────────────────────────────────────────
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('', PORT), Handler) as httpd:
    print(f'ComEd EESP System running on port {PORT}')
    httpd.serve_forever()
