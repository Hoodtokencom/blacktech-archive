#!/bin/bash
# Blacktech Pi — Weekly Maintenance Script
# Runs Sunday 3am via Hermes cron

REPORT=""
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

REPORT+="🔧 **Weekly Pi Maintenance Report**\n"
REPORT+="📅 $TIMESTAMP\n\n"

# 1. System updates
REPORT+="**📦 System Updates:**\n"
sudo apt-get update -qq 2>&1
UPGRADABLE=$(apt list --upgradable 2>/dev/null | grep -c upgradable)
if [ "$UPGRADABLE" -gt 0 ]; then
    UPGRADE_OUTPUT=$(sudo apt-get upgrade -y -qq 2>&1)
    REPORT+="✅ $UPGRADABLE packages upgraded\n"
else
    REPORT+="✅ Already up to date\n"
fi

# 2. Autoremove old packages
REMOVED=$(sudo apt-get autoremove -y -qq 2>&1 | grep -c "Removing")
if [ "$REMOVED" -gt 0 ]; then
    REPORT+="🗑️ $REMOVED old packages removed\n"
fi

# 3. Clean apt cache
sudo apt-get clean -qq
REPORT+="\n"

# 4. Log cleanup — rotate logs over 30 days / over 50MB
REPORT+="**📋 Log Cleanup:**\n"
CLEANED=0

# Blockchain listener log
if [ -f /home/allenai/data/blockchain_listener.log ]; then
    LOG_SIZE=$(stat -f%z /home/allenai/data/blockchain_listener.log 2>/dev/null || stat -c%s /home/allenai/data/blockchain_listener.log 2>/dev/null)
    LOG_MB=$((LOG_SIZE / 1048576))
    if [ "$LOG_MB" -gt 50 ]; then
        tail -1000 /home/allenai/data/blockchain_listener.log > /tmp/bl_trim.log
        mv /tmp/bl_trim.log /home/allenai/data/blockchain_listener.log
        REPORT+="✂️ blockchain_listener.log trimmed (was ${LOG_MB}MB)\n"
        CLEANED=1
    else
        REPORT+="✅ blockchain_listener.log: ${LOG_MB}MB (ok)\n"
    fi
fi

# General old logs
OLD_LOGS=$(find /home/allenai/data -name "*.log" -mtime +30 2>/dev/null | wc -l)
if [ "$OLD_LOGS" -gt 0 ]; then
    find /home/allenai/data -name "*.log" -mtime +30 -delete 2>/dev/null
    REPORT+="🗑️ $OLD_LOGS old log files removed (30+ days)\n"
fi
if [ "$CLEANED" -eq 0 ] && [ "$OLD_LOGS" -eq 0 ]; then
    REPORT+="✅ All logs clean\n"
fi
REPORT+="\n"

# 5. Disk usage
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}')
DISK_AVAIL=$(df -h / | awk 'NR==2{print $4}')
REPORT+="**💾 Disk:** ${DISK_USAGE} used, ${DISK_AVAIL} free\n"

# 6. Memory
MEM_USAGE=$(free -h | awk 'NR==2{printf "%s / %s", $3, $2}')
REPORT+="**🧠 RAM:** $MEM_USAGE\n"

# 7. Uptime
UPTIME=$(uptime -p)
REPORT+="**⏱️ Uptime:** $UPTIME\n\n"

# 8. Check if kernel update needs reboot
if [ -f /var/run/reboot-required ]; then
    REPORT+="⚠️ **Reboot required** (kernel update). Will auto-reboot in 5 min.\n"
    echo "Rebooting in 5 minutes for kernel update..." | wall 2>/dev/null
    sudo shutdown -r +5 "Kernel update reboot"
else
    REPORT+="✅ No reboot needed\n"
fi

# 9. Service health check
REPORT+="\n**🖥️ Services:**\n"
SERVICES_UP=0
SERVICES_DOWN=0
for PORT in 8080 8090 8094 8096 8097 8099 8100 5678; do
    if ss -tlnp sport = :$PORT | grep -q LISTEN; then
        SERVICES_UP=$((SERVICES_UP + 1))
    else
        SERVICES_DOWN=$((SERVICES_DOWN + 1))
        REPORT+="❌ Port $PORT DOWN\n"
    fi
done
REPORT+="✅ $SERVICES_UP services running"
if [ "$SERVICES_DOWN" -gt 0 ]; then
    REPORT+=", ❌ $SERVICES_DOWN down"
fi

echo -e "$REPORT"
