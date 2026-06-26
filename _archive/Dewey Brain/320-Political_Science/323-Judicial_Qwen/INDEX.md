# 323 — Judicial Branch (Qwen 1.5B-65K)

**Dewey Class:** 323 — Judicial  
**Authority:** Security sweeps, schedule cleaning, system audits  
**Model:** Qwen 2.5 1.5B-65K — runs LOCAL on Raspberry Pi  
**Cron:** `Qwen Security Sweep` → daily midnight (0 0 * * *)

---

## Responsibilities

- 🧹 Clean temp files (>7 days old)
- 📄 Rotate and trim logs over 50MB
- 🔍 Verify Ollama models present
- 💾 Monitor disk usage
- 🧠 Monitor RAM usage
- ⚠️ Detect zombie processes
- ✅ Verify critical service ports (8090, 8111, 8095)
- 📂 Verify data directory integrity
- 🏛️ Constitutional guard — cannot modify Constitutional or delete Body files

## Restrictions

- **No constitutional modifications** — 323 may only read and audit
- **No Body file deletions** — 323 may clean /tmp and logs only
- **No override authority** — 323 reports findings, Executive decides action

## Cron Job

- **ID:** 230688f5dab4
- **Schedule:** `0 0 * * *` (daily midnight)
- **Script:** `/home/allenai/scripts/qwen_security.py`
- **Model:** qwen2.5-1.5b-65k (local Ollama)
- **Deliver:** local (silent)
- **Log:** `/home/allenai/data/qwen_security_log.txt`

## Latest Sweep Status

- Disk: 32% used (76GB free)
- RAM: 3.2GB/7.9GB
- Ports: All 3 up (8090, 8111, 8095)
- Zombies: 3 (normal for Pi)