#!/usr/bin/env python3
"""
Pipeline Monitor — Checks recent Triple-Play pipeline runs from SQLite.
Reports: last run time, success rate, total cost today, avg latency.
Usage: python3 scripts/pipeline_monitor.py
"""
import sqlite3, os, json, datetime

DB_PATH = "/home/allenai/data/blacktech.db"

def main():
    print("📊 Pipeline Monitor Report")
    print("=" * 40)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(
            """SELECT task_id, task_type, gemini_status, ollama_status, claude_status, total_cost, created_at
               FROM pipeline_results ORDER BY id DESC LIMIT 10"""
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            print("No pipeline runs found.")
            return

        total_cost = 0.0
        success = 0
        for r in rows:
            tid, ttype, g, o, c, cost, ts = r
            total_cost += float(cost) if cost else 0
            if g == "completed" and o in ("completed", "skipped"):
                success += 1
            status_icon = "✅" if g == "completed" else "❌"
            print(f"{status_icon} #{tid} | {ttype} | G:{g} O:{o} C:{c} | ${float(cost):.6f} | {ts}")

        print("=" * 40)
        print(f"Runs checked: {len(rows)} | Success rate: {success}/{len(rows)} | Total cost: ${total_cost:.6f}")

        # Write state for dashboard
        state = {
            "checked_at": datetime.datetime.now().isoformat(),
            "last_10": len(rows),
            "success_rate": f"{success}/{len(rows)}",
            "total_cost_10": round(total_cost, 6)
        }
        with open("/home/allenai/data/.monitor_state.json", "w") as f:
            json.dump(state, f)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
