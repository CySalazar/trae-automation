#!/usr/bin/env python3
"""
Graphical User Interface Module

This module provides a comprehensive GUI for monitoring and controlling the automatic
detection system. It includes real-time dashboards, configuration panels, log viewers,
and system controls.

Features:
- Real-time monitoring dashboard
- Interactive configuration editor
- Live log viewer with filtering
- System performance graphs
- Statistics and analytics
- Profile management
- Emergency controls

Author: Matteo Sala
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import time
from datetime import datetime
import json
from typing import Dict, Any, Optional
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from system_controller import SystemState
from matplotlib.figure import Figure
import numpy as np
from collections import deque

# Import our modules
from statistics_manager import get_stats_manager
from config_manager import get_config_manager
from logger import get_logger
from system_controller import get_system_controller, SystemState

class SystemMonitorGUI:
    """Main GUI application for system monitoring and control"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Continue Detection System - Monitor & Control")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Get manager instances
        self.stats_manager = get_stats_manager()
        self.config_manager = get_config_manager()
        self.logger = get_logger()
        self.controller = get_system_controller()
        
        # Add callbacks for system state changes
        self.controller.add_state_callback('gui', self._on_system_state_change)
        self.controller.add_scan_callback('gui', self._on_scan_event)
        
        # GUI state
        self.is_running = True
        self.update_interval = 1000  # 1 second
        self.auto_refresh = tk.BooleanVar(value=True)
        
        # Data for graphs
        self.graph_data = {
            'timestamps': deque(maxlen=100),
            'cpu_usage': deque(maxlen=100),
            'memory_usage': deque(maxlen=100),
            'scan_times': deque(maxlen=100),
            'success_rate': deque(maxlen=100)
        }
        
        # Setup GUI
        self._setup_styles()
        self._create_menu()
        self._create_main_interface()
        self._setup_update_thread()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_styles(self):
        """Setup custom styles for the GUI"""
        style = ttk.Style()
        
        # Configure styles
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 9))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Warning.TLabel', foreground='orange')
    
    def _create_menu(self):
        """Create the main menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Statistics", command=self._export_statistics)
        file_menu.add_command(label="Export Configuration", command=self._export_configuration)
        file_menu.add_separator()
        file_menu.add_command(label="Import Configuration", command=self._import_configuration)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_checkbutton(label="Auto Refresh", variable=self.auto_refresh)
        view_menu.add_command(label="Refresh Now", command=self._manual_refresh)
        view_menu.add_separator()
        view_menu.add_command(label="Reset Statistics", command=self._reset_statistics)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="System Test", command=self._run_system_test)
        tools_menu.add_command(label="Performance Analysis", command=self._show_performance_analysis)
        tools_menu.add_separator()
        tools_menu.add_command(label="Emergency Stop", command=self._emergency_stop)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Documentation", command=self._show_documentation)
    
    def _create_main_interface(self):
        """Create the main interface with tabs"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self._create_dashboard_tab()
        self._create_configuration_tab()
        self._create_logs_tab()
        self._create_statistics_tab()
        self._create_system_tab()
    
    def _create_dashboard_tab(self):
        """Create the main dashboard tab"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="Dashboard")
        
        # Main container with paned window
        paned = ttk.PanedWindow(dashboard_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Status and controls
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Right panel - Graphs
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        # === LEFT PANEL ===
        
        # System status section
        status_frame = ttk.LabelFrame(left_frame, text="System Status", padding=10)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_labels = {}
        status_items = [
            ('System State', 'system_state'),
            ('Uptime', 'uptime'),
            ('Total Scans', 'total_scans'),
            ('Success Rate', 'success_rate'),
            ('Last Detection', 'last_detection'),
            ('Current Streak', 'current_streak')
        ]
        
        for i, (label, key) in enumerate(status_items):
            ttk.Label(status_frame, text=f"{label}:", style='Subtitle.TLabel').grid(
                row=i, column=0, sticky=tk.W, padx=(0, 10), pady=2
            )
            self.status_labels[key] = ttk.Label(status_frame, text="--", style='Status.TLabel')
            self.status_labels[key].grid(row=i, column=1, sticky=tk.W, pady=2)
        
        # Performance metrics section
        perf_frame = ttk.LabelFrame(left_frame, text="Performance Metrics", padding=10)
        perf_frame.pack(fill=tk.X, padx=5, pady=5)
        
        perf_items = [
            ('CPU Usage', 'cpu_usage'),
            ('Memory Usage', 'memory_usage'),
            ('Avg Scan Time', 'avg_scan_time'),
            ('Last Scan Time', 'last_scan_time')
        ]
        
        for i, (label, key) in enumerate(perf_items):
            ttk.Label(perf_frame, text=f"{label}:", style='Subtitle.TLabel').grid(
                row=i, column=0, sticky=tk.W, padx=(0, 10), pady=2
            )
            self.status_labels[key] = ttk.Label(perf_frame, text="--", style='Status.TLabel')
            self.status_labels[key].grid(row=i, column=1, sticky=tk.W, pady=2)
        
        # Control buttons section
        control_frame = ttk.LabelFrame(left_frame, text="System Controls", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Start System", command=self._start_system).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(button_frame, text="Stop System", command=self._stop_system).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(button_frame, text="Pause System", command=self._pause_system).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(button_frame, text="Reset Statistics", command=self._reset_statistics).pack(
            fill=tk.X, pady=2
        )
        
        # Quick settings section
        quick_frame = ttk.LabelFrame(left_frame, text="Quick Settings", padding=10)
        quick_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Scan interval
        ttk.Label(quick_frame, text="Scan Interval (s):").pack(anchor=tk.W)
        self.scan_interval_var = tk.DoubleVar(value=self.config_manager.get_parameter('scan_interval'))
        scan_scale = ttk.Scale(quick_frame, from_=0.1, to=10.0, variable=self.scan_interval_var,
                              orient=tk.HORIZONTAL, command=self._update_scan_interval)
        scan_scale.pack(fill=tk.X, pady=2)
        
        # OCR confidence
        ttk.Label(quick_frame, text="OCR Confidence:").pack(anchor=tk.W, pady=(10, 0))
        self.confidence_var = tk.DoubleVar(value=self.config_manager.get_parameter('ocr_confidence_threshold'))
        conf_scale = ttk.Scale(quick_frame, from_=0.1, to=1.0, variable=self.confidence_var,
                              orient=tk.HORIZONTAL, command=self._update_confidence)
        conf_scale.pack(fill=tk.X, pady=2)
        
        # === RIGHT PANEL ===
        
        # Create matplotlib figure for graphs
        self.fig = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Create subplots
        self.ax1 = self.fig.add_subplot(221)  # CPU/Memory
        self.ax2 = self.fig.add_subplot(222)  # Scan times
        self.ax3 = self.fig.add_subplot(223)  # Success rate
        self.ax4 = self.fig.add_subplot(224)  # Detection count
        
        self.fig.tight_layout()
    
    def _create_configuration_tab(self):
        """Create the configuration tab"""
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Configuration")
        
        # Create paned window
        paned = ttk.PanedWindow(config_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Categories
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Right panel - Parameters
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        # Categories listbox
        ttk.Label(left_frame, text="Categories", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        self.categories_listbox = tk.Listbox(left_frame)
        self.categories_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.categories_listbox.bind('<<ListboxSelect>>', self._on_category_select)
        
        # Profile management
        profile_frame = ttk.LabelFrame(left_frame, text="Profiles", padding=5)
        profile_frame.pack(fill=tk.X, pady=5)
        
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var, state="readonly")
        self.profile_combo.pack(fill=tk.X, pady=2)
        
        ttk.Button(profile_frame, text="Load Profile", command=self._load_profile).pack(fill=tk.X, pady=1)
        ttk.Button(profile_frame, text="Save Profile", command=self._save_profile).pack(fill=tk.X, pady=1)
        ttk.Button(profile_frame, text="Delete Profile", command=self._delete_profile).pack(fill=tk.X, pady=1)
        
        # Parameters panel
        ttk.Label(right_frame, text="Parameters", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        # Create scrollable frame for parameters
        canvas = tk.Canvas(right_frame)
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        self.params_frame = ttk.Frame(canvas)
        
        self.params_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.params_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Parameter widgets storage
        self.param_widgets = {}
        
        # Load categories
        self._load_categories()
    
    def _create_logs_tab(self):
        """Create the logs tab"""
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Logs")
        
        # Top frame for controls
        control_frame = ttk.Frame(logs_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Log level filter
        ttk.Label(control_frame, text="Level:").pack(side=tk.LEFT, padx=(0, 5))
        self.log_level_var = tk.StringVar(value="ALL")
        log_level_combo = ttk.Combobox(control_frame, textvariable=self.log_level_var,
                                      values=["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                      state="readonly", width=10)
        log_level_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # Search filter
        ttk.Label(control_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.log_search_var = tk.StringVar()
        search_entry = ttk.Entry(control_frame, textvariable=self.log_search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Control buttons
        ttk.Button(control_frame, text="Refresh", command=self._refresh_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Clear", command=self._clear_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Export", command=self._export_logs).pack(side=tk.LEFT, padx=2)
        
        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Auto-scroll", variable=self.auto_scroll_var).pack(side=tk.RIGHT)
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(logs_frame, wrap=tk.WORD, height=25)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure text tags for different log levels
        self.log_text.tag_configure("DEBUG", foreground="gray")
        self.log_text.tag_configure("INFO", foreground="black")
        self.log_text.tag_configure("WARNING", foreground="orange")
        self.log_text.tag_configure("ERROR", foreground="red")
        self.log_text.tag_configure("CRITICAL", foreground="red", background="yellow")
    
    def _create_statistics_tab(self):
        """Create the statistics tab"""
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="Statistics")
        
        # Create notebook for statistics sub-tabs
        stats_notebook = ttk.Notebook(stats_frame)
        stats_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Summary tab
        summary_frame = ttk.Frame(stats_notebook)
        stats_notebook.add(summary_frame, text="Summary")
        
        # Create summary statistics display
        self._create_summary_statistics(summary_frame)
        
        # Historical tab
        historical_frame = ttk.Frame(stats_notebook)
        stats_notebook.add(historical_frame, text="Historical")
        
        # Create historical data display
        self._create_historical_statistics(historical_frame)
        
        # Performance tab
        performance_frame = ttk.Frame(stats_notebook)
        stats_notebook.add(performance_frame, text="Performance")
        
        # Create performance analysis display
        self._create_performance_statistics(performance_frame)
    
    def _create_system_tab(self):
        """Create the system information tab"""
        system_frame = ttk.Frame(self.notebook)
        self.notebook.add(system_frame, text="System")
        
        # System information display
        info_frame = ttk.LabelFrame(system_frame, text="System Information", padding=10)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.system_info_text = scrolledtext.ScrolledText(info_frame, height=10, wrap=tk.WORD)
        self.system_info_text.pack(fill=tk.BOTH, expand=True)
        
        # Resource monitoring
        resource_frame = ttk.LabelFrame(system_frame, text="Resource Monitoring", padding=10)
        resource_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create resource monitoring display
        self._create_resource_monitoring(resource_frame)
    
    def _create_summary_statistics(self, parent):
        """Create summary statistics display"""
        # Create scrollable text widget
        self.summary_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_historical_statistics(self, parent):
        """Create historical statistics display"""
        # Time range selection
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="Time Range:").pack(side=tk.LEFT, padx=(0, 5))
        self.time_range_var = tk.StringVar(value="1 Hour")
        time_combo = ttk.Combobox(control_frame, textvariable=self.time_range_var,
                                 values=["1 Hour", "6 Hours", "12 Hours", "24 Hours", "7 Days"],
                                 state="readonly", width=10)
        time_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="Refresh", command=self._refresh_historical).pack(side=tk.LEFT)
        
        # Historical data display
        self.historical_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD)
        self.historical_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_performance_statistics(self, parent):
        """Create performance statistics display"""
        self.performance_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD)
        self.performance_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_resource_monitoring(self, parent):
        """Create resource monitoring display"""
        # Create main container with grid layout
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # CPU Usage Section
        cpu_frame = ttk.LabelFrame(main_frame, text="CPU Usage", padding=5)
        cpu_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.cpu_label = ttk.Label(cpu_frame, text="CPU: 0%", font=('Arial', 10, 'bold'))
        self.cpu_label.pack()
        
        self.cpu_progress = ttk.Progressbar(cpu_frame, length=200, mode='determinate')
        self.cpu_progress.pack(pady=5)
        
        # Memory Usage Section
        memory_frame = ttk.LabelFrame(main_frame, text="Memory Usage", padding=5)
        memory_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        self.memory_label = ttk.Label(memory_frame, text="Memory: 0%", font=('Arial', 10, 'bold'))
        self.memory_label.pack()
        
        self.memory_progress = ttk.Progressbar(memory_frame, length=200, mode='determinate')
        self.memory_progress.pack(pady=5)
        
        # Disk Usage Section
        disk_frame = ttk.LabelFrame(main_frame, text="Disk Usage", padding=5)
        disk_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        self.disk_label = ttk.Label(disk_frame, text="Disk: 0%", font=('Arial', 10, 'bold'))
        self.disk_label.pack()
        
        self.disk_progress = ttk.Progressbar(disk_frame, length=200, mode='determinate')
        self.disk_progress.pack(pady=5)
        
        # Network Usage Section
        network_frame = ttk.LabelFrame(main_frame, text="Network Activity", padding=5)
        network_frame.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        self.network_label = ttk.Label(network_frame, text="Network: Idle", font=('Arial', 10, 'bold'))
        self.network_label.pack()
        
        # Process Information Section
        process_frame = ttk.LabelFrame(main_frame, text="Process Information", padding=5)
        process_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Process details
        process_info_frame = ttk.Frame(process_frame)
        process_info_frame.pack(fill=tk.X)
        
        ttk.Label(process_info_frame, text="PID:").grid(row=0, column=0, sticky="w", padx=5)
        self.pid_label = ttk.Label(process_info_frame, text="N/A")
        self.pid_label.grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(process_info_frame, text="Threads:").grid(row=0, column=2, sticky="w", padx=5)
        self.threads_label = ttk.Label(process_info_frame, text="N/A")
        self.threads_label.grid(row=0, column=3, sticky="w", padx=5)
        
        ttk.Label(process_info_frame, text="Handles:").grid(row=1, column=0, sticky="w", padx=5)
        self.handles_label = ttk.Label(process_info_frame, text="N/A")
        self.handles_label.grid(row=1, column=1, sticky="w", padx=5)
        
        ttk.Label(process_info_frame, text="Start Time:").grid(row=1, column=2, sticky="w", padx=5)
        self.start_time_label = ttk.Label(process_info_frame, text="N/A")
        self.start_time_label.grid(row=1, column=3, sticky="w", padx=5)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        process_info_frame.columnconfigure(1, weight=1)
        process_info_frame.columnconfigure(3, weight=1)
    
    def _update_resource_monitoring(self):
        """Update resource monitoring display"""
        try:
            import psutil
            import os
            
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_label.config(text=f"CPU: {cpu_percent:.1f}%")
            self.cpu_progress['value'] = cpu_percent
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.memory_label.config(text=f"Memory: {memory_percent:.1f}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)")
            self.memory_progress['value'] = memory_percent
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.disk_label.config(text=f"Disk: {disk_percent:.1f}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)")
            self.disk_progress['value'] = disk_percent
            
            # Get network activity
            net_io = psutil.net_io_counters()
            if hasattr(self, '_prev_net_io'):
                bytes_sent = net_io.bytes_sent - self._prev_net_io.bytes_sent
                bytes_recv = net_io.bytes_recv - self._prev_net_io.bytes_recv
                if bytes_sent > 0 or bytes_recv > 0:
                    self.network_label.config(text=f"Network: ↑{bytes_sent//1024}KB ↓{bytes_recv//1024}KB")
                else:
                    self.network_label.config(text="Network: Idle")
            self._prev_net_io = net_io
            
            # Get process information
            current_process = psutil.Process(os.getpid())
            self.pid_label.config(text=str(current_process.pid))
            self.threads_label.config(text=str(current_process.num_threads()))
            
            try:
                if hasattr(current_process, 'num_handles'):
                    self.handles_label.config(text=str(current_process.num_handles()))
                else:
                    self.handles_label.config(text="N/A")
            except:
                self.handles_label.config(text="N/A")
            
            start_time = datetime.fromtimestamp(current_process.create_time())
            self.start_time_label.config(text=start_time.strftime('%H:%M:%S'))
            
        except Exception as e:
            # Fallback if psutil is not available
            self.cpu_label.config(text="CPU: N/A")
            self.memory_label.config(text="Memory: N/A")
            self.disk_label.config(text="Disk: N/A")
            self.network_label.config(text="Network: N/A")
            self.pid_label.config(text="N/A")
            self.threads_label.config(text="N/A")
            self.handles_label.config(text="N/A")
            self.start_time_label.config(text="N/A")
    
    def _update_system_info(self):
        """Update system information display"""
        try:
            if hasattr(self, 'system_controller'):
                system_info = self.system_controller.get_system_info()
                
                info_text = f"""System Status: {system_info.get('status', 'Unknown')}
