#!/usr/bin/env python3
"""
Gate Keeper — Unified token contract + approval + spend tracking system
Usage:
  python3 gate_keeper.py preview D2 2100 "Contract review for NuVision"
  python3 gate_keeper.py run D2 2100 "Contract review" --task-body "..."
  python3 gate_keeper.py status
  python3 gate_keeper.py ledger
"""

import sys, os, json, csv, sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, "/home/allenai/scripts")

LEDGER_PATH    = "/home/allenai/data/token_ledger.csv"
BUDGET_PATH    = "/home/allenai/data/token_budget.json"
TOLL_JSON      = "/home/allenai/data/ai_toll_meter.json"
ENV_FILE       = "/home/allenai/.hermes/profiles/derrell-black/.env"

# ── Duty Catalog ──────────────────────────────────────────
DUTIES = {
    "D1": ("Chat / General",          "Qwen 3",              None,                 1024, 0.00),
    "D2": ("Contract Review",         "Gemini Pro",          "Claude Sonnet 4-6",  4096, 0.22),
    "D3": ("Deep Legal Analysis",     "Gemini Pro",          "Claude Opus 4-6",    8192, 0.35),
    "D4": ("Code Build / Dev",        "Gemini Pro",          "Claude Sonnet/Codex",8192, 0.28),
    "D5": ("Code Review",             "Gemini Pro",          "Claude Sonnet",      4096, 0.18),
    "D6": ("Image Generation",        "ComfyUI/DALL-E",      None,                 0,    0.00),
    "D7": ("Video / Audio",           "Suno/TTS local",     None,                 0,    0.00),
    "D8": ("Heavy ML / Research",     "Gemini Pro",          "Claude Opus/Gemma", 16384, 0.55),
    "D9": ("Multi-Agent Orchestration", "Hermes Subagents",    "Claude per sub",     0,    0.00),
    "D10":("Wage / Compliance",       "Local+Qwen",          "Gemini Pro",         2048, 0.00),
}

CLAUDE_UPGRADE = {
    "D2": 0.52, "D3": 0.80, "D4": 0.65, "D5": 0.45, "D8": 1.20,
}

# ── Helpers ─────────────────────────────────────────────────
def load_env():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                if line.startswith("export ") and "=" in line:
                    k,v = line.replace("export ","",1).strip().split("=",1)
                    os.environ.setdefault(k, v.strip('"'))

def get_gemini_key():
    load_env()
    return os.environ.get("GEMINI_API_KEY","")

def budget_state():
    """Return daily spend, monthly spend, daily limit, monthly limit."""
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")
    day_spend = month_spend = 0.0
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH) as f:
            reader = csv.DictReader(f)
            for row in reader:
                cost = float(row.get("cost","0") or 0)
                ts   = row.get("timestamp","")[:7]  # YYYY-MM
                if ts == month:
                    month_spend += cost
                if row.get("timestamp","").startswith(today):
                    day_spend += cost
    # Default limits
    limits = {"daily": 5.0, "monthly": 50.0}
    if os.path.exists(BUDGET_PATH):
        try:
            limits.update(json.load(open(BUDGET_PATH)))
        except:
            pass
    return day_spend, month_spend, limits["daily"], limits["monthly"]

def log_spend(duty, model, input_tok, output_tok, cost, task):
    ts = datetime.now().isoformat()
    row = [ts, duty, model, input_tok, output_tok, round(cost,6), task[:80]]
    file_exists = os.path.exists(LEDGER_PATH)
    with open(LEDGER_PATH, "a", newline="") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["timestamp","duty","model","tokens_in","tokens_out","cost","task"])
        w.writerow(row)

def gate_color(duty, cost):
    if cost == 0.0:
        return "GREEN"
    if cost <= 0.30:
        return "BLUE"
    if cost <= 0.75:
        return "YELLOW"
    if cost <= 2.00:
        return "RED"
    return "BLACK"

def preview_block(duty_id, input_est, task_desc=""):
    if duty_id not in DUTIES:
        return f"Unknown duty: {duty_id}"
    name, opt1, opt2, max_out, gemini_cost = DUTIES[duty_id]
    claude_cost = CLAUDE_UPGRADE.get(duty_id)
    tier = gate_color(duty_id, gemini_cost)
    lines = []
    lines.append("="*43)
    lines.append("         TOKEN CONTRACT PREVIEW")
    lines.append("="*43)
    lines.append(f"Duty:        {duty_id} {name}")
    lines.append(f"Option 1:    {opt1} (RECOMMENDED)")
    if opt2:
        lines.append(f"Option 2:    {opt2} (UPGRADE)")
    lines.append(f"Input:       ~{input_est} tokens")
    lines.append(f"Output max:  {max_out:,} tokens")
    lines.append(f"Gate:        {tier}")
    lines.append("="*43)
    lines.append(f"Gemini cost: ${gemini_cost:.2f} est")
    if claude_cost:
        lines.append(f"Claude cost: ${claude_cost:.2f} est")
    lines.append("="*43)
    if tier == "GREEN":
        lines.append("✅ Auto-execute — no approval needed")
    elif tier == "BLUE":
        lines.append("Reply: YES GEMINI  → Option 1")
        if opt2:
            lines.append("Reply: YES CLAUDE  → Option 2")
        lines.append("Reply: NO          → Cancel")
    elif tier == "YELLOW":
        lines.append("🛑 Upgrade gate — confirm to proceed")
        lines.append("Reply: YES GEMINI  → Option 1")
        lines.append("Reply: YES CLAUDE  → Option 2")
        lines.append("Reply: NO          → Cancel")
    elif tier == "RED":
        lines.append("🛑 HIGH COST — confirm explicitly")
        lines.append("Reply: YES [MODEL] → Execute")
        lines.append("Reply: NO          → Cancel")
    elif tier == "BLACK":
        lines.append("🛑 BLACK GATE — Human negotiation required")
    lines.append("="*43)
    day_spend, _, day_lim, _ = budget_state()
    lines.append(f"📊 Budget: ${day_spend:.2f} / ${day_lim:.2f} today")
    return "\n".join(lines)

