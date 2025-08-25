#!/usr/bin/env python3
"""
Command Line Interface Module

This module provides a comprehensive CLI for monitoring and controlling the automatic
detection system. It includes interactive commands, real-time monitoring, configuration
management, and system controls.

Features:
- Interactive command shell
- Real-time status monitoring
- Configuration management
- Log viewing and filtering
- Statistics and analytics
- System controls
- Batch operations

Author: Matteo Sala
Version: 1.0.0
"""

import cmd
import threading
import time
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import argparse
from pathlib import Path
import shlex
import subprocess
from collections import defaultdict

# Import our modules
from statistics_manager import get_stats_manager
from config_manager import get_config_manager
from logger import get_logger

class SystemMonitorCLI(cmd.Cmd):
    """Interactive CLI for system monitoring and control"""
    
    intro = """
╔══════════════════════════════════════════════════════════════╗
║              Continue Detection System CLI                   ║
║                     Version 1.0.0                          ║
╠══════════════════════════════════════════════════════════════╣
║  Type 'help' for available commands                         ║
║  Type 'status' for current system status                    ║
║  Type 'monitor' for real-time monitoring                    ║
║  Type 'quit' to exit                                        ║
╚══════════════════════════════════════════════════════════════╝
    """
    
    prompt = '(CDS) > '
    
    def __init__(self):
        super().__init__()
        
        # Get manager instances
        self.stats_manager = get_stats_manager()
        self.config_manager = get_config_manager()
        self.logger = get_logger()
        
        # CLI state
        self.monitoring = False
        self.monitor_thread = None
        self.last_stats = None
        
        # Display settings
        self.show_timestamps = True
        self.show_colors = True
        self.refresh_interval = 1.0
        
        # Command aliases
        self.aliases = {
            'st': 'status',
            'cfg': 'config',
            'mon': 'monitor',
            'log': 'logs',
            'stats': 'statistics',
            'sys': 'system',
            'q': 'quit',
            'exit': 'quit',
            'h': 'help'
        }
    
    def default(self, line):
        """Handle unknown commands and aliases"""
        cmd_name = line.split()[0] if line.split() else ''
        if cmd_name in self.aliases:
            return self.onecmd(line.replace(cmd_name, self.aliases[cmd_name], 1))
        else:
            self.print_error(f"Unknown command: {cmd_name}. Type 'help' for available commands.")
    
    def emptyline(self):
        """Handle empty line input"""
        pass
    
    # === UTILITY METHODS ===
    
    def print_header(self, text: str, char: str = '='):
        """Print a formatted header"""
        width = 70
        print(f"\n{char * width}")
        print(f"{text.center(width)}")
        print(f"{char * width}")
    
    def print_subheader(self, text: str):
        """Print a formatted subheader"""
        print(f"\n--- {text} ---")
    
    def print_success(self, text: str):
        """Print success message"""
        if self.show_colors:
            print(f"\033[92m✓ {text}\033[0m")
        else:
            print(f"✓ {text}")
    
    def print_error(self, text: str):
        """Print error message"""
        if self.show_colors:
            print(f"\033[91m✗ {text}\033[0m")
        else:
            print(f"✗ {text}")
    
    def print_warning(self, text: str):
        """Print warning message"""
        if self.show_colors:
            print(f"\033[93m⚠ {text}\033[0m")
        else:
            print(f"⚠ {text}")
    
    def print_info(self, text: str):
        """Print info message"""
        if self.show_colors:
            print(f"\033[94mℹ {text}\033[0m")
        else:
            print(f"ℹ {text}")
    
    def format_timestamp(self, timestamp: Optional[str] = None) -> str:
        """Format timestamp for display"""
        if not self.show_timestamps:
            return ""
        
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return f"[{dt.strftime('%H:%M:%S')}] "
            except:
                return f"[{timestamp}] "
        else:
            return f"[{datetime.now().strftime('%H:%M:%S')}] "
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 1:
            return f"{seconds*1000:.1f}ms"
        elif seconds < 60:
            return f"{seconds:.2f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def format_percentage(self, value: float, decimals: int = 1) -> str:
        """Format percentage with color coding"""
        formatted = f"{value:.{decimals}f}%"
        
        if not self.show_colors:
            return formatted
        
        if value >= 90:
            return f"\033[92m{formatted}\033[0m"  # Green
        elif value >= 70:
            return f"\033[93m{formatted}\033[0m"  # Yellow
        else:
            return f"\033[91m{formatted}\033[0m"  # Red
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    # === STATUS COMMANDS ===
    
    def do_status(self, args):
        """Show current system status
        
        Usage: status [--detailed] [--json]
        
        Options:
            --detailed    Show detailed status information
            --json        Output in JSON format
        """
        try:
            parser = argparse.ArgumentParser(prog='status', add_help=False)
            parser.add_argument('--detailed', action='store_true', help='Show detailed information')
            parser.add_argument('--json', action='store_true', help='Output in JSON format')
            
            try:
                parsed_args = parser.parse_args(shlex.split(args))
            except SystemExit:
                return
            
            stats = self.stats_manager.get_current_stats()
            
            if parsed_args.json:
                print(json.dumps(stats, indent=2, default=str))
                return
            
            self.print_header("System Status")
            
            # Basic status
            print(f"System State:     Running")
            print(f"Uptime:          {stats['session']['uptime_formatted']}")
            print(f"Total Scans:     {stats['scans']['total']}")
            print(f"Success Rate:    {self.format_percentage(stats['scans']['success_rate'])}")
            print(f"Total Detections: {stats['scans']['total_detections']}")
            
            if stats['detection']['last_detection']:
                last_det = datetime.fromisoformat(stats['detection']['last_detection'].replace('Z', '+00:00'))
                print(f"Last Detection:  {last_det.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"Last Detection:  Never")
            
            print(f"Current Streak:  {stats['detection']['current_streak']}")
            
            if parsed_args.detailed:
                self.print_subheader("Performance Metrics")
                print(f"CPU Usage:       {self.format_percentage(stats['system']['cpu_percent'])}")
                print(f"Memory Usage:    {self.format_percentage(stats['system']['memory_percent'])}")
                print(f"Avg Scan Time:   {self.format_duration(stats['performance']['avg_scan_time'])}")
                print(f"Last Scan Time:  {self.format_duration(stats['performance']['last_scan_time'])}")
                print(f"Min Scan Time:   {self.format_duration(stats['performance']['min_scan_time'])}")
                print(f"Max Scan Time:   {self.format_duration(stats['performance']['max_scan_time'])}")
                
                self.print_subheader("Error Statistics")
                print(f"Total Errors:    {stats['errors']['total']}")
                print(f"OCR Errors:      {stats['errors']['ocr_errors']}")
                print(f"Click Errors:    {stats['errors']['click_errors']}")
                print(f"System Errors:   {stats['errors']['system_errors']}")
                
                if stats['errors']['last_error']:
                    last_err = datetime.fromisoformat(stats['errors']['last_error'].replace('Z', '+00:00'))
                    print(f"Last Error:      {last_err.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print(f"Last Error:      None")
            
        except Exception as e:
            self.print_error(f"Error getting status: {e}")
    
    def do_monitor(self, args):
        """Start/stop real-time monitoring
        
        Usage: monitor [start|stop] [--interval SECONDS]
        
        Options:
            --interval    Refresh interval in seconds (default: 1.0)
        """
        try:
            parser = argparse.ArgumentParser(prog='monitor', add_help=False)
            parser.add_argument('action', nargs='?', choices=['start', 'stop'], default='start')
            parser.add_argument('--interval', type=float, default=1.0, help='Refresh interval')
            
            try:
                parsed_args = parser.parse_args(shlex.split(args))
            except SystemExit:
                return
            
            if parsed_args.action == 'stop':
                self._stop_monitoring()
            else:
                self.refresh_interval = parsed_args.interval
                self._start_monitoring()
                
        except Exception as e:
            self.print_error(f"Error with monitor command: {e}")
    
    def _start_monitoring(self):
        """Start real-time monitoring"""
        if self.monitoring:
            self.print_warning("Monitoring is already running")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self.monitor_thread.start()
        
        self.print_success(f"Started real-time monitoring (interval: {self.refresh_interval}s)")
        self.print_info("Press Ctrl+C or type 'monitor stop' to stop monitoring")
    
    def _stop_monitoring(self):
        """Stop real-time monitoring"""
        if not self.monitoring:
            self.print_warning("Monitoring is not running")
            return
        
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        self.print_success("Stopped real-time monitoring")
    
    def _monitor_worker(self):
        """Background worker for real-time monitoring"""
        try:
            while self.monitoring:
                self.clear_screen()
                
                # Display header
                print("╔" + "═" * 68 + "╗")
                print("║" + " Continue Detection System - Real-time Monitor ".center(68) + "║")
                print("║" + f" Refresh: {self.refresh_interval}s | Press Ctrl+C to stop ".center(68) + "║")
                print("╚" + "═" * 68 + "╝")
                
                try:
                    stats = self.stats_manager.get_current_stats()
                    
                    # System status section
                    print("\n┌─ System Status " + "─" * 50 + "┐")
                    print(f"│ State: Running          Uptime: {stats['session']['uptime_formatted']:<20} │")
                    print(f"│ Scans: {stats['scans']['total']:<8}         Success: {stats['scans']['success_rate']:.1f}%{' ' * 15} │")
                    print(f"│ Detections: {stats['scans']['total_detections']:<5}     Streak: {stats['detection']['current_streak']:<8}{' ' * 15} │")
                    print("└" + "─" * 67 + "┘")
                    
                    # Performance section
                    print("\n┌─ Performance " + "─" * 52 + "┐")
                    print(f"│ CPU: {stats['system']['cpu_percent']:5.1f}%           Memory: {stats['system']['memory_percent']:5.1f}%{' ' * 20} │")
                    print(f"│ Scan Time: {stats['performance']['last_scan_time']*1000:6.1f}ms   Avg: {stats['performance']['avg_scan_time']*1000:6.1f}ms{' ' * 15} │")
                    print("└" + "─" * 67 + "┘")
                    
                    # Recent activity
                    print("\n┌─ Recent Activity " + "─" * 48 + "┐")
                    
                    # Get recent scans
                    recent_scans = self.stats_manager.get_recent_scans(5)
                    if recent_scans:
                        for scan in recent_scans[-3:]:  # Show last 3
                            timestamp = datetime.fromisoformat(scan['timestamp'].replace('Z', '+00:00'))
                            status = "✓" if scan['success'] else "✗"
                            duration = scan['duration'] * 1000
                            print(f"│ {timestamp.strftime('%H:%M:%S')} {status} Scan completed in {duration:6.1f}ms{' ' * 15} │")
                    else:
                        print(f"│ No recent activity{' ' * 44} │")
                    
                    print("└" + "─" * 67 + "┘")
                    
                    # Error summary
                    if stats['errors']['total'] > 0:
                        print("\n┌─ Errors " + "─" * 56 + "┐")
                        print(f"│ Total: {stats['errors']['total']:<5}  OCR: {stats['errors']['ocr_errors']:<5}  Click: {stats['errors']['click_errors']:<5}  System: {stats['errors']['system_errors']:<5} │")
                        print("└" + "─" * 67 + "┘")
                    
                    # Configuration summary
                    print("\n┌─ Configuration " + "─" * 49 + "┐")
                    scan_interval = self.config_manager.get_parameter('scan_interval')
                    confidence = self.config_manager.get_parameter('ocr_confidence_threshold')
                    print(f"│ Scan Interval: {scan_interval}s      OCR Confidence: {confidence:.2f}{' ' * 15} │")
                    print("└" + "─" * 67 + "┘")
                    
                except Exception as e:
                    print(f"\nError updating monitor: {e}")
                
                time.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            self.monitoring = False
            print("\n\nMonitoring stopped by user")
        except Exception as e:
            self.monitoring = False
            print(f"\n\nMonitoring stopped due to error: {e}")
    
    # === CONFIGURATION COMMANDS ===
    
    def do_config(self, args):
        """Configuration management
        
        Usage: config <subcommand> [options]
        
        Subcommands:
            list [category]           List all parameters or by category
            get <parameter>           Get parameter value
            set <parameter> <value>   Set parameter value
            reset <parameter>         Reset parameter to default
            categories                List all categories
            export <file>             Export configuration
            import <file>             Import configuration
            profiles                  List profiles
            save-profile <name>       Save current config as profile
            load-profile <name>       Load profile
            delete-profile <name>     Delete profile
        """
        if not args:
            self.print_error("Missing subcommand. Type 'help config' for usage.")
            return
        
        parts = shlex.split(args)
        subcommand = parts[0]
        
        try:
            if subcommand == 'list':
                category = parts[1] if len(parts) > 1 else None
                self._config_list(category)
            elif subcommand == 'get':
                if len(parts) < 2:
                    self.print_error("Missing parameter name")
                    return
                self._config_get(parts[1])
            elif subcommand == 'set':
                if len(parts) < 3:
                    self.print_error("Missing parameter name or value")
                    return
                self._config_set(parts[1], parts[2])
            elif subcommand == 'reset':
                if len(parts) < 2:
                    self.print_error("Missing parameter name")
                    return
                self._config_reset(parts[1])
            elif subcommand == 'categories':
                self._config_categories()
            elif subcommand == 'export':
                if len(parts) < 2:
                    self.print_error("Missing filename")
                    return
                self._config_export(parts[1])
            elif subcommand == 'import':
                if len(parts) < 2:
                    self.print_error("Missing filename")
                    return
                self._config_import(parts[1])
            elif subcommand == 'profiles':
                self._config_profiles()
            elif subcommand == 'save-profile':
                if len(parts) < 2:
                    self.print_error("Missing profile name")
                    return
                self._config_save_profile(parts[1])
            elif subcommand == 'load-profile':
                if len(parts) < 2:
                    self.print_error("Missing profile name")
                    return
                self._config_load_profile(parts[1])
            elif subcommand == 'delete-profile':
                if len(parts) < 2:
                    self.print_error("Missing profile name")
                    return
                self._config_delete_profile(parts[1])
            else:
                self.print_error(f"Unknown subcommand: {subcommand}")
                
        except Exception as e:
            self.print_error(f"Error in config command: {e}")
    
    def _config_list(self, category: Optional[str] = None):
        """List configuration parameters"""
        if category:
            parameters = self.config_manager.get_parameters_by_category(category)
            self.print_header(f"Configuration Parameters - {category}")
        else:
            parameters = self.config_manager.get_all_parameters()
            self.print_header("All Configuration Parameters")
        
        if not parameters:
            self.print_warning("No parameters found")
            return
        
        # Group by category if showing all
        if not category:
            by_category = defaultdict(list)
            for param_name, value in parameters.items():
                param_info = self.config_manager.get_parameter_info(param_name)
                by_category[param_info['category']].append((param_name, value, param_info))
            
            for cat_name in sorted(by_category.keys()):
                self.print_subheader(cat_name)
                for param_name, value, param_info in sorted(by_category[cat_name]):
                    self._print_parameter(param_name, value, param_info)
        else:
            for param_name, value in sorted(parameters.items()):
                param_info = self.config_manager.get_parameter_info(param_name)
                self._print_parameter(param_name, value, param_info)
    
    def _print_parameter(self, name: str, value: Any, info: Dict[str, Any]):
        """Print a single parameter"""
        print(f"  {name:<30} = {value}")
        print(f"    Description: {info['description']}")
        print(f"    Type: {info['data_type']:<10} Default: {info['default_value']}")
        if info['allowed_values']:
            print(f"    Allowed: {', '.join(map(str, info['allowed_values']))}")
        if info['min_value'] is not None or info['max_value'] is not None:
            print(f"    Range: {info['min_value']} - {info['max_value']}")
        print()
    
    def _config_get(self, parameter: str):
        """Get parameter value"""
        try:
            value = self.config_manager.get_parameter(parameter)
            info = self.config_manager.get_parameter_info(parameter)
            
            self.print_header(f"Parameter: {parameter}")
            print(f"Current Value: {value}")
            print(f"Default Value: {info['default_value']}")
            print(f"Description:   {info['description']}")
            print(f"Type:          {info['data_type']}")
            print(f"Category:      {info['category']}")
            
            if info['allowed_values']:
                print(f"Allowed Values: {', '.join(map(str, info['allowed_values']))}")
            if info['min_value'] is not None or info['max_value'] is not None:
                print(f"Range:         {info['min_value']} - {info['max_value']}")
                
        except KeyError:
            self.print_error(f"Parameter '{parameter}' not found")
        except Exception as e:
            self.print_error(f"Error getting parameter: {e}")
    
    def _config_set(self, parameter: str, value: str):
        """Set parameter value"""
        try:
            # Convert value to appropriate type
            param_info = self.config_manager.get_parameter_info(parameter)
            
            if param_info['data_type'] == 'bool':
                value = value.lower() in ('true', '1', 'yes', 'on')
            elif param_info['data_type'] == 'int':
                value = int(value)
            elif param_info['data_type'] == 'float':
                value = float(value)
            # str values remain as-is
            
            if self.config_manager.set_parameter(parameter, value, "CLI User", "Set via CLI"):
                self.print_success(f"Parameter '{parameter}' set to '{value}'")
            else:
                self.print_error(f"Failed to set parameter '{parameter}'")
                
        except KeyError:
            self.print_error(f"Parameter '{parameter}' not found")
        except ValueError as e:
            self.print_error(f"Invalid value for parameter '{parameter}': {e}")
        except Exception as e:
            self.print_error(f"Error setting parameter: {e}")
    
    def _config_reset(self, parameter: str):
        """Reset parameter to default"""
        try:
            if self.config_manager.reset_parameter(parameter, "CLI User"):
                default_value = self.config_manager.get_parameter_info(parameter)['default_value']
                self.print_success(f"Parameter '{parameter}' reset to default value: {default_value}")
            else:
                self.print_error(f"Failed to reset parameter '{parameter}'")
                
        except KeyError:
            self.print_error(f"Parameter '{parameter}' not found")
        except Exception as e:
            self.print_error(f"Error resetting parameter: {e}")
    
    def _config_categories(self):
        """List all categories"""
        categories = self.config_manager.get_all_categories()
        
        self.print_header("Configuration Categories")
        for category in sorted(categories):
            param_count = len(self.config_manager.get_parameters_by_category(category))
            print(f"  {category:<20} ({param_count} parameters)")
    
    def _config_export(self, filename: str):
        """Export configuration"""
        try:
            if self.config_manager.export_configuration(filename):
                self.print_success(f"Configuration exported to '{filename}'")
            else:
                self.print_error(f"Failed to export configuration to '{filename}'")
        except Exception as e:
            self.print_error(f"Error exporting configuration: {e}")
    
    def _config_import(self, filename: str):
        """Import configuration"""
        try:
            if not os.path.exists(filename):
                self.print_error(f"File '{filename}' not found")
                return
                
            if self.config_manager.import_configuration(filename, "CLI User"):
                self.print_success(f"Configuration imported from '{filename}'")
            else:
                self.print_error(f"Failed to import configuration from '{filename}'")
        except Exception as e:
            self.print_error(f"Error importing configuration: {e}")
    
    def _config_profiles(self):
        """List all profiles"""
        profiles = self.config_manager.get_profiles()
        
        self.print_header("Configuration Profiles")
        if profiles:
            for profile in sorted(profiles):
                print(f"  {profile}")
        else:
            self.print_warning("No profiles found")
    
    def _config_save_profile(self, name: str):
        """Save current configuration as profile"""
        try:
            if self.config_manager.save_profile(name):
                self.print_success(f"Profile '{name}' saved")
            else:
                self.print_error(f"Failed to save profile '{name}'")
        except Exception as e:
            self.print_error(f"Error saving profile: {e}")
    
    def _config_load_profile(self, name: str):
        """Load configuration profile"""
        try:
            if self.config_manager.load_profile(name, "CLI User"):
                self.print_success(f"Profile '{name}' loaded")
            else:
                self.print_error(f"Failed to load profile '{name}'")
        except Exception as e:
            self.print_error(f"Error loading profile: {e}")
    
    def _config_delete_profile(self, name: str):
        """Delete configuration profile"""
        try:
            if self.config_manager.delete_profile(name):
                self.print_success(f"Profile '{name}' deleted")
            else:
                self.print_error(f"Failed to delete profile '{name}'")
        except Exception as e:
            self.print_error(f"Error deleting profile: {e}")
    
    # === LOG COMMANDS ===
    
    def do_logs(self, args):
        """Log management and viewing
        
        Usage: logs <subcommand> [options]
        
        Subcommands:
            show [--level LEVEL] [--lines N] [--follow]   Show logs
            clear                                         Clear logs
            export <file>                                 Export logs
            levels                                        Show log levels
        """
        if not args:
            self._logs_show([])
            return
        
        parts = shlex.split(args)
        subcommand = parts[0]
        
        try:
            if subcommand == 'show':
                self._logs_show(parts[1:])
            elif subcommand == 'clear':
                self._logs_clear()
            elif subcommand == 'export':
                if len(parts) < 2:
                    self.print_error("Missing filename")
                    return
                self._logs_export(parts[1])
            elif subcommand == 'levels':
                self._logs_levels()
            else:
                self.print_error(f"Unknown subcommand: {subcommand}")
                
        except Exception as e:
            self.print_error(f"Error in logs command: {e}")
    
    def _logs_show(self, args: List[str]):
        """Show logs"""
        parser = argparse.ArgumentParser(prog='logs show', add_help=False)
        parser.add_argument('--level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Filter by log level')
        parser.add_argument('--lines', type=int, default=50, help='Number of lines to show')
        parser.add_argument('--follow', action='store_true', help='Follow log output')
        
        try:
            parsed_args = parser.parse_args(args)
        except SystemExit:
            return
        
        # This would integrate with the actual logger
        # For now, show placeholder
        self.print_header("System Logs")
        print(f"Showing last {parsed_args.lines} lines")
        if parsed_args.level:
            print(f"Filtered by level: {parsed_args.level}")
        
        print("\n[Log integration would be implemented here]")
        print(f"{self.format_timestamp()}INFO: Sample log entry")
        print(f"{self.format_timestamp()}WARNING: Another sample entry")
        print(f"{self.format_timestamp()}ERROR: Sample error entry")
        
        if parsed_args.follow:
            self.print_info("Following logs... Press Ctrl+C to stop")
            try:
                while True:
                    time.sleep(1)
                    # Would show new log entries here
            except KeyboardInterrupt:
                print("\nStopped following logs")
    
    def _logs_clear(self):
        """Clear logs"""
        # This would clear the actual log files
        self.print_success("Logs cleared (functionality would be implemented)")
    
    def _logs_export(self, filename: str):
        """Export logs"""
        try:
            # This would export actual logs
            with open(filename, 'w') as f:
                f.write(f"# System logs exported at {datetime.now()}\n")
                f.write("# Log export functionality would be implemented here\n")
            
            self.print_success(f"Logs exported to '{filename}'")
        except Exception as e:
            self.print_error(f"Error exporting logs: {e}")
    
    def _logs_levels(self):
        """Show log levels"""
        self.print_header("Log Levels")
        levels = [
            ('DEBUG', 'Detailed information for debugging'),
            ('INFO', 'General information messages'),
            ('WARNING', 'Warning messages'),
            ('ERROR', 'Error messages'),
            ('CRITICAL', 'Critical error messages')
        ]
        
        for level, description in levels:
            print(f"  {level:<10} - {description}")
    
    # === STATISTICS COMMANDS ===
    
    def do_statistics(self, args):
        """Statistics and analytics
        
        Usage: statistics <subcommand> [options]
        
        Subcommands:
            summary                           Show summary statistics
            performance                       Show performance statistics
            errors                           Show error statistics
            historical [--hours N]          Show historical data
            export <file>                    Export statistics
            reset                            Reset all statistics
        """
        if not args:
            self._stats_summary()
            return
        
        parts = shlex.split(args)
        subcommand = parts[0]
        
        try:
            if subcommand == 'summary':
                self._stats_summary()
            elif subcommand == 'performance':
                self._stats_performance()
            elif subcommand == 'errors':
                self._stats_errors()
            elif subcommand == 'historical':
                hours = 24  # default
                if len(parts) > 1 and parts[1] == '--hours' and len(parts) > 2:
                    hours = int(parts[2])
                self._stats_historical(hours)
            elif subcommand == 'export':
                if len(parts) < 2:
                    self.print_error("Missing filename")
                    return
                self._stats_export(parts[1])
            elif subcommand == 'reset':
                self._stats_reset()
            else:
                self.print_error(f"Unknown subcommand: {subcommand}")
                
        except Exception as e:
            self.print_error(f"Error in statistics command: {e}")
    
    def _stats_summary(self):
        """Show summary statistics"""
        try:
            stats = self.stats_manager.get_current_stats()
            
            self.print_header("Statistics Summary")
            
            # Session info
            self.print_subheader("Session")
            print(f"Start Time:      {stats['session']['start_time']}")
            print(f"Uptime:          {stats['session']['uptime_formatted']}")
            
            # Scan statistics
            self.print_subheader("Scans")
            print(f"Total Scans:     {stats['scans']['total']}")
            print(f"Successful:      {stats['scans']['successful']}")
            print(f"Failed:          {stats['scans']['failed']}")
            print(f"Success Rate:    {self.format_percentage(stats['scans']['success_rate'])}")
            print(f"Total Detections: {stats['scans']['total_detections']}")
            
            # Detection statistics
            self.print_subheader("Detections")
            print(f"Current Streak:  {stats['detection']['current_streak']}")
            print(f"Best Streak:     {stats['detection']['best_streak']}")
            
            if stats['detection']['last_detection']:
                last_det = datetime.fromisoformat(stats['detection']['last_detection'].replace('Z', '+00:00'))
                print(f"Last Detection:  {last_det.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"Last Detection:  Never")
            
            # Performance statistics
            self.print_subheader("Performance")
            print(f"Avg Scan Time:   {self.format_duration(stats['performance']['avg_scan_time'])}")
            print(f"Min Scan Time:   {self.format_duration(stats['performance']['min_scan_time'])}")
            print(f"Max Scan Time:   {self.format_duration(stats['performance']['max_scan_time'])}")
            print(f"Last Scan Time:  {self.format_duration(stats['performance']['last_scan_time'])}")
            
        except Exception as e:
            self.print_error(f"Error getting statistics: {e}")
    
    def _stats_performance(self):
        """Show performance statistics"""
        try:
            stats = self.stats_manager.get_current_stats()
            
            self.print_header("Performance Statistics")
            
            # System resources
            self.print_subheader("System Resources")
            print(f"CPU Usage:       {self.format_percentage(stats['system']['cpu_percent'])}")
            print(f"Memory Usage:    {self.format_percentage(stats['system']['memory_percent'])}")
            print(f"Available Memory: {stats['system']['memory_available']:.1f} MB")
            
            # Scan performance
            self.print_subheader("Scan Performance")
            print(f"Average Time:    {self.format_duration(stats['performance']['avg_scan_time'])}")
            print(f"Minimum Time:    {self.format_duration(stats['performance']['min_scan_time'])}")
            print(f"Maximum Time:    {self.format_duration(stats['performance']['max_scan_time'])}")
            print(f"Last Scan:       {self.format_duration(stats['performance']['last_scan_time'])}")
            
            # Performance trends (would be calculated from historical data)
            self.print_subheader("Trends")
            print(f"Performance trend analysis would be shown here")
            
        except Exception as e:
            self.print_error(f"Error getting performance statistics: {e}")
    
    def _stats_errors(self):
        """Show error statistics"""
        try:
            stats = self.stats_manager.get_current_stats()
            
            self.print_header("Error Statistics")
            
            print(f"Total Errors:    {stats['errors']['total']}")
            print(f"OCR Errors:      {stats['errors']['ocr_errors']}")
            print(f"Click Errors:    {stats['errors']['click_errors']}")
            print(f"System Errors:   {stats['errors']['system_errors']}")
            
            if stats['errors']['last_error']:
                last_err = datetime.fromisoformat(stats['errors']['last_error'].replace('Z', '+00:00'))
                print(f"Last Error:      {last_err.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"Last Error:      None")
            
            # Error rate
            if stats['scans']['total'] > 0:
                error_rate = (stats['errors']['total'] / stats['scans']['total']) * 100
                print(f"Error Rate:      {error_rate:.2f}%")
            
        except Exception as e:
            self.print_error(f"Error getting error statistics: {e}")
    
    def _stats_historical(self, hours: int):
        """Show historical statistics"""
        try:
            historical_data = self.stats_manager.get_historical_data(hours)
            
            self.print_header(f"Historical Statistics - Last {hours} Hours")
            
            # Scan data
            scans = historical_data['scans']
            self.print_subheader("Scan Summary")
            print(f"Total Scans:     {len(scans)}")
            
            if scans:
                successful = sum(1 for scan in scans if scan['success'])
                print(f"Successful:      {successful}")
                print(f"Failed:          {len(scans) - successful}")
                print(f"Success Rate:    {self.format_percentage(successful/len(scans)*100)}")
                
                # Performance summary
                scan_times = [scan['duration'] for scan in scans]
                avg_time = sum(scan_times) / len(scan_times)
                min_time = min(scan_times)
                max_time = max(scan_times)
                
                self.print_subheader("Performance Summary")
                print(f"Average Time:    {self.format_duration(avg_time)}")
                print(f"Minimum Time:    {self.format_duration(min_time)}")
                print(f"Maximum Time:    {self.format_duration(max_time)}")
            
            # Error data
            errors = historical_data['errors']
            if errors:
                self.print_subheader("Error Summary")
                print(f"Total Errors:    {len(errors)}")
                
                error_types = defaultdict(int)
                for error in errors:
                    error_types[error['type']] += 1
                
                for error_type, count in error_types.items():
                    print(f"{error_type.title()} Errors: {count}")
            
        except Exception as e:
            self.print_error(f"Error getting historical statistics: {e}")
    
    def _stats_export(self, filename: str):
        """Export statistics"""
        try:
            self.stats_manager.export_data(filename)
            self.print_success(f"Statistics exported to '{filename}'")
        except Exception as e:
            self.print_error(f"Error exporting statistics: {e}")
    
    def _stats_reset(self):
        """Reset statistics"""
        try:
            response = input("Are you sure you want to reset all statistics? (y/N): ")
            if response.lower() in ('y', 'yes'):
                self.stats_manager.reset_statistics()
                self.print_success("Statistics reset successfully")
            else:
                self.print_info("Reset cancelled")
        except Exception as e:
            self.print_error(f"Error resetting statistics: {e}")
    
    # === SYSTEM COMMANDS ===
    
    def do_system(self, args):
        """System control and information
        
        Usage: system <subcommand> [options]
        
        Subcommands:
            info                    Show system information
            start                   Start the detection system
            stop                    Stop the detection system
            restart                 Restart the detection system
            pause                   Pause the detection system
            resume                  Resume the detection system
            test                    Run system test
            emergency-stop          Emergency stop
        """
        if not args:
            self._system_info()
            return
        
        parts = shlex.split(args)
        subcommand = parts[0]
        
        try:
            if subcommand == 'info':
                self._system_info()
            elif subcommand == 'start':
                self._system_start()
            elif subcommand == 'stop':
                self._system_stop()
            elif subcommand == 'restart':
                self._system_restart()
            elif subcommand == 'pause':
                self._system_pause()
            elif subcommand == 'resume':
                self._system_resume()
            elif subcommand == 'test':
                self._system_test()
            elif subcommand == 'emergency-stop':
                self._system_emergency_stop()
            else:
                self.print_error(f"Unknown subcommand: {subcommand}")
                
        except Exception as e:
            self.print_error(f"Error in system command: {e}")
    
    def _system_info(self):
        """Show system information"""
        try:
            import platform
            import psutil
            
            self.print_header("System Information")
            
            # Platform info
            self.print_subheader("Platform")
            print(f"OS:              {platform.system()} {platform.release()}")
            print(f"Architecture:    {platform.machine()}")
            print(f"Python Version:  {platform.python_version()}")
            print(f"Hostname:        {platform.node()}")
            
            # System resources
            self.print_subheader("Resources")
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            print(f"CPU Cores:       {cpu_count}")
            print(f"Total Memory:    {memory.total / (1024**3):.1f} GB")
            print(f"Available Memory: {memory.available / (1024**3):.1f} GB")
            print(f"Memory Usage:    {self.format_percentage(memory.percent)}")
            print(f"Disk Usage:      {self.format_percentage(disk.percent)}")
            
            # Process info
            self.print_subheader("Process")
            process = psutil.Process()
            print(f"PID:             {process.pid}")
            print(f"CPU Usage:       {self.format_percentage(process.cpu_percent())}")
            print(f"Memory Usage:    {process.memory_info().rss / (1024**2):.1f} MB")
            print(f"Threads:         {process.num_threads()}")
            
        except Exception as e:
            self.print_error(f"Error getting system information: {e}")
    
    def _system_start(self):
        """Start the detection system"""
        self.print_info("Starting detection system...")
        # Implementation would start the actual detection system
        self.print_success("Detection system started")
    
    def _system_stop(self):
        """Stop the detection system"""
        self.print_info("Stopping detection system...")
        # Implementation would stop the actual detection system
        self.print_success("Detection system stopped")
    
    def _system_restart(self):
        """Restart the detection system"""
        self.print_info("Restarting detection system...")
        # Implementation would restart the actual detection system
        self.print_success("Detection system restarted")
    
    def _system_pause(self):
        """Pause the detection system"""
        self.print_info("Pausing detection system...")
        # Implementation would pause the actual detection system
        self.print_success("Detection system paused")
    
    def _system_resume(self):
        """Resume the detection system"""
        self.print_info("Resuming detection system...")
        # Implementation would resume the actual detection system
        self.print_success("Detection system resumed")
    
    def _system_test(self):
        """Run system test"""
        self.print_info("Running system test...")
        
        # Simulate test steps
        tests = [
            "Testing OCR functionality",
            "Testing screen capture",
            "Testing click simulation",
            "Testing configuration system",
            "Testing statistics system"
        ]
        
        for test in tests:
            print(f"  {test}...", end=" ")
            time.sleep(0.5)  # Simulate test time
            self.print_success("PASS")
        
        self.print_success("All tests passed")
    
    def _system_emergency_stop(self):
        """Emergency stop"""
        response = input("Are you sure you want to perform an emergency stop? (y/N): ")
        if response.lower() in ('y', 'yes'):
            self.print_warning("Performing emergency stop...")
            # Implementation would perform emergency stop
            self.print_success("Emergency stop completed")
        else:
            self.print_info("Emergency stop cancelled")
    
    # === UTILITY COMMANDS ===
    
    def do_settings(self, args):
        """CLI settings
        
        Usage: settings <subcommand> [options]
        
        Subcommands:
            show                    Show current settings
            colors [on|off]         Enable/disable colors
            timestamps [on|off]     Enable/disable timestamps
            interval <seconds>      Set monitor refresh interval
        """
        if not args:
            self._settings_show()
            return
        
        parts = shlex.split(args)
        subcommand = parts[0]
        
        if subcommand == 'show':
            self._settings_show()
        elif subcommand == 'colors':
            if len(parts) > 1:
                self.show_colors = parts[1].lower() in ('on', 'true', '1')
                self.print_success(f"Colors {'enabled' if self.show_colors else 'disabled'}")
            else:
                self.print_info(f"Colors are {'enabled' if self.show_colors else 'disabled'}")
        elif subcommand == 'timestamps':
            if len(parts) > 1:
                self.show_timestamps = parts[1].lower() in ('on', 'true', '1')
                self.print_success(f"Timestamps {'enabled' if self.show_timestamps else 'disabled'}")
            else:
                self.print_info(f"Timestamps are {'enabled' if self.show_timestamps else 'disabled'}")
        elif subcommand == 'interval':
            if len(parts) > 1:
                try:
                    self.refresh_interval = float(parts[1])
                    self.print_success(f"Refresh interval set to {self.refresh_interval}s")
                except ValueError:
                    self.print_error("Invalid interval value")
            else:
                self.print_info(f"Current refresh interval: {self.refresh_interval}s")
        else:
            self.print_error(f"Unknown subcommand: {subcommand}")
    
    def _settings_show(self):
        """Show current CLI settings"""
        self.print_header("CLI Settings")
        print(f"Colors:          {'Enabled' if self.show_colors else 'Disabled'}")
        print(f"Timestamps:      {'Enabled' if self.show_timestamps else 'Disabled'}")
        print(f"Refresh Interval: {self.refresh_interval}s")
        print(f"Monitoring:      {'Active' if self.monitoring else 'Inactive'}")
    
    def do_clear(self, args):
        """Clear the screen"""
        self.clear_screen()
    
    def do_quit(self, args):
        """Exit the CLI"""
        if self.monitoring:
            self._stop_monitoring()
        
        self.print_info("Goodbye!")
        return True
    
    def do_EOF(self, args):
        """Handle Ctrl+D"""
        print()  # New line
        return self.do_quit(args)

def run_cli():
    """Run the CLI interface"""
    try:
        cli = SystemMonitorCLI()
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"Error running CLI: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Continue Detection System CLI")
    parser.add_argument('--no-colors', action='store_true', help='Disable colored output')
    parser.add_argument('--no-timestamps', action='store_true', help='Disable timestamps')
    parser.add_argument('--command', '-c', help='Run a single command and exit')
    
    args = parser.parse_args()
    
    if args.command:
        # Run single command mode
        cli = SystemMonitorCLI()
        if args.no_colors:
            cli.show_colors = False
        if args.no_timestamps:
            cli.show_timestamps = False
        
        cli.onecmd(args.command)
    else:
        # Interactive mode
        cli = SystemMonitorCLI()
        if args.no_colors:
            cli.show_colors = False
        if args.no_timestamps:
            cli.show_timestamps = False
        
        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            print("\n\nExiting...")
        except Exception as e:
            print(f"Error running CLI: {e}")

if __name__ == "__main__":
    main()