Uptime: {system_info.get('uptime', 'N/A')}
Total Scans: {system_info.get('total_scans', 0)}
Success Rate: {system_info.get('success_rate', 0):.1f}%
Last Detection: {system_info.get('last_detection', 'Never')}
Current Streak: {system_info.get('current_streak', 0)}

Configuration:
- Scan Interval: {system_info.get('scan_interval', 'N/A')}ms
- OCR Confidence: {system_info.get('ocr_confidence', 'N/A')}%
- Auto Refresh: {'Enabled' if self.auto_refresh.get() else 'Disabled'}
- Update Interval: {self.update_interval}ms

System Resources:
- Python Version: {system_info.get('python_version', 'N/A')}
- Platform: {system_info.get('platform', 'N/A')}
- Architecture: {system_info.get('architecture', 'N/A')}
"""
                
                self.system_info_text.config(state=tk.NORMAL)
                self.system_info_text.delete(1.0, tk.END)
                self.system_info_text.insert(tk.END, info_text)
                self.system_info_text.config(state=tk.DISABLED)
            
        except Exception as e:
            error_text = f"Error retrieving system information: {str(e)}"
            self.system_info_text.config(state=tk.NORMAL)
            self.system_info_text.delete(1.0, tk.END)
            self.system_info_text.insert(tk.END, error_text)
            self.system_info_text.config(state=tk.DISABLED)
    
    def _setup_update_thread(self):
        """Setup the background update thread"""
        self.update_thread = threading.Thread(target=self._update_worker, daemon=True)
        self.update_thread.start()
    
    def _update_worker(self):
        """Background worker for updating the GUI"""
        while self.is_running:
            try:
                if self.auto_refresh.get():
                    self.root.after(0, self._update_dashboard)
                    self.root.after(0, self._update_graphs)
                    self.root.after(0, self._update_resource_monitoring)
                    self.root.after(0, self._update_system_info)
                time.sleep(self.update_interval / 1000.0)
            except Exception as e:
                print(f"Error in update worker: {e}")
                time.sleep(5)
    
    def _update_dashboard(self):
        """Update dashboard status labels"""
        try:
            stats = self.stats_manager.get_current_stats()
            
            # Update system status from controller
            self._update_system_status()
            
            # Update other status labels
            self.status_labels['uptime'].config(text=stats['session']['uptime_formatted'])
            self.status_labels['total_scans'].config(text=str(stats['scans']['total']))
            self.status_labels['success_rate'].config(text=f"{stats['scans']['success_rate']:.1f}%")
            
            last_detection = stats['detection']['last_detection']
            if last_detection:
                last_det_time = datetime.fromisoformat(last_detection.replace('Z', '+00:00'))
                self.status_labels['last_detection'].config(text=last_det_time.strftime('%H:%M:%S'))
            else:
                self.status_labels['last_detection'].config(text="Never")
            
            self.status_labels['current_streak'].config(text=str(stats['detection']['current_streak']))
            
            # Update performance labels
            self.status_labels['cpu_usage'].config(text=f"{stats['system']['cpu_percent']:.1f}%")
            self.status_labels['memory_usage'].config(text=f"{stats['system']['memory_percent']:.1f}%")
            self.status_labels['avg_scan_time'].config(text=f"{stats['performance']['avg_scan_time']:.3f}s")
            self.status_labels['last_scan_time'].config(text=f"{stats['performance']['last_scan_time']:.3f}s")
            
        except Exception as e:
            print(f"Error updating dashboard: {e}")
    
    def _update_dashboard_metrics(self):
        """Update dashboard performance metrics"""
        try:
            # Get real metrics from system controller
            info = self.controller.get_system_info()
            
            # Update performance metrics
            if hasattr(self, 'cpu_var'):
                cpu_usage = info.get('cpu_usage', 0)
                self.cpu_var.set(f"CPU: {cpu_usage:.1f}%")
            
            if hasattr(self, 'memory_var'):
                memory_mb = info.get('memory_usage_mb', 0)
                self.memory_var.set(f"Memory: {memory_mb:.0f} MB")
            
            if hasattr(self, 'scans_var'):
                scan_count = info.get('scan_count', 0)
                self.scans_var.set(f"Scans: {scan_count:,}")
            
            if hasattr(self, 'success_var'):
                success_rate = info.get('success_rate', 0) * 100
                self.success_var.set(f"Success Rate: {success_rate:.1f}%")
            
            if hasattr(self, 'uptime_var'):
                uptime_seconds = info.get('uptime_seconds', 0)
                hours = int(uptime_seconds // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                seconds = int(uptime_seconds % 60)
                self.uptime_var.set(f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}")
                
        except Exception as e:
            print(f"Error updating dashboard metrics: {e}")
    
    def _update_performance_graph(self, info):
        """Update performance graph with current data"""
        try:
            if hasattr(self, 'performance_fig') and hasattr(self, 'performance_ax'):
                # Clear previous data
                self.performance_ax.clear()
                
                # Get performance data
                cpu_usage = info.get('cpu_usage', 0)
                memory_usage = info.get('memory_usage_mb', 0)
                
                # Create simple bar chart
                metrics = ['CPU %', 'Memory MB']
                values = [cpu_usage, memory_usage / 10]  # Scale memory for display
                
                bars = self.performance_ax.bar(metrics, values, color=['#3498db', '#e74c3c'])
                self.performance_ax.set_title('System Performance')
                self.performance_ax.set_ylabel('Usage')
                
                # Add value labels on bars
                for bar, value in zip(bars, [cpu_usage, memory_usage]):
                    height = bar.get_height()
                    self.performance_ax.text(bar.get_x() + bar.get_width()/2., height,
                                           f'{value:.1f}', ha='center', va='bottom')
                
                self.performance_canvas.draw()
        except Exception as e:
            print(f"Error updating performance graph: {e}")
    
    def _update_scan_rate_graph(self, info):
        """Update scan rate graph with current data"""
        try:
            if hasattr(self, 'scan_rate_fig') and hasattr(self, 'scan_rate_ax'):
                # Clear previous data
                self.scan_rate_ax.clear()
                
                # Get scan data
                scan_count = info.get('scan_count', 0)
                success_rate = info.get('success_rate', 0) * 100
                
                # Create simple line plot (placeholder data)
                x_data = list(range(10))
                y_data = [success_rate + (i % 3 - 1) * 2 for i in x_data]  # Simulate variation
                
                self.scan_rate_ax.plot(x_data, y_data, 'g-', linewidth=2)
                self.scan_rate_ax.set_title('Success Rate Trend')
                self.scan_rate_ax.set_xlabel('Time')
                self.scan_rate_ax.set_ylabel('Success Rate %')
                self.scan_rate_ax.grid(True, alpha=0.3)
                
                self.scan_rate_canvas.draw()
        except Exception as e:
            print(f"Error updating scan rate graph: {e}")
    
    def _update_graphs(self):
        """Update the performance graphs"""
        try:
            stats = self.stats_manager.get_current_stats()
            current_time = time.time()
            
            # Add data points
            self.graph_data['timestamps'].append(current_time)
            self.graph_data['cpu_usage'].append(stats['system']['cpu_percent'])
            self.graph_data['memory_usage'].append(stats['system']['memory_percent'])
            self.graph_data['scan_times'].append(stats['performance']['last_scan_time'] * 1000)  # Convert to ms
            self.graph_data['success_rate'].append(stats['scans']['success_rate'])
            
            # Clear and redraw graphs
            self.ax1.clear()
            self.ax2.clear()
            self.ax3.clear()
            self.ax4.clear()
            
            if len(self.graph_data['timestamps']) > 1:
                times = list(self.graph_data['timestamps'])
                time_labels = [datetime.fromtimestamp(t).strftime('%H:%M:%S') for t in times[-10:]]
                
                # CPU/Memory graph
                self.ax1.plot(times, self.graph_data['cpu_usage'], 'b-', label='CPU %', linewidth=2)
                self.ax1.plot(times, self.graph_data['memory_usage'], 'r-', label='Memory %', linewidth=2)
                self.ax1.set_title('System Resources')
                self.ax1.set_ylabel('Usage %')
                self.ax1.legend()
                self.ax1.grid(True, alpha=0.3)
                
                # Scan times graph
                self.ax2.plot(times, self.graph_data['scan_times'], 'g-', linewidth=2)
                self.ax2.set_title('Scan Performance')
                self.ax2.set_ylabel('Time (ms)')
                self.ax2.grid(True, alpha=0.3)
                
                # Success rate graph
                self.ax3.plot(times, self.graph_data['success_rate'], 'm-', linewidth=2)
                self.ax3.set_title('Success Rate')
                self.ax3.set_ylabel('Success %')
                self.ax3.grid(True, alpha=0.3)
                
                # Detection count (placeholder)
                detections = [stats['scans']['total_detections']] * len(times)
                self.ax4.plot(times, detections, 'c-', linewidth=2)
                self.ax4.set_title('Total Detections')
                self.ax4.set_ylabel('Count')
                self.ax4.grid(True, alpha=0.3)
                
                # Format x-axis for all subplots
                for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
                    if len(times) > 10:
                        ax.set_xticks(times[-10::2])
                        ax.set_xticklabels(time_labels[::2], rotation=45)
                    else:
                        ax.set_xticks(times)
                        ax.set_xticklabels(time_labels, rotation=45)
            
            self.fig.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating graphs: {e}")
    
    def _load_categories(self):
        """Load configuration categories"""
        categories = self.config_manager.get_all_categories()
        self.categories_listbox.delete(0, tk.END)
        for category in sorted(categories):
            self.categories_listbox.insert(tk.END, category)
        
        # Load profiles
        profiles = self.config_manager.get_profiles()
        self.profile_combo['values'] = profiles
        if profiles:
            self.profile_combo.set(profiles[0])
    
    def _on_category_select(self, event):
        """Handle category selection"""
        selection = self.categories_listbox.curselection()
        if not selection:
            return
        
        category = self.categories_listbox.get(selection[0])
        self._load_category_parameters(category)
    
    def _load_category_parameters(self, category: str):
        """Load parameters for a specific category"""
        # Clear existing widgets
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_widgets.clear()
        
        # Get parameters for category
        parameters = self.config_manager.get_parameters_by_category(category)
        
        row = 0
        for param_name, value in parameters.items():
            param_info = self.config_manager.get_parameter_info(param_name)
            
            # Parameter label
            label_frame = ttk.Frame(self.params_frame)
            label_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)
            
            ttk.Label(label_frame, text=param_name, style='Subtitle.TLabel').pack(anchor=tk.W)
            ttk.Label(label_frame, text=param_info['description'], style='Status.TLabel').pack(anchor=tk.W)
            
            # Parameter input widget
            input_frame = ttk.Frame(self.params_frame)
            input_frame.grid(row=row+1, column=0, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=(0, 10))
            
            if param_info['data_type'] == 'bool':
                var = tk.BooleanVar(value=value)
                widget = ttk.Checkbutton(input_frame, variable=var)
            elif param_info['allowed_values']:
                var = tk.StringVar(value=str(value))
                widget = ttk.Combobox(input_frame, textvariable=var, values=param_info['allowed_values'], state="readonly")
            elif param_info['data_type'] in ['int', 'float']:
                var = tk.StringVar(value=str(value))
                widget = ttk.Entry(input_frame, textvariable=var)
                
                # Add scale if min/max values are available
                if param_info['min_value'] is not None and param_info['max_value'] is not None:
                    scale_var = tk.DoubleVar(value=float(value))
                    scale = ttk.Scale(input_frame, from_=param_info['min_value'], to=param_info['max_value'],
                                     variable=scale_var, orient=tk.HORIZONTAL)
                    scale.pack(fill=tk.X, pady=2)
                    
                    def update_entry(val, entry_var=var, scale_var=scale_var):
                        entry_var.set(f"{scale_var.get():.3f}" if param_info['data_type'] == 'float' else str(int(scale_var.get())))
                    
                    scale.configure(command=update_entry)
            else:
                var = tk.StringVar(value=str(value))
                widget = ttk.Entry(input_frame, textvariable=var)
            
            widget.pack(fill=tk.X)
            
            # Save button
            def make_save_callback(param_name, var):
                return lambda: self._save_parameter(param_name, var.get())
            
            ttk.Button(input_frame, text="Save", command=make_save_callback(param_name, var)).pack(side=tk.RIGHT, padx=(5, 0))
            
            # Reset button
            def make_reset_callback(param_name):
                return lambda: self._reset_parameter(param_name)
            
            ttk.Button(input_frame, text="Reset", command=make_reset_callback(param_name)).pack(side=tk.RIGHT)
            
            self.param_widgets[param_name] = (var, widget)
            row += 2
    
    # Event handlers and utility methods
    def _save_parameter(self, param_name: str, value: Any):
        """Save a parameter value"""
        try:
            if self.config_manager.set_parameter(param_name, value, "GUI User", "Modified via GUI"):
                messagebox.showinfo("Success", f"Parameter '{param_name}' updated successfully")
            else:
                messagebox.showerror("Error", f"Failed to update parameter '{param_name}'")
        except Exception as e:
            messagebox.showerror("Error", f"Error updating parameter: {e}")
    
    def _reset_parameter(self, param_name: str):
        """Reset a parameter to default value"""
        try:
            if self.config_manager.reset_parameter(param_name, "GUI User"):
                messagebox.showinfo("Success", f"Parameter '{param_name}' reset to default")
                # Refresh the current category
                selection = self.categories_listbox.curselection()
                if selection:
                    category = self.categories_listbox.get(selection[0])
                    self._load_category_parameters(category)
            else:
                messagebox.showerror("Error", f"Failed to reset parameter '{param_name}'")
        except Exception as e:
            messagebox.showerror("Error", f"Error resetting parameter: {e}")
    
    def _update_scan_interval(self, value):
        """Update scan interval from scale"""
        self.config_manager.set_parameter('scan_interval', float(value), "GUI User", "Quick setting")
    
    def _update_confidence(self, value):
        """Update OCR confidence from scale"""
        self.config_manager.set_parameter('ocr_confidence_threshold', float(value), "GUI User", "Quick setting")
    
    def _start_system(self):
        """Start the detection system"""
        try:
            if self.controller.start_system():
                messagebox.showinfo("System Start", "Detection system started successfully!")
            else:
                messagebox.showerror("Error", "Failed to start detection system. Check logs for details.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start system: {str(e)}")
    
    def _stop_system(self):
        """Stop the detection system"""
        try:
            current_state = self.controller.get_state()
            
            if current_state.value == "stopped":
                messagebox.showinfo("System Stop", "Detection system is already stopped.")
                return
                
            if self.controller.stop_system():
                messagebox.showinfo("System Stop", "Detection system stopped successfully!")
            else:
                messagebox.showerror("Error", f"Failed to stop detection system. Current state: {current_state.value}. Check logs for details.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop system: {str(e)}")
    
    def _pause_system(self):
        """Pause/Resume the detection system"""
        try:
            if self.controller.is_paused():
                # Resume
                if self.controller.resume_system():
                    messagebox.showinfo("System Resume", "Detection system resumed successfully!")
                else:
                    messagebox.showerror("Error", "Failed to resume detection system.")
            elif self.controller.is_running():
                # Pause
                if self.controller.pause_system():
                    messagebox.showinfo("System Pause", "Detection system paused successfully!")
                else:
                    messagebox.showerror("Error", "Failed to pause detection system.")
            else:
                messagebox.showwarning("Warning", "System must be running to pause/resume.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to pause/resume system: {str(e)}")
    
    def _reset_statistics(self):
        """Reset all statistics"""
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all statistics?"):
            self.stats_manager.reset_statistics()
            messagebox.showinfo("Success", "Statistics reset successfully")
    
    def _emergency_stop(self):
        """Emergency stop all operations"""
        try:
            result = messagebox.askyesno(
                "Emergency Stop", 
                "Are you sure you want to perform an emergency stop?\n\nThis will immediately halt all operations.",
                icon='warning'
            )
            if result:
                if self.controller.emergency_stop():
                    messagebox.showinfo("Emergency Stop", "Emergency stop completed successfully!")
                else:
                    messagebox.showerror("Error", "Emergency stop failed. Check logs for details.")
        except Exception as e:
            messagebox.showerror("Error", f"Emergency stop failed: {str(e)}")
    
    def _manual_refresh(self):
        """Manual refresh of all data"""
        self._update_dashboard()
        self._update_graphs()
        self._refresh_logs()
    
    def _export_statistics(self):
        """Export statistics to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.stats_manager.export_data(filename)
                messagebox.showinfo("Success", f"Statistics exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export statistics: {e}")
    
    def _export_configuration(self):
        """Export configuration to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                if self.config_manager.export_configuration(filename):
                    messagebox.showinfo("Success", f"Configuration exported to {filename}")
                else:
                    messagebox.showerror("Error", "Failed to export configuration")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export configuration: {e}")
    
    def _import_configuration(self):
        """Import configuration from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                if self.config_manager.import_configuration(filename, "GUI User"):
                    messagebox.showinfo("Success", f"Configuration imported from {filename}")
                    self._load_categories()  # Refresh categories
                else:
                    messagebox.showerror("Error", "Failed to import configuration")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import configuration: {e}")
    
    def _load_profile(self):
        """Load selected profile"""
        profile_name = self.profile_var.get()
        if profile_name:
            if self.config_manager.load_profile(profile_name, "GUI User"):
                messagebox.showinfo("Success", f"Profile '{profile_name}' loaded")
                # Refresh current category view
                selection = self.categories_listbox.curselection()
                if selection:
                    category = self.categories_listbox.get(selection[0])
                    self._load_category_parameters(category)
            else:
                messagebox.showerror("Error", f"Failed to load profile '{profile_name}'")
    
    def _save_profile(self):
        """Save current configuration as profile"""
        profile_name = tk.simpledialog.askstring("Save Profile", "Enter profile name:")
        if profile_name:
            if self.config_manager.save_profile(profile_name):
                messagebox.showinfo("Success", f"Profile '{profile_name}' saved")
                # Refresh profile list
                profiles = self.config_manager.get_profiles()
                self.profile_combo['values'] = profiles
            else:
                messagebox.showerror("Error", f"Failed to save profile '{profile_name}'")
    
    def _delete_profile(self):
        """Delete selected profile"""
        profile_name = self.profile_var.get()
        if profile_name:
            if messagebox.askyesno("Confirm Delete", f"Delete profile '{profile_name}'?"):
                if self.config_manager.delete_profile(profile_name):
                    messagebox.showinfo("Success", f"Profile '{profile_name}' deleted")
                    # Refresh profile list
                    profiles = self.config_manager.get_profiles()
                    self.profile_combo['values'] = profiles
                    if profiles:
                        self.profile_combo.set(profiles[0])
                    else:
                        self.profile_combo.set("")
                else:
                    messagebox.showerror("Error", f"Failed to delete profile '{profile_name}'")
    
    def _refresh_logs(self):
        """Refresh log display"""
        try:
            if hasattr(self, 'log_text'):
                # Get recent logs from logger
                try:
                    # Try to get logs from the logger module
                    recent_logs = self.logger.get_recent_logs(100)  # Get last 100 log entries
                    
                    # Clear current logs
                    self.log_text.delete(1.0, tk.END)
                    
                    # Add recent logs
                    for log_entry in recent_logs:
                        timestamp = log_entry.get('timestamp', datetime.now().strftime('%H:%M:%S'))
                        level = log_entry.get('level', 'INFO')
                        message = log_entry.get('message', '')
                        
                        # Format log entry
                        formatted_log = f"[{timestamp}] [{level}] {message}\n"
                        
                        # Insert with color coding based on level
                        self.log_text.insert(tk.END, formatted_log)
                        
                        # Apply color tags based on log level
                        if level == 'ERROR':
                            self.log_text.tag_add('error', f"end-{len(formatted_log)}c", 'end-1c')
                        elif level == 'WARNING':
                            self.log_text.tag_add('warning', f"end-{len(formatted_log)}c", 'end-1c')
                        elif level == 'DEBUG':
                            self.log_text.tag_add('debug', f"end-{len(formatted_log)}c", 'end-1c')
                    
                    # Configure color tags
                    self.log_text.tag_config('error', foreground='red')
                    self.log_text.tag_config('warning', foreground='orange')
                    self.log_text.tag_config('debug', foreground='gray')
                    
                    # Scroll to bottom
                    self.log_text.see(tk.END)
                    
                except (AttributeError, TypeError):
                    # Fallback if get_recent_logs is not available
                    self.log_text.delete(1.0, tk.END)
                    self.log_text.insert(tk.END, "Log integration would be implemented here\n")
                    self.log_text.insert(tk.END, f"Current time: {datetime.now()}\n")
                    self.log_text.insert(tk.END, "Sample log entries would appear here...\n")
                    
        except Exception as e:
            print(f"Error refreshing logs: {e}")
    
    def _clear_logs(self):
        """Clear log display"""
        self.log_text.delete(1.0, tk.END)
    
    def _export_logs(self):
        """Export logs to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Logs exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export logs: {e}")
    
    def _refresh_historical(self):
        """Refresh historical statistics"""
        time_range = self.time_range_var.get()
        hours = {
            "1 Hour": 1,
            "6 Hours": 6,
            "12 Hours": 12,
            "24 Hours": 24,
            "7 Days": 168
        }.get(time_range, 1)
        
        try:
            historical_data = self.stats_manager.get_historical_data(hours)
            
            self.historical_text.delete(1.0, tk.END)
            self.historical_text.insert(tk.END, f"Historical Data - Last {time_range}\n")
            self.historical_text.insert(tk.END, "=" * 50 + "\n\n")
            
            # Display scan data
            scans = historical_data['scans']
            self.historical_text.insert(tk.END, f"Total Scans: {len(scans)}\n")
            
            if scans:
                successful = sum(1 for scan in scans if scan['success'])
                self.historical_text.insert(tk.END, f"Successful: {successful}\n")
                self.historical_text.insert(tk.END, f"Success Rate: {successful/len(scans)*100:.1f}%\n")
                
                avg_time = sum(scan['duration'] for scan in scans) / len(scans)
                self.historical_text.insert(tk.END, f"Average Scan Time: {avg_time:.3f}s\n")
            
            self.historical_text.insert(tk.END, "\n" + json.dumps(historical_data, indent=2, default=str))
            
        except Exception as e:
            self.historical_text.delete(1.0, tk.END)
            self.historical_text.insert(tk.END, f"Error loading historical data: {e}")
    
    def _run_system_test(self):
        """Run system diagnostics"""
        try:
            # Create a progress dialog
            test_window = tk.Toplevel(self.root)
            test_window.title("System Diagnostics")
            test_window.geometry("500x400")
            test_window.transient(self.root)
            test_window.grab_set()
            
            # Center the window
            test_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
            
            # Create test results display
            test_frame = ttk.Frame(test_window, padding="10")
            test_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(test_frame, text="System Diagnostics", font=('Arial', 14, 'bold')).pack(pady=(0, 10))
            
            # Results text area
            results_text = scrolledtext.ScrolledText(test_frame, height=15, width=60)
            results_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # Progress bar
            progress = ttk.Progressbar(test_frame, mode='determinate', length=400)
            progress.pack(fill=tk.X, pady=(0, 10))
            
            # Close button
            close_btn = ttk.Button(test_frame, text="Close", command=test_window.destroy)
            close_btn.pack()
            
            def run_tests():
                """Run the actual tests"""
                tests = [
                    ("System Controller Status", self._test_system_controller),
                    ("Configuration Validation", self._test_configuration),
                    ("Logger Functionality", self._test_logger),
                    ("Scanner Module", self._test_scanner),
                    ("Resource Availability", self._test_resources),
                    ("Dependencies Check", self._test_dependencies)
                ]
                
                total_tests = len(tests)
                results_text.insert(tk.END, "Starting system diagnostics...\n\n")
                test_window.update()
                
                for i, (test_name, test_func) in enumerate(tests):
                    results_text.insert(tk.END, f"Running {test_name}...\n")
                    test_window.update()
                    
                    try:
                        result = test_func()
                        status = "✅ PASS" if result else "❌ FAIL"
                        results_text.insert(tk.END, f"{test_name}: {status}\n")
                    except Exception as e:
                        results_text.insert(tk.END, f"{test_name}: ❌ ERROR - {str(e)}\n")
                    
                    progress['value'] = ((i + 1) / total_tests) * 100
                    test_window.update()
                    time.sleep(0.5)  # Small delay for visual effect
                
                results_text.insert(tk.END, "\nDiagnostics completed.\n")
                results_text.see(tk.END)
            
            # Run tests in a separate thread to avoid blocking UI
            threading.Thread(target=run_tests, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run system test: {str(e)}")
    
    def _test_system_controller(self):
        """Test system controller functionality"""
        try:
            state = self.controller.get_state()
            info = self.controller.get_system_info()
            return state is not None and info is not None
        except:
            return False
    
    def _test_configuration(self):
        """Test configuration validation"""
        try:
            config = self.config_manager.get_all_config()
            return len(config) > 0
        except:
            return False
    
    def _test_logger(self):
        """Test logger functionality"""
        try:
            # Test if logger can write a test message
            from logger import log_debug
            log_debug("System test message")
            return True
        except:
            return False
    
    def _test_scanner(self):
        """Test scanner module availability"""
        try:
            import scanner
            return hasattr(scanner, 'perform_scan_with_retry')
        except:
            return False
    
    def _test_resources(self):
        """Test system resources"""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            return cpu_percent < 90 and memory.percent < 90
        except:
            return True  # If psutil not available, assume OK
    
    def _test_dependencies(self):
        """Test required dependencies"""
        try:
            required_modules = ['tkinter', 'matplotlib', 'pyautogui']
            for module in required_modules:
                __import__(module)
            return True
        except:
            return False
    
    def _show_performance_analysis(self):
        """Show detailed performance analysis"""
        try:
            # Create performance analysis window
            perf_window = tk.Toplevel(self.root)
            perf_window.title("Performance Analysis")
            perf_window.geometry("800x600")
            perf_window.transient(self.root)
            
            # Center the window
            perf_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
            
            # Create notebook for different analysis tabs
            notebook = ttk.Notebook(perf_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # System Performance Tab
            sys_frame = ttk.Frame(notebook)
            notebook.add(sys_frame, text="System Performance")
            self._create_system_performance_tab(sys_frame)
            
            # Scan Statistics Tab
            scan_frame = ttk.Frame(notebook)
            notebook.add(scan_frame, text="Scan Statistics")
            self._create_scan_statistics_tab(scan_frame)
            
            # Resource Usage Tab
            resource_frame = ttk.Frame(notebook)
            notebook.add(resource_frame, text="Resource Usage")
            self._create_resource_usage_tab(resource_frame)
            
            # Close button
            close_frame = ttk.Frame(perf_window)
            close_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            ttk.Button(close_frame, text="Close", command=perf_window.destroy).pack(side=tk.RIGHT)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show performance analysis: {str(e)}")
    
    def _create_system_performance_tab(self, parent):
        """Create system performance analysis tab"""
        try:
            # Get system info
            info = self.controller.get_system_info()
            
            # Create scrollable frame
            canvas = tk.Canvas(parent)
            scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Performance metrics
            ttk.Label(scrollable_frame, text="System Performance Metrics", font=('Arial', 12, 'bold')).pack(pady=(10, 5))
            
            metrics_frame = ttk.LabelFrame(scrollable_frame, text="Current Metrics", padding="10")
            metrics_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Display metrics
            metrics = [
                ("System State", info.get('state', 'Unknown')),
                ("Uptime", f"{info.get('uptime_seconds', 0):.0f} seconds"),
                ("Total Scans", f"{info.get('scan_count', 0):,}"),
                ("Success Rate", f"{info.get('success_rate', 0)*100:.1f}%"),
                ("CPU Usage", f"{info.get('cpu_usage', 0):.1f}%"),
                ("Memory Usage", f"{info.get('memory_usage_mb', 0):.0f} MB")
            ]
            
            for i, (label, value) in enumerate(metrics):
                row_frame = ttk.Frame(metrics_frame)
                row_frame.pack(fill=tk.X, pady=2)
                ttk.Label(row_frame, text=f"{label}:", width=15).pack(side=tk.LEFT)
                ttk.Label(row_frame, text=str(value), font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            ttk.Label(parent, text=f"Error loading performance data: {e}").pack(pady=20)
    
    def _create_scan_statistics_tab(self, parent):
        """Create scan statistics tab"""
        try:
            info = self.controller.get_system_info()
            
            # Statistics display
            ttk.Label(parent, text="Scan Statistics", font=('Arial', 12, 'bold')).pack(pady=(10, 5))
            
            stats_frame = ttk.LabelFrame(parent, text="Scan Performance", padding="10")
            stats_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Scan statistics
            scan_stats = [
                ("Total Scans Performed", f"{info.get('scan_count', 0):,}"),
                ("Successful Scans", f"{int(info.get('scan_count', 0) * info.get('success_rate', 0)):,}"),
                ("Failed Scans", f"{int(info.get('scan_count', 0) * (1 - info.get('success_rate', 0))):,}"),
                ("Success Rate", f"{info.get('success_rate', 0)*100:.2f}%"),
                ("Average Scan Time", f"{info.get('avg_scan_time', 0):.3f} seconds"),
                ("Clicks Performed", f"{info.get('clicks_performed', 0):,}")
            ]
            
            for label, value in scan_stats:
                row_frame = ttk.Frame(stats_frame)
                row_frame.pack(fill=tk.X, pady=2)
                ttk.Label(row_frame, text=f"{label}:", width=20).pack(side=tk.LEFT)
                ttk.Label(row_frame, text=str(value), font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
            
        except Exception as e:
            ttk.Label(parent, text=f"Error loading scan statistics: {e}").pack(pady=20)
    
    def _create_resource_usage_tab(self, parent):
        """Create resource usage tab"""
        try:
            # Resource usage display
            ttk.Label(parent, text="Resource Usage", font=('Arial', 12, 'bold')).pack(pady=(10, 5))
            
            # Try to get system resource info
            try:
                import psutil
                
                resource_frame = ttk.LabelFrame(parent, text="System Resources", padding="10")
                resource_frame.pack(fill=tk.X, padx=10, pady=5)
                
                # Get resource data
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                resources = [
                    ("CPU Usage", f"{cpu_percent:.1f}%"),
                    ("Memory Usage", f"{memory.percent:.1f}% ({memory.used // (1024**2)} MB / {memory.total // (1024**2)} MB)"),
                    ("Disk Usage", f"{disk.percent:.1f}% ({disk.used // (1024**3)} GB / {disk.total // (1024**3)} GB)"),
                    ("Available Memory", f"{memory.available // (1024**2)} MB"),
                    ("CPU Count", f"{psutil.cpu_count()} cores")
                ]
                
                for label, value in resources:
                    row_frame = ttk.Frame(resource_frame)
                    row_frame.pack(fill=tk.X, pady=2)
                    ttk.Label(row_frame, text=f"{label}:", width=15).pack(side=tk.LEFT)
                    ttk.Label(row_frame, text=str(value), font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
                    
            except ImportError:
                ttk.Label(parent, text="psutil module not available for detailed resource monitoring").pack(pady=20)
                
        except Exception as e:
            ttk.Label(parent, text=f"Error loading resource data: {e}").pack(pady=20)
    
    def _show_about(self):
        """Show about dialog"""
        about_text = """
