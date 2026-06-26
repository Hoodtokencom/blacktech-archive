# BlackTech Security - Bad Activity Monitor

## Overview
Runs every minute to detect suspicious network activity.

## What It Detects

### 1. Unauthorized Devices
- New MAC addresses joining the network
- Alerts immediately if unknown device connects
- Maintains baseline of known devices

### 2. Blocked Query Attempts
- Tracks attempts to access blocked domains
- Top blocked domains logged
- Pattern analysis for repeat offenders

### 3. After-Hours Activity (10PM - 6AM)
- Detects active devices during night hours
- Tracks which devices are making DNS queries
- Flags unusual late-night activity

### 4. High-Volume Queries
- Monitors query volume per device
- Flags devices making 100+ queries per scan cycle
- Possible indicators: malware, botnet, crypto mining

### 5. Suspicious Ports
- Scans for open ports commonly used by attackers
- Monitors: SSH(22), Telnet(23), SMB(445), RDP(3389), VNC(5900)
- Alerts if any found open on internal devices

## Alert Delivery
- **Immediate:** Telegram message when threat detected
- **Dashboard:** http://10.0.0.100/admin
- **Logs:** ~/Documents/BlackTech-Security/PiHole/logs/
- **Alerts:** ~/Documents/BlackTech-Security/PiHole/alerts/

## Response Actions

### New Device Detected
1. Check dashboard → Group Management → Clients
2. Identify device by IP/MAC
3. If unauthorized: Change WiFi password immediately
4. If authorized: Add to appropriate group

### High-Volume Queries
1. Identify device IP from alert
2. Check what domains it's querying
3. Isolate device from network if suspicious
4. Run malware scan on affected device

### After-Hours Activity
1. Check which device is active
2. Verify if it's a known scheduled task
3. If suspicious: Block device in Pi-hole groups

### Suspicious Ports
1. Identify which device has port open
2. Determine if service is intentional
3. If not: Disconnect device, investigate

## Cron Jobs Active
| Job | Frequency | Purpose |
|-----|-----------|---------|
| pihole-lease-monitor | Every 5 min | DHCP leases + DNS queries |
| bad-activity-monitor | Every 1 min | Threat detection + alerts |

## Files
- Monitor script: `~/Documents/BlackTech-Security/PiHole/logs/bad-activity-monitor.sh`
- Logs: `~/Documents/BlackTech-Security/PiHole/logs/YYYY-MM-DD/`
- Reports: `~/Documents/BlackTech-Security/PiHole/reports/YYYY-MM-DD/`
- Alerts: `~/Documents/BlackTech-Security/PiHole/alerts/YYYY-MM-DD/`
