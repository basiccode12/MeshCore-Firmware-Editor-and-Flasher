@echo off
REM Simple launcher script for Meshcore Firmware Editor and Flasher (Windows)

REM Try to run the installed version first
where meshcore-firmware-editor >nul 2>&1
if %errorlevel% equ 0 (
    meshcore-firmware-editor
) else (
    REM Fall back to running directly
    python meshcore_flasher.py 2>nul
    if %errorlevel% neq 0 (
        py meshcore_flasher.py 2>nul
        if %errorlevel% neq 0 (
            python3 meshcore_flasher.py
        )
    )
)

