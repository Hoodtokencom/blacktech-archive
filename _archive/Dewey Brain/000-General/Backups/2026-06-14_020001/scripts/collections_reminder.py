#!/usr/bin/env python3
"""
Blacktech Collections Auto-Reminder
Sends email reminders to customers with open balances.
Run via cron — safe to run daily, skips recently reminded customers.
"""

import sqlite3
import smtplib
import json
import os
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DB = '/home/allenai/data/blacktech_core.db'
LOG = '/home/allenai/data/collections_log.json'

# Load SMTP config
SMTP_CONFIG = '/home/allenai/data/smtp_config.json'
try:
    with open(SMTP_CONFIG) as f:
        smtp = json.load(f)
except:
    smtp = {}

SMTP_HOST = smtp.get('host', 'mail.blacktechsolutionscorp.com')
SMTP_PORT = smtp.get('port', 587)
SMTP_USER = smtp.get('user', 'payroll@blacktechsolutionscorp.com')
SMTP_PASS = smtp.get('password', '')
FROM_NAME = 'Blacktech Solutions Corp'
FROM_EMAIL = SMTP_USER
PORTAL_URL = 'https://app.blacktechsolutionscorp.com/portal'
PHONE = '(773) 754-8390'

def load_log():
    try:
        with open(LOG) as f:
            return json.load(f)
    except:
        return {}

def save_log(log):
    with open(LOG, 'w') as f:
        json.dump(log, f, indent=2)

def days_since_reminded(log, invoice_id):
    if invoice_id not in log:
        return 9999
    last = log[invoice_id].get('last_reminded')
    if not last:
        return 9999
    delta = datetime.datetime.now() - datetime.datetime.fromisoformat(last)
    return delta.days

def get_open_invoices():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    # Get all invoices with balance due, join best contact info
    cur.execute('''
        SELECT
            i.id as inv_id,
            i.invoice_number,
            i.total,
            i.amount_paid,
            i.total - i.amount_paid as balance,
            i.due_date,
            i.status,
            i.notes,
            c.name as customer_name,
            c.email,
            c.phone
        FROM invoices i
        JOIN contacts c ON i.contact_id = c.id
        WHERE (i.total - i.amount_paid) > 0
        AND i.status NOT IN ('paid', 'draft')
        ORDER BY i.due_date ASC
    ''')
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows

def days_overdue(due_date_str):
    if not due_date_str or due_date_str == '—':
        return 0
    try:
        # Handle both MM/DD/YYYY and YYYY-MM-DD
        for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S'):
            try:
                due = datetime.datetime.strptime(due_date_str.split('T')[0], fmt.split('T')[0])
                delta = datetime.datetime.now() - due
                return delta.days
            except:
                continue
    except:
        pass
    return 0

def reminder_subject(invoice_number, balance, overdue_days):
    if overdue_days > 30:
        return f'⚠️ FINAL NOTICE — Invoice {invoice_number} — ${balance:,.2f} Past Due'
    elif overdue_days > 0:
        return f'Reminder: Invoice {invoice_number} is {overdue_days} days past due'
    else:
        return f'Friendly Reminder: Invoice {invoice_number} — ${balance:,.2f} Due Soon'

def reminder_body(row, overdue_days):
    name = row['customer_name'].split('/')[0].strip()
    invoice_number = row['invoice_number'] or row['inv_id']
    balance = row['balance']
    due_date = row['due_date'] or 'on file'

    if overdue_days > 30:
        urgency = f"""
<p style="color:#c53030;font-weight:bold;font-size:16px;">
⚠️ This invoice is now {overdue_days} days past due. Immediate payment is required to avoid further action.
</p>"""
        cta = "Pay Immediately"
    elif overdue_days > 0:
        urgency = f"""
<p style="color:#dd6b20;font-weight:bold;">
This invoice was due on {due_date} and is now {overdue_days} days past due.
</p>"""
        cta = "Pay Now"
    else:
        urgency = f"""
<p style="color:#2d3748;">
Your invoice is due on <strong>{due_date}</strong>. This is a friendly reminder to ensure timely payment.
</p>"""
        cta = "View & Pay Invoice"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f7fafc;margin:0;padding:20px;">
