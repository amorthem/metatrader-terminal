#!/bin/bash

# ==============================================================================
# Dynamic Configuration Environment Variables (หรือกำหนดค่า Default ไว้ที่นี่)
# ==============================================================================
ALLOWED_URLS="${MT5_WEB_REQUEST_URLS:-https://api.yourdomain.com;http://localhost:8000}"

MT5_DIR="/opt/wineprefix/drive_c/Metatrader-5"
MT5_CFG_DIR="$MT5_DIR/Config"
LOGIN_MARKER="/tmp/login_complete"
CONFIG_FILE="$MT5_DIR/startup.ini"

# ==============================================================================
# 1. MT5 Installation & Base Configuration Setup
# ==============================================================================
if [ ! -f "$MT5_DIR/terminal64.exe" ]; then
    echo "[SETUP] MetaTrader 5 not found. Starting installation..."

    # MetaTrader & WebView2 Download URLs
    URL="https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe"
    URL_WEBVIEW="https://msedge.sf.dl.delivery.mp.microsoft.com/filestreamingservice/files/c1336fd6-a2eb-4669-9b03-949fc70ace0e/MicrosoftEdgeWebview2Setup.exe"

    # Download Installers
    wget -q $URL -O mt5setup.exe
    wget -q $URL_WEBVIEW -O MicrosoftEdgeWebview2Setup.exe

    # Set Wine environment to Windows 11
    winecfg -v=win11

    # Install WebView2
    wine MicrosoftEdgeWebview2Setup.exe /silent /install
    wineserver -w

    # Install MT5 Terminal
    wine mt5setup.exe /auto /path:"C:\Metatrader-5"
    wineserver -w

    # Clean up installers
    rm -f mt5setup.exe MicrosoftEdgeWebview2Setup.exe
else
    echo "[SETUP] MetaTrader 5 is already installed."
fi

# ==============================================================================
# 2. Config Files Generation (UTF-16LE with BOM)
# ==============================================================================
mkdir -p "$MT5_CFG_DIR"

# 2.1 Disable LiveUpdate (terminal.ini)
{ 
    printf '\xFF\xFE'
    printf '[LiveUpdate]\r\nLiveUpdateMode=2\r\n' | iconv -f UTF-8 -t UTF-16LE
} > "$MT5_CFG_DIR/terminal.ini"

# 2.2 Enable Algo Trading + DLL Imports + WebRequest (common.ini)
COMMON_CONFIG="[Experts]\r\nEnabled=1\r\nAllowDllImport=1\r\nWebRequest=1\r\nWebRequestURLs=${ALLOWED_URLS}\r\n"
{ 
    printf '\xFF\xFE'
    printf "$COMMON_CONFIG" | iconv -f UTF-8 -t UTF-16LE
} > "$MT5_CFG_DIR/common.ini"

echo "[CONFIG] LiveUpdate disabled, AlgoTrading & WebRequest enabled (URLs: ${ALLOWED_URLS})."

# Exit early if in Docker Build Mode
if [ "$BUILD_MODE" = "1" ]; then
    echo "[BUILD] Metatrader 5 installed successfully (Build Mode). Exiting."
    exit 0
fi

# ==============================================================================
# 3. Process Execution Loop (Keep Alive & Startup Manager)
# ==============================================================================
while true; do
    echo "[RUN] Launching MetaTrader 5..."

    # ตรวจสอบว่ามีการ Mount ไฟล์ startup.ini เข้ามาสำหรับ Auto-Attach EA หรือไม่
    if [ -f "$CONFIG_FILE" ]; then
        echo "[RUN] Using Startup Config: $CONFIG_FILE"
        wine "$MT5_DIR/terminal64.exe" /portable /experts:on /config:"C:\Metatrader-5\startup.ini"
    else
        echo "[RUN] No startup config found. Launching standard terminal mode..."
        wine "$MT5_DIR/terminal64.exe" /portable /experts:on
    fi

    EXIT_CODE=$?

    # Restart Delay Logic
    if [ -f "$LOGIN_MARKER" ]; then
        echo "[WARN] MT5 exited (code $EXIT_CODE) after login — restarting in 5s..."
        sleep 5
    else
        echo "[WARN] MT5 exited (code $EXIT_CODE) before login — restarting in 2s..."
        sleep 2
    fi
done