Continue Detection System
Version 1.0.0

A comprehensive system for automatic detection and interaction
with UI elements using OCR and computer vision.

Features:
- Real-time monitoring
- Dynamic configuration
- Performance analytics
- Comprehensive logging

Developed with Python, Tkinter, and OpenCV
        """
        messagebox.showinfo("About", about_text)
    
    def _show_documentation(self):
        """Show help documentation"""
        try:
            # Create documentation window
            doc_window = tk.Toplevel(self.root)
            doc_window.title("System Documentation")
            doc_window.geometry("900x700")
            doc_window.transient(self.root)
            
            # Center the window
            doc_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
            
            # Create main frame with padding
            main_frame = ttk.Frame(doc_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Title
            title_label = ttk.Label(main_frame, text="Auto-Detection System Documentation", 
                                  font=('Arial', 16, 'bold'))
            title_label.pack(pady=(0, 20))
            
            # Create notebook for different documentation sections
            doc_notebook = ttk.Notebook(main_frame)
            doc_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # Overview Tab
            overview_frame = ttk.Frame(doc_notebook)
            doc_notebook.add(overview_frame, text="Overview")
            self._create_overview_tab(overview_frame)
            
            # Getting Started Tab
            getting_started_frame = ttk.Frame(doc_notebook)
            doc_notebook.add(getting_started_frame, text="Getting Started")
            self._create_getting_started_tab(getting_started_frame)
            
            # Configuration Tab
            config_doc_frame = ttk.Frame(doc_notebook)
            doc_notebook.add(config_doc_frame, text="Configuration")
            self._create_config_documentation_tab(config_doc_frame)
            
            # Troubleshooting Tab
            troubleshooting_frame = ttk.Frame(doc_notebook)
            doc_notebook.add(troubleshooting_frame, text="Troubleshooting")
            self._create_troubleshooting_tab(troubleshooting_frame)
            
            # API Reference Tab
            api_frame = ttk.Frame(doc_notebook)
            doc_notebook.add(api_frame, text="API Reference")
            self._create_api_reference_tab(api_frame)
            
            # Close button
            close_frame = ttk.Frame(main_frame)
            close_frame.pack(fill=tk.X, pady=(10, 0))
            ttk.Button(close_frame, text="Close", command=doc_window.destroy).pack(side=tk.RIGHT)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show documentation: {str(e)}")
    
    def _create_overview_tab(self, parent):
        """Create overview documentation tab"""
        # Create scrollable text widget
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        overview_text = """
AUTO-DETECTION SYSTEM OVERVIEW

