# Meshcore Firmware Editor and Flasher

A comprehensive, intuitive GUI tool for editing, compiling, flashing, and managing MeshCore firmware — all in one place.

**Repository:** https://github.com/basiccode12/Meshcore-Firmware-Editor-and-Flasher

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Features

### 📦 Firmware Management
- **Download firmware from GitHub** — Download directly from the MeshCore repository
  - Select from available branches and tags
  - Filter versions by firmware type (Companion Radio, Repeater Radio, Room Server)
  - Automatic version detection
- **Browse local firmware files** — Load and edit your own firmware files
- **Automatic project setup** — Clones and configures the MeshCore repository automatically

### 🔧 BLE Name Customisation
- **Optional custom BLE name** — Override the default `MeshCore-<node_name>` naming convention
- **Immediate reflection** — Changes applied to `main.cpp` instantly; visible in the C++ editor
- **Standard code restore** — Leave the field blank and click Apply to revert to the standard MeshCore naming
- **⚠️ Note** — A custom BLE name may interfere with automatic Bluetooth connection in some MeshCore phone apps

### ✏️ Code Editing
- **C++ Source Code Editor** (`main.cpp`) — Full-featured editor with:
  - Syntax highlighting (via QScintilla if installed)
  - Find and replace (Ctrl+F)
  - Auto-loads when firmware is downloaded or browsed
  - Save with automatic backup creation
  - Reload from disk / Reset to original
  - Real-time change tracking
- **PlatformIO.ini Editor** — Edit build settings, environments, and device targets

### 🔨 Build & Flash
- **Compile firmware** — Build for your selected device using PlatformIO
- **Flash via USB** — Upload compiled firmware directly from the serial port selector
- **Flash pre-built `.bin`** — Browse and flash any `.bin` file without compiling
- **Flash modes** — *Update Only* (faster, keeps settings) or *Full Erase* (wipes entire flash)
- **Serial port selector** — Choose a specific port or use Auto-detect
- **🔄 Refresh Ports** — Rescan available serial ports at any time
- **Real-time progress** — Watch compilation and flashing in the log panel

### 📡 OTA Update
- **Wireless firmware updates** over WiFi via the MeshCore OTA workflow
  - BLE scan and connect to your local gateway device
  - Load contacts from the device to select the remote target
  - Sends `start ota` command via the mesh network
  - Automatically connects to the `MeshCore-OTA` WiFi hotspot
  - Opens the ElegantOTA upload page in your browser (`.bin` file upload)
  - Confirmation dialog appears immediately so you can upload at your own pace
  - Reconnects to your previous WiFi on completion
- **Contact caching** — Contacts cached per device for faster repeat use
- **Device memory** — Remembers last BLE device and target device between sessions

### 🖥️ Serial Monitor
- **Always-on live output** — Opens and streams device output automatically; no Start/Stop needed
- **Auto-reconnects** — If the device is unplugged and replugged the monitor reconnects in 3 seconds
- **Port & baud selector** — Changing either restarts the monitor immediately
- **Refresh Ports** — Rescan without restarting the app
- **Clear** — One-click wipe of the terminal output
- Uses **pyserial** directly — no PlatformIO subprocess, works reliably in all environments

### ⌨️ MeshCore CLI
- **Direct serial CLI** — Send MeshCore commands to a device over USB serial
- **Context-sensitive quick buttons** — Switch between **Repeater**, **Companion**, and **Room Server** modes; button groups change to match the device type
- **Collapsible command groups** — Info, Logging, Radio, Power, Region, GPS, Manage (and Room for room servers) — collapsed by default to save space
- **Hover tooltips** — Detailed description of every command button, including the exact command sent
- **CLI mode detection** — Detects the `>` prompt and confirms when CLI mode is active
- **No-response watchdog** — If a command gets no reply within 3 seconds, actionable guidance is shown
- **Command history** — ↑/↓ arrow keys navigate previously sent commands
- **Colour-coded terminal** — Sent commands in blue, device responses in white, info in green, errors in red
- **Port sharing** — Automatically pauses the Serial Monitor when CLI connects, resumes on disconnect

