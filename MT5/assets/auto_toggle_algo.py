"""
VNC Client to toggle MetaTrader 5 Algo Trading using Ctrl+E
"""

import os
import time
from vncdotool import api

class ShortVNClient:
    def __init__(self, server_url: str, password: str = None):
        # เชื่อมต่อ VNC
        self.client = api.connect(server_url, password=password)
        self.client.timeout = 10

    def enable_algo_trading(self):
        """ กดปุ่ม Ctrl + E เพื่อเปิดใช้งาน Algo Trading """
        print("Sending Ctrl+E to toggle Algo Trading...")
        self.client.keyDown('ctrl')
        self.client.keyPress('e')
        self.client.keyUp('ctrl')
        time.sleep(0.5)

    def disconnect(self):
        if self.client is not None:
            self.client.disconnect()

def main():
    # ดึงค่า Host และ Password ของ VNC จาก Environment Variables (ถ้ามี)
    VNC_SERVER_URL = os.getenv('VNC_SERVER_HOST', 'localhost')
    VNC_SERVER_PASSWORD = os.getenv('VNC_PASSWORD', None)

    client = ShortVNClient(server_url=VNC_SERVER_URL, password=VNC_SERVER_PASSWORD)

    try:
        # รอให้โปรแกรม MT5 เปิดขึ้นมาและ GUI พร้อมทำงาน (ปรับเวลาลด/เพิ่มได้ตามสะดวก)
        print("Waiting for terminal GUI...")
        time.sleep(10) 
        
        # สั่งกดปุ่มเปิด Algo Trading
        client.enable_algo_trading()
        print("Algo Trading toggled successfully.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        
    finally:
        # ตัดการเชื่อมต่อ VNC
        client.disconnect()

if __name__ == "__main__":
    main()