The Auto-Detection System is a comprehensive solution for automated screen monitoring and interaction. It provides real-time detection capabilities with configurable parameters and robust error handling.

KEY FEATURES:

• Real-time Screen Monitoring
  - Continuous scanning of specified screen regions
  - Configurable scan intervals and detection thresholds
  - Multi-threaded processing for optimal performance

• Intelligent Detection
  - OCR (Optical Character Recognition) capabilities
  - Image pattern matching
  - Configurable confidence levels

• Automated Actions
  - Programmable click responses
  - Customizable action sequences
  - Conditional logic support

• Comprehensive Logging
  - Detailed operation logs
  - Performance metrics tracking
  - Error reporting and diagnostics

• User-Friendly Interface
  - Intuitive GUI with real-time dashboard
  - Configuration management
  - System monitoring and control

SYSTEM ARCHITECTURE:

The system is built with a modular architecture consisting of:

• Core Detection Engine (detect.py)
• Scanner Module (scanner.py)
• Configuration Manager (config_manager.py)
• Logging System (logger.py)
• User Interfaces (GUI, CLI)
• System Controller (system_controller.py)

This modular design ensures maintainability, scalability, and ease of customization.
"""
        
        text_widget.insert(tk.END, overview_text)
        text_widget.config(state=tk.DISABLED)
    
    def _create_getting_started_tab(self, parent):
        """Create getting started documentation tab"""
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        getting_started_text = """
GETTING STARTED

