#!/usr/bin/env python3
"""
Lightweight CI/CD for Hoodtokencom/assets repo.
Uses GitHub API to poll for new commits, downloads ONLY changed .py files
from the repo (no 685MB clone), syncs to /home/allenai/scripts/, restarts services.
"""
import os, sys, json, subprocess, time, hashlib, urllib.request
from pathlib import Path

# ── Config ──────────────────────────────────────────────
REPO = "Hoodtokencom/assets"
BRANCH = "master"
LOCAL_DIR = "/home/allenai/scripts"
STATE_FILE = "/home/allenai/data/.cicd_state.json"
LOG_FILE = "/home/allenai/data/cicd.log"
OWNER = "Hoodtokencom"
REPO_NAME = "assets"

# Files we care about in the repo (relative paths)
# If you add scripts to the repo under e.g. blacktech/ folder, update these paths
SCRIPT_PATHS = [
    "Blacktech/Blacktech_watchdog.py",
    "Blacktech/telegram_bot.py",
]

# ── Telegram Alert ───────────────────────────────────────
def telegram_alert(message: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat, "text": message, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass

# ── Helpers ──────────────────────────────────────────────
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)
    print(line, end="")

def read_state() -> dict:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def write_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def api_get(path: str) -> dict:
    url = f"https://api.github.com/repos/{REPO}/{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "Blacktech-CI/CD")
    # Optional: add token for higher rate limits
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read().decode())

def download_file(url: str, dest: str) -> bool:
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        log(f"  ✗ Download failed: {e}")
        return False

def restart_services():
    """Kill old process by name, then start fresh with nohup."""
    # Map: script basename → full path to restart
    services = {
        "energy_board_server.py": "/home/allenai/energy_board_server.py",
        "bfn_watchdog.py": "/home/allenai/scripts/bfn_watchdog.py",
        "hood_api.py": "/home/allenai/scripts/hood_api.py",
        "auto_fill_server.py": "/home/allenai/scripts/auto_fill_server.py",
        "triple_play_pipeline.py": "/home/allenai/scripts/triple_play_pipeline.py",
        "pipeline_monitor.py": "/home/allenai/scripts/pipeline_monitor.py",
        "blockchain_listener.py": "/home/allenai/scripts/blockchain_listener.py",
        "money_budget_server.py": "/home/allenai/money_budget_server.py",
        "comed_server.py": "/home/allenai/comed_server.py",
        "lead_intake_bot.py": "/home/allenai/.hermes/profiles/derrell-black/scripts/lead_intake_bot.py",
        "command_center_server.py": "/home/allenai/command_center_server.py",
        "finance_server.py": "/home/allenai/finance_server.py",
        "bluewednesday_server.py": "/home/allenai/bluewednesday_server.py",
    }

    for script_name, script_path in services.items():
        # Kill old
        try:
            subprocess.run(
                ["pkill", "-f", script_name],
                capture_output=True, timeout=5
            )
            log(f"  💀 Killed {script_name}")
        except Exception:
            pass

        # Restart fresh
        try:
            subprocess.Popen(
                ["nohup", "python3", script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd="/home/allenai",
                start_new_session=True
            )
            log(f"  ✅ Restarted {script_name}")
        except Exception as e:
            log(f"  ⚠️ Restart failed for {script_name}: {e}")

# ── Main ─────────────────────────────────────────────────
def main():
    log("🔍 CI/CD poll started")
    state = read_state()
    last_sha = state.get("last_sha", "")

    try:
        commit_info = api_get(f"commits/{BRANCH}")
        current_sha = commit_info["sha"]
    except Exception as e:
        log(f"  ✗ Could not fetch commit: {e}")
        telegram_alert("🚨 <b>CI/CD Error</b>\nCould not fetch GitHub commit.")
        return 1

    if current_sha == last_sha:
        log("  → No new commits. Up to date.")
        return 0

    log(f"  → New commit: {current_sha[:7]}")

    # If you haven't added SCRIPT_PATHS yet, just log and alert
    if not SCRIPT_PATHS:
        msg = (
            f"📦 <b>New Commit Detected</b>\n"
            f"Repo: <code>{REPO}</code>\n"
            f"SHA: <code>{current_sha[:7]}</code>\n\n"
            f"⚠️ No script paths configured yet.\n"
            f"Add your .py files to the repo, then update SCRIPT_PATHS in this script."
        )
        log("  ⚠️ SCRIPT_PATHS is empty — nothing to sync")
        telegram_alert(msg)
        state["last_sha"] = current_sha
        write_state(state)
        return 0

    deployed = []
    for rel_path in SCRIPT_PATHS:
        try:
            file_info = api_get(f"contents/{rel_path}?ref={BRANCH}")
            download_url = file_info.get("download_url", "")
            if not download_url:
                log(f"  ✗ No download_url for {rel_path}")
                continue
            dest = os.path.join(LOCAL_DIR, os.path.basename(rel_path))
            if download_file(download_url, dest):
                os.chmod(dest, 0o755)
                log(f"  ✅ Synced {rel_path} → {dest}")
                deployed.append(rel_path)
        except Exception as e:
            log(f"  ✗ Error syncing {rel_path}: {e}")

    if deployed:
        restart_services()
        msg = (
            f"🚀 <b>Auto-Deploy Complete</b>\n"
            f"Repo: <code>{REPO}</code>\n"
            f"Commit: <code>{current_sha[:7]}</code>\n"
            f"Files: {len(deployed)}\n"
            f"{' '.join(deployed)}"
        )
    else:
        msg = (
            f"⚠️ <b>New Commit But No Deploy</b>\n"
            f"Repo: <code>{REPO}</code>\n"
            f"SHA: <code>{current_sha[:7]}</code>\n\n"
            f"Script paths may be wrong."
        )

    telegram_alert(msg)
    state["last_sha"] = current_sha
    write_state(state)
    log("✅ CI/CD cycle complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())