<div style="max-width:560px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#002244,#003875);padding:28px 32px;text-align:center;">
    <div style="color:white;font-size:26px;font-weight:800;letter-spacing:1px;">BLACKTECH<span style="color:#FFD700;">⚡</span>SOLUTIONS</div>
    <div style="color:rgba(255,255,255,0.75);font-size:13px;margin-top:4px;">Professional Electrical Contractors · Chicago, IL</div>
  </div>

  <!-- Body -->
  <div style="padding:32px;">
    <p style="color:#2d3748;font-size:16px;margin-bottom:8px;">Hi {name},</p>
    <p style="color:#4a5568;margin-bottom:16px;">
      Thank you for choosing Blacktech Solutions. We're following up regarding the outstanding balance on your account.
    </p>

    <!-- Invoice Box -->
    <div style="background:#f7faff;border:1px solid #bee3f8;border-radius:10px;padding:20px;margin-bottom:20px;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <div>
          <div style="font-size:12px;color:#718096;text-transform:uppercase;letter-spacing:0.5px;">Invoice</div>
          <div style="font-size:18px;font-weight:700;color:#002244;">{invoice_number}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:12px;color:#718096;text-transform:uppercase;letter-spacing:0.5px;">Balance Due</div>
          <div style="font-size:24px;font-weight:800;color:#e53e3e;">${balance:,.2f}</div>
        </div>
      </div>
    </div>

    {urgency}

    <!-- CTA Button -->
    <div style="text-align:center;margin:24px 0;">
      <a href="{PORTAL_URL}" style="display:inline-block;background:linear-gradient(135deg,#002244,#003875);color:white;text-decoration:none;padding:14px 32px;border-radius:10px;font-size:15px;font-weight:700;">{cta} →</a>
    </div>

    <!-- Payment Methods -->
    <div style="background:#f0fff4;border:1px solid #9ae6b4;border-radius:8px;padding:16px;margin-bottom:20px;">
      <div style="font-size:13px;font-weight:700;color:#276749;margin-bottom:8px;">💳 Payment Options:</div>
      <div style="font-size:13px;color:#2f855a;line-height:1.7;">
        • <strong>Zelle:</strong> payroll@blacktechsolutionscorp.com<br>
        • <strong>Check:</strong> Payable to Blacktech Solutions Corp<br>
        • <strong>ACH:</strong> Routing 071026356 · Acct ****7765<br>
        • <strong>Cash:</strong> 10052 S Forest Ave, Chicago IL 60628
      </div>
    </div>

    <p style="color:#718096;font-size:13px;">
      Questions? Call or text us at <strong>{PHONE}</strong> or reply to this email.<br>
      Reference invoice <strong>{invoice_number}</strong> with your payment.
    </p>
  </div>

  <!-- Footer -->
  <div style="background:#f7fafc;padding:16px 32px;text-align:center;border-top:1px solid #e2e8f0;">
    <div style="font-size:12px;color:#a0aec0;">Blacktech Solutions Corp · EIN 82-3394717</div>
    <div style="font-size:12px;color:#a0aec0;">10052 S Forest Ave, Chicago IL 60628 · {PHONE}</div>
  </div>
</div>
</body>
</html>"""

def send_reminder(row, overdue_days, dry_run=False):
    email = (row.get('email') or '').strip()
    if not email or '@' not in email:
        return {'sent': False, 'reason': 'no_email', 'customer': row['customer_name']}

    invoice_number = row['invoice_number'] or row['inv_id']
    subject = reminder_subject(invoice_number, row['balance'], overdue_days)
    html = reminder_body(row, overdue_days)

    if dry_run:
        return {'sent': True, 'dry_run': True, 'to': email, 'subject': subject, 'customer': row['customer_name']}

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'{FROM_NAME} <{FROM_EMAIL}>'
    msg['To'] = email
    msg['Reply-To'] = FROM_EMAIL
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(FROM_EMAIL, [email], msg.as_string())
        return {'sent': True, 'to': email, 'subject': subject, 'customer': row['customer_name']}
    except Exception as e:
        return {'sent': False, 'reason': str(e), 'customer': row['customer_name']}

def main(dry_run=False, force=False):
    log = load_log()
    invoices = get_open_invoices()
    now = datetime.datetime.now().isoformat()
    results = []

    for row in invoices:
        inv_id = row['inv_id']
        overdue_days = days_overdue(row['due_date'])
        since_last = days_since_reminded(log, inv_id)

        # Reminder schedule:
        # Overdue >30 days: remind every 7 days
        # Overdue 1-30 days: remind every 14 days
        # Not yet due: remind once (7 days before due)
        if overdue_days > 30:
            remind_interval = 7
        elif overdue_days > 0:
            remind_interval = 14
        else:
            remind_interval = 9999  # only manual for not-yet-due

        should_remind = force or (since_last >= remind_interval)

        if not should_remind:
            results.append({
                'customer': row['customer_name'],
                'invoice': row['invoice_number'],
                'balance': row['balance'],
                'action': 'skipped',
                'reason': f'reminded {since_last}d ago (interval={remind_interval}d)'
            })
            continue

        result = send_reminder(row, overdue_days, dry_run=dry_run)
        result['invoice'] = row['invoice_number']
        result['balance'] = row['balance']
        result['overdue_days'] = overdue_days
        result['action'] = 'reminded'

        if result.get('sent') and not dry_run:
            log[inv_id] = {'last_reminded': now, 'count': log.get(inv_id, {}).get('count', 0) + 1}

        results.append(result)

    if not dry_run:
        save_log(log)

    return results

if __name__ == '__main__':
    import sys
    dry = '--dry' in sys.argv
    force = '--force' in sys.argv
    results = main(dry_run=dry, force=force)
    print(json.dumps(results, indent=2))