FOLLOW THESE STEPS TO BEGIN USING THE AUTO-DETECTION SYSTEM:

1. SYSTEM REQUIREMENTS
   • Python 3.7 or higher
   • Required packages: tkinter, matplotlib, pyautogui, pillow
   • Optional: psutil (for advanced system monitoring)

2. INSTALLATION
   • Ensure all dependencies are installed
   • Run: pip install -r requirements.txt
   • Verify installation by running the system test

3. INITIAL CONFIGURATION
   • Open the Configuration tab in the GUI
   • Set your desired scan interval (default: 1 second)
   • Configure OCR confidence level (default: 0.8)
   • Define detection regions if needed

4. STARTING THE SYSTEM
   • Click the "Start System" button in the Dashboard
   • Monitor the system status indicator
   • Check the logs for any issues

5. MONITORING OPERATIONS
   • Use the Dashboard to view real-time metrics
   • Check the Statistics tab for performance data
   • Review logs for detailed operation history

6. STOPPING THE SYSTEM
   • Click "Stop System" for normal shutdown
   • Use "Emergency Stop" for immediate termination
   • System state is preserved between sessions

QUICK START CHECKLIST:
☐ Install dependencies
☐ Run system test
☐ Configure basic settings
☐ Start the system
☐ Monitor initial operation
☐ Review logs for any issues

