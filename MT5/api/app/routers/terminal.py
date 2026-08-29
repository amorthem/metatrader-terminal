import os
import re
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException
from app.services.mt5_service import mt5_service
from app.services.connector import mt5_connector
from app.utils.exceptions import MT5ConnectionError
from typing import Dict, Any, List
import MetaTrader5 as mt5

router = APIRouter(prefix="/terminal", tags=["Terminal"])


@router.get("/info")
def get_terminal_info() -> Dict[str, Any]:
    info = mt5_service.get_terminal_info()
    if info is None:
        raise MT5ConnectionError("Failed to get terminal info")
    return info._asdict() if hasattr(info, '_asdict') else dict(info)


@router.get("/account/info")
def get_account_info() -> Dict[str, Any]:
    account_info = mt5_service.get_account_info()
    if account_info is None:
        raise MT5ConnectionError("Failed to get account info")
    return account_info._asdict() if hasattr(account_info, '_asdict') else dict(account_info)


@router.get("/version")
def get_mt5_version():
    mt5_service.initialize()
    return {"version": mt5.version()}


@router.post("/disconnect")
def disconnect():
    if not mt5.shutdown():
        raise MT5ConnectionError("Failed to disconnect from MT5 terminal")
    mt5_connector._initialized = False
    return {"status": "disconnected"}


@router.get("/ping")
def ping():
    mt5_service.initialize()
    info = mt5.terminal_info()
    if info is None:
        raise MT5ConnectionError("Terminal not connected")
    return {"ping": info.ping_last}


@router.get("/last_error")
def get_last_error():
    code, msg = mt5.last_error()
    return {"error_code": code, "error_message": msg}

@router.get("/logs", response_model=List[Dict[str, Any]], summary="ดึงข้อมูลไฟล์ Log ของ MT5 ในรูปแบบ JSON")
def get_mt5_terminal_logs_json(
    date: str = Query(default=None, description="ระบุวันที่ฟอร์แมต YYYYMMDD (เช่น 20260824) หากไม่ใส่จะดึงของวันนี้"),
    lines: int = Query(default=100, description="จำนวนบรรทัดล่าสุดที่ต้องการดึง")
):
    """
    Endpoint ดึง Log ของ MT5 และจัดระเบียบโครงสร้างใหม่เป็น JSON อ้างอิงสถาปัตยกรรม Log บน Wine จริง
    """
    LOG_DIR = "/opt/wineprefix/drive_c/Metatrader-5/logs"
    
    # 1. จัดการเรื่องวันที่ (แปลงฟอร์แมตเพื่อนำไปใส่ในฟิลด์ timestamp ของ JSON ให้สมบูรณ์)
    if not date:
        date = datetime.now().strftime("%Y%m%d")
        
    try:
        # แปลงจาก 20260824 -> 2026.08.24 เพื่อเตรียมใช้ทำ Timestamp
        date_formatted = datetime.strptime(date, "%Y%m%d").strftime("%Y.%m.%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="ฟอร์แมตวันที่ไม่ถูกต้อง กรุณาใช้ YYYYMMDD เช่น 20260824")
    
    file_name = f"{date}.log"
    log_path = os.path.join(LOG_DIR, file_name)

    if not os.path.exists(log_path):
        raise HTTPException(
            status_code=404, 
            detail=f"ไม่พบไฟล์ Log สำหรับวันที่ {date} (ตรวจสอบชื่อไฟล์: {file_name})"
        )

    json_logs = []

    try:
        # เปิดไฟล์ด้วย utf-16le เสมอสำหรับข้อมูลดิบของ MT5
        with open(log_path, "r", encoding="utf-16le", errors="ignore") as f:
            all_lines = f.readlines()
            target_lines = all_lines[-lines:]
            
            for index, line in enumerate(target_lines):
                clean_line = line.strip()
                if not clean_line:
                    continue
                
                # แยกโครงสร้างด้วย Tab (\t) เป็นหลัก
                parts = clean_line.split("\t")
                
                # จากโครงสร้างจริงของล็อกคุณ: [อักขระขยะ, ดัชนีระบบ(0), เวลา, โมดูล, ข้อความ]
                if len(parts) >= 5:
                    time_part = parts[2].strip()      # เช่น 05:31:18.253
                    source_part = parts[3].strip()    # เช่น Network
                    message_part = " ".join(parts[4:]).strip()  # เก็บข้อความทั้งหมดที่เหลือ
                    
                    timestamp = f"{date_formatted} {time_part}"
                elif len(parts) == 4:
                    # กรณีฉุกเฉินหลุดมา 4 คอลัมน์
                    time_part = parts[1].strip()
                    source_part = parts[2].strip()
                    message_part = parts[3].strip()
                    timestamp = f"{date_formatted} {time_part}"
                else:
                    # แถวที่ไม่เป็นระบบ (Fallback)
                    timestamp = f"{date_formatted} --:--:--.---"
                    source_part = "System"
                    message_part = clean_line

                json_logs.append({
                    "id": index + 1,
                    "timestamp": timestamp,
                    "source": source_part,
                    "message": message_part
                })
                
        return json_logs

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"เกิดข้อผิดพลาดในการแปลงไฟล์ Log เป็น JSON: {str(e)}"
        )