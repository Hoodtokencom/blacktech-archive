#!/bin/bash
# BlackTech Security - Bad Activity Monitor v3
# Silent mode: all output to files only, nothing to Telegram

LOGDIR="$HOME/Documents/BlackTech-Security/PiHole/logs"
REPORTDIR="$HOME/Documents/BlackTech-Security/PiHole/reports"
ALERTDIR="$HOME/Documents/BlackTech-Security/PiHole/alerts"
DATEDIR="$(date +%Y-%m-%d)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
HOUR="$(date +%H)"

mkdir -p "$LOGDIR/$DATEDIR"
mkdir -p "$REPORTDIR/$DATEDIR"
mkdir -p "$ALERTDIR/$DATEDIR"

# Fresh alert file each run — no stacking
ALERT_FILE="$ALERTDIR/$DATEDIR/ALERT_$TIMESTAMP.txt"
REPORT_FILE="$REPORTDIR/$DATEDIR/network-scan_$TIMESTAMP.txt"
DEDUP_FILE="$ALERTDIR/dedup.txt"
MASTER_LOG="$LOGDIR/security-events.log"

# Initialize empty alert
> "$ALERT_FILE"

echo "=== BLACKTECH SECURITY NETWORK SCAN === $TIMESTAMP ===" > "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 1. UNAUTHORIZED DEVICES
echo "[1] CHECKING FOR NEW DEVICES..." >> "$REPORT_FILE"
CURRENT_DEVICES=$(sudo -n cat /etc/pihole/dhcp.leases 2>/dev/null | wc -l)
KNOWN_DEVICES_FILE="$LOGDIR/known_devices.txt"

if [ ! -f "$KNOWN_DEVICES_FILE" ]; then
    sudo -n cat /etc/pihole/dhcp.leases 2>/dev/null | awk '{print $2}' | sort > "$KNOWN_DEVICES_FILE"
    echo "  Initial device list created." >> "$REPORT_FILE"
else
    NEW_DEVICES=$(comm -13 <(sort "$KNOWN_DEVICES_FILE") <(sudo -n cat /etc/pihole/dhcp.leases 2>/dev/null | awk '{print $2}' | sort))
    if [ -n "$NEW_DEVICES" ]; then
        echo "  ⚠ NEW DEVICE DETECTED:" >> "$REPORT_FILE"
        echo "$NEW_DEVICES" >> "$REPORT_FILE"
        echo "NEW_DEVICE|$TIMESTAMP|$NEW_DEVICES" >> "$ALERT_FILE"
        echo "$(date '+%Y-%m-%d %H:%M:%S') | NEW_DEVICE | $NEW_DEVICES" >> "$MASTER_LOG"
    else
        echo "  ✓ No new devices" >> "$REPORT_FILE"
    fi
    sudo -n cat /etc/pihole/dhcp.leases 2>/dev/null | awk '{print $2}' | sort > "$KNOWN_DEVICES_FILE"
fi
echo "" >> "$REPORT_FILE"

# 2. BLOCKED QUERIES
echo "[2] BLOCKED QUERY ANALYSIS..." >> "$REPORT_FILE"
BLOCKED_COUNT=$(sudo -n grep "gravity_blocked" /var/log/pihole/pihole.log 2>/dev/null | wc -l)
echo "  Total blocked queries in log: $BLOCKED_COUNT" >> "$REPORT_FILE"
echo "  Top blocked domains:" >> "$REPORT_FILE"
sudo -n grep "gravity_blocked" /var/log/pihole/pihole.log 2>/dev/null | awk '{print $6}' | sort | uniq -c | sort -rn | head -10 >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 3. AFTER-HOURS ACTIVITY (10PM - 6AM)
echo "[3] AFTER-HOURS ACTIVITY CHECK..." >> "$REPORT_FILE"
if [ "$HOUR" -ge 22 ] || [ "$HOUR" -le 6 ]; then
    ACTIVE_DEVICES=$(sudo -n cat /etc/pihole/dhcp.leases 2>/dev/null | wc -l)
    echo "  ⚠ AFTER HOURS ($HOUR:00) - $ACTIVE_DEVICES devices active" >> "$REPORT_FILE"
    RECENT_QUERIES=$(tail -n 100 /var/log/pihole/pihole.log 2>/dev/null | grep -oP 'from \K[0-9.]+' | sort | uniq -c | sort -rn)
    if [ -n "$RECENT_QUERIES" ]; then
        echo "  Recent query sources:" >> "$REPORT_FILE"
        echo "$RECENT_QUERIES" >> "$REPORT_FILE"
        echo "AFTER_HOURS|$TIMESTAMP|$HOUR:00|$ACTIVE_DEVICES devices" >> "$ALERT_FILE"
        echo "$(date '+%Y-%m-%d %H:%M:%S') | AFTER_HOURS | $HOUR:00 | $ACTIVE_DEVICES devices" >> "$MASTER_LOG"
    fi
