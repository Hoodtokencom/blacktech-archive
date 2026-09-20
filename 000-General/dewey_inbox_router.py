#!/usr/bin/env python3
"""
Dewey Inbox Router — Two-tier classification + 3-way mirror sync.
===============================================================
Tier 1: Keyword prefix matching (fast, free, reliable)
Tier 2: AI classification fallback (for unmatched files only)

After routing, triggers dewey_sync.py for full 3-mirror sync
(Brain → Google Drive, Body → Internal, Archive → GitHub).

Usage:
  python3 dewey_inbox_router.py              — Route all inbox files
  python3 dewey_inbox_router.py --dry-run    — Preview, no moves
  python3 dewey_inbox_router.py --status     — Show inbox contents
  python3 dewey_inbox_router.py --no-sync    — Route but skip mirror sync
  python3 dewey_inbox_router.py --no-ai      — Keyword only, skip AI fallback
"""

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

# ── Real Pi paths ─────────────────────────────────────────────────
INBOX_DIR = "/home/allenai/blacktech_inbox"
BODY_DIR = "/home/allenai/blacktech_brain"
SYNC_SCRIPT = os.path.join(BODY_DIR, "000-General", "dewey_sync.py")
BLOCKCHAIN = f"python3 {BODY_DIR}/000-General/dewey_blockchain.py"

# ── AI fallback config (local Ollama) ──────────────────────────────
AI_ENABLED = True          # Set False to disable AI fallback entirely
AI_BASE_URL = "http://localhost:11434/v1"
AI_MODEL = "bt-worker:latest"  # qwen2.5:3b — deepseek-r1:7b NOT installed (404); qwen3 empty via /v1 (think ignored)
AI_TIMEOUT = 90               # Cold Ollama model load can take 60s+; 30s caused false "timed out"

# ── Tier 1: Keyword → Dewey section mapping ────────────────────────
# Matched by word-boundary prefix (e.g., "est_" → 692, "contract-" → 690)
DEWEY_MAP = {
    "est":      "692-Auxiliary_Practices",   # Estimates, bids, proposals
    "contract": "690-Building_Construction",  # Contracts
    "elec":     "696-Utilities",              # Electrical work docs
    "hvac":     "697-HVAC",                   # Heating/cooling docs
    "mat":      "691-Building_Materials",     # Material lists, parts
    "inv":      "657-Accounting_Finance",     # Invoices
    "payroll":  "657-Accounting_Finance",     # Payroll docs
    "proposal": "692-Auxiliary_Practices",    # Proposals (same as estimates)
    "bid":      "692-Auxiliary_Practices",    # Bids
    "spec":     "692-Auxiliary_Practices",    # Specifications
    "panel":    "696-Utilities",              # Panel schedules
    "wiring":   "696-Utilities",              # Wiring diagrams
    "duct":     "697-HVAC",                   # Ductwork
    "boiler":   "697-HVAC",                   # Boiler docs
    "chiller":  "697-HVAC",                   # Chiller docs
    "supplier": "691-Building_Materials",     # Supplier lists
    "catalog":  "691-Building_Materials",     # Parts catalogs
    "receipt":  "657-Accounting_Finance",     # Receipts
    "ledger":   "657-Accounting_Finance",     # Ledgers
    "religion": "200-Religion",                # Faith/ministry docs
    "faith":    "200-Religion",                # Faith/ministry docs
    "sermon":   "200-Religion",                # Sermons, teaching notes
    "scripture":"200-Religion",                # Scripture study
    "ministry": "200-Religion",                # Ministry program docs
}

