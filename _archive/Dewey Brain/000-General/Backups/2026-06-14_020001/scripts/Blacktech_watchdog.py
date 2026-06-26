#!/usr/bin/env python3
"""
Blacktech Watchdog — General health monitor for all Blacktech services.
Runs as a cron job every 5 minutes, checks all daemons, logs status.

LOCK FILE GUARD: Only one instance may run at a time.
If a lock file exists and the PID inside is still alive, this instance exits immediately.

Restart manually:
    pkill -f blacktech_watchdog.py && sleep 1 && python3 /home/allenai/scripts/blacktech_watchdog.py &
"""
import os, sys, time, subprocess, json, datetime, fcntl

LOG_FILE   = "/home/allenai/data/blacktech_watchdog.log"
STATE_FILE = "/home/allenai/data/.watchdog_state.json"
LOCK_FILE  = "/tmp/blacktech_watchdog.lock"

# Daemons that should ALWAYS be running
DAEMONS = [
    ("Kanban Board",         "energy_board_server.py",         8080),
    ("Command Center",       "command_center_server.py",       8090),
    ("Blockchain Listener",  "scripts/blockchain_listener.py", None),
    ("Budget",               "money_budget_server.py",         None),
    ("ComEd",                "comed_server.py",                None),
    ("Leads",                "lead_intake_bot.py",             None),
    ("Finance",              "finance_server.py",              None),
    ("BlueWed",              "bluewednesday_server.py",        None),
]

# ── Lock-file guard ────────────────────────────────────────────────────────────
def acquire_lock():
    """
    Open LOCK_FILE and acquire an exclusive non-blocking flock.
    Returns the open file object on success (caller must keep it open to hold the lock).
    Exits the process immediately if the lock is already held by another instance.
    """
    try:
        lock_fh = open(LOCK_FILE, "w")
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fh.write(str(os.getpid()) + "\n")
        lock_fh.flush()
        return lock_fh
    except BlockingIOError:
        # Another instance is already running — exit silently
        print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] "
              "blacktech_watchdog: lock held by another instance — exiting.")
        sys.exit(0)

# ── Logging ────────────────────────────────────────────────────────────────────
def log(msg):
    ts   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ── Daemon health check ────────────────────────────────────────────────────────
def check_daemon(name, script, port):
    try:
        result  = subprocess.run(["pgrep", "-f", script], capture_output=True, text=True)
        running = result.returncode == 0
        pid     = result.stdout.strip().split("\n")[0] if running else ""

        port_ok = True
        if port and running:
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect(("127.0.0.1", port))
                s.close()
            except Exception:
                port_ok = False

        return {"name": name, "script": script, "running": running,
                "pid": pid, "port_ok": port_ok}
    except Exception as e:
        return {"name": name, "script": script, "running": False,
                "pid": "", "port_ok": False, "error": str(e)}

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    # Acquire lock — exits immediately if another instance is running
    lock_fh = acquire_lock()

    log("🐕 Blacktech Watchdog check started")
    try:
        status     = []
        down_count = 0

        for name, script, port in DAEMONS:
            info = check_daemon(name, script, port)
            status.append(info)

            if not info["running"]:
                down_count += 1
                log(f"⚠️  {name} is DOWN (script: {script})")
                try:
                    subprocess.Popen(
                        ["python3", f"/home/allenai/{script}"],
                        cwd="/home/allenai",
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    log(f"🔄 Restarted {name}")
                except Exception as re:
                    log(f"❌ Failed to restart {name}: {re}")

            elif port and not info["port_ok"]:
                # Zombie process — running but port dead. Kill and restart.
                log(f"🧟 {name} is zombie (PID {info['pid']}) — killing and restarting")
                try:
                    subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
                    time.sleep(1)
                    subprocess.Popen(
                        ["python3", f"/home/allenai/{script}"],
                        cwd="/home/allenai",
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    log(f"🔄 Restarted {name} after zombie kill")
                    down_count += 1
                except Exception as ze:
                    log(f"❌ Failed to kill/restart {name}: {ze}")
            # else: healthy — nothing to do

        state = {
            "checked_at": datetime.datetime.now().isoformat(),
            "total":      len(DAEMONS),
            "down":       down_count,
            "services":   status,
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

        if down_count == 0:
            log(f"✅ All {len(DAEMONS)} daemons healthy")
        else:
            log(f"❌ {down_count}/{len(DAEMONS)} daemons down — restarts attempted")

    except Exception as e:
        log(f"💥 Watchdog error: {e}")
    finally:
        # Release lock
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        lock_fh.close()
        try:
            os.remove(LOCK_FILE)
        except FileNotFoundError:
            pass

if __name__ == "__main__":
    main()
