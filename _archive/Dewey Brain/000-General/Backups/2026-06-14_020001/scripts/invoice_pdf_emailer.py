#!/usr/bin/env python3
"""
Blacktech Invoice PDF Generator + Emailer
Usage: python3 invoice_pdf_emailer.py <invoice_id> [--email]
"""
import sys, os, sqlite3, smtplib, json, uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

DB_PATH   = '/home/allenai/data/blacktech_core.db'
PDF_DIR   = '/home/allenai/data/invoices_pdf'
SMTP_HOST = 'mail.blacktechsolutionscorp.com'
SMTP_PORT = 465
SMTP_USER = 'support@blacktechsolutionscorp.com'
SMTP_PASS = 'Newproject26$'
FROM_EMAIL = 'invoices@blacktechsolutionscorp.com'
FROM_NAME  = 'Blacktech Solutions Corp'

os.makedirs(PDF_DIR, exist_ok=True)

# ── Fetch invoice data ──────────────────────────────────────────
def get_invoice(invoice_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inv = conn.execute("""
        SELECT i.*, c.name as contact_name, c.email as contact_email,
               c.phone as contact_phone, c.address as contact_address,
               c.city as contact_city, c.state as contact_state, c.zip as contact_zip
        FROM invoices i
        LEFT JOIN contacts c ON i.contact_id = c.id
        WHERE i.id=? OR i.invoice_number=?
    """, (invoice_id, invoice_id)).fetchone()
    if not inv:
        conn.close()
        return None, []
    lines = conn.execute("""
        SELECT * FROM invoice_lines WHERE invoice_id=? ORDER BY category, id
    """, (inv['id'],)).fetchall()
    conn.close()
    return dict(inv), [dict(l) for l in lines]

# ── Build HTML for PDF ──────────────────────────────────────────
def build_html(inv, lines):
    paid    = float(inv.get('amount_paid') or 0)
    total   = float(inv.get('total') or 0)
    balance = total - paid
    status_color = '#00c853' if balance <= 0 else '#ff6f00' if paid > 0 else '#d32f2f'
    status_label = 'PAID IN FULL' if balance <= 0 else 'PARTIAL PAYMENT' if paid > 0 else 'PAYMENT DUE'

    labor_lines = [l for l in lines if l.get('category') == 'electrical']
    mat_lines   = [l for l in lines if l.get('category') == 'materials']
    other_lines = [l for l in lines if l.get('category') not in ('electrical','materials')]

    def rows(items):
        html = ''
        for l in items:
            amt = float(l.get('amount') or 0)
            qty = float(l.get('qty') or 1)
            rate = float(l.get('rate') or 0)
            html += f"""
            <tr>
              <td style="padding:8px 10px;border-bottom:1px solid #f0f0f0;">{l.get('description','')}</td>
              <td style="padding:8px 10px;border-bottom:1px solid #f0f0f0;text-align:center;">{int(qty) if qty==int(qty) else qty}</td>
              <td style="padding:8px 10px;border-bottom:1px solid #f0f0f0;text-align:right;">${rate:,.2f}</td>
              <td style="padding:8px 10px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;">${amt:,.2f}</td>
            </tr>"""
        return html

    labor_total = sum(float(l.get('amount',0)) for l in labor_lines)
    mat_total   = sum(float(l.get('amount',0)) for l in mat_lines)
    other_total = sum(float(l.get('amount',0)) for l in other_lines)

    addr = ', '.join(filter(None, [
        inv.get('contact_address',''),
        inv.get('contact_city',''),
        inv.get('contact_state',''),
        inv.get('contact_zip','')
    ]))

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; font-size: 13px; color: #1a1a1a; margin: 0; padding: 0; }}
  .page {{ padding: 40px 48px; max-width: 800px; margin: 0 auto; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; border-bottom: 3px solid #1565c0; padding-bottom: 20px; }}
  .company-name {{ font-size: 22px; font-weight: 900; color: #1565c0; letter-spacing: 1px; }}
  .company-sub {{ font-size: 11px; color: #666; margin-top: 3px; }}
  .inv-title {{ font-size: 28px; font-weight: 900; color: #1565c0; text-align: right; }}
  .inv-meta {{ text-align: right; font-size: 12px; color: #555; margin-top: 4px; }}
  .billing {{ display: flex; justify-content: space-between; margin-bottom: 28px; }}
  .billing-block {{ }}
  .billing-label {{ font-size: 10px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
  .billing-name {{ font-size: 14px; font-weight: 700; color: #1a1a1a; }}
  .billing-detail {{ font-size: 12px; color: #555; line-height: 1.6; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
  thead tr {{ background: #1565c0; color: white; }}
  thead th {{ padding: 10px; text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
  thead th:last-child, thead th:nth-child(3) {{ text-align: right; }}
  thead th:nth-child(2) {{ text-align: center; }}
  .section-header td {{ background: #e3f2fd; font-weight: 700; color: #1565c0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; padding: 6px 10px; }}
  .totals {{ float: right; width: 280px; margin-top: 10px; }}
  .totals table {{ margin: 0; }}
  .totals td {{ padding: 6px 10px; font-size: 13px; }}
  .totals .label {{ color: #555; }}
  .totals .total-row td {{ font-size: 16px; font-weight: 900; color: #1565c0; border-top: 2px solid #1565c0; padding-top: 10px; }}
  .totals .balance-row td {{ font-size: 15px; font-weight: 900; color: {status_color}; }}
  .status-badge {{ display: inline-block; background: {status_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
  .footer {{ margin-top: 48px; border-top: 1px solid #eee; padding-top: 16px; font-size: 11px; color: #999; text-align: center; }}
  .thank-you {{ font-size: 15px; font-weight: 700; color: #1565c0; text-align: center; margin: 24px 0 8px; }}
</style>
</head>
<body><div class="page">

  <!-- Header -->
  <div class="header">
    <div>
      <div class="company-name">⚡ BLACKTECH SOLUTIONS CORP</div>
      <div class="company-sub">Licensed Electrical Contractor · Chicago, IL</div>
      <div class="company-sub">10052 S Forest Ave, Chicago, IL 60628</div>
      <div class="company-sub">payroll@blacktechsolutionscorp.com</div>
    </div>
    <div>
      <div class="inv-title">INVOICE</div>
      <div class="inv-meta"><strong>{inv.get('invoice_number','—')}</strong></div>
      <div class="inv-meta">Issued: {inv.get('issue_date','—')}</div>
      <div class="inv-meta">Due: {inv.get('due_date','—')}</div>
      <div style="margin-top:8px;text-align:right;"><span class="status-badge">{status_label}</span></div>
    </div>
  </div>

  <!-- Billing -->
  <div class="billing">
    <div class="billing-block">
      <div class="billing-label">Bill To</div>
      <div class="billing-name">{inv.get('contact_name','—')}</div>
      <div class="billing-detail">{addr or '—'}</div>
      {'<div class="billing-detail">' + (inv.get('contact_phone') or '') + '</div>' if inv.get('contact_phone') else ''}
      {'<div class="billing-detail">' + (inv.get('contact_email') or '') + '</div>' if inv.get('contact_email') else ''}
    </div>
    <div class="billing-block" style="text-align:right;">
      <div class="billing-label">From</div>
      <div class="billing-name">Blacktech Solutions Corp</div>
      <div class="billing-detail">Derrell A Black, Owner</div>
      <div class="billing-detail">EIN: 82-3394717</div>
    </div>
  </div>

  <!-- Line Items -->
  <table>
    <thead>
      <tr>
        <th style="width:50%">Description</th>
        <th style="width:10%">Qty</th>
        <th style="width:18%">Rate</th>
        <th style="width:18%">Amount</th>
      </tr>
    </thead>
    <tbody>
      {'<tr class="section-header"><td colspan="4">Labor</td></tr>' if labor_lines else ''}
      {rows(labor_lines)}
      {'<tr class="section-header"><td colspan="4">Materials &amp; Supplies</td></tr>' if mat_lines else ''}
      {rows(mat_lines)}
      {'<tr class="section-header"><td colspan="4">Other</td></tr>' if other_lines else ''}
      {rows(other_lines)}
    </tbody>
  </table>

  <!-- Totals -->
  <div class="totals">
    <table>
      {f'<tr><td class="label">Labor</td><td style="text-align:right;">${labor_total:,.2f}</td></tr>' if labor_lines else ''}
      {f'<tr><td class="label">Materials</td><td style="text-align:right;">${mat_total:,.2f}</td></tr>' if mat_lines else ''}
      <tr class="total-row"><td>TOTAL</td><td style="text-align:right;">${total:,.2f}</td></tr>
      {f'<tr><td class="label" style="color:#00c853;">Amount Paid</td><td style="text-align:right;color:#00c853;">(${paid:,.2f})</td></tr>' if paid > 0 else ''}
      {'<tr class="balance-row"><td>BALANCE DUE</td><td style="text-align:right;">${:,.2f}</td></tr>'.format(max(0,balance)) if balance > 0 else ''}
    </table>
  </div>
  <div style="clear:both;"></div>

  <!-- Payment info -->
  <div style="margin-top:28px;background:#f8f9fa;border-left:4px solid #1565c0;padding:12px 16px;border-radius:4px;font-size:12px;">
    <strong>Payment Methods:</strong> Cash · Check (payable to Blacktech Solutions Corp) · Zelle: payroll@blacktechsolutionscorp.com · ACH: Routing 071026356 · Acct *7765
  </div>

  <div class="thank-you">Thank you for your business! 🙏</div>
  <div class="footer">Blacktech Solutions Corp · 10052 S Forest Ave, Chicago IL 60628 · EIN: 82-3394717<br>
  Questions? Email invoices@blacktechsolutionscorp.com</div>

</div></body></html>"""

# ── Generate PDF ────────────────────────────────────────────────
def generate_pdf(invoice_id):
    inv, lines = get_invoice(invoice_id)
    if not inv:
        return None, f"Invoice {invoice_id} not found"
    html = build_html(inv, lines)
    pdf_name = f"Blacktech_Invoice_{inv['invoice_number'].replace('/','_').replace(' ','_')}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    try:
        import weasyprint
        weasyprint.HTML(string=html).write_pdf(pdf_path)
        return pdf_path, inv
    except Exception as e:
        return None, str(e)

# ── Send Email ──────────────────────────────────────────────────
def send_invoice_email(invoice_id):
    pdf_path, inv = generate_pdf(invoice_id)
    if not pdf_path:
        return {"success": False, "error": inv}  # inv is error string here

    to_email = inv.get('contact_email','').strip()
    if not to_email:
        return {"success": False, "error": "No email address on file for this customer"}

    total   = float(inv.get('total') or 0)
    balance = total - float(inv.get('amount_paid') or 0)
    inv_num = inv.get('invoice_number','—')
    name    = inv.get('contact_name','Valued Customer')
    due     = inv.get('due_date','—')

    msg = MIMEMultipart()
    msg['From']    = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg['To']      = to_email
    msg['Subject'] = f"Invoice {inv_num} from Blacktech Solutions Corp — ${balance:,.2f} Due"

    body = f"""Hello {name},

Please find attached Invoice {inv_num} from Blacktech Solutions Corp.

Invoice Total: ${total:,.2f}
Amount Paid:   ${float(inv.get('amount_paid') or 0):,.2f}
Balance Due:   ${max(0,balance):,.2f}
Due Date:      {due}

Payment Methods:
  • Cash or Check (payable to Blacktech Solutions Corp)
  • Zelle: payroll@blacktechsolutionscorp.com
  • ACH: Routing 071026356, Account *7765

Thank you for choosing Blacktech Solutions Corp for your electrical needs.
If you have any questions, please reply to this email.

Best regards,
Derrell A Black
Owner, Blacktech Solutions Corp
payroll@blacktechsolutionscorp.com
"""
    msg.attach(MIMEText(body, 'plain'))

    # Attach PDF
    with open(pdf_path, 'rb') as f:
        part = MIMEApplication(f.read(), _subtype='pdf')
        part.add_header('Content-Disposition', 'attachment',
                        filename=os.path.basename(pdf_path))
        msg.attach(part)

    try:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        server.quit()
        return {"success": True, "to": to_email, "pdf": pdf_path, "invoice": inv_num}
    except Exception as e:
        return {"success": False, "error": str(e), "pdf": pdf_path}

# ── CLI ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 invoice_pdf_emailer.py <invoice_id> [--email]")
        sys.exit(1)
    invoice_id = sys.argv[1]
    do_email   = '--email' in sys.argv
    if do_email:
        result = send_invoice_email(invoice_id)
        print(json.dumps(result, indent=2))
    else:
        pdf_path, inv = generate_pdf(invoice_id)
        if pdf_path:
            print(json.dumps({"success": True, "pdf": pdf_path, "invoice": inv.get('invoice_number')}))
        else:
            print(json.dumps({"success": False, "error": inv}))