For detailed configuration options, see the Configuration tab.
For troubleshooting, see the Troubleshooting tab.
"""
        
        text_widget.insert(tk.END, getting_started_text)
        text_widget.config(state=tk.DISABLED)
    
    def _create_config_documentation_tab(self, parent):
        """Create configuration documentation tab"""
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        config_text = """
CONFIGURATION GUIDE

The system provides extensive configuration options to customize behavior:

SCAN SETTINGS:
• Scan Interval: Time between scans (0.1 - 10 seconds)
• OCR Confidence: Detection confidence threshold (0.1 - 1.0)
• Max Retries: Number of retry attempts on failure
• Timeout: Maximum time for each scan operation

DETECTION PARAMETERS:
• Target Images: Images to detect on screen
• Text Patterns: Text strings to search for
• Detection Regions: Specific screen areas to monitor
• Confidence Thresholds: Minimum match confidence

ACTION CONFIGURATION:
• Click Coordinates: Where to click when detection occurs
• Action Delays: Timing between actions
• Conditional Logic: Rules for when to perform actions
• Sequence Definitions: Multi-step action sequences

LOGGING OPTIONS:
• Log Level: DEBUG, INFO, WARNING, ERROR
• Log File Location: Where to save log files
• Log Rotation: Automatic log file management
• Console Output: Real-time log display

