#!/usr/bin/env python3
"""
Meshcore Firmware Editor and Flasher
A simple GUI tool to change BLE name and flash firmware to MeshCore devices

Copyright (c) 2024 MeshCore
Licensed under the MIT License
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import urllib.request
import json
from datetime import datetime
import subprocess
import threading
import tempfile
import shutil
import time
import sys
import configparser
import re
import http.server
import socketserver
import socket
import asyncio
import webbrowser
from urllib.parse import urlparse

# Try to import QScintilla for advanced code editing
HAS_QSCINTILLA = False
QSCINTILLA_EDITOR = None
try:
    from PyQt5.QtWidgets import QApplication, QWidget
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.Qsci import QsciScintilla, QsciLexerCPP, QsciLexerProperties
    from PyQt5.QtGui import QColor
    import sip
    HAS_QSCINTILLA = True
except ImportError:
    try:
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.Qsci import QsciScintilla, QsciLexerCPP, QsciLexerProperties
        from PyQt6.QtGui import QColor
        import sip
        HAS_QSCINTILLA = True
    except ImportError:
        HAS_QSCINTILLA = False

# GitHub repository URLs
GITHUB_API_BASE = "https://api.github.com/repos/meshcore-dev/MeshCore"
GITHUB_BRANCHES_URL = f"{GITHUB_API_BASE}/branches"
GITHUB_TAGS_URL = f"{GITHUB_API_BASE}/tags"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/meshcore-dev/MeshCore/{ref}/examples/{firmware_type}/main.cpp"
MESHCORE_FIRMWARE_REPO_URL = "https://github.com/meshcore-dev/MeshCore.git"


class QScintillaWrapper:
    """Wrapper class to integrate QScintilla with Tkinter - provides ScrolledText-compatible interface"""
    def __init__(self, parent_frame, language='cpp'):
        self.parent_frame = parent_frame
        self.language = language
        self.use_qscintilla = False
        self.qsci_editor = None
        self.container_frame = None
        
        if HAS_QSCINTILLA:
            try:
                # Create QApplication if it doesn't exist
                if not QApplication.instance():
                    self.qapp = QApplication([])
                else:
                    self.qapp = QApplication.instance()
                
                # Create container frame for embedding
                self.container_frame = tk.Frame(parent_frame)
                
                # Create QScintilla editor
                self.qsci_editor = QsciScintilla()
                
                # Set up lexer based on language
                if language == 'cpp':
                    lexer = QsciLexerCPP()
                    lexer.setDefaultFont(self.qsci_editor.font())
                    self.qsci_editor.setLexer(lexer)
                elif language == 'ini' or language == 'properties':
                    lexer = QsciLexerProperties()
                    lexer.setDefaultFont(self.qsci_editor.font())
                    self.qsci_editor.setLexer(lexer)
                
                # Configure editor features
                self.qsci_editor.setUtf8(True)
                self.qsci_editor.setAutoIndent(True)
                self.qsci_editor.setIndentationGuides(True)
                self.qsci_editor.setIndentationsUseTabs(False)
                self.qsci_editor.setIndentationWidth(2)
                self.qsci_editor.setTabWidth(2)
                self.qsci_editor.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
                self.qsci_editor.setCaretLineVisible(True)
                self.qsci_editor.setCaretLineBackgroundColor(QColor("#e8e8e8"))
                self.qsci_editor.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
                self.qsci_editor.setMarginWidth(0, "0000")
                self.qsci_editor.setMarginsBackgroundColor(QColor("#f0f0f0"))
                self.qsci_editor.setMarginsForegroundColor(QColor("#808080"))
                self.qsci_editor.setFolding(QsciScintilla.FoldStyle.PlainFoldStyle)
                self.qsci_editor.setFoldMarginColors(QColor("#f0f0f0"), QColor("#f0f0f0"))
                
                # Note: Embedding PyQt widgets in Tkinter is complex and platform-specific
                # For now, we'll use a simpler approach: create the QScintilla widget
                # but display it in a way that works. Full embedding requires additional setup.
                # This is a placeholder - in a production environment, you might want to:
                # 1. Use a library like 'pyqt5-tk' if available
                # 2. Use platform-specific embedding code
                # 3. Or switch the entire app to PyQt
                
                # For now, we'll attempt basic embedding on Windows, but fall back gracefully
                try:
                    wid = self.container_frame.winfo_id()
                    if sys.platform == "win32":
                        # Windows: Attempt embedding using SetParent
                        try:
                            import ctypes
                            from ctypes import wintypes
                            # Get QScintilla window handle
                            qsci_hwnd = int(self.qsci_editor.winId())
                            # Get Tkinter frame handle
                            tk_hwnd = wid
                            # Embed QScintilla into Tkinter frame
                            ctypes.windll.user32.SetParent(qsci_hwnd, tk_hwnd)
                            # Show the QScintilla widget
                            self.qsci_editor.show()
                            self.use_qscintilla = True
                            self.editor = self.qsci_editor
                        except Exception as embed_error:
                            # Embedding failed, fall back to ScrolledText
                            raise embed_error
                    else:
                        # For Linux/macOS, embedding is more complex
                        # For now, fall back to ScrolledText
                        # TODO: Implement proper X11/Cocoa embedding
                        raise Exception(f"QScintilla embedding not yet implemented for {sys.platform}")
                except Exception as e:
                    # Embedding failed, fall back to ScrolledText
                    self.use_qscintilla = False
                    self.qsci_editor = None
                    self.container_frame = None
                    self.editor = scrolledtext.ScrolledText(parent_frame, wrap=tk.NONE, font=('Courier', 10))
            except Exception as e:
                # QScintilla setup failed, use ScrolledText
                self.use_qscintilla = False
                self.editor = scrolledtext.ScrolledText(parent_frame, wrap=tk.NONE, font=('Courier', 10))
        else:
            # QScintilla not available, use ScrolledText
            self.editor = scrolledtext.ScrolledText(parent_frame, wrap=tk.NONE, font=('Courier', 10))
        
        # Store callbacks for event handling
        self._callbacks = {}
    
    def grid(self, **kwargs):
        """Place the editor widget"""
        if self.use_qscintilla and self.container_frame:
            self.container_frame.grid(**kwargs)
            # Resize QScintilla to match container
            def resize_editor():
                if self.container_frame and self.qsci_editor:
                    width = self.container_frame.winfo_width()
                    height = self.container_frame.winfo_height()
                    if width > 1 and height > 1:
                        self.qsci_editor.resize(width, height)
            self.container_frame.after(100, resize_editor)
            # Update on resize
            self.container_frame.bind('<Configure>', lambda e: resize_editor())
        else:
            self.editor.grid(**kwargs)
    
    def get(self, start, end):
        """Get text content - compatible with Tkinter ScrolledText interface"""
        if self.use_qscintilla:
            text = self.qsci_editor.text()
            if start == '1.0' and end == tk.END:
                return text
            # Handle position-based extraction (simplified)
            lines = text.split('\n')
            start_line, start_col = map(int, start.split('.'))
            if end == tk.END:
                end_line, end_col = len(lines), len(lines[-1]) if lines else 0
            else:
                end_line, end_col = map(int, end.split('.'))
            
            result_lines = lines[start_line-1:end_line]
            if result_lines:
                result_lines[0] = result_lines[0][start_col:]
                result_lines[-1] = result_lines[-1][:end_col]
            return '\n'.join(result_lines)
        else:
            return self.editor.get(start, end)
    
    def delete(self, start, end):
        """Delete text"""
        if self.use_qscintilla:
            if start == '1.0' and end == tk.END:
                self.qsci_editor.clear()
            else:
                # Handle range deletion (simplified - clear all for now)
                self.qsci_editor.clear()
        else:
            self.editor.delete(start, end)
    
    def insert(self, pos, text):
        """Insert text"""
        if self.use_qscintilla:
            if pos == '1.0':
                self.qsci_editor.setText(text)
            else:
                # Handle position-based insertion (simplified - append for now)
                current = self.qsci_editor.text()
                self.qsci_editor.setText(current + text)
        else:
            self.editor.insert(pos, text)
    
    def bind(self, event, callback):
        """Bind event - maps Tkinter events to QScintilla signals"""
        if self.use_qscintilla:
            # Map Tkinter events to QScintilla signals
            if event == '<KeyRelease>':
                self.qsci_editor.textChanged.connect(lambda: callback(None))
            elif event == '<Button-1>':
                self.qsci_editor.cursorPositionChanged.connect(lambda: callback(None))
            self._callbacks[event] = callback
        else:
            self.editor.bind(event, callback)
    
    def tag_config(self, tag, **kwargs):
        """Configure text tag - only works with ScrolledText"""
        if not self.use_qscintilla:
            self.editor.tag_config(tag, **kwargs)
    
    def tag_add(self, tag, start, end):
        """Add tag to text range - only works with ScrolledText"""
        if not self.use_qscintilla:
            self.editor.tag_add(tag, start, end)
    
    def tag_remove(self, tag, start, end):
        """Remove tag from text range - only works with ScrolledText"""
        if not self.use_qscintilla:
            self.editor.tag_remove(tag, start, end)
    
    def mark_set(self, mark, pos):
        """Set mark position - only works with ScrolledText"""
        if not self.use_qscintilla:
            self.editor.mark_set(mark, pos)
    
    def see(self, pos):
        """Scroll to position"""
        if self.use_qscintilla:
            # Convert Tkinter position to QScintilla line/column and scroll
            try:
                line, col = map(int, pos.split('.'))
                self.qsci_editor.setCursorPosition(line - 1, col)
                self.qsci_editor.ensureLineVisible(line - 1)
            except:
                pass
        else:
            self.editor.see(pos)
    
    def search(self, pattern, start, end, **kwargs):
        """Search for pattern - only works with ScrolledText"""
        if not self.use_qscintilla:
            return self.editor.search(pattern, start, end, **kwargs)
        # For QScintilla, use built-in find functionality
        return None


class OTARequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for serving firmware binaries"""
    
    def __init__(self, bin_file_path, *args, **kwargs):
        self.bin_file_path = bin_file_path
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for firmware binary"""
        if self.path == '/firmware.bin' or self.path == '/update':
            try:
                if not os.path.exists(self.bin_file_path):
                    self.send_error(404, "Firmware file not found")
                    return
                
                # Get file size
                file_size = os.path.getsize(self.bin_file_path)
                
                # Send headers
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(self.bin_file_path)}"')
                self.send_header('Content-Length', str(file_size))
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                
                # Send file in chunks
                with open(self.bin_file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                
            except Exception as e:
                self.send_error(500, f"Error serving file: {str(e)}")
        else:
            # Return simple HTML page for root
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>MeshCore OTA Update Server</title></head>
            <body>
                <h1>MeshCore OTA Update Server</h1>
                <p>Firmware available at: <a href="/firmware.bin">/firmware.bin</a></p>
                <p>File: {os.path.basename(self.bin_file_path)}</p>
                <p>Size: {os.path.getsize(self.bin_file_path) / 1024:.2f} KB</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        """Override to suppress default logging"""
        pass


class MeshCoreBLEFlasher:
    def __init__(self, root):
        self.root = root
        self.root.title("Meshcore Firmware Editor and Flasher")
        # Set window to fullscreen/maximized (cross-platform)
        import sys
        if sys.platform == 'win32':
            # Windows
            self.root.state('zoomed')
        elif sys.platform == 'darwin':
            # macOS
            self.root.state('zoomed')
        else:
            # Linux - use geometry to maximize
            self.root.update_idletasks()
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            self.root.geometry(f"{width}x{height}+0+0")
        self.root.resizable(True, True)
        
        # State variables
        # Separate file paths and content for each firmware type
        self.file_paths = {
            "companion_radio": None,
            "simple_repeater": None,
            "room_server": None,
        }
        self.original_contents = {
            "companion_radio": None,
            "simple_repeater": None,
            "room_server": None,
        }
        # Keep for backward compatibility and current access
        self.file_path = None  # Will point to current firmware type's file
        self.original_content = None  # Will point to current firmware type's content
        self.is_downloaded = False
        self.project_dir = None
        self.is_compiling = False
        self.platformio_available = False
        self.all_devices = {}  # Store all devices (unfiltered)
        self.available_devices = {}  # Filtered devices based on firmware type
        self.platformio_ini_modified = False
        self.platformio_ini_loaded_path = None  # Track loaded platformio.ini file path
        self.selected_version = "main"  # Default to main branch
        self.available_versions = []  # Will be populated with branches and tags
        self.firmware_type = "companion_radio"  # Default to companion_radio (maps to examples/companion_radio)
        
        # Storage settings
        self.storage_root = None  # User-selectable root folder
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'meshcore_config.ini')
        self.load_storage_settings()
        
        # OTA settings
        self.ota_server = None
        self.ota_server_thread = None
        self.ota_server_port = 8080
        self.ota_bin_file = None
        self.ota_device_ip = None
        self.last_compiled_bin = None  # Store path to last compiled binary
        self.ota_meshcore = None  # MeshCore connection for OTA/contact-loading
        self.ota_contacts_dict = {}  # Map dropdown display name to public_key
        self.ota_contacts_cache = {}
        self._ota_ble_spin_active = False       # BLE scan spinner state
        self._ota_contacts_spin_active = False  # Contacts load spinner state
        # Single persistent event loop for all BLE/OTA async operations so that
        # the MeshCore object created during Load Contacts can be safely reused
        # by the OTA workflow without "Future attached to a different loop" errors.
        import asyncio as _asyncio
        self.ota_event_loop = _asyncio.new_event_loop()
        _ota_loop_thread = threading.Thread(
            target=self.ota_event_loop.run_forever,
            daemon=True, name="ota-event-loop"
        )
        _ota_loop_thread.start()  # Cache contacts per BLE device: {ble_address: (contact_list, contact_dict)}
        self.ota_scanned_devices = {}  # Map display name to (name, address) for scanned BLE devices
        self.previous_wifi_connection = None  # Store previous WiFi connection before OTA
        self.ota_wifi_connected = False  # Track if connected to MeshCore-OTA
        self.last_ble_device = None  # Store last BLE device address
        self.last_target_device = None  # Store last target device ID
        
        # Theme and UI settings
        self.dark_mode = False  # Dark mode toggle
        self.recent_files = []  # Recent files list (max 10)
        self.auto_save_enabled = True  # Auto-save for editors
        self.auto_save_timer = None  # Timer for auto-save
        self.compilation_start_time = None  # Track compilation time
        
        # OTA history
        self.ota_history = []  # Store OTA update history

        # Serial monitor state
        self.serial_monitor_process = None
        self.serial_monitor_running = False
        self._sm_usb_autosuspend_path = None
        self._sm_usb_autosuspend_old = None
        self.serial_monitor_after_id = None
        self._sm_shutting_down = False

        # MeshCore CLI tab state
        self.cli_serial = None
        self.cli_running = False
        self._cli_usb_autosuspend_path = None
        self._cli_usb_autosuspend_old = None
        self.cli_cmd_history = []
        self.cli_history_idx = -1
        self.cli_quick_btn_widgets = []  # keep refs so we can destroy/rebuild
        self._cli_mode_active = False    # True once we see a '>' prompt
        self._cli_pending_get = None      # "radio" or "name" when waiting to parse response
        self._cli_pending_get_buf = []    # accumulate response lines for parsing
        self._cli_no_response_id = None  # after() id for no-response hint timer

        self.setup_ui()
        self.check_platformio()
        
        # Automatically refresh device list on startup (same approach as meshcore_ble_name_editor)
        self.root.after(100, self.refresh_devices)
        
        # Ensure window is visible
        self.root.after(500, lambda: self._ensure_window_visible())
    
    def _ensure_window_visible(self):
        """Ensure the window is visible and on top"""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.root.update()
        except:
            pass
    
    def create_scrollable_frame(self, parent):
        """Create a scrollable frame with canvas and scrollbar"""
        # Create canvas and scrollbar
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Create window in canvas for scrollable frame
        canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Configure canvas scrolling
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mousewheel scrolling (works on Windows and Mac)
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"  # Prevent event propagation
        
        # Enable mousewheel scrolling for Linux (Button-4 and Button-5)
        def on_mousewheel_linux(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            return "break"  # Prevent event propagation
        
        # Function to recursively bind mousewheel to widget and all its children
        def bind_mousewheel_to_children(widget):
            """Recursively bind mousewheel events to widget and all its children"""
            widget.bind("<MouseWheel>", on_mousewheel)
            widget.bind("<Button-4>", on_mousewheel_linux)
            widget.bind("<Button-5>", on_mousewheel_linux)
            for child in widget.winfo_children():
                bind_mousewheel_to_children(child)
        
        # Update scroll region when frame size changes
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Keep canvas width equal to scrollable frame width
            canvas_width = event.width
            canvas.itemconfig(canvas_frame, width=canvas_width)
            # Bind mousewheel to any new children that were added
            bind_mousewheel_to_children(scrollable_frame)
        
        scrollable_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_frame, width=e.width))
        
        # Bind mousewheel events to canvas
        canvas.bind("<MouseWheel>", on_mousewheel)
        canvas.bind("<Button-4>", on_mousewheel_linux)
        canvas.bind("<Button-5>", on_mousewheel_linux)
        
        # Bind mousewheel events to scrollable frame so scrolling works anywhere in the frame
        scrollable_frame.bind("<MouseWheel>", on_mousewheel)
        scrollable_frame.bind("<Button-4>", on_mousewheel_linux)
        scrollable_frame.bind("<Button-5>", on_mousewheel_linux)
        
        # Also bind to canvas focus for better scrolling
        canvas.bind("<Enter>", lambda e: canvas.focus_set())
        
        # Initial bind to existing children
        bind_mousewheel_to_children(scrollable_frame)
        
        # Grid canvas and scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        return scrollable_frame, canvas, scrollbar
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        # Configure for 2 columns: content on left, logs on right
        main_frame.columnconfigure(0, weight=3)           # Content area (expands)
        main_frame.columnconfigure(1, weight=1, minsize=220)  # Log area (never < 220 px)
        main_frame.rowconfigure(0, weight=1)
        
        # Left side: Content area
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(content_frame, text="Meshcore Firmware Editor and Flasher",
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # Right side: Log output (shared across tabs) - vertical layout
        # Create this first so it's available for logging during tab setup
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="10")
        log_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log text widget - sized for vertical sidebar (narrower width, full height)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=1, width=50,
                                                   font=('Courier', 9), wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create tabs
        self.welcome_tab = ttk.Frame(self.notebook, padding="10")
        self.firmware_tab = ttk.Frame(self.notebook, padding="10")
        self.settings_tab = ttk.Frame(self.notebook, padding="10")
        self.cpp_editor_tab = ttk.Frame(self.notebook, padding="10")
        self.ota_tab = ttk.Frame(self.notebook, padding="10")
        self.serial_monitor_tab = ttk.Frame(self.notebook, padding="10")
        self.cli_tab = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.welcome_tab, text="🏠 Welcome")
        self.notebook.add(self.firmware_tab, text="📦 Firmware")
        self.notebook.add(self.cpp_editor_tab, text="main.cpp")
        self.notebook.add(self.settings_tab, text="platformio.ini")
        self.notebook.add(self.ota_tab, text="📡 OTA Update")
        self.notebook.add(self.serial_monitor_tab, text="🖥️ Serial Monitor")
        self.notebook.add(self.cli_tab, text="⌨️ MeshCore CLI")
        
        # Setup welcome tab
        self.setup_welcome_tab()
        
        # Setup firmware tab
        self.setup_firmware_tab()
        
        # Setup C++ editor tab
        self.setup_cpp_editor_tab()
        
        # Setup settings tab
        self.setup_settings_tab()
        
        # Setup OTA tab
        self.setup_ota_tab()

        # Setup Serial Monitor tab
        self.setup_serial_monitor_tab()

        # Setup MeshCore CLI tab
        self.setup_cli_tab()

        # Auto-start serial monitor once the main loop is running
        self.root.after(500, self.start_serial_monitor)
        
        # Load OTA checkbox settings (after OTA tab is set up)
        self.load_ota_checkbox_settings()
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Setup auto-save timer
        if self.auto_save_enabled:
            self.setup_auto_save()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_welcome_tab(self):
        """Setup the Welcome tab with app information and purpose"""
        # Create scrollable frame
        scrollable_frame, canvas, scrollbar = self.create_scrollable_frame(self.welcome_tab)
        welcome_frame = scrollable_frame
        welcome_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(welcome_frame, text="Meshcore Firmware Editor and Flasher",
                               font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        subtitle_label = ttk.Label(welcome_frame,
            text="An all-in-one GUI tool for editing, compiling, flashing and managing MeshCore firmware.",
            font=('Arial', 10), foreground='gray')
        subtitle_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 20))

        # Purpose section
        purpose_frame = ttk.LabelFrame(welcome_frame, text="Purpose", padding="15")
        purpose_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        purpose_frame.columnconfigure(0, weight=1)
        purpose_label = ttk.Label(purpose_frame, font=('Arial', 10),
                                  foreground='black', justify=tk.LEFT, wraplength=800,
                                  text=(
            "This application gives MeshCore enthusiasts a single, intuitive place to manage firmware — "
            "from downloading source code and editing key settings, to compiling, flashing, OTA updates, "
            "and direct serial CLI access.\n\n"
            "All UI changes are reflected directly in the underlying source files so you always know "
            "exactly what the firmware will contain."
        ))
        purpose_label.grid(row=0, column=0, sticky=tk.W)

        # Key Features section
        features_frame = ttk.LabelFrame(welcome_frame, text="Key Features", padding="15")
        features_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        features_frame.columnconfigure(0, weight=1)
        features_label = ttk.Label(features_frame, font=('Arial', 9),
                                   foreground='black', justify=tk.LEFT, wraplength=800,
                                   text=(
            "📦 FIRMWARE MANAGEMENT\n"
            "   • Download firmware from GitHub — Companion Radio, Repeater Radio, or Room Server\n"
            "   • Browse and load local firmware files\n"
            "   • Automatic version detection and type filtering\n\n"
            "🔧 BLE NAME CUSTOMISATION\n"
            "   • Optional custom BLE name overrides the default MeshCore-<node_name> convention\n"
            "   • Applied immediately to main.cpp and visible in the C++ editor\n"
            "   • Leave blank and click Apply to revert to the standard naming code\n"
            "   • ⚠ Custom names may interfere with auto-connect in some MeshCore phone apps\n\n"
            "✏️ CODE EDITING\n"
            "   • Full-featured C++ editor for main.cpp (syntax highlighting if QScintilla installed)\n"
            "   • PlatformIO.ini editor — edit build settings, environments, and targets\n"
            "   • Find/replace (Ctrl+F), auto-backup on save, reload, reset to original\n\n"
            "🔨 BUILD & FLASH\n"
            "   • Compile firmware using PlatformIO for your selected device\n"
            "   • Flash via USB — select a specific serial port or use Auto-detect\n"
            "   • Flash pre-built .bin files directly — no compilation needed\n"
            "   • Flash modes: Update Only (keeps settings) or Full Erase (wipes entire flash)\n"
            "   • 🔄 Refresh Ports to rescan available serial ports at any time\n\n"
            "📡 OTA UPDATE\n"
            "   • Wireless firmware updates via the MeshCore OTA workflow\n"
            "   • BLE scan → load contacts → send 'start ota' → auto-connect to MeshCore-OTA WiFi\n"
            "   • Upload .bin via ElegantOTA in your browser; confirmation dialog waits for you\n"
            "   • Reconnects to your previous WiFi on completion\n\n"
            "🖥️ SERIAL MONITOR\n"
            "   • Always-on live device output — starts automatically, auto-reconnects if unplugged\n"
            "   • Uses pyserial directly — no PlatformIO subprocess required\n"
            "   • Port sharing — pauses automatically when CLI tab takes the connection\n\n"
            "⌨️ MESHCORE CLI\n"
            "   • Direct serial CLI — send any MeshCore command over USB serial\n"
            "   • Context-sensitive quick buttons for Repeater, Companion, and Room Server\n"
            "   • Collapsible command groups (Info, Logging, Radio, Power, Region, GPS, Manage)\n"
            "   • Hover tooltips on every button with full command description\n"
            "   • CLI mode detection — confirms when '>' prompt is active\n"
            "   • No-response watchdog — guides you if commands aren't getting replies\n"
            "   • Command history navigation with ↑/↓ arrow keys\n\n"
            "🎨 USER INTERFACE\n"
            "   • BLE and WiFi status dots turn green when connected\n"
            "   • Fullscreen layout with vertical log panel (minimum width enforced)\n"
            "   • Device memory — remembers last BLE device, target, and serial port\n"
            "   • Tabs: Welcome · Firmware · main.cpp · platformio.ini · OTA Update · Serial Monitor · MeshCore CLI"
        ))
        features_label.grid(row=0, column=0, sticky=tk.W)

        # Workflow section
        workflow_frame = ttk.LabelFrame(welcome_frame, text="Typical Workflows", padding="15")
        workflow_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        workflow_frame.columnconfigure(0, weight=1)
        workflow_label = ttk.Label(workflow_frame, font=('Arial', 9),
                                   foreground='black', justify=tk.LEFT, wraplength=800,
                                   text=(
            "Compile & Flash from source:\n"
            "  1. 📦 Firmware tab   — select type, download or browse, set optional BLE name\n"
            "  2. ✏️ main.cpp tab   — review or edit source code\n"
            "  3. ⚙️ platformio.ini — adjust build settings if needed\n"
            "  4. 🔨 Compile        — build firmware (BLE name applied automatically)\n"
            "  5. ⚡ Flash          — select serial port, choose flash mode, and upload\n\n"
            "Flash a pre-built .bin:\n"
            "  1. 📦 Firmware tab  — click Browse .bin, select your file\n"
            "  2. ⚡ Flash .bin    — select serial port and flash immediately\n\n"
            "OTA Update:\n"
            "  1. 📡 OTA Update tab — scan for and select your local BLE gateway device\n"
            "  2. Load Contacts     — fetch the device contact list, select the remote target\n"
            "  3. Start OTA Update  — app handles BLE, WiFi, and opens upload page in browser\n"
            "  4. Upload .bin       — upload in the browser, then confirm in the dialog\n\n"
            "Serial CLI:\n"
            "  1. ⌨️ MeshCore CLI tab — select port/baud, click Connect\n"
            "  2. Enter CLI mode       — usually hold BOOT on device, power on\n"
            "  3. Wait for '>'         — a '>' prompt confirms CLI mode is active\n"
            "  4. Select device type  — quick buttons update for Repeater / Companion / Room\n"
            "  5. Expand a group      — click any ▸ header, then click a command button\n"
            "  6. Disconnect          — Serial Monitor resumes automatically"
        ))
        workflow_label.grid(row=0, column=0, sticky=tk.W)

        # Requirements section
        requirements_frame = ttk.LabelFrame(welcome_frame, text="Requirements", padding="15")
        requirements_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        requirements_frame.columnconfigure(0, weight=1)
        requirements_label = ttk.Label(requirements_frame, font=('Arial', 9),
                                       foreground='black', justify=tk.LEFT, wraplength=800,
                                       text=(
            "• Python 3.8 or higher\n"
            "• pyserial  — pip install pyserial  (required for Serial Monitor and CLI)\n"
            "• PlatformIO  — pip install platformio  (required for compile/flash)\n"
            "• Git  (required to download firmware from GitHub)\n"
            "• meshcore  — pip install meshcore  (required for OTA)\n"
            "• bleak  — pip install bleak  (required for BLE in OTA)\n"
            "• Optional: tkinterweb  — pip install tkinterweb  (embedded browser in OTA tab)\n"
            "• Optional: QScintilla / PyQt5  — pip install QScintilla PyQt5  (syntax highlighting)\n"
            "• Linux OTA: NetworkManager (nmcli) for automatic WiFi management"
        ))
        requirements_label.grid(row=0, column=0, sticky=tk.W)

        # Repository section
        repo_frame = ttk.LabelFrame(welcome_frame, text="Repository & License", padding="15")
        repo_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        repo_frame.columnconfigure(0, weight=1)
        repo_label = ttk.Label(repo_frame, font=('Arial', 9),
                               foreground='black', justify=tk.LEFT, wraplength=800,
                               text=(
            "Repository: https://github.com/basiccode12/Meshcore-Firmware-Editor-and-Flasher\n"
            "License: MIT License\n\n"
            "Contributions, bug reports, and feature requests are welcome via GitHub Issues."
        ))
        repo_label.grid(row=0, column=0, sticky=tk.W)

        # Getting Started section
        getting_started_frame = ttk.LabelFrame(welcome_frame, text="Getting Started", padding="15")
        getting_started_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        getting_started_frame.columnconfigure(0, weight=1)
        getting_started_label = ttk.Label(getting_started_frame, font=('Arial', 9),
                                          foreground='black', justify=tk.LEFT, wraplength=800,
                                          text=(
            "Head to the 📦 Firmware tab to download or load a firmware project — that's all you need "
            "to get started. All operations are logged in the panel on the right.\n\n"
            "For live device output, the 🖥️ Serial Monitor starts automatically.\n\n"
            "For interactive configuration, use the ⌨️ MeshCore CLI tab — connect, "
            "enter CLI mode on the device, and start sending commands. Hover any quick-button for a full description."
        ))
        getting_started_label.grid(row=0, column=0, sticky=tk.W)
    
    def setup_firmware_tab(self):
        """Setup the firmware tab"""
        # Create scrollable frame
        scrollable_frame, canvas, scrollbar = self.create_scrollable_frame(self.firmware_tab)
        firmware_frame = scrollable_frame
        firmware_frame.columnconfigure(0, weight=1)
        firmware_frame.columnconfigure(1, weight=1)
        firmware_frame.rowconfigure(4, weight=1)
        
        # Storage Settings Section (at the top)
        storage_frame = ttk.LabelFrame(firmware_frame, text="📁 Storage Settings", padding="10")
        storage_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        storage_frame.columnconfigure(1, weight=1)
        
        ttk.Label(storage_frame, text="Root Folder:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        self.storage_root_var = tk.StringVar()
        if self.storage_root:
            self.storage_root_var.set(self.storage_root)
        else:
            self.storage_root_var.set("Not set - files will be saved in current directory")
        
        storage_path_label = ttk.Label(storage_frame, textvariable=self.storage_root_var,
                                      font=('Courier', 9), foreground='blue', wraplength=600)
        storage_path_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(storage_frame, text="📂 Browse", 
                  command=self.select_storage_root, width=15).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(storage_frame, text="🗑️ Clear", 
                  command=self.clear_storage_root, width=12).grid(row=0, column=3)
        
        info_label = ttk.Label(storage_frame, 
                              text="Files will be organized in date-labeled folders: YYYY-MM-DD/bin/, YYYY-MM-DD/cpp/, YYYY-MM-DD/platformio/",
                              font=('Arial', 8), foreground='gray', wraplength=700)
        info_label.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(5, 0))
        
        # Step 1: Get Firmware
        step1_frame = ttk.LabelFrame(firmware_frame, text="1. Get Firmware", padding="10")
        step1_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        step1_frame.columnconfigure(1, weight=1)
        
        # Version selection
        version_frame = ttk.Frame(step1_frame)
        version_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        version_frame.columnconfigure(1, weight=1)
        
        ttk.Label(version_frame, text="Firmware Type:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        
        self.firmware_type_var = tk.StringVar()
        self.firmware_type_var.set("Companion Radio")
        firmware_type_combo = ttk.Combobox(version_frame, textvariable=self.firmware_type_var,
                                           values=["Companion Radio", "Repeater Radio", "Room Server"],
                                           state='readonly', width=18)
        firmware_type_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        firmware_type_combo.bind('<<ComboboxSelected>>', self._on_firmware_type_selected)
        
        ttk.Label(version_frame, text="Version:").grid(row=0, column=2, padx=(10, 5), sticky=tk.W)
        
        self.version_var = tk.StringVar()
        self.version_var.set("main")
        self.version_combo = ttk.Combobox(version_frame, textvariable=self.version_var,
                                         values=["main"], state='readonly', width=25)
        self.version_combo.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(0, 10))
        self.version_combo.bind('<<ComboboxSelected>>', self._on_version_selected)
        
        ttk.Button(version_frame, text="🔄 Refresh Versions",
                  command=self.refresh_versions, width=18).grid(row=0, column=4)
        
        # Download and browse buttons
        button_frame = ttk.Frame(step1_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Button(button_frame, text="📥 Download Selected",
                  command=self.download_firmware, width=18).grid(row=0, column=0, padx=(0, 5))
        
        ttk.Button(button_frame, text="📂 Browse Local File",
                  command=self.browse_file, width=18).grid(row=0, column=1, padx=(0, 5))
        
        self.file_path_var = tk.StringVar()
        self.file_path_var.set("No file loaded")
        ttk.Label(step1_frame, textvariable=self.file_path_var,
                 foreground='blue', font=('Arial', 9)).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Load versions on startup (after firmware type is set)
        self.root.after(500, self.refresh_versions)
        
        # Step 2: BLE Name (Left Column)
        step2_frame = ttk.LabelFrame(firmware_frame, text="2. Set BLE Name (Optional)", padding="10")
        step2_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 5), pady=(0, 10))
        step2_frame.columnconfigure(1, weight=1)
        
        ttk.Label(step2_frame, text="BLE Name:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        self.ble_name_var = tk.StringVar()
        name_entry = ttk.Entry(step2_frame, textvariable=self.ble_name_var, font=('Arial', 10))
        name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        name_entry.bind('<Return>', lambda e: self.apply_ble_name_changes())

        ttk.Button(step2_frame, text="✏ Apply to main.cpp",
                   command=self.apply_ble_name_changes, width=20).grid(
            row=0, column=2, padx=(8, 0), sticky=tk.W)

        ttk.Label(step2_frame, text="Leave blank to use MeshCore's default naming: MeshCore-<node_name>",
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 1))
        ttk.Label(step2_frame, text="If set, overwrites the default — written into main.cpp and reflected in the C++ editor. Also applied automatically on compile.",
                 font=('Arial', 8), foreground='gray').grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(0, 2))
        ttk.Label(step2_frame, text="⚠ Custom names may break auto-connect in MeshCore phone apps (apps scan for 'MeshCore-*').",
                 font=('Arial', 8), foreground='#b35900').grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(0, 0))
        
        # Step 3: Device Selection (Right Column)
        step3_frame = ttk.LabelFrame(firmware_frame, text="3. Select Device", padding="10")
        step3_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N), padx=(5, 0), pady=(0, 10))
        step3_frame.columnconfigure(1, weight=1)
        
        ttk.Label(step3_frame, text="Device:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(step3_frame, textvariable=self.device_var,
                                         values=[], state='readonly', width=30)
        self.device_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Step 4: Edit C++ (Optional) (Left Column)
        step4_frame = ttk.LabelFrame(firmware_frame, text="4. Edit main.cpp (Optional)", padding="10")
        step4_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=(0, 5), pady=(0, 10))
        step4_frame.columnconfigure(0, weight=1)
        
        ttk.Button(step4_frame, text="main.cpp",
                  command=self.go_to_cpp_editor_tab, width=30).grid(row=0, column=0)
        
        ttk.Label(step4_frame, text="Edit source code before compiling", 
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, pady=(5, 0))
        
        # Step 5: Configure PlatformIO (Optional) (Right Column)
        step5_frame = ttk.LabelFrame(firmware_frame, text="5. Configure PlatformIO (Optional)", padding="10")
        step5_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0, 10))
        step5_frame.columnconfigure(0, weight=1)
        
        ttk.Button(step5_frame, text="platformio.ini",
                  command=self.go_to_settings_tab, width=30).grid(row=0, column=0)
        
        ttk.Label(step5_frame, text="Edit platformio.ini configuration", 
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, pady=(5, 0))
        
        # Step 6: Build & Flash (Full Width)
        step6_frame = ttk.LabelFrame(firmware_frame, text="6. Build & Flash", padding="10")
        step6_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        step6_frame.columnconfigure(0, weight=1)

        # Serial port selector row
        port_frame = ttk.Frame(step6_frame)
        port_frame.grid(row=0, column=0, sticky=tk.W, pady=(0, 8))

        ttk.Label(port_frame, text="Serial Port:").grid(row=0, column=0, padx=(0, 8), sticky=tk.W)
        self.serial_port_var = tk.StringVar(value="Auto")
        self.serial_port_combo = ttk.Combobox(port_frame, textvariable=self.serial_port_var,
                                              values=["Auto"], state='readonly', width=22)
        self.serial_port_combo.grid(row=0, column=1, padx=(0, 5))
        ttk.Button(port_frame, text="🔄 Refresh Ports", command=self.refresh_serial_ports_combo,
                   width=16).grid(row=0, column=2)
        ttk.Label(port_frame, text="(Auto = PlatformIO detects)",
                  font=('Arial', 8), foreground='gray').grid(row=0, column=3, padx=(8, 0))

        # Flash mode selection
        flash_mode_frame = ttk.Frame(step6_frame)
        flash_mode_frame.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        ttk.Label(flash_mode_frame, text="Flash Mode:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        self.flash_mode_var = tk.StringVar()
        self.flash_mode_var.set("update")  # Default to update only
        
        ttk.Radiobutton(flash_mode_frame, text="Update Only", variable=self.flash_mode_var,
                       value="update", width=15).grid(row=0, column=1, padx=5)
        ttk.Radiobutton(flash_mode_frame, text="Full Erase", variable=self.flash_mode_var,
                       value="erase", width=15).grid(row=0, column=2, padx=5)
        
        ttk.Label(flash_mode_frame, text="(Update: faster, keeps settings)", 
                 font=('Arial', 8), foreground='gray').grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=(2, 0))
        
        button_frame = ttk.Frame(step6_frame)
        button_frame.grid(row=2, column=0)
        
        self.compile_btn = ttk.Button(button_frame, text="🔨 Compile",
                                      command=self.compile_firmware, width=15)
        self.compile_btn.grid(row=0, column=0, padx=5)
        
        self.flash_btn = ttk.Button(button_frame, text="⚡ Flash",
                                   command=self.flash_firmware, width=15)
        self.flash_btn.grid(row=0, column=1, padx=5)
        
        self.ota_quick_btn = ttk.Button(button_frame, text="📡 OTA Update",
                                       command=self.go_to_ota_tab, width=15)
        self.ota_quick_btn.grid(row=0, column=2, padx=5)

        # Pre-built binary flash section
        prebuilt_frame = ttk.LabelFrame(step6_frame, text="Flash Pre-built .bin (no compile needed)", padding="8")
        prebuilt_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(12, 0))
        prebuilt_frame.columnconfigure(1, weight=1)

        ttk.Label(prebuilt_frame, text="Binary:").grid(row=0, column=0, padx=(0, 8), sticky=tk.W)
        self.prebuilt_bin_var = tk.StringVar(value="No file selected")
        ttk.Label(prebuilt_frame, textvariable=self.prebuilt_bin_var,
                  foreground='blue', font=('Arial', 9),
                  wraplength=400).grid(row=0, column=1, sticky=(tk.W, tk.E))
        ttk.Button(prebuilt_frame, text="📂 Browse .bin",
                   command=self.browse_prebuilt_bin, width=14).grid(row=0, column=2, padx=(8, 4))
        self.flash_prebuilt_btn = ttk.Button(prebuilt_frame, text="⚡ Flash .bin",
                                             command=self.flash_prebuilt_bin, width=13)
        self.flash_prebuilt_btn.grid(row=0, column=3)
        ttk.Label(prebuilt_frame,
                  text="Directly flash any .bin file via the selected serial port (uses esptool).",
                  font=('Arial', 8), foreground='gray').grid(row=1, column=0, columnspan=4,
                                                              sticky=tk.W, pady=(4, 0))
        self.prebuilt_bin_path = None  # actual path stored here
        
        # Status
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        ttk.Label(step6_frame, textvariable=self.status_var,
                 font=('Arial', 9), foreground='gray').grid(row=5, column=0, pady=(5, 0))
    
    def setup_cpp_editor_tab(self):
        """Setup the C++ file editor tab"""
        # Direct grid layout — no scrollable-frame wrapper so the editor can fill all space
        tab = self.cpp_editor_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)   # editor container row expands

        # Title row
        title_frame = ttk.Frame(tab)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
        title_frame.columnconfigure(0, weight=1)

        ttk.Label(title_frame, text="C++ Source Code Editor",
                  font=('Arial', 14, 'bold')).grid(row=0, column=0, sticky=tk.W)

        self.cpp_editor_status_var = tk.StringVar(value="No file loaded")
        ttk.Label(title_frame, textvariable=self.cpp_editor_status_var,
                  font=('Arial', 9), foreground='gray').grid(row=0, column=1, sticky=tk.E)

        # Info label
        ttk.Label(tab,
                  text="Edit the main.cpp source code. Changes will be saved to the current firmware file.",
                  font=('Arial', 9), foreground='gray').grid(
            row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 4))

        # Editor container — this row has weight=1 so it stretches
        editor_container = ttk.Frame(tab)
        editor_container.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        editor_container.columnconfigure(0, weight=1)
        editor_container.rowconfigure(2, weight=1)   # editor_frame row

        # File path label
        self.cpp_editor_path_var = tk.StringVar(value="No file loaded yet")
        ttk.Label(editor_container, textvariable=self.cpp_editor_path_var,
                  font=('Courier', 8), foreground='blue').grid(
            row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 3))

        # Find bar (hidden by default)
        self.cpp_find_bar = ttk.Frame(editor_container)
        self.cpp_find_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 3))
        self.cpp_find_bar.columnconfigure(1, weight=1)
        self.cpp_find_bar_visible = False
        self.cpp_find_bar.grid_remove()

        ttk.Label(self.cpp_find_bar, text="Find:").grid(row=0, column=0, padx=(0, 5))
        self.cpp_find_entry = ttk.Entry(self.cpp_find_bar, width=30)
        self.cpp_find_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.cpp_find_entry.bind('<Return>', lambda e: self.cpp_find_next())
        self.cpp_find_entry.bind('<KeyRelease>', self._on_cpp_find_entry_change)
        ttk.Button(self.cpp_find_bar, text="🔍 Find Next",
                   command=self.cpp_find_next, width=12).grid(row=0, column=2, padx=2)
        ttk.Button(self.cpp_find_bar, text="⬆️ Find Previous",
                   command=self.cpp_find_previous, width=14).grid(row=0, column=3, padx=2)
        ttk.Button(self.cpp_find_bar, text="✕",
                   command=self.cpp_hide_find_bar, width=3).grid(row=0, column=4, padx=(5, 0))
        self.cpp_find_status_var = tk.StringVar(value="")
        ttk.Label(self.cpp_find_bar, textvariable=self.cpp_find_status_var,
                  font=('Arial', 8), foreground='gray').grid(
            row=1, column=0, columnspan=5, sticky=tk.W, pady=(3, 0))

        # Editor frame — fills all remaining vertical space
        editor_frame = ttk.Frame(editor_container)
        editor_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(0, weight=1)

        try:
            self.cpp_editor = QScintillaWrapper(editor_frame, language='cpp')
            if self.cpp_editor.use_qscintilla:
                self.log("✓ Using QScintilla editor with advanced features (syntax highlighting, code folding, etc.)")
            else:
                self.log("⚠ QScintilla not available, using basic ScrolledText editor")
                self.log("  Install PyQt5 and QScintilla for advanced editing features:")
                self.log("    pip install PyQt5 PyQt5-QScintilla")
        except Exception as e:
            self.log(f"⚠ Error initializing QScintilla: {str(e)}")
            self.log("  Falling back to basic ScrolledText editor")
            self.cpp_editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.NONE, font=('Courier', 10))

        self.cpp_editor.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Button row (fixed height, below the editor)
        button_frame = ttk.Frame(tab)
        button_frame.grid(row=3, column=0, pady=(6, 0))
        
        ttk.Button(button_frame, text="🔍 Find", 
                  command=self.cpp_show_find_bar, width=12).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="📁 Load File", 
                  command=self.load_cpp_file_from_disk, width=15).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="🔄 Reload", 
                  command=self.reload_cpp_file, width=15).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="💾 Save", 
                  command=self.save_cpp_file, width=15).grid(row=0, column=3, padx=5)
        ttk.Button(button_frame, text="↩️ Reset to Original", 
                  command=self.reset_cpp_file, width=20).grid(row=0, column=4, padx=5)
        
        # Track if content was modified
        self.cpp_original_content = None
        self.cpp_modified = False
        
        # Bind text change events
        self.cpp_editor.bind('<KeyRelease>', self._on_cpp_editor_change)
        self.cpp_editor.bind('<Button-1>', self._on_cpp_editor_change)
        
        # Bind Ctrl+F for find
        self.cpp_editor.bind('<Control-f>', lambda e: (self.cpp_show_find_bar(), 'break'))
        self.cpp_editor.bind('<Control-F>', lambda e: (self.cpp_show_find_bar(), 'break'))
        
        # Track find state
        self.cpp_find_search_start = '1.0'
        self.cpp_find_matches = []
        self.cpp_find_current_match = -1
    
    def setup_settings_tab(self):
        """Setup the settings tab with platformio.ini editor"""
        # Direct grid layout — no scrollable-frame wrapper so the editor fills all space
        tab = self.settings_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)   # editor container row expands

        # Title row
        title_frame = ttk.Frame(tab)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
        title_frame.columnconfigure(1, weight=1)

        ttk.Label(title_frame, text="PlatformIO Configuration",
                  font=('Arial', 14, 'bold')).grid(row=0, column=0, sticky=tk.W)

        self.platformio_ini_status_var = tk.StringVar(value="No changes made")
        ttk.Label(title_frame, textvariable=self.platformio_ini_status_var,
                  font=('Arial', 9), foreground='gray').grid(row=0, column=1, sticky=tk.E)

        # Info label
        ttk.Label(tab,
                  text="Edit the platformio.ini file to customize build settings, environments, and other PlatformIO options.",
                  font=('Arial', 9), foreground='gray').grid(
            row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 4))

        # Editor container — stretches vertically
        editor_container = ttk.Frame(tab)
        editor_container.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        editor_container.columnconfigure(0, weight=1)
        editor_container.rowconfigure(2, weight=1)   # editor_frame row

        # File path label
        self.platformio_ini_path_var = tk.StringVar(value="Project not loaded yet")
        ttk.Label(editor_container, textvariable=self.platformio_ini_path_var,
                  font=('Courier', 8), foreground='blue').grid(
            row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 3))

        # Find bar (hidden by default)
        self.find_bar = ttk.Frame(editor_container)
        self.find_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 3))
        self.find_bar.columnconfigure(1, weight=1)
        self.find_bar_visible = False
        self.find_bar.grid_remove()

        ttk.Label(self.find_bar, text="Find:").grid(row=0, column=0, padx=(0, 5))
        self.find_entry = ttk.Entry(self.find_bar, width=30)
        self.find_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.find_entry.bind('<Return>', lambda e: self.find_next())
        self.find_entry.bind('<KeyRelease>', self._on_find_entry_change)
        ttk.Button(self.find_bar, text="🔍 Find Next",
                   command=self.find_next, width=12).grid(row=0, column=2, padx=2)
        ttk.Button(self.find_bar, text="⬆️ Find Previous",
                   command=self.find_previous, width=14).grid(row=0, column=3, padx=2)
        ttk.Button(self.find_bar, text="✕",
                   command=self.hide_find_bar, width=3).grid(row=0, column=4, padx=(5, 0))
        self.find_status_var = tk.StringVar(value="")
        ttk.Label(self.find_bar, textvariable=self.find_status_var,
                  font=('Arial', 8), foreground='gray').grid(
            row=1, column=0, columnspan=5, sticky=tk.W, pady=(3, 0))

        # Editor frame — fills all remaining vertical space
        editor_frame = ttk.Frame(editor_container)
        editor_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(0, weight=1)

        try:
            self.platformio_ini_editor = QScintillaWrapper(editor_frame, language='ini')
            if self.platformio_ini_editor.use_qscintilla:
                if not hasattr(self, '_qscintilla_logged') or not self._qscintilla_logged:
                    self.log("✓ Using QScintilla editor for platformio.ini")
                    self._qscintilla_logged = True
        except Exception as e:
            if not hasattr(self, '_qscintilla_error_logged') or not self._qscintilla_error_logged:
                self.log(f"⚠ Error initializing QScintilla for platformio.ini: {str(e)}")
                self._qscintilla_error_logged = True
            self.platformio_ini_editor = scrolledtext.ScrolledText(
                editor_frame, wrap=tk.NONE, font=('Courier', 10))

        self.platformio_ini_editor.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Button row (fixed height, below the editor)
        button_frame = ttk.Frame(tab)
        button_frame.grid(row=3, column=0, pady=(6, 0))
        
        ttk.Button(button_frame, text="🔍 Find", 
                  command=self.show_find_bar, width=12).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="📁 Load File", 
                  command=self.load_platformio_ini_from_disk, width=15).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="🔄 Reload", 
                  command=self.reload_platformio_ini, width=15).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="💾 Save", 
                  command=self.save_platformio_ini, width=15).grid(row=0, column=3, padx=5)
        ttk.Button(button_frame, text="↩️ Reset to Original", 
                  command=self.reset_platformio_ini, width=20).grid(row=0, column=4, padx=5)
        
        # Track if content was modified
        self.platformio_ini_original_content = None
        self.platformio_ini_modified = False
        
        # Bind text change events
        self.platformio_ini_editor.bind('<KeyRelease>', self._on_platformio_ini_change)
        self.platformio_ini_editor.bind('<Button-1>', self._on_platformio_ini_change)
        
        # Bind Ctrl+F for find
        self.platformio_ini_editor.bind('<Control-f>', lambda e: (self.show_find_bar(), 'break'))
        self.platformio_ini_editor.bind('<Control-F>', lambda e: (self.show_find_bar(), 'break'))
        
        # Track find state
        self.find_search_start = '1.0'
        self.find_matches = []
        self.find_current_match = -1
        
        # Load platformio.ini when settings tab is selected
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
    
    def setup_ota_tab(self):
        """Setup the OTA update tab"""
        # Create scrollable frame
        scrollable_frame, canvas, scrollbar = self.create_scrollable_frame(self.ota_tab)
        ota_frame = scrollable_frame
        ota_frame.columnconfigure(0, weight=1)
        ota_frame.rowconfigure(4, weight=1)
        
        # Title
        title_label = ttk.Label(ota_frame, text="WiFi OTA Firmware Update",
                               font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Device roles explanation section (collapsible)
        roles_container = ttk.Frame(ota_frame)
        roles_container.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        roles_container.columnconfigure(0, weight=1)
        
        self.roles_expanded = False
        roles_header = ttk.Frame(roles_container)
        roles_header.grid(row=0, column=0, sticky=(tk.W, tk.E))
        roles_header.columnconfigure(1, weight=1)
        
        self.roles_toggle_btn = ttk.Button(roles_header, text="▶ Device Roles (Click to expand)",
                                          command=lambda: self._toggle_section('roles'))
        self.roles_toggle_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        roles_text = (
            "📱 LOCAL BLE DEVICE (Gateway):\n"
            "   • This is YOUR MeshCore device connected via Bluetooth\n"
            "   • Acts as a gateway to relay commands over the mesh network\n"
            "   • Must be within BLE range of your computer\n\n"
            "🌐 TARGET DEVICE (Remote):\n"
            "   • This is the REMOTE MeshCore device you want to update\n"
            "   • NO direct BLE connection - only accessible via mesh network\n"
            "   • Must be in the local device's contact list\n"
            "   • All commands (WiFi on/off, OTA URL) are sent through the gateway device"
        )
        
        self.roles_content_frame = ttk.LabelFrame(roles_container, text="Device Roles", padding="10")
        self.roles_content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.roles_content_frame.columnconfigure(0, weight=1)
        self.roles_content_frame.grid_remove()  # Initially hidden
        
        ttk.Label(self.roles_content_frame, text=roles_text, font=('Arial', 9), foreground='darkblue',
                 justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)
        
        # Steps section (collapsible)
        steps_container = ttk.Frame(ota_frame)
        steps_container.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        steps_container.columnconfigure(0, weight=1)
        
        self.steps_expanded = False
        steps_header = ttk.Frame(steps_container)
        steps_header.grid(row=0, column=0, sticky=(tk.W, tk.E))
        steps_header.columnconfigure(1, weight=1)
        
        self.steps_toggle_btn = ttk.Button(steps_header, text="▶ Steps (Click to expand)",
                                          command=lambda: self._toggle_section('steps'))
        self.steps_toggle_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        info_text = (
            "1. Select your LOCAL BLE device (gateway) and scan for it\n"
            "2. Connect to local device and load contacts\n"
            "3. Select TARGET device from contacts (the remote device to update)\n"
            "4. (Optional) Enter admin password if required\n"
            "5. Click 'Start OTA Update' - sends 'start ota' command to target device\n"
            "6. Device creates WiFi hotspot: MeshCore-OTA\n"
            "7. App will auto-connect to MeshCore-OTA WiFi\n"
            "8. Browser opens automatically - upload your .bin file\n"
            "9. Wait for update to complete (WiFi reconnects automatically)"
        )
        
        self.steps_content_frame = ttk.LabelFrame(steps_container, text="Steps", padding="10")
        self.steps_content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.steps_content_frame.columnconfigure(0, weight=1)
        self.steps_content_frame.grid_remove()  # Initially hidden
        
        ttk.Label(self.steps_content_frame, text=info_text, font=('Arial', 9), foreground='black',
                 justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)
        
        # Configuration section
        config_frame = ttk.LabelFrame(ota_frame, text="Configuration", padding="10")
        config_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # BLE Device selection (local gateway device)
        ttk.Label(config_frame, text="Local BLE Device (Gateway):").grid(row=0, column=0, padx=(0, 10), sticky=tk.W, pady=5)
        self.ota_ble_device_var = tk.StringVar()
        self.ota_ble_device_var.set("Auto-scan")
        
        # Combobox for scanned devices
        self.ota_ble_device_combo = ttk.Combobox(config_frame, textvariable=self.ota_ble_device_var,
                                                 width=40, state='readonly')
        self.ota_ble_device_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=5)
        self.ota_ble_device_combo.bind('<<ComboboxSelected>>', self._on_ble_device_selected)
        
        ttk.Button(config_frame, text="🔍 Scan", 
                  command=self.scan_ble_devices, width=12).grid(row=0, column=2, pady=5)
        self.ota_ble_spinner_var = tk.StringVar(value="")
        ttk.Label(config_frame, textvariable=self.ota_ble_spinner_var,
                  font=('Arial', 12), foreground='#1a6fc4').grid(row=0, column=3, padx=(6, 0))
        ttk.Label(config_frame, text="Click Scan to find MeshCore devices, or leave as 'Auto-scan'", 
                 font=('Arial', 8), foreground='gray').grid(row=1, column=1, sticky=tk.W, padx=(0, 10))
        
        # Store scanned devices info
        self.ota_scanned_devices = {}  # Map display name to (name, address)
        
        # Target device ID (device to update via mesh) - now a dropdown with search
        ttk.Label(config_frame, text="Target Device (Remote):").grid(row=2, column=0, padx=(0, 10), sticky=tk.W, pady=5)
        
        # Search field for filtering contacts
        search_frame = ttk.Frame(config_frame)
        search_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=5)
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="🔍 Search:", font=('Arial', 8)).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.ota_target_search_var = tk.StringVar()
        self.ota_target_search_var.set("")
        search_entry = ttk.Entry(search_frame, textvariable=self.ota_target_search_var, width=25)
        search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        search_entry.bind('<KeyRelease>', self._on_search_target_device)
        
        self.ota_target_device_var = tk.StringVar()
        self.ota_target_device_var.set("")
        self.ota_target_device_combo = ttk.Combobox(config_frame, textvariable=self.ota_target_device_var, 
                                                    width=30, state='readonly')
        self.ota_target_device_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=5)
        self.ota_target_device_combo.bind('<<ComboboxSelected>>', self._on_target_device_selected)
        ttk.Button(config_frame, text="🔄 Load Contacts", 
                  command=self.load_contacts_from_device, width=15).grid(row=3, column=2, pady=5)
        self.ota_contacts_spinner_var = tk.StringVar(value="")
        ttk.Label(config_frame, textvariable=self.ota_contacts_spinner_var,
                  font=('Arial', 12), foreground='#1a6fc4').grid(row=3, column=3, padx=(6, 0))
        ttk.Label(config_frame, text="Select from local device's contact list (REQUIRED)", 
                 font=('Arial', 8), foreground='gray').grid(row=4, column=1, sticky=tk.W, padx=(0, 10))
        
        # Store full contact list for filtering
        self.ota_all_contacts_list = []  # Full unfiltered list
        self.ota_all_contacts_dict = {}  # Full unfiltered dict
        
        # Try to restore last BLE device and auto-connect
        self.root.after(1000, self._restore_last_devices)  # Delay to let UI initialize
        
        # Admin Password (optional, for device access)
        ttk.Label(config_frame, text="Admin Password:").grid(row=4, column=0, padx=(0, 10), sticky=tk.W, pady=5)
        self.ota_admin_password_var = tk.StringVar()
        self.ota_admin_password_var.set("")
        admin_password_entry = ttk.Entry(config_frame, textvariable=self.ota_admin_password_var, 
                                         width=20, show="*")
        admin_password_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=5)
        ttk.Label(config_frame, text="Optional: Admin password from device settings", 
                 font=('Arial', 8), foreground='gray').grid(row=5, column=1, sticky=tk.W, padx=(0, 10))
        
        # Disconnect options
        disconnect_options_frame = ttk.Frame(config_frame)
        disconnect_options_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 5))

        self.ota_keep_wifi_connected_var = tk.BooleanVar()
        self.ota_keep_wifi_connected_var.set(False)
        keep_wifi_checkbox = ttk.Checkbutton(disconnect_options_frame,
                                            text="Keep WiFi connected (do not disconnect from MeshCore-OTA)",
                                            variable=self.ota_keep_wifi_connected_var)
        keep_wifi_checkbox.grid(row=0, column=0, sticky=tk.W)

        ttk.Label(config_frame, text="Note: BLE stays connected until you use Manual Disconnect.",
                 font=('Arial', 8), foreground='gray').grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        
        # Connection Status & Manual Disconnect section
        conn_status_frame = ttk.LabelFrame(config_frame, text="Connection Status", padding="8")
        conn_status_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 5))
        conn_status_frame.columnconfigure(1, weight=1)
        conn_status_frame.columnconfigure(3, weight=1)
        
        # BLE status + disconnect
        ttk.Label(conn_status_frame, text="BLE:", font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.ble_status_var = tk.StringVar(value="⚫ Not connected")
        self.ble_status_label = ttk.Label(conn_status_frame, textvariable=self.ble_status_var,
                                          font=('Arial', 9), foreground='gray')
        self.ble_status_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        self.manual_ble_disconnect_btn = ttk.Button(conn_status_frame, text="🔌 Disconnect BLE",
                                                    command=self.manual_ble_disconnect, width=18)
        self.manual_ble_disconnect_btn.grid(row=0, column=2, padx=(10, 5))
        
        # WiFi status + disconnect
        ttk.Label(conn_status_frame, text="WiFi:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.wifi_status_var = tk.StringVar(value="⚫ Not connected to MeshCore-OTA")
        self.wifi_status_label = ttk.Label(conn_status_frame, textvariable=self.wifi_status_var,
                                           font=('Arial', 9), foreground='gray')
        self.wifi_status_label.grid(row=1, column=1, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.manual_wifi_disconnect_btn = ttk.Button(conn_status_frame, text="📶 Disconnect WiFi",
                                                     command=self.manual_wifi_disconnect, width=18)
        self.manual_wifi_disconnect_btn.grid(row=1, column=2, padx=(10, 5), pady=(5, 0))
        
        # Control buttons
        button_frame = ttk.Frame(ota_frame)
        button_frame.grid(row=4, column=0, pady=(10, 0))
        
        self.ota_update_btn = ttk.Button(button_frame, text="📤 Start OTA Update",
                                         command=self.start_ota_update_workflow, width=20)
        self.ota_update_btn.grid(row=0, column=2, padx=5)
        
        # Progress section
        progress_frame = ttk.LabelFrame(ota_frame, text="Progress", padding="10")
        progress_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        progress_frame.columnconfigure(0, weight=1)
        
        self.ota_progress_var = tk.StringVar()
        self.ota_progress_var.set("Ready")
        progress_label = ttk.Label(progress_frame, textvariable=self.ota_progress_var,
                                   font=('Arial', 9))
        progress_label.grid(row=0, column=0, sticky=tk.W)
        
        self.ota_progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate', length=400)
        self.ota_progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # OTA Upload Browser section
        browser_frame = ttk.LabelFrame(ota_frame, text="OTA Upload Interface", padding="10")
        browser_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        browser_frame.columnconfigure(0, weight=1)
        browser_frame.rowconfigure(2, weight=1)  # WebView row
        
        browser_info_label = ttk.Label(browser_frame, 
                                      text="After 'start ota' command is sent, the app will auto-connect to MeshCore-OTA WiFi and load the upload page:",
                                      font=('Arial', 9), foreground='gray', wraplength=600)
        browser_info_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Try to use tkinterweb for embedded browser, fallback to external browser
        self.ota_webview = None
        self.ota_webview_frame = None
        self.use_embedded_browser = False
        
        try:
            import tkinterweb
            self.use_embedded_browser = True
            # Create embedded frame for status messages (not for actual browser - ElegantOTA requires JavaScript)
            self.ota_webview_frame = ttk.Frame(browser_frame)
            self.ota_webview_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
            self.ota_webview_frame.columnconfigure(0, weight=1)
            self.ota_webview_frame.rowconfigure(0, weight=1)
            
            # Show info that external browser will be used (ElegantOTA requires JavaScript)
            info_label = ttk.Label(self.ota_webview_frame,
                                   text="OTA upload page opens in external browser.\n"
                                        "ElegantOTA requires JavaScript support.",
                                   font=('Arial', 9), foreground='darkblue', justify=tk.CENTER, wraplength=600)
            info_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
            self.log("✓ Browser frame ready (external browser will be used for OTA uploads)")
        except ImportError:
            # Fallback: show message that external browser will be used
            fallback_label = ttk.Label(browser_frame,
                                       text="Note: OTA upload page opens in external browser.\n"
                                            "ElegantOTA requires JavaScript support.",
                                       font=('Arial', 9), foreground='darkblue', justify=tk.CENTER, wraplength=600)
            fallback_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
            self.log("✓ External browser will be used for OTA uploads")
        
        url_info_label = ttk.Label(browser_frame,
                                   text="Note: 192.168.4.1 is the device's IP when in OTA mode (standard ESP32 AP IP). Works on all PCs once connected to MeshCore-OTA WiFi.",
                                   font=('Arial', 8), foreground='gray', wraplength=600)
        url_info_label.grid(row=3, column=0, sticky=tk.W, pady=(5, 0))
        
        # Store OTA URL (hardcoded - this is the standard IP for ESP32 access points)
        # The device creates its own WiFi hotspot and uses this fixed IP address
        self.ota_upload_url = "http://192.168.4.1/update"
        
        # Load OTA Upload Page button at the bottom
        self.ota_browser_btn = ttk.Button(browser_frame, 
                                          text=f"🌐 Manually Load OTA Upload Page ({self.ota_upload_url})",
                                          command=self.load_ota_upload_page)
        self.ota_browser_btn.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def load_storage_settings(self):
        """Load storage root folder from config file"""
        try:
            config = configparser.ConfigParser()
            if os.path.exists(self.config_file):
                config.read(self.config_file)
                if 'Storage' in config and 'root_folder' in config['Storage']:
                    root = config['Storage']['root_folder']
                    if root and os.path.exists(root):
                        self.storage_root = root
                
                # Load OTA device settings
                if 'OTA' in config:
                    if 'last_ble_device' in config['OTA']:
                        self.last_ble_device = config['OTA']['last_ble_device']
                    if 'last_target_device' in config['OTA']:
                        self.last_target_device = config['OTA']['last_target_device']
        except Exception as e:
            # Called during __init__ before UI is built; use print since log widget may not exist yet
            if hasattr(self, 'log_text'):
                self.log(f"⚠ Could not load storage settings: {str(e)}")
            else:
                print(f"⚠ Could not load storage settings: {str(e)}")
    
    def load_ota_checkbox_settings(self):
        """Load OTA checkbox settings from config file (called after OTA tab is set up)"""
        try:
            config = configparser.ConfigParser()
            if os.path.exists(self.config_file):
                config.read(self.config_file)
                if 'OTA' in config:
                    if hasattr(self, 'ota_keep_wifi_connected_var'):
                        if 'keep_wifi_connected' in config['OTA']:
                            self.ota_keep_wifi_connected_var.set(config['OTA'].getboolean('keep_wifi_connected', False))
        except Exception as e:
            self.log(f"⚠ Could not load OTA checkbox settings: {str(e)}")
    
    def save_storage_settings(self):
        """Save storage root folder to config file"""
        try:
            config = configparser.ConfigParser()
            if os.path.exists(self.config_file):
                config.read(self.config_file)
            
            if 'Storage' not in config:
                config.add_section('Storage')
            
            if self.storage_root:
                config['Storage']['root_folder'] = self.storage_root
            else:
                if 'root_folder' in config['Storage']:
                    config.remove_option('Storage', 'root_folder')
            
            # Save OTA device settings
            if 'OTA' not in config:
                config.add_section('OTA')
            
            if self.last_ble_device:
                config['OTA']['last_ble_device'] = self.last_ble_device
            else:
                if 'last_ble_device' in config['OTA']:
                    config.remove_option('OTA', 'last_ble_device')
            
            if self.last_target_device:
                config['OTA']['last_target_device'] = self.last_target_device
            else:
                if 'last_target_device' in config['OTA']:
                    config.remove_option('OTA', 'last_target_device')
            
            # Save disconnect options
            if hasattr(self, 'ota_keep_wifi_connected_var'):
                config['OTA']['keep_wifi_connected'] = str(self.ota_keep_wifi_connected_var.get())
            
            with open(self.config_file, 'w') as f:
                config.write(f)
        except Exception as e:
            self.log(f"⚠ Could not save storage settings: {str(e)}")
    
    def save_ota_device_settings(self):
        """Save OTA device settings (BLE and target device)"""
        self.save_storage_settings()  # Reuse the same config file
    
    def select_storage_root(self):
        """Open folder dialog to select storage root folder"""
        initial_dir = self.storage_root if self.storage_root else os.path.expanduser("~")
        folder = filedialog.askdirectory(
            title="Select Root Folder for Storing Files",
            initialdir=initial_dir
        )
        if folder:
            self.storage_root = folder
            self.storage_root_var.set(self.storage_root)
            self.save_storage_settings()
            self.log(f"✓ Storage root folder set to: {self.storage_root}")
            messagebox.showinfo("Success", f"Storage root folder set to:\n{self.storage_root}")
    
    def clear_storage_root(self):
        """Clear the storage root folder setting"""
        response = messagebox.askyesno(
            "Clear Storage Root",
            "This will clear the storage root folder setting.\n"
            "Files will be saved in the current directory.\n\n"
            "Continue?"
        )
        if response:
            self.storage_root = None
            self.storage_root_var.set("Not set - files will be saved in current directory")
            self.save_storage_settings()
            self.log("✓ Storage root folder cleared")
    
    def get_date_folder(self):
        """Get the date-labeled folder path for today"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.storage_root:
            return os.path.join(self.storage_root, today)
        else:
            # Fallback to current directory
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), today)
    
    def get_storage_path(self, file_type):
        """
        Get storage path for a specific file type
        file_type: 'bin', 'cpp', or 'platformio'
        Returns: full path to the folder
        """
        date_folder = self.get_date_folder()
        folder = os.path.join(date_folder, file_type)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    def get_local_ip(self):
        """Get the local IP address of this machine"""
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def select_ota_bin_file(self):
        """Open file dialog to select .bin file for OTA update"""
        # First check if we have a recently compiled binary
        initial_dir = None
        if self.storage_root:
            date_folder = self.get_date_folder()
            bin_folder = os.path.join(date_folder, 'bin')
            if os.path.exists(bin_folder):
                initial_dir = bin_folder
        
        filename = filedialog.askopenfilename(
            title="Select Firmware Binary File",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")],
            initialdir=initial_dir if initial_dir else os.path.expanduser("~")
        )
        
        if filename:
            self.ota_bin_file = filename
            self.ota_bin_file_var.set(os.path.basename(filename))
            file_size = os.path.getsize(filename) / 1024  # Size in KB
            self.log(f"✓ Selected OTA firmware: {os.path.basename(filename)} ({file_size:.2f} KB)")
    
    def start_ota_server(self):
        """Start the HTTP server for OTA updates"""
        if not self.ota_bin_file or not os.path.exists(self.ota_bin_file):
            messagebox.showwarning("No File", "Please select a firmware .bin file first.")
            return
        
        try:
            port = int(self.ota_port_var.get())
        except ValueError:
            messagebox.showerror("Invalid Port", "Please enter a valid port number.")
            return
        
        # Create custom handler with bin file path
        handler = lambda *args, **kwargs: OTARequestHandler(self.ota_bin_file, *args, **kwargs)
        
        try:
            # Create server
            self.ota_server = socketserver.TCPServer(("", port), handler)
            self.ota_server.allow_reuse_address = True
            
            # Start server in background thread
            self.ota_server_thread = threading.Thread(target=self._run_ota_server, daemon=True)
            self.ota_server_thread.start()
            
            # Get local IP
            local_ip = self.get_local_ip()
            server_url = f"http://{local_ip}:{port}/firmware.bin"
            
            self.ota_server_status_var.set(f"Running on {local_ip}:{port}")
            self.ota_start_btn.config(state='disabled')
            self.ota_stop_btn.config(state='normal')
            
            self.log(f"\n" + "="*60)
            self.log(f"OTA SERVER STARTED")
            self.log("="*60)
            self.log(f"Server URL: {server_url}")
            self.log(f"Firmware: {os.path.basename(self.ota_bin_file)}")
            self.log(f"Device should connect to: {server_url}")
            self.log("="*60)
            
            messagebox.showinfo("OTA Server Started", 
                              f"OTA server is running!\n\n"
                              f"Server URL: {server_url}\n\n"
                              f"Configure your device to download from this URL.")
            
        except OSError as e:
            if "Address already in use" in str(e):
                messagebox.showerror("Port Busy", f"Port {port} is already in use. Please choose a different port.")
            else:
                messagebox.showerror("Error", f"Failed to start OTA server:\n{str(e)}")
            self.log(f"✗ Failed to start OTA server: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start OTA server:\n{str(e)}")
            self.log(f"✗ Failed to start OTA server: {str(e)}")
    
    def _run_ota_server(self):
        """Run the OTA server in background thread"""
        try:
            self.ota_server.serve_forever()
        except Exception as e:
            self.log(f"✗ OTA server error: {str(e)}")
    
    def stop_ota_server(self):
        """Stop the OTA server"""
        if self.ota_server:
            try:
                self.ota_server.shutdown()
                self.ota_server.server_close()
                self.ota_server = None
                
                self.ota_server_status_var.set("Stopped")
                self.ota_start_btn.config(state='normal')
                self.ota_stop_btn.config(state='disabled')
                
                self.log("✓ OTA server stopped")
            except Exception as e:
                self.log(f"✗ Error stopping OTA server: {str(e)}")
    
    def scan_ble_devices(self):
        """Scan for BLE devices"""
        self.log("Scanning for BLE devices...")
        self.ota_progress_var.set("Scanning for BLE devices...")
        self._start_spinner(self.ota_ble_spinner_var, '_ota_ble_spin_active')
        thread = threading.Thread(target=self._scan_ble_devices_thread, daemon=True)
        thread.start()
    
    def _scan_ble_devices_thread(self):
        """Background thread for BLE scanning - uses same method as BLEConnection"""
        try:
            import asyncio
            from bleak import BleakScanner
            from bleak.backends.scanner import BLEDevice, AdvertisementData

            scan_duration = 5.0
            self.log(f"Scanning for BLE devices ({int(scan_duration)} seconds)...")
            
            async def scan():
                """Scan for all BLE devices, with special handling for MeshCore devices"""
                all_devices = []  # All BLE devices found
                all_scanned_devices = {}  # Map display name to (name, address) for all devices
                meshcore_devices = []  # MeshCore devices only
                meshcore_scanned = {}  # Map display name to (name, address) for MeshCore devices
                seen_addresses = set()  # Track devices we've already added
                meshcore_found_list = []  # List to collect MeshCore devices for logging
                all_found_list = []  # List to collect all devices for logging
                
                def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
                    """Callback to collect all BLE devices"""
                    # Avoid duplicates
                    if device.address in seen_addresses:
                        return
                    seen_addresses.add(device.address)
                    
                    # Get device name from advertisement or device
                    local_name = advertisement_data.local_name
                    device_name = local_name if local_name else (device.name if device.name else f"Unknown ({device.address[:8]})")
                    device_address = device.address
                    
                    # Create display string: "Name (Address)"
                    display_name = f"{device_name} ({device_address})"
                    all_devices.append(display_name)
                    all_scanned_devices[display_name] = (device_name, device_address)
                    all_found_list.append((device_name, device_address))
                    
                    # Check if it's a MeshCore device
                    if local_name and local_name.startswith("MeshCore"):
                        meshcore_devices.append(display_name)
                        meshcore_scanned[display_name] = (device_name, device_address)
                        meshcore_found_list.append((device_name, device_address))
                
                # Use BleakScanner with callback to collect all devices
                scanner = BleakScanner(detection_callback)
                await scanner.start()
                await asyncio.sleep(scan_duration)
                await scanner.stop()
                
                # Log found devices after scanning
                if meshcore_found_list:
                    self.log(f"Found {len(meshcore_found_list)} MeshCore device(s):")
                    for device_name, device_address in meshcore_found_list:
                        self.log(f"  MeshCore: {device_name} - {device_address}")
                
                if all_found_list:
                    self.log(f"Found {len(all_found_list)} total BLE device(s)")
                
                return all_devices, all_scanned_devices, meshcore_devices, meshcore_scanned
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            all_device_list, all_scanned_devices, meshcore_list, meshcore_scanned = loop.run_until_complete(scan())
            loop.close()
            
            # Determine which devices to show
            # If exactly 1 MeshCore device found, use only MeshCore devices
            # If 0 or 2+ MeshCore devices found, show ALL devices
            if len(meshcore_list) == 1:
                # Exactly one MeshCore device - use only MeshCore list
                device_list = meshcore_list
                scanned_devices = meshcore_scanned
                self.log(f"✓ Found exactly 1 MeshCore device - showing MeshCore devices only")
            else:
                # Zero or multiple MeshCore devices - show all devices
                device_list = all_device_list
                scanned_devices = all_scanned_devices
                if len(meshcore_list) == 0:
                    self.log(f"⚠ No MeshCore devices found - showing all {len(all_device_list)} BLE device(s)")
                else:
                    self.log(f"⚠ Found {len(meshcore_list)} MeshCore device(s) - showing all {len(all_device_list)} BLE device(s) for selection")
            
            # Update UI on main thread
            def update_ui():
                self.ota_scanned_devices = scanned_devices
                # Add "Auto-scan" as first option
                all_values = ["Auto-scan"] + device_list
                self.ota_ble_device_combo['values'] = all_values
                
                # Try to restore last BLE device if it's in the scanned list
                restored = False
                if self.last_ble_device:
                    for display_name, (name, address) in scanned_devices.items():
                        if address == self.last_ble_device or name == self.last_ble_device:
                            self.ota_ble_device_var.set(display_name)
                            self.log(f"✓ Restored last BLE device: {display_name}")
                            restored = True
                            # Auto-connect and load contacts
                            self.root.after(500, self._auto_connect_and_load_contacts)
                            break
                
                # If not restored, auto-select first found device
                if not restored and device_list:
                    self.ota_ble_device_var.set(device_list[0])
                elif not restored:
                    self.ota_ble_device_var.set("Auto-scan")
            
            self.root.after(0, update_ui)
            
            self.root.after(0, lambda: self._stop_spinner(self.ota_ble_spinner_var, '_ota_ble_spin_active'))
            self.root.after(0, lambda: self.ota_progress_var.set("Ready"))
        except Exception as e:
            import traceback
            error_msg = str(e)
            traceback_str = traceback.format_exc()
            self.log(f"✗ BLE scan error: {error_msg}")
            self.log(f"Traceback: {traceback_str}")
            self.root.after(0, lambda: self._stop_spinner(self.ota_ble_spinner_var, '_ota_ble_spin_active'))
            self.root.after(0, lambda: self.ota_progress_var.set("Scan failed"))
            def update_ui():
                self.ota_scanned_devices = {}
                self.ota_ble_device_combo['values'] = ["Auto-scan"]
                self.ota_ble_device_var.set("Auto-scan")
            
            self.root.after(0, update_ui)
    
    def _normalize_ble_address(self, address):
        """Normalize BLE address to lowercase for consistent caching"""
        if not address:
            return None
        return address.strip().lower()
    
    def _on_ble_device_selected(self, event=None):
        """Callback when user selects a device from the dropdown"""
        selected_value = self.ota_ble_device_var.get().strip()
        
        if not selected_value or selected_value == "Auto-scan":
            self.last_ble_device = None
            self.save_ota_device_settings()
            return
        
        # Determine BLE address from selection
        ble_address = None
        if selected_value in self.ota_scanned_devices:
            name, address = self.ota_scanned_devices[selected_value]
            ble_address = self._normalize_ble_address(address)  # Normalize for consistent caching
            self.last_ble_device = address  # Save original format
            self.log(f"Device selected: {selected_value} (saved: {address})")
        else:
            ble_address = self._normalize_ble_address(selected_value)
            self.last_ble_device = selected_value
            self.log(f"Device selected: {selected_value}")
        
        self.save_ota_device_settings()

        # Use cache only if it has actual contacts; empty cache means we still need to connect
        if ble_address and ble_address in self.ota_contacts_cache:
            contact_list, contact_dict = self.ota_contacts_cache[ble_address]
            if contact_list:
                self.log(f"✓ Using cached contacts for {ble_address} ({len(contact_list)} contacts)")
                self._populate_contacts_dropdown(contact_list, contact_dict)
                self.ota_progress_var.set("Ready")
                return
            else:
                # Stale empty cache — remove it and fetch fresh
                del self.ota_contacts_cache[ble_address]

        # No valid cache — auto-connect and load contacts
        self._auto_connect_and_load_contacts()
    
    def load_contacts_from_device(self):
        """Load contacts from the local BLE device and populate the target device dropdown"""
        # Get device identifier from combobox
        selected_value = self.ota_ble_device_var.get().strip()
        
        if not selected_value or selected_value == "Auto-scan":
            messagebox.showwarning("No Device", "Please scan and select a local BLE device first, or leave as 'Auto-scan' to auto-detect.")
            return
        
        # Determine which value to use
        if selected_value in self.ota_scanned_devices:
            # User selected from combobox - use the MAC address (more reliable than name)
            name, address = self.ota_scanned_devices[selected_value]
            ble_address = self._normalize_ble_address(address)  # Normalize for consistent caching
            self.log(f"Selected device: {name} ({address})")
        else:
            # User might have manually edited (shouldn't happen with readonly, but handle it)
            ble_address = self._normalize_ble_address(selected_value)
        
        if not ble_address:
            messagebox.showwarning("No Device", "Please select a local BLE device first.")
            return

        # Prevent concurrent BLE contact-load operations — two simultaneous
        # BLE connections to the same device will segfault the native library.
        if self._ota_contacts_spin_active:
            self.log("⚠ Contact load already in progress, please wait...")
            return

        # Always fetch fresh when user explicitly clicks Load Contacts —
        # remove any stale (especially empty) cache entry for this device
        if ble_address in self.ota_contacts_cache:
            del self.ota_contacts_cache[ble_address]

        self.log("Loading contacts from local device...")
        self.ota_progress_var.set("Loading contacts...")
        self._start_spinner(self.ota_contacts_spinner_var, '_ota_contacts_spin_active')
        thread = threading.Thread(target=self._load_contacts_thread, daemon=True, args=(ble_address,))
        thread.start()
    
    def _load_contacts_thread(self, ble_address):
        """Background thread for loading contacts"""
        try:
            import asyncio
            from meshcore import MeshCore
            from meshcore.ble_cx import BLEConnection

            # Normalize address for consistent caching
            normalized_address = self._normalize_ble_address(ble_address)
            # Keep original for connection (BLE library may need original format)
            original_address = ble_address
            
            async def load_contacts():
                meshcore = None
                
                # Check if we already have a connection to this device
                if self.ota_meshcore and hasattr(self.ota_meshcore, 'connection_manager'):
                    try:
                        # Check if connection manager reports connected
                        if self.ota_meshcore.connection_manager.is_connected:
                            # Check if it's the same device by checking the underlying connection
                            if hasattr(self.ota_meshcore.connection_manager, 'cx'):
                                cx = self.ota_meshcore.connection_manager.cx
                                if hasattr(cx, 'address') and self._normalize_ble_address(cx.address) == normalized_address:
                                    # Verify connection is actually working by checking if client is connected
                                    if hasattr(cx, 'client') and hasattr(cx.client, 'is_connected'):
                                        if cx.client.is_connected:
                                            meshcore = self.ota_meshcore
                                            self.log("✓ Using existing BLE connection")
                                        else:
                                            self.log("⚠ Existing connection client not active, reconnecting...")
                                            try:
                                                await self.ota_meshcore.disconnect()
                                            except:
                                                pass
                                            meshcore = None
                                    else:
                                        # Can't verify, try to use it but will reconnect if it fails
                                        meshcore = self.ota_meshcore
                                        self.log("✓ Attempting to use existing BLE connection")
                                else:
                                    self.log("⚠ Existing connection is to different device, reconnecting...")
                                    try:
                                        await self.ota_meshcore.disconnect()
                                    except:
                                        pass
                                    meshcore = None
                            else:
                                # No underlying connection object, reconnect
                                self.log("⚠ Existing connection has no underlying connection, reconnecting...")
                                meshcore = None
                        else:
                            self.log("⚠ Existing connection manager reports not connected, reconnecting...")
                            meshcore = None
                    except Exception as e:
                        self.log(f"⚠ Error checking existing connection: {str(e)}, connecting fresh...")
                        meshcore = None
                
                # If no active connection, create a new one
                if not meshcore:
                    self.log(f"Connecting to local device via BLE...")
                    self.log(f"  Device address: {original_address}")
                    connection_attempts = 0
                    max_attempts = 2
                    
                    while connection_attempts < max_attempts:
                        try:
                            ble_conn = BLEConnection(address=original_address)
                            meshcore = MeshCore(ble_conn, debug=False)
                            self.log("  Attempting connection...")
                            await meshcore.connect()
                            # Verify connection actually worked
                            if meshcore.is_connected:
                                self.log("✓ Connected to local device")
                                break
                            else:
                                raise ConnectionError("Connection returned but is_connected is False")
                        except Exception as e:
                            connection_attempts += 1
                            error_msg = str(e)
                            if connection_attempts < max_attempts:
                                self.log(f"⚠ Connection attempt {connection_attempts} failed: {error_msg}")
                                self.log("  Retrying...")
                                await asyncio.sleep(1)  # Brief delay before retry
                            else:
                                # Last attempt failed, try auto-scan if address format might be wrong
                                if ":" not in ble_address:
                                    self.log("  Retrying with auto-scan (device name provided)...")
                                    try:
                                        ble_conn = BLEConnection(address=None)  # Auto-scan
                                        meshcore = MeshCore(ble_conn, debug=False)
                                        await meshcore.connect()
                                        if meshcore.is_connected:
                                            self.log("✓ Connected via auto-scan")
                                            break
                                        else:
                                            raise ConnectionError("Auto-scan connection returned but is_connected is False")
                                    except Exception as e2:
                                        raise Exception(f"Connection failed with address ({error_msg}) and auto-scan ({str(e2)})")
                                else:
                                    raise Exception(f"Connection failed after {max_attempts} attempts: {error_msg}")
                
                # Wait a moment for connection to stabilize (MeshCore examples pattern)
                self.log("Waiting for connection to stabilize...")
                await asyncio.sleep(1.0)
                
                # Get contacts - use get_contacts() which waits for the CONTACTS event
                # This is the proper way per MeshCore examples
                self.log("Fetching contacts...")
                from meshcore.events import EventType
                
                # Use get_contacts() with a longer timeout to wait for all contacts
                # This method waits for the CONTACTS event and handles NEXT_CONTACT events
                contacts_result = await meshcore.commands.get_contacts(timeout=15.0)
                
                if contacts_result and contacts_result.type == EventType.CONTACTS:
                    # Contacts received via event - use the payload
                    contacts = contacts_result.payload
                    self.log(f"✓ Received {len(contacts)} contact(s) via CONTACTS event")
                elif contacts_result and contacts_result.type == EventType.ERROR:
                    self.log(f"✗ Error getting contacts: {contacts_result.payload}")
                    contacts = {}
                else:
                    # Fallback: check if contacts were populated via event subscription
                    # (the _update_contacts handler may have already populated meshcore.contacts)
                    contacts = meshcore.contacts
                    if contacts:
                        self.log(f"✓ Found {len(contacts)} contact(s) from cached contacts")
                    else:
                        self.log("⚠ No contacts received - device may not have any contacts")
                        contacts = {}
                
                # Build list for dropdown: "Name (public_key)"
                contact_list = []
                contact_dict = {}  # Map display name to public_key
                
                for public_key, contact_info in contacts.items():
                    # Handle both dict format and direct access
                    if isinstance(contact_info, dict):
                        name = contact_info.get('adv_name', contact_info.get('name', 'Unknown'))
                    else:
                        name = getattr(contact_info, 'adv_name', getattr(contact_info, 'name', 'Unknown'))
                    
                    if not name or name.strip() == '':
                        name = f"Device {public_key[:8]}"
                    display_name = f"{name} ({public_key})"
                    contact_list.append(display_name)
                    contact_dict[display_name] = public_key
                
                # Cache contacts for this BLE device (use normalized address for consistent caching)
                self.ota_contacts_cache[normalized_address] = (contact_list.copy(), contact_dict.copy())
                self.log(f"✓ Cached contacts for {normalized_address}")
                
                # Update UI in main thread
                self.root.after(0, lambda: self._populate_contacts_dropdown(contact_list, contact_dict))
                
                if contact_list:
                    self.log(f"✓ Contacts loaded successfully: {len(contact_list)} contact(s) available")
                else:
                    self.log("⚠ No contacts found on device")
                
                # Always keep the connection active — only manual disconnect closes it
                self.ota_meshcore = meshcore
                self.log("✓ BLE connection kept active (disconnect manually when done)")
                self._update_ble_status(True, original_address or "Connected")
            
            future = asyncio.run_coroutine_threadsafe(load_contacts(), self.ota_event_loop)
            future.result()  # block this thread until the coroutine completes

            self.root.after(0, lambda: self._stop_spinner(self.ota_contacts_spinner_var, '_ota_contacts_spin_active'))
            self.root.after(0, lambda: self.ota_progress_var.set("Ready"))
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self._stop_spinner(self.ota_contacts_spinner_var, '_ota_contacts_spin_active'))
            # Only show error if contacts weren't successfully loaded
            # (Sometimes connection errors occur but contacts still load via existing connection)
            if not hasattr(self, 'ota_contacts_dict') or not self.ota_contacts_dict:
                self.log(f"✗ Error loading contacts: {error_msg}")
                self.root.after(0, lambda: self.ota_progress_var.set("Load failed"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to load contacts:\n{error_msg}"))
            else:
                # Contacts were loaded despite the error, just log a warning
                self.log(f"⚠ Warning during contact loading (but contacts were loaded): {error_msg}")
                self.root.after(0, lambda: self.ota_progress_var.set("Ready"))
    
    def _populate_contacts_dropdown(self, contact_list, contact_dict):
        """Update the contacts dropdown in the UI thread"""
        # Store full unfiltered lists
        self.ota_all_contacts_list = contact_list.copy()
        self.ota_all_contacts_dict = contact_dict.copy()
        self.ota_contacts_dict = contact_dict  # Store mapping for later use
        
        if contact_list:
            self.log(f"✓ {len(contact_list)} contact(s) available in dropdown")
            
            # Auto-select last target device if it's in the contacts (check full list, not filtered)
            if self.last_target_device:
                # Try to find the target device in the full contact list
                for contact_display in contact_list:
                    # Check if the last_target_device matches the public key in the display name
                    if self.last_target_device in contact_display:
                        self.ota_target_device_var.set(contact_display)
                        self.log(f"✓ Auto-selected last target device: {contact_display}")
                        break
                    # Also check if it matches the public key in the dict
                    if contact_display in contact_dict and contact_dict[contact_display] == self.last_target_device:
                        self.ota_target_device_var.set(contact_display)
                        self.log(f"✓ Auto-selected last target device: {contact_display}")
                        break
            
            # Apply current search filter if any (after auto-selection)
            self._apply_search_filter()
        else:
            self.log("⚠ No contacts to display")
    
    def _on_search_target_device(self, event=None):
        """Handle search input for filtering target device dropdown"""
        self._apply_search_filter()
    
    def _apply_search_filter(self):
        """Apply search filter to the contacts dropdown and auto-select closest match"""
        if not hasattr(self, 'ota_all_contacts_list') or not self.ota_all_contacts_list:
            return
        
        search_term = self.ota_target_search_var.get().strip().lower()
        current_selection = self.ota_target_device_var.get()
        
        if not search_term:
            # No filter - show all contacts
            filtered_list = self.ota_all_contacts_list.copy()
            # Don't auto-select when search is cleared
        else:
            # Filter contacts by search term (name or public key)
            filtered_list = []
            for contact_display in self.ota_all_contacts_list:
                if search_term in contact_display.lower():
                    filtered_list.append(contact_display)
            
            # Auto-select the closest match
            if filtered_list:
                # Find the best match (exact start match > contains match)
                best_match = None
                for contact in filtered_list:
                    contact_lower = contact.lower()
                    # Prefer matches that start with the search term
                    if contact_lower.startswith(search_term):
                        best_match = contact
                        break
                
                # If no start match, use the first filtered result
                if not best_match:
                    best_match = filtered_list[0]
                
                # Auto-select the best match
                self.ota_target_device_var.set(best_match)
            else:
                # No matches found, clear selection
                if current_selection:
                    self.ota_target_device_var.set("")
        
        # Update dropdown with filtered list
        self.ota_target_device_combo['values'] = filtered_list
        
        # If current selection is not in filtered list and we're not auto-selecting, clear it
        if current_selection and current_selection not in filtered_list:
            # Only clear if there's an active search filter and we didn't just set a new value
            if search_term and self.ota_target_device_var.get() != current_selection:
                # Already handled by auto-select above
                pass
    
    def get_current_wifi_connection(self):
        """Get the current WiFi connection name/SSID and check for multiple connections"""
        try:
            wifi_connections = []
            
            if sys.platform == "linux":
                # Use nmcli to get current connection
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "NAME,DEVICE,TYPE", "connection", "show", "--active"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if '802-11-wireless' in line or 'wifi' in line.lower():
                            parts = line.split(':')
                            if len(parts) >= 1:
                                wifi_connections.append(parts[0])  # Store connection name
            elif sys.platform == "darwin":  # macOS
                result = subprocess.run(
                    ["networksetup", "-getairportnetwork", "en0"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and "Current Wi-Fi Network:" in result.stdout:
                    ssid = result.stdout.split("Current Wi-Fi Network:")[1].strip()
                    if ssid:
                        wifi_connections.append(ssid)
            elif sys.platform == "win32":  # Windows
                result = subprocess.run(
                    ["netsh", "wlan", "show", "interfaces"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'SSID' in line and 'BSSID' not in line:
                            ssid = line.split(':')[1].strip() if ':' in line else None
                            if ssid and ssid not in wifi_connections:
                                wifi_connections.append(ssid)
            
            # Check for multiple WiFi connections
            if len(wifi_connections) > 1:
                self.log("\n" + "="*60)
                self.log("⚠ WARNING: Multiple WiFi connections detected!")
                self.log("="*60)
                self.log(f"Found {len(wifi_connections)} active WiFi connection(s):")
                for i, conn in enumerate(wifi_connections, 1):
                    self.log(f"  {i}. {conn}")
                self.log("")
                self.log("Having multiple WiFi connections can cause issues during OTA updates.")
                self.log("The app may not know which connection to restore after OTA completes.")
                self.log("")
                self.log("HOW TO FIX:")
                if sys.platform == "linux":
                    self.log("1. Open NetworkManager settings (GUI) or use command line:")
                    self.log("2. List connections: nmcli connection show")
                    self.log("3. Disconnect extra WiFi: nmcli connection down <connection-name>")
                    self.log("4. Keep only ONE WiFi connection active")
                    self.log("5. Example: nmcli connection down 'Wi-Fi connection 2'")
                elif sys.platform == "darwin":
                    self.log("1. Open System Settings (or System Preferences)")
                    self.log("2. Go to Network settings")
                    self.log("3. Select each WiFi interface and click 'Disconnect'")
                    self.log("4. Keep only ONE WiFi connection active")
                    self.log("5. Or use: networksetup -setairportpower <interface> off")
                elif sys.platform == "win32":
                    self.log("1. Open Settings > Network & Internet > Wi-Fi")
                    self.log("2. Click 'Manage known networks'")
                    self.log("3. Disconnect from additional WiFi networks")
                    self.log("4. Keep only ONE WiFi connection active")
                    self.log("5. Or use: netsh wlan disconnect")
                self.log("")
                self.log("After fixing, restart the OTA update process.")
                self.log("The app will use the first connection found for reconnection.")
                self.log("="*60)
                
                # Show warning dialog with platform-specific instructions
                warning_msg = (
                    f"WARNING: {len(wifi_connections)} active WiFi connections detected:\n\n" +
                    "\n".join([f"• {conn}" for conn in wifi_connections]) +
                    "\n\nHaving multiple WiFi connections can cause issues during OTA updates.\n"
                    "The app may not know which connection to restore after OTA completes.\n\n"
                    "HOW TO FIX:\n"
                )
                
                if sys.platform == "linux":
                    warning_msg += (
                        "1. Open NetworkManager settings (GUI) or use command line\n"
                        "2. List connections: nmcli connection show\n"
                        "3. Disconnect extra WiFi: nmcli connection down <connection-name>\n"
                        "4. Keep only ONE WiFi connection active\n"
                        "5. Example: nmcli connection down 'Wi-Fi connection 2'\n"
                    )
                elif sys.platform == "darwin":
                    warning_msg += (
                        "1. Open System Settings (or System Preferences)\n"
                        "2. Go to Network settings\n"
                        "3. Select each WiFi interface and click 'Disconnect'\n"
                        "4. Keep only ONE WiFi connection active\n"
                        "5. Or use: networksetup -setairportpower <interface> off\n"
                    )
                elif sys.platform == "win32":
                    warning_msg += (
                        "1. Open Settings > Network & Internet > Wi-Fi\n"
                        "2. Click 'Manage known networks'\n"
                        "3. Disconnect from additional WiFi networks\n"
                        "4. Keep only ONE WiFi connection active\n"
                        "5. Or use: netsh wlan disconnect\n"
                    )
                
                warning_msg += "\nAfter fixing, restart the OTA update process."
                
                # Show warning dialog (capture warning_msg in lambda)
                msg = warning_msg  # Capture for lambda
                self.root.after(0, lambda m=msg: messagebox.showwarning(
                    "Multiple WiFi Connections Detected",
                    m
                ))
            
            # Return the first connection (or None)
            return wifi_connections[0] if wifi_connections else None
            
        except Exception as e:
            self.log(f"⚠ Could not get current WiFi connection: {str(e)}")
        return None
    
    def scan_and_connect_ota_wifi(self):
        """Scan for MeshCore-OTA WiFi and connect to it"""
        try:
            self.log("Scanning for MeshCore-OTA WiFi network...")
            
            if sys.platform == "linux":
                # Scan for networks
                result = subprocess.run(
                    ["nmcli", "device", "wifi", "rescan"],
                    capture_output=True, text=True, timeout=10
                )
                time.sleep(2)  # Wait for scan to complete
                
                # List available networks
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "SSID,SIGNAL", "device", "wifi", "list"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if 'MeshCore-OTA' in line:
                            self.log("✓ Found MeshCore-OTA network")
                            # Connect to MeshCore-OTA (no password needed for hotspot)
                            connect_result = subprocess.run(
                                ["nmcli", "device", "wifi", "connect", "MeshCore-OTA"],
                                capture_output=True, text=True, timeout=30
                            )
                            if connect_result.returncode == 0:
                                self.log("✓ Connected to MeshCore-OTA WiFi")
                                self.ota_wifi_connected = True
                                self._update_wifi_status(True)
                                return True
                            else:
                                self.log(f"✗ Failed to connect: {connect_result.stderr}")
                                return False
                    self.log("✗ MeshCore-OTA network not found in scan")
                    return False
                    
            elif sys.platform == "darwin":  # macOS
                # Scan and connect
                result = subprocess.run(
                    ["networksetup", "-setairportnetwork", "en0", "MeshCore-OTA"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    self.log("✓ Connected to MeshCore-OTA WiFi")
                    self.ota_wifi_connected = True
                    self._update_wifi_status(True)
                    return True
                else:
                    self.log(f"✗ Failed to connect: {result.stderr}")
                    return False
                    
            elif sys.platform == "win32":  # Windows
                # Connect to MeshCore-OTA
                result = subprocess.run(
                    ["netsh", "wlan", "connect", "name=MeshCore-OTA"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    self.log("✓ Connected to MeshCore-OTA WiFi")
                    self.ota_wifi_connected = True
                    self._update_wifi_status(True)
                    return True
                else:
                    self.log(f"✗ Failed to connect: {result.stderr}")
                    return False
                    
        except subprocess.TimeoutExpired:
            self.log("✗ WiFi connection timeout")
            return False
        except Exception as e:
            self.log(f"✗ Failed to connect to MeshCore-OTA WiFi: {str(e)}")
            return False
        return False
    
    def disconnect_ota_wifi(self):
        """Disconnect from MeshCore-OTA WiFi"""
        try:
            if sys.platform == "linux":
                result = subprocess.run(
                    ["nmcli", "device", "disconnect", "wlan0"],
                    capture_output=True, text=True, timeout=10
                )
                # Try wlp* interface names too
                if result.returncode != 0:
                    result = subprocess.run(
                        ["nmcli", "device", "disconnect", "wifi"],
                        capture_output=True, text=True, timeout=10
                    )
            elif sys.platform == "darwin":  # macOS
                result = subprocess.run(
                    ["networksetup", "-setairportpower", "en0", "off"],
                    capture_output=True, text=True, timeout=5
                )
                time.sleep(1)
                subprocess.run(
                    ["networksetup", "-setairportpower", "en0", "on"],
                    capture_output=True, text=True, timeout=5
                )
            elif sys.platform == "win32":  # Windows
                result = subprocess.run(
                    ["netsh", "wlan", "disconnect"],
                    capture_output=True, text=True, timeout=10
                )
            
            self.ota_wifi_connected = False
            self._update_wifi_status(False)
            self.log("✓ Disconnected from MeshCore-OTA WiFi")
            return True
        except Exception as e:
            self.log(f"⚠ Could not disconnect from MeshCore-OTA: {str(e)}")
            return False
    
    def reconnect_previous_wifi(self):
        """Reconnect to the previous WiFi connection"""
        if not self.previous_wifi_connection:
            self.log("⚠ No previous WiFi connection stored")
            return False
        
        try:
            self.log(f"Reconnecting to previous WiFi: {self.previous_wifi_connection}")
            
            if sys.platform == "linux":
                result = subprocess.run(
                    ["nmcli", "connection", "up", self.previous_wifi_connection],
                    capture_output=True, text=True, timeout=30
                )
            elif sys.platform == "darwin":  # macOS
                result = subprocess.run(
                    ["networksetup", "-setairportnetwork", "en0", self.previous_wifi_connection],
                    capture_output=True, text=True, timeout=30
                )
            elif sys.platform == "win32":  # Windows
                result = subprocess.run(
                    ["netsh", "wlan", "connect", f"name={self.previous_wifi_connection}"],
                    capture_output=True, text=True, timeout=30
                )
            
            if result.returncode == 0:
                self.log(f"✓ Reconnected to {self.previous_wifi_connection}")
                return True
            else:
                self.log(f"⚠ Could not reconnect to {self.previous_wifi_connection}")
                return False
        except Exception as e:
            self.log(f"✗ Failed to reconnect to previous WiFi: {str(e)}")
            return False
    
    def monitor_ota_completion(self, max_wait_time=300):
        """Monitor OTA completion by checking if device is still in OTA mode"""
        # Poll the OTA URL to see if device is still responding.
        # Only declare completion if we first got at least one successful response,
        # then subsequently lost contact — this prevents premature exit when the
        # device hasn't started serving the OTA page yet.
        import urllib.request
        start_time = time.time()
        last_response_time = None  # None until we get the first successful response
        got_first_response = False

        while time.time() - start_time < max_wait_time:
            try:
                req = urllib.request.Request(self.ota_upload_url, method='HEAD')
                try:
                    urllib.request.urlopen(req, timeout=5)  # timeout must be on urlopen
                    last_response_time = time.time()
                    got_first_response = True
                    self.log("  Device still in OTA mode...")
                except:
                    # Only consider OTA complete if we previously had a response and
                    # it's been more than 10 seconds since the last one.
                    if got_first_response and time.time() - last_response_time > 10:
                        self.log("  Device appears to have completed OTA (no longer responding)")
                        return True
            except Exception:
                pass

            time.sleep(10)  # Wait 10 seconds before retesting WiFi

        self.log("  OTA monitoring timeout - assuming complete")
        return True
    
    def _toggle_section(self, section_name):
        """Toggle expand/collapse of help sections"""
        if section_name == 'roles':
            self.roles_expanded = not self.roles_expanded
            if self.roles_expanded:
                self.roles_content_frame.grid()
                self.roles_toggle_btn.config(text="▼ Device Roles (Click to collapse)")
            else:
                self.roles_content_frame.grid_remove()
                self.roles_toggle_btn.config(text="▶ Device Roles (Click to expand)")
        elif section_name == 'steps':
            self.steps_expanded = not self.steps_expanded
            if self.steps_expanded:
                self.steps_content_frame.grid()
                self.steps_toggle_btn.config(text="▼ Steps (Click to collapse)")
            else:
                self.steps_content_frame.grid_remove()
                self.steps_toggle_btn.config(text="▶ Steps (Click to expand)")
    
    def _on_target_device_selected(self, event=None):
        """Callback when user selects a target device from the dropdown"""
        selected_value = self.ota_target_device_var.get().strip()
        
        if not selected_value:
            self.last_target_device = None
            self.save_ota_device_settings()
            return
        
        # Extract public key from selection and save it
        if selected_value in self.ota_contacts_dict:
            self.last_target_device = self.ota_contacts_dict[selected_value]
        else:
            # Try to extract from "Name (public_key)" format
            import re
            match = re.search(r'\(([^)]+)\)', selected_value)
            if match:
                self.last_target_device = match.group(1).strip()
            else:
                self.last_target_device = selected_value
        
        self.save_ota_device_settings()
        self.log(f"Target device selected: {selected_value} (saved)")
    
    def _restore_last_devices(self):
        """Restore last BLE device and target device from saved settings"""
        if not self.last_ble_device:
            return
        
        # Try to find the device in scanned devices or scan for it
        found_device = None
        for display_name, (name, address) in self.ota_scanned_devices.items():
            if address == self.last_ble_device or name == self.last_ble_device:
                found_device = display_name
                break
        
        if found_device:
            # Device found in already scanned devices
            self.ota_ble_device_var.set(found_device)
            self.log(f"✓ Restored last BLE device: {found_device}")
            # Auto-connect and load contacts
            self._auto_connect_and_load_contacts()
        else:
            # Device not in scanned list, try to scan for it
            self.log(f"Last BLE device ({self.last_ble_device}) not in scanned list, scanning...")
            self.scan_ble_devices()
            # After scan completes, try to restore
            self.root.after(6000, self._restore_last_devices)  # Wait for scan to complete
    
    def _auto_connect_and_load_contacts(self):
        """Auto-connect to BLE device and load contacts if device is available"""
        # Don't start another BLE operation if one is already running
        if self._ota_contacts_spin_active:
            return

        selected_value = self.ota_ble_device_var.get().strip()

        if not selected_value or selected_value == "Auto-scan":
            return

        # Check if device is in scanned devices
        if selected_value not in self.ota_scanned_devices:
            return
        
        # Auto-load contacts
        self.log("Auto-connecting and loading contacts...")
        self.load_contacts_from_device()
    
    def load_ota_upload_page(self):
        """Load the OTA upload page in external browser (ElegantOTA requires JavaScript)"""
        url = self.ota_upload_url
        
        # Always use external browser for OTA uploads because ElegantOTA requires JavaScript
        # and tkinterweb's embedded browser doesn't support JavaScript
        self.log(f"Opening OTA upload page in external browser (JavaScript required for ElegantOTA): {url}")
        self.open_ota_upload_page_external()
        
        # If embedded browser frame exists, show a helpful message instead of trying to load the page
        if self.use_embedded_browser and self.ota_webview_frame:
            # Clear any existing webview
            if hasattr(self, 'ota_webview') and self.ota_webview:
                try:
                    self.ota_webview.destroy()
                    self.ota_webview = None
                except:
                    pass
            
            # Show informational message in the embedded browser frame
            try:
                # Remove any existing widgets in the frame
                for widget in self.ota_webview_frame.winfo_children():
                    widget.destroy()
                
                info_label = ttk.Label(self.ota_webview_frame,
                                       text="OTA Upload Page\n\n"
                                            "The upload page has been opened in your external browser.\n\n"
                                            "ElegantOTA requires JavaScript support, which is only\n"
                                            "available in external browsers (not in embedded view).\n\n"
                                            "Please use the external browser window to upload your\n"
                                            "firmware file (.bin).",
                                       font=('Arial', 10), justify=tk.CENTER, 
                                       foreground='darkblue', wraplength=600)
                info_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=20, pady=20)
            except Exception as e:
                self.log(f"⚠ Could not update embedded browser frame: {str(e)}")
    
    def open_ota_upload_page(self):
        """Open the OTA upload page (alias for compatibility)"""
        self.load_ota_upload_page()
    
    def open_ota_upload_page_external(self):
        """Open the OTA upload page in the default web browser"""
        try:
            url = self.ota_upload_url
            self.log(f"Opening OTA upload page in external browser: {url}")
            webbrowser.open(url)
            self.log("✓ External browser opened")
        except Exception as e:
            self.log(f"✗ Failed to open browser: {str(e)}")
            messagebox.showerror("Error", f"Failed to open browser:\n{str(e)}")
    
    def start_ota_update_workflow(self):
        """Start the complete OTA update workflow"""
        # Check if target device is selected
        target_device = self.ota_target_device_var.get().strip()
        if not target_device:
            messagebox.showwarning("No Target Device", "Please select a target device from the contact list first.")
            return
        
        # Confirm OTA update
        response = messagebox.askyesno(
            "Confirm OTA Update",
            "This will:\n"
            "1. Connect to local BLE device (gateway)\n"
            "2. Send 'start ota' command to target device via mesh\n"
            "3. Target device will create WiFi hotspot: MeshCore-OTA\n"
            "4. App will auto-connect to MeshCore-OTA WiFi\n"
            "5. Browser will open - upload your .bin file\n"
            "6. WiFi will reconnect automatically after update\n\n"
            "Continue?",
            icon='warning'
        )
        
        if not response:
            return
        
        self.ota_update_btn.config(state='disabled')
        self.ota_progress_var.set("Starting OTA workflow...")
        self.ota_progress_bar.start()
        
        # Run OTA workflow in background thread
        thread = threading.Thread(target=self._ota_workflow_thread, daemon=True)
        thread.start()
    
    def _ota_workflow_thread(self):
        """Background thread for complete OTA workflow"""
        import asyncio
        from meshcore import MeshCore
        from meshcore.ble_cx import BLEConnection
        
        try:
            # Submit to the shared persistent event loop so ota_meshcore (created
            # during Load Contacts in the same loop) can be safely reused.
            future = asyncio.run_coroutine_threadsafe(
                self._ota_workflow_async(), self.ota_event_loop
            )
            future.result()  # block this thread until the workflow completes

        except Exception as e:
            self.log(f"\n✗ OTA workflow error: {str(e)}")
            self.root.after(0, lambda: self.ota_progress_var.set(f"Error: {str(e)}"))
            self.root.after(0, lambda: self.ota_progress_bar.stop())
            self.root.after(0, lambda: self.ota_update_btn.config(state='normal'))
            messagebox.showerror("OTA Error", f"OTA workflow failed:\n{str(e)}")
    
    async def _ota_workflow_async(self):
        """Async OTA workflow: Save WiFi -> Connect BLE -> Send start ota -> Connect to MeshCore-OTA -> Monitor -> Reconnect WiFi"""
        from meshcore import MeshCore
        from meshcore.ble_cx import BLEConnection
        from meshcore.events import EventType
        
        # Step 0: Save current WiFi connection
        self.root.after(0, lambda: self.ota_progress_var.set("Saving current WiFi connection..."))
        self.log("\n[0/4] Saving current WiFi connection...")
        self.previous_wifi_connection = self.get_current_wifi_connection()
        if self.previous_wifi_connection:
            self.log(f"✓ Current WiFi connection saved: {self.previous_wifi_connection}")
        else:
            self.log("⚠ No active WiFi connection found (will skip reconnection)")
        
        # Get device identifier from combobox
        selected_value = self.ota_ble_device_var.get().strip()
        
        # Determine which value to use
        if selected_value and selected_value != "Auto-scan" and selected_value in self.ota_scanned_devices:
            # User selected from combobox - use the MAC address (more reliable than name)
            name, address = self.ota_scanned_devices[selected_value]
            ble_address = address  # Use MAC address for connection (more reliable)
        elif selected_value and selected_value != "Auto-scan":
            # Fallback (shouldn't happen with readonly, but handle it)
            ble_address = selected_value
        else:
            ble_address = None  # Will use auto-scan
        
        self.log("\n" + "="*60)
        self.log("STARTING OTA WORKFLOW")
        self.log("="*60)
        self.log(f"BLE Device: {ble_address or 'Auto-scan'}")
        self.log("OTA Method: Device creates MeshCore-OTA WiFi hotspot")
        self.log("="*60)
        
        meshcore = None
        target_device_id = None  # Store target device ID
        workflow_owns_connection = False  # True only if this workflow created the BLE connection

        try:
            # Step 1: Reuse existing BLE connection if available, otherwise connect fresh
            self.log("\n[1/4] Checking BLE connection...")
            existing_mc = self.ota_meshcore
            if existing_mc is not None:
                try:
                    is_live = (hasattr(existing_mc, 'connection_manager') and
                               existing_mc.connection_manager.is_connected)
                except Exception:
                    is_live = False
                if is_live:
                    meshcore = existing_mc
                    self.log("✓ Reusing existing BLE connection (from Load Contacts)")
                    self.root.after(0, lambda: self.ota_progress_var.set("BLE already connected"))
                else:
                    self.log("⚠ Existing connection stale — will reconnect...")
                    try:
                        await existing_mc.disconnect()
                    except Exception:
                        pass
                    self.ota_meshcore = None
                    self._update_ble_status(False)

            if meshcore is None:
                workflow_owns_connection = True
                self.root.after(0, lambda: self.ota_progress_var.set("Connecting via BLE..."))
                self.log(f"  Device address: {ble_address or 'Auto-scan'}")
                try:
                    ble_conn = BLEConnection(address=ble_address)
                    meshcore = MeshCore(ble_conn, debug=False)
                    self.log("  Attempting connection...")
                    await meshcore.connect()
                    self.log("✓ BLE connected")
                    self.ota_meshcore = meshcore
                    self._update_ble_status(True, ble_address or "")
                except Exception as e:
                    error_msg = str(e)
                    self.log(f"✗ BLE connection failed: {error_msg}")
                    # Try with None (auto-scan) if address format might be wrong
                    if ble_address and ":" not in ble_address:
                        self.log("  Retrying with auto-scan (device name provided)...")
                        try:
                            ble_conn = BLEConnection(address=None)  # Auto-scan
                            meshcore = MeshCore(ble_conn, debug=False)
                            await meshcore.connect()
                            self.log("✓ BLE connected via auto-scan")
                            self.ota_meshcore = meshcore
                            self._update_ble_status(True, "auto-scan")
                        except Exception as e2:
                            raise Exception(f"BLE connection failed with address and auto-scan: {error_msg}, {str(e2)}")
                    else:
                        raise
            
            # Get target device ID (device to update) - REQUIRED since we can't connect directly
            target_device_selection = self.ota_target_device_var.get().strip()
            if not target_device_selection:
                raise Exception("Target Device is required! Please select a device from the contact list.")
            
            # Extract public key from dropdown selection
            # Format is "Name (public_key)" or we can use the contacts dict
            target_device_id = None
            if hasattr(self, 'ota_contacts_dict') and self.ota_contacts_dict:
                # Try to get from dictionary first
                target_device_id = self.ota_contacts_dict.get(target_device_selection)
            
            # If not in dict, try to extract from string format "Name (public_key)"
            if not target_device_id:
                import re
                # Extract text between parentheses
                match = re.search(r'\(([^)]+)\)', target_device_selection)
                if match:
                    target_device_id = match.group(1).strip()
                else:
                    # If no parentheses, assume the whole string is the public key
                    target_device_id = target_device_selection
            
            if not target_device_id:
                raise Exception("Could not extract device public key. Please select a device from the contact list.")
            
            self.log(f"Target device (remote): {target_device_id[:12]}...")
            self.log("All commands will be sent via mesh network through local gateway device")
            
            # Step 2a: Login to target device if admin password is provided
            admin_password = self.ota_admin_password_var.get().strip()
            if admin_password:
                self.root.after(0, lambda: self.ota_progress_var.set("Logging in to target device..."))
                self.log("\n[2a/4] Logging in to target device...")
                self.log("Sending login request with admin password...")
                
                original_timeout = meshcore.commands.default_timeout
                meshcore.commands.default_timeout = 15.0  # Use longer timeout for login
                try:
                    login_result = await meshcore.commands.send_login(target_device_id, admin_password)
                    
                    if login_result.type == EventType.LOGIN_SUCCESS:
                        self.log("✓ Login successful - authenticated to target device")
                    elif login_result.type == EventType.LOGIN_FAILED:
                        self.log("✗ Login failed - incorrect password or authentication error")
                        raise Exception("Login failed: Incorrect admin password or device authentication error")
                    elif login_result.type == EventType.ERROR:
                        error_reason = login_result.payload.get("reason", "")
                        self.log(f"⚠ Login error: {error_reason}")
                        # Some devices may not require login, continue anyway
                        self.log("  Continuing - device may not require authentication")
                    elif login_result.type == EventType.MSG_SENT:
                        # Login command sent, wait for LOGIN_SUCCESS or LOGIN_FAILED event
                        self.log("  Login request sent, waiting for authentication response...")
                        try:
                            login_response = await asyncio.wait_for(
                                meshcore.dispatcher.wait_for_event(
                                    [EventType.LOGIN_SUCCESS, EventType.LOGIN_FAILED],
                                    timeout=10.0
                                ),
                                timeout=10.0
                            )
                            if login_response and login_response.type == EventType.LOGIN_SUCCESS:
                                self.log("✓ Login successful - authenticated to target device")
                            elif login_response and login_response.type == EventType.LOGIN_FAILED:
                                self.log("✗ Login failed - incorrect password")
                                raise Exception("Login failed: Incorrect admin password")
                            else:
                                self.log("⚠ Login response timeout - continuing anyway")
                        except asyncio.TimeoutError:
                            self.log("⚠ Login response timeout - device may not require authentication")
                            self.log("  Continuing with OTA command...")
                    else:
                        self.log(f"⚠ Unexpected login response: {login_result.type}")
                        self.log("  Continuing with OTA command...")
                finally:
                    meshcore.commands.default_timeout = original_timeout
            else:
                self.log("\n[2a/4] Skipping login (no admin password provided)")
                self.log("  Note: Some devices may require authentication - add password if commands fail")
            
            # Step 2b: Trigger OTA update using "start ota" command
            # Per official guide: https://github.com/Mraanderson/meshcore-ota
            self.root.after(0, lambda: self.ota_progress_var.set("Triggering OTA update..."))
            self.log("\n[2b/4] Triggering OTA update...")
            self.log("Sending 'start ota' command to target device...")
            self.log("Device will create WiFi hotspot: MeshCore-OTA")
            
            # Send "start ota" command to target device via CLI console using repeater management
            # The command is sent through the mesh network via the gateway device's CLI console
            # Format: "start ota" - this is the CLI console command format per official guide
            ota_cmd = "start ota"
            self.log(f"Sending CLI console command via repeater management: {ota_cmd}")
            self.log("  (Command sent through mesh network via gateway device's CLI console)")
            
            # Use longer timeout directly (mesh commands need more time for MSG_SENT confirmation)
            # Skip the initial shorter timeout attempt and use the longer timeout from the start
            original_timeout = meshcore.commands.default_timeout
            meshcore.commands.default_timeout = 15.0  # Use longer timeout directly (15 seconds)
            try:
                ota_result = await meshcore.commands.send_cmd(target_device_id, ota_cmd)
            finally:
                meshcore.commands.default_timeout = original_timeout  # Restore original timeout
            
            if ota_result.type == EventType.ERROR:
                error_reason = ota_result.payload.get("reason", "")
                self.log(f"⚠ Could not send OTA command via mesh: {ota_result.payload}")
                self.log("  Continuing anyway - device may still process the command")
            
            if ota_result.type == EventType.MSG_SENT:
                self.log("✓ 'start ota' command sent to mesh network (MSG_SENT received)")
                
                # Wait for ACK from remote device
                exp_ack = ota_result.payload.get("expected_ack")
                suggested_timeout = ota_result.payload.get("suggested_timeout", 10000) / 1000.0  # Convert ms to seconds
                
                if exp_ack:
                    # Convert to hex string if bytes
                    ack_code = exp_ack.hex() if isinstance(exp_ack, bytes) else exp_ack
                    wait_timeout = max(suggested_timeout * 1.5, 15.0)  # Add 50% buffer, minimum 15s
                    
                    self.log(f"Waiting for ACK from remote device (timeout: {wait_timeout:.1f}s)...")
                    try:
                        ack_result = await meshcore.dispatcher.wait_for_event(
                            EventType.ACK,
                            attribute_filters={"code": ack_code},
                            timeout=wait_timeout
                        )
                        
                        if ack_result:
                            self.log("✓ OTA command acknowledged by remote device")
                        else:
                            self.log("⚠ No ACK received from remote device (command may still be processed)")
                    except Exception as e:
                        self.log(f"⚠ Error waiting for ACK: {str(e)}")
                        self.log("  Command may still be processed by remote device")
                else:
                    self.log("⚠ No expected_ack in response, cannot wait for ACK")
            else:
                self.log("✓ 'start ota' command sent to target device via CLI console/repeater management")
            
            # Keep BLE connection active - we'll need it for firmware version verification at the end
            # Store meshcore instance for later use
            self.ota_meshcore = meshcore
            self.log("\n✓ OTA mode initiated on target device")
            self.log("✓ BLE connection kept active for firmware verification at end of workflow")
            
            # Step 3: Connect to MeshCore-OTA WiFi
            self.root.after(0, lambda: self.ota_progress_var.set("Connecting to MeshCore-OTA WiFi..."))
            self.log("\n[3/4] Connecting to MeshCore-OTA WiFi...")
            self.log("Waiting 10 seconds for device to create hotspot...")
            await asyncio.sleep(10)  # Give device time to create hotspot
            
            # Try to connect to MeshCore-OTA WiFi
            max_attempts = 3
            connected = False
            for attempt in range(max_attempts):
                self.log(f"  Attempt {attempt + 1}/{max_attempts} to connect to MeshCore-OTA...")
                if self.scan_and_connect_ota_wifi():
                    connected = True
                    # WiFi will remain connected until user confirms completion
                    # No auto-disconnect timer - user controls when to disconnect
                    self.log("✓ Connected to MeshCore-OTA WiFi")
                    self.log("  WiFi will remain connected until you confirm OTA completion")
                    break
                if attempt < max_attempts - 1:
                    self.log("  Waiting 5 seconds before retry...")
                    await asyncio.sleep(5)
            
            if not connected:
                # WiFi connection failed - abort OTA workflow
                self.log("\n" + "="*60)
                self.log("✗ OTA WORKFLOW ABORTED")
                self.log("="*60)
                self.log("⚠ Could not connect to MeshCore-OTA WiFi hotspot")
                self.log("")
                self.log("Possible reasons:")
                self.log("  • Device did not create the WiFi hotspot")
                self.log("  • Device is still rebooting/processing")
                self.log("  • WiFi hotspot name is different than expected")
                self.log("  • Network manager issues")
                self.log("")
                self.log("Please check:")
                self.log("  • Device is powered on and in range")
                self.log("  • Device has received the 'start ota' command")
                self.log("  • Try manually connecting to MeshCore-OTA WiFi")
                self.log("="*60)
                
                # Reconnect to previous WiFi if we disconnected from it
                if self.previous_wifi_connection:
                    self.log("\nReconnecting to previous WiFi connection...")
                    self.reconnect_previous_wifi()
                
                # Update progress and show error
                self.root.after(0, lambda: self.ota_progress_var.set("OTA workflow aborted - WiFi connection failed"))
                self.root.after(0, lambda: messagebox.showerror(
                    "OTA Workflow Aborted",
                    "Could not connect to MeshCore-OTA WiFi hotspot.\n\n"
                    "The OTA workflow has been aborted.\n\n"
                    "Please check:\n"
                    "• Device is powered on and in range\n"
                    "• Device received the 'start ota' command\n"
                    "• Try manually connecting to MeshCore-OTA WiFi\n\n"
                    "Previous WiFi connection will be restored."
                ))
                
                # Disconnect BLE if connected
                if meshcore:
                    try:
                        await meshcore.disconnect()
                        self.log("✓ Disconnected from BLE device")
                    except:
                        pass
                
                # Abort workflow - don't proceed to browser/monitoring
                return
            
            # Step 4: Open browser and monitor OTA
            self.root.after(0, lambda: self.ota_progress_var.set("Opening upload page..."))
            self.log("\n[4/4] Opening OTA upload page...")
            await asyncio.sleep(2)  # Give WiFi connection time to stabilize
            
            # Load browser (embedded or external)
            self.root.after(0, self.load_ota_upload_page)
            self.log("✓ Upload page loaded - please upload your .bin firmware file")

            # Show confirmation dialog immediately in a background thread —
            # don't wait for polling; let the browser stay in the foreground.
            def monitor_thread():
                import threading

                # Give the browser a moment to open before showing the dialog
                time.sleep(2)

                self.log("\n" + "="*60)
                self.log("Upload the firmware in your browser, then confirm here when done.")
                self.log("The dialog is ready — return to the app whenever you are finished.")
                self.log("="*60)

                self.root.after(0, lambda: self.ota_progress_var.set("Upload firmware in browser — confirm here when done"))

                # Use threading events to wait for user confirmation
                first_confirmed = threading.Event()
                first_result = [None]

                def show_first_confirmation():
                    # Keep app window behind the browser
                    self.root.attributes('-topmost', False)
                    self.root.lower()
                    self.root.update_idletasks()
                    result = messagebox.askyesno(
                        "OTA Upload Complete?",
                        "Upload the firmware .bin in your browser, then confirm here.\n\n"
                        "Please verify in the browser that:\n"
                        "• The firmware file was uploaded successfully\n"
                        "• The device has finished processing the update\n"
                        "• The device may have rebooted\n\n"
                        "Did the upload complete successfully?",
                        icon='question',
                        parent=self.root
                    )
                    first_result[0] = result
                    first_confirmed.set()
                    self.root.lower()
                    self.root.attributes('-topmost', False)

                # Loop until the user confirms the upload is complete
                while True:
                    first_confirmed.clear()
                    first_result[0] = None

                    self.root.after(0, show_first_confirmation)
                    first_confirmed.wait(timeout=600)  # 10 minute timeout

                    if first_result[0]:
                        break  # User confirmed — proceed

                    self.log("⚠ User indicated upload is not complete yet - dialog will reappear...")
                    self.root.after(0, lambda: self.ota_progress_var.set("Waiting for OTA upload to complete..."))
                
                # Second confirmation - final confirmation before finishing
                second_confirmed = threading.Event()
                second_result = [None]
                
                def show_second_confirmation():
                    # Don't force window to front - let user return manually
                    self.root.attributes('-topmost', False)
                    # Lower the window to keep it behind browser
                    self.root.lower()
                    # Use update_idletasks to ensure attributes are applied
                    self.root.update_idletasks()
                    
                    # Build message based on checkbox states
                    keep_wifi = self.ota_keep_wifi_connected_var.get() if hasattr(self, 'ota_keep_wifi_connected_var') else False

                    actions = []
                    if not keep_wifi:
                        actions.append("• Disconnect from MeshCore-OTA WiFi")
                        actions.append("• Reconnect to your previous WiFi")
                    else:
                        actions.append("• Keep WiFi connected to MeshCore-OTA (as requested)")
                    actions.append("• Keep BLE connection active (disconnect manually when done)")
                    actions.append("• Mark the workflow as complete")
                    
                    result = messagebox.askyesno(
                        "Final Confirmation",
                        "Final confirmation required:\n\n"
                        "Are you absolutely sure the OTA update is complete?\n\n"
                        "Once confirmed, the workflow will:\n" + "\n".join(actions) + "\n\n"
                        "Proceed with completing the workflow?",
                        icon='question',
                        parent=self.root
                    )
                    second_result[0] = result
                    second_confirmed.set()
                    # Keep window lowered after dialog closes
                    self.root.lower()
                    self.root.attributes('-topmost', False)
                
                self.log("First confirmation received.")
                self.log("A final confirmation dialog is waiting in the application.")
                self.log("Please return to the app window when ready to complete the workflow.")

                # Loop until the user gives final confirmation
                while True:
                    second_confirmed.clear()
                    second_result[0] = None

                    # Update progress to show final dialog is waiting
                    self.root.after(0, lambda: self.ota_progress_var.set("Final confirmation dialog waiting - return to app when ready"))
                    self.root.after(0, show_second_confirmation)

                    # Wait for second confirmation
                    second_confirmed.wait(timeout=600)  # 10 minute timeout

                    if second_result[0]:
                        break  # User confirmed — proceed

                    self.log("⚠ User cancelled final confirmation - asking again...")
                    self.root.after(0, lambda: self.ota_progress_var.set("Waiting for final confirmation..."))
                
                # Both confirmations received - proceed with completion
                self.log("\n✓ Both confirmations received. Completing workflow...")
                
                # After monitoring, reconnect WiFi (unless user wants to keep WiFi connected)
                keep_wifi = self.ota_keep_wifi_connected_var.get() if hasattr(self, 'ota_keep_wifi_connected_var') else False
                if not keep_wifi:
                    self.log("\nReconnecting to previous WiFi connection...")
                    if self.previous_wifi_connection:
                        if self.disconnect_ota_wifi():
                            time.sleep(2)  # Wait before reconnecting
                            self.reconnect_previous_wifi()
                    else:
                        self.disconnect_ota_wifi()
                    # Show completion dialog when WiFi is disconnected/reconnected
                    self.root.after(0, lambda: messagebox.showinfo(
                        "OTA Update Complete",
                        "OTA update workflow completed!\n\n"
                        "✓ WiFi has been reconnected to your previous network.\n\n"
                        "Note: BLE connection will be handled per your checkbox settings."
                    ))
                else:
                    self.log("\n⚠ Keeping WiFi connected to MeshCore-OTA (as requested)")
                    
                    # Verify firmware version after OTA update
                    # Per MeshCore CLI docs: https://github.com/meshcore-dev/meshcore-cli/blob/main/REPEATER_COMMANDS.md
                    # Use "ver" and "board" commands which work in client mode (via mesh network)
                    self.log("\n" + "="*60)
                    self.log("Verifying installed firmware version on target device...")
                    self.log("="*60)
                    self.log("Using 'ver' and 'board' commands per MeshCore CLI documentation")
                    self.root.after(0, lambda: self.ota_progress_var.set("Verifying firmware version..."))
                    
                    # Get target device ID (the repeater that was updated)
                    target_device_selection = self.ota_target_device_var.get().strip()
                    target_device_id = None
                    if hasattr(self, 'ota_contacts_dict') and self.ota_contacts_dict:
                        target_device_id = self.ota_contacts_dict.get(target_device_selection)
                    if not target_device_id:
                        import re
                        match = re.search(r'\(([^)]+)\)', target_device_selection)
                        if match:
                            target_device_id = match.group(1).strip()
                        else:
                            target_device_id = target_device_selection
                    
                    if target_device_id and self.ota_meshcore:
                        try:
                            import asyncio
                            from meshcore.events import EventType
                            
                            async def verify_firmware_version():
                                try:
                                    # Use existing BLE connection (kept active throughout workflow)
                                    meshcore_verify = self.ota_meshcore
                                    self.log("✓ Using existing BLE connection for firmware verification")
                                    
                                    # Check if connection is still active
                                    if not meshcore_verify.connection_manager.is_connected:
                                        self.log("⚠ BLE connection lost, reconnecting...")
                                        # Reconnect if needed
                                        selected_value = self.ota_ble_device_var.get().strip()
                                        if selected_value in self.ota_scanned_devices:
                                            name, ble_address = self.ota_scanned_devices[selected_value]
                                        else:
                                            ble_address = selected_value if selected_value != "Auto-scan" else None
                                        
                                        if ble_address:
                                            from meshcore import MeshCore
                                            from meshcore.ble_cx import BLEConnection
                                            ble_conn = BLEConnection(address=ble_address)
                                            meshcore_verify = MeshCore(ble_conn, debug=False)
                                            await meshcore_verify.connect()
                                            self.log("✓ Reconnected to local device")
                                        else:
                                            raise Exception("Could not reconnect - no BLE address available")
                                    else:
                                        self.log("✓ BLE connection is still active")
                                    
                                    # Wait for connection to stabilize
                                    await asyncio.sleep(2.0)
                                    
                                    # Query TARGET device (repeater) for firmware version using "ver" command
                                    # Per MeshCore CLI docs: "ver" and "board" commands work in client mode (via mesh)
                                    # Reference: https://github.com/meshcore-dev/meshcore-cli/blob/main/REPEATER_COMMANDS.md
                                    self.log(f"Querying target device {target_device_id[:12]}... for firmware version...")
                                    self.log("Sending 'ver' command via mesh network (per MeshCore CLI docs)...")
                                    
                                    # Send "ver" command to target device (repeater) via mesh
                                    ver_result = await asyncio.wait_for(
                                        meshcore_verify.commands.send_cmd(target_device_id, "ver"),
                                        timeout=15.0
                                    )
                                    
                                    fw_version = "Unknown"
                                    board_name = "Unknown"
                                    
                                    # Wait for text response from "ver" command
                                    # Responses come back as CONTACT_MSG_RECV events with text payload
                                    if ver_result and ver_result.type == EventType.MSG_SENT:
                                        self.log("✓ 'ver' command sent successfully, waiting for response...")
                                        try:
                                            # Wait for a message response (text from repeater)
                                            # The response should come as CONTACT_MSG_RECV event
                                            msg_response = await asyncio.wait_for(
                                                meshcore_verify.dispatcher.wait_for_event(
                                                    EventType.CONTACT_MSG_RECV,
                                                    timeout=10.0
                                                ),
                                                timeout=10.0
                                            )
                                            if msg_response and msg_response.payload:
                                                response_text = msg_response.payload.get('text', '').strip()
                                                if response_text:
                                                    fw_version = response_text
                                                    self.log(f"✓ Received version response: {fw_version}")
                                        except asyncio.TimeoutError:
                                            self.log("⚠ Timeout waiting for 'ver' response (device may still be processing)")
                                        except Exception as e:
                                            self.log(f"⚠ Could not parse 'ver' response: {str(e)}")
                                    
                                    # Also get board name using "board" command
                                    try:
                                        self.log("Sending 'board' command via mesh network...")
                                        board_result = await asyncio.wait_for(
                                            meshcore_verify.commands.send_cmd(target_device_id, "board"),
                                            timeout=15.0
                                        )
                                        
                                        if board_result and board_result.type == EventType.MSG_SENT:
                                            self.log("✓ 'board' command sent successfully, waiting for response...")
                                            try:
                                                # Wait for board name response
                                                msg_response = await asyncio.wait_for(
                                                    meshcore_verify.dispatcher.wait_for_event(
                                                        EventType.CONTACT_MSG_RECV,
                                                        timeout=10.0
                                                    ),
                                                    timeout=10.0
                                                )
                                                if msg_response and msg_response.payload:
                                                    response_text = msg_response.payload.get('text', '').strip()
                                                    if response_text:
                                                        board_name = response_text
                                                        self.log(f"✓ Received board response: {board_name}")
                                            except asyncio.TimeoutError:
                                                self.log("⚠ Timeout waiting for 'board' response")
                                            except Exception as e:
                                                self.log(f"⚠ Could not parse 'board' response: {str(e)}")
                                    except Exception as e:
                                        self.log(f"⚠ Could not send 'board' command: {str(e)}")
                                    
                                    # Also try device_query as fallback (queries local device, not target)
                                    try:
                                        self.log("Also querying local device info...")
                                        device_info = await asyncio.wait_for(
                                            meshcore_verify.commands.send_device_query(),
                                            timeout=10.0
                                        )
                                        
                                        if device_info and device_info.type == EventType.DEVICE_INFO:
                                            local_info = device_info.payload
                                            local_ver = local_info.get('ver', 'Unknown')
                                            local_model = local_info.get('model', 'Unknown')
                                            self.log(f"Local device (gateway): Model={local_model}, Version={local_ver}")
                                    except:
                                        pass
                                    
                                    self.log("\n" + "="*60)
                                    self.log("✓ FIRMWARE VERSION VERIFICATION")
                                    self.log("="*60)
                                    self.log(f"Target Device: {target_device_id[:12]}...")
                                    self.log(f"Board: {board_name}")
                                    self.log(f"Firmware Version: {fw_version}")
                                    self.log("="*60)
                                    self.log("\nNote: 'ver' and 'board' commands sent via mesh network.")
                                    self.log("Check device logs or use serial connection for detailed version info.")
                                    
                                    # Show version/completion dialog (keep_wifi=True path)
                                    self.root.after(0, lambda: messagebox.showinfo(
                                        "OTA Update Complete",
                                        f"OTA update workflow completed!\n\n"
                                        f"Target Device: {target_device_id[:12]}...\n"
                                        f"Board: {board_name}\n"
                                        f"Version: {fw_version}\n\n"
                                        f"Note: Version commands sent via mesh network.\n"
                                        f"WiFi kept connected to MeshCore-OTA (as requested)."
                                    ))
                                    
                                    # Don't disconnect here - will disconnect at end of workflow
                                    self.log("✓ Firmware version verified (BLE connection kept active)")
                                    
                                except asyncio.TimeoutError:
                                    self.log("⚠ Timeout waiting for version response (device may still be rebooting)")
                                    self.root.after(0, lambda: messagebox.showinfo(
                                        "OTA Update Complete",
                                        "OTA update workflow completed!\n\n"
                                        "Could not verify firmware version - device may still be rebooting.\n"
                                        "WiFi kept connected to MeshCore-OTA (as requested)."
                                    ))
                                except Exception as e:
                                    self.log(f"⚠ Could not verify firmware version: {str(e)}")
                                    self.root.after(0, lambda: messagebox.showinfo(
                                        "OTA Update Complete",
                                        "OTA update workflow completed!\n\n"
                                        f"Could not verify firmware version: {str(e)}\n"
                                        "WiFi kept connected to MeshCore-OTA (as requested)."
                                    ))
                                # Don't disconnect here - will disconnect at end of workflow
                            
                            future = asyncio.run_coroutine_threadsafe(
                                verify_firmware_version(), self.ota_event_loop
                            )
                            future.result(timeout=60)
                                
                        except Exception as e:
                            self.log(f"⚠ Error verifying firmware version: {str(e)}")
                    else:
                        if not target_device_id:
                            self.log("⚠ Could not verify firmware version - missing target device ID")
                        elif not self.ota_meshcore:
                            self.log("⚠ Could not verify firmware version - BLE connection not available")
                        else:
                            self.log("⚠ Could not verify firmware version - unknown error")
                        # Still show a completion dialog even if version check was skipped
                        self.root.after(0, lambda: messagebox.showinfo(
                            "OTA Update Complete",
                            "OTA update workflow completed!\n\n"
                            "Could not verify firmware version (missing device ID or BLE connection).\n"
                            "WiFi kept connected to MeshCore-OTA (as requested)."
                        ))
                
                # --- Completion steps - always run regardless of checkbox state ---
                self.log("\n✓ OTA workflow complete!")
                
                # Record OTA history
                target_device_id = self.ota_target_device_var.get()
                ota_entry = {
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'target_device': target_device_id if target_device_id else 'Unknown',
                    'firmware_file': os.path.basename(self.ota_bin_file) if self.ota_bin_file and os.path.exists(self.ota_bin_file) else 'Unknown',
                    'status': 'Success' if first_result[0] and second_result[0] else 'Completed with warnings'
                }
                self.ota_history.append(ota_entry)
                # Keep only last 50 entries
                if len(self.ota_history) > 50:
                    self.ota_history = self.ota_history[-50:]
                self.log(f"📝 OTA history updated: {ota_entry['status']} at {ota_entry['timestamp']}")
                
                # BLE stays connected — user must manually disconnect
                self.log("\n✓ BLE connection remains active. Use Manual Disconnect when done.")
                
                # Update progress UI - message reflects actual WiFi state
                keep_wifi_final = self.ota_keep_wifi_connected_var.get() if hasattr(self, 'ota_keep_wifi_connected_var') else False
                progress_msg = "OTA complete - WiFi kept connected" if keep_wifi_final else "OTA complete - WiFi reconnected"
                self.root.after(0, lambda: self.ota_progress_var.set(progress_msg))
                self.root.after(0, lambda: self.ota_progress_bar.stop())
                self.root.after(0, lambda: self.ota_update_btn.config(state='normal'))

            # Start monitor thread AFTER the function is defined (not inside it)
            threading.Thread(target=monitor_thread, daemon=True).start()

            # Show message box with instructions
            self.root.after(0, lambda: messagebox.showinfo(
                "OTA Mode Started",
                "Device is now in OTA mode!\n\n"
                f"{'✓ Connected to MeshCore-OTA WiFi' if connected else 'Please connect to MeshCore-OTA WiFi'}\n"
                f"{'✓ Browser opened' if connected else ''}\n\n"
                f"Next steps:\n"
                f"{'1. Upload your .bin firmware file in the browser' if connected else '1. Connect to WiFi: MeshCore-OTA'}\n"
                f"{'2. Wait for update to complete' if connected else '2. Click Open OTA Upload Page button'}\n"
                f"{'' if connected else '3. Upload your .bin firmware file'}\n"
                f"{'' if connected else '4. Wait for update to complete'}\n\n"
                "WiFi will be automatically reconnected after OTA completes."
            ))
            
            # Don't wait for reboot - monitoring happens in background
            if not connected:
                self.root.after(0, lambda: self.ota_progress_var.set("Waiting for WiFi connection..."))
            
            # Success - OTA mode initiated (but process is paused)
            self.log("")
            self.log("=" * 60)
            self.log("✓ OTA MODE INITIATED - PROCESS PAUSED FOR MANUAL ACTION")
            self.log("=" * 60)
            self.log("")
            self.log("⚠️  REMINDER: The process is WAITING for your manual action.")
            self.log("   Please refer to the instructions above to complete the update.")
            self.log("")
            self.log("=" * 60)
            
            self.root.after(0, lambda: self.ota_progress_var.set("OTA mode started - waiting for upload"))
            self.root.after(0, lambda: self.ota_progress_bar.stop())
            self.root.after(0, lambda: self.ota_update_btn.config(state='normal'))
            
        except Exception as e:
            self.log(f"\n✗ OTA workflow error: {str(e)}")
            # Only tear down the BLE link if this workflow created it — preserve pre-existing connections
            if workflow_owns_connection and meshcore:
                try:
                    await meshcore.disconnect()
                except Exception:
                    pass
                self.ota_meshcore = None
                self._update_ble_status(False)
            
            self.root.after(0, lambda: self.ota_progress_var.set(f"Error: {str(e)}"))
            self.root.after(0, lambda: self.ota_progress_bar.stop())
            self.root.after(0, lambda: self.ota_update_btn.config(state='normal'))
            messagebox.showerror("OTA Error", f"OTA workflow failed:\n{str(e)}")
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def setup_keyboard_shortcuts(self):
        """Setup global keyboard shortcuts"""
        # Ctrl+S - Save current editor
        self.root.bind('<Control-s>', lambda e: self._handle_save_shortcut())
        self.root.bind('<Control-S>', lambda e: self._handle_save_shortcut())
        
        # Ctrl+B - Compile
        self.root.bind('<Control-b>', lambda e: self._handle_compile_shortcut())
        self.root.bind('<Control-B>', lambda e: self._handle_compile_shortcut())
        
        # Ctrl+O - Open file
        self.root.bind('<Control-o>', lambda e: self._handle_open_shortcut())
        self.root.bind('<Control-O>', lambda e: self._handle_open_shortcut())
        
        # Ctrl+Shift+S - Save As / Export log
        self.root.bind('<Control-Shift-S>', lambda e: self._handle_export_log())
        
        # Escape - Close dialogs/find bars
        self.root.bind('<Escape>', lambda e: self._handle_escape())
    
    def _handle_save_shortcut(self):
        """Handle Ctrl+S shortcut"""
        # Determine which tab is active and save accordingly
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 2:  # main.cpp tab
            if hasattr(self, 'cpp_editor') and self.cpp_editor:
                self.save_cpp_file()
        elif current_tab == 3:  # platformio.ini tab
            if hasattr(self, 'platformio_ini_editor') and self.platformio_ini_editor:
                self.save_platformio_ini()
        return "break"
    
    def _handle_compile_shortcut(self):
        """Handle Ctrl+B shortcut"""
        if not self.is_compiling and self.platformio_available:
            self.compile_firmware()
        return "break"
    
    def _handle_open_shortcut(self):
        """Handle Ctrl+O shortcut"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 2:  # main.cpp tab
            self.load_cpp_file_from_disk()
        elif current_tab == 3:  # platformio.ini tab
            self.load_platformio_ini_from_disk()
        return "break"
    
    def _handle_export_log(self):
        """Handle Ctrl+Shift+S - Export log"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Export Log"
            )
            if filename:
                log_content = self.log_text.get('1.0', tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.log(f"✓ Log exported to: {filename}")
                messagebox.showinfo("Success", f"Log exported to:\n{filename}")
        except Exception as e:
            self.log(f"✗ Error exporting log: {str(e)}")
        return "break"
    
    def _handle_escape(self):
        """Handle Escape key"""
        # Close find bars if open
        if hasattr(self, 'cpp_find_bar_visible') and self.cpp_find_bar_visible:
            self.cpp_hide_find_bar()
        if hasattr(self, 'find_bar_visible') and self.find_bar_visible:
            self.hide_find_bar()
        return "break"
    
    def setup_auto_save(self):
        """Setup auto-save timer for editors"""
        def auto_save():
            if self.auto_save_enabled:
                try:
                    # Auto-save C++ editor if modified
                    if hasattr(self, 'cpp_modified') and self.cpp_modified:
                        if hasattr(self, 'file_path') and self.file_path:
                            self.save_cpp_file(silent=True)
                    
                    # Auto-save platformio.ini if modified
                    if hasattr(self, 'platformio_ini_modified') and self.platformio_ini_modified:
                        if hasattr(self, 'project_dir') and self.project_dir:
                            self.save_platformio_ini(silent=True)
                except:
                    pass  # Silently fail on auto-save errors
                
                # Schedule next auto-save (every 30 seconds)
                self.auto_save_timer = self.root.after(30000, auto_save)
        
        # Start auto-save timer
        self.auto_save_timer = self.root.after(30000, auto_save)
    
    def check_platformio_dependencies(self, project_dir, env_name):
        """Check if PlatformIO dependencies are installed"""
        try:
            # Check if .pio directory exists
            pio_dir = os.path.join(project_dir, ".pio")
            if not os.path.exists(pio_dir):
                return False
            
            # Check if libraries are installed for this environment
            lib_dir = os.path.join(pio_dir, "libdeps", env_name)
            if os.path.exists(lib_dir):
                # Check if any libraries are installed
                libs = [d for d in os.listdir(lib_dir) if os.path.isdir(os.path.join(lib_dir, d))]
                return len(libs) > 0
            
            return False
        except:
            return False
    
    def check_platformio(self):
        """Check if PlatformIO is available"""
        try:
            result = subprocess.run(['pio', '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                self.platformio_available = True
                version = result.stdout.decode().strip()
                self.log(f"✓ PlatformIO detected: {version}")
            else:
                self.platformio_available = False
                self.log("⚠ PlatformIO not found - compilation/flashing disabled")
        except:
            self.platformio_available = False
            self.log("⚠ PlatformIO not found - compilation/flashing disabled")
    
    def refresh_devices(self):
        """Refresh the device list (same approach as meshcore_ble_name_editor)"""
        if not self.platformio_available:
            return
        
        # Show loading indicator
        self.status_var.set("Refreshing device list...")
        
        # Run in background thread
        thread = threading.Thread(target=self._refresh_devices_thread)
        thread.daemon = True
        thread.start()
    
    def _refresh_devices_thread(self):
        """Background thread for refreshing devices"""
        log_buffer = []
        
        try:
            log_buffer.append("\n🔄 Refreshing device list...")
            
            # If project directory doesn't exist, set it up
            if not self.project_dir or not os.path.exists(self.project_dir):
                log_buffer.append("Project not found - cloning MeshCore repository...")
                log_buffer.append("(This will take a minute on first refresh)")
                
                # Setup project (clone repository)
                project_dir = self.setup_project_silent()
                if project_dir:
                    self.project_dir = project_dir
                    log_buffer.append("✓ Repository cloned")
                else:
                    log_buffer.append("✗ Failed to clone repository")
            
            # Scan for available environments
            if self.project_dir and os.path.exists(self.project_dir):
                log_buffer.append("Scanning platformio.ini files for available environments...")
                scanned_devices = self.scan_platformio_environments(self.project_dir)
                if scanned_devices:
                    self.all_devices = scanned_devices  # Store all devices
                    log_buffer.append(f"✓ Found {len(scanned_devices)} firmware profiles in repository")
            
            # Filter devices based on current firmware type (don't update UI yet, we'll do it in update_ui)
            self._filter_devices_by_type(update_ui=False)
            
            # Sort device list alphabetically
            current_selection = self.device_var.get()
            device_list = sorted(list(self.available_devices.keys()))
            
            # Update UI on main thread
            def update_ui():
                self.device_combo['values'] = device_list
                
                # Restore selection if still valid
                if current_selection in device_list:
                    self.device_var.set(current_selection)
                elif device_list:
                    self.device_combo.current(0)
                
                # Write all buffered log messages at once
                for msg in log_buffer:
                    self.log(msg)
                firmware_type_display = self.firmware_type.replace('_', ' ')
                self.log(f"✓ Device list refreshed - {len(device_list)} {firmware_type_display} profiles available (sorted A-Z)")
                
                self.status_var.set(f"Device list refreshed - {len(device_list)} {firmware_type_display} devices available")
            
            self.root.after(0, update_ui)
            
        except Exception as e:
            def show_error():
                self.log(f"\n✗ Error refreshing devices: {str(e)}")
                self.status_var.set("Refresh failed")
            
            self.root.after(0, show_error)
    
    def setup_project_silent(self):
        """Setup MeshCore project directory silently (for device scanning)"""
        if self.project_dir and os.path.exists(self.project_dir):
            return self.project_dir
        
        try:
            # Create a temporary directory for the project
            project_dir = tempfile.mkdtemp(prefix="meshcore_")
            
            # Clone the repository
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', MESHCORE_FIRMWARE_REPO_URL, project_dir],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                return None
            
            return project_dir
            
        except Exception:
            return None
    
    def refresh_versions(self):
        """Fetch available versions (branches and tags) from GitHub, filtered by firmware type"""
        def fetch_thread():
            try:
                firmware_type = getattr(self, 'firmware_type', 'companion_radio')
                firmware_type_display = firmware_type.replace('_', ' ').title()
                self.log(f"Fetching available versions for {firmware_type_display} from GitHub...")
                versions = []
                
                # Fetch branches
                try:
                    req = urllib.request.Request(GITHUB_BRANCHES_URL)
                    req.add_header('User-Agent', 'MeshCore-Firmware-Editor-and-Flasher')
                    with urllib.request.urlopen(req, timeout=10) as response:
                        branches = json.loads(response.read().decode())
                        for branch in branches:
                            branch_name = branch['name']
                            # Check if this branch has the firmware type
                            try:
                                check_url = GITHUB_RAW_URL.format(ref=branch_name, firmware_type=firmware_type)
                                check_req = urllib.request.Request(check_url, method='HEAD')
                                check_req.add_header('User-Agent', 'MeshCore-Firmware-Editor-and-Flasher')
                                with urllib.request.urlopen(check_req, timeout=5) as check_resp:
                                    # File exists, include this branch
                                    versions.append(('branch', branch_name, branch_name))
                            except:
                                # File doesn't exist for this firmware type, skip it
                                pass
                except Exception as e:
                    self.log(f"⚠ Could not fetch branches: {str(e)}")
                
                # Fetch tags (using releases endpoint for better compatibility)
                try:
                    releases_url = f"{GITHUB_API_BASE}/releases"
                    req = urllib.request.Request(releases_url)
                    req.add_header('User-Agent', 'MeshCore-Firmware-Editor-and-Flasher')
                    with urllib.request.urlopen(req, timeout=10) as response:
                        releases = json.loads(response.read().decode())
                        for release in releases:
                            tag_name = release.get('tag_name', release.get('name', ''))
                            if tag_name:
                                # Check if this tag has the firmware type
                                try:
                                    check_url = GITHUB_RAW_URL.format(ref=tag_name, firmware_type=firmware_type)
                                    check_req = urllib.request.Request(check_url, method='HEAD')
                                    check_req.add_header('User-Agent', 'MeshCore-Firmware-Editor-and-Flasher')
                                    with urllib.request.urlopen(check_req, timeout=5) as check_resp:
                                        # File exists, include this tag
                                        versions.append(('tag', tag_name, f"{tag_name} (release)"))
                                except:
                                    # File doesn't exist for this firmware type, skip it
                                    pass
                except Exception as e:
                    # Fallback to tags endpoint
                    try:
                        req = urllib.request.Request(GITHUB_TAGS_URL)
                        req.add_header('User-Agent', 'MeshCore-Firmware-Editor-and-Flasher')
                        with urllib.request.urlopen(req, timeout=10) as response:
                            tags = json.loads(response.read().decode())
                            for tag in tags:
                                tag_name = tag.get('name', '')
                                if tag_name:
                                    # Check if this tag has the firmware type
                                    try:
                                        check_url = GITHUB_RAW_URL.format(ref=tag_name, firmware_type=firmware_type)
                                        check_req = urllib.request.Request(check_url, method='HEAD')
                                        check_req.add_header('User-Agent', 'MeshCore-Firmware-Editor-and-Flasher')
                                        with urllib.request.urlopen(check_req, timeout=5) as check_resp:
                                            versions.append(('tag', tag_name, f"{tag_name} (tag)"))
                                    except:
                                        pass
                    except Exception as e2:
                        self.log(f"⚠ Could not fetch tags: {str(e2)}")
                
                # Sort versions: branches first, then tags, both alphabetically
                versions.sort(key=lambda x: (x[0] != 'branch', x[1].lower()))
                
                # Update UI on main thread
                def update_ui():
                    self.available_versions = versions
                    version_list = [v[2] for v in versions]  # Display names
                    self.version_combo['values'] = version_list
                    
                    # Keep current selection if still valid
                    current = self.version_var.get()
                    if current in version_list:
                        self.version_var.set(current)
                    elif version_list:
                        self.version_var.set(version_list[0])
                        self.selected_version = versions[0][1]  # Store actual name
                    
                    firmware_type_display = firmware_type.replace('_', ' ').title()
                    self.log(f"✓ Found {len(versions)} version(s) for {firmware_type_display}")
                
                self.root.after(0, update_ui)
                
            except Exception as e:
                def show_error():
                    self.log(f"⚠ Error fetching versions: {str(e)}")
                    # Keep default "main" if fetch fails
                    if not self.version_combo['values']:
                        self.version_combo['values'] = ["main"]
                
                self.root.after(0, show_error)
        
        thread = threading.Thread(target=fetch_thread)
        thread.daemon = True
        thread.start()
    
    def _on_firmware_type_selected(self, event=None):
        """Handle firmware type selection (companion vs repeater)"""
        # Save current file state before switching
        if self.file_path and self.original_content:
            old_firmware_type = self.firmware_type
            self.file_paths[old_firmware_type] = self.file_path
            self.original_contents[old_firmware_type] = self.original_content
        
        selected = self.firmware_type_var.get()
        if selected == "Companion Radio":
            self.firmware_type = "companion_radio"  # Maps to examples/companion_radio
        elif selected == "Repeater Radio":
            self.firmware_type = "simple_repeater"  # Maps to examples/simple_repeater
        elif selected == "Room Server":
            self.firmware_type = "room_server"  # Maps to examples/room_server
        else:
            self.firmware_type = "companion_radio"  # Default
        
        # Load the file for the new firmware type
        self.file_path = self.file_paths.get(self.firmware_type)
        self.original_content = self.original_contents.get(self.firmware_type)
        
        # Update UI to reflect current file
        if self.file_path and os.path.exists(self.file_path):
            filename = os.path.basename(self.file_path)
            firmware_type_display = "Companion" if self.firmware_type == "companion_radio" else "Repeater"
            self.file_path_var.set(f"✓ Loaded: {filename} ({firmware_type_display})")
        else:
            self.file_path_var.set("No file loaded")
        
        # Reload C++ editor if we're on that tab
        if hasattr(self, 'cpp_editor'):
            current_tab = self.notebook.index(self.notebook.select())
            if current_tab == 2:  # main.cpp (C++ Editor) tab
                self.load_cpp_file()
        
        # Filter devices based on firmware type
        self._filter_devices_by_type()
        
        # Refresh versions to show only versions that have this firmware type
        self.refresh_versions()
    
    def _filter_devices_by_type(self, update_ui=True):
        """Filter available devices based on selected firmware type"""
        if not self.all_devices:
            return
        
        # Determine what to filter for
        if self.firmware_type == "simple_repeater":
            filter_keyword = "repeater"
            exclude_keyword = "companion"
        elif self.firmware_type == "room_server":
            filter_keyword = "room"
            exclude_keyword = ""
        else:  # companion_radio
            filter_keyword = "companion"
            exclude_keyword = "repeater"
        
        # Filter devices
        filtered = {}
        for readable_name, env_name in self.all_devices.items():
            env_lower = env_name.lower()
            # Include if it contains the keyword and doesn't contain the exclude keyword
            if filter_keyword in env_lower and (not exclude_keyword or exclude_keyword not in env_lower):
                filtered[readable_name] = env_name
        
        self.available_devices = filtered
        
        # Update device dropdown (only on main thread)
        if update_ui:
            def update_dropdown():
                current_selection = self.device_var.get()
                device_list = sorted(list(self.available_devices.keys()))
                self.device_combo['values'] = device_list
                
                # Restore selection if still valid, otherwise select first
                if current_selection in device_list:
                    self.device_var.set(current_selection)
                elif device_list:
                    self.device_combo.current(0)
                else:
                    self.device_var.set("")
            
            # Use root.after to ensure we're on main thread
            self.root.after(0, update_dropdown)
    
    def _on_version_selected(self, event=None):
        """Handle version selection"""
        selected_display = self.version_var.get()
        # Find the actual version name (without the "(tag)" suffix)
        for vtype, name, display in self.available_versions:
            if display == selected_display:
                self.selected_version = name
                break
        else:
            self.selected_version = selected_display
    
    def download_firmware(self):
        """Download firmware from GitHub for selected version"""
        version_ref = self.selected_version
        if not version_ref:
            version_ref = "main"
        
        # Clean up version_ref - remove any "(release)" or "(tag)" suffixes
        # Also handle cases where selected_version might be the display name
        if version_ref:
            version_ref = version_ref.split(" (")[0].strip()  # Remove "(release)" or "(tag)" suffix
        
        self.log("\n" + "="*60)
        self.log(f"DOWNLOADING FIRMWARE FROM GITHUB ({version_ref})")
        self.log("="*60)
        self.status_var.set(f"Downloading firmware ({version_ref})...")
        
        try:
            # Determine if it's a branch or tag and get commit hash
            self.log(f"Fetching commit information for '{version_ref}'...")
            
            # Try as branch first
            branch_url = f"{GITHUB_API_BASE}/branches/{version_ref}"
            commit_hash = None
            commit_date = None
            
            try:
                req = urllib.request.Request(branch_url)
                req.add_header('User-Agent', 'MeshCore-Firmware-Editor-and-Flasher')
                with urllib.request.urlopen(req, timeout=10) as response:
                    branch_info = json.loads(response.read().decode())
                    commit_hash = branch_info['commit']['sha']
                    commit_date = branch_info['commit']['commit']['author']['date']
                    self.log(f"✓ Found as branch")
            except:
                # Try as tag - fetch tag info
                try:
                    tag_url = f"{GITHUB_API_BASE}/git/refs/tags/{version_ref}"
                    req = urllib.request.Request(tag_url)
                    req.add_header('User-Agent', 'MeshCore-Firmware-Editor-and-Flasher')
                    with urllib.request.urlopen(req, timeout=10) as response:
                        tag_info = json.loads(response.read().decode())
                        # Handle both lightweight and annotated tags
                        if 'object' in tag_info:
                            if tag_info['object']['type'] == 'commit':
                                commit_hash = tag_info['object']['sha']
                            elif tag_info['object']['type'] == 'tag':  # annotated tag
                                # Get the commit from the tag object
                                tag_obj_url = tag_info['object']['url']
                                tag_obj_req = urllib.request.Request(tag_obj_url)
                                tag_obj_req.add_header('User-Agent', 'MeshCore-Firmware-Editor-and-Flasher')
                                with urllib.request.urlopen(tag_obj_req, timeout=10) as tag_obj_resp:
                                    tag_obj = json.loads(tag_obj_resp.read().decode())
                                    commit_hash = tag_obj.get('object', {}).get('sha', version_ref)
                        self.log(f"✓ Found as tag")
                except Exception as tag_err:
                    # Fallback: use the ref directly (GitHub will resolve it)
                    commit_hash = None  # Will use ref directly in URL
                    self.log(f"⚠ Using ref directly: {version_ref}")
            
            if commit_hash:
                self.log(f"✓ Commit: {commit_hash[:8]}")
                if commit_date:
                    self.log(f"✓ Date: {commit_date}")
            
            # Download the main.cpp file
            self.log(f"\nDownloading main.cpp from {version_ref} ({self.firmware_type})...")
            raw_url = GITHUB_RAW_URL.format(ref=version_ref, firmware_type=self.firmware_type)
            self.log(f"URL: {raw_url}")
            
            req = urllib.request.Request(raw_url)
            req.add_header('User-Agent', 'MeshCore-Firmware-Editor-and-Flasher')
            
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    content = response.read().decode('utf-8')
                    # Store content for current firmware type
                    self.original_contents[self.firmware_type] = content
                    self.original_content = content  # Current pointer
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    self.log(f"\n✗ 404 Not Found!")
                    self.log(f"✗ URL attempted: {raw_url}")
                    self.log(f"✗ This path may not exist in the repository.")
                    self.log(f"✗ Version: {version_ref}, Firmware Type: {self.firmware_type}")
                    self.log(f"✗ Please check if this version/branch exists and has the {self.firmware_type} firmware.")
                    raise Exception(f"404 Not Found: {raw_url}\nThe file may not exist at this path. Check if the version '{version_ref}' exists and contains '{self.firmware_type}' firmware.")
                else:
                    raise
            
            # Save to a local file in date-labeled folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            storage_dir = self.get_storage_path('cpp')
            version_safe = version_ref.replace('/', '_').replace('\\', '_')
            firmware_type_short = "companion" if self.firmware_type == "companion_radio" else "repeater"
            filename = f"main_{firmware_type_short}_{version_safe}_{timestamp}.cpp"
            file_path = os.path.join(storage_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.original_content)
            
            # Store in the appropriate firmware type slot
            self.file_paths[self.firmware_type] = file_path
            self.original_contents[self.firmware_type] = self.original_content
            self.file_path = file_path  # Current pointer
            self.is_downloaded = True
            
            lines = self.original_content.split('\n')
            self.log(f"✓ Downloaded successfully!")
            self.log(f"✓ File has {len(lines)} lines")
            self.log(f"✓ Saved as: {filename}")
            
            firmware_type_display = "Companion" if self.firmware_type == "companion_radio" else "Repeater"
            self.file_path_var.set(f"✓ Downloaded: {filename} ({firmware_type_display}, {version_ref})")
            self.status_var.set(f"Firmware downloaded successfully! ({firmware_type_display}, {version_ref})")
            
            # Add to recent files
            if file_path not in self.recent_files:
                self.recent_files.insert(0, file_path)
                # Keep only last 10 files
                if len(self.recent_files) > 10:
                    self.recent_files = self.recent_files[:10]
            
            # Load file into C++ editor if tab exists
            if hasattr(self, 'cpp_editor'):
                self.load_cpp_file()
            
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            self.log(f"\n✗ {error_msg}")
            messagebox.showerror("Download Error", error_msg)
            self.status_var.set("Download failed")
    
    def browse_file(self):
        """Open file browser to select main.cpp"""
        filename = filedialog.askopenfilename(
            title="Select main.cpp",
            filetypes=[("C++ files", "*.cpp"), ("All files", "*.*")],
            initialdir=os.path.expanduser("~")
        )
        
        if filename:
            # Add to recent files
            if filename not in self.recent_files:
                self.recent_files.insert(0, filename)
                # Keep only last 10 files
                if len(self.recent_files) > 10:
                    self.recent_files = self.recent_files[:10]
            self._load_file(filename, is_downloaded=False)
    
    def _load_file(self, filename, is_downloaded=False):
        """Internal method to load a file"""
        try:
            # Store in the appropriate firmware type slot
            self.file_paths[self.firmware_type] = filename
            self.file_path = filename  # Current pointer
            self.is_downloaded = is_downloaded
            
            # Load the file
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Store content for current firmware type
            self.original_contents[self.firmware_type] = content
            self.original_content = content  # Current pointer
            
            # Update UI
            filename_display = os.path.basename(filename)
            firmware_type_display = "Companion" if self.firmware_type == "companion_radio" else "Repeater"
            
            if is_downloaded:
                self.file_path_var.set(f"✓ Loaded: {filename_display} ({firmware_type_display})")
                self.status_var.set(f"File loaded: {filename_display}")
            else:
                self.file_path_var.set(f"✓ Selected: {filename_display} ({firmware_type_display})")
                self.status_var.set(f"File selected: {filename_display}")
            
            lines = content.split('\n')
            self.log(f"\n✓ File loaded: {filename}")
            self.log(f"  File has {len(lines)} lines")
            self.log(f"  Firmware type: {firmware_type_display}")
            
            # Load file into C++ editor if tab exists
            if hasattr(self, 'cpp_editor'):
                self.load_cpp_file()
                
        except Exception as e:
            self.log(f"\n✗ Error loading file: {str(e)}")
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
    
    def apply_ble_name_changes(self, silent=False):
        """Apply BLE name changes to the firmware file"""
        if not self.original_content:
            if not silent:
                messagebox.showwarning("No File", "Please download or select a firmware file first.")
            return False
        
        ble_name = self.ble_name_var.get().strip()
        if not ble_name:
            # Blank field — restore standard MeshCore naming (MeshCore-<node_name>)
            return self.restore_standard_ble_name(silent=silent)
        
        if not silent:
            self.log("\n" + "="*60)
            self.log("APPLYING BLE NAME CHANGES")
            self.log("="*60)
        
        try:
            lines = self.original_content.split('\n')
            modified_lines = []
            changes_made = 0
            
            # Check firmware type to determine pattern
            firmware_type = getattr(self, 'firmware_type', 'companion_radio')
            
            for i, line in enumerate(lines, 1):
                original_line = line
                modified = False
                
                if firmware_type == "companion_radio":
                    # Companion radio uses: serial_interface.begin(BLE_NAME_PREFIX, the_mesh.getNodePrefs()->node_name, ...)
                    # Replace: the_mesh.getNodePrefs()->node_name with the BLE name
                    if 'serial_interface.begin(' in line and 'the_mesh.getNodePrefs()->node_name' in line:
                        # Replace node_name with the custom BLE name
                        new_line = line.replace('the_mesh.getNodePrefs()->node_name', f'"{ble_name}"')
                        modified_lines.append(new_line)
                        changes_made += 1
                        modified = True
                        if not silent:
                            self.log(f"  ✓ Modified line {i}:")
                            self.log(f"    Before: {original_line.strip()}")
                            self.log(f"    After:  {new_line.strip()}")
                    # Also check for old dev_name pattern (backward compatibility)
                    elif 'serial_interface.begin(dev_name,' in line:
                        new_line = line.replace('dev_name,', f'"{ble_name}",')
                        modified_lines.append(new_line)
                        changes_made += 1
                        modified = True
                        if not silent:
                            self.log(f"  ✓ Modified line {i}:")
                            self.log(f"    Before: {original_line.strip()}")
                            self.log(f"    After:  {new_line.strip()}")
                
                elif firmware_type == "simple_repeater":
                    # Repeater firmware may not support BLE name changes
                    # Check if there's a pattern we can modify
                    if 'serial_interface.begin(' in line and ('node_name' in line or 'BLE_NAME' in line):
                        # Try to replace node_name references
                        if 'the_mesh.getNodePrefs()->node_name' in line:
                            new_line = line.replace('the_mesh.getNodePrefs()->node_name', f'"{ble_name}"')
                            modified_lines.append(new_line)
                            changes_made += 1
                            modified = True
                            if not silent:
                                self.log(f"  ✓ Modified line {i}:")
                                self.log(f"    Before: {original_line.strip()}")
                                self.log(f"    After:  {new_line.strip()}")
                
                if not modified:
                    modified_lines.append(line)
            
            if changes_made == 0:
                firmware_type = getattr(self, 'firmware_type', 'companion_radio')
                if firmware_type == "simple_repeater":
                    if not silent:
                        self.log("  ⚠️ WARNING: Repeater firmware may not support BLE name changes!")
                        self.log("  ⚠️ No BLE interface calls found to modify in repeater firmware.")
                        messagebox.showwarning("Repeater Firmware", 
                            "Repeater firmware may not support BLE name changes.\n"
                            "BLE name changes are typically only supported in Companion Radio firmware.")
                    return False
                else:
                    if not silent:
                        self.log("  ⚠️ WARNING: No BLE interface calls found to modify!")
                        messagebox.showwarning("No Changes", "No BLE interface calls found to modify.")
                    return False
            
            # Generate timestamped filename in date-labeled folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            storage_dir = self.get_storage_path('cpp')
            if self.is_downloaded:
                filename = f"main_custom_{ble_name.replace(' ', '_')}_{timestamp}.cpp"
                save_path = os.path.join(storage_dir, filename)
            else:
                original_name = os.path.splitext(os.path.basename(self.file_path))[0]
                filename = f"{original_name}_custom_{timestamp}.cpp"
                save_path = os.path.join(storage_dir, filename)
            
            # Save modified file
            modified_content = '\n'.join(modified_lines)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            # Update file_path for current firmware type
            self.file_paths[self.firmware_type] = save_path
            self.file_path = save_path  # Current pointer
            self.file_path_var.set(f"✓ Modified: {filename}")
            self.original_contents[self.firmware_type] = modified_content
            self.original_content = modified_content  # Current pointer
            
            # Refresh the C++ editor so the change is immediately visible
            if hasattr(self, 'cpp_editor'):
                self.load_cpp_file()

            if not silent:
                self.log(f"  ✓ Applied {changes_made} change(s)")
                self.log(f"  ✓ Saved as: {filename}")
                self.status_var.set("Changes applied successfully!")
                messagebox.showinfo("Success", f"BLE name '{ble_name}' applied successfully!")
            else:
                self.log(f"  ✓ Applied BLE name '{ble_name}' ({changes_made} change(s))")
            
            return True
            
        except Exception as e:
            if not silent:
                self.log(f"  ✗ Error applying changes: {str(e)}")
                messagebox.showerror("Error", f"Failed to apply changes:\n{str(e)}")
            else:
                self.log(f"  ✗ Error applying BLE name: {str(e)}")
            return False

    def restore_standard_ble_name(self, silent=False):
        """Restore standard MeshCore BLE naming (the_mesh.getNodePrefs()->node_name)
        when the BLE name field is blank. Reverses any previously applied custom name."""
        import re
        if not self.original_content:
            return True  # Nothing loaded yet — nothing to restore

        lines = self.original_content.split('\n')
        modified_lines = []
        changes_made = 0

        for i, line in enumerate(lines, 1):
            modified = False

            if 'serial_interface.begin(' in line and 'the_mesh.getNodePrefs()->node_name' not in line:
                # A quoted custom name may have replaced node_name — restore it
                new_line = re.sub(
                    r'(serial_interface\.begin\s*\([^,]*,\s*)"[^"]*"',
                    r'\1the_mesh.getNodePrefs()->node_name',
                    line
                )
                if new_line != line:
                    modified_lines.append(new_line)
                    changes_made += 1
                    modified = True
                    if not silent:
                        self.log(f"  ✓ Restored standard BLE naming on line {i}:")
                        self.log(f"    Before: {line.strip()}")
                        self.log(f"    After:  {new_line.strip()}")

            if not modified:
                modified_lines.append(line)

        if changes_made == 0:
            if not silent:
                self.log("  ✓ BLE name already using standard MeshCore-<node_name> — no changes needed.")
                messagebox.showinfo("Already Standard",
                    "The firmware is already using MeshCore's default BLE naming\n"
                    "(MeshCore-<node_name>). No changes were needed.")
            return True  # Already standard — nothing to do

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            storage_dir = self.get_storage_path('cpp')
            filename = f"main_standard_ble_{timestamp}.cpp"
            save_path = os.path.join(storage_dir, filename)

            modified_content = '\n'.join(modified_lines)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)

            self.file_paths[self.firmware_type] = save_path
            self.file_path = save_path
            self.file_path_var.set(f"✓ Standard BLE: {filename}")
            self.original_contents[self.firmware_type] = modified_content
            self.original_content = modified_content

            # Refresh C++ editor so the restored code is immediately visible
            if hasattr(self, 'cpp_editor'):
                self.load_cpp_file()

            if not silent:
                self.log(f"  ✓ Restored standard BLE naming ({changes_made} change(s))")
                messagebox.showinfo("Restored",
                    "BLE name cleared — firmware restored to MeshCore's default naming\n"
                    "(MeshCore-<node_name>). The C++ editor has been updated.")
            else:
                self.log(f"  ✓ BLE name blank — using standard MeshCore-<node_name> naming")

        except Exception as e:
            self.log(f"  ✗ Error restoring standard BLE name: {str(e)}")

        return True

    def scan_platformio_environments(self, project_root):
        """Scan platformio.ini files for available companion_radio and simple_repeater environments"""
        devices = {}
        try:
            # Scan root platformio.ini
            root_ini = os.path.join(project_root, "platformio.ini")
            if os.path.exists(root_ini):
                with open(root_ini, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('[env:') and line.endswith(']'):
                            env_name = line[5:-1]
                            readable_name = env_name.replace('_', ' ').title()
                            devices[readable_name] = env_name
            
            # Scan variant platformio.ini files
            variants_dir = os.path.join(project_root, "variants")
            if os.path.exists(variants_dir):
                for variant in os.listdir(variants_dir):
                    variant_ini = os.path.join(variants_dir, variant, "platformio.ini")
                    if os.path.exists(variant_ini):
                        with open(variant_ini, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith('[env:') and line.endswith(']'):
                                    env_name = line[5:-1]
                                    # Filter for companion_radio and simple_repeater environments
                                    if ('companion' in env_name or 'radio' in env_name or 
                                        'repeater' in env_name):
                                        readable_name = env_name.replace('_', ' ').title()
                                        devices[readable_name] = env_name
        except Exception as e:
            self.log(f"Note: Could not scan platformio.ini: {str(e)}")
        
        return devices
    
    def setup_project(self, silent=False):
        """Setup MeshCore project directory for compilation"""
        if self.project_dir and os.path.exists(self.project_dir):
            # Update main.cpp if file exists
            if self.file_path and os.path.exists(self.file_path):
                # Use the firmware type that was downloaded
                firmware_type = getattr(self, 'firmware_type', 'companion_radio')
                dest_path = os.path.join(self.project_dir, "examples", firmware_type, "main.cpp")
                # Ensure directory exists
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(self.file_path, dest_path)
                if not silent:
                    self.log(f"\n✓ Updated main.cpp in existing project ({firmware_type})")
            return self.project_dir
        
        if not silent:
            self.log("\n" + "="*60)
            self.log("SETTING UP PROJECT FOR COMPILATION")
            self.log("="*60)
        
        try:
            # Use a persistent directory instead of temporary
            # Store in user's home directory or app data directory
            if sys.platform == "win32":
                base_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'MeshCoreFlasher')
            else:
                base_dir = os.path.join(os.path.expanduser('~'), '.meshcore_flasher')
            
            project_dir = os.path.join(base_dir, 'meshcore_project')
            
            # If project exists, just update main.cpp if needed
            if os.path.exists(project_dir):
                if not silent:
                    self.log(f"\n✓ Using existing project directory: {project_dir}")
                    self.log("  Dependencies should already be installed - compilation will be faster")
                
                # Update main.cpp if file exists
                if self.file_path and os.path.exists(self.file_path):
                    firmware_type = getattr(self, 'firmware_type', 'companion_radio')
                    dest_path = os.path.join(project_dir, "examples", firmware_type, "main.cpp")
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(self.file_path, dest_path)
                    if not silent:
                        self.log(f"✓ Updated main.cpp in existing project ({firmware_type})")
                
                self.project_dir = project_dir
                return project_dir
            
            # Create base directory if it doesn't exist
            os.makedirs(base_dir, exist_ok=True)
            self.project_dir = project_dir
            
            if not silent:
                self.log(f"Creating project directory: {project_dir}")
                self.log("Cloning MeshCore repository (this may take a minute)...")
                self.log("Note: This only happens once. Future compilations will be faster.")
                self.status_var.set("Cloning repository...")
            elif not self.status_var.get().startswith("Scanning"):
                self.status_var.set("Scanning for devices...")
            
            # Clone the repository
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', MESHCORE_FIRMWARE_REPO_URL, project_dir],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")
            
            if not silent:
                self.log("✓ Repository cloned successfully")
            
            # Scan for available environments
            if not silent:
                self.log("Scanning for available device profiles...")
            scanned_devices = self.scan_platformio_environments(project_dir)
            if scanned_devices:
                self.all_devices = scanned_devices  # Store all devices
                if not silent:
                    self.log(f"✓ Found {len(scanned_devices)} firmware profiles (companion_radio & simple_repeater)")
                
                # Filter based on current firmware type
                self._filter_devices_by_type()
                
                device_list = sorted(list(self.available_devices.keys()))
                self.root.after(0, lambda: self.device_combo.configure(values=device_list))
                if device_list:
                    self.root.after(0, lambda: self.device_combo.set(device_list[0]))
            
            # Load platformio.ini in settings tab if it exists
            self.root.after(0, self.load_platformio_ini)
            
            # Copy our modified main.cpp to the project
            if self.file_path and os.path.exists(self.file_path):
                # Use the firmware type that was downloaded
                firmware_type = getattr(self, 'firmware_type', 'companion_radio')
                dest_path = os.path.join(project_dir, "examples", firmware_type, "main.cpp")
                # Ensure directory exists
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(self.file_path, dest_path)
                if not silent:
                    self.log(f"✓ Copied custom main.cpp to project ({firmware_type})")
            elif not silent:
                self.log("⚠️ WARNING: No custom main.cpp file to copy!")
            
            return project_dir
            
        except Exception as e:
            if not silent:
                self.log(f"✗ Setup failed: {str(e)}")
                messagebox.showerror("Error", f"Project setup failed:\n{str(e)}")
            return None
    
    def compile_firmware(self):
        """Compile the firmware in a background thread"""
        if not self.platformio_available:
            messagebox.showwarning(
                "PlatformIO Not Found",
                "PlatformIO is required for compilation.\n\n"
                "Install it from: https://platformio.org/"
            )
            return
        
        if not self.file_path or not os.path.exists(self.file_path):
            messagebox.showwarning("No File", "Please download or select a firmware file first.")
            return
        
        if self.is_compiling:
            messagebox.showinfo("Already Compiling", "A compilation is already in progress.")
            return
        
        # Get selected device
        device_name = self.device_var.get()
        env_name = self.available_devices.get(device_name)
        
        if not env_name:
            messagebox.showwarning(
                "No Device Selected",
                "Please select a device from the dropdown.\n\n"
                "If the dropdown is empty, wait for devices to load or compile once to populate it."
            )
            return
        
        # Automatically apply BLE name changes before compiling
        ble_name = self.ble_name_var.get().strip()
        if ble_name:
            if not self.apply_ble_name_changes(silent=True):
                messagebox.showwarning(
                    "BLE Name Error",
                    "Failed to apply BLE name changes. Please check the BLE name and try again."
                )
                return
        else:
            # BLE name blank — ensure main.cpp uses the standard MeshCore naming convention
            self.restore_standard_ble_name(silent=True)
        
        # Run compilation in background thread
        self.is_compiling = True
        self.compile_btn.config(state='disabled')
        self.status_var.set(f"Compiling for {device_name}...")
        
        thread = threading.Thread(target=self._compile_thread, args=(env_name, device_name))
        thread.daemon = True
        thread.start()
    
    def _compile_thread(self, env_name, device_name):
        """Background thread for compilation"""
        try:
            import time
            self.compilation_start_time = time.time()
            
            self.log("\n" + "="*60)
            self.log(f"COMPILING FIRMWARE FOR {device_name.upper()}")
            self.log("="*60)
            
            # Setup project
            project_dir = self.setup_project()
            if not project_dir:
                return
            
            self.log(f"\nProject directory: {project_dir}")
            self.log(f"Starting compilation for environment: {env_name}")
            
            # Check if dependencies are already installed
            if self.check_platformio_dependencies(project_dir, env_name):
                self.log("✓ Dependencies appear to be installed - PlatformIO will only check for updates")
                self.log("  Compilation should be faster than first run")
            else:
                self.log("⚠ Dependencies not found - PlatformIO will install them (this may take a few minutes)")
                self.log("  This is normal for the first compilation")
            
            # Display configuration
            if self.ble_name_var.get().strip():
                self.log(f"\nBLE Name: {self.ble_name_var.get()}")
            
            self.log("\nStarting compilation...")
            self.log("")
            
            # Verify platformio.ini exists
            pio_ini = os.path.join(project_dir, "platformio.ini")
            if not os.path.exists(pio_ini):
                raise Exception(f"platformio.ini not found at {pio_ini}")
            
            # Update status to show progress
            self.root.after(0, lambda: self.status_var.set(f"Compiling {device_name}... (checking dependencies)"))
            
            # Run PlatformIO build
            process = subprocess.Popen(
                ['pio', 'run', '-e', env_name],
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Track progress
            line_count = 0
            dependency_phase = True
            
            # Stream output to log with progress tracking
            for line in process.stdout:
                self.log(line.rstrip())
                line_count += 1
                
                # Update status based on output
                line_lower = line.lower()
                if 'installing' in line_lower or 'downloading' in line_lower:
                    if dependency_phase:
                        self.root.after(0, lambda: self.status_var.set(f"Installing dependencies for {device_name}..."))
                        dependency_phase = False
                elif 'compiling' in line_lower or 'building' in line_lower:
                    dependency_phase = False
                    self.root.after(0, lambda: self.status_var.set(f"Compiling {device_name}..."))
                elif 'linking' in line_lower:
                    self.root.after(0, lambda: self.status_var.set(f"Linking {device_name}..."))
                elif 'success' in line_lower:
                    self.root.after(0, lambda: self.status_var.set(f"Compilation successful for {device_name}"))
            
            process.wait()
            
            # Calculate compilation time
            minutes = 0
            seconds = 0
            if self.compilation_start_time:
                compilation_time = time.time() - self.compilation_start_time
                minutes = int(compilation_time // 60)
                seconds = int(compilation_time % 60)
            
            if process.returncode == 0:
                # Save compiled .bin file to date-labeled folder
                try:
                    bin_source = os.path.join(project_dir, ".pio", "build", env_name, "firmware.bin")
                    if os.path.exists(bin_source):
                        storage_dir = self.get_storage_path('bin')
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        device_safe = device_name.replace(' ', '_').replace('/', '_')
                        bin_filename = f"firmware_{device_safe}_{timestamp}.bin"
                        bin_dest = os.path.join(storage_dir, bin_filename)
                        shutil.copy2(bin_source, bin_dest)
                        self.last_compiled_bin = bin_dest  # Store for OTA
                        self.log(f"✓ Saved binary to: {bin_dest}")
                except Exception as e:
                    self.log(f"⚠ Could not save binary file: {str(e)}")
                
                self.log("\n" + "="*60)
                self.log("✓ COMPILATION SUCCESSFUL!")
                self.log(f"⏱ Compilation time: {minutes}m {seconds}s")
                self.log("="*60)
                self.root.after(0, lambda: self.status_var.set(f"Compilation successful! ({minutes}m {seconds}s)"))
                messagebox.showinfo("Success", f"Firmware compiled successfully for {device_name}!\n\nCompilation time: {minutes}m {seconds}s")
            else:
                self.log("\n" + "="*60)
                self.log("✗ COMPILATION FAILED")
                self.log(f"⏱ Compilation time before failure: {minutes}m {seconds}s")
                self.log("="*60)
                self.log("\nTroubleshooting tips:")
                self.log("  • Check the error messages above")
                self.log("  • Verify your code changes are correct")
                self.log("  • Ensure all dependencies are installed")
                self.log("  • Try cleaning the build: pio run -e " + env_name + " -t clean")
                self.root.after(0, lambda: self.status_var.set("Compilation failed - see log"))
                messagebox.showerror("Compilation Failed", 
                    f"Compilation failed after {minutes}m {seconds}s.\n\n"
                    "See log for details and troubleshooting tips.")
            
        except Exception as e:
            self.log(f"\n✗ Compilation error: {str(e)}")
            self.root.after(0, lambda: self.status_var.set("Compilation error"))
            messagebox.showerror("Error", f"Compilation failed:\n{str(e)}")
        finally:
            self.is_compiling = False
            self.root.after(0, lambda: self.compile_btn.config(state='normal'))
    
    def flash_firmware(self):
        """Flash the compiled firmware to the device"""
        if not self.platformio_available:
            messagebox.showwarning(
                "PlatformIO Not Found",
                "PlatformIO is required for flashing.\n\n"
                "Install it from: https://platformio.org/"
            )
            return
        
        if not self.project_dir or not os.path.exists(self.project_dir):
            messagebox.showwarning(
                "Not Compiled",
                "Please compile the firmware first before flashing."
            )
            return
        
        if self.is_compiling:
            messagebox.showinfo("Busy", "Please wait for compilation to finish.")
            return
        
        # Get selected device
        device_name = self.device_var.get()
        env_name = self.available_devices.get(device_name)
        
        if not env_name:
            messagebox.showwarning(
                "No Device Selected",
                "Please select a device from the dropdown."
            )
            return
        
        # Get flash mode
        flash_mode = self.flash_mode_var.get()
        mode_text = "Full Erase" if flash_mode == "erase" else "Update Only"
        
        # Confirm flash operation
        response = messagebox.askyesno(
            "Confirm Flash",
            f"This will flash the firmware to your {device_name}.\n\n"
            f"Flash Mode: {mode_text}\n\n"
            "Make sure your device is connected via USB.\n\n"
            "Continue?",
            icon='warning'
        )
        
        if not response:
            return
        
        self.log("\n" + "="*60)
        self.log(f"FLASHING FIRMWARE TO {device_name.upper()}")
        self.log(f"Flash Mode: {mode_text}")
        self.log("="*60)
        
        self.flash_btn.config(state='disabled')
        self.status_var.set(f"Flashing firmware ({mode_text.lower()})...")
        
        thread = threading.Thread(target=self._flash_thread, args=(env_name, device_name, flash_mode))
        thread.daemon = True
        thread.start()
    
    def _flash_thread(self, env_name, device_name, flash_mode):
        """Background thread for flashing"""
        try:
            if flash_mode == "erase":
                self.log("\n⚠️ FULL ERASE MODE SELECTED")
                self.log("This will erase the entire flash memory before uploading.")
                self.log("All data and settings will be lost!")
                self.log("")
                self.log("Erasing flash memory...")
                
                # First, erase the flash
                # Try erase_flash first (ESP32 standard), fallback to erase
                erase_targets = ['erase_flash', 'erase']
                erase_success = False
                
                for erase_target in erase_targets:
                    try:
                        self.log(f"Attempting erase with target: {erase_target}...")
                        erase_process = subprocess.Popen(
                            ['pio', 'run', '-e', env_name, '--target', erase_target],
                            cwd=self.project_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1
                        )
                        
                        # Stream erase output
                        for line in erase_process.stdout:
                            self.log(line.rstrip())
                        
                        erase_process.wait()
                        
                        if erase_process.returncode == 0:
                            erase_success = True
                            break
                        else:
                            self.log(f"Target '{erase_target}' failed, trying next...")
                    except Exception as e:
                        self.log(f"Error with target '{erase_target}': {str(e)}")
                        continue
                
                if not erase_success:
                    self.log("\n✗ ERASE FAILED")
                    self.log("Could not erase flash with any available target.")
                    self.log("Note: Some platforms may not support erase. Continuing with upload...")
                    response = messagebox.askyesno(
                        "Erase Failed",
                        "Flash erase failed or not supported.\n\n"
                        "Would you like to continue with upload anyway?\n"
                        "(This may work if erase is not required for your device)"
                    )
                    if not response:
                        self.root.after(0, lambda: self.status_var.set("Erase failed - cancelled"))
                        return
                    self.log("Continuing with upload (erase skipped)...")
                else:
                    self.log("✓ Flash erased successfully")
                    self.log("")
            
            self.log("Uploading firmware to device...")
            self.log("Please don't disconnect the device during flashing!")
            self.log("")
            
            # Build upload command (optionally with explicit port)
            upload_cmd = ['pio', 'run', '-e', env_name, '--target', 'upload']
            selected_port = getattr(self, 'serial_port_var', None)
            if selected_port:
                port_val = selected_port.get()
                if port_val and port_val != "Auto":
                    upload_cmd += ['--upload-port', port_val]

            # Run PlatformIO upload
            process = subprocess.Popen(
                upload_cmd,
                cwd=self.project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream output to log
            for line in process.stdout:
                self.log(line.rstrip())
            
            process.wait()
            
            if process.returncode == 0:
                self.log("\n" + "="*60)
                self.log("✓ FLASHING SUCCESSFUL!")
                self.log("="*60)
                self.root.after(0, lambda: self.status_var.set("Flashing successful!"))
                messagebox.showinfo("Success", f"Firmware flashed successfully to {device_name}!")
            else:
                self.log("\n" + "="*60)
                self.log("✗ FLASHING FAILED")
                self.log("="*60)
                self.root.after(0, lambda: self.status_var.set("Flashing failed"))
                messagebox.showerror("Flash Failed", "See log for details.")
            
        except Exception as e:
            self.log(f"\n✗ Flashing error: {str(e)}")
            self.root.after(0, lambda: self.status_var.set("Flashing error"))
            messagebox.showerror("Error", f"Flashing failed:\n{str(e)}")
        finally:
            self.root.after(0, lambda: self.flash_btn.config(state='normal'))
    
    def _on_tab_changed(self, event=None):
        """Handle tab change event"""
        # Tab indices: 0=Welcome, 1=Firmware, 2=main.cpp, 3=platformio.ini,
        #              4=OTA Update, 5=CLI, 6=Serial Monitor
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 2:  # main.cpp (C++ Editor) tab
            self.load_cpp_file()
        elif selected_tab == 3:  # platformio.ini (Settings) tab
            self.load_platformio_ini()
        elif selected_tab == 4:  # OTA Update tab
            # Auto-select last compiled binary if available and no file selected
            if not self.ota_bin_file and self.last_compiled_bin and os.path.exists(self.last_compiled_bin):
                self.ota_bin_file = self.last_compiled_bin
                self.ota_bin_file_var.set(os.path.basename(self.last_compiled_bin))
        elif selected_tab == 6:  # Serial Monitor tab
            self.refresh_serial_ports_combo()
    
    def go_to_cpp_editor_tab(self):
        """Navigate to C++ editor tab"""
        self.notebook.select(2)  # Switch to main.cpp tab (index 2)
        # Load C++ file if not already loaded
        if self.cpp_original_content is None:
            self.load_cpp_file()
    
    def go_to_settings_tab(self):
        """Navigate to settings tab"""
        self.notebook.select(3)  # Switch to platformio.ini tab (index 3)
        # Load platformio.ini if not already loaded
        if self.platformio_ini_original_content is None:
            self.load_platformio_ini()
    
    def go_to_ota_tab(self):
        """Navigate to OTA tab and auto-select last compiled binary"""
        self.notebook.select(4)  # Switch to OTA Update tab (index 4)
        # Auto-select last compiled binary if available
        if self.last_compiled_bin and os.path.exists(self.last_compiled_bin):
            self.ota_bin_file = self.last_compiled_bin
            self.ota_bin_file_var.set(os.path.basename(self.last_compiled_bin))
            file_size = os.path.getsize(self.last_compiled_bin) / 1024
            self.log(f"✓ Auto-selected compiled firmware: {os.path.basename(self.last_compiled_bin)} ({file_size:.2f} KB)")
    
    def _on_platformio_ini_change(self, event=None):
        """Track changes to platformio.ini editor"""
        if self.platformio_ini_original_content is None:
            return
        
        current_content = self.platformio_ini_editor.get('1.0', tk.END)
        if current_content.endswith('\n'):
            current_content = current_content[:-1]
        
        self.platformio_ini_modified = (current_content != self.platformio_ini_original_content)
        
        if self.platformio_ini_modified:
            self.platformio_ini_status_var.set("⚠ Unsaved changes")
        else:
            self.platformio_ini_status_var.set("✓ No changes")
    
    def load_platformio_ini(self):
        """Load platformio.ini into the editor"""
        # Ensure project is set up first
        if not self.project_dir or not os.path.exists(self.project_dir):
            self.platformio_ini_path_var.set("Project not loaded - clone repository first")
            self.platformio_ini_editor.delete('1.0', tk.END)
            self.platformio_ini_editor.insert('1.0', 
                "# Project not loaded yet.\n"
                "# Please wait for the device list to populate, or compile firmware first.")
            self.platformio_ini_original_content = None
            self.platformio_ini_loaded_path = None  # Clear loaded path when loading from project
            return
        
        platformio_ini_path = os.path.join(self.project_dir, "platformio.ini")
        self.platformio_ini_path_var.set(platformio_ini_path)
        self.platformio_ini_loaded_path = None  # Clear loaded path when loading from project
        
        if not os.path.exists(platformio_ini_path):
            self.platformio_ini_editor.delete('1.0', tk.END)
            self.platformio_ini_editor.insert('1.0', f"# Error: platformio.ini not found at:\n# {platformio_ini_path}")
            self.platformio_ini_original_content = None
            return
        
        try:
            with open(platformio_ini_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.platformio_ini_editor.delete('1.0', tk.END)
            self.platformio_ini_editor.insert('1.0', content)
            self.platformio_ini_editor.mark_set(tk.INSERT, '1.0')
            self.platformio_ini_original_content = content
            self.platformio_ini_modified = False
            self.platformio_ini_status_var.set("✓ Loaded")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load platformio.ini:\n{str(e)}")
            self.platformio_ini_original_content = None
    
    def load_platformio_ini_from_disk(self):
        """Load a platformio.ini file from disk into the editor"""
        # Get the current directory (where downloaded files are saved)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Look for saved files in current directory
        filename = filedialog.askopenfilename(
            title="Load platformio.ini File",
            filetypes=[
                ("INI files", "*.ini"),
                ("All files", "*.*")
            ],
            initialdir=current_dir
        )
        
        if not filename:
            return
        
        # Check for unsaved changes
        if self.platformio_ini_modified:
            response = messagebox.askyesno(
                "Unsaved Changes",
                "You have unsaved changes. Loading a new file will discard them.\n\n"
                "Continue?",
                icon='warning'
            )
            if not response:
                return
        
        try:
            # Load the file
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Track the loaded file path
            self.platformio_ini_loaded_path = filename
            
            # Load into editor
            self.platformio_ini_editor.delete('1.0', tk.END)
            self.platformio_ini_editor.insert('1.0', content)
            self.platformio_ini_editor.mark_set(tk.INSERT, '1.0')
            self.platformio_ini_original_content = content
            self.platformio_ini_modified = False
            
            # Update UI
            self.platformio_ini_path_var.set(filename)
            self.platformio_ini_status_var.set("✓ Loaded from disk")
            self.log(f"✓ platformio.ini loaded: {os.path.basename(filename)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load platformio.ini file:\n{str(e)}")
            self.log(f"✗ Error loading platformio.ini file: {str(e)}")
    
    def reload_platformio_ini(self):
        """Reload platformio.ini from disk"""
        if self.platformio_ini_modified:
            response = messagebox.askyesno(
                "Unsaved Changes",
                "You have unsaved changes. Reloading will discard them.\n\n"
                "Continue?",
                icon='warning'
            )
            if not response:
                return
        
        # If a file was loaded from disk, reload that; otherwise reload from project
        if self.platformio_ini_loaded_path and os.path.exists(self.platformio_ini_loaded_path):
            try:
                with open(self.platformio_ini_loaded_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.platformio_ini_editor.delete('1.0', tk.END)
                self.platformio_ini_editor.insert('1.0', content)
                self.platformio_ini_editor.mark_set(tk.INSERT, '1.0')
                self.platformio_ini_original_content = content
                self.platformio_ini_modified = False
                self.platformio_ini_status_var.set("✓ Reloaded")
                self.log("✓ platformio.ini reloaded from disk")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reload platformio.ini:\n{str(e)}")
        else:
            self.load_platformio_ini()
            self.log("✓ platformio.ini reloaded from project")
    
    def save_platformio_ini(self, silent=False):
        """Save platformio.ini to disk"""
        # Determine save path: use loaded path if available, otherwise use project_dir
        if self.platformio_ini_loaded_path and os.path.exists(os.path.dirname(self.platformio_ini_loaded_path)):
            platformio_ini_path = self.platformio_ini_loaded_path
        elif self.project_dir and os.path.exists(self.project_dir):
            platformio_ini_path = os.path.join(self.project_dir, "platformio.ini")
        else:
            messagebox.showerror("Error", "No file loaded and project not available. Cannot save platformio.ini.")
            return
        
        try:
            new_content = self.platformio_ini_editor.get('1.0', tk.END)
            # Remove trailing newline that tkinter adds
            if new_content.endswith('\n'):
                new_content = new_content[:-1]
            
            # Backup original file
            backup_path = platformio_ini_path + '.backup'
            if os.path.exists(platformio_ini_path):
                shutil.copy2(platformio_ini_path, backup_path)
            
            # Save new content
            with open(platformio_ini_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Also save a copy to date-labeled folder
            try:
                storage_dir = self.get_storage_path('platformio')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                storage_filename = f"platformio_{timestamp}.ini"
                storage_path = os.path.join(storage_dir, storage_filename)
                with open(storage_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.log(f"✓ Saved copy to: {storage_path}")
            except Exception as e:
                self.log(f"⚠ Could not save copy to storage folder: {str(e)}")
            
            self.platformio_ini_original_content = new_content
            self.platformio_ini_modified = False
            self.platformio_ini_status_var.set("✓ Saved")
            
            if not silent:
                self.log(f"✓ platformio.ini saved (backup: {os.path.basename(backup_path)})")
                messagebox.showinfo("Success", "platformio.ini saved successfully!")
                # Switch back to firmware tab
                self.notebook.select(1)  # Switch to Firmware tab (index 1)
            else:
                # Silent save - just log briefly
                pass  # Auto-save is silent
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save platformio.ini:\n{str(e)}")
    
    def reset_platformio_ini(self):
        """Reset platformio.ini to original content"""
        if not self.platformio_ini_modified:
            messagebox.showinfo("Info", "No changes to reset.")
            return
        
        response = messagebox.askyesno(
            "Reset Changes",
            "This will discard all unsaved changes and restore the original content.\n\n"
            "Continue?",
            icon='warning'
        )
        
        if response:
            if self.platformio_ini_original_content:
                self.platformio_ini_editor.delete('1.0', tk.END)
                self.platformio_ini_editor.insert('1.0', self.platformio_ini_original_content)
                self.platformio_ini_modified = False
                self.platformio_ini_status_var.set("✓ Reset to original")
                self.log("✓ platformio.ini reset to original content")
            else:
                self.load_platformio_ini()
    
    def show_find_bar(self):
        """Show the find bar"""
        if not self.find_bar_visible:
            self.find_bar.grid()
            self.find_bar_visible = True
            self.find_entry.focus()
            self.find_entry.select_range(0, tk.END)
    
    def hide_find_bar(self):
        """Hide the find bar"""
        if self.find_bar_visible:
            self.find_bar.grid_remove()
            self.find_bar_visible = False
            self.find_entry.delete(0, tk.END)
            self.find_status_var.set("")
            # Clear highlighting
            self.platformio_ini_editor.tag_remove("search", "1.0", tk.END)
            self.platformio_ini_editor.tag_remove("search_current", "1.0", tk.END)
            self.find_matches = []
            self.find_current_match = -1
    
    def _on_find_entry_change(self, event=None):
        """Handle find entry text changes"""
        search_text = self.find_entry.get()
        if not search_text:
            self.find_status_var.set("")
            self.platformio_ini_editor.tag_remove("search", "1.0", tk.END)
            self.platformio_ini_editor.tag_remove("search_current", "1.0", tk.END)
            self.find_matches = []
            self.find_current_match = -1
            return
        
        # Find all matches
        self.find_matches = []
        content = self.platformio_ini_editor.get('1.0', tk.END)
        start_pos = '1.0'
        
        # Clear previous highlighting
        self.platformio_ini_editor.tag_remove("search", "1.0", tk.END)
        self.platformio_ini_editor.tag_remove("search_current", "1.0", tk.END)
        
        # Configure search tag
        self.platformio_ini_editor.tag_config("search", background="yellow")
        self.platformio_ini_editor.tag_config("search_current", background="orange")
        
        # Find all occurrences (case-insensitive)
        while True:
            pos = self.platformio_ini_editor.search(search_text, start_pos, tk.END, nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(search_text)}c"
            self.find_matches.append((pos, end_pos))
            self.platformio_ini_editor.tag_add("search", pos, end_pos)
            start_pos = end_pos
        
        # Update status
        if self.find_matches:
            self.find_status_var.set(f"Found {len(self.find_matches)} match(es)")
            self.find_current_match = -1
        else:
            self.find_status_var.set("No matches found")
            self.find_current_match = -1
    
    def find_next(self):
        """Find next occurrence"""
        search_text = self.find_entry.get()
        if not search_text:
            return
        
        if not self.find_matches:
            self._on_find_entry_change()
        
        if not self.find_matches:
            return
        
        # Get current cursor position
        cursor_pos = self.platformio_ini_editor.index(tk.INSERT)
        
        # Find next match after cursor
        next_match = None
        for i, (start, end) in enumerate(self.find_matches):
            if self.platformio_ini_editor.compare(start, ">", cursor_pos):
                next_match = i
                break
        
        # If no match after cursor, wrap to first
        if next_match is None:
            next_match = 0
        
        # Highlight and scroll to match
        self._highlight_match(next_match)
    
    def find_previous(self):
        """Find previous occurrence"""
        search_text = self.find_entry.get()
        if not search_text:
            return
        
        if not self.find_matches:
            self._on_find_entry_change()
        
        if not self.find_matches:
            return
        
        # Get current cursor position
        cursor_pos = self.platformio_ini_editor.index(tk.INSERT)
        
        # Find previous match before cursor
        prev_match = None
        for i in range(len(self.find_matches) - 1, -1, -1):
            start, end = self.find_matches[i]
            if self.platformio_ini_editor.compare(start, "<", cursor_pos):
                prev_match = i
                break
        
        # If no match before cursor, wrap to last
        if prev_match is None:
            prev_match = len(self.find_matches) - 1
        
        # Highlight and scroll to match
        self._highlight_match(prev_match)
    
    def _highlight_match(self, match_index):
        """Highlight a specific match"""
        if not self.find_matches or match_index < 0 or match_index >= len(self.find_matches):
            return
        
        # Clear current match highlighting
        self.platformio_ini_editor.tag_remove("search_current", "1.0", tk.END)
        
        # Highlight all matches
        for i, (start, end) in enumerate(self.find_matches):
            self.platformio_ini_editor.tag_add("search", start, end)
        
        # Highlight current match
        start, end = self.find_matches[match_index]
        self.platformio_ini_editor.tag_add("search_current", start, end)
        
        # Move cursor and scroll to match
        self.platformio_ini_editor.mark_set(tk.INSERT, start)
        self.platformio_ini_editor.see(start)
        self.find_current_match = match_index
        
        # Update status
        self.find_status_var.set(f"Match {match_index + 1} of {len(self.find_matches)}")
    
    # C++ Editor Methods
    def load_cpp_file(self):
        """Load the current C++ file into the editor"""
        if not self.file_path or not os.path.exists(self.file_path):
            self.cpp_editor_path_var.set("No file loaded - download or browse a firmware file first")
            self.cpp_editor.delete('1.0', tk.END)
            self.cpp_editor.insert('1.0', 
                "// No file loaded yet.\n"
                "// Please download firmware or browse a local file first.")
            self.cpp_original_content = None
            self.cpp_modified = False
            self.cpp_editor_status_var.set("No file loaded")
            return
        
        self.cpp_editor_path_var.set(self.file_path)
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.cpp_editor.delete('1.0', tk.END)
            self.cpp_editor.insert('1.0', content)
            self.cpp_editor.mark_set(tk.INSERT, '1.0')
            self.cpp_original_content = content
            self.cpp_modified = False
            self.cpp_editor_status_var.set("✓ Loaded")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load C++ file:\n{str(e)}")
            self.cpp_original_content = None
    
    def load_cpp_file_from_disk(self):
        """Load a C++ file from disk into the editor"""
        # Get the current directory (where downloaded files are saved)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Look for saved files in current directory
        filename = filedialog.askopenfilename(
            title="Load C++ File",
            filetypes=[
                ("C++ files", "*.cpp"),
                ("All files", "*.*")
            ],
            initialdir=current_dir
        )
        
        if not filename:
            return
        
        # Check for unsaved changes
        if self.cpp_modified:
            response = messagebox.askyesno(
                "Unsaved Changes",
                "You have unsaved changes. Loading a new file will discard them.\n\n"
                "Continue?",
                icon='warning'
            )
            if not response:
                return
        
        try:
            # Load the file
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update file path and content for current firmware type
            self.file_paths[self.firmware_type] = filename
            self.file_path = filename  # Current pointer
            self.original_contents[self.firmware_type] = content
            self.original_content = content  # Current pointer
            
            # Load into editor
            self.cpp_editor.delete('1.0', tk.END)
            self.cpp_editor.insert('1.0', content)
            self.cpp_editor.mark_set(tk.INSERT, '1.0')
            self.cpp_original_content = content
            self.cpp_modified = False
            
            # Update UI
            self.cpp_editor_path_var.set(filename)
            self.cpp_editor_status_var.set("✓ Loaded from disk")
            self.log(f"✓ C++ file loaded: {os.path.basename(filename)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load C++ file:\n{str(e)}")
            self.log(f"✗ Error loading C++ file: {str(e)}")
    
    def reload_cpp_file(self):
        """Reload C++ file from disk"""
        if self.cpp_modified:
            response = messagebox.askyesno(
                "Unsaved Changes",
                "You have unsaved changes. Reloading will discard them.\n\n"
                "Continue?",
                icon='warning'
            )
            if not response:
                return
        
        self.load_cpp_file()
        self.log("✓ C++ file reloaded from disk")
    
    def save_cpp_file(self, silent=False):
        """Save C++ file to disk"""
        if not self.file_path:
            if not silent:
                messagebox.showerror("Error", "No file loaded. Cannot save.")
            return
        
        try:
            new_content = self.cpp_editor.get('1.0', tk.END)
            # Remove trailing newline that tkinter adds
            if new_content.endswith('\n'):
                new_content = new_content[:-1]
            
            # Backup original file
            backup_path = self.file_path + '.backup'
            if os.path.exists(self.file_path):
                shutil.copy2(self.file_path, backup_path)
            
            # Save new content
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Also save a copy to date-labeled folder
            try:
                storage_dir = self.get_storage_path('cpp')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                original_name = os.path.splitext(os.path.basename(self.file_path))[0]
                storage_filename = f"{original_name}_saved_{timestamp}.cpp"
                storage_path = os.path.join(storage_dir, storage_filename)
                with open(storage_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.log(f"✓ Saved copy to: {storage_path}")
            except Exception as e:
                self.log(f"⚠ Could not save copy to storage folder: {str(e)}")
            
            # Update content for current firmware type
            self.cpp_original_content = new_content
            self.original_contents[self.firmware_type] = new_content
            self.original_content = new_content  # Current pointer
            self.cpp_modified = False
            self.cpp_editor_status_var.set("✓ Saved")
            
            if not silent:
                self.log(f"✓ C++ file saved (backup: {os.path.basename(backup_path)})")
                messagebox.showinfo("Success", "C++ file saved successfully!")
                # Switch back to firmware tab
                self.notebook.select(1)  # Switch to Firmware tab (index 1)
            else:
                # Silent save - just update status
                pass  # Auto-save is silent
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save C++ file:\n{str(e)}")
    
    def reset_cpp_file(self):
        """Reset C++ file to original content"""
        if not self.cpp_original_content:
            messagebox.showinfo("Info", "No original content to reset to.")
            return
        
        if not self.cpp_modified:
            messagebox.showinfo("Info", "No changes to reset.")
            return
        
        response = messagebox.askyesno(
            "Reset Changes",
            "This will discard all unsaved changes and restore the original content.\n\n"
            "Continue?",
            icon='warning'
        )
        if response:
            self.cpp_editor.delete('1.0', tk.END)
            self.cpp_editor.insert('1.0', self.cpp_original_content)
            self.cpp_modified = False
            self.cpp_editor_status_var.set("✓ Reset to original")
            self.log("✓ C++ file reset to original content")
    
    def _on_cpp_editor_change(self, event=None):
        """Track changes to C++ editor"""
        if self.cpp_original_content is None:
            return
        
        current_content = self.cpp_editor.get('1.0', tk.END)
        if current_content.endswith('\n'):
            current_content = current_content[:-1]
        
        self.cpp_modified = (current_content != self.cpp_original_content)
        
        if self.cpp_modified:
            self.cpp_editor_status_var.set("⚠ Unsaved changes")
        else:
            self.cpp_editor_status_var.set("✓ No changes")
    
    def cpp_show_find_bar(self):
        """Show the find bar for C++ editor"""
        if not self.cpp_find_bar_visible:
            self.cpp_find_bar.grid()
            self.cpp_find_bar_visible = True
            self.cpp_find_entry.focus()
            self.cpp_find_entry.select_range(0, tk.END)
    
    def cpp_hide_find_bar(self):
        """Hide the find bar for C++ editor"""
        if self.cpp_find_bar_visible:
            self.cpp_find_bar.grid_remove()
            self.cpp_find_bar_visible = False
            self.cpp_find_entry.delete(0, tk.END)
            self.cpp_find_status_var.set("")
            # Clear highlighting
            self.cpp_editor.tag_remove("search", "1.0", tk.END)
            self.cpp_editor.tag_remove("search_current", "1.0", tk.END)
            self.cpp_find_matches = []
            self.cpp_find_current_match = -1
    
    def _on_cpp_find_entry_change(self, event=None):
        """Handle find entry text changes for C++ editor"""
        search_text = self.cpp_find_entry.get()
        if not search_text:
            self.cpp_find_status_var.set("")
            self.cpp_editor.tag_remove("search", "1.0", tk.END)
            self.cpp_editor.tag_remove("search_current", "1.0", tk.END)
            self.cpp_find_matches = []
            self.cpp_find_current_match = -1
            return
        
        # Find all matches
        self.cpp_find_matches = []
        
        # Clear previous highlighting
        self.cpp_editor.tag_remove("search", "1.0", tk.END)
        self.cpp_editor.tag_remove("search_current", "1.0", tk.END)
        
        # Configure search tag
        self.cpp_editor.tag_config("search", background="yellow")
        self.cpp_editor.tag_config("search_current", background="orange")
        
        # Find all occurrences (case-insensitive)
        start_pos = '1.0'
        while True:
            pos = self.cpp_editor.search(search_text, start_pos, tk.END, nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(search_text)}c"
            self.cpp_find_matches.append((pos, end_pos))
            self.cpp_editor.tag_add("search", pos, end_pos)
            start_pos = end_pos
        
        # Update status
        if self.cpp_find_matches:
            self.cpp_find_status_var.set(f"Found {len(self.cpp_find_matches)} match(es)")
            self.cpp_find_current_match = -1
        else:
            self.cpp_find_status_var.set("No matches found")
            self.cpp_find_current_match = -1
    
    def cpp_find_next(self):
        """Find next occurrence in C++ editor"""
        search_text = self.cpp_find_entry.get()
        if not search_text:
            return
        
        if not self.cpp_find_matches:
            self._on_cpp_find_entry_change()
        
        if not self.cpp_find_matches:
            return
        
        # Find next match
        self.cpp_find_current_match = (self.cpp_find_current_match + 1) % len(self.cpp_find_matches)
        self._cpp_highlight_match(self.cpp_find_current_match)
    
    def cpp_find_previous(self):
        """Find previous occurrence in C++ editor"""
        search_text = self.cpp_find_entry.get()
        if not search_text:
            return
        
        if not self.cpp_find_matches:
            self._on_cpp_find_entry_change()
        
        if not self.cpp_find_matches:
            return
        
        # Find previous match
        prev_match = self.cpp_find_current_match - 1
        if prev_match < 0:
            prev_match = len(self.cpp_find_matches) - 1
        
        # Highlight and scroll to match
        self._cpp_highlight_match(prev_match)
    
    def _cpp_highlight_match(self, match_index):
        """Highlight a specific match in C++ editor"""
        if not self.cpp_find_matches or match_index < 0 or match_index >= len(self.cpp_find_matches):
            return
        
        # Clear current match highlighting
        self.cpp_editor.tag_remove("search_current", "1.0", tk.END)
        
        # Highlight all matches
        for i, (start, end) in enumerate(self.cpp_find_matches):
            self.cpp_editor.tag_add("search", start, end)
        
        # Highlight current match
        start, end = self.cpp_find_matches[match_index]
        self.cpp_editor.tag_add("search_current", start, end)
        
        # Move cursor and scroll to match
        self.cpp_editor.mark_set(tk.INSERT, start)
        self.cpp_editor.see(start)
        self.cpp_find_current_match = match_index
        
        # Update status
        self.cpp_find_status_var.set(f"Match {match_index + 1} of {len(self.cpp_find_matches)}")
    
    # ------------------------------------------------------------------
    # Manual connection control helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------ spinner
    _SPINNER_FRAMES = ('⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏')

    def _start_spinner(self, var: tk.StringVar, flag: str):
        """Activate a spinner on *var*, keyed by the bool attribute *flag*."""
        setattr(self, flag, True)
        self._tick_spinner(var, flag, 0)

    def _stop_spinner(self, var: tk.StringVar, flag: str):
        """Deactivate the spinner on *var*."""
        setattr(self, flag, False)
        var.set("")

    def _tick_spinner(self, var: tk.StringVar, flag: str, idx: int):
        """One animation tick — reschedules itself while *flag* is True."""
        if not getattr(self, flag, False):
            var.set("")
            return
        var.set(self._SPINNER_FRAMES[idx % len(self._SPINNER_FRAMES)])
        self.root.after(100, lambda: self._tick_spinner(var, flag, idx + 1))

    # ------------------------------------------------------------------ /spinner

    def _update_ble_status(self, connected: bool, device_name: str = ""):
        """Update the BLE status label in the OTA tab."""
        if not hasattr(self, 'ble_status_var'):
            return
        if connected:
            label = f"🟢 Connected: {device_name}" if device_name else "🟢 Connected"
            colour = '#1a9c1a'  # green
        else:
            label = "⚫ Not connected"
            colour = 'gray'
        def _apply():
            self.ble_status_var.set(label)
            if hasattr(self, 'ble_status_label'):
                self.ble_status_label.config(foreground=colour)
        self.root.after(0, _apply)

    def _update_wifi_status(self, connected: bool, ssid: str = "MeshCore-OTA"):
        """Update the WiFi status label in the OTA tab."""
        if not hasattr(self, 'wifi_status_var'):
            return
        if connected:
            label = f"🟢 Connected: {ssid}"
            colour = '#1a9c1a'  # green
        else:
            label = "⚫ Not connected to MeshCore-OTA"
            colour = 'gray'
        def _apply():
            self.wifi_status_var.set(label)
            if hasattr(self, 'wifi_status_label'):
                self.wifi_status_label.config(foreground=colour)
        self.root.after(0, _apply)

    def manual_ble_disconnect(self):
        """Manually disconnect from the active BLE device."""
        if not self.ota_meshcore:
            messagebox.showinfo("BLE", "No active BLE connection to disconnect.")
            return

        response = messagebox.askyesno(
            "Disconnect BLE",
            "Disconnect from the current BLE device?\n\n"
            "You can reconnect at any time by clicking 'Load Contacts'.",
            icon='question',
            parent=self.root
        )
        if not response:
            return

        self.ota_progress_var.set("Disconnecting BLE...")
        self.log("\nManually disconnecting from BLE device...")

        def _do_disconnect():
            mc = self.ota_meshcore
            self.ota_meshcore = None
            self._update_ble_status(False)
            if mc is not None:
                try:
                    import asyncio
                    future = asyncio.run_coroutine_threadsafe(
                        mc.disconnect(), self.ota_event_loop
                    )
                    future.result(timeout=10)
                except Exception:
                    pass
            self.log("✓ BLE disconnected")
            self.root.after(0, lambda: self.ota_progress_var.set("BLE disconnected"))

        threading.Thread(target=_do_disconnect, daemon=True).start()

    async def _send_stop_ota_async(self):
        """Send 'stop ota' to the target device via BLE, reconnecting if necessary."""
        import asyncio
        from meshcore import MeshCore
        from meshcore.ble_cx import BLEConnection
        from meshcore.events import EventType

        # Resolve the target device ID
        target_device_selection = self.ota_target_device_var.get().strip()
        target_device_id = None
        if hasattr(self, 'ota_contacts_dict') and self.ota_contacts_dict:
            target_device_id = self.ota_contacts_dict.get(target_device_selection)
        if not target_device_id:
            import re
            match = re.search(r'\(([^)]+)\)', target_device_selection)
            target_device_id = match.group(1).strip() if match else target_device_selection

        if not target_device_id:
            self.log("⚠ Cannot send 'stop ota' — no target device ID found")
            return False

        meshcore_conn = None
        we_reconnected = False

        try:
            # Prefer the existing BLE connection
            if self.ota_meshcore is not None:
                try:
                    is_live = self.ota_meshcore.connection_manager.is_connected
                except Exception:
                    is_live = False

                if is_live:
                    self.log("✓ Using existing BLE connection to send 'stop ota'")
                    meshcore_conn = self.ota_meshcore
                else:
                    self.log("⚠ Existing BLE connection lost — will reconnect")

            if meshcore_conn is None:
                # Reconnect BLE specifically for this command
                self.log("Reconnecting BLE to send 'stop ota' command...")
                selected_value = self.ota_ble_device_var.get().strip()
                ble_address = None
                if (selected_value and selected_value != "Auto-scan"
                        and selected_value in self.ota_scanned_devices):
                    _, ble_address = self.ota_scanned_devices[selected_value]

                ble_conn = BLEConnection(address=ble_address)
                meshcore_conn = MeshCore(ble_conn, debug=False)
                await meshcore_conn.connect()
                we_reconnected = True
                self.log("✓ BLE reconnected for 'stop ota' command")

            # Send 'stop ota' to the target device via mesh
            self.log("Sending 'stop ota' command to target device — shutting down WiFi hotspot...")
            self.root.after(0, lambda: self.ota_progress_var.set("Sending 'stop ota' to device..."))
            result = await asyncio.wait_for(
                meshcore_conn.commands.send_cmd(target_device_id, "stop ota"),
                timeout=15.0
            )

            if result.type == EventType.MSG_SENT:
                self.log("✓ 'stop ota' command sent — device will shut down its WiFi hotspot")
                await asyncio.sleep(2.0)  # Give the device time to process
                return True
            else:
                self.log(f"⚠ 'stop ota' returned unexpected response: {result.type} — continuing anyway")
                return False

        except asyncio.TimeoutError:
            self.log("⚠ Timeout sending 'stop ota' — proceeding with WiFi disconnect anyway")
            return False
        except Exception as e:
            self.log(f"⚠ Could not send 'stop ota': {str(e)} — proceeding with WiFi disconnect anyway")
            return False
        finally:
            # Only clean up a connection WE created; leave ota_meshcore untouched
            if we_reconnected and meshcore_conn:
                try:
                    await meshcore_conn.disconnect()
                    self.log("✓ Temporary BLE connection closed")
                except Exception:
                    pass

    def manual_wifi_disconnect(self):
        """Manually disconnect from MeshCore-OTA WiFi, with optional reconnect to previous network."""
        if not self.ota_wifi_connected:
            messagebox.showinfo("WiFi", "Not currently connected to MeshCore-OTA WiFi.")
            return

        # Step 1: Confirm the disconnect
        if not messagebox.askyesno(
            "Disconnect WiFi",
            "Disconnect from MeshCore-OTA WiFi?",
            icon='question',
            parent=self.root
        ):
            return

        # Step 2: Ask about reconnecting to previous network (only if one is stored)
        reconnect = False
        if self.previous_wifi_connection:
            reconnect = messagebox.askyesno(
                "Reconnect to Previous Network",
                f"Reconnect to your previous WiFi network?\n\n"
                f"  '{self.previous_wifi_connection}'\n\n"
                f"• Yes — disconnect from MeshCore-OTA and reconnect to previous network\n"
                f"• No  — just disconnect from MeshCore-OTA (your OS may reconnect on its own)",
                icon='question',
                parent=self.root
            )

        self.log("\nManually disconnecting from MeshCore-OTA WiFi...")
        self.ota_progress_var.set("Stopping OTA hotspot on device...")

        # Capture for closure
        do_reconnect = reconnect
        prev_network = self.previous_wifi_connection

        def _do_wifi_disconnect():
            import asyncio

            # Step A: Tell the device to stop the OTA hotspot via BLE before disconnecting WiFi
            self.log("\n[1/2] Telling device to stop OTA hotspot...")
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._send_stop_ota_async(), self.ota_event_loop
                )
                future.result(timeout=30)
            except Exception as e:
                self.log(f"⚠ Could not stop OTA hotspot on device: {str(e)}")

            # Step B: Disconnect from the WiFi network on this machine
            self.log("\n[2/2] Disconnecting from MeshCore-OTA WiFi...")
            self.root.after(0, lambda: self.ota_progress_var.set("Disconnecting WiFi..."))
            self.disconnect_ota_wifi()
            self._update_wifi_status(False)

            if do_reconnect and prev_network:
                self.log(f"Reconnecting to '{prev_network}'...")
                success = self.reconnect_previous_wifi()
                if success:
                    self.root.after(0, lambda: self.ota_progress_var.set(
                        f"WiFi reconnected to '{prev_network}'"))
                else:
                    self.root.after(0, lambda: self.ota_progress_var.set(
                        "WiFi disconnected (could not reconnect to previous network)"))
            else:
                self.root.after(0, lambda: self.ota_progress_var.set("WiFi disconnected"))

        threading.Thread(target=_do_wifi_disconnect, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────
    # Serial Monitor Tab
    # ──────────────────────────────────────────────────────────────────────────

    def setup_serial_monitor_tab(self):
        """Build the Serial Monitor tab."""
        self.serial_monitor_tab.columnconfigure(0, weight=1)
        self.serial_monitor_tab.rowconfigure(2, weight=1)

        # Title row
        title_frame = ttk.Frame(self.serial_monitor_tab)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        title_frame.columnconfigure(0, weight=1)
        ttk.Label(title_frame, text="🖥️ Serial Monitor",
                  font=('Arial', 14, 'bold')).grid(row=0, column=0, sticky=tk.W)
        self.sm_status_var = tk.StringVar(value="Stopped")
        ttk.Label(title_frame, textvariable=self.sm_status_var,
                  font=('Arial', 9), foreground='gray').grid(row=0, column=1, sticky=tk.E)

        # Controls row
        ctrl_frame = ttk.Frame(self.serial_monitor_tab)
        ctrl_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 6))

        ttk.Label(ctrl_frame, text="Port:").grid(row=0, column=0, padx=(0, 4), sticky=tk.W)
        self.sm_port_var = tk.StringVar(value="Auto")
        self.sm_port_combo = ttk.Combobox(ctrl_frame, textvariable=self.sm_port_var,
                                          values=["Auto"], state='readonly', width=20)
        self.sm_port_combo.grid(row=0, column=1, padx=(0, 8))
        self.sm_port_var.trace_add('write', lambda *_: self._sm_restart())

        ttk.Label(ctrl_frame, text="Baud:").grid(row=0, column=2, padx=(0, 4), sticky=tk.W)
        self.sm_baud_var = tk.StringVar(value="115200")
        sm_baud_combo = ttk.Combobox(ctrl_frame, textvariable=self.sm_baud_var,
                                     values=["9600", "38400", "57600", "115200", "230400", "921600"],
                                     state='readonly', width=10)
        sm_baud_combo.grid(row=0, column=3, padx=(0, 8))
        self.sm_baud_var.trace_add('write', lambda *_: self._sm_restart())

        ttk.Button(ctrl_frame, text="🔄 Refresh Ports", width=14,
                   command=self.refresh_serial_ports_combo).grid(row=0, column=4, padx=(0, 8))
        ttk.Button(ctrl_frame, text="🗑 Clear", width=10,
                   command=self.clear_serial_monitor).grid(row=0, column=5)

        # Output area
        out_frame = ttk.Frame(self.serial_monitor_tab)
        out_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(0, weight=1)

        self.sm_output = tk.Text(out_frame, font=('Courier', 9), wrap=tk.WORD,
                                 bg='#1e1e1e', fg='#d4d4d4', insertbackground='white',
                                 state='disabled')
        self.sm_output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        sm_scrollbar = ttk.Scrollbar(out_frame, orient="vertical", command=self.sm_output.yview)
        sm_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.sm_output['yscrollcommand'] = sm_scrollbar.set

    def refresh_serial_ports_combo(self):
        """Refresh the serial port lists in both the firmware tab and serial monitor tab."""
        ports = self._scan_serial_ports()
        values = ["Auto"] + ports

        # Firmware tab port combo
        if hasattr(self, 'serial_port_combo'):
            current = self.serial_port_var.get()
            self.serial_port_combo['values'] = values
            if current not in values:
                self.serial_port_var.set("Auto")

        # Serial monitor tab port combo
        if hasattr(self, 'sm_port_combo'):
            current = self.sm_port_var.get()
            self.sm_port_combo['values'] = values
            if current not in values:
                self.sm_port_var.set("Auto")

        # CLI tab port combo
        if hasattr(self, 'cli_port_combo'):
            current = self.cli_port_var.get()
            self.cli_port_combo['values'] = values
            if current not in values:
                self.cli_port_var.set("Auto")

    def _linux_disable_usb_autosuspend(self, port: str):
        """On Linux, disable USB autosuspend for the device behind the serial port.
        Returns (autosuspend_path, old_value) if successful, else (None, None).
        Call _linux_restore_usb_autosuspend with the result when disconnecting.
        """
        if not sys.platform.startswith('linux'):
            return None, None
        basename = os.path.basename(port)
        if not (basename.startswith('ttyUSB') or basename.startswith('ttyACM')):
            return None, None
        device_path = f'/sys/class/tty/{basename}/device'
        if not os.path.exists(device_path):
            return None, None
        path = os.path.realpath(device_path)
        while path and path != '/':
            autosuspend = os.path.join(path, 'power', 'autosuspend')
            if os.path.exists(autosuspend):
                try:
                    with open(autosuspend, 'r') as f:
                        old = f.read().strip()
                    with open(autosuspend, 'w') as f:
                        f.write('-1')
                    return autosuspend, old
                except PermissionError:
                    # Writing to sysfs usually requires root; user can run with sudo or add udev rules
                    return None, None
                except (OSError, IOError):
                    return None, None
            path = os.path.dirname(path)
        return None, None

    def _linux_restore_usb_autosuspend(self, autosuspend_path: str, old_value: str):
        """Restore the previous USB autosuspend value when disconnecting."""
        if not autosuspend_path or old_value is None or not sys.platform.startswith('linux'):
            return
        try:
            with open(autosuspend_path, 'w') as f:
                f.write(old_value)
        except (OSError, IOError):
            pass

    def _scan_serial_ports(self):
        """Return a list of available serial port names."""
        ports = []
        try:
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
        except ImportError:
            # Fallback: scan common paths
            if sys.platform.startswith('linux') or sys.platform == 'darwin':
                import glob
                candidates = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/cu.*')
                ports = sorted(candidates)
            elif sys.platform == 'win32':
                import winreg
                try:
                    reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                         r'HARDWARE\DEVICEMAP\SERIALCOMM')
                    i = 0
                    while True:
                        try:
                            ports.append(winreg.EnumValue(reg, i)[1])
                            i += 1
                        except OSError:
                            break
                except Exception:
                    pass
        except Exception:
            pass
        return ports

    def start_serial_monitor(self):
        """Start the serial monitor using pyserial directly (no pio subprocess)."""
        if self.serial_monitor_running:
            return

        import serial as _serial

        port = self.sm_port_var.get()
        baud = int(self.sm_baud_var.get())

        if port == "Auto":
            detected = self._scan_serial_ports()
            if not detected:
                self._sm_append("⚠ No serial port detected. Connect a device and click Refresh Ports.\n")
                return
            port = detected[0]
            self._sm_append(f"ℹ Auto-selected port: {port}\n")

        self._sm_append(f"\n▶ Opening {port} at {baud} baud...\n")

        # On Linux, disable USB autosuspend to prevent connection drops
        self._sm_usb_autosuspend_path, self._sm_usb_autosuspend_old = self._linux_disable_usb_autosuspend(port)
        if self._sm_usb_autosuspend_path:
            self._sm_append("ℹ Disabled USB autosuspend (Linux) to prevent connection drops.\n")

        try:
            self.serial_monitor_process = _serial.Serial(port, baud, timeout=0.1)
        except Exception as e:
            self._linux_restore_usb_autosuspend(self._sm_usb_autosuspend_path, self._sm_usb_autosuspend_old)
            self._sm_usb_autosuspend_path = None
            self._sm_usb_autosuspend_old = None
            self._sm_append(f"✗ Could not open {port}: {e}\n")
            return

        self.serial_monitor_running = True
        self.sm_status_var.set(f"Running  {port}")

        thread = threading.Thread(target=self._sm_reader_thread, daemon=True)
        thread.start()

    def _sm_reader_thread(self):
        """Background thread — reads bytes from the open serial port."""
        buf = b""
        ser = self.serial_monitor_process
        try:
            while self.serial_monitor_running and ser and ser.is_open:
                chunk = ser.read(256)
                if chunk:
                    buf += chunk
                    # Flush complete lines; keep partial line in buffer
                    while b'\n' in buf:
                        line, buf = buf.split(b'\n', 1)
                        text = line.decode('utf-8', errors='replace').rstrip('\r') + '\n'
                        self.root.after(0, lambda t=text: self._sm_append(t))
        except Exception:
            pass
        self.root.after(0, self._sm_on_stopped)

    def _sm_on_stopped(self):
        """Called when the reader thread exits — auto-restart after a short delay."""
        self.serial_monitor_running = False
        self._linux_restore_usb_autosuspend(
            getattr(self, '_sm_usb_autosuspend_path', None),
            getattr(self, '_sm_usb_autosuspend_old', None))
        self._sm_usb_autosuspend_path = None
        self._sm_usb_autosuspend_old = None
        if self._sm_shutting_down:
            return
        self.sm_status_var.set("Reconnecting…")
        self._sm_append("⚠ Monitor stopped — reconnecting in 3 s...\n")
        self.root.after(3000, self._sm_auto_restart)

    def _sm_auto_restart(self):
        """Restart the monitor if not already running (called after a disconnect)."""
        if not self._sm_shutting_down and not self.serial_monitor_running:
            self.start_serial_monitor()

    def _sm_restart(self):
        """Stop and immediately restart — used when port/baud changes."""
        self.stop_serial_monitor()
        self.root.after(500, self.start_serial_monitor)

    def stop_serial_monitor(self):
        """Close the serial port and stop the monitor (without auto-restart)."""
        self.serial_monitor_running = False
        self._linux_restore_usb_autosuspend(
            getattr(self, '_sm_usb_autosuspend_path', None),
            getattr(self, '_sm_usb_autosuspend_old', None))
        self._sm_usb_autosuspend_path = None
        self._sm_usb_autosuspend_old = None
        if self.serial_monitor_process:
            try:
                self.serial_monitor_process.close()
            except Exception:
                pass
            self.serial_monitor_process = None
        self.sm_status_var.set("Stopped")

    def clear_serial_monitor(self):
        """Clear the serial monitor output area."""
        self.sm_output.config(state='normal')
        self.sm_output.delete('1.0', tk.END)
        self.sm_output.config(state='disabled')

    def _sm_append(self, text):
        """Append text to the serial monitor output (must run on main thread)."""
        self.sm_output.config(state='normal')
        self.sm_output.insert(tk.END, text)
        self.sm_output.see(tk.END)
        self.sm_output.config(state='disabled')

    # ──────────────────────────────────────────────────────────────────────────
    # Pre-built binary flash
    # ──────────────────────────────────────────────────────────────────────────

    def browse_prebuilt_bin(self):
        """Let the user pick a pre-compiled .bin file."""
        path = filedialog.askopenfilename(
            title="Select Pre-built Firmware Binary",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if not path:
            return
        self.prebuilt_bin_path = path
        self.prebuilt_bin_var.set(os.path.basename(path))

    def flash_prebuilt_bin(self):
        """Flash the selected .bin file directly via esptool (no compile required)."""
        if not self.prebuilt_bin_path or not os.path.exists(self.prebuilt_bin_path):
            messagebox.showwarning("No File", "Please browse and select a .bin file first.")
            return

        port = self.serial_port_var.get()
        if port == "Auto":
            # Try to auto-detect
            detected = self._scan_serial_ports()
            if not detected:
                messagebox.showwarning(
                    "No Port",
                    "No serial port detected automatically.\n"
                    "Please select a port from the Serial Port dropdown."
                )
                return
            port = detected[0]
            self.log(f"Auto-detected port: {port}")

        confirm = messagebox.askyesno(
            "Confirm Flash",
            f"Flash {os.path.basename(self.prebuilt_bin_path)}\n"
            f"to port {port}?\n\n"
            "Make sure the device is connected and in flash mode.\n\n"
            "Continue?",
            icon='warning'
        )
        if not confirm:
            return

        self.flash_prebuilt_btn.config(state='disabled')
        self.status_var.set("Flashing pre-built binary…")
        self.log(f"\n{'='*60}")
        self.log(f"FLASHING PRE-BUILT BINARY")
        self.log(f"File : {self.prebuilt_bin_path}")
        self.log(f"Port : {port}")
        self.log(f"{'='*60}")

        thread = threading.Thread(
            target=self._flash_prebuilt_thread,
            args=(self.prebuilt_bin_path, port),
            daemon=True
        )
        thread.start()

    def _flash_prebuilt_thread(self, bin_path, port):
        """Background thread: run esptool to flash the binary."""
        try:
            # Use esptool via Python module (ships with PlatformIO)
            cmd = [
                sys.executable, '-m', 'esptool',
                '--port', port,
                '--baud', '921600',
                'write_flash',
                '0x10000',   # standard ESP32 app partition offset
                bin_path
            ]
            self.log(f"Command: {' '.join(cmd)}\n")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                self.log(line.rstrip())
            process.wait()

            if process.returncode == 0:
                self.log(f"\n✓ FLASHING SUCCESSFUL!")
                self.root.after(0, lambda: self.status_var.set("Pre-built binary flashed successfully!"))
                messagebox.showinfo("Success", "Firmware flashed successfully!")
            else:
                self.log(f"\n✗ FLASHING FAILED (exit code {process.returncode})")
                self.log("Tip: Try pressing the BOOT button on the device before flashing.")
                self.root.after(0, lambda: self.status_var.set("Flash failed – see log"))
                messagebox.showerror("Flash Failed", "Flashing failed. See log for details.\n\n"
                                     "Tip: Try pressing the BOOT button on the device.")
        except Exception as e:
            self.log(f"\n✗ Error: {e}")
            self.root.after(0, lambda: self.status_var.set("Flash error"))
            messagebox.showerror("Error", f"Flash failed:\n{e}")
        finally:
            self.root.after(0, lambda: self.flash_prebuilt_btn.config(state='normal'))

    def on_closing(self):
        """Handle window closing"""
        # Save settings before exit (checkbox states, last devices, storage root, etc.)
        try:
            self.save_storage_settings()
        except Exception:
            pass
        
        # Stop serial monitor if running (set flag first to prevent auto-restart)
        self._sm_shutting_down = True
        self.stop_serial_monitor()

        # Stop OTA server if running
        if self.ota_server:
            self.stop_ota_server()
        
        # Disconnect OTA connection if active
        ota_mc = self.ota_meshcore
        self.ota_meshcore = None
        if ota_mc is not None:
            try:
                import asyncio
                future = asyncio.run_coroutine_threadsafe(
                    ota_mc.disconnect(), self.ota_event_loop
                )
                future.result(timeout=5)
            except Exception:
                pass

        # Stop the shared BLE event loop
        self.ota_event_loop.call_soon_threadsafe(self.ota_event_loop.stop)

        self.root.destroy()


    # ──────────────────────────────────────────────────────────────────────────
    # MeshCore CLI tab
    # ──────────────────────────────────────────────────────────────────────────

    # Per-device-type quick-button definitions.
    # Each entry: (button_label, command_string, tooltip_description)
    _CLI_COMMANDS = {
        "repeater": {
            "Info": [
                ("ver",         "ver",         "Show firmware version and build date"),
                ("clock",       "clock",       "Display current time from the device clock"),
                ("neighbors",   "neighbors",   "List nearby repeater nodes heard via zero-hop adverts (id, timestamp, SNR)"),
                ("advert",      "advert",      "Broadcast an advertisement packet immediately"),
                ("clear stats", "clear stats", "Reset all packet and airtime statistics counters to zero"),
                ("get acl",     "get acl",     "Show the Access Control List of authorised nodes"),
            ],
            "Logging": [
                ("log",       "log",       "Stream the full packet log from the file system to the console (serial only)"),
                ("log start", "log start", "Begin recording packets to the on-device log file"),
                ("log stop",  "log stop",  "Stop recording packets to the log file"),
                ("log erase", "log erase", "Delete the stored packet log from the file system"),
            ],
            "Radio": [
                ("get freq",   "get freq",   "Read the current LoRa centre frequency (MHz)"),
                ("get radio",  "get radio",  "Read all radio parameters: frequency, bandwidth, spreading factor, coding rate"),
                ("get tx",     "get tx",     "Read the current TX power setting (dBm)"),
                ("get af",     "get af",     "Read the air-time factor — scales how aggressively the node uses airtime"),
                ("get txdelay","get txdelay","Read the TX delay factor used to reduce flood packet collisions"),
            ],
            "Power": [
                ("powersaving",     "powersaving",     "Show the current power saving mode (on or off)"),
                ("powersaving on",  "powersaving on",  "Enable power saving mode (persisted to preferences). Available from v1.12.0+"),
                ("powersaving off", "powersaving off", "Disable power saving mode (persisted to preferences)"),
            ],
            "Region": [
                ("region",      "region",      "List all defined regions and current flood permissions (serial only)"),
                ("region home", "region home", "Show the current 'home' region assigned to this node"),
                ("region save", "region save", "Persist the current region list and permissions to storage"),
            ],
            "GPS": [
                ("gps",        "gps",        "Show GPS status: on/off, fix status, and satellite count"),
                ("gps on",     "gps on",     "Power on the GPS module"),
                ("gps off",    "gps off",    "Power off the GPS module"),
                ("gps sync",   "gps sync",   "Sync the node clock with the GPS clock"),
                ("gps setloc", "gps setloc", "Set the node's position to the current GPS coordinates and save to preferences"),
            ],
            "Manage": [
                ("reboot",    "reboot",    "Soft-reboot the device (you will see a Timeout response — this is normal)"),
                ("erase FS",  "erase",     "Completely erase the device's local file system. WARNING: all stored data is lost (serial only)"),
                ("start ota", "start ota", "Kick off OTA firmware update — device will create a MeshCore-OTA WiFi hotspot"),
            ],
        },
        "companion": {
            "Info": [
                ("ver",         "ver",         "Show firmware version and build date"),
                ("clock",       "clock",       "Display current time from the device clock"),
                ("advert",      "advert",      "Broadcast an advertisement packet immediately"),
                ("clear stats", "clear stats", "Reset all packet and airtime statistics counters to zero"),
            ],
            "Logging": [
                ("log",       "log",       "Stream the full packet log to the console (serial only)"),
                ("log start", "log start", "Begin recording packets to the on-device log file"),
                ("log stop",  "log stop",  "Stop recording packets to the log file"),
                ("log erase", "log erase", "Delete the stored packet log from the file system"),
            ],
            "Radio": [
                ("get freq",  "get freq",  "Read the current LoRa centre frequency (MHz)"),
                ("get radio", "get radio", "Read all radio parameters: frequency, bandwidth, spreading factor, coding rate"),
                ("get tx",    "get tx",    "Read the current TX power setting (dBm)"),
                ("get af",    "get af",    "Read the air-time factor"),
            ],
            "GPS": [
                ("gps",        "gps",        "Show GPS status: on/off, fix status, and satellite count"),
                ("gps on",     "gps on",     "Power on the GPS module"),
                ("gps off",    "gps off",    "Power off the GPS module"),
                ("gps sync",   "gps sync",   "Sync the node clock with the GPS clock"),
                ("gps setloc", "gps setloc", "Set the node's position to current GPS coordinates and save to preferences"),
            ],
            "Manage": [
                ("reboot",    "reboot",    "Soft-reboot the device"),
                ("erase FS",  "erase",     "Completely erase the device's local file system. WARNING: all stored data is lost (serial only)"),
                ("start ota", "start ota", "Kick off OTA firmware update — device creates a MeshCore-OTA WiFi hotspot"),
            ],
        },
        "room": {
            "Info": [
                ("ver",         "ver",         "Show firmware version and build date"),
                ("clock",       "clock",       "Display current time from the device clock"),
                ("advert",      "advert",      "Broadcast an advertisement packet immediately"),
                ("clear stats", "clear stats", "Reset all packet and airtime statistics counters to zero"),
                ("get acl",     "get acl",     "Show the Access Control List of authorised nodes"),
            ],
            "Logging": [
                ("log",       "log",       "Stream the full packet log to the console (serial only)"),
                ("log start", "log start", "Begin recording packets to the on-device log file"),
                ("log stop",  "log stop",  "Stop recording packets to the log file"),
                ("log erase", "log erase", "Delete the stored packet log from the file system"),
            ],
            "Radio": [
                ("get freq",  "get freq",  "Read the current LoRa centre frequency (MHz)"),
                ("get radio", "get radio", "Read all radio parameters: frequency, bandwidth, spreading factor, coding rate"),
                ("get tx",    "get tx",    "Read the current TX power setting (dBm)"),
                ("get af",    "get af",    "Read the air-time factor"),
            ],
            "Room": [
                ("read only on",  "set allow.read.only on",  "Allow login with blank password for read-only access (cannot post to room)"),
                ("read only off", "set allow.read.only off", "Require authentication to read — disables anonymous read-only access"),
                ("guest pw",      None,                      "Set the guest password — guests can send 'Get Stats' requests"),
            ],
            "Manage": [
                ("reboot",    "reboot",    "Soft-reboot the device"),
                ("erase FS",  "erase",     "Completely erase the device's local file system. WARNING: all stored data is lost (serial only)"),
                ("start ota", "start ota", "Kick off OTA firmware update — device creates a MeshCore-OTA WiFi hotspot"),
            ],
        },
    }

    @staticmethod
    def _attach_tooltip(widget, text: str):
        """Show a small tooltip popup when the mouse hovers over *widget*."""
        tip_win = [None]

        def show(event=None):
            if tip_win[0] or not text:
                return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.attributes('-topmost', True)
            lbl = tk.Label(tw, text=text, justify='left',
                           background='#ffffe0', relief='solid', borderwidth=1,
                           font=('Arial', 8), wraplength=320, padx=4, pady=3)
            lbl.pack()
            tip_win[0] = tw

        def hide(event=None):
            if tip_win[0]:
                tip_win[0].destroy()
                tip_win[0] = None

        widget.bind('<Enter>', show)
        widget.bind('<Leave>', hide)
        widget.bind('<ButtonPress>', hide)

    def setup_cli_tab(self):
        """Build the MeshCore CLI tab."""
        f = self.cli_tab
        f.columnconfigure(0, weight=1)
        f.rowconfigure(4, weight=1)   # terminal expands

        # ── Title row ───────────────────────────────────────────────────────
        title_f = ttk.Frame(f)
        title_f.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 6))
        title_f.columnconfigure(1, weight=1)
        ttk.Label(title_f, text="⌨️ MeshCore CLI",
                  font=('Arial', 14, 'bold')).grid(row=0, column=0, sticky=tk.W)
        self.cli_status_var = tk.StringVar(value="Disconnected")
        ttk.Label(title_f, textvariable=self.cli_status_var,
                  font=('Arial', 9), foreground='gray').grid(row=0, column=2, sticky=tk.E)

        # ── Connection controls ──────────────────────────────────────────────
        conn_f = ttk.LabelFrame(f, text="Serial Connection", padding="6")
        conn_f.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 6))

        ttk.Label(conn_f, text="Port:").grid(row=0, column=0, padx=(0, 4), sticky=tk.W)
        self.cli_port_var = tk.StringVar(value="Auto")
        ports = ["Auto"] + self._scan_serial_ports()
        self.cli_port_combo = ttk.Combobox(conn_f, textvariable=self.cli_port_var,
                                           values=ports, state='readonly', width=18)
        self.cli_port_combo.grid(row=0, column=1, padx=(0, 8))

        ttk.Label(conn_f, text="Baud:").grid(row=0, column=2, padx=(0, 4), sticky=tk.W)
        self.cli_baud_var = tk.StringVar(value="115200")
        ttk.Combobox(conn_f, textvariable=self.cli_baud_var,
                     values=["9600", "38400", "57600", "115200", "230400", "921600"],
                     state='readonly', width=9).grid(row=0, column=3, padx=(0, 8))

        self.cli_connect_btn = ttk.Button(conn_f, text="🔌 Connect", width=12,
                                          command=self.cli_connect)
        self.cli_connect_btn.grid(row=0, column=4, padx=(0, 4))
        self.cli_disconnect_btn = ttk.Button(conn_f, text="⏏ Disconnect", width=12,
                                             command=self.cli_disconnect, state='disabled')
        self.cli_disconnect_btn.grid(row=0, column=5, padx=(0, 8))
        ttk.Button(conn_f, text="🔄 Ports", width=9,
                   command=self.refresh_serial_ports_combo).grid(row=0, column=6, padx=(0, 8))

        ttk.Label(conn_f, text="Device type:").grid(row=0, column=7, padx=(8, 4), sticky=tk.W)
        self.cli_device_type_var = tk.StringVar(value="repeater")
        for col, (label, val) in enumerate([("Repeater", "repeater"),
                                             ("Companion", "companion"),
                                             ("Room Server", "room")], start=8):
            ttk.Radiobutton(conn_f, text=label, variable=self.cli_device_type_var,
                            value=val,
                            command=self._cli_rebuild_quick_buttons).grid(
                row=0, column=col, padx=4)

        # ── Set Radio panel ───────────────────────────────────────────────────
        radio_f = ttk.LabelFrame(f, text="Set Radio", padding="6")
        radio_f.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 6))
        radio_f.columnconfigure(1, weight=1)
        ttk.Label(radio_f, text="Freq (MHz):").grid(row=0, column=0, padx=(0, 4), sticky=tk.W)
        self.cli_set_radio_freq_var = tk.StringVar(value="915.8")
        ttk.Entry(radio_f, textvariable=self.cli_set_radio_freq_var, width=8).grid(row=0, column=1, padx=(0, 8), sticky=tk.W)
        ttk.Label(radio_f, text="BW (kHz):").grid(row=0, column=2, padx=(8, 4), sticky=tk.W)
        self.cli_set_radio_bw_var = tk.StringVar(value="125")
        ttk.Entry(radio_f, textvariable=self.cli_set_radio_bw_var, width=6).grid(row=0, column=3, padx=(0, 8), sticky=tk.W)
        ttk.Label(radio_f, text="SF:").grid(row=0, column=4, padx=(0, 4), sticky=tk.W)
        self.cli_set_radio_sf_var = tk.StringVar(value="11")
        ttk.Entry(radio_f, textvariable=self.cli_set_radio_sf_var, width=4).grid(row=0, column=5, padx=(0, 8), sticky=tk.W)
        ttk.Label(radio_f, text="CR:").grid(row=0, column=6, padx=(0, 4), sticky=tk.W)
        self.cli_set_radio_cr_var = tk.StringVar(value="5")
        ttk.Entry(radio_f, textvariable=self.cli_set_radio_cr_var, width=4).grid(row=0, column=7, padx=(0, 8), sticky=tk.W)
        ttk.Button(radio_f, text="Get Radio", width=10,
                   command=self._cli_get_radio).grid(row=0, column=8, padx=(8, 4))
        ttk.Button(radio_f, text="Set Radio", width=10,
                   command=self._cli_set_radio).grid(row=0, column=9, padx=(0, 0))

        ttk.Label(radio_f, text="Name:").grid(row=1, column=0, padx=(0, 4), pady=(6, 0), sticky=tk.W)
        self.cli_set_name_var = tk.StringVar(value="")
        ttk.Entry(radio_f, textvariable=self.cli_set_name_var, width=24).grid(row=1, column=1, columnspan=7, padx=(0, 8), pady=(6, 0), sticky=(tk.W, tk.E))
        ttk.Button(radio_f, text="Get Name", width=10,
                   command=self._cli_get_name).grid(row=1, column=8, padx=(8, 4), pady=(6, 0))
        ttk.Button(radio_f, text="Set Name", width=10,
                   command=self._cli_set_name).grid(row=1, column=9, padx=(0, 0), pady=(6, 0))

        # ── Quick buttons panel (collapsible groups in a wrapping grid) ─────────
        self.cli_quick_frame = ttk.LabelFrame(f, text="Quick Commands", padding="6")
        self.cli_quick_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 6))
        # track expanded state per group: {group_name: BooleanVar}
        self._cli_group_expanded = {}
        self._cli_rebuild_quick_buttons()

        # ── Terminal output ──────────────────────────────────────────────────
        term_f = ttk.Frame(f)
        term_f.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        term_f.columnconfigure(0, weight=1)
        term_f.rowconfigure(0, weight=1)

        self.cli_output = tk.Text(term_f, font=('Courier', 9), wrap=tk.WORD,
                                  bg='#1a1a2e', fg='#e0e0ff',
                                  insertbackground='white', state='disabled')
        self.cli_output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        sb = ttk.Scrollbar(term_f, orient="vertical", command=self.cli_output.yview)
        sb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.cli_output['yscrollcommand'] = sb.set

        # Colour tags
        self.cli_output.tag_config('cmd',   foreground='#7ec8e3')   # sent commands
        self.cli_output.tag_config('resp',  foreground='#e0e0ff')   # device responses
        self.cli_output.tag_config('info',  foreground='#a0ffa0')   # app info messages
        self.cli_output.tag_config('error', foreground='#ff7070')   # errors

        # ── Input bar ───────────────────────────────────────────────────────
        input_f = ttk.Frame(f)
        input_f.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(6, 0))
        input_f.columnconfigure(0, weight=1)

        self.cli_input_var = tk.StringVar()
        self.cli_input_entry = ttk.Entry(input_f, textvariable=self.cli_input_var,
                                         font=('Courier', 10))
        self.cli_input_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 6))
        self.cli_input_entry.bind('<Return>',  self._cli_on_enter)
        self.cli_input_entry.bind('<Up>',      self._cli_history_up)
        self.cli_input_entry.bind('<Down>',    self._cli_history_down)

        ttk.Button(input_f, text="Send ↵", width=10,
                   command=self._cli_send_from_entry).grid(row=0, column=1, padx=(0, 4))
        ttk.Button(input_f, text="🗑 Clear", width=9,
                   command=self._cli_clear).grid(row=0, column=2)

    def _cli_get_radio(self):
        """Send get radio and set _cli_pending_get so response populates the form fields."""
        self._cli_pending_get = "radio"
        self._cli_pending_get_buf = []
        self.cli_send_command("get radio")

    def _cli_get_name(self):
        """Send get name and set _cli_pending_get so response populates the form fields."""
        self._cli_pending_get = "name"
        self._cli_pending_get_buf = []
        self.cli_send_command("get name")

    def _cli_set_radio(self):
        """Send 'set radio freq,bw,sf,cr' with the current form values."""
        freq = self.cli_set_radio_freq_var.get().strip()
        bw = self.cli_set_radio_bw_var.get().strip()
        sf = self.cli_set_radio_sf_var.get().strip()
        cr = self.cli_set_radio_cr_var.get().strip()
        if freq and bw and sf and cr:
            self.cli_send_command(f"set radio {freq},{bw},{sf},{cr}")

    def _cli_set_name(self):
        """Send 'set name {name}' — sets the advertisement name broadcast by the device."""
        name = self.cli_set_name_var.get().strip()
        if name:
            self.cli_send_command(f"set name {name}")

    def _cli_rebuild_quick_buttons(self):
        """Destroy and rebuild quick-button groups for the current device type.

        Each group is a collapsible row: a toggle button header + a button panel
        that shows/hides. Groups are arranged GROUPS_PER_ROW across the frame.
        """
        for w in self.cli_quick_btn_widgets:
            w.destroy()
        self.cli_quick_btn_widgets.clear()

        device_type = self.cli_device_type_var.get()
        groups = self._CLI_COMMANDS.get(device_type, {})

        BTNS_PER_ROW  = 4   # command buttons per row inside an expanded group
        GROUPS_PER_ROW = 4  # group columns across the quick-commands frame

        for gc, (group_name, cmds) in enumerate(groups.items()):
            grow = gc // GROUPS_PER_ROW
            gcol = gc %  GROUPS_PER_ROW

            # Preserve expanded state across rebuilds (default: collapsed)
            if group_name not in self._cli_group_expanded:
                self._cli_group_expanded[group_name] = tk.BooleanVar(value=False)
            expanded_var = self._cli_group_expanded[group_name]

            # Outer container for this group
            outer = ttk.Frame(self.cli_quick_frame)
            outer.grid(row=grow, column=gcol, padx=(0, 8), pady=(0, 4),
                       sticky=(tk.N, tk.W))
            self.cli_quick_btn_widgets.append(outer)

            # Inner panel that holds the command buttons (toggled show/hide)
            btn_panel = ttk.Frame(outer, relief='groove', borderwidth=1, padding=3)

            def _make_toggle(panel, var, header_btn, name):
                def toggle():
                    if var.get():
                        panel.grid()
                        header_btn.config(text=f"▾ {name}")
                    else:
                        panel.grid_remove()
                        header_btn.config(text=f"▸ {name}")
                return toggle

            arrow = "▾" if expanded_var.get() else "▸"
            header = ttk.Button(outer, text=f"{arrow} {group_name}",
                                style='Toolbutton')
            header.grid(row=0, column=0, sticky=(tk.W, tk.E))
            self.cli_quick_btn_widgets.append(header)

            toggle_fn = _make_toggle(btn_panel, expanded_var, header, group_name)

            def _cmd_toggle(fn=toggle_fn, var=expanded_var):
                var.set(not var.get())
                fn()

            header.config(command=_cmd_toggle)

            # Command buttons inside the panel
            for i, entry in enumerate(cmds):
                label, cmd = entry[0], entry[1]
                tip   = entry[2] if len(entry) > 2 else ""
                r, c = divmod(i, BTNS_PER_ROW)
                if cmd is None:
                    b = ttk.Button(btn_panel, text=label,
                                   command=lambda lbl=label: self._cli_prompt_command(lbl))
                else:
                    b = ttk.Button(btn_panel, text=label,
                                   command=lambda c=cmd: self.cli_send_command(c))
                b.grid(row=r, column=c, padx=2, pady=2, sticky=(tk.W, tk.E))
                if tip:
                    self._attach_tooltip(b, f"{cmd or label}\n\n{tip}")
                self.cli_quick_btn_widgets.append(b)

            btn_panel.grid(row=1, column=0, sticky=(tk.W, tk.E))
            if not expanded_var.get():
                btn_panel.grid_remove()

    def cli_connect(self):
        """Open serial connection to the selected port.

        If the Serial Monitor is already holding the same port open, pause it
        first so the CLI can take exclusive access.
        """
        import serial as _serial
        port = self.cli_port_var.get()
        baud = int(self.cli_baud_var.get())

        if port == "Auto":
            detected = self._scan_serial_ports()
            if not detected:
                self._cli_append("✗ No serial port detected. Connect a device and click Refresh Ports.\n", 'error')
                return
            port = detected[0]
            self._cli_append(f"ℹ Auto-selected port: {port}\n", 'info')

        # Pause the Serial Monitor if it holds this port so we can open it
        sm_was_running = self.serial_monitor_running
        sm_port = self.sm_port_var.get()
        if sm_was_running and (sm_port == port or sm_port == "Auto"):
            self._cli_append("ℹ Pausing Serial Monitor while CLI is connected...\n", 'info')
            self._sm_shutting_down = True   # prevent auto-restart
            self.stop_serial_monitor()
            self._sm_shutting_down = False
        else:
            sm_was_running = False
        self._cli_sm_was_running = sm_was_running  # remember so we can resume on disconnect

        # On Linux, disable USB autosuspend to prevent connection drops
        self._cli_usb_autosuspend_path, self._cli_usb_autosuspend_old = self._linux_disable_usb_autosuspend(port)
        if self._cli_usb_autosuspend_path:
            self._cli_append("ℹ Disabled USB autosuspend (Linux) to prevent connection drops.\n", 'info')

        try:
            self.cli_serial = _serial.Serial(port, baud, timeout=0.1)
        except Exception as e:
            self._linux_restore_usb_autosuspend(self._cli_usb_autosuspend_path, self._cli_usb_autosuspend_old)
            self._cli_usb_autosuspend_path = None
            self._cli_usb_autosuspend_old = None
            self._cli_append(f"✗ Could not open {port}: {e}\n", 'error')
            # Resume monitor if we paused it
            if sm_was_running:
                self.root.after(500, self.start_serial_monitor)
            return

        self.cli_running = True
        self._cli_mode_active = False
        self.cli_connect_btn.config(state='disabled')
        self.cli_disconnect_btn.config(state='normal')
        self.cli_status_var.set(f"Connected  {port} @ {baud}")
        self._cli_append(f"✓ Connected to {port} at {baud} baud\n", 'info')
        self._cli_append(
            "ℹ To enter CLI mode: usually hold the BOOT button on the device, power on.\n"
            "  You should see a '>' prompt appear when CLI mode is active.\n",
            'info')

        threading.Thread(target=self._cli_reader_thread, daemon=True).start()

    def cli_disconnect(self):
        """Close the serial connection and resume the Serial Monitor if it was paused."""
        self.cli_running = False
        self._cli_mode_active = False
        self._cli_pending_get = None
        self._cli_pending_get_buf = []
        self._cli_cancel_no_response_timer()
        self._linux_restore_usb_autosuspend(
            getattr(self, '_cli_usb_autosuspend_path', None),
            getattr(self, '_cli_usb_autosuspend_old', None))
        self._cli_usb_autosuspend_path = None
        self._cli_usb_autosuspend_old = None
        if self.cli_serial:
            try:
                self.cli_serial.close()
            except Exception:
                pass
            self.cli_serial = None
        self.cli_connect_btn.config(state='normal')
        self.cli_disconnect_btn.config(state='disabled')
        self.cli_status_var.set("Disconnected")
        self._cli_append("⏏ Disconnected.\n", 'info')

        # Resume Serial Monitor if we paused it
        if getattr(self, '_cli_sm_was_running', False):
            self._cli_sm_was_running = False
            self._cli_append("ℹ Resuming Serial Monitor...\n", 'info')
            self.root.after(500, self.start_serial_monitor)

    def _cli_reader_thread(self):
        """Background thread — reads lines from the serial port."""
        buf = b""
        while self.cli_running and self.cli_serial and self.cli_serial.is_open:
            try:
                chunk = self.cli_serial.read(256)
                if chunk:
                    buf += chunk
                    # Flush complete lines
                    while b'\n' in buf:
                        line, buf = buf.split(b'\n', 1)
                        text = line.decode('utf-8', errors='replace').rstrip('\r') + '\n'
                        self.root.after(0, lambda t=text: self._cli_on_response(t))
                    # Also handle bare '>' prompt (no newline)
                    if buf.strip() == b'>':
                        text = buf.decode('utf-8', errors='replace')
                        buf = b""
                        self.root.after(0, lambda t=text: self._cli_on_response(t))
            except Exception:
                break
        self.root.after(0, self._cli_on_disconnected)

    def _cli_on_disconnected(self):
        """Called on main thread when the reader thread exits unexpectedly."""
        self._linux_restore_usb_autosuspend(
            getattr(self, '_cli_usb_autosuspend_path', None),
            getattr(self, '_cli_usb_autosuspend_old', None))
        self._cli_usb_autosuspend_path = None
        self._cli_usb_autosuspend_old = None
        if self.cli_running:   # wasn't a deliberate disconnect
            self.cli_running = False
            self._cli_mode_active = False
            self._cli_pending_get = None
            self._cli_pending_get_buf = []
            self._cli_cancel_no_response_timer()
            self.cli_connect_btn.config(state='normal')
            self.cli_disconnect_btn.config(state='disabled')
            self.cli_status_var.set("Disconnected")
            # Resume Serial Monitor if it was paused for us
            if getattr(self, '_cli_sm_was_running', False):
                self._cli_sm_was_running = False
                self._cli_append("ℹ Resuming Serial Monitor...\n", 'info')
                self.root.after(500, self.start_serial_monitor)
            self._cli_append("⚠ Serial connection lost.\n", 'error')

    def cli_send_command(self, cmd: str):
        """Send a command string to the device over serial."""
        if not self.cli_serial or not self.cli_serial.is_open:
            self._cli_append("✗ Not connected. Click Connect first.\n", 'error')
            return
        try:
            self.cli_serial.write((cmd + '\r\n').encode('utf-8'))
            self._cli_append(f"> {cmd}\n", 'cmd')
            # Add to history (avoid consecutive duplicates)
            if not self.cli_cmd_history or self.cli_cmd_history[-1] != cmd:
                self.cli_cmd_history.append(cmd)
            self.cli_history_idx = len(self.cli_cmd_history)
            # Start a no-response watchdog — cancelled if any data arrives
            self._cli_cancel_no_response_timer()
            self._cli_no_response_id = self.root.after(3000, self._cli_no_response_hint)
        except Exception as e:
            self._cli_append(f"✗ Send error: {e}\n", 'error')


    def _cli_no_response_hint(self):
        """Called when a command got no reply within 3 seconds."""
        self._cli_no_response_id = None
        if not self._cli_mode_active:
            self._cli_append(
                "⚠ No response received.\n"
                "  The device may not be in CLI mode yet.\n"
                "  → Usually hold the BOOT button on the device, power on.\n"
                "  → Resend your command once you see the '>' prompt.\n"
                "  → The device may have gone into powersaving mode — reset it, run\n"
                "    'powersaving off', then turn powersaving back on before disconnecting if needed.\n"
                "  If still no response, ensure no other tool is holding the serial port.\n",
                'error')
        else:
            self._cli_append(
                "⚠ No response received. The device may be busy, the command may not be\n"
                "  supported, or it may have gone into powersaving mode — reset the device,\n"
                "  run 'powersaving off', then turn powersaving back on before disconnecting if needed.\n",
                'error')

    def _cli_cancel_no_response_timer(self):
        if self._cli_no_response_id is not None:
            try:
                self.root.after_cancel(self._cli_no_response_id)
            except Exception:
                pass
            self._cli_no_response_id = None

    def _cli_on_response(self, text: str):
        """Called on the main thread whenever data arrives from the device."""
        # Any incoming data cancels the no-response watchdog
        self._cli_cancel_no_response_timer()
        # Parse pending get responses and update form fields
        if self._cli_pending_get:
            line = text.strip()
            self._cli_pending_get_buf.append(line)
            if self._cli_pending_get == "radio":
                # Match freq,bw,sf,cr: comma-separated, space-separated, or 4 numbers in buf
                for ln in self._cli_pending_get_buf:
                    m = re.search(r'([\d.]+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', ln)
                    if not m:
                        m = re.search(r'([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)', ln)
                    if m:
                        self.cli_set_radio_freq_var.set(m.group(1))
                        self.cli_set_radio_bw_var.set(m.group(2))
                        self.cli_set_radio_sf_var.set(m.group(3))
                        self.cli_set_radio_cr_var.set(m.group(4))
                        self._cli_pending_get = None
                        self._cli_pending_get_buf = []
                        break
            elif self._cli_pending_get == "name":
                # Name: first non-empty line that's not a prompt or command echo
                for ln in self._cli_pending_get_buf:
                    skip = not ln or ln in (">", "> ") or ln.startswith("get name") or ln == "get name"
                    if not skip:
                        name = ln.lstrip("-> ").lstrip("> ").strip()
                        if name and not re.match(r'^[\d.,\s]+$', name):
                            self.cli_set_name_var.set(name)
                            self._cli_pending_get = None
                            self._cli_pending_get_buf = []
                            break
            # Clear when we see the prompt (response complete)
            if line in ('>', '> ') or (len(line) == 1 and line == '>'):
                self._cli_pending_get = None
                self._cli_pending_get_buf = []
        # Detect '>' prompt — CLI mode is confirmed active
        if '>' in text and not self._cli_mode_active:
            self._cli_mode_active = True
            self.cli_status_var.set(
                self.cli_status_var.get().replace("Connected", "CLI Active ✓"))
            self._cli_append("✓ CLI prompt detected — device is in CLI mode.\n", 'info')
        self._cli_append(text, 'resp')

    def _cli_send_from_entry(self):
        cmd = self.cli_input_var.get().strip()
        if not cmd:
            return
        self.cli_input_var.set("")
        self.cli_send_command(cmd)

    def _cli_on_enter(self, event=None):
        self._cli_send_from_entry()

    def _cli_history_up(self, event=None):
        if not self.cli_cmd_history:
            return
        self.cli_history_idx = max(0, self.cli_history_idx - 1)
        self.cli_input_var.set(self.cli_cmd_history[self.cli_history_idx])
        self.cli_input_entry.icursor(tk.END)

    def _cli_history_down(self, event=None):
        if not self.cli_cmd_history:
            return
        self.cli_history_idx = min(len(self.cli_cmd_history), self.cli_history_idx + 1)
        if self.cli_history_idx == len(self.cli_cmd_history):
            self.cli_input_var.set("")
        else:
            self.cli_input_var.set(self.cli_cmd_history[self.cli_history_idx])
        self.cli_input_entry.icursor(tk.END)

    def _cli_prompt_command(self, label: str):
        """For commands that need a parameter — open a small input dialog."""
        from tkinter import simpledialog
        prompts = {
            "guest pw": ("Set Guest Password", "set guest.password {password}", "Enter new guest password:"),
        }
        title, template, prompt_text = prompts.get(label, (label, label, f"Enter value for '{label}':"))
        value = simpledialog.askstring(title, prompt_text, parent=self.root)
        if value is None:
            return
        cmd = template.replace("{password}", value)
        self.cli_send_command(cmd)

    def _cli_append(self, text: str, tag: str = 'resp'):
        """Append coloured text to the CLI terminal (must run on main thread)."""
        self.cli_output.config(state='normal')
        self.cli_output.insert(tk.END, text, tag)
        self.cli_output.see(tk.END)
        self.cli_output.config(state='disabled')

    def _cli_clear(self):
        self.cli_output.config(state='normal')
        self.cli_output.delete('1.0', tk.END)
        self.cli_output.config(state='disabled')


def main():
    root = tk.Tk()
    
    # Set theme
    style = ttk.Style()
    available_themes = style.theme_names()
    if 'clam' in available_themes:
        style.theme_use('clam')
    
    app = MeshCoreBLEFlasher(root)
    
    # Force window to be visible
    try:
        root.deiconify()
        root.lift()
        root.attributes('-topmost', True)
        root.update()
        root.attributes('-topmost', False)
        root.focus_force()
        root.update()
    except Exception as e:
        print(f"Warning: Could not force window visibility: {e}")
    
    root.mainloop()


if __name__ == "__main__":
    main()

