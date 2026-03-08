# Meshcore Firmware Editor and Flasher

A simple, focused GUI tool for editing and flashing MeshCore firmware.

**Repository:** https://github.com/basiccode12/Meshcore-Firmware-Editor-and-Flasher

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Features

### Firmware Management
- **Download firmware from GitHub** - Download firmware directly from the MeshCore repository
  - Select from available versions (branches and tags)
  - Filter versions by firmware type (Companion Radio or Repeater Radio)
  - Automatic version detection and filtering
- **Browse local firmware files** - Load and edit your own firmware files
- **Firmware type selection** - Choose between Companion Radio and Repeater Radio firmware
- **Version selection** - Select specific branches or tags to download

### Code Editing
- **C++ Source Code Editor** - Full-featured editor for editing main.cpp files
  - Syntax highlighting support
  - Find and replace functionality (Ctrl+F)
  - Auto-loads when firmware is downloaded or browsed
  - Save with automatic backup creation
  - Reload from disk
  - Reset to original content
  - Real-time change tracking

### Configuration Management
- **PlatformIO.ini Editor** - Built-in editor for PlatformIO configuration
  - Edit build settings, environments, and options
  - Find and replace functionality (Ctrl+F)
  - Save with automatic backup creation
  - Reload from disk
  - Reset to original content
  - Real-time change tracking

### Device Management
- **Automatic device detection** - Device list auto-populates from platformio.ini files
- **Device filtering** - Shows only devices matching selected firmware type
- **Device selection** - Easy dropdown selection of target device

### BLE Name Customization
- **BLE name editing** - Change BLE device name with one click
- **Automatic application** - BLE name changes are automatically applied before compilation
- **Companion Radio support** - Full BLE name support for Companion Radio firmware
- **Repeater Radio support** - Attempts to apply BLE names to Repeater Radio firmware

### Build & Flash
- **Compile firmware** - Build firmware for your selected device using PlatformIO
- **Flash firmware** - Upload compiled firmware directly to your device via USB
- **Real-time progress** - Watch compilation and flashing progress in the log window
- **Automatic project setup** - Automatically clones and sets up the MeshCore repository

### User Interface
- **Tabbed interface** - Organized into Firmware, C++ Editor, and Settings tabs
- **Modern GUI** - Clean, intuitive interface built with Tkinter
- **Real-time logging** - Comprehensive log output for all operations
- **Status indicators** - Visual feedback for file status and changes
- **Keyboard shortcuts** - Ctrl+F for find functionality in editors

### Installation & Setup
- **Automatic dependency installation** - Installs Python, pip, Tkinter, PlatformIO, and Git automatically
- **Cross-platform support** - Works on Linux, macOS, and Windows
- **Simple installation** - One-command installation scripts for all platforms
- **No external dependencies** - Uses only Python standard library (except PlatformIO and Git for firmware operations)

## Requirements

- **Python 3.6 or higher** (Python 3.8+ recommended)
- **PlatformIO** (auto-installed, for compilation and flashing)
- **Git** (auto-installed, for downloading firmware repository)

## Quick Installation

### 🐧 Linux / 🍎 macOS

1. **Download or clone the repository:**
   ```bash
   git clone https://github.com/basiccode12/Meshcore-Firmware-Editor-and-Flasher.git
   cd "Meshcore-Firmware-Editor-and-Flasher"
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
   meshcore-firmware-editor
   ```
   
   Or use the launcher script:
   ```bash
   ./run.sh
   ```
   
   Or directly:
   ```bash
   python3 meshcore_flasher.py
   ```

### 🪟 Windows

1. **Download or clone the repository:**
   - Download as ZIP and extract, or
   - Clone with Git: `git clone https://github.com/basiccode12/Meshcore-Firmware-Editor-and-Flasher.git`

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
   meshcore-firmware-editor
   ```
   
   Or double-click `run.bat`, or run:
   ```cmd
   run.bat
   ```
   
   Or directly:
   ```cmd
   python meshcore_flasher.py
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
meshcore-firmware-editor
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

Once the application is running, you'll see three main tabs:

### 📦 Firmware Tab

1. **Get Firmware**: 
   - Select firmware type: **Companion Radio** or **Repeater Radio**
   - Select version: Choose from available branches and tags (versions are filtered by firmware type)
   - Click "📥 Download" to download firmware from GitHub
   - Or click "📂 Browse Local File" to use your own firmware file
   - The downloaded/browsed file will automatically load into the C++ Editor tab

2. **Set BLE Name** (optional): 
   - Enter your desired BLE name (e.g., "My Radio")
   - The BLE name will be automatically saved before compilation
   - If no BLE name is entered, firmware will compile with default settings
   - Note: BLE name changes work best with Companion Radio firmware

3. **Select Device**: 
   - Choose your device from the dropdown
   - Device list auto-populates on startup and filters by selected firmware type
   - Only devices matching your firmware type (Companion/Repeater) are shown

4. **Configure PlatformIO** (Optional): 
   - Click "✏️ Edit platformio.ini" to navigate to the Settings tab
   - Or manually switch to the Settings tab to edit configuration

5. **Compile**: 
   - Click "🔨 Compile" to build the firmware
   - BLE name changes (if entered) will be applied automatically before compilation
   - Your platformio.ini and C++ code edits (if made) will be used
   - First compilation takes longer (downloads toolchains)
   - Watch progress in the log window at the bottom

6. **Flash**: 
   - Connect your device via USB
   - Click "⚡ Flash" to upload firmware
   - Don't disconnect during flashing!

### 📝 Edit C++ Tab

- **Edit source code** - Make direct edits to the main.cpp file
- **Find functionality** - Press Ctrl+F or click "🔍 Find" to search in the code
- **Save changes** - Click "💾 Save" to save your edits (backup created automatically)
- **Reload** - Click "🔄 Reload" to reload the file from disk
- **Reset** - Click "↩️ Reset to Original" to discard unsaved changes
- **Auto-load** - File automatically loads when you download or browse firmware

### ⚙️ Settings Tab

- **Edit platformio.ini** - Customize build settings, environments, and PlatformIO options
- **Find functionality** - Press Ctrl+F or click "🔍 Find" to search in the configuration
- **Save changes** - Click "💾 Save" to save your edits (backup created automatically)
- **Reload** - Click "🔄 Reload" to reload the file from disk
- **Reset** - Click "↩️ Reset to Original" to discard unsaved changes
- **Auto-load** - Configuration automatically loads when you switch to this tab

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

## Design Philosophy

This tool is designed to be a comprehensive yet user-friendly solution for MeshCore firmware development:
- **Focused workflow** - Everything you need for firmware editing and flashing in one place
- **No external dependencies** - Uses only Python standard library (PlatformIO and Git are auto-installed)
- **Automatic setup** - Handles repository cloning, project setup, and dependency installation
- **Intuitive interface** - Tabbed design separates firmware operations, code editing, and configuration
- **Real-time feedback** - Comprehensive logging and status indicators keep you informed

## Support

For issues or questions, check the log output in the application for detailed error messages.

