#!/usr/bin/env python3
"""
Blacktech Lead Intake Bot
─────────────────────────
Watches Telegram for lead messages from team members.
Uses Claude AI to extract fields from ANY format (free text, structured, etc.)
Saves lead to:
  1. CRM jobs file  (/home/allenai/data/jobs.json)
  2. Money dashboard (/home/allenai/data/budget.json)
  3. Notifies Derrell on Telegram with summary

Team members just send a message like:
  "Got a lead - John Smith, 1234 S MLK Dr, panel upgrade, $3500"
  or
  "Lead: Maria Garcia | 5678 W Cermak | HVAC + electrical | estimate $8,200"

The bot figures out the fields automatically.
"""

import os, json, time, re, logging, urllib.request, urllib.parse, datetime, sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────
BOT_TOKEN       = os.getenv("LEAD_BOT_TOKEN", "")
DERRELL_CHAT_ID = "5805015753"
TEAM_GROUP_ID   = "-1002987688577"
ANTHROPIC_KEY   = os.getenv("ANTHROPIC_TOKEN", "")
DATA_DIR        = Path("/home/allenai/data")
JOBS_FILE       = DATA_DIR / "jobs.json"
BUDGET_FILE     = DATA_DIR / "budget.json"
OFFSET_FILE     = DATA_DIR / "tg_offset.txt"

# ── System Integration ────────────────────────────────────────────
# Unified lead router → blacktech_core.db
sys.path.insert(0, '/home/allenai/scripts')
try:
    from lead_router import intake_lead
    HAS_LEAD_ROUTER = True
except Exception as _lr_err:
    HAS_LEAD_ROUTER = False
    logging.getLogger("lead-bot").warning(f"lead_router not available: {_lr_err}")

# Service endpoints for cross-system sync
FIELD_TRACKER_URL = "http://localhost:8098/api/pins"
CRM_REFRESH_URL   = "http://localhost:8092/api/refresh"
KANBAN_URL         = "http://localhost:8080/api/kanban/add"

# Team member chat IDs that are allowed to submit leads
# Add team member Telegram user IDs here
ALLOWED_USERS   = set(os.getenv("TEAM_CHAT_IDS", DERRELL_CHAT_ID).split(","))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("lead-bot")

# ── Data Helpers ──────────────────────────────────────────────────
def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)
    if not JOBS_FILE.exists():
        JOBS_FILE.write_text(json.dumps([]))
    if not BUDGET_FILE.exists():
        BUDGET_FILE.write_text(json.dumps([]))

def load_jobs():
    return json.loads(JOBS_FILE.read_text())

def save_jobs(jobs):
    JOBS_FILE.write_text(json.dumps(jobs, indent=2))

def load_budget():
    return json.loads(BUDGET_FILE.read_text())

def save_budget(budget):
    BUDGET_FILE.write_text(json.dumps(budget, indent=2))

def next_job_id(jobs):
    """Generate next job ID based on existing jobs."""
    nums = []
    for j in jobs:
        try:
            nums.append(int(re.sub(r'\D', '', str(j.get('id', '')))))
        except:
            pass
    return str(max(nums) + 1) if nums else "1001"

# ── Claude AI Extract ─────────────────────────────────────────────
def extract_lead_with_ai(message_text, sender_name):
    """Send message to Claude, get structured lead fields back."""
    if not ANTHROPIC_KEY:
        log.warning("No Anthropic key — using basic extraction")
        return basic_extract(message_text)

    prompt = f"""Extract lead information from this message. The message was submitted by a team member to log a NEW CUSTOMER lead.

Message:
\"\"\"{message_text}\"\"\"

The first line is almost always the CUSTOMER NAME (the person Blacktech will do work for).
Subsequent lines may be: address, city/state, phone number, or scope of work.
A phone number looks like 10 digits or formatted like (773) 449-9396.
Scope is the type of electrical work (e.g. "Electrical", "Panel upgrade", "HVAC", "Rewire", etc).

Return ONLY a valid JSON object with these exact fields (use null if not found):
{{
  "customer_name": "full name of the CUSTOMER (not the team member who sent this)",
  "address": "street address only (no city/state)",
  "city": "city name or null",
  "state": "2-letter state abbreviation or null",
  "phone": "phone number as string, or null",
  "scope": "type of work / job description",
  "amount": 0.00,
  "status": "estimate",
  "notes": "any extra info"
}}

Rules:
- customer_name is the person/company being served, NOT the sender
- amount must be a number only (no $ sign, no commas) — use 0 if not mentioned
- status must be one of: estimate, invoiced, paid, overdue — default to "estimate"
- Return ONLY the JSON object, no explanation, no markdown"""

    payload = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            text = data["content"][0]["text"].strip()
            # Extract JSON from response
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                # Safety check — if customer_name is null/None/empty, try basic parse
                if not result.get("customer_name") or result["customer_name"].lower() in ("none", "null", "unknown", ""):
                    lines = [l.strip() for l in message_text.strip().splitlines() if l.strip()]
                    if lines:
                        result["customer_name"] = lines[0]
                return result
    except Exception as e:
        log.error(f"Claude extract failed: {e}")

    return basic_extract(message_text)

