#!/usr/bin/env python3
"""
BFN Watchdog — Monitors the BFN (Blacktech Finance Network) port 8094.
Ensures the BFN service is responding. Logs health status.
Restart: pkill -f bfn_watchdog.py && nohup python3 scripts/bfn_watchdog.py &
"""
import os, time, socket, datetime, json

LOG_FILE = "/home/allenai/data/bfn_watchdog.log"
STATE_FILE = "/home/allenai/data/.bfn_state.json"
BFN_HOST = "127.0.0.1"
BFN_PORT = 8094
CHECK_INTERVAL = 30  # seconds

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def check_bfn():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((BFN_HOST, BFN_PORT))
        s.close()
        return True, "Port responding"
    except Exception as e:
        return False, str(e)

def main():
    log("🔍 BFN Watchdog started — monitoring port 8094")
    while True:
        try:
            ok, detail = check_bfn()
            state = {
                "checked_at": datetime.datetime.now().isoformat(),
                "host": BFN_HOST,
                "port": BFN_PORT,
                "status": "UP" if ok else "DOWN",
                "detail": detail
            }
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)

            if ok:
                log("✅ BFN port 8094 responding")
            else:
                log(f"❌ BFN port 8094 down — {detail}")

        except Exception as e:
            log(f"💥 BFN Watchdog error: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
