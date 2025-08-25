#!/usr/bin/env python3
"""
Interactive Log Viewer with Filtering and Search Capabilities

This module provides a comprehensive log viewing interface with:
- Real-time log monitoring
- Advanced filtering by level, timestamp, and content
- Search functionality with regex support
- Export capabilities
- Multiple viewing modes (GUI and CLI)

Author: Matteo Sala
License: GNU GPL v3.0
"""

import os
import re
import time
import json
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Import static config for default values
try:
    import config as static_config
except ImportError:
    static_config = None

class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class LogEntry:
    """Represents a single log entry"""
    timestamp: datetime
    level: LogLevel
    message: str
    source: str = ""
    line_number: int = 0
    raw_line: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'message': self.message,
            'source': self.source,
            'line_number': self.line_number,
            'raw_line': self.raw_line
        }

class LogFilter:
    """Advanced log filtering system"""
    
    def __init__(self):
        self.level_filter: Optional[LogLevel] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.message_pattern: Optional[str] = None
        self.source_filter: Optional[str] = None
        self.regex_enabled: bool = False
        self.case_sensitive: bool = False
        
    def matches(self, entry: LogEntry) -> bool:
        """Check if log entry matches current filter criteria"""
        # Level filter
        if self.level_filter and entry.level != self.level_filter:
            return False
            
        # Time range filter
        if self.start_time and entry.timestamp < self.start_time:
            return False
        if self.end_time and entry.timestamp > self.end_time:
            return False
            
        # Source filter
        if self.source_filter:
            if self.case_sensitive:
                if self.source_filter not in entry.source:
                    return False
            else:
                if self.source_filter.lower() not in entry.source.lower():
                    return False
                    
        # Message pattern filter
        if self.message_pattern:
            if self.regex_enabled:
                try:
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    if not re.search(self.message_pattern, entry.message, flags):
                        return False
                except re.error:
                    # Invalid regex, fall back to simple string search
                    if self.case_sensitive:
                        if self.message_pattern not in entry.message:
                            return False
                    else:
                        if self.message_pattern.lower() not in entry.message.lower():
                            return False
            else:
                if self.case_sensitive:
                    if self.message_pattern not in entry.message:
                        return False
                else:
                    if self.message_pattern.lower() not in entry.message.lower():
                        return False
                        
        return True

