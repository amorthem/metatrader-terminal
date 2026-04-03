#!/bin/bash
# wine_fix.sh — Upgrade Wine inside the nodalytics/mt5-terminal container.
#
# Installs WineHQ Wine 9.x (staging) for MT5 IPC named pipe support.
# Wine 10.0 stable has IPC issues with MetaTrader5 Python library 5.0.5640.
# Wine 9.x staging has better named pipe compatibility.
#
# Usage (standalone):
#   docker exec <container> bash /tmp/wine_fix.sh
#
set -e

CURRENT=$(wine --version 2>/dev/null | grep -oP '[0-9]+\.[0-9]+' | head -1)
MAJOR=${CURRENT%%.*}

if [ "$MAJOR" -ge 9 ] 2>/dev/null; then
    echo "wine_fix: Wine $CURRENT already >= 9.0, skipping upgrade."
    exit 0
fi

echo "wine_fix: Wine $CURRENT detected — upgrading to Wine 9.x staging..."

dpkg --add-architecture i386 2>/dev/null || true

# Install prerequisites quietly
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq wget gnupg2 2>/dev/null

# Add WineHQ key + repo
mkdir -p /etc/apt/keyrings
wget -qO /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key

# Detect Debian codename
CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
CODENAME=${CODENAME:-bullseye}

# Remove any conflicting sources
rm -f /etc/apt/sources.list.d/winehq.sources
echo "deb [signed-by=/etc/apt/keyrings/winehq-archive.key] https://dl.winehq.org/wine-builds/debian/ $CODENAME main" \
    > /etc/apt/sources.list.d/winehq.list

apt-get update -qq
# Pin to Wine 9.0 — Wine 10.0's IPC named pipes don't work with MT5 Python lib
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --allow-downgrades \
    winehq-stable=9.0.0.0~bullseye-1 \
    wine-stable=9.0.0.0~bullseye-1 \
    wine-stable-amd64=9.0.0.0~bullseye-1 \
    wine-stable-i386=9.0.0.0~bullseye-1 2>/dev/null \
    || DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --allow-downgrades winehq-stable

echo "wine_fix: Upgrade complete — $(wine --version 2>/dev/null)"

# Kill the old wineserver so MT5 restarts with new Wine
wineserver -k 2>/dev/null || true
sleep 2

# Restart MT5 terminal + FastAPI server + auto-login via supervisor
if command -v supervisorctl &>/dev/null; then
    supervisorctl restart mt5 2>/dev/null || true
    supervisorctl restart server 2>/dev/null || true
    supervisorctl restart auto-login 2>/dev/null || true
    echo "wine_fix: Restarted MT5, server, auto-login."
fi