else
    echo "  ✓ Business hours ($HOUR:00)" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 4. HIGH-VOLUME QUERY SOURCES
echo "[4] HIGH-VOLUME QUERY SOURCES..." >> "$REPORT_FILE"
tail -n 500 /var/log/pihole/pihole.log 2>/dev/null | grep -oP 'from \K[0-9.]+' | sort | uniq -c | sort -rn | head -10 >> "$REPORT_FILE"
HIGH_VOLUME=$(tail -n 500 /var/log/pihole/pihole.log 2>/dev/null | grep -oP 'from \K[0-9.]+' | sort | uniq -c | sort -rn | head -1 | awk '{print $1}')
if [ -n "$HIGH_VOLUME" ] && [ "$HIGH_VOLUME" -gt 200 ]; then
    SUSPICIOUS_IP=$(tail -n 500 /var/log/pihole/pihole.log 2>/dev/null | grep -oP 'from \K[0-9.]+' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
    echo "  ⚠ SUSPICIOUS: $SUSPICIOUS_IP made $HIGH_VOLUME queries (possible malware)" >> "$REPORT_FILE"
    echo "HIGH_VOLUME|$TIMESTAMP|$SUSPICIOUS_IP|$HIGH_VOLUME" >> "$ALERT_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | HIGH_VOLUME | $SUSPICIOUS_IP | $HIGH_VOLUME queries" >> "$MASTER_LOG"
fi
echo "" >> "$REPORT_FILE"

# 5. SUSPICIOUS PORTS — EXCLUDE SSH (22)
echo "[5] SUSPICIOUS CONNECTION ATTEMPTS..." >> "$REPORT_FILE"
CONNECTIONS=$(sudo ss -tuln | grep -v ':22' | grep -cE ':23|:445|:3389|:5900|:21|:3306' 2>/dev/null)
if [ -n "$CONNECTIONS" ] && [ "$CONNECTIONS" -gt 0 ]; then
    echo "  ⚠ $CONNECTIONS suspicious open ports detected" >> "$REPORT_FILE"
    sudo ss -tuln | grep -v ':22' | grep -E ':23|:445|:3389|:5900|:21|:3306' >> "$REPORT_FILE" 2>/dev/null
    echo "SUSPICIOUS_PORT|$TIMESTAMP|$CONNECTIONS ports" >> "$ALERT_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | SUSPICIOUS_PORT | $CONNECTIONS ports open" >> "$MASTER_LOG"
else
    echo "  ✓ No suspicious ports detected" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 6. SUMMARY
echo "[6] SUMMARY" >> "$REPORT_FILE"
echo "  Total active devices: $CURRENT_DEVICES" >> "$REPORT_FILE"
echo "  Scan completed: $TIMESTAMP" >> "$REPORT_FILE"

# 7. DEDUPLICATION — only keep alert file if NEW issue vs last run
if [ -f "$ALERT_FILE" ] && [ -s "$ALERT_FILE" ]; then
    ALERT_HASH=$(cat "$ALERT_FILE" | sort | md5sum | awk '{print $1}')
    LAST_HASH=""
    if [ -f "$DEDUP_FILE" ]; then
        LAST_HASH=$(cat "$DEDUP_FILE" | head -1)
    fi
    
    if [ "$ALERT_HASH" != "$LAST_HASH" ]; then
        # New alert — keep it
        echo "" >> "$ALERT_FILE"
        echo "=== ACTION REQUIRED ===" >> "$ALERT_FILE"
        echo "Check dashboard: http://10.0.0.100/admin" >> "$ALERT_FILE"
        echo "Review report: $REPORT_FILE" >> "$ALERT_FILE"
        cp "$ALERT_FILE" "$ALERTDIR/LATEST_ALERT.txt"
        echo "$ALERT_HASH" > "$DEDUP_FILE"
        # Print alert to stdout for cron delivery
        cat "$ALERT_FILE"
    else
        # Duplicate — delete it, don't spam files
        rm "$ALERT_FILE"
    fi
else
    # No alert — clean scan
    rm -f "$ALERT_FILE"
fi

# 8. AUTO-CLEANUP — delete files older than 2 days
find "$REPORTDIR" -type f -mtime +2 -delete 2>/dev/null
find "$ALERTDIR" -type f -mtime +2 -delete 2>/dev/null
find "$LOGDIR" -name "*.log" -type f -mtime +2 -delete 2>/dev/null
find "$LOGDIR" -name "network-scan_*.txt" -type f -mtime +2 -delete 2>/dev/null
find "$LOGDIR" -name "ALERT_*.txt" -type f -mtime +2 -delete 2>/dev/null

# Always log scan completion silently
echo "[$(date)] Scan complete. Devices: $CURRENT_DEVICES | Blocked: $BLOCKED_COUNT" >> "$LOGDIR/activity.log"
