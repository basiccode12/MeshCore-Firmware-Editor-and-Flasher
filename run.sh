#!/bin/bash
# Simple launcher script for MeshCore BLE Flasher (Linux/macOS)

# Try to run the installed version first
if command -v meshcore-ble-flasher >/dev/null 2>&1; then
    meshcore-ble-flasher
else
    # Fall back to running directly
    if command -v python3 >/dev/null 2>&1; then
        python3 ble_flasher.py
    elif command -v python >/dev/null 2>&1; then
        python ble_flasher.py
    else
        echo "Error: Python not found. Please install Python 3.6 or higher."
        exit 1
    fi
fi