# ── Tier 1.5: Content markers (deterministic, before the AI guess) ──
# The 3B local model misroutes fuzzy topics (e.g. tithing -> 100). These
# high-precision markers short-circuit it when the FILENAME gave no clue.
# Order matters: first pattern that hits wins.
CONTENT_MAP = [
    ("200-Religion", r"\b(tith(e|es|ing)|stewardship|sermons?|scriptures?|"
                     r"parables?|worship|prayer|congregation|ministry|"
                     r"bible|gospel|blessing|faith)\b"),
    ("697-HVAC",     r"\b(hvac|furnace|chiller|boiler|thermostat|ductwork|"
                     r"air condition\w*|refrigerant|condenser|heat pump)\b"),
    ("696-Utilities",r"\b(comed|utilit(y|ies)|kwh|kilowatt|electric bill|"
                     r"smart meter|auto[- ]?save|supply charge|delivery charge)\b"),
    ("692-Auxiliary_Practices",
                     r"\b(statement of work|estimates?|bids?|proposals?|"
                     r"scope of work|change order)\b"),
    ("657-Accounting_Finance",
                     r"\b(invoices?|payroll|receipts?|ledgers?|1099|w-9|"
                     r"profit (and|&) loss|balance sheet)\b"),
    ("691-Building_Materials",
                     r"\b(vendor list|supplier list|parts catalog|"
                     r"material list|bill of materials)\b"),
    # ── Below: sections the flat 3-digit codes can't express ──
    # (the AI prompt + dewey_to_folder() only know 3-digit codes, so these
    #  subfolders were unreachable until CONTENT_MAP named them.)
    ("003-Computing_Science",
                     r"\b(server|hostgator|nginx|cron|systemd|ssh|git repo|"
                     r"api key|docker|vm|backup script|firewall|dns)\b"),
    ("650-Management_Business",
                     r"\b(management|operations|kpi|org chart|hiring|onboarding|"
                     r"job description|performance review|strateg(y|ies)|"
                     r"standard operating procedure|sop)\b"),
    ("658-Marketing_Sales",
                     r"\b(marketing|sales funnel|lead gen|ad campaign|branding|"
                     r"social media post|seo|customer acquisition|pitch deck)\b"),
    ("600-Wealth_Precious_Metals",
                     r"\b(silver|gold bullion|precious metal|bullion|"
                     r"coin dealer|troy ounce|spot price|melt value)\b"),
    ("620-ComEd_Standard_Offering",
                     r"\b(standard offering|rate class|capacity charge|"
                     r"residential supply rate|electricity procurement)\b"),
    ("910-Regional_Data",
                     r"\b(census|zip code|zIP[- ]?\d|demographic|population|"
                     r"regional data|market data by (city|state|zip))\b"),
    # ── Broad topics LAST — specific markers above must win ──
    ("600-Technology",
                     r"\b(software|hardware|raspberry pi|ollama|llm|ai model|"
                     r"python script|database|networking|automation|"
                     r"blockchain|ipfs|codebase)\b"),
    ("300-Social_Sciences",
                     r"\b(community|nonprofit|law|legal|policy|government|"
                     r"civic|outreach|volunteer|ssbn|member|tenant rights)\b"),
]

# ── Tier 2: AI classification prompt ───────────────────────────────
AI_CLASSIFY_PROMPT = """You are the Blacktech Dewey Decimal classifier.
Analyze this file content and return ONLY the 3-digit Dewey code.

Available codes:
  000 - General, uncategorized, miscellaneous notes that fit nothing else
  003 - Computing: servers, hosting, scripts, networking, backups
  100 - Philosophy, mindset, leadership
  200 - Religion, faith
  300 - Social sciences, law, community, SSBN
  400 - Language, templates, brand voice
  500 - Science, math, systems architecture, schematics
  600 - Technology, software, hardware, Pi infrastructure
  601 - Wealth: silver, gold, precious metals, bullion
  620 - ComEd standard offering, rate classes, procurement
  640 - Household favorites
  650 - Management: operations, KPIs, hiring, SOPs
  657 - Accounting, payroll, invoices, passcodes
  658 - Marketing, sales, funnels, branding, lead gen
  690 - Construction contracts, approvals
  691 - Building materials, supplier catalogs
  692 - Estimates, bids, proposals, specs
  696 - Utilities, electrical work
  697 - HVAC, heating, cooling, ventilation
  700 - Arts, design, music
  800 - Literature, blogs, articles
  900 - History, project timelines
  910 - Regional data: census, zip codes, demographics
  999 - Decisions log, change history

Respond with ONLY the 3-digit number. No explanation.

Content:
\"\"\"
{content}
\"\"\""""

