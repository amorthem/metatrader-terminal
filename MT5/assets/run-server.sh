#!/bin/sh

# Wait for auto-login wrapper to complete (VNC login + wineserver -k + marker)
LOGIN_MARKER="/tmp/login_complete"

echo "Waiting for auto-login to complete..."
while [ ! -f "$LOGIN_MARKER" ]; do
    sleep 2
done
echo "Auto-login marker found."

# Give MT5 time to restart on fresh wineserver and reconnect to broker
sleep 10

# Start the server
echo "Starting FastAPI Server..."
cd $HOME/api
wine python -m app
