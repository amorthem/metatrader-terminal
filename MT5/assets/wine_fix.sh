#!/bin/bash
# wine_fix.sh — Upgrade Wine 7.0 → 10.0 inside the nodalytics/mt5-terminal container.
#
# MT5 build 5727+ requires Wine 10.0+ for IPC (named pipes) to work.
# Without this, mt5.initialize() returns (-10005, 'IPC timeout') because
# Wine 7.0 doesn't implement the pipe APIs the new MT5 build uses.
#
# This script is injected and executed by DockerizedMT5Gateway.safe_start()
# after the container starts but before the health/IPC check.
#
# Usage (standalone):
#   docker exec <container> bash /tmp/wine_fix.sh
#
set -e

CURRENT=$(wine --version 2>/dev/null | grep -oP '[0-9]+\.[0-9]+' | head -1)
MAJOR=${CURRENT%%.*}

if [ "$MAJOR" -ge 10 ] 2>/dev/null; then
    echo "wine_fix: Wine $CURRENT already >= 10.0, skipping upgrade."
    exit 0
fi

echo "wine_fix: Wine $CURRENT detected — upgrading to 10.0..."

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
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --allow-downgrades winehq-stable

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
