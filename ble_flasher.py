#!/usr/bin/env python3
"""
MeshCore BLE Flasher
A simple GUI tool to change BLE name and flash firmware to MeshCore devices
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
GITHUB_API_URL = "https://api.github.com/repos/meshcore-dev/MeshCore/branches/main"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/meshcore-dev/MeshCore/{commit}/examples/companion_radio/main.cpp"
GITHUB_REPO_URL = "https://github.com/meshcore-dev/MeshCore.git"


class MeshCoreBLEFlasher:
    def __init__(self, root):
        self.root = root
        self.root.title("MeshCore BLE Flasher")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # State variables
        self.file_path = None
        self.original_content = None
        self.is_downloaded = False
        self.project_dir = None
        self.is_compiling = False
        self.platformio_available = False
        self.available_devices = {}
        
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
        main_frame.rowconfigure(5, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="MeshCore BLE Flasher",
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Step 1: Get Firmware
        step1_frame = ttk.LabelFrame(main_frame, text="1. Get Firmware", padding="10")
        step1_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        step1_frame.columnconfigure(1, weight=1)
        
        ttk.Button(step1_frame, text="📥 Download Latest",
                  command=self.download_firmware, width=20).grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(step1_frame, text="📂 Browse Local File",
                  command=self.browse_file, width=20).grid(row=0, column=1, padx=(0, 10))
        
        self.file_path_var = tk.StringVar()
        self.file_path_var.set("No file loaded")
        ttk.Label(step1_frame, textvariable=self.file_path_var,
                 foreground='blue', font=('Arial', 9)).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Step 2: BLE Name
        step2_frame = ttk.LabelFrame(main_frame, text="2. Set BLE Name", padding="10")
        step2_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        step2_frame.columnconfigure(1, weight=1)
        
        ttk.Label(step2_frame, text="BLE Name:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        self.ble_name_var = tk.StringVar()
        name_entry = ttk.Entry(step2_frame, textvariable=self.ble_name_var, font=('Arial', 10))
        name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(step2_frame, text="(will be saved before compilation)", 
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Step 3: Device Selection
        step3_frame = ttk.LabelFrame(main_frame, text="3. Select Device", padding="10")
        step3_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        step3_frame.columnconfigure(1, weight=1)
        
        ttk.Label(step3_frame, text="Device:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(step3_frame, textvariable=self.device_var,
                                         values=[], state='readonly', width=40)
        self.device_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Step 4: Actions
        step4_frame = ttk.LabelFrame(main_frame, text="4. Build & Flash", padding="10")
        step4_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        button_frame = ttk.Frame(step4_frame)
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
        ttk.Label(step4_frame, textvariable=self.status_var,
                 font=('Arial', 9), foreground='gray').grid(row=1, column=0, pady=(5, 0))
        
        # Log output
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="10")
        log_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80,
                                                   font=('Courier', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
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
                    self.available_devices = scanned_devices  # Replace, don't update
                    log_buffer.append(f"✓ Found {len(scanned_devices)} companion_radio profiles in repository")
            
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
                self.log(f"✓ Device list refreshed - {len(device_list)} profiles available (sorted A-Z)")
                
                self.status_var.set(f"Device list refreshed - {len(device_list)} devices available")
            
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
                ['git', 'clone', '--depth', '1', GITHUB_REPO_URL, project_dir],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                return None
            
            return project_dir
            
        except Exception:
            return None
    
    def download_firmware(self):
        """Download the latest firmware from GitHub"""
        self.log("\n" + "="*60)
        self.log("DOWNLOADING LATEST FIRMWARE FROM GITHUB")
        self.log("="*60)
        self.status_var.set("Downloading firmware...")
        
        try:
            # Get the latest commit hash
            self.log("Fetching latest commit information...")
            req = urllib.request.Request(GITHUB_API_URL)
            req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                branch_info = json.loads(response.read().decode())
                commit_hash = branch_info['commit']['sha']
                commit_date = branch_info['commit']['commit']['author']['date']
                
            self.log(f"✓ Latest commit: {commit_hash[:8]}")
            self.log(f"✓ Commit date: {commit_date}")
            
            # Download the main.cpp file
            self.log("\nDownloading main.cpp...")
            raw_url = GITHUB_RAW_URL.format(commit=commit_hash)
            
            req = urllib.request.Request(raw_url)
            req.add_header('User-Agent', 'MeshCore-BLE-Flasher')
            
            with urllib.request.urlopen(req, timeout=15) as response:
                self.original_content = response.read().decode('utf-8')
            
            # Save to a local file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            download_dir = os.path.dirname(os.path.abspath(__file__))
            filename = f"main_downloaded_{timestamp}.cpp"
            self.file_path = os.path.join(download_dir, filename)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.original_content)
            
            self.is_downloaded = True
            
            lines = self.original_content.split('\n')
            self.log(f"✓ Downloaded successfully!")
            self.log(f"✓ File has {len(lines)} lines")
            self.log(f"✓ Saved as: {filename}")
            
            self.file_path_var.set(f"✓ Downloaded: {filename}")
            self.status_var.set("Firmware downloaded successfully!")
            
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
            self.file_path = filename
            self.is_downloaded = False
            self.file_path_var.set(os.path.basename(filename))
            self.status_var.set(f"File loaded: {os.path.basename(filename)}")
            self.log(f"\n✓ File selected: {filename}")
            
            # Load the file
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.original_content = f.read()
                lines = self.original_content.split('\n')
                self.log(f"  File has {len(lines)} lines")
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
            
            # Target serial_interface.begin(dev_name, ...) calls
            target_pattern = 'serial_interface.begin(dev_name,'
            
            for i, line in enumerate(lines, 1):
                if target_pattern in line:
                    new_line = line.replace('dev_name,', f'"{ble_name}",')
                    modified_lines.append(new_line)
                    changes_made += 1
                    if not silent:
                        self.log(f"  ✓ Modified line {i}:")
                        self.log(f"    Before: {line.strip()}")
                        self.log(f"    After:  {new_line.strip()}")
                else:
                    modified_lines.append(line)
            
            if changes_made == 0:
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
            
            # Update file_path
            self.file_path = save_path
            self.file_path_var.set(f"✓ Modified: {filename}")
            self.original_content = modified_content
            
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
        """Scan platformio.ini files for available companion_radio environments"""
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
                                    # Filter for companion_radio environments
                                    if 'companion' in env_name or 'radio' in env_name:
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
                dest_path = os.path.join(self.project_dir, "examples", "companion_radio", "main.cpp")
                shutil.copy2(self.file_path, dest_path)
                if not silent:
                    self.log(f"\n✓ Updated main.cpp in existing project")
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
                ['git', 'clone', '--depth', '1', GITHUB_REPO_URL, project_dir],
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
                self.available_devices = scanned_devices
                if not silent:
                    self.log(f"✓ Found {len(scanned_devices)} companion_radio profiles")
                device_list = sorted(list(self.available_devices.keys()))
                self.root.after(0, lambda: self.device_combo.configure(values=device_list))
                if device_list:
                    self.root.after(0, lambda: self.device_combo.set(device_list[0]))
            
            # Copy our modified main.cpp to the project
            if self.file_path and os.path.exists(self.file_path):
                dest_path = os.path.join(project_dir, "examples", "companion_radio", "main.cpp")
                shutil.copy2(self.file_path, dest_path)
                if not silent:
                    self.log(f"✓ Copied custom main.cpp to project")
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

