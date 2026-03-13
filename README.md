# Meshcore Firmware Editor and Flasher

A comprehensive, intuitive GUI tool for editing, compiling, flashing, and managing MeshCore firmware — all in one place.

**Repository:** https://github.com/basiccode12/Meshcore-Firmware-Editor-and-Flasher

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Features

### 📦 Firmware Management
- **Download firmware from GitHub** - Download directly from the MeshCore repository
  - Select from available branches and tags
  - Filter versions by firmware type
  - Automatic version detection
- **Browse local firmware files** - Load and edit your own firmware files
- **Firmware type selection** - Choose between **Companion Radio**, **Repeater Radio**, and **Room Server**
- **Automatic project setup** - Clones and configures the MeshCore repository automatically

### ✏️ Code Editing
- **C++ Source Code Editor** (`main.cpp`) - Full-featured editor with:
  - Syntax highlighting (via QScintilla if installed)
  - Find and replace (Ctrl+F)
  - Auto-loads when firmware is downloaded or browsed
  - Save with automatic backup creation
  - Reload from disk / Reset to original
  - Real-time change tracking
- **PlatformIO.ini Editor** - Edit build settings, environments, and device targets
  - Same editing features as the C++ editor

### 🔧 BLE Name Customisation
- **Optional custom BLE name** - Override the default `MeshCore-<node_name>` naming convention
- **Immediate reflection** - Changes applied to `main.cpp` instantly; visible in the C++ editor
- **Standard code restore** - Leave the field blank and click Apply to revert to the standard MeshCore naming
- **⚠️ Note** - A custom BLE name may interfere with automatic Bluetooth connection in some MeshCore phone apps

### 🔨 Build & Flash
- **Compile firmware** - Build for your selected device using PlatformIO
- **Flash via USB** - Upload compiled firmware directly from the serial port selector
- **Flash pre-built `.bin`** - Browse and flash any `.bin` file without compiling
- **Serial port selector** - Choose a specific port or use Auto-detect
- **🔄 Refresh Ports** button - Rescan available serial ports at any time
- **Real-time progress** - Watch compilation and flashing in the log panel

### 📡 OTA Update
- **Wireless firmware updates** over WiFi via the MeshCore OTA workflow
  - BLE scan and connect to your local gateway device
  - Load contacts from the device to select the remote target
  - Sends `start ota` command via the mesh network
  - Automatically connects to the `MeshCore-OTA` WiFi hotspot
  - Opens the upload page (embedded browser if `tkinterweb` installed, otherwise external)
  - Monitors completion and reconnects to your previous WiFi
- **Manual BLE & WiFi disconnect** - All disconnects are user-initiated, no automatic teardown
- **Contact caching** - Contacts cached per device for faster repeat use
- **Device memory** - Remembers last BLE device and target device between sessions
- **Send stop ota** - Gracefully shuts down the device hotspot on manual WiFi disconnect

### 🖥️ Serial Monitor
- **Live serial output** - Stream device output directly in the app
- **Auto-start on tab switch** - Monitoring begins as soon as you open the tab
- **Port selector** - Choose a specific port or auto-detect
- **Baud rate selection** - Standard baud rates supported
- **Clear output** - One-click clear of the terminal window

### 🎨 User Interface
- **Tabbed layout** - Organised into: Welcome · Firmware · main.cpp · platformio.ini · OTA Update · Serial Monitor
- **Connection status indicators** - BLE and WiFi dots turn **green** when connected, grey when not
- **Fullscreen layout** - Opens maximised for maximum workspace
- **Vertical log panel** - Real-time logs on the right side of the screen
- **Device memory** - Remembers last BLE device, target device, and serial port
- **Keyboard shortcuts** - Ctrl+F for find in editors

---

## Requirements

- **Python 3.8 or higher**
- **PlatformIO** (auto-installed — required for compile/flash)
- **Git** (auto-installed — required for downloading firmware)
- **meshcore** Python library — `pip install meshcore` (required for OTA)
- **bleak** — `pip install bleak` (required for BLE in OTA)
- **Optional: tkinterweb** — `pip install tkinterweb` (embedded browser in OTA tab)
- **Optional: QScintilla / PyQt5** — `pip install QScintilla PyQt5` (syntax highlighting in editors)
- **For OTA on Linux** — NetworkManager (`nmcli`) for automatic WiFi management

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
pip install meshcore bleak
# Optional extras:
pip install tkinterweb QScintilla PyQt5
```

---

## Usage Guide

### 📦 Firmware Tab

1. **Select firmware type** — Companion Radio, Repeater Radio, or Room Server
2. **Download or browse** firmware from GitHub or a local folder
3. **Set BLE Name (Optional)** — Enter a custom name to override `MeshCore-<node_name>`, or leave blank to keep the standard convention. Click **✏ Apply to main.cpp** (or press Enter) to apply immediately.
4. **Select device** — Choose from the auto-populated dropdown (filtered by firmware type)
5. **Compile** — Click **🔨 Compile** to build; BLE name is applied automatically before compilation
6. **Flash** — Connect via USB, select the serial port, and click **⚡ Flash**
7. **Flash pre-built .bin** — Click **Browse .bin** then **Flash .bin** to skip compilation

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
   - Opens the firmware upload page
   - Monitors completion and reconnects your previous WiFi
5. Upload your `.bin` file via the browser, then wait for the confirmation dialog

### 🖥️ Serial Monitor Tab

- Switch to the tab — monitoring starts automatically
- Select port and baud rate as needed
- Click **Clear** to wipe the output

---

## Troubleshooting

### BLE connection fails
- Ensure `bleak` and `meshcore` are installed: `pip install bleak meshcore`
- On Linux, ensure your user has Bluetooth permissions (add to `bluetooth` group if needed)

### "Python not found"
- **Windows**: Reinstall Python with "Add to PATH" checked
- **Linux/macOS**: Install via package manager

### "No module named 'tkinter'"
- **Linux**: `sudo apt-get install python3-tk`
- **macOS**: `brew install python-tk`

### "PlatformIO not found"
- `pip install platformio` or visit https://platformio.org/install/cli

### OTA WiFi won't connect
- Ensure `nmcli` (NetworkManager) is available on Linux
- Wait 10–15 seconds after `start ota` for the hotspot to appear
- Try manually connecting to `MeshCore-OTA` first

### Embedded browser not showing
- Install tkinterweb: `pip install tkinterweb`
- Without it the app opens the upload page in your default browser

---

## Design Philosophy

- **Enthusiast-focused** — Covers everything a regular MeshCore user needs to touch without requiring CLI knowledge
- **Non-destructive** — Automatic backups on every save; easy reset to original
- **Transparent** — All UI changes (BLE name, settings) are reflected directly in the source files you can inspect
- **Minimal friction** — Automatic setup, device memory, and cached contacts reduce repetitive steps
- **Real-time feedback** — Comprehensive logging and colour-coded status indicators throughout

## Support

For issues or questions, check the log output in the application for detailed error messages, or open an issue on GitHub.