PERFORMANCE TUNING:
• Thread Pool Size: Number of worker threads
• Memory Limits: Maximum memory usage
• CPU Throttling: Limit CPU usage
• Cache Settings: Image and data caching

CONFIGURATION PROFILES:
Save and load different configuration sets:
• Development Profile: High logging, frequent scans
• Production Profile: Optimized for performance
• Debug Profile: Maximum logging and diagnostics
• Custom Profiles: User-defined configurations

IMPORT/EXPORT:
• Export configurations to JSON files
• Import configurations from backups
• Share configurations between systems
• Version control integration
"""
        
        text_widget.insert(tk.END, config_text)
        text_widget.config(state=tk.DISABLED)
    
    def _create_troubleshooting_tab(self, parent):
        """Create troubleshooting documentation tab"""
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        troubleshooting_text = """
TROUBLESHOOTING GUIDE

COMMON ISSUES AND SOLUTIONS:

1. SYSTEM WON'T START
   Problem: Start button doesn't respond or shows error
   Solutions:
   • Check system dependencies (run System Test)
   • Verify configuration settings
   • Review error logs for specific issues
   • Restart the application

2. DETECTION NOT WORKING
   Problem: System runs but doesn't detect targets
   Solutions:
   • Lower OCR confidence threshold
   • Check target image quality
   • Verify detection regions
   • Test with simpler targets first

