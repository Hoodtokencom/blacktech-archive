#!/bin/bash
# Dewey 3-Tier: Pi Brain → Internal Drive (Body) Mirror Sync
# ExFAT-safe: no perms/owner/group flags required for external drive
BRAIN="/home/allenai/blacktech_brain"
BODY="/media/allenai/Expansion/Blacktech_Drive/Dewey_Library"

# Check if Body drive is mounted
if [ ! -d "$BODY/000-General" ]; then
    echo "❌ Body drive not mounted at $BODY"
    exit 1
fi

# Sync Pi Brain → Body Library (exFAT-safe flags)
# --exclude: dewey_blockchain.py writes chain.json via a transient .tmp
# (tmp+rename atomic write); without the exclude, rsync copies that
# half-written staging file to Body as a junk 0-byte leftover.
rsync -av --no-perms --no-owner --no-group --checksum \
      --exclude='*.tmp' --exclude='*.part' --exclude='__pycache__/' "$BRAIN/" "$BODY/"
echo "✅ Dewey Brain → Body sync complete: $(date)"