class LogParser:
    """Parses log files and extracts structured log entries"""
    
    def __init__(self):
        # Common log patterns
        self.patterns = [
            # Standard format: 2024-01-15 10:30:45 - INFO - Message
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*-\s*(?P<level>\w+)\s*-\s*(?P<message>.*)',
            # Alternative format: [2024-01-15 10:30:45] INFO: Message
            r'\[(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s*(?P<level>\w+):\s*(?P<message>.*)',
            # Simple format: INFO: Message (with current timestamp)
            r'(?P<level>\w+):\s*(?P<message>.*)',
        ]
        
        self.timestamp_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%d/%m/%Y %H:%M:%S',
            '%m/%d/%Y %H:%M:%S'
        ]
        
    def parse_line(self, line: str, line_number: int = 0) -> Optional[LogEntry]:
        """Parse a single log line into a LogEntry"""
        line = line.strip()
        if not line:
            return None
            
        for pattern in self.patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groupdict()
                
                # Parse timestamp
                timestamp = datetime.now()
                if 'timestamp' in groups and groups['timestamp']:
                    timestamp = self._parse_timestamp(groups['timestamp'])
                    
                # Parse level
                level = LogLevel.INFO
                if 'level' in groups and groups['level']:
                    try:
                        level = LogLevel(groups['level'].upper())
                    except ValueError:
                        level = LogLevel.INFO
                        
                # Extract message
                message = groups.get('message', line)
                
                return LogEntry(
                    timestamp=timestamp,
                    level=level,
                    message=message,
                    line_number=line_number,
                    raw_line=line
                )
                
        # If no pattern matches, treat as info message
        return LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message=line,
            line_number=line_number,
            raw_line=line
        )
        
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string using various formats"""
        for fmt in self.timestamp_formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        # If all formats fail, return current time
        return datetime.now()
        
    def parse_file(self, file_path: str) -> List[LogEntry]:
        """Parse entire log file and return list of log entries"""
        entries = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_number, line in enumerate(f, 1):
                    entry = self.parse_line(line, line_number)
                    if entry:
                        entry.source = os.path.basename(file_path)
                        entries.append(entry)
        except Exception as e:
            print(f"Error parsing log file {file_path}: {e}")
            
        return entries

class LogViewer:
    """Main log viewer class with filtering and search capabilities"""
    
    def __init__(self, log_files: List[str] = None):
        """Initialize log viewer
        
        Args:
            log_files: List of log file paths to monitor
        """
        self.log_files = log_files or []
        if not self.log_files and static_config:
            # Use default log file from config
            default_log = getattr(static_config, 'LOG_FILE', 'log.txt')
            if os.path.exists(default_log):
                self.log_files = [default_log]
                
        self.parser = LogParser()
        self.filter = LogFilter()
        self.entries: List[LogEntry] = []
        self.filtered_entries: List[LogEntry] = []
        
        # Monitoring settings
        self.auto_refresh = False
        self.refresh_interval = 1.0  # seconds
        self.max_entries = 10000
        
        # Threading
        self._stop_monitoring = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        
        # File monitoring
        self._file_positions: Dict[str, int] = {}
        
        # Load initial entries
        self.refresh_logs()
        
    def add_log_file(self, file_path: str):
        """Add a log file to monitor"""
        if file_path not in self.log_files:
            self.log_files.append(file_path)
            self._file_positions[file_path] = 0
            
    def remove_log_file(self, file_path: str):
        """Remove a log file from monitoring"""
        if file_path in self.log_files:
            self.log_files.remove(file_path)
            self._file_positions.pop(file_path, None)
            
    def refresh_logs(self):
        """Refresh log entries from all monitored files"""
        new_entries = []
        
        for file_path in self.log_files:
            if os.path.exists(file_path):
                file_entries = self.parser.parse_file(file_path)
                new_entries.extend(file_entries)
                
        # Sort by timestamp
        new_entries.sort(key=lambda x: x.timestamp)
        
        # Limit entries to prevent memory issues
        if len(new_entries) > self.max_entries:
            new_entries = new_entries[-self.max_entries:]
            
        self.entries = new_entries
        self.apply_filter()
        
    def monitor_new_entries(self):
        """Monitor for new log entries (for real-time viewing)"""
        new_entries = []
        
        for file_path in self.log_files:
            if not os.path.exists(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Get current position or start from beginning
                    current_pos = self._file_positions.get(file_path, 0)
                    f.seek(current_pos)
                    
                    line_number = current_pos
                    for line in f:
                        line_number += 1
                        entry = self.parser.parse_line(line, line_number)
                        if entry:
                            entry.source = os.path.basename(file_path)
                            new_entries.append(entry)
                            
                    # Update position
                    self._file_positions[file_path] = f.tell()
                    
            except Exception as e:
                print(f"Error monitoring file {file_path}: {e}")
                
        if new_entries:
            # Add new entries and sort
            self.entries.extend(new_entries)
            self.entries.sort(key=lambda x: x.timestamp)
            
            # Limit entries
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[-self.max_entries:]
                
            self.apply_filter()
            
        return len(new_entries)
        
    def start_monitoring(self):
        """Start real-time log monitoring"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
            
        self.auto_refresh = True
        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop real-time log monitoring"""
        self.auto_refresh = False
        self._stop_monitoring.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            
    def _monitor_loop(self):
        """Main monitoring loop"""
        while not self._stop_monitoring.is_set():
            try:
                self.monitor_new_entries()
                time.sleep(self.refresh_interval)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(1.0)
                
    def apply_filter(self):
        """Apply current filter to log entries"""
        self.filtered_entries = [entry for entry in self.entries if self.filter.matches(entry)]
        
    def search(self, pattern: str, regex: bool = False, case_sensitive: bool = False) -> List[LogEntry]:
        """Search log entries for specific pattern"""
        results = []
        
        for entry in self.entries:
            if regex:
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    if re.search(pattern, entry.message, flags) or re.search(pattern, entry.raw_line, flags):
                        results.append(entry)
                except re.error:
                    # Invalid regex, fall back to simple search
                    if case_sensitive:
                        if pattern in entry.message or pattern in entry.raw_line:
                            results.append(entry)
                    else:
                        if pattern.lower() in entry.message.lower() or pattern.lower() in entry.raw_line.lower():
                            results.append(entry)
            else:
                if case_sensitive:
                    if pattern in entry.message or pattern in entry.raw_line:
                        results.append(entry)
                else:
                    if pattern.lower() in entry.message.lower() or pattern.lower() in entry.raw_line.lower():
                        results.append(entry)
                        
        return results
        
    def get_entries_by_level(self, level: LogLevel) -> List[LogEntry]:
        """Get all entries of specific log level"""
        return [entry for entry in self.entries if entry.level == level]
        
    def get_entries_by_time_range(self, start_time: datetime, end_time: datetime) -> List[LogEntry]:
        """Get entries within specific time range"""
        return [entry for entry in self.entries 
                if start_time <= entry.timestamp <= end_time]
                
    def get_recent_entries(self, minutes: int = 60) -> List[LogEntry]:
        """Get entries from last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [entry for entry in self.entries if entry.timestamp >= cutoff_time]
        
    def export_entries(self, entries: List[LogEntry], file_path: str, format: str = 'json'):
        """Export log entries to file
        
        Args:
            entries: List of log entries to export
            file_path: Output file path
            format: Export format ('json', 'csv', 'txt')
        """
        try:
            if format.lower() == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([entry.to_dict() for entry in entries], f, indent=2, default=str)
                    
            elif format.lower() == 'csv':
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Timestamp', 'Level', 'Source', 'Message'])
                    for entry in entries:
                        writer.writerow([
                            entry.timestamp.isoformat(),
                            entry.level.value,
                            entry.source,
                            entry.message
                        ])
                        
            elif format.lower() == 'txt':
                with open(file_path, 'w', encoding='utf-8') as f:
                    for entry in entries:
                        f.write(f"{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {entry.level.value} - {entry.message}\n")
                        
            print(f"Exported {len(entries)} entries to {file_path}")
            
        except Exception as e:
            print(f"Error exporting entries: {e}")
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about current log entries"""
        if not self.entries:
            return {}
            
        level_counts = {level.value: 0 for level in LogLevel}
        for entry in self.entries:
            level_counts[entry.level.value] += 1
            
        oldest_entry = min(self.entries, key=lambda x: x.timestamp)
        newest_entry = max(self.entries, key=lambda x: x.timestamp)
        
        return {
            'total_entries': len(self.entries),
            'filtered_entries': len(self.filtered_entries),
            'level_distribution': level_counts,
            'time_range': {
                'oldest': oldest_entry.timestamp.isoformat(),
                'newest': newest_entry.timestamp.isoformat(),
                'span_hours': (newest_entry.timestamp - oldest_entry.timestamp).total_seconds() / 3600
            },
            'sources': list(set(entry.source for entry in self.entries)),
            'monitoring_active': self.auto_refresh
        }

# CLI Interface for Log Viewer
class LogViewerCLI:
    """Command-line interface for the log viewer"""
    
    def __init__(self, log_viewer: LogViewer):
        self.viewer = log_viewer
        self.running = True
        
    def run(self):
        """Run the CLI interface"""
        print("\n" + "="*60)
        print("📋 INTERACTIVE LOG VIEWER")
        print("="*60)
        print("Type 'help' for available commands")
        
        while self.running:
            try:
                command = input("\nlog_viewer> ").strip().lower()
                self.process_command(command)
            except KeyboardInterrupt:
                print("\nExiting log viewer...")
                break
            except Exception as e:
                print(f"Error: {e}")
                
        self.viewer.stop_monitoring()
        
    def process_command(self, command: str):
        """Process CLI commands"""
        parts = command.split()
        if not parts:
            return
            
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == 'help':
            self.show_help()
        elif cmd == 'show':
            self.show_entries(args)
        elif cmd == 'filter':
            self.set_filter(args)
        elif cmd == 'search':
            self.search_entries(args)
        elif cmd == 'stats':
            self.show_statistics()
        elif cmd == 'export':
            self.export_entries(args)
        elif cmd == 'monitor':
            self.toggle_monitoring(args)
        elif cmd == 'refresh':
            self.viewer.refresh_logs()
            print(f"Refreshed logs. Total entries: {len(self.viewer.entries)}")
        elif cmd == 'clear':
            os.system('cls' if os.name == 'nt' else 'clear')
        elif cmd in ['quit', 'exit']:
            self.running = False
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")
            
    def show_help(self):
        """Show help information"""
        help_text = """
