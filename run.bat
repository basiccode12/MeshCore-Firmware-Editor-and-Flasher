@echo off
REM Simple launcher script for MeshCore BLE Flasher (Windows)

REM Try to run the installed version first
where meshcore-ble-flasher >nul 2>&1
if %errorlevel% equ 0 (
    meshcore-ble-flasher
) else (
    REM Fall back to running directly
    python ble_flasher.py 2>nul
    if %errorlevel% neq 0 (
        py ble_flasher.py 2>nul
        if %errorlevel% neq 0 (
            python3 ble_flasher.py
        )
    )
)

