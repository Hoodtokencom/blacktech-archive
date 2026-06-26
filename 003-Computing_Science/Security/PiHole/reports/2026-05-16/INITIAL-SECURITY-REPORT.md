# BlackTech Security Network Report

**Date:** Saturday, May 16, 2026 — 09:37 AM CDT
**Report Type:** Initial Security Setup Report

---

## 📊 EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| Active Devices | 22 (on WiFi) |
| Pi-hole DNS | ✓ Running |
| Pi-hole DHCP | ✓ Active |
| Blocked Domains | 164,391 unique |
| Custom Blocklists | 4 active |
| Monitoring Jobs | 3 cron jobs running |
| Security Alerts | 4 (port scan alerts) |

---

## 📱 DEVICE INVENTORY (from WiFi scan)

| IP | MAC | Device |
|----|-----|--------|
| 10.0.0.1 | 48:BD:CE:15:DE:1B | Router |
| 10.0.0.10 | 18:EF:3A:F9:26:A0 | Sichuan AI-Link |
| 10.0.0.30 | 64:9A:63:E8:17:50 | Unknown |
| 10.0.0.39 | 34:E6:E6:BD:C6:E6 | Unknown |
| 10.0.0.54 | — | Raspberry Pi (Pi-hole) |
| 10.0.0.66 | 34:E6:E6:05:15:80 | Unknown |
| 10.0.0.78 | 34:E6:E6:FF:52:EB | Unknown |
| 10.0.0.138 | CA:78:5A:66:64:52 | Unknown IoT |
| 10.0.0.147 | 0C:95:05:74:7D:76 | LiftMaster MyQ |
| 10.0.0.155 | DA:8D:93:0E:C3:2A | Unknown |
| 10.0.0.159 | 2C:C3:E6:73:48:81 | Unknown |
| 10.0.0.165 | 04:B9:E3:5C:25:56 | Samsung |
| 10.0.0.176 | 5A:E7:2B:CA:C1:8B | Unknown IoT |
| 10.0.0.182 | FA:46:84:EC:B3:1F | Unknown |
| 10.0.0.189 | 90:48:6C:68:EA:C1 | Ring |
| 10.0.0.191 | 7E:8D:F2:63:8C:E1 | Unknown IoT |
| 10.0.0.207 | 5C:47:5E:35:9B:9A | Ring |
| 10.0.0.220 | 22:1C:7D:18:EA:A3 | Unknown |
| 10.0.0.226 | E2:BB:B7:A2:7D:C5 | Unknown |
| 10.0.0.227 | 90:48:6C:9B:8C:22 | Ring |
| 10.0.0.235 | B0:09:DA:BB:DA:19 | Ring Solutions |
| 10.0.0.236 | 48:A2:E6:C2:CA:D2 | Resideo/Honeywell |

---

## ⚠️ SECURITY FLAGS

### HIGH RISK
- **LiftMaster MyQ (10.0.0.147)** — Port 80 admin panel exposed on LAN. Serial/MAC/SSID visible.
- **Unknown IoT devices (4x)** — Port 49152 open. Possible smart plugs/sensors.

### MEDIUM RISK
- **15 unknown MAC addresses** — Verify these are your devices.

---

## 🚫 BLOCKLISTS ACTIVE

| Blocklist | Domains | Targets |
|-----------|---------|---------|
| StevenBlack base | 82,208 | Ads, trackers, malware |
| Porn/adult | 158,245 | Adult content |
| Gambling + porn | 164,274 | Gambling + adult |
| Drugs/malware | 12,765 | Drugs, exploits |
| Global blocked | 8 | Custom drugs/malware |
| IoT blocked | 8 | Ring/Samsung telemetry |
| Kids safe | 9 | TikTok, Snap, Instagram |
| Work only | 78 | Streaming, gaming, shopping |

**Total:** 164,391 unique blocked domains

---

## 🏥 NETWORK HEALTH

- **Pi-hole DNS:** ✓ Running (port 53)
- **Pi-hole DHCP:** ✓ Active (port 67)
- **IP range:** 10.0.0.101 — 10.0.0.200
- **Gateway:** 10.0.0.1 (Comcast)

---

## 🔄 TRANSITION STATUS

**Current:** Comcast DHCP still active. Pi-hole DHCP also active.
**Result:** Two DHCP servers running — minor conflict risk.
**Resolution needed:** Reboot router or disable Comcast DHCP in Xfinity app.
**Full transition:** Up to 48 hours for all devices to refresh leases.

---

## 📋 MONITORING JOBS

| Job | Frequency | Status |
|-----|-----------|--------|
| pihole-lease-monitor | Every 5 min | Active |
| bad-activity-monitor | Every 1 min | Active |
| security-12hr-report | Every 12 hours | Active (next: 12:00 PM) |

---

## 💡 IMMEDIATE ACTIONS NEEDED

1. **Secure garage door opener** — Change MyQ password, enable 2FA, check firmware updates
2. **Verify unknown devices** — 15 unknown MACs. Check if yours. If not: change WiFi password.
3. **Disable Comcast DHCP** — Use Xfinity app or reboot router.
4. **Review LiftMaster port 80** — Consider disabling admin panel if unused.

---

## 📁 DOCUMENTS

- Dashboard: http://10.0.0.100/admin
- Password: blacktech2026
- Reports: ~/Documents/BlackTech-Security/PiHole/
- Blocklists: ~/Documents/BlackTech-Security/PiHole/blocklists/

---

Report generated: 2026-05-16 09:37 AM CDT
Next report: 2026-05-16 12:00 PM CDT
