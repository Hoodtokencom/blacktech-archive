#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════
BLACKTECH SERVICE WATCHDOG v2 — Auto-restart + Telegram Alerts
═══════════════════════════════════════════════════════════
Monitors all critical ports. If a service dies:
  1. Auto-restarts it
  2. Sends Telegram alert if restart fails

Runs via cron every 5 minutes.
"""

import os
import sys
import json
import time
import socket
import subprocess
import urllib.request
from datetime import datetime

# ── CONFIG ───────────────────────────────────────────────
LOG_FILE = "/home/allenai/data/watchdog.log"
ALERT_STATE_FILE = "/home/allenai/data/watchdog_alerts.json"
HERMES_ENV_FILE = "/home/allenai/.hermes/.env"

# Your Telegram chat ID (where alerts go)
TELEGRAM_CHAT_ID = "5805015753"

# Load bot token from Hermes .env (watchdog runs in cron, no env vars)
def load_telegram_token():
    # Use vault_loader if .env is encrypted
    enc_path = "/home/allenai/.env.enc"
    env_path = "/home/allenai/.env"
    if os.path.exists(enc_path):
        try:
            import vault_loader
            vault_loader.load_env()
            return os.getenv("TELEGRAM_BOT_TOKEN", "")
        except Exception:
            pass
    # Fallback: read plain .env directly
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

TELEGRAM_BOT_TOKEN = load_telegram_token()
# Service name → [port, start_command, working_dir]
SERVICES = {
    "n8n Auto":              [5678,  "npx n8n",                         "/home/allenai"],
    "Energy Experts Board":  [8080,  "python3 energy_board_server.py",  "/home/allenai"],
    "File Manager":          [8081,  "python3 file_manager_server.py",   "/home/allenai"],
    "Think Energy Leads":    [8088,  "python3 lead_portal_server.py",    "/home/allenai"],
    "Command Center":        [8090,  "python3 command_center_server.py","/home/allenai"],
    "Money / Budget":        [8091,  "python3 money_budget_server.py",  "/home/allenai"],
    "CRM / Lead Portal":     [8092,  "python3 lead_portal_server.py",   "/home/allenai"],
    "Finance / Reports":     [8093,  "python3 finance_server.py",       "/home/allenai"],
    "BFN / Blue Wednesday":  [8094,  "python3 bluewednesday_server.py",  "/home/allenai"],
    "ComEd Dashboard":       [8095,  "python3 comed_server.py",          "/home/allenai"],
}

# ── UTILS ────────────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("Telegram not configured — skipping alert")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        body = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception as e:
        log(f"Telegram send failed: {e}")
        return False

def is_port_alive(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("localhost", port))
        s.close()
        return result == 0
    except Exception:
        return False

def kill_port(port):
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=5)
        time.sleep(1)
        return True
    except Exception:
        return False

def start_service(name, port, cmd, cwd):
    try:
        kill_port(port)
        subprocess.Popen(
            cmd.split(),
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        time.sleep(3)
        if is_port_alive(port):
            return True
        subprocess.Popen(
            ["nohup"] + cmd.split(),
            cwd=cwd,
            stdout=open(f"/tmp/{name.replace(' ', '_')}.log", "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        time.sleep(3)
        return is_port_alive(port)
    except Exception as e:
        log(f"Failed to start {name}: {e}")
        return False

# ── ALERT DEDUPLICATION ──────────────────────────────────
def load_alert_state():
    try:
        with open(ALERT_STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_alert_state(state):
    try:
        with open(ALERT_STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        log(f"Failed to save alert state: {e}")

def should_alert(service_name):
    """Only alert once per hour per service to avoid spam."""
    state = load_alert_state()
    now = time.time()
    last_alert = state.get(service_name, 0)
    if now - last_alert < 3600:  # 1 hour cooldown
        return False
    state[service_name] = now
    save_alert_state(state)
    return True

# ── MAIN ─────────────────────────────────────────────────
def main():
    log("═══ Watchdog check started ═══")
    down_count = 0
    restart_fail_count = 0
    alert_sent = 0

    for name, (port, cmd, cwd) in SERVICES.items():
        alive = is_port_alive(port)
        if alive:
            log(f"✅ {name} (port {port}) — OK")
            continue

        log(f"🔴 {name} (port {port}) — DOWN")
        down_count += 1

        # Try restart
        restarted = start_service(name, port, cmd, cwd)
        if restarted:
            log(f"🟢 {name} — RESTARTED successfully")
        else:
            log(f"❌ {name} — RESTART FAILED")
            restart_fail_count += 1
            if should_alert(name):
                msg = (
                    f"🔴 *{name}* is DOWN\n"
                    f"Port: `{port}`\n"
                    f"Auto-restart: FAILED\n"
                    f"Time: {datetime.now().strftime('%H:%M')}\n\n"
                    f"_You need to check this manually._"
                )
                ok = send_telegram(msg)
                if ok:
                    alert_sent += 1
                    log(f"📨 Telegram alert sent for {name}")
                else:
                    log(f"⚠️ Telegram alert FAILED for {name}")

    # Summary alert if anything was wrong
    if down_count > 0:
        summary = (
            f"⚠️ *Watchdog Report*\n"
            f"Down: {down_count} | Restart failed: {restart_fail_count} | Alerts sent: {alert_sent}\n"
            f"Time: {datetime.now().strftime('%H:%M')}"
        )
        send_telegram(summary)

    log(f"═══ Done. Down: {down_count}, Restart fails: {restart_fail_count}, Alerts: {alert_sent} ═══")
    return 0 if restart_fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
