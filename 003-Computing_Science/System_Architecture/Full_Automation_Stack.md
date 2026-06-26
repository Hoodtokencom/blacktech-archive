# Blacktech Solutions Corp — Full Automation Stack
## Table of Contents
**Last updated:** May 25, 2026  
**Built on:** Raspberry Pi 5 + External Hard Drive (Blacktech_Drive)

---

## 1. The Brain: Hermes Agent (Pi)
**What it is:** AI assistant running 24/7 on your headless Raspberry Pi
**Location:** `/home/allenai/.hermes/profiles/derrell-black/`
**What it does:**
- Reads/responds to your Telegram messages instantly
- Runs scheduled cron jobs (social, invoices, reminders)
- Executes scripts (browser automation, email, file management)
- Remembers your preferences across sessions (MEMORY.md)

---

## 2. Data Storage Layer

### A) External Hard Drive — Blacktech_Drive
**Mount:** `/media/allenai/Expansion/Blacktech_Drive/`
**Purpose:** All business files live here, not on the Pi

| Folder | What's Inside |
|--------|---------------|
| `1-Admin/` | Invoices, estimates, reports, checklists, lead files |
| `1-Admin/QBO_Reports/` | Invoice templates, London Town schedule, Electrification estimate |
| `1-Admin/Leads/` | Contact files (e.g., `Ali_Khalifa_60482.md`) |
| `1-Admin/System_Architecture/` | This document |
| *(other folders exist)* | Marketing, accounting, project files |

### B) Pi Local Storage
**Path:** `~/.hermes/profiles/derrell-black/`
| File | Purpose |
|------|---------|
| `scripts/` | Python scripts (QBO checker, email bots, social generators) |
| `qbo_cookies.json` | Session cookies for QuickBooks Online automation |
| `.env.qbo` | QBO login credentials |
| `cache/images/` | Screenshots and images you send via Telegram |

---

## 3. Communication Layer

### A) Email System (HostGator)
**Server:** `mail.blacktechsolutionscorp.com`
**Password:** `Newproject26$`

| Address | Status | Forwards To | Auto-Reply? |
|---------|--------|-------------|-------------|
| `support@blacktechsolutionscorp.com` | ACTIVE | — (primary) | No |
| `vendors@blacktechsolutionscorp.com` | ACTIVE | `support@` | No |
| `invoices@blacktechsolutionscorp.com` | ACTIVE | `support@` | Yes ✅ |
| `automation@blacktechsolutionscorp.com` | ACTIVE | — (Zapier/tools) | No |

**How the Pi uses email:**
- Checks `invoices@` for payment notifications
- Sends invoice reminders (e.g., Cleo, Production Down)
- Sends lead follow-ups (e.g., Ali Khalifa)
- Alerts you via Telegram for real customer emails

### B) Telegram (Right Now)
**Your main interface** to the Pi. You text the Pi, it does the work.

### C) Zapier — Facebook Auto-Post
**What it is:** Bridge between the Pi and Facebook
**How it works:**
1. Pi writes a social post
2. Pi sends it via `curl` to a Zapier webhook URL
3. Zapier pushes it to Blacktech's Facebook Page
**Status:** ⚠️ Broken — webhook returned "please unsubscribe me" — needs rebuild

### D) Twilio — (NOT YET SET UP)
**Status:** ❌ Not configured
**What it would do:** Send SMS text messages to leads/customers directly from the Pi
**What you'd need:** Twilio account, phone number, API key

### E) Cloudflare — (NOT YET SET UP)
**Status:** ❌ Not configured
**What it would do:**
- Host your website/landing page
- Tunnel into your Pi from outside your home network (Cloudflare Tunnel)
- Protect against spam/bots
- Custom domain: `blacktechsolutionscorp.com`

---

## 4. Business Layer

### A) QuickBooks Online (QBO)
**What it is:** Your accounting + invoicing system
**How Pi connects:**
- Browser automation with Playwright + saved cookies
- Reads QBO cookie file from laptop (you export from Edge on laptop, paste into Telegram)

**What the Pi does:**
- Searches invoices (e.g., "Does Robbins invoice exist?")
- Generates invoice templates (London Town, Electrification)
- Monitors overdue invoices (daily report)
- ⚠️ Creating invoices is still manual on laptop (Playwright too fragile)

**Manual steps for QBO cookie refresh:**
1. Log in to QBO on laptop
2. Export cookies from Edge DevTools
3. Paste into Telegram
4. Pi saves to `qbo_cookies.json`

### B) Invoice & Collections Tracking
**What you've built:**
- `London_Town_Invoices_Template.md` — 15 invoices × $9,200 = $138,000
- `Electrification_Rough_In_15_Units.md` — 15 units × $9,488 = $142,313
- `Invoice_Submission_Checklist.md` — Drexel/Dorchester tracker

