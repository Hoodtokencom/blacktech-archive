# 🎯 8→10 CHECKLIST — Blacktech Systems Hardening

**Your current score: 8/10**  
**Goal: 10/10 — Bulletproof, Self-Healing, Enterprise-Grade**

**Last updated:** June 6, 2026  
**Location:** `8-Misc/8_to_10_Checklist.md` on Blacktech Drive

---

## 🔴 PHASE 1: STOP THE BLEEDING (Do This Week)

| # | Task | Why | How Hard | Status |
|---|------|-----|----------|--------|
| 1 | **Install service watchdog** | BFN/Finance/ComEd died today — you had to manually restart them | Easy | ☐ |
| 2 | **Add Telegram alerts for downtime** | Find out a service is dead BEFORE you try to use it | Easy | ☐ |
| 3 | **Encrypt API keys** | Claude + Gemini keys are in plain text env vars — if Pi is stolen, keys are gone | Medium | ☐ |
| 4 | **Auto-backup scripts to Blacktech Drive weekly** | Right now you copy-paste manually — cron should do it | Easy | ☐ |

---

## 🟡 PHASE 2: HARDEN THE FOUNDATION (Do This Month)

| # | Task | Why | How Hard | Status |
|---|------|-----|----------|--------|
| 5 | **Get SSL certificates (HTTPS)** | Every app is HTTP — not safe for customer data or login pages | Medium | ☐ |
| 6 | **Move from JSON files to SQLite database** | JSON will corrupt at scale — SQLite is free, built into Python | Medium | ☐ |
| 7 | **Add user authentication** | Anyone with the URL can open your apps right now | Medium | ☐ |
| 8 | **Set up log rotation** | Server logs grow forever — they will fill your Pi SD card | Easy | ☐ |

---

## 🟢 PHASE 3: SCALE TO ENTERPRISE (Do When Revenue Justifies)

| # | Task | Why | How Hard | Status |
|---|------|-----|----------|--------|
| 9 | **CI/CD auto-deploy** | Push code → tests run → auto-deploy to Pi — no manual restart | Hard | ☐ |
| 10 | **Backup Pi (redundancy)** | If main Pi dies, backup Pi takes over in < 30 seconds | Hard | ☐ |
| 11 | **PostgreSQL central database** | SQLite is good for 1 user — PostgreSQL handles 100+ | Hard | ☐ |
| 12 | **Load balancer + clustering** | Multiple Pi's sharing work — true enterprise scale | Hard | ☐ |

---

## 📋 PHASE 1 DETAIL — STEP BY STEP

### 1. Service Watchdog (THIS WEEK)

**What it does:** Every 5 minutes, pings all your ports. If one is dead, kills the old process and restarts it.

**File to create:** `/home/allenai/watchdog.sh`

```bash
#!/bin/bash
# Blacktech Service Watchdog
# Add to crontab: */5 * * * * /home/allenai/watchdog.sh

PORTS="8090 8091 8092 8093 8094 8095 8080 8081 5678"
for PORT in $PORTS; do
  if ! curl -s -o /dev/null http://localhost:$PORT/; then
    # Service is dead — restart it
    case $PORT in
      8090) fuser -k 8090/tcp 2>/dev/null; sleep 2; cd /home/allenai && nohup python3 command_center_server.py > /tmp/cc.log 2>&1 & ;;
      8094) fuser -k 8094/tcp 2>/dev/null; sleep 2; cd /home/allenai && nohup python3 bluewednesday_server.py > /tmp/bfn.log 2>&1 & ;;
      # Add other ports...
    esac
    echo "$(date): Restarted port $PORT" >> /tmp/watchdog.log
  fi
done
```

---

### 2. Telegram Downtime Alerts (THIS WEEK)

**What it does:** When watchdog detects a dead service, sends you a Telegram message instantly.

**Add to watchdog script:**
```bash
BOT_TOKEN="your-bot-token"
CHAT_ID="your-chat-id"
curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
  -d "chat_id=$CHAT_ID" \
  -d "text=🚨 ALERT: Port $PORT is DOWN on Blacktech Pi. Auto-restarting now."
```

---

### 3. Encrypt API Keys (THIS WEEK)

**What it does:** Store Claude + Gemini keys in an encrypted file, not plain text.

**Tool:** `cryptography` Python library

```bash
pip install cryptography
```

**Script:** `/home/allenai/scripts/encrypt_keys.py`
- Reads keys from user input
- Encrypts with a master password
- Saves to `/home/allenai/data/.keys.enc`
- Pipeline scripts decrypt at runtime

---

### 4. Auto-Backup to Blacktech Drive (THIS WEEK)

**What it does:** Every Sunday at 3 AM, copies all `.py` scripts, `.html` files, and data to Blacktech Drive.

**Cron job:**
```bash
0 3 * * 0 rsync -av /home/allenai/*.py /home/allenai/*.html /home/allenai/data/ /media/allenai/Expansion/Blacktech_Drive/6-Operations/AI_Pipeline/backup_$(date +\%Y\%m\%d)/
```

---

## 📋 PHASE 2 DETAIL

### 5. SSL / HTTPS (THIS MONTH)

**Options:**
- **Cloudflare Origin Certificates** (free, easiest) — install cert on Pi, Cloudflare proxies HTTPS
- **Let's Encrypt** (free, harder) — certbot renews every 90 days

**Result:** `https://command.blacktechsolutionscorp.com` instead of `http://`

---

### 6. SQLite Database (THIS MONTH)

**Replace all JSON files:**
- `/home/allenai/data/bfn_shared.json` → SQLite
- `/home/allenai/data/ai_toll_meter.txt` → SQLite table
- `/home/allenai/data/comed_leads.json` → SQLite

**Benefits:**
- No file corruption
- Query data with SQL
- Multiple apps can read/write safely

---

### 7. User Login (THIS MONTH)

**Simple approach:** PIN codes per user
- Admin PIN: `BLACKTECH2026`
- Guest PIN: read-only access
- Store hashed PINs in SQLite

**Result:** Apps show login screen before content loads.

---

## 🏆 THE 10/10 DEFINITION

| Score | Meaning |
|-------|---------|
| **8/10** (NOW) | Everything works when you turn it on. You have to babysit it. |
| **9/10** (Phase 1+2) | Everything fixes itself. You get alerts. Data is encrypted. HTTPS everywhere. |
| **10/10** (All phases) | Zero manual intervention. Push code, it deploys. Pi dies, backup takes over. Scale to 100 users. |

---

## 💰 ESTIMATED COST TO GET TO 10/10

| Phase | Cost | Time |
|-------|------|------|
| Phase 1 (Watchdog + Alerts + Encryption + Backup) | **$0** | 1 weekend |
| Phase 2 (SSL + SQLite + Auth + Logs) | **$0** | 2 weekends |
| Phase 3 (CI/CD + Redundancy + PostgreSQL) | **~$150** (2nd Pi + SSD) | 1 month |

---

## ✅ NEXT ACTION

**Pick ONE thing from Phase 1 and do it this weekend.**  
Don't try to do all 12 at once.

**Recommended:** Start with **#1 Watchdog** — it stops the pain of dead services immediately.

---

**Questions?** Ask me to build any of these step-by-step, one item at a time. 👊