3. HIGH CPU USAGE
   Problem: System consuming too many resources
   Solutions:
   • Increase scan interval
   • Reduce detection regions
   • Enable CPU throttling
   • Close unnecessary applications

4. FREQUENT ERRORS
   Problem: Many errors in logs
   Solutions:
   • Check screen resolution changes
   • Verify target applications are running
   • Update detection images
   • Review configuration settings

5. SLOW PERFORMANCE
   Problem: System responds slowly
   Solutions:
   • Optimize scan intervals
   • Reduce image sizes
   • Clear cache and logs
   • Check system resources

DIAGNOSTIC TOOLS:

• System Test: Comprehensive system check
• Performance Analysis: Detailed performance metrics
• Log Viewer: Real-time log monitoring
• Resource Monitor: System resource usage

LOG ANALYSIS:

Check logs for these common patterns:
• "Timeout" - Increase timeout values
• "Not found" - Adjust detection parameters
• "Memory" - Reduce memory usage
• "Permission" - Check file/system permissions

GETTING HELP:

If issues persist:
1. Run the System Test and note any failures
2. Export your configuration
3. Collect recent log files
4. Note your system specifications
5. Document the exact steps to reproduce the issue
"""
        
        text_widget.insert(tk.END, troubleshooting_text)
        text_widget.config(state=tk.DISABLED)
    
    def _create_api_reference_tab(self, parent):
        """Create API reference documentation tab"""
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('Courier', 9))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        api_text = """
API REFERENCE

SYSTEM CONTROLLER API:

class SystemController:
    def start_system() -> bool
        Start the detection system
        Returns: True if successful, False otherwise
    
    def stop_system() -> bool
        Stop the detection system
        Returns: True if successful, False otherwise
    
    def pause_system() -> bool
        Pause the detection system
        Returns: True if successful, False otherwise
    
    def resume_system() -> bool
        Resume the paused system
        Returns: True if successful, False otherwise
    
    def get_state() -> SystemState
        Get current system state
        Returns: STOPPED, RUNNING, PAUSED, ERROR
    
    def get_system_info() -> dict
        Get comprehensive system information
        Returns: Dictionary with metrics and status

CONFIGURATION MANAGER API:

class ConfigManager:
    def get_config(key: str) -> any
        Get configuration value
    
    def set_config(key: str, value: any) -> bool
        Set configuration value
    
    def get_all_config() -> dict
        Get all configuration settings
    
    def save_config() -> bool
        Save configuration to file
    
    def load_config() -> bool
        Load configuration from file

LOGGER API:

Functions:
    log_info(message: str)
    log_warning(message: str)
    log_error(message: str)
    log_debug(message: str)
    get_recent_logs(count: int) -> list

SCANNER API:

class Scanner:
    def perform_scan_with_retry() -> bool
        Perform detection scan with retry logic
    
    def detect_text(text: str, confidence: float) -> bool
        Detect specific text on screen
    
    def detect_image(image_path: str, confidence: float) -> bool
        Detect image pattern on screen

EVENT CALLBACKS:

System events that can be monitored:
• on_system_state_change(old_state, new_state)
• on_scan_complete(success, details)
• on_detection_found(target, location)
• on_action_performed(action, result)
• on_error_occurred(error_type, message)

CONFIGURATION KEYS:

• 'scan_interval': float (seconds)
• 'ocr_confidence': float (0.0-1.0)
• 'max_retries': int
• 'timeout': float (seconds)
• 'log_level': str ('DEBUG', 'INFO', 'WARNING', 'ERROR')
• 'detection_regions': list of tuples
• 'target_images': list of file paths
• 'action_sequences': list of action definitions
"""
        
        text_widget.insert(tk.END, api_text)
        text_widget.config(state=tk.DISABLED)
    
    def _on_system_state_change(self, old_state, new_state):
        """Handle system state changes"""
        try:
            self.root.after(0, self._update_system_status)
        except Exception as e:
            print(f"Error handling state change: {e}")
    
    def _on_scan_event(self, event_type, scan_data):
        """Handle scan events"""
        try:
            # Update dashboard with latest scan data
            self.root.after(0, self._update_dashboard)
        except Exception as e:
            print(f"Error handling scan event: {e}")
    
    def _update_system_status(self):
        """Update system status display"""
        try:
            state = self.controller.get_state()
            
            # Update status labels based on system state
            if state == SystemState.RUNNING:
                status_text = "Running"
                status_style = 'Success.TLabel'
            elif state == SystemState.PAUSED:
                status_text = "Paused"
                status_style = 'Warning.TLabel'
            elif state == SystemState.STARTING:
                status_text = "Starting"
                status_style = 'Status.TLabel'
            elif state == SystemState.STOPPING:
                status_text = "Stopping"
                status_style = 'Status.TLabel'
            elif state == SystemState.ERROR:
                status_text = "Error"
                status_style = 'Error.TLabel'
            else:
                status_text = "Stopped"
                status_style = 'Error.TLabel'
            
            if hasattr(self, 'status_labels') and 'system_state' in self.status_labels:
                self.status_labels['system_state'].config(text=status_text, style=status_style)
                
        except Exception as e:
            print(f"Error updating system status: {e}")
    
    def _on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.is_running = False
            # Stop the system controller if running
            try:
                if self.controller.is_running():
                    self.controller.stop_system()
            except Exception as e:
                print(f"Error stopping system on close: {e}")
            self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

def main():
    """Main entry point for the GUI application"""
    try:
        app = SystemMonitorGUI()
        app.run()
    except Exception as e:
        print(f"Error starting GUI application: {e}")
        messagebox.showerror("Error", f"Failed to start application: {e}")

if __name__ == "__main__":
    main()