#!/usr/bin/env python3
"""
Blacktech Telegram Bot — Command Interface

Commands:
  /status  — Show running services
  /deploy  — Force CI/CD deploy
  /toll    — Show AI cost balance
  /help    — List commands

Runs via polling (no webhook needed).
Add to CI/CD: telegram_bot.py
"""
import os, sys, json, time, urllib.request, urllib.parse, subprocess, sqlite3

# Load vault if keys not already in environment
if not os.environ.get("TELEGRAM_BOT_TOKEN"):
    sys.path.insert(0, "/home/allenai/scripts")
    try:
        from vault_loader import load_env
        load_env()
    except Exception as e:
        print(f"⚠️ Vault load failed: {e}")

# Fallback: lead bot token is the same bot
BOT = os.environ.get("TELEGRAM_BOT_TOKEN", os.environ.get("LEAD_BOT_TOKEN", "")).strip()
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "5805015753").strip()
TOLL_FILE = "/home/allenai/data/ai_toll_meter.txt"
DB_PATH = "/home/allenai/data/blacktech.db"

if not BOT:
    print("❌ TELEGRAM_BOT_TOKEN not set")
    sys.exit(1)

BASE = f"https://api.telegram.org/bot{BOT}"

# ── Helpers ──────────────────────────────────────────
def api(method, params=None):
    url = f"{BASE}/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"API error: {e}")
        return {}

def send(chat_id, text):
    api("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

def get_services():
    scripts = [
        ("Kanban Board", "energy_board_server.py"),
        ("BFN Watchdog", "bfn_watchdog.py"),
        ("HOOD API", "hood_api.py"),
        ("Auto-Fill", "auto_fill_server.py"),
        ("Pipeline", "triple_play_pipeline.py"),
        ("Monitor", "pipeline_monitor.py"),
        ("Blockchain", "blockchain_listener.py"),
        ("Budget", "money_budget_server.py"),
        ("ComEd", "comed_server.py"),
        ("Leads", "lead_intake_bot.py"),
        ("Command Center", "command_center_server.py"),
        ("Finance", "finance_server.py"),
        ("BlueWed", "bluewednesday_server.py"),
        ("CI/CD", "cicd_deploy.py"),
        ("Watchdog", "Blacktech_watchdog.py"),
        ("Telegram Bot", "telegram_bot.py"),
    ]
    lines = []
    running = 0
    for name, script in scripts:
        try:
            result = subprocess.run(["pgrep", "-f", script], capture_output=True, text=True)
            ok = result.returncode == 0
            if ok:
                running += 1
            lines.append(f"{'🟢' if ok else '🔴'} {name}")
        except:
            lines.append(f"🔴 {name}")
    return f"<b>🖥️ Blacktech Status</b>\n{running}/{len(scripts)} running\n\n" + "\n".join(lines)

def get_toll():
    try:
        with open(TOLL_FILE, "r") as f:
            lines = f.readlines()
        # Find last balance line
        total = "$0.00"
        for line in reversed(lines):
            if "BALANCE DUE" in line or "CURRENT BALANCE" in line:
                parts = line.split("$")
                if len(parts) > 1:
                    total = "$" + parts[-1].strip().split()[0]
                break
        # Count entries
        count = sum(1 for l in lines if l.strip().startswith("|"))
        return f"<b>💰 AI Toll Meter</b>\nBalance: {total}\nEntries: {count}\n\n<i>Every AI pass costs — watch the meter run</i>"
    except:
        return "<b>💰 AI Toll Meter</b>\nBalance: unavailable"

def get_pipeline_summary():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("SELECT COUNT(*), SUM(total_cost) FROM pipeline_results")
        count, cost = cur.fetchone()
        conn.close()
        return f"<b>🚀 Pipeline Summary</b>\nTasks: {count or 0}\nTotal spent: ${cost or 0:.6f}"
    except:
        return "<b>🚀 Pipeline</b>\nDB unavailable"

def trigger_deploy():
    try:
        subprocess.Popen(
            ["python3", "/home/allenai/scripts/cicd_deploy.py"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return "<b>🚀 Deploy Triggered</b>\nCI/CD script launched. Check dashboard for results."
    except Exception as e:
        return f"<b>❌ Deploy Failed</b>\n{str(e)[:200]}"

# ── Command Router ───────────────────────────────────
def handle(update):
    msg = update.get("message", {})
    text = msg.get("text", "").strip().lower()
    chat_id = msg.get("chat", {}).get("id", CHAT)
    user = msg.get("from", {}).get("first_name", "User")

    if text == "/status":
        send(chat_id, get_services())
    elif text == "/toll":
        send(chat_id, get_toll())
    elif text == "/pipeline":
        send(chat_id, get_pipeline_summary())
    elif text == "/deploy":
        send(chat_id, trigger_deploy())
    elif text == "/help":
        send(chat_id, (
            "<b>🤖 Blacktech Bot Commands</b>\n\n"
            "/status — See what's running\n"
            "/toll — AI cost balance\n"
            "/pipeline — Blockchain-AI summary\n"
            "/deploy — Force CI/CD deploy\n"
            "/help — This message"
        ))
    elif text.startswith("/"):
        send(chat_id, f"Unknown command. Type /help for options.")

# ── Main Loop ────────────────────────────────────────
def main():
    print("🤖 Blacktech Telegram Bot starting...")
    print(f"   Token: {BOT[:10]}...")
    print("   Polling for messages...")
    offset = 0
    while True:
        result = api("getUpdates", {"offset": offset, "limit": 10})
        for update in result.get("result", []):
            offset = max(offset, update["update_id"] + 1)
            handle(update)
        time.sleep(2)

if __name__ == "__main__":
    main()
