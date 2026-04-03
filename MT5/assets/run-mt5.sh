#!/bin/bash

# Only install if not already present
if [ ! -f "/opt/wineprefix/drive_c/Metatrader-5/terminal64.exe" ]; then
    echo "MetaTrader 5 not found. Starting installation..."

    # MetaTrader download url
    URL="https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe"
    # WebView2 Runtime download url
    URL_WEBVIEW="https://msedge.sf.dl.delivery.mp.microsoft.com/filestreamingservice/files/c1336fd6-a2eb-4669-9b03-949fc70ace0e/MicrosoftEdgeWebview2Setup.exe"

    # Download
    wget -q $URL
    wget -q $URL_WEBVIEW

    # Set environment to Windows 10
    winecfg -v=win10

    # Install WebView2
    wine MicrosoftEdgeWebview2Setup.exe /silent /install
    wineserver -w

    # Install MT5
    wine mt5setup.exe /auto /path:"C:\Metatrader-5"
    wineserver -w

    # Clean up
    rm mt5setup.exe MicrosoftEdgeWebview2Setup.exe
else
    echo "MetaTrader 5 already installed."
fi

# Patch MT5 config files (UTF-16LE encoded) — only once via marker file
MT5_CFG="/opt/wineprefix/drive_c/Metatrader-5/Config"
PATCH_MARKER="$MT5_CFG/.patched"

if [ ! -f "$PATCH_MARKER" ]; then
    # Disable LiveUpdate to prevent version mismatch with MetaTrader5 pip package
    if [ -f "$MT5_CFG/terminal.ini" ]; then
        iconv -f UTF-16LE -t UTF-8 "$MT5_CFG/terminal.ini" > /tmp/mt5_cfg.ini 2>/dev/null
        if ! grep -q "LiveUpdateMode" /tmp/mt5_cfg.ini; then
            sed -i 's/\[LiveUpdate\]/[LiveUpdate]\nLiveUpdateMode=2/' /tmp/mt5_cfg.ini
            iconv -f UTF-8 -t UTF-16LE /tmp/mt5_cfg.ini > "$MT5_CFG/terminal.ini"
            echo "LiveUpdate disabled in terminal.ini"
        fi
        rm -f /tmp/mt5_cfg.ini
    fi

    # Enable algo trading via config
    if [ -f "$MT5_CFG/common.ini" ]; then
        iconv -f UTF-16LE -t UTF-8 "$MT5_CFG/common.ini" > /tmp/mt5_cfg.ini 2>/dev/null
        sed -i 's/^\(Enabled=\).*/\11/' /tmp/mt5_cfg.ini
        if ! grep -q "Enabled=1" /tmp/mt5_cfg.ini; then
            sed -i 's/\[Experts\]/[Experts]\nEnabled=1/' /tmp/mt5_cfg.ini
        fi
        iconv -f UTF-8 -t UTF-16LE /tmp/mt5_cfg.ini > "$MT5_CFG/common.ini"
        echo "Algo trading enabled in common.ini"
        rm -f /tmp/mt5_cfg.ini
    fi

    touch "$PATCH_MARKER"
fi

# Run MT5 (Skip if in BUILD_MODE)
if [ "$BUILD_MODE" = "1" ]; then
    echo "Metatrader 5 installed successfully (Build Mode). Skipping launch."
    exit 0
fi

# Run MT5
echo "Launching MetaTrader 5..."
wine /opt/wineprefix/drive_c/Metatrader-5/terminal64.exe /portable