#!/usr/bin/env python3
"""
Blockchain Listener + Triple-Play Pipeline Marriage
Phase 3: Blockchain fires → AI Pipeline processes → Result saved → Telegram alert

Usage:
  python3 blockchain_listener.py --demo       # Simulated events → full AI pipeline
  python3 blockchain_listener.py --testnet    # Real Sepolia events → AI pipeline
  python3 blockchain_listener.py --file PATH  # JSON task file → AI pipeline
"""
import os, sys, json, asyncio, subprocess, urllib.request, sqlite3
from datetime import datetime
from pathlib import Path

# ── CONFIG ───────────────────────────────────────────
SEPOLIA_RPCS = [
    "https://sepolia.drpc.org",
    "https://ethereum-sepolia-rpc.publicnode.com",
    "https://rpc.sepolia.org",
]
WALLET = os.environ.get("WALLET_ADDRESS", "0x312fC758b9e6C7F38Ee3E8563B45a9937eaf59B4")
DB_PATH = "/home/allenai/data/blacktech.db"
LOG_FILE = "/home/allenai/data/blockchain_listener.log"

BOT = os.environ.get("LEAD_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip()
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "5805015753").strip()

# Task templates per type
TASK_TEMPLATES = {
    "invoice": "Generate a professional electrical contractor invoice for {data}. Include labor, materials, line items, subtotal, tax, and total.",
    "lead":    "Qualify this new lead for Think Energy: {data}. Create a summary, score urgency (1-10), and suggest next action.",
    "report":  "Create a weekly business report for Blacktech Solutions: {data}. Include revenue, expenses, open jobs, and action items.",
    "email":   "Draft a professional follow-up email: {data}. Keep it under 150 words, compelling call-to-action.",
    "code":    "{data}. Provide the complete solution with code and brief explanation.",
}

# Simulated demo events
DEMO_EVENTS = [
    {"task_id": 1, "type": "invoice", "priority": "low",  "data": "client Taurus Williams, 10150 S Luella Ave, Chicago, IL 60628. Labor proposal $12,500"},
    {"task_id": 2, "type": "lead",    "priority": "high", "data": "CAIC contact from 60628, phone 773-785-8076, interested in energy audit"},
    {"task_id": 3, "type": "report",  "priority": "med",  "data": "Week of June 1-7, 2026. 3 jobs completed, $18,400 invoiced, $3,200 expenses"},
    {"task_id": 4, "type": "email",   "priority": "low",  "data": "Thank CAIC for the Roseland/West Pullman area business directory listing"},
    {"task_id": 5, "type": "code",    "priority": "high", "data": "Write a Python function that reads ComEd rate data from an API and alerts when off-peak hours start"},
]

# ── HELPERS ──────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] 🔗 {msg}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)
    print(line, end="")

