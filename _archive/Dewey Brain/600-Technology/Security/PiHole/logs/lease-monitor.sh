#!/bin/bash
# BlackTech Security - Pi-hole Lease Monitor
# Captures all DHCP lease assignments and DNS queries
# Checks for new devices joining the network

# Fixed base directory (so sudo still writes to the user directory)
BASEDIR="/home/allenai/Documents/BlackTech-Security/PiHole"
LOGDIR="$BASEDIR/logs"
LEASEDIR="$BASEDIR/leases"
DATEDIR="$(date +%Y-%m-%d)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DEVICE_TRACKER="$BASEDIR/devices/known_devices.txt"
ALERT_LOG="$BASEDIR/reports/new_devices_alert.log"

mkdir -p "$LOGDIR/$DATEDIR"
mkdir -p "$LEASEDIR/$DATEDIR"
mkdir -p "$BASEDIR/devices"
mkdir -p "$BASEDIR/reports"

# --- Capture current leases ---
if sudo test -r /etc/pihole/dhcp.leases; then
    sudo cp /etc/pihole/dhcp.leases "$LEASEDIR/$DATEDIR/leases_$TIMESTAMP.txt"
    sudo chown allenai:allenai "$LEASEDIR/$DATEDIR/leases_$TIMESTAMP.txt"
    sudo chmod 644 "$LEASEDIR/$DATEDIR/leases_$TIMESTAMP.txt"
else
    echo "# /etc/pihole/dhcp.leases not readable" > "$LEASEDIR/$DATEDIR/leases_$TIMESTAMP.txt"
fi

# --- Capture query log (last 1000 entries) ---
if sudo test -r /var/log/pihole/pihole.log; then
    sudo tail -n 1000 /var/log/pihole/pihole.log > "$LOGDIR/$DATEDIR/queries_$TIMESTAMP.txt"
    sudo grep "gravity_blocked" /var/log/pihole/pihole.log | tail -n 500 > "$LOGDIR/$DATEDIR/blocked_$TIMESTAMP.txt" 2>/dev/null || true
else
    echo "# pihole.log not readable" > "$LOGDIR/$DATEDIR/queries_$TIMESTAMP.txt"
    echo "# pihole.log not readable" > "$LOGDIR/$DATEDIR/blocked_$TIMESTAMP.txt"
fi

# --- Device activity summary ---
{
    echo "=== Device Activity Report - $TIMESTAMP ==="
    echo ""
} > "$LOGDIR/$DATEDIR/report_$TIMESTAMP.txt"

# Build current device list from leases
current_devices="$LEASEDIR/$DATEDIR/devices_current_$TIMESTAMP.txt"
> "$current_devices"

if sudo test -s /etc/pihole/dhcp.leases; then
    sudo cat /etc/pihole/dhcp.leases | while read -r line; do
        if [ -n "$line" ]; then
            echo "$line" >> "$LOGDIR/$DATEDIR/report_$TIMESTAMP.txt"
            # Extract MAC as unique device key (field 2 in dnsmasq lease format)
            mac=$(echo "$line" | awk '{print $2}')
            if [ -n "$mac" ]; then
                echo "$mac $line" >> "$current_devices"
            fi
        fi
    done
else
    echo "# No active DHCP leases" >> "$LOGDIR/$DATEDIR/report_$TIMESTAMP.txt"
fi

sudo chown allenai:allenai "$current_devices" 2>/dev/null || true
sudo chown allenai:allenai "$LOGDIR/$DATEDIR/report_$TIMESTAMP.txt" 2>/dev/null || true

# --- New-device detection ---
new_macs=""
if [ -f "$DEVICE_TRACKER" ] && [ -s "$current_devices" ]; then
    new_macs=$(awk '{print $1}' "$current_devices" | sort -u | while read -r mac; do
        if ! grep -qi "$mac" "$DEVICE_TRACKER"; then
            echo "$mac"
        fi
    done)
fi

if [ -n "$new_macs" ]; then
    alert_msg="[$(date)] ALERT: New device(s) detected on network:\n$new_macs"
    echo -e "$alert_msg" >> "$ALERT_LOG"
    echo -e "\n>>> NEW DEVICE ALERT <<<\n$alert_msg" >> "$LOGDIR/$DATEDIR/report_$TIMESTAMP.txt"
fi

# Update known-devices tracker (deduplicated)
if [ -s "$current_devices" ]; then
    awk '{print $1}' "$current_devices" | sort -uf > "$DEVICE_TRACKER.new"
    mv "$DEVICE_TRACKER.new" "$DEVICE_TRACKER"
fi

# --- Fix ownership so user can read everything without sudo ---
sudo chown -R allenai:allenai "$LOGDIR/$DATEDIR" "$LEASEDIR/$DATEDIR" "$BASEDIR/devices" "$BASEDIR/reports" 2>/dev/null || true

echo "[$(date)] Lease monitor: Captured at $TIMESTAMP" >> "$LOGDIR/activity.log"