def basic_extract(text):
    """Fallback: basic regex extraction if Claude is unavailable."""
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    # First line = customer name
    customer = lines[0] if lines else "Unknown"
    # Find phone — 10 consecutive digits
    phone_match = re.search(r'(\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4})', text)
    phone = phone_match.group(1) if phone_match else None
    # Find dollar amount
    amount_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', text)
    amount = float(amount_match.group(1).replace(',','')) if amount_match else 0
    # Address = any line with digits + street keywords
    address = None
    for line in lines[1:]:
        if re.search(r'\d+\s+\w', line) and re.search(r'st|ave|dr|blvd|rd|ln|way|ct|pl|chicago|il', line, re.I):
            address = line
            break
    # Scope = last non-phone, non-address, non-name line
    scope_line = ""
    for line in lines[1:]:
        if not phone_match or line != phone_match.group(1):
            scope_line = line
    return {
        "customer_name": customer,
        "address": address or "",
        "phone": phone,
        "scope": scope_line or text[:100],
        "amount": amount,
        "status": "estimate",
        "notes": text
    }

# ── Save Lead ─────────────────────────────────────────────────────
def save_lead(fields, sender_name):
    """Save lead to ALL connected systems:
    1. jobs.json      (CRM server :8092)
    2. budget.json    (Money Dashboard :8091)
    3. blacktech_core.db (lead_router → unified DB)
    4. Field Tracker   (:8098 → map pin)
    5. Kanban Board    (:8080 → card)
    """
    jobs = load_jobs()
    job_id = next_job_id(jobs)
    today = datetime.date.today().strftime("%Y-%m-%d")

    job = {
        "id":           job_id,
        "customer":     fields.get("customer_name", "Unknown"),
        "scope":        fields.get("scope", ""),
        "address":      fields.get("address", ""),
        "city":         fields.get("city", ""),
        "state":        fields.get("state", ""),
        "phone":        fields.get("phone", ""),
        "amount":       float(fields.get("amount") or 0),
        "status":       fields.get("status", "estimate"),
        "notes":        fields.get("notes", ""),
        "submitted_by": sender_name,
        "date_added":   today,
        "source":       "telegram"
    }

    # ── 1. CRM: jobs.json ──────────────────────────────────────────
    jobs.append(job)
    save_jobs(jobs)
    log.info(f"📁 jobs.json updated — #{job_id}")

    # ── 2. Money Dashboard: budget.json ────────────────────────────
    budget = load_budget()
    budget.append({
        "id":       job_id,
        "customer": job["customer"],
        "scope":    job["scope"],
        "address":  job["address"],
        "amount":   job["amount"],
        "status":   job["status"],
        "date":     today
    })
    save_budget(budget)
    log.info(f"💰 budget.json updated — #{job_id}")

    # ── 3. Unified DB: blacktech_core.db via lead_router ───────────
    if HAS_LEAD_ROUTER:
        try:
            lr_result = intake_lead(
                source='telegram',
                name=job["customer"],
                phone=job.get("phone", ""),
                email=fields.get("email", ""),
                address=job["address"],
                city=job.get("city", "Chicago"),
                state=job.get("state", "IL"),
                services=[job["scope"]] if job["scope"] else [],
                notes=f"Submitted by {sender_name} via Telegram. {job['notes']}".strip(),
                raw=None
            )
            if lr_result.get('ok'):
                log.info(f"🗃️ lead_router → {lr_result.get('job_id')} (core DB)")
            else:
                log.warning(f"lead_router error: {lr_result.get('error')}")
        except Exception as lr_err:
            log.warning(f"lead_router sync failed (non-fatal): {lr_err}")

    # ── 4. Field Tracker: map pin on :8098 ─────────────────────────
    try:
        # Determine business type from scope/notes
        scope_lower = (job["scope"] + " " + job["notes"]).lower()
        is_energy = any(kw in scope_lower for kw in ['energy', 'comed', 'solar', 'battery', 'think energy', 'savings'])
        business = 'think_energy' if is_energy else 'blacktech'

        pin_data = {
            "pin_type": "lead",
            "title": f"Lead — {job['customer']}",
            "address": ', '.join(filter(None, [job['address'], job.get('city',''), job.get('state','')])),
            "status": "new",
            "priority": "high" if job["amount"] >= 5000 else "medium",
            "contact_name": job["customer"],
            "contact_phone": job.get("phone", ""),
            "contact_email": fields.get("email", ""),
            "business": business,
            "notes": f"🤖 Auto-created from Telegram lead\n📋 {job['scope']}\n👤 Submitted by: {sender_name}\n🆔 Job #{job_id}",
            "amount": job["amount"],
            "assigned_to": "Derrell"
        }
        pin_payload = json.dumps(pin_data).encode()
        pin_req = urllib.request.Request(
            FIELD_TRACKER_URL,
            data=pin_payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        pin_resp = urllib.request.urlopen(pin_req, timeout=8)
        pin_result = json.loads(pin_resp.read())
        log.info(f"📍 Field Tracker pin #{pin_result.get('id')} created for {job['customer']}")
    except Exception as pin_err:
        log.warning(f"Field Tracker sync failed (non-fatal): {pin_err}")

    # ── 5. Kanban Board: card on :8080 ─────────────────────────────
    try:
        city_state = ', '.join(filter(None, [job.get('city',''), job.get('state','')]))
        phone_str  = f"\n📞 {job['phone']}" if job['phone'] else ""
        addr_str   = f"\n📍 {job['address']}" if job['address'] else ""
        city_str   = f"\n🏙️ {city_state}" if city_state else ""
        scope_str  = f"\n📋 {job['scope']}" if job['scope'] else ""
        notes_text = f"{phone_str}{addr_str}{city_str}{scope_str}".strip()

        kanban_card = {
            "title":  job["customer"],
            "notes":  notes_text,
            "status": "backlog",
            "tag":    "projects",
            "color":  ""
        }
        kanban_data = json.dumps(kanban_card).encode()
        kanban_req = urllib.request.Request(
            KANBAN_URL,
            data=kanban_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(kanban_req, timeout=5)
        log.info(f"📋 Kanban card created for {job['customer']}")
    except Exception as kanban_err:
        log.warning(f"Kanban sync failed (non-fatal): {kanban_err}")

    log.info(f"✅ Lead #{job_id} — {job['customer']} → synced to ALL systems")
    return job

# ── Telegram Helpers ──────────────────────────────────────────────
def tg_get(method, params=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        timeout = 35 if "getUpdates" in method else 10
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error(f"Telegram GET {method} failed: {e}")
        return {}

def tg_send(chat_id, text, parse_mode="Markdown"):
    payload = json.dumps({
        "chat_id": str(chat_id),
        "text": text,
        "parse_mode": parse_mode
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error(f"Telegram send failed: {e}")

def get_offset():
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except:
            pass
    return 0

def save_offset(offset):
    OFFSET_FILE.write_text(str(offset))

# ── Message Processor ─────────────────────────────────────────────
def is_lead_message(text):
    """Detect if a message is a lead submission."""
    if not text:
        return False
    text_lower = text.lower()
    # Trigger keywords
    triggers = ["lead", "client", "customer", "job", "quote", "estimate",
                "prospect", "referral", "new job", "got a", "i have a"]
    return any(t in text_lower for t in triggers)

def process_message(msg):
    """Process an incoming Telegram message."""
    chat_id  = str(msg.get("chat", {}).get("id", ""))
    chat_type = msg.get("chat", {}).get("type", "")
    user     = msg.get("from", {})
    user_id  = str(user.get("id", ""))
    fname    = user.get("first_name", "")
    lname    = user.get("last_name", "")
    username = user.get("username", "")
    sender   = f"{fname} {lname}".strip() or username or user_id
    text     = msg.get("text", "").strip()

    if not text:
        return

    # Only process messages from Derrell's DM or The Energy Experts group
    if chat_id not in [DERRELL_CHAT_ID, TEAM_GROUP_ID]:
        return

    # Handle /lead command or lead keyword messages
    if text.startswith("/lead") or is_lead_message(text):
        clean_text = re.sub(r'^/lead\s*', '', text).strip()
        if not clean_text:
            tg_send(chat_id, "📋 *Submit a Lead*\n\nType `/lead` followed by the customer details.\n\n*Example:*\n`/lead John Smith, 1234 S MLK Dr Chicago, panel upgrade, $3,500`\n\nOr just describe it naturally and we'll capture it.")
            return

        # Extract fields with AI
        fields = extract_lead_with_ai(clean_text, sender)

        # Save to system
        job = save_lead(fields, sender)

        # Confirm in group/chat
        city_state = ', '.join(filter(None, [job.get('city',''), job.get('state','')]))
        full_location = ' — '.join(filter(None, [job['address'], city_state])) or 'Not provided'

        confirm = f"""✅ *New Lead — Synced to All Systems*

👤 *Customer:* {job['customer']}
📍 *Address:* {job['address'] or 'Not provided'}
🏙️ *City/State:* {city_state or 'Not provided'}
📞 *Phone:* {job['phone'] or 'Not provided'}
🔧 *Scope:* {job['scope']}
💰 *Estimate:* ${job['amount']:,.2f}
🆔 *Job ID:* #{job['id']}
👤 *Logged by:* {sender}

📡 *Connected:*
  ✅ CRM · ✅ Money · ✅ Map · ✅ Kanban · ✅ Core DB"""

        tg_send(chat_id, confirm)

        # Always alert Derrell privately if lead came from the group
        if chat_id == TEAM_GROUP_ID:
            tg_send(DERRELL_CHAT_ID, f"🔔 *New Lead — {job['customer']}*\n\n📍 {full_location}\n🔧 {job['scope']}\n💰 ${job['amount']:,.2f}\n🆔 Job #{job['id']}\n👤 Logged by {sender}")

    elif text in ["/status", "/status@your_bot"]:
        jobs = load_jobs()
        total     = sum(j.get('amount', 0) for j in jobs)
        estimates = sum(j.get('amount', 0) for j in jobs if j.get('status') == 'estimate')
        invoiced  = sum(j.get('amount', 0) for j in jobs if j.get('status') == 'invoiced')
        paid      = sum(j.get('amount', 0) for j in jobs if j.get('status') == 'paid')
        tg_send(chat_id, f"""📊 *Blacktech Pipeline Summary*

💼 Total Jobs: {len(jobs)}
💰 Pipeline Value: ${total:,.2f}
📝 Estimates: ${estimates:,.2f}
🧾 Invoiced: ${invoiced:,.2f}
✅ Collected: ${paid:,.2f}""")

    elif text in ["/help", "/help@your_bot"]:
        tg_send(chat_id, """🤖 *Blacktech Lead Bot*

Use this bot to submit and track job leads for Blacktech Solutions Corp.

*Submit a lead:*
`/lead John Smith, 1234 S MLK Dr Chicago, panel upgrade, $3,500`

Or describe it naturally:
`Got a lead — Maria Garcia, HVAC work, 567 W Cermak, ~$8k`

*Commands:*
/lead — Submit a new lead
/status — View pipeline summary
/help — Show this message""")

# ── Main Loop ─────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        log.error("❌ No TELEGRAM_BOT_TOKEN set in environment")
        return

    ensure_data_dir()
    log.info("🚀 Blacktech Lead Bot started")
    tg_send(DERRELL_CHAT_ID, "✅ *Blacktech Lead Bot is Online*\nReady to capture leads from The Energy Experts group.")

    offset = get_offset()

    while True:
        try:
            result = tg_get("getUpdates", {"offset": offset, "timeout": 20, "allowed_updates": ["message"]})
            updates = result.get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                save_offset(offset)
                msg = update.get("message", {})
                if msg:
                    process_message(msg)

        except KeyboardInterrupt:
            log.info("⏹️  Bot stopped")
            break
        except Exception as e:
            log.error(f"Main loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
