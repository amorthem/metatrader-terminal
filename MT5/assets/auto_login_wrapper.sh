#!/bin/bash
# Wrapper: runs VNC auto-login under Wine, then kills wineserver
# from Linux for a clean IPC handshake on restart.

LOG=/tmp/auto_login.log

# Wait for VNC to be ready
echo "Waiting for VNC server..."
for i in $(seq 1 30); do
    if bash -c "echo > /dev/tcp/localhost/5900" 2>/dev/null; then
        echo "VNC ready after ${i}s"
        break
    fi
    sleep 1
done

# Run auto-login in background, capture output.
# wine python hangs after script completes (wineserver keeps it alive),
# so we watch the log for the completion message.
wine python /root/auto_login.py > $LOG 2>&1 &
WINE_PID=$!

# Wait for completion message or timeout (120s)
echo "Waiting for auto-login to complete..."
for i in $(seq 1 60); do
    if grep -q "Auto-login sequence completed" $LOG 2>/dev/null; then
        echo "Auto-login succeeded — killing wineserver for clean IPC..."
        /usr/bin/wineserver -k 2>/dev/null || true
        sleep 2
        echo "1" > /tmp/login_complete
        echo "Marker created, services will restart via supervisor."
        exit 0
    fi
    if grep -q "An error occurred" $LOG 2>/dev/null; then
        echo "Auto-login failed:"
        cat $LOG
        exit 1
    fi
    sleep 2
done

echo "Auto-login timed out after 120s"
cat $LOG
exit 1
