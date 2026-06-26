#!/bin/bash
# dewey_body_sync.sh — Sync Brain → Body (External Drive)
# Per the Dewey Constitutional: 3-way mirror sync for the Body tier
# Brain: /home/allenai/blacktech_brain/
# Body:  /media/allenai/Expansion/Blacktech_Drive/Dewey_Library/

BRAIN="/home/allenai/blacktech_brain/"
BODY="/media/allenai/Expansion/Blacktech_Drive/Dewey_Library/"

# Check if external drive is mounted
if [ ! -d "$BODY" ]; then
    echo "❌ Body drive not mounted at $BODY"
    echo "   Please connect the external drive and re-run."
    exit 1
fi

echo "🧠 Dewey Body Sync — $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Rsync brain to body, excluding _archive and dotfiles
# --exclude handles the colon-named files that FAT/exFAT can't store
rsync -av \
  --exclude='_archive' \
  --exclude='.*' \
  --exclude='*:*' \
  "$BRAIN" "$BODY" 2>&1

SYNC_EXIT=$?

if [ $SYNC_EXIT -eq 0 ]; then
    echo ""
    echo "✅ Body sync complete."
else
    echo ""
    echo "⚠️  Body sync completed with warnings (exit code $SYNC_EXIT)."
    echo "   Files with colons in names cannot sync to FAT/exFAT drives."
fi

# Log to blockchain
python3 "${BRAIN}000-General/dewey_blockchain.py" log SYNC "${BRAIN}000-General/dewey_body_sync.sh" --trigger body-sync 2>/dev/null || true