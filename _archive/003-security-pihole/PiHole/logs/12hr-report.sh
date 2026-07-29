#!/bin/bash
# BlackTech Security - 12-Hour Network Report
# Generated: $(date)

REPORTDIR="$HOME/Documents/BlackTech-Security/PiHole/reports"
DATEDIR="$(date +%Y-%m-%d)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="$REPORTDIR/$DATEDIR/12hr-report_$TIMESTAMP.txt"

mkdir -p "$REPORTDIR/$DATEDIR"

echo "╔═══════════════════════════════════════════════════════════╗" > "$REPORT_FILE"
echo "║  BLACKTECH SECURITY — 12-HOUR NETWORK REPORT             ║" >> "$REPORT_FILE"
echo "║  Generated: $(date)                                      ║" >> "$REPORT_FILE"
echo "╚═══════════════════════════════════════════════════════════╝" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 1. EXECUTIVE SUMMARY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
echo "📊 EXECUTIVE SUMMARY" >> "$REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"

ACTIVE_DEVICES=$(cat /etc/pihole/dhcp.leases 2>/dev/null | wc -l)
BLOCKED_TOTAL=$(grep -c "gravity_blocked" /var/log/pihole/pihole.log 2>/dev/null)
UNIQUE_BLOCKED=$(grep "gravity_blocked" /var/log/pihole/pihole.log 2>/dev/null | awk '{print $6}' | sort -u | wc -l)
TOTAL_QUERIES=$(wc -l < /var/log/pihole/pihole.log 2>/dev/null)

echo "  Active Devices:       $ACTIVE_DEVICES" >> "$REPORT_FILE"
echo "  Total DNS Queries:    $TOTAL_QUERIES" >> "$REPORT_FILE"
echo "  Blocked Queries:      $BLOCKED_TOTAL" >> "$REPORT_FILE"
echo "  Unique Blocked Domains: $UNIQUE_BLOCKED" >> "$REPORT_FILE"
echo "  Block Rate:           $(awk "BEGIN {printf \"%.1f%%\", ($BLOCKED_TOTAL/$TOTAL_QUERIES)*100}")" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 2. DEVICE INVENTORY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
echo "📱 DEVICE INVENTORY" >> "$REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
echo "  IP Address    |  MAC Address         |  Hostname" >> "$REPORT_FILE"
echo "  ----------------------------------------------------------" >> "$REPORT_FILE"
cat /etc/pihole/dhcp.leases 2>/dev/null | awk '{printf "  %-13s | %-20s | %s\n", $3, $2, $4}' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 3. TOP BLOCKED CATEGORIES
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
echo "🚫 TOP BLOCKED DOMAINS" >> "$REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
grep "gravity_blocked" /var/log/pihole/pihole.log 2>/dev/null | awk '{print $6}' | sort | uniq -c | sort -rn | head -15 | awk '{printf "  %-5s | %s\n", $1, $2}' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 4. TOP QUERY SOURCES
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
echo "🔍 TOP QUERY SOURCES (By Device)" >> "$REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
tail -n 2000 /var/log/pihole/pihole.log 2>/dev/null | grep -oP 'from \K[0-9.]+' | sort | uniq -c | sort -rn | head -10 | awk '{printf "  %-5s queries | %s\n", $1, $2}' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 5. SECURITY ALERTS
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
echo "⚠️  SECURITY ALERTS (Last 12 Hours)" >> "$REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"

# Check for alerts in last 12 hours
ALERT_COUNT=$(find $HOME/Documents/BlackTech-Security/PiHole/alerts/$DATEDIR/ -name "ALERT_*.txt" -mmin -720 2>/dev/null | wc -l)
if [ "$ALERT_COUNT" -gt 0 ]; then
    echo "  $ALERT_COUNT alert(s) detected in last 12 hours:" >> "$REPORT_FILE"
    find $HOME/Documents/BlackTech-Security/PiHole/alerts/$DATEDIR/ -name "ALERT_*.txt" -mmin -720 2>/dev/null | while read alert; do
        echo "  - $(basename $alert)" >> "$REPORT_FILE"
        head -3 "$alert" >> "$REPORT_FILE"
    done
else
    echo "  ✓ No security alerts in last 12 hours" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 6. AFTER-HOURS ACTIVITY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
echo "🌙 AFTER-HOURS ACTIVITY (10PM - 6AM)" >> "$REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
NIGHT_QUERIES=$(grep "$(date +%Y-%m-%d)" /var/log/pihole/pihole.log 2>/dev/null | grep -E " (2[2-3]|0[0-5]):" | wc -l)
echo "  Night-time queries (today): $NIGHT_QUERIES" >> "$REPORT_FILE"
if [ "$NIGHT_QUERIES" -gt 100 ]; then
    echo "  ⚠ Elevated night activity detected" >> "$REPORT_FILE"
    grep "$(date +%Y-%m-%d)" /var/log/pihole/pihole.log 2>/dev/null | grep -E " (2[2-3]|0[0-5]):" | grep -oP 'from \K[0-9.]+' | sort | uniq -c | sort -rn | head -5 >> "$REPORT_FILE"
else
    echo "  ✓ Normal night activity" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 7. NETWORK HEALTH
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
echo "🏥 NETWORK HEALTH" >> "$REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"

# Pi-hole status
if sudo systemctl is-active --quiet pihole-FTL 2>/dev/null; then
    echo "  Pi-hole DNS:     ✓ Running" >> "$REPORT_FILE"
else
    echo "  Pi-hole DNS:     ✗ STOPPED" >> "$REPORT_FILE"
fi

# DHCP status
if sudo ss -ulnp | grep -q ':67'; then
    echo "  Pi-hole DHCP:    ✓ Active" >> "$REPORT_FILE"
else
    echo "  Pi-hole DHCP:    ✗ Inactive" >> "$REPORT_FILE"
fi

# Blocked domains count
BLOCKLIST_COUNT=$(sqlite3 /etc/pihole/gravity.db "SELECT COUNT(*) FROM gravity;" 2>/dev/null)
echo "  Blocked Domains: $BLOCKLIST_COUNT" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 8. RECOMMENDATIONS
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
echo "💡 RECOMMENDATIONS" >> "$REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"

if [ "$ACTIVE_DEVICES" -gt 25 ]; then
    echo "  • High device count ($ACTIVE_DEVICES) — review for unauthorized devices" >> "$REPORT_FILE"
fi
if [ "$BLOCKED_TOTAL" -gt 10000 ]; then
    echo "  • High block rate — consider stricter filtering on entertainment devices" >> "$REPORT_FILE"
fi
if [ "$UNIQUE_BLOCKED" -gt 100 ]; then
    echo "  • Diverse blocked domains — potential sign of browsing variety" >> "$REPORT_FILE"
fi
echo "  • Dashboard: http://10.0.0.100/admin" >> "$REPORT_FILE"
echo "  • Password: blacktech2026" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"
echo "Report complete. Next report in 12 hours." >> "$REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$REPORT_FILE"

# Output for cron delivery
cat "$REPORT_FILE"