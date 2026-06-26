#!/usr/bin/env python3
"""
AI Toll Meter — Clean auto-updating tracker
Reads from pipeline DB + manual entries, writes a clean JSON + text file
"""
import json, sqlite3, os
from datetime import datetime

TOLL_JSON   = "/home/allenai/data/ai_toll_meter.json"
TOLL_TXT    = "/home/allenai/data/ai_toll_meter.txt"
DB_PATH     = "/home/allenai/data/blacktech.db"

def load_manual():
    """Load manual session entries (stored in JSON)."""
    try:
        with open(TOLL_JSON) as f:
            return json.load(f)
    except:
        return {"manual_entries": [], "last_updated": None}

def save_json(data):
    with open(TOLL_JSON, "w") as f:
        json.dump(data, f, indent=2)

def get_pipeline_costs():
    """Pull costs from pipeline DB grouped by date."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(
            "SELECT date(created_at), SUM(total_cost), COUNT(*) "
            "FROM pipeline_results GROUP BY date(created_at) ORDER BY date(created_at)"
        )
        rows = [{"date": r[0], "cost": round(r[1] or 0, 6), "runs": r[2]} for r in cur.fetchall()]
        conn.close()
        return rows
    except:
        return []

def add_manual_entry(date, task, cost):
    """Add a manual entry (called from outside)."""
    data = load_manual()
    data["manual_entries"].append({
        "date": date,
        "task": task,
        "cost": round(cost, 6)
    })
    data["last_updated"] = datetime.now().isoformat()
    save_json(data)
    rebuild()

def rebuild():
    """Rebuild the toll meter text file from DB + manual entries."""
    data        = load_manual()
    manual      = data.get("manual_entries", [])
    pipeline    = get_pipeline_costs()

    # Combine all entries
    all_entries = []
    for e in manual:
        all_entries.append({
            "date":   e["date"],
            "source": "manual",
            "task":   e["task"],
            "cost":   e["cost"],
            "runs":   1
        })
    for p in pipeline:
        all_entries.append({
            "date":   p["date"],
            "source": "pipeline",
            "task":   f"Pipeline runs ({p['runs']} tasks)",
            "cost":   p["cost"],
            "runs":   p["runs"]
        })

    all_entries.sort(key=lambda x: x["date"] or "")
    running = 0.0
    lines   = []
    lines.append("╔══════════════════════════════════════════════════════════════════╗")
    lines.append("║              🚗  AI TOLL METER — Blacktech Solutions  🚗         ║")
    lines.append("║           Auto-updating · Pipeline + Manual sessions             ║")
    lines.append("╠══════════════════╦══════════════════════════════════╦═══════╦═══════╣")
    lines.append("║  DATE            ║  TASK                            ║  COST ║ TOTAL ║")
    lines.append("╠══════════════════╬══════════════════════════════════╬═══════╬═══════╣")

    for e in all_entries:
        running += e["cost"]
        src_tag = "🤖" if e["source"] == "pipeline" else "👤"
        task_str = (e["task"][:32] + "..") if len(e["task"]) > 34 else e["task"]
        lines.append(
            f"║  {e['date'] or 'Unknown':16}║ {src_tag} {task_str:<32} ║ ${e['cost']:>5.4f}║ ${running:>5.4f}║"
        )

    lines.append("╠══════════════════╩══════════════════════════════════╩═══════╩═══════╣")
    lines.append(f"║  💰 TOTAL AI SPEND:  ${running:>8.4f}                                ║")
    lines.append(f"║  📅 Last updated:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):20}                   ║")
    lines.append("╚══════════════════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append("📊 SOURCES:")
    lines.append("  🤖 Pipeline — auto-tracked from blockchain/AI pipeline runs")
    lines.append("  👤 Manual   — recorded from Hermes chat sessions")
    lines.append("")
    lines.append(f"TOTAL=${running:.6f}")  # machine-readable last line for /api/telemetry

    with open(TOLL_TXT, "w") as f:
        f.write("\n".join(lines))

    # Update JSON with totals
    data["total"] = round(running, 6)
    data["last_updated"] = datetime.now().isoformat()
    data["pipeline_total"] = round(sum(p["cost"] for p in pipeline), 6)
    data["manual_total"]   = round(sum(e["cost"] for e in manual), 6)
    save_json(data)

    print(f"✅ Toll meter rebuilt — Total: ${running:.4f} | Entries: {len(all_entries)}")
    return running

if __name__ == "__main__":
    rebuild()