def telegram_alert(msg):
    if not BOT or not CHAT:
        log("⚠️ Telegram alert skipped — BOT or CHAT missing")
        return
    url = f"https://api.telegram.org/bot{BOT}/sendMessage"
    payload = json.dumps({"chat_id": CHAT, "text": msg, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        log("   📲 Telegram alert sent")
    except Exception as e:
        log(f"   ❌ Telegram alert FAILED: {e}")

def init_db():
    """Ensure pipeline_results table exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            task_type TEXT,
            priority TEXT,
            input_data TEXT,
            final_output TEXT,
            total_cost REAL,
            gemini_status TEXT,
            ollama_status TEXT,
            claude_status TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_result(task, final_output, cost, gemini_status, ollama_status, claude_status):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO pipeline_results
        (task_id, task_type, priority, input_data, final_output, total_cost,
         gemini_status, ollama_status, claude_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task["task_id"], task["type"], task["priority"], task["data"],
        final_output, cost, gemini_status, ollama_status, claude_status,
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

def run_pipeline(task):
    """Call Triple-Play Pipeline via subprocess, return (output, cost, statuses)."""
    template = TASK_TEMPLATES.get(task["type"], "{data}")
    prompt = template.format(data=task["data"])

    log(f"🤖 Routing to Triple-Play Pipeline: {task['type'].upper()}")
    log(f"   Prompt: {prompt[:80]}...")

    # Run pipeline as subprocess (inherit env so API keys work)
    cmd = ["python3", "/home/allenai/scripts/triple_play_pipeline.py", prompt]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=os.environ.copy())
        # Output file was written by pipeline
        out_files = sorted(Path("/tmp").glob("pipeline_output_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if out_files:
            output_path = str(out_files[0])
            with open(output_path, "r") as f:
                content = f.read()
            # Parse cost from content (handles both "TOTAL COST:" and legacy "TOTAL:")
            cost = 0.0
            for line in content.split("\n"):
                ln = line.strip()
                if ("TOTAL COST:" in ln or ("TOTAL" in ln and "$" in ln)) and not line.startswith("Gemini") and not line.startswith("Ollama") and not line.startswith("Claude"):
                    try:
                        cost = float(ln.split("$")[-1].strip().split()[0])
                    except Exception:
                        pass
            # Parse statuses from new format: "GEMINI: COMPLETED -- $0.000150"
            gs, os_, cs = "unknown", "unknown", "unknown"
            for line in content.split("\n"):
                if line.startswith("GEMINI:") and "--" in line:
                    gs = line.split("--")[0].replace("GEMINI:", "").strip().lower()
                elif line.startswith("OLLAMA:") and "--" in line:
                    os_ = line.split("--")[0].replace("OLLAMA:", "").strip().lower()
                elif line.startswith("CLAUDE:") and "--" in line:
                    cs = line.split("--")[0].replace("CLAUDE:", "").strip().lower()
            gs = gs or "unknown"
            os_ = os_ or "unknown"
            cs = cs or "unknown"
            # Extract final output section
            final = content
            if "FINAL OUTPUT:" in content:
                final = content.split("FINAL OUTPUT:")[-1].strip()
            return final, cost, gs, os_, cs, output_path
        else:
            return "Pipeline output file not found", 0.0, "unknown", "unknown", "unknown", ""
    except subprocess.TimeoutExpired:
        return "Pipeline timed out after 3 minutes", 0.0, "timeout", "timeout", "timeout", ""
    except Exception as e:
        return f"Pipeline error: {e}", 0.0, "error", "error", "error", ""

# ── DEMO MODE ────────────────────────────────────────
async def run_demo():
    # Load vault for API keys + Telegram tokens
    global BOT, CHAT
    if not os.environ.get("GEMINI_API_KEY"):
        sys.path.insert(0, "/home/allenai/scripts")
        try:
            from vault_loader import load_env
            load_env()
            log("✅ Vault loaded")
        except Exception as e:
            log(f"⚠️ Vault load failed: {e}")
    BOT = os.environ.get("LEAD_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip()
    CHAT = os.environ.get("TELEGRAM_CHAT_ID", "5805015753").strip()
    log(f"📲 Telegram: BOT={'✅' if BOT else '❌'} CHAT={'✅' if CHAT else '❌'}")

    log("═══ DEMO MODE: Blockchain → AI Pipeline ═══")
    init_db()

    for event in DEMO_EVENTS:
        await asyncio.sleep(3)
        log(f"🚨 TASK EMITTED — ID: {event['task_id']} | {event['type'].upper()} | Priority: {event['priority']}")

        # Run pipeline
        output, cost, gs, os_, cs, out_path = run_pipeline(event)

        # Save to DB
        save_result(event, output, cost, gs, os_, cs)

        # Alert Telegram
        cost_str = f"${cost:.6f}" if cost > 0 else "$0.00"
        msg = (
            f"🚀 <b>Pipeline Complete</b>\n"
            f"Task #{event['task_id']} — {event['type'].upper()}\n"
            f"Cost: {cost_str}\n"
            f"Gemini: {gs.upper()} | Ollama: {os_.upper()} | Claude: {cs.upper()}\n\n"
            f"Output preview:\n<code>{output[:300]}...</code>"
        )
        telegram_alert(msg)
        log(f"   ✅ Saved to DB | Cost: {cost_str} | Output: {output[:100]}...")
        log("")

    log("═══ All 5 demo tasks processed. Check /home/allenai/data/blacktech.db for results. ═══")

# ── TESTNET MODE ─────────────────────────────────────
async def run_testnet():
    # Load vault if keys not already in environment
    if not os.environ.get("GEMINI_API_KEY"):
        sys.path.insert(0, "/home/allenai/scripts")
        try:
            from vault_loader import load_env
            load_env()
            log("✅ Vault loaded")
        except Exception as e:
            log(f"⚠️ Vault load failed: {e}")

    # Reload Telegram tokens from env (loaded by vault or set externally)
    global BOT, CHAT
    BOT = os.environ.get("LEAD_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip()
    CHAT = os.environ.get("TELEGRAM_CHAT_ID", "5805015753").strip()
    log(f"📲 Telegram alert configured: BOT={'✅' if BOT else '❌'} CHAT={'✅' if CHAT else '❌'}")

    try:
        from web3 import Web3
    except ImportError:
        log("❌ web3 not installed. Run: pip3 install web3")
        return

    log("═══ TESTNET MODE: Sepolia → AI Pipeline ═══")
    init_db()

    # Try multiple RPCs
    w3 = None
    for rpc in SEPOLIA_RPCS:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc))
            if w3.is_connected():
                log(f"✅ Connected via {rpc}")
                break
        except:
            continue
    if not w3 or not w3.is_connected():
        log("❌ Cannot connect to any Sepolia RPC. Check internet or use --demo.")
        return

    if not w3.is_connected():
        log("❌ Cannot connect to Sepolia. Use --demo for offline testing.")
        return

    block = w3.eth.block_number
    log(f"✅ Connected. Latest block: {block}")
    log(f"Watching wallet: {WALLET}")
    last_block = block

    # Show balance
    try:
        bal = w3.from_wei(w3.eth.get_balance(WALLET), 'ether')
        log(f"💰 Wallet balance: {bal:.4f} ETH")
    except:
        pass

    while True:
        await asyncio.sleep(5)
        try:
            current = w3.eth.block_number
            if current > last_block:
                for b in range(last_block + 1, current + 1):
                    block_data = w3.eth.get_block(b, full_transactions=True)
                    for tx in block_data.transactions:
                        to_addr = tx.get('to', '')
                        if to_addr and to_addr.lower() == WALLET.lower():
                            value = w3.from_wei(tx['value'], 'ether')
                            event = {
                                "task_id": int(tx['hash'].hex(), 16) % 100000,
                                "type": "transaction",
                                "priority": "high",
                                "data": f"Received {value} ETH from {tx['from']} in block #{b}"
                            }
                            log(f"🚨 WALLET TRANSACTION — {value} ETH")
                            # Run pipeline in background so listener stays responsive
                            asyncio.create_task(handle_tx(event, value))
                last_block = current
        except Exception as e:
            log(f"⚠️ Error: {e}")

async def handle_tx(event, value):
    """Async wrapper: run pipeline + save + alert without blocking listener."""
    try:
        loop = asyncio.get_event_loop()
        output, cost, gs, os_, cs, _ = await loop.run_in_executor(None, run_pipeline, event)
        save_result(event, output, cost, gs, os_, cs)
        telegram_alert(f"🚀 <b>Blockchain Task Processed</b>\n{value} ETH received → Pipeline ran. Cost: ${cost:.6f}")
    except Exception as e:
        log(f"   ❌ Pipeline/alert error: {e}")

# ── LOCAL FILE MODE ──────────────────────────────────
async def run_local_file(watch_path="/home/allenai/data/blockchain_tasks.json"):
    log(f"═══ FILE MODE: Watching {watch_path} → AI Pipeline ═══")
    init_db()
    processed = set()

    while True:
        await asyncio.sleep(2)
        if os.path.exists(watch_path):
            try:
                with open(watch_path, 'r') as f:
                    data = json.load(f)
                task_id = data.get("task_id", 0)
                if task_id not in processed:
                    processed.add(task_id)
                    log(f"🚨 FILE TASK — ID: {task_id} | {data.get('type', 'unknown').upper()}")
                    output, cost, gs, os_, cs, _ = run_pipeline(data)
                    save_result(data, output, cost, gs, os_, cs)
                    telegram_alert(f"🚀 <b>File Task Processed</b>\nType: {data.get('type','unknown')} | Cost: ${cost:.6f}")
            except Exception as e:
                log(f"⚠️ File task error: {e}")

# ── MAIN ─────────────────────────────────────────────
async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Blockchain + AI Pipeline")
    parser.add_argument("--demo", action="store_true", help="Simulated events")
    parser.add_argument("--testnet", action="store_true", help="Sepolia testnet")
    parser.add_argument("--file", metavar="PATH", help="Watch local JSON file")
    args = parser.parse_args()

    if args.testnet:
        await run_testnet()
    elif args.file:
        await run_local_file(args.file)
    else:
        await run_demo()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Blockchain listener stopped.")
        sys.exit(0)