### 🎨 User Interface
- **Tabbed layout** — Welcome · Firmware · main.cpp · platformio.ini · OTA Update · Serial Monitor · MeshCore CLI
- **Connection status indicators** — BLE and WiFi dots turn **green** when connected
- **Fullscreen layout** — Opens maximised for maximum workspace
- **Vertical log panel** — Real-time logs always visible on the right side; minimum width enforced
- **Device memory** — Remembers last BLE device, target device, and serial port between sessions
- **Keyboard shortcuts** — Ctrl+F for find in editors

---

## Requirements

- **Python 3.8 or higher**
- **pyserial** — `pip install pyserial` (required for Serial Monitor and CLI)
- **PlatformIO** — `pip install platformio` (required for compile/flash)
- **Git** (required for downloading firmware from GitHub)
- **meshcore** — `pip install meshcore` (required for OTA)
- **bleak** — `pip install bleak` (required for BLE in OTA)
- **Optional: tkinterweb** — `pip install tkinterweb` (embedded browser in OTA tab)
- **Optional: QScintilla / PyQt5** — `pip install QScintilla PyQt5` (syntax highlighting in editors)
- **Linux OTA** — NetworkManager (`nmcli`) for automatic WiFi management

---

## Quick Installation

### 🐧 Linux / 🍎 macOS

1. **Clone the repository:**
   ```bash
   git clone https://github.com/basiccode12/Meshcore-Firmware-Editor-and-Flasher.git
   cd "Meshcore-Firmware-Editor-and-Flasher"
   ```

2. **Run the installation script:**
   ```bash
   ./install.sh
   ```

3. **Run the application:**
   ```bash
   python3 meshcore_flasher.py
   ```

### 🪟 Windows

1. **Clone or download** the repository as ZIP and extract.

2. **Run the installation script:**
   ```cmd
   install.bat
   ```

3. **Run the application:**
   ```cmd
   python meshcore_flasher.py
   ```

### Manual dependency install

```bash
pip install pyserial meshcore bleak
# Optional extras:
pip install tkinterweb QScintilla PyQt5
```

---

## Usage Guide

### 📦 Firmware Tab

1. **Select firmware type** — Companion Radio, Repeater Radio, or Room Server
2. **Download or browse** firmware from GitHub or a local folder
3. **Set BLE Name (Optional)** — Enter a custom name to override `MeshCore-<node_name>`, or leave blank for the standard convention. Click **✏ Apply to main.cpp** to apply.
4. **Select device** — Choose from the auto-populated dropdown (filtered by firmware type)
5. **Compile** — Click **🔨 Compile** to build; BLE name is applied automatically before compilation
6. **Flash** — Connect via USB, select the serial port, choose a flash mode, and click **⚡ Flash**
7. **Flash pre-built .bin** — Click **Browse .bin** then **Flash .bin** to skip compilation entirely

### ✏️ main.cpp / platformio.ini Tabs

- Edit code directly in the full-screen editor
- **Ctrl+F** — Find / search in file
- **💾 Save** — Save with automatic backup
- **🔄 Reload** — Reload from disk
- **↩️ Reset** — Discard unsaved changes

### 📡 OTA Update Tab

1. **Scan** for your local BLE gateway device (or leave as Auto-scan)
2. **Load Contacts** — Fetch the device contact list; select your target device
3. *(Optional)* Enter an admin password
4. **Start OTA Update** — The app:
   - Connects to the local BLE device
   - Sends `start ota` to the target via the mesh network
   - Waits for and connects to the `MeshCore-OTA` WiFi hotspot
   - Opens the ElegantOTA firmware upload page in your browser
5. **Upload your `.bin` file** via the browser, then click **Yes** in the confirmation dialog when done