**Collections workflow:**
- Pi runs daily check → texts you total overdue count + dollar amount
- You say "mark paid" or "void" → Pi updates QBO status

---

## 5. Marketing Automation Layer

### A) Daily Social Posts
**Cronjob:** `blacktech-daily-social` — runs at **8 AM every day**
**What it does:**
- Writes a Facebook post about electrical services
- ⚠️ Currently broken (Zapier webhook dead)
- Normally would auto-post; for now Pi texts you the draft to copy/paste

### B) Weekly Batch Content
**Cronjob:** `blacktech-weekly-batch` — runs at **7 AM Mondays**
**What it does:** Generates full week of social media + Mailchimp content

### C) Saturday Post
**Cronjob:** `blacktech-social-saturday` — runs at **10 AM Saturdays**
**What it does:** Weekend-themed electrical post

### D) Mailchimp Daily Email
**Cronjob:** `blacktech-daily-mailchimp` — runs at **9 AM every day**
**What it does:** Drafts a daily email for Mailchimp list

### E) Monthly Newsletter
**Cronjob:** `blacktech-monthly-newsletter` — runs at **9 AM on the 1st**
**What it does:** Builds full monthly email

---

## 6. System Monitoring & Security

| Cronjob | Schedule | What It Checks |
|---------|----------|----------------|
| Weekly Network Security Scan | Sundays at 4 AM | Pi security status |
| 4AM Network Status Report | Daily at 4 AM | Pi CPU, memory, disk usage |
| Daily Invoice Report | Daily at 8 AM | QBO overdue invoices + text alert |

---

## 7. Lead Management Workflow

**Example: Ali Khalifa (LG Pro Dealer)**
1. **Lead comes in** (screenshot from LG Pro Dealer) → sent to Telegram
2. **Pi reads it** → drafts email → you approve
3. **Pi sends email** from `support@blacktechsolutionscorp.com`
4. **Pi saves contact** to `/Blacktech_Drive/1-Admin/Leads/`
5. **Pi sets reminder** — call at scheduled time tomorrow
6. **Cronjob fires** → Pi reminds you in Telegram

---

## 8. How It All Connects

```
YOU (Laptop / Phone)
        │
        ├─── Telegram ───> Hermes Agent (Pi)
        │                      │
        │                      ├─ Cronjobs (social, invoices, reminders)
        │                      ├─ Scripts (email, QBO, file management)
        │                      └─ Memory (your preferences)
        │
        ├─── Email ──────> HostGator (support@ / vendors@ / invoices@ / automation@)
        │                      │
        │                      └─ Forwarded to one inbox
        │
        ├─── QuickBooks ─> QBO Online (invoicing, payments)
        │                      │
        │                      └─ Pi connects via Edge cookies
        │
        └─── Facebook ───> Zapier webhook (currently broken)
                               │
                               └─ Posts to Blacktech Facebook Page

EXTERNAL DRIVE
        └─ All business files, templates, leads, reports
```

---

## 9. What's Working vs. What's Broken

| System | Status | Notes |
|--------|--------|-------|
| Hermes Agent (Pi) | ✅ Working | 24/7, answers instantly |
| Telegram messaging | ✅ Working | Your primary interface |
| Email (send/receive) | ✅ Working | Sends from Pi, checks inboxes |
| Email forwarding | ✅ Working | invoices@ + vendors@ → support@ |
| Email auto-reply | ✅ Working | invoices@ auto-replies now |
| QBO cookie login | ✅ Working | Fresh cookies from laptop |
| QBO invoice search | ✅ Working | Pi can find invoices |
| QBO create invoice | ❌ Broken | Too fragile; do it manually on laptop |
| Zapier → Facebook | ❌ Broken | Webhook dead; needs rebuild |
| Twilio SMS | ❌ Not set up | Would cost ~$15/month |
| Cloudflare | ❌ Not set up | Website security + Pi tunneling |
| Google Drive sync | ❌ Not done | Could sync external drive to cloud |
| Formspree | ⚠️ Needs upgrade | Hit free limit; needs Gold tier |

---

## 10. Next Priorities

1. **Rebuild Zapier webhook** using `automation@blacktechsolutionscorp.com` ✅
2. **Formspree upgrade** to Gold for file attachments ✅
3. **Google Drive sync** for Drexel/Dorchester files
4. **Twilio setup** if you want SMS lead alerts
5. **Cloudflare tunnel** to access Pi from anywhere
6. **Website landing page** for Blacktech
7. **QBO invoice creation** via more reliable script

---

*Document maintained by Hermes Agent — ask "Update the stack doc" to refresh.*
