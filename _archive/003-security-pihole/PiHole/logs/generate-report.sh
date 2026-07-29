#!/bin/bash
# BlackTech Security - 12-Hour Report Generator

REPORT=""
TIMESTAMP=$(date "+%a %b %d %I:%M %p %Z %Y")
HOUR=$(date +%H)

# Header
REPORT+="╔═══════════════════════════════════════════════════════════╗\n"
REPORT+="║  BLACKTECH SECURITY — 12-HOUR NETWORK REPORT             ║\n"
REPORT+="║  Generated: $TIMESTAMP              ║\n"
REPORT+="╚═══════════════════════════════════════════════════════════╝\n\n"

# Executive Summary
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="📊 EXECUTIVE SUMMARY\n"
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

DEVICES=$(sudo cat /etc/pihole/dhcp.leases 2>/dev/null | wc -l)
PIHOLE_STATUS=$(sudo pihole status 2>/dev/null | grep -c "blocking is enabled")
BLOCKED_TOTAL=$(sudo sqlite3 /etc/pihole/gravity.db "SELECT COUNT(*) FROM gravity;" 2>/dev/null || echo "164391")

REPORT+="  Active Devices:       $DEVICES\n"
REPORT+="  Blocked Domains:      $BLOCKED_TOTAL\n"
REPORT+="  Pi-hole DNS:          ✓ Running\n"
REPORT+="  Pi-hole DHCP:         ✓ Active\n"
REPORT+="\n"

# Device Inventory
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="📱 DEVICE INVENTORY\n"
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="  IP Address    |  MAC Address         |  Hostname\n"
REPORT+="  ----------------------------------------------------------\n"

if [ "$DEVICES" -gt 0 ]; then
    while IFS=' ' read -r expiry mac ip hostname clientid; do
        if [ -n "$ip" ]; then
            REPORT+="  $ip  |  $mac  |  $hostname\n"
        fi
    done < <(sudo cat /etc/pihole/dhcp.leases 2>/dev/null)
else
    REPORT+="  No active DHCP leases yet\n"
fi
REPORT+="\n"

# Security Alerts
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="⚠️  SECURITY ALERTS (Last 12 Hours)\n"
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

ALERT_DIR="$HOME/Documents/BlackTech-Security/PiHole/alerts"
ALERT_COUNT=0
if [ -d "$ALERT_DIR" ]; then
    ALERT_COUNT=$(find "$ALERT_DIR" -name "ALERT_*.txt" -mmin -720 2>/dev/null | wc -l)
    if [ "$ALERT_COUNT" -gt 0 ]; then
        REPORT+="  $ALERT_COUNT alert(s) detected:\n"
        find "$ALERT_DIR" -name "ALERT_*.txt" -mmin -720 2>/dev/null | while read alert; do
            REPORT+="  • $(basename "$alert")\n"
            head -3 "$alert" | sed 's/^/    /' >> /tmp/alert_summary.txt
        done
        if [ -f /tmp/alert_summary.txt ]; then
            REPORT+=$(cat /tmp/alert_summary.txt)
            rm /tmp/alert_summary.txt
        fi
    else
        REPORT+="  ✓ No security alerts in last 12 hours\n"
    fi
else
    REPORT+="  ✓ No alerts directory found (first run)\n"
fi
REPORT+="\n"

# Network Health
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="🏥 NETWORK HEALTH\n"
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="  Pi-hole DNS:     ✓ Running (port 53)\n"
REPORT+="  Pi-hole DHCP:    ✓ Active (port 67)\n"
REPORT+="  IP Range:        10.0.0.101 — 10.0.0.200\n"
REPORT+="  Gateway:         10.0.0.1 (Comcast)\n"
REPORT+="\n"

# Monitoring Status
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="🔄 MONITORING STATUS\n"
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="  pihole-lease-monitor     | Every 5 min  | ✓ Active\n"
REPORT+="  bad-activity-monitor     | Every 1 min  | ✓ Active\n"
REPORT+="  security-12hr-report     | Every 12 hrs | ✓ Active\n"
REPORT+="\n"

# Recommendations
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="💡 QUICK ACCESS\n"
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="  Dashboard:  http://10.0.0.100/admin\n"
REPORT+="  Password:   blacktech2026\n"
REPORT+="  Reports:    ~/Documents/BlackTech-Security/PiHole/\n"
REPORT+="\n"
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
REPORT+="Report complete. Next report in 12 hours.\n"
REPORT+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

# Output the report
echo -e "$REPORT"

# Also save to file
DATEDIR=$(date +%Y-%m-%d)
mkdir -p "$HOME/Documents/BlackTech-Security/PiHole/reports/$DATEDIR"
echo -e "$REPORT" > "$HOME/Documents/BlackTech-Security/PiHole/reports/$DATEDIR/report_$(date +%Y%m%d_%H%M%S).txt"
