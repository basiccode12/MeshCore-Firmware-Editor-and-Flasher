# MeshCore BLE Flasher

A simple, focused GUI tool for changing BLE names and flashing firmware to MeshCore devices.

## Features

- **Download firmware** from GitHub (latest version)
- **Browse local firmware** files
- **Change BLE name** with one click
- **Compile firmware** for your device
- **Flash firmware** directly to device

## Requirements

- **Python 3.6 or higher** (Python 3.8+ recommended)
- **PlatformIO** (auto-installed, for compilation and flashing)
- **Git** (auto-installed, for downloading firmware repository)

## Quick Installation

### 🐧 Linux / 🍎 macOS

1. **Download or clone the repository:**
   ```bash
   git clone <repository-url>
   cd "Meshcore BLE Flasher"
   ```
   Or download as ZIP and extract it.

2. **Run the installation script:**
   ```bash
   ./install.sh
   ```
   
   The script will automatically:
   - Check for Python installation
   - Install/verify pip
   - Install Tkinter if needed
   - Install the application
   - Install PlatformIO (for compilation/flashing)
   - Install Git (for downloading firmware)

3. **Run the application:**
   ```bash
   meshcore-ble-flasher
   ```
   
   Or use the launcher script:
   ```bash
   ./run.sh
   ```
   
   Or directly:
   ```bash
   python3 ble_flasher.py
   ```

### 🪟 Windows

1. **Download or clone the repository:**
   - Download as ZIP and extract, or
   - Clone with Git: `git clone <repository-url>`

2. **Run the installation script:**
   - Double-click `install.bat`, or
   - Open Command Prompt/PowerShell in the folder and run:
     ```cmd
     install.bat
     ```
   
   The script will automatically:
   - Check for Python installation
   - Install/verify pip
   - Check for Tkinter
   - Install the application
   - Install PlatformIO (for compilation/flashing)
   - Install Git (for downloading firmware)

3. **Run the application:**
   ```cmd
   meshcore-ble-flasher
   ```
   
   Or double-click `run.bat`, or run:
   ```cmd
   run.bat
   ```
   
   Or directly:
   ```cmd
   python ble_flasher.py
   ```

### Alternative: Manual Installation

If you prefer to install manually:

```bash
# Install using pip
pip install -e .

# Or install in user directory (no admin rights needed)
pip install -e . --user
```

Then run with:
```bash
meshcore-ble-flasher
```

## Manual Setup (If Installation Scripts Don't Work)

### Prerequisites

**Python:**
- Download from https://www.python.org/downloads/
- Make sure to check "Add Python to PATH" during installation (Windows)

**Tkinter (GUI library):**
- **Linux (Ubuntu/Debian):** `sudo apt-get install python3-tk`
- **Linux (Fedora):** `sudo dnf install python3-tkinter`
- **Linux (Arch):** `sudo pacman -S tk`
- **macOS:** `brew install python-tk`
- **Windows:** Usually included with Python

**Note:** PlatformIO and Git are automatically installed by the installation scripts. If you need to install them manually:

**PlatformIO:**
- Install via pip: `pip install platformio`

**Git:**
- **Windows:** https://git-scm.com/download/win (or use winget: `winget install Git.Git`)
- **Linux:** `sudo apt-get install git` (or your package manager)
- **macOS:** `brew install git`

## Usage Guide

Once the application is running:

1. **Get Firmware**: 
   - Click "📥 Download Latest" to get the newest firmware from GitHub
   - Or click "📂 Browse Local File" to use your own firmware file

2. **Set BLE Name** (optional): 
   - Enter your desired BLE name (e.g., "My Radio")
   - The BLE name will be automatically saved before compilation
   - If no BLE name is entered, firmware will compile with default settings

3. **Select Device**: 
   - Choose your device from the dropdown
   - (Dropdown will be populated automatically on startup)

4. **Compile**: 
   - Click "🔨 Compile" to build the firmware
   - BLE name changes (if entered) will be applied automatically before compilation
   - First compilation takes longer (downloads toolchains)
   - Watch progress in the log window

5. **Flash**: 
   - Connect your device via USB
   - Click "⚡ Flash" to upload firmware
   - Don't disconnect during flashing!

## Troubleshooting

### "Python not found" or "python: command not found"
- **Windows**: Reinstall Python and check "Add to PATH" during installation
- **Linux/macOS**: Install Python using your package manager

### "No module named 'tkinter'"
- **Linux**: Install `python3-tk` or `python3-tkinter` package
- **macOS**: Install with `brew install python-tk`
- **Windows**: Usually included with Python, try reinstalling Python

### "PlatformIO not found"
- Install PlatformIO: https://platformio.org/install/cli
- Or use PlatformIO IDE: https://platformio.org/install/ide

### "Git not found"
- **Windows**: Download from https://git-scm.com/download/win
- **Linux**: `sudo apt-get install git` (Ubuntu/Debian) or use your package manager
- **macOS**: `brew install git` or download from https://git-scm.com/download/mac

### Window doesn't appear
- Check if it's minimized or on another workspace
- Try running from terminal to see error messages
- On Linux, ensure you have a display server running (X11 or Wayland)

## Simplified Design

This is a streamlined version focused only on:
- BLE name changes
- Firmware compilation
- Device flashing

All other features (channels, messaging, CLI, etc.) have been removed for simplicity.

## Support

For issues or questions, check the log output in the application for detailed error messages.

