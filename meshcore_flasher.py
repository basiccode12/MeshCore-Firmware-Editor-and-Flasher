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

# GitHub repository URLs
GITHUB_API_BASE = "https://api.github.com/repos/meshcore-dev/MeshCore"
GITHUB_BRANCHES_URL = f"{GITHUB_API_BASE}/branches"
GITHUB_TAGS_URL = f"{GITHUB_API_BASE}/tags"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/meshcore-dev/MeshCore/{ref}/examples/{firmware_type}/main.cpp"
MESHCORE_FIRMWARE_REPO_URL = "https://github.com/meshcore-dev/MeshCore.git"


class MeshCoreBLEFlasher:
    def __init__(self, root):
        self.root = root
        self.root.title("Meshcore Firmware Editor and Flasher")
        # Set window size to better fit content (width x height)
        self.root.geometry("1000x800")
        self.root.resizable(True, True)
        
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # State variables
        # Separate file paths and content for each firmware type
        self.file_paths = {
            "companion_radio": None,
            "simple_repeater": None
        }
        self.original_contents = {
            "companion_radio": None,
            "simple_repeater": None
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
        self.selected_version = "main"  # Default to main branch
        self.available_versions = []  # Will be populated with branches and tags
        self.firmware_type = "companion_radio"  # Default to companion_radio (maps to examples/companion_radio)
        
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
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Meshcore Firmware Editor and Flasher",
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create tabs
        self.firmware_tab = ttk.Frame(self.notebook, padding="10")
        self.settings_tab = ttk.Frame(self.notebook, padding="10")
        self.cpp_editor_tab = ttk.Frame(self.notebook, padding="10")
        
        self.notebook.add(self.firmware_tab, text="📦 Firmware")
        self.notebook.add(self.cpp_editor_tab, text="📝 Edit C++")
        self.notebook.add(self.settings_tab, text="⚙️ Settings")
        
        # Setup firmware tab
        self.setup_firmware_tab()
        
        # Setup C++ editor tab
        self.setup_cpp_editor_tab()
        
        # Setup settings tab
        self.setup_settings_tab()
        
        # Log output (shared across tabs)
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="10")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=100,
                                                   font=('Courier', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_firmware_tab(self):
        """Setup the firmware tab"""
        firmware_frame = self.firmware_tab
        firmware_frame.columnconfigure(0, weight=1)
        firmware_frame.columnconfigure(1, weight=1)
        firmware_frame.rowconfigure(2, weight=1)
        
        # Step 1: Get Firmware
        step1_frame = ttk.LabelFrame(firmware_frame, text="1. Get Firmware", padding="10")
        step1_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        step1_frame.columnconfigure(1, weight=1)
        
        # Version selection
        version_frame = ttk.Frame(step1_frame)
        version_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        version_frame.columnconfigure(1, weight=1)
        
        ttk.Label(version_frame, text="Firmware Type:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        
        self.firmware_type_var = tk.StringVar()
        self.firmware_type_var.set("Companion Radio")
        firmware_type_combo = ttk.Combobox(version_frame, textvariable=self.firmware_type_var,
                                           values=["Companion Radio", "Repeater Radio"], 
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
        
        ttk.Button(button_frame, text="📁 Load Saved File",
                  command=self.load_saved_file, width=18).grid(row=0, column=2, padx=(0, 5))
        
        self.file_path_var = tk.StringVar()
        self.file_path_var.set("No file loaded")
        ttk.Label(step1_frame, textvariable=self.file_path_var,
                 foreground='blue', font=('Arial', 9)).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Load versions on startup (after firmware type is set)
        self.root.after(500, self.refresh_versions)
        
        # Step 2: BLE Name (Left Column)
        step2_frame = ttk.LabelFrame(firmware_frame, text="2. Set BLE Name", padding="10")
        step2_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 5), pady=(0, 10))
        step2_frame.columnconfigure(1, weight=1)
        
        ttk.Label(step2_frame, text="BLE Name:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        self.ble_name_var = tk.StringVar()
        name_entry = ttk.Entry(step2_frame, textvariable=self.ble_name_var, font=('Arial', 10))
        name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(step2_frame, text="(auto-saved before compile)", 
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Step 3: Device Selection (Right Column)
        step3_frame = ttk.LabelFrame(firmware_frame, text="3. Select Device", padding="10")
        step3_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N), padx=(5, 0), pady=(0, 10))
        step3_frame.columnconfigure(1, weight=1)
        
        ttk.Label(step3_frame, text="Device:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(step3_frame, textvariable=self.device_var,
                                         values=[], state='readonly', width=30)
        self.device_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Step 4: Edit C++ (Optional) (Left Column)
        step4_frame = ttk.LabelFrame(firmware_frame, text="4. Edit C++ (Optional)", padding="10")
        step4_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=(0, 5), pady=(0, 10))
        step4_frame.columnconfigure(0, weight=1)
        
        ttk.Button(step4_frame, text="📝 Open C++ Editor",
                  command=self.go_to_cpp_editor_tab, width=30).grid(row=0, column=0)
        
        ttk.Label(step4_frame, text="Edit source code before compiling", 
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, pady=(5, 0))
        
        # Step 5: Configure PlatformIO (Optional) (Right Column)
        step5_frame = ttk.LabelFrame(firmware_frame, text="5. Configure PlatformIO (Optional)", padding="10")
        step5_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0, 10))
        step5_frame.columnconfigure(0, weight=1)
        
        ttk.Button(step5_frame, text="⚙️ Open Settings",
                  command=self.go_to_settings_tab, width=30).grid(row=0, column=0)
        
        ttk.Label(step5_frame, text="Edit platformio.ini configuration", 
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, pady=(5, 0))
        
        # Step 6: Build & Flash (Full Width)
        step6_frame = ttk.LabelFrame(firmware_frame, text="6. Build & Flash", padding="10")
        step6_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        button_frame = ttk.Frame(step6_frame)
        button_frame.grid(row=0, column=0)
        
        self.compile_btn = ttk.Button(button_frame, text="🔨 Compile",
                                      command=self.compile_firmware, width=15)
        self.compile_btn.grid(row=0, column=0, padx=5)
        
        self.flash_btn = ttk.Button(button_frame, text="⚡ Flash",
                                   command=self.flash_firmware, width=15)
        self.flash_btn.grid(row=0, column=1, padx=5)
        
        # Status
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        ttk.Label(step6_frame, textvariable=self.status_var,
                 font=('Arial', 9), foreground='gray').grid(row=1, column=0, pady=(5, 0))
    
    def setup_cpp_editor_tab(self):
        """Setup the C++ file editor tab"""
        cpp_frame = ttk.Frame(self.cpp_editor_tab)
        cpp_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        cpp_frame.columnconfigure(0, weight=1)
        cpp_frame.rowconfigure(2, weight=1)
        self.cpp_editor_tab.columnconfigure(0, weight=1)
        self.cpp_editor_tab.rowconfigure(0, weight=1)
        
        # Title frame
        title_frame = ttk.Frame(cpp_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        title_frame.columnconfigure(0, weight=1)
        
        title_label = ttk.Label(title_frame, text="C++ Source Code Editor",
                               font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        self.cpp_editor_status_var = tk.StringVar()
        self.cpp_editor_status_var.set("No file loaded")
        ttk.Label(title_frame, textvariable=self.cpp_editor_status_var,
                 font=('Arial', 9), foreground='gray').grid(row=0, column=1, sticky=tk.E)
        
        # Info label
        info_label = ttk.Label(cpp_frame, 
                               text="Edit the main.cpp source code. Changes will be saved to the current firmware file.",
                               font=('Arial', 9), foreground='gray', wraplength=700)
        info_label.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Editor container
        editor_container = ttk.Frame(cpp_frame)
        editor_container.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        editor_container.columnconfigure(0, weight=1)
        editor_container.rowconfigure(2, weight=1)  # Editor frame row
        
        # File path label
        self.cpp_editor_path_var = tk.StringVar()
        self.cpp_editor_path_var.set("No file loaded yet")
        path_label = ttk.Label(editor_container, textvariable=self.cpp_editor_path_var,
                              font=('Courier', 8), foreground='blue')
        path_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Find bar (initially hidden)
        self.cpp_find_bar = ttk.Frame(editor_container)
        self.cpp_find_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        self.cpp_find_bar.columnconfigure(1, weight=1)
        self.cpp_find_bar_visible = False
        self.cpp_find_bar.grid_remove()  # Hide by default
        
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
        
        self.cpp_find_status_var = tk.StringVar()
        self.cpp_find_status_var.set("")
        ttk.Label(self.cpp_find_bar, textvariable=self.cpp_find_status_var,
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=(3, 0))
        
        # Text editor with scrollbars
        editor_frame = ttk.Frame(editor_container)
        editor_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(0, weight=1)
        
        self.cpp_editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.NONE,
                                                               font=('Courier', 10))
        self.cpp_editor.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Button frame
        button_frame = ttk.Frame(cpp_frame)
        button_frame.grid(row=3, column=0, pady=(10, 0))
        
        ttk.Button(button_frame, text="🔍 Find", 
                  command=self.cpp_show_find_bar, width=12).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="🔄 Reload", 
                  command=self.reload_cpp_file, width=15).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="💾 Save", 
                  command=self.save_cpp_file, width=15).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="↩️ Reset to Original", 
                  command=self.reset_cpp_file, width=20).grid(row=0, column=3, padx=5)
        
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
        settings_frame = self.settings_tab
        settings_frame.columnconfigure(0, weight=1)
        settings_frame.rowconfigure(2, weight=1)  # Editor container row
        
        # Title and info
        title_frame = ttk.Frame(settings_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        title_frame.columnconfigure(1, weight=1)
        
        ttk.Label(title_frame, text="PlatformIO Configuration", 
                 font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky=tk.W)
        
        self.platformio_ini_status_var = tk.StringVar()
        self.platformio_ini_status_var.set("No changes made")
        ttk.Label(title_frame, textvariable=self.platformio_ini_status_var,
                 font=('Arial', 9), foreground='gray').grid(row=0, column=1, sticky=tk.E)
        
        # Info label
        info_label = ttk.Label(settings_frame, 
                               text="Edit the platformio.ini file to customize build settings, environments, and other PlatformIO options.",
                               font=('Arial', 9), foreground='gray', wraplength=700)
        info_label.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Editor container
        editor_container = ttk.Frame(settings_frame)
        editor_container.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        editor_container.columnconfigure(0, weight=1)
        editor_container.rowconfigure(2, weight=1)  # Editor frame row
        
        # File path label
        self.platformio_ini_path_var = tk.StringVar()
        self.platformio_ini_path_var.set("Project not loaded yet")
        path_label = ttk.Label(editor_container, textvariable=self.platformio_ini_path_var,
                              font=('Courier', 8), foreground='blue')
        path_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Find bar (initially hidden)
        self.find_bar = ttk.Frame(editor_container)
        self.find_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        self.find_bar.columnconfigure(1, weight=1)
        self.find_bar_visible = False
        self.find_bar.grid_remove()  # Hide by default
        
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
        
        self.find_status_var = tk.StringVar()
        self.find_status_var.set("")
        ttk.Label(self.find_bar, textvariable=self.find_status_var,
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=(3, 0))
        
        # Text editor with scrollbars
        editor_frame = ttk.Frame(editor_container)
        editor_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(0, weight=1)
        
        self.platformio_ini_editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.NONE,
                                                               font=('Courier', 10))
        self.platformio_ini_editor.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Button frame
        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=3, column=0, pady=(10, 0))
        
        ttk.Button(button_frame, text="🔍 Find", 
                  command=self.show_find_bar, width=12).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="🔄 Reload", 
                  command=self.reload_platformio_ini, width=15).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="💾 Save", 
                  command=self.save_platformio_ini, width=15).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="↩️ Reset to Original", 
                  command=self.reset_platformio_ini, width=20).grid(row=0, column=3, padx=5)
        
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
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
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
                    req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
                    with urllib.request.urlopen(req, timeout=10) as response:
                        branches = json.loads(response.read().decode())
                        for branch in branches:
                            branch_name = branch['name']
                            # Check if this branch has the firmware type
                            try:
                                check_url = GITHUB_RAW_URL.format(ref=branch_name, firmware_type=firmware_type)
                                check_req = urllib.request.Request(check_url, method='HEAD')
                                check_req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
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
                    req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
                    with urllib.request.urlopen(req, timeout=10) as response:
                        releases = json.loads(response.read().decode())
                        for release in releases:
                            tag_name = release.get('tag_name', release.get('name', ''))
                            if tag_name:
                                # Check if this tag has the firmware type
                                try:
                                    check_url = GITHUB_RAW_URL.format(ref=tag_name, firmware_type=firmware_type)
                                    check_req = urllib.request.Request(check_url, method='HEAD')
                                    check_req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
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
                        req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
                        with urllib.request.urlopen(req, timeout=10) as response:
                            tags = json.loads(response.read().decode())
                            for tag in tags:
                                tag_name = tag.get('name', '')
                                if tag_name:
                                    # Check if this tag has the firmware type
                                    try:
                                        check_url = GITHUB_RAW_URL.format(ref=tag_name, firmware_type=firmware_type)
                                        check_req = urllib.request.Request(check_url, method='HEAD')
                                        check_req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
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
            if current_tab == 1:  # C++ Editor tab
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
            # Only show repeater environments
            filter_keyword = "repeater"
            exclude_keyword = "companion"
        else:  # companion_radio
            # Only show companion environments
            filter_keyword = "companion"
            exclude_keyword = "repeater"
        
        # Filter devices
        filtered = {}
        for readable_name, env_name in self.all_devices.items():
            env_lower = env_name.lower()
            # Include if it contains the keyword and doesn't contain the exclude keyword
            if filter_keyword in env_lower and exclude_keyword not in env_lower:
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
                req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
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
                    req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
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
                                tag_obj_req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
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
            req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
            
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
            
            # Save to a local file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            download_dir = os.path.dirname(os.path.abspath(__file__))
            version_safe = version_ref.replace('/', '_').replace('\\', '_')
            firmware_type_short = "companion" if self.firmware_type == "companion_radio" else "repeater"
            filename = f"main_{firmware_type_short}_{version_safe}_{timestamp}.cpp"
            file_path = os.path.join(download_dir, filename)
            
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
            self._load_file(filename, is_downloaded=False)
    
    def load_saved_file(self):
        """Load a previously saved firmware file"""
        # Get the current directory (where downloaded files are saved)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Look for saved files in current directory
        filename = filedialog.askopenfilename(
            title="Load Saved Firmware File",
            filetypes=[
                ("C++ files", "*.cpp"),
                ("All files", "*.*")
            ],
            initialdir=current_dir
        )
        
        if filename:
            self._load_file(filename, is_downloaded=True)
    
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
            if not silent:
                messagebox.showwarning("No Name", "Please enter a BLE name.")
            return False
        
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
            
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if self.is_downloaded:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                filename = f"main_custom_{ble_name.replace(' ', '_')}_{timestamp}.cpp"
                save_path = os.path.join(base_dir, filename)
            else:
                original_dir = os.path.dirname(self.file_path)
                original_name = os.path.splitext(os.path.basename(self.file_path))[0]
                filename = f"{original_name}_custom_{timestamp}.cpp"
                save_path = os.path.join(original_dir, filename)
            
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
            # Create a temporary directory for the project
            project_dir = tempfile.mkdtemp(prefix="meshcore_")
            self.project_dir = project_dir
            
            if not silent:
                self.log(f"Created project directory: {project_dir}")
                self.log("Cloning MeshCore repository (this may take a minute)...")
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
            self.log("\n" + "="*60)
            self.log(f"COMPILING FIRMWARE FOR {device_name.upper()}")
            self.log("="*60)
            
            # Setup project
            project_dir = self.setup_project()
            if not project_dir:
                return
            
            self.log(f"\nProject directory: {project_dir}")
            self.log(f"Starting compilation for environment: {env_name}")
            
            # Display configuration
            if self.ble_name_var.get().strip():
                self.log(f"\nBLE Name: {self.ble_name_var.get()}")
            
            self.log("\nThis may take several minutes on first run...")
            self.log("")
            
            # Verify platformio.ini exists
            pio_ini = os.path.join(project_dir, "platformio.ini")
            if not os.path.exists(pio_ini):
                raise Exception(f"platformio.ini not found at {pio_ini}")
            
            # Run PlatformIO build
            process = subprocess.Popen(
                ['pio', 'run', '-e', env_name],
                cwd=project_dir,
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
                self.log("✓ COMPILATION SUCCESSFUL!")
                self.log("="*60)
                self.root.after(0, lambda: self.status_var.set("Compilation successful!"))
                messagebox.showinfo("Success", f"Firmware compiled successfully for {device_name}!")
            else:
                self.log("\n" + "="*60)
                self.log("✗ COMPILATION FAILED")
                self.log("="*60)
                self.root.after(0, lambda: self.status_var.set("Compilation failed"))
                messagebox.showerror("Compilation Failed", "See log for details.")
            
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
        
        # Confirm flash operation
        response = messagebox.askyesno(
            "Confirm Flash",
            f"This will flash the firmware to your {device_name}.\n\n"
            "Make sure your device is connected via USB.\n\n"
            "Continue?",
            icon='warning'
        )
        
        if not response:
            return
        
        self.log("\n" + "="*60)
        self.log(f"FLASHING FIRMWARE TO {device_name.upper()}")
        self.log("="*60)
        
        self.flash_btn.config(state='disabled')
        self.status_var.set("Flashing firmware...")
        
        thread = threading.Thread(target=self._flash_thread, args=(env_name, device_name))
        thread.daemon = True
        thread.start()
    
    def _flash_thread(self, env_name, device_name):
        """Background thread for flashing"""
        try:
            self.log("\nUploading firmware to device...")
            self.log("Please don't disconnect the device during flashing!")
            self.log("")
            
            # Run PlatformIO upload
            process = subprocess.Popen(
                ['pio', 'run', '-e', env_name, '--target', 'upload'],
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
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 1:  # C++ Editor tab
            self.load_cpp_file()
        elif selected_tab == 2:  # Settings tab
            self.load_platformio_ini()
    
    def go_to_cpp_editor_tab(self):
        """Navigate to C++ editor tab"""
        self.notebook.select(1)  # Switch to C++ editor tab (index 1)
        # Load C++ file if not already loaded
        if self.cpp_original_content is None:
            self.load_cpp_file()
    
    def go_to_settings_tab(self):
        """Navigate to settings tab"""
        self.notebook.select(2)  # Switch to settings tab (index 2)
        # Load platformio.ini if not already loaded
        if self.platformio_ini_original_content is None:
            self.load_platformio_ini()
    
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
            return
        
        platformio_ini_path = os.path.join(self.project_dir, "platformio.ini")
        self.platformio_ini_path_var.set(platformio_ini_path)
        
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
        
        self.load_platformio_ini()
        self.log("✓ platformio.ini reloaded from disk")
    
    def save_platformio_ini(self):
        """Save platformio.ini to disk"""
        if not self.project_dir or not os.path.exists(self.project_dir):
            messagebox.showerror("Error", "Project not loaded. Cannot save platformio.ini.")
            return
        
        platformio_ini_path = os.path.join(self.project_dir, "platformio.ini")
        
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
            
            self.platformio_ini_original_content = new_content
            self.platformio_ini_modified = False
            self.platformio_ini_status_var.set("✓ Saved")
            self.log(f"✓ platformio.ini saved (backup: {os.path.basename(backup_path)})")
            
            messagebox.showinfo("Success", "platformio.ini saved successfully!")
            
            # Switch back to firmware tab
            self.notebook.select(0)  # Switch to firmware tab (index 0)
            
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
        search_lower = search_text.lower()
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
    
    def save_cpp_file(self):
        """Save C++ file to disk"""
        if not self.file_path:
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
            
            # Update content for current firmware type
            self.cpp_original_content = new_content
            self.original_contents[self.firmware_type] = new_content
            self.original_content = new_content  # Current pointer
            self.cpp_modified = False
            self.cpp_editor_status_var.set("✓ Saved")
            self.log(f"✓ C++ file saved (backup: {os.path.basename(backup_path)})")
            
            messagebox.showinfo("Success", "C++ file saved successfully!")
            
            # Switch back to firmware tab
            self.notebook.select(0)  # Switch to firmware tab (index 0)
            
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
    
    def on_closing(self):
        """Handle window closing"""
        self.root.destroy()


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