# ── Gemini dispatch (minimal) ──────────────────────────────
def run_gemini(task_body, max_tokens=4096):
    key = get_gemini_key()
    if not key:
        return "ERROR: No GEMINI_API_KEY", 0, 0, 0.0
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": task_body}]}],
        "generationConfig": {"maxOutputTokens": max_tokens}
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"})
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        # Rough token estimate: 1 token ≈ 4 chars
        out_tok = len(text) // 4
        in_tok  = len(task_body) // 4
        cost = round((in_tok + out_tok) / 1e6 * 0.15, 6)  # Gemini flash rate ~$0.15/M tok
        return text, in_tok, out_tok, cost
    except Exception as e:
        return f"ERROR: {e}", 0, 0, 0.0

# ── CLI ─────────────────────────────────────────────────────
def cmd_preview(args):
    if len(args) < 2:
        print("Usage: gate_keeper.py preview <duty_id> <input_tokens> [task_desc]")
        sys.exit(1)
    print(preview_block(args[0], args[1], " ".join(args[2:])))

def cmd_status(args):
    day, month, dlim, mlim = budget_state()
    print(f"Daily:   ${day:.2f} / ${dlim:.2f}")
    print(f"Monthly: ${month:.2f} / ${mlim:.2f}")
    remaining = dlim - day
    color = "🟢" if remaining > dlim*0.5 else "🟡" if remaining > dlim*0.2 else "🔴"
    print(f"{color} Remaining today: ${remaining:.2f}")

def cmd_ledger(args):
    if not os.path.exists(LEDGER_PATH):
        print("No ledger yet.")
        return
    with open(LEDGER_PATH) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"{'TIME':19} {'DUTY':4} {'MODEL':16} {'IN':>6} {'OUT':>6} {'COST':>8} TASK")
    for r in rows[-20:]:
        print(f"{r['timestamp'][:19]:19} {r['duty']:4} {r['model']:16} {r['tokens_in']:>6} {r['tokens_out']:>6} ${r['cost']:>7} {r['task'][:40]}")
    print(f"\nTotal entries: {len(rows)}")

def cmd_run(args):
    """Execute a task after approval. In practice you pre-approved via chat."""
    if len(args) < 3:
        print("Usage: gate_keeper.py run <duty_id> <input_tokens> <task_body>")
        sys.exit(1)
    duty_id, input_est = args[0], args[1]
    task_body = " ".join(args[2:])
    if duty_id not in DUTIES:
        print(f"Unknown duty: {duty_id}")
        sys.exit(1)
    _, opt1, opt2, max_out, _ = DUTIES[duty_id]
    # Default to Gemini for paid tasks
    if opt1 == "Qwen 3" or opt1 == "Local+Qwen":
        print("FREE task — no spend logged.")
        return
    print(f"Running {opt1}...")
    text, in_tok, out_tok, cost = run_gemini(task_body, max_out)
    if text.startswith("ERROR"):
        print(text)
        sys.exit(1)
    log_spend(duty_id, opt1, in_tok, out_tok, cost, task_body)
    # Also update toll meter
    try:
        from toll_meter import add_manual_entry
        add_manual_entry(datetime.now().strftime("%Y-%m-%d"), task_body[:40], cost)
    except Exception:
        pass
    print(f"\n✅ Complete | Cost: ${cost:.4f} | Tokens: {in_tok}+{out_tok}")
    print("-" * 40)
    print(text[:800])
    if len(text) > 800:
        print("... [truncated]")

def main():
    cmds = {"preview": cmd_preview, "status": cmd_status, "ledger": cmd_ledger, "run": cmd_run}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print("Usage: gate_keeper.py [preview|status|ledger|run] <args...>")
        print("\nExamples:")
        print('  python3 gate_keeper.py preview D2 2100 "Review subcontract"')
        print('  python3 gate_keeper.py status')
        print('  python3 gate_keeper.py run D2 2100 "Summarize this contract..."')
        sys.exit(1)
    cmds[sys.argv[1]](sys.argv[2:])

if __name__ == "__main__":
    main()
