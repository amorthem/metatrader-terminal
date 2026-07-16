#!/bin/bash
# Wrapper: รอ VNC พร้อมแล้วรันสคริปต์กดปุ่ม Algo Trading

LOG=/tmp/algo_toggle.log

# 1. รอ VNC Server เปิดบริการ
echo "Waiting for VNC server..."
for i in $(seq 1 30); do
    if bash -c "echo > /dev/tcp/localhost/5900" 2>/dev/null; then
        echo "VNC ready after ${i}s"
        break
    fi
    sleep 1
done

# 2. รันสคริปต์ Python ผ่าน Wine (ส่งไปทำงานที่ Background)
wine python /root/auto_toggle_algo.py > $LOG 2>&1 &

echo "Algo Trading toggle script triggered."
exit 0