# ── Helpers ────────────────────────────────────────────────────────

def file_hash(path):
    """SHA256 of file contents."""
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def log_blockchain(action, filepath, section, trigger="inbox-router"):
    """Log a CREATE block to the Dewey blockchain."""
    cmd = f'{BLOCKCHAIN} log {action} "{filepath}" --section "{section}" --trigger {trigger}'
    try:
        subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
    except Exception as e:
        print(f"  ⚠ Blockchain log failed (non-fatal): {e}")

def log_change(message):
    """Append a human-readable note to the change history log."""
    log_path = os.path.join(BODY_DIR, "999-Decisions_Logs", "change_history.md")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as log_file:
        log_file.write(f"- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def match_keyword(filename):
    """
    Tier 1: Match filename to Dewey section via keyword prefix.
    Keyword must appear at a word boundary (start, underscore, or hyphen).
    Returns (dewey_number, section_folder, matched_keyword) or (None, None, None).
    """
    lower = os.path.splitext(filename.lower())[0]

    for keyword, folder in DEWEY_MAP.items():
        pattern = rf'(^|[-_]){re.escape(keyword)}([-_]|$)'
        if re.search(pattern, lower):
            dewey_num = folder.split("-")[0]
            return dewey_num, folder, keyword

    return None, None, None

def match_content(file_path):
    """
    Tier 1.5: Deterministic content-marker match (no AI).
    Used only when the FILENAME gave no keyword clue. High-precision terms
    beat the 3B model, which misroutes fuzzy topics (tithing -> 100).
    Returns (dewey_number, section_folder, marker) or (None, None, None).
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3',
               '.xlsx', '.docx', '.zip', '.gz', '.enc', '.salt', '.db'}:
        return None, None, None
    try:
        with open(file_path, 'r', errors='ignore') as f:
            head = f.read(3000).lower()
    except Exception:
        return None, None, None
    if not head.strip():
        return None, None, None

    for folder, pattern in CONTENT_MAP:
        m = re.search(pattern, head, re.IGNORECASE)
        if m:
            return folder.split("-")[0], folder, m.group(0)
    return None, None, None

def ai_classify_file(file_path):
    """
    Tier 2: Ask local Ollama to classify an unmatched file.
    Reads first 1500 chars of text files; skips binary files.
    Returns Dewey number string or None on failure.
    """
    if not AI_ENABLED:
        return None

    # Skip binary files — AI can't read them
    ext = os.path.splitext(file_path)[1].lower()
    binary_exts = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3',
                   '.xlsx', '.docx', '.zip', '.gz', '.enc', '.salt', '.db'}
    if ext in binary_exts:
        print(f"  ⚠ Binary file ({ext}) — AI classification skipped")
        return None

    # Read first 1500 chars
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read(1500)
    except Exception as e:
        print(f"  ⚠ Cannot read file for AI: {e}")
        return None

    if not content.strip():
        print(f"  ⚠ Empty file — AI classification skipped")
        return None

    prompt = AI_CLASSIFY_PROMPT.format(content=content)

    try:
        # Use requests directly to avoid openai dependency
        import json, urllib.request

        body = json.dumps({
            "model": AI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "stream": False
        }).encode()

        req = urllib.request.Request(
            f"{AI_BASE_URL}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=AI_TIMEOUT) as resp:
            result = json.loads(resp.read())

        raw = result["choices"][0]["message"]["content"].strip()

        # Extract 3-digit code from response
        match = re.search(r'\b(000|100|200|300|400|500|600|640|657|'
                          r'690|691|692|696|697|700|800|900|999)\b', raw)
        if match:
            return match.group(0)
        else:
            print(f"  ⚠ AI returned unparseable response: '{raw[:80]}...'")
            return None

    except Exception as e:
        print(f"  ⚠ AI classification failed: {e}")
        return None

def dewey_to_folder(dewey_code):
    """Map a Dewey number to the actual folder name in BODY_DIR."""
    mapping = {
        "000": "000-General",
        "003": "003-Computing_Science",
        "100": "100-Philosophy",
        "200": "200-Religion",
        "300": "300-Social_Sciences",
        "400": "400-Language",
        "500": "500-Science",
        "600": "600-Technology",
        "601": "600-Wealth_Precious_Metals",
        "620": "620-ComEd_Standard_Offering",
        "640": "640-Household_Favorites",
        "650": "650-Management_Business",
        "657": "657-Accounting_Finance",
        "658": "658-Marketing_Sales",
        "690": "690-Building_Construction",
        "691": "691-Building_Materials",
        "692": "692-Auxiliary_Practices",
        "696": "696-Utilities",
        "697": "697-HVAC",
        "700": "700-Arts_Recreation",
        "800": "800-Literature",
        "900": "900-History_Geography",
        "910": "910-Regional_Data",
        "999": "999-Decisions_Logs",
    }
    # Accept a full folder name too (CONTENT_MAP returns folder names).
    if dewey_code in mapping.values():
        return dewey_code
    return mapping.get(dewey_code, "000-General")

def sync_mirrors():
    """Call dewey_sync.py for full 3-way mirror sync."""
    print(f"\n🔄 Triggering 3-Way Mirror Sync...")
    try:
        result = subprocess.run(
            ["python3", SYNC_SCRIPT],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print("✅ Mirror sync complete.")
            # Print summary lines
            for line in result.stdout.splitlines():
                if "Sync complete" in line or "uploaded" in line or "pushed" in line:
                    print(f"   {line.strip()}")
        else:
            print(f"⚠ Mirror sync exited with code {result.returncode}")
            if result.stderr:
                print(f"   {result.stderr[:300]}")
    except subprocess.TimeoutExpired:
        print("⚠ Mirror sync timed out (5 min) — may have partially completed")
    except Exception as e:
        print(f"⚠ Mirror sync failed (non-fatal per Article VIII): {e}")

# ── Main ───────────────────────────────────────────────────────────

def scan_and_route(dry_run=False, do_sync=True, use_ai=True):
    """Scan inbox and route files using two-tier classification."""
    global AI_ENABLED
    AI_ENABLED = use_ai

    if not os.path.isdir(INBOX_DIR):
        print(f"❌ Inbox directory not found: {INBOX_DIR}")
        print(f"   Create it with: mkdir -p {INBOX_DIR}")
        return

    files = sorted([f for f in os.listdir(INBOX_DIR)
                    if os.path.isfile(os.path.join(INBOX_DIR, f))])

    if not files:
        print(f"📭 Inbox is empty — nothing to route.")
        return

    print(f"📥 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
          f"Scanning inbox: {len(files)} file(s)")
    if dry_run:
        print("   🧪 DRY RUN — no files will be moved\n")
    print()

    routed = 0
    ai_routed = 0
    skipped = 0
    errors = 0

    for filename in files:
        source_path = os.path.join(INBOX_DIR, filename)

        # ── Tier 0: Section provenance suffix (`INDEX__696-Utilities.md`) ──
        # The puller namespaces same-named files from different sections; honor it
        # so a section's own INDEX.md goes home instead of being AI-guessed.
        section_hint = os.path.splitext(filename)[0].split("__")[-1]
        target_folder = ""
        tier = ""
        if "__" in filename and os.path.isdir(os.path.join(BODY_DIR, section_hint)):
            target_folder = section_hint
            dewey_num = section_hint.split("-")[0]
            tier = f"🏷️ section tag '{section_hint}'"
        else:
            # ── Tier 1: Keyword match ──
            dewey_num, target_folder, keyword = match_keyword(filename)
            if dewey_num:
                tier = f"🔑 keyword '{keyword}'"
            else:
                # ── Tier 1.5: Content markers (deterministic, pre-AI) ──
                dewey_num, target_folder, marker = match_content(source_path)
                if dewey_num:
                    tier = f"📄 content marker '{marker}'"

        if not target_folder and not dewey_num:
            # ── Tier 2: AI fallback ──
            if AI_ENABLED:
                print(f"🤖 AI classifying: {filename}...")
                dewey_num = ai_classify_file(source_path)
                if dewey_num:
                    target_folder = dewey_to_folder(dewey_num)
                    tier = f"🤖 AI → {dewey_num}"
                    ai_routed += 1
                else:
                    print(f"⚠  UNMATCHED: {filename} — no keyword, AI failed. Left in inbox.")
                    skipped += 1
                    continue
            else:
                print(f"⚠  UNMATCHED: {filename} — no keyword, AI disabled. Left in inbox.")
                skipped += 1
                continue

        destination_dir = os.path.join(BODY_DIR, target_folder)
        # Strip the puller's `__<section>` provenance suffix — the destination
        # folder already disambiguates, so files keep their original names.
        landing_name = filename
        if "__" in filename:
            stem, ext = os.path.splitext(filename)
            head, sep, tail = stem.rpartition("__")
            if sep and tail == target_folder:
                landing_name = head + ext
        destination_path = os.path.join(destination_dir, landing_name)

        # Check for duplicate — identical content is a no-op, NOT a new file.
        # (Renaming to -DUPLICATE- every run littered the brain with copies.)
        if os.path.exists(destination_path):
            try:
                same = file_hash(source_path) == file_hash(destination_path)
            except Exception:
                same = False
            if same:
                print(f"↩  SKIP (identical copy already in {target_folder}/): {filename}")
                skipped += 1
                continue
            ts = datetime.now().strftime('%Y%m%d-%H%M%S')
            stem, ext = os.path.splitext(filename)
            new_name = f"{stem}-DIFFERS-{ts}{ext}"
            destination_path = os.path.join(destination_dir, new_name)
            print(f"⚠  SAME NAME, DIFFERENT CONTENT: {filename} → {new_name}")

        if dry_run:
            print(f"🧪 WOULD ROUTE [{tier}]: {filename} → {target_folder}/")
            routed += 1
            continue

        try:
            os.makedirs(destination_dir, exist_ok=True)
            shutil.move(source_path, destination_path)
            fhash = file_hash(destination_path)

            print(f"✅ ROUTED [{tier}]: {filename} → {target_folder}/")

            # Blockchain audit trail
            log_blockchain("CREATE", f"{target_folder}/{filename}", dewey_num)

            # Human-readable log
            log_change(f"Inbox route [{tier}]: {filename} → {target_folder} "
                       f"(SHA256: {fhash[:12]}...)")

            routed += 1

        except PermissionError:
            print(f"❌ PERMISSION DENIED: {filename}")
            errors += 1
        except OSError as e:
            print(f"❌ OS ERROR: {filename} — {e}")
            errors += 1
        except Exception as e:
            print(f"❌ UNEXPECTED: {filename} — {e}")
            errors += 1

    # ── Summary ──
    print(f"\n{'─' * 55}")
    print(f"📊 ROUTE SUMMARY: {routed} routed ({ai_routed} via AI) | "
          f"{skipped} skipped | {errors} errors")
    if dry_run:
        print(f"   🧪 This was a DRY RUN — re-run without --dry-run to execute")
    print(f"{'─' * 55}")

    # ── Mirror sync ──
    if routed > 0 and not dry_run and do_sync:
        sync_mirrors()

def show_status():
    """Display current inbox contents with routing predictions."""
    if not os.path.isdir(INBOX_DIR):
        print(f"❌ Inbox directory not found: {INBOX_DIR}")
        return

    files = sorted([f for f in os.listdir(INBOX_DIR)
                    if os.path.isfile(os.path.join(INBOX_DIR, f))])

    if not files:
        print("📭 Inbox is empty.")
        return

    print(f"📥 Inbox contents ({len(files)} files):\n")
    for f in files:
        fpath = os.path.join(INBOX_DIR, f)
        size = os.path.getsize(fpath)
        dewey_num, target, keyword = match_keyword(f)

        if target:
            match_info = f"🔑 → {target} (keyword: {keyword})"
        else:
            match_info = "⚠ unmatched — would need AI fallback"

        print(f"  {f:<50} {size:>8,} bytes  {match_info}")

# ── Entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    do_sync = "--no-sync" not in sys.argv
    use_ai = "--no-ai" not in sys.argv

    if "--status" in sys.argv:
        show_status()
    else:
        scan_and_route(dry_run=dry_run, do_sync=do_sync, use_ai=use_ai)