Available Commands:

show [count]           - Show recent log entries (default: 20)
filter level <LEVEL>   - Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
filter time <minutes>  - Show entries from last N minutes
filter clear          - Clear all filters
search <pattern>      - Search for pattern in log entries
search regex <pattern> - Search using regex pattern
stats                 - Show log statistics
export <format> <file> - Export entries (formats: json, csv, txt)
monitor start         - Start real-time monitoring
monitor stop          - Stop real-time monitoring
refresh               - Refresh log entries
clear                 - Clear screen
quit/exit             - Exit log viewer

Examples:
  show 50
  filter level ERROR
  filter time 30
  search "error occurred"
  search regex "\\d{4}-\\d{2}-\\d{2}"
  export json logs_export.json
        """
        print(help_text)
        
    def show_entries(self, args):
        """Show log entries"""
        count = 20
        if args:
            try:
                count = int(args[0])
            except ValueError:
                print("Invalid count. Using default: 20")
                
        entries = self.viewer.filtered_entries[-count:] if self.viewer.filtered_entries else self.viewer.entries[-count:]
        
        if not entries:
            print("No log entries found.")
            return
            
        print(f"\nShowing last {len(entries)} entries:")
        print("-" * 80)
        
        for entry in entries:
            timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            level_color = self._get_level_color(entry.level)
            print(f"{timestamp} | {level_color}{entry.level.value:8}{self._reset_color()} | {entry.message}")
            
    def _get_level_color(self, level: LogLevel) -> str:
        """Get ANSI color code for log level"""
        colors = {
            LogLevel.DEBUG: '\033[36m',    # Cyan
            LogLevel.INFO: '\033[32m',     # Green
            LogLevel.WARNING: '\033[33m',  # Yellow
            LogLevel.ERROR: '\033[31m',    # Red
            LogLevel.CRITICAL: '\033[35m'  # Magenta
        }
        return colors.get(level, '')
        
    def _reset_color(self) -> str:
        """Reset ANSI color"""
        return '\033[0m'
        
    def set_filter(self, args):
        """Set log filter"""
        if not args:
            print("Filter options: level <LEVEL>, time <minutes>, clear")
            return
            
        filter_type = args[0]
        
        if filter_type == 'clear':
            self.viewer.filter = LogFilter()
            self.viewer.apply_filter()
            print("Filters cleared.")
            
        elif filter_type == 'level' and len(args) > 1:
            try:
                level = LogLevel(args[1].upper())
                self.viewer.filter.level_filter = level
                self.viewer.apply_filter()
                print(f"Filtering by level: {level.value}")
            except ValueError:
                print(f"Invalid log level: {args[1]}")
                
        elif filter_type == 'time' and len(args) > 1:
            try:
                minutes = int(args[1])
                cutoff_time = datetime.now() - timedelta(minutes=minutes)
                self.viewer.filter.start_time = cutoff_time
                self.viewer.apply_filter()
                print(f"Filtering entries from last {minutes} minutes")
            except ValueError:
                print(f"Invalid time value: {args[1]}")
        else:
            print("Invalid filter command. Use: filter level <LEVEL> or filter time <minutes>")
            
    def search_entries(self, args):
        """Search log entries"""
        if not args:
            print("Usage: search <pattern> or search regex <pattern>")
            return
            
        regex_mode = args[0] == 'regex'
        pattern = ' '.join(args[1:]) if regex_mode else ' '.join(args)
        
        if not pattern:
            print("Please provide a search pattern.")
            return
            
        results = self.viewer.search(pattern, regex=regex_mode)
        
        if not results:
            print(f"No entries found matching: {pattern}")
            return
            
        print(f"\nFound {len(results)} entries matching '{pattern}':")
        print("-" * 80)
        
        for entry in results[-20:]:  # Show last 20 matches
            timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            level_color = self._get_level_color(entry.level)
            print(f"{timestamp} | {level_color}{entry.level.value:8}{self._reset_color()} | {entry.message}")
            
    def show_statistics(self):
        """Show log statistics"""
        stats = self.viewer.get_statistics()
        
        if not stats:
            print("No statistics available.")
            return
            
        print("\n📊 LOG STATISTICS")
        print("=" * 40)
        print(f"Total Entries: {stats['total_entries']}")
        print(f"Filtered Entries: {stats['filtered_entries']}")
        print(f"Monitoring Active: {stats['monitoring_active']}")
        
        print("\nLevel Distribution:")
        for level, count in stats['level_distribution'].items():
            print(f"  {level}: {count}")
            
        if 'time_range' in stats:
            time_range = stats['time_range']
            print(f"\nTime Range:")
            print(f"  Oldest: {time_range['oldest']}")
            print(f"  Newest: {time_range['newest']}")
            print(f"  Span: {time_range['span_hours']:.2f} hours")
            
        if stats['sources']:
            print(f"\nSources: {', '.join(stats['sources'])}")
            
    def export_entries(self, args):
        """Export log entries"""
        if len(args) < 2:
            print("Usage: export <format> <filename>")
            print("Formats: json, csv, txt")
            return
            
        format_type = args[0]
        filename = args[1]
        
        entries = self.viewer.filtered_entries if self.viewer.filtered_entries else self.viewer.entries
        
        if not entries:
            print("No entries to export.")
            return
            
        self.viewer.export_entries(entries, filename, format_type)
        
    def toggle_monitoring(self, args):
        """Toggle real-time monitoring"""
        if not args:
            print("Usage: monitor start|stop")
            return
            
        action = args[0]
        
        if action == 'start':
            self.viewer.start_monitoring()
            print("Real-time monitoring started.")
        elif action == 'stop':
            self.viewer.stop_monitoring()
            print("Real-time monitoring stopped.")
        else:
            print("Invalid action. Use 'start' or 'stop'.")

def main():
    """Main function for standalone usage"""
    import sys
    
    log_files = sys.argv[1:] if len(sys.argv) > 1 else None
    
    viewer = LogViewer(log_files)
    cli = LogViewerCLI(viewer)
    
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        viewer.stop_monitoring()

if __name__ == "__main__":
    main()