> **Note:** ElegantOTA accepts plain `.bin` app binaries (e.g. `firmware.bin` from PlatformIO's `.pio/build/<env>/` folder). If the upload shows 100% but the firmware doesn't change, power-cycle the device immediately after — some builds have auto-reset disabled.

### 🖥️ Serial Monitor Tab

- The monitor **starts automatically** when the app opens — no button press needed
- Select port and baud rate as needed; the monitor restarts automatically on change
- Click **Refresh Ports** to rescan, **Clear** to wipe the output

### ⌨️ MeshCore CLI Tab

1. **Select port and baud rate**, then click **🔌 Connect**
2. **Enter CLI mode on the device** — usually hold the **BOOT** button on the device, power on
3. Wait for the `>` prompt — the status bar updates to **CLI Active ✓** when confirmed
4. **Select device type** (Repeater / Companion / Room Server) — quick-button groups update automatically
5. **Click any group header** (e.g. `▸ Info`) to expand it and reveal the command buttons
6. **Hover any button** for a detailed tooltip explaining the command
7. **Type custom commands** in the input bar and press Enter; use ↑/↓ to recall history
8. Click **⏏ Disconnect** when done — the Serial Monitor resumes automatically

> **Tip:** If commands are sent but nothing comes back, the 3-second watchdog will show guidance. Usually hold BOOT on the device and power on to enter CLI mode first.

---

## Troubleshooting

### BLE connection fails
- Ensure `bleak` and `meshcore` are installed: `pip install bleak meshcore`
- On Linux, ensure your user has Bluetooth permissions (add to `bluetooth` group if needed)

### "Python not found"
- **Windows**: Reinstall Python with "Add to PATH" checked
- **Linux/macOS**: Install via package manager (`python3`)

### "No module named 'tkinter'"
- **Linux**: `sudo apt-get install python3-tk`
- **macOS**: `brew install python-tk`

### "PlatformIO not found"
- `pip install platformio` or visit https://platformio.org/install/cli

### Serial Monitor shows nothing / CLI gets no response
- Ensure `pyserial` is installed: `pip install pyserial`
- Check the correct port is selected and the device is connected
- For CLI: usually hold **BOOT** on the device, power on to enter CLI mode — you should see a `>` prompt appear

### Serial connection drops on Linux (USB autosuspend)
- The app automatically disables USB autosuspend when connecting (Linux only) to prevent drops
- If you don't see "Disabled USB autosuspend" in the log, writing to sysfs may require root — try: `sudo python3 meshcore_flasher.py`
- Or disable autosuspend manually before running: `echo -1 | sudo tee /sys/bus/usb/devices/*/power/autosuspend`

### OTA WiFi won't connect
- Ensure `nmcli` (NetworkManager) is available on Linux
- Wait 10–15 seconds after `start ota` for the hotspot to appear
- Try manually connecting to `MeshCore-OTA` in your OS network settings

### OTA upload hits 100% but firmware doesn't change
- Power-cycle the device immediately after the browser shows success — auto-reset may be disabled
- Ensure you're uploading the app-only `.bin` (not a merged/full-flash image)
- The correct file is typically `.pio/build/<env>/firmware.bin`

### Embedded browser not showing in OTA tab
- ElegantOTA requires JavaScript; the app always uses your external browser for OTA uploads

---

## Design Philosophy

- **Enthusiast-focused** — Covers everything a regular MeshCore user needs without requiring CLI knowledge, while also providing a full CLI for power users
- **Non-destructive** — Automatic backups on every save; easy reset to original
- **Transparent** — All UI changes (BLE name, settings) are reflected directly in the source files you can inspect
- **Minimal friction** — Automatic setup, device memory, cached contacts, and always-on serial monitor reduce repetitive steps
- **Real-time feedback** — Comprehensive logging, colour-coded CLI output, status indicators, and watchdog hints throughout

## Support

For issues or questions, check the log output in the application for detailed error messages, or open an issue on GitHub.
