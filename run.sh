#!/bin/bash
# Simple launcher script for Meshcore Firmware Editor and Flasher (Linux/macOS)

# Try to run the installed version first
if command -v meshcore-firmware-editor >/dev/null 2>&1; then
    meshcore-firmware-editor
else
    # Fall back to running directly
    if command -v python3 >/dev/null 2>&1; then
        python3 meshcore_flasher.py
    elif command -v python >/dev/null 2>&1; then
        python meshcore_flasher.py
    else
        echo "Error: Python not found. Please install Python 3.6 or higher."
        exit 1
    fi
fi

