"""Module for system logging and statistics management.

This module provides complete functionality for:
- Structured logging with timestamps
- Performance statistics monitoring
- System status reports
- Error handling and metrics
"""

import time
import os
from datetime import datetime
from config import (
    LOG_FILE, TIMESTAMP_FORMAT, LOG_SEPARATOR, SUB_SEPARATOR,
    STATUS_REPORT_FREQUENCY, MAX_SCAN_TIMES_HISTORY,
    get_initial_stats
)

# Global system statistics
stats = get_initial_stats()

def log_message(message, level="INFO", include_separator=False):
    """Records a message in the log file with timestamp.
    
    Args:
        message (str): The message to record
        level (str): Log level (INFO, ERROR, WARNING, DEBUG)
        include_separator (bool): Whether to include a separator before the message
    """
    try:
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Print to console
        print(log_entry)
        
        # Write to file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            if include_separator:
                f.write(f"\n{LOG_SEPARATOR}\n")
            f.write(log_entry + "\n")
            
    except Exception as e:
        # Fallback: print only to console if file is not accessible
        print(f"[{datetime.now().strftime(TIMESTAMP_FORMAT)}] [ERROR] Logging error: {e}")
        print(f"[{datetime.now().strftime(TIMESTAMP_FORMAT)}] [{level}] {message}")

def log_error(message, exception=None):
    """Records an error message with optional exception details.
    
    Args:
        message (str): Error message
        exception (Exception, optional): Exception to include in details
    """
    error_msg = message
    if exception:
        error_msg += f" - Details: {str(exception)}"
    
    log_message(error_msg, "ERROR")
    
    # Update error statistics
    stats['total_errors'] += 1

def log_warning(message):
    """Records a warning message.
    
    Args:
        message (str): Warning message
    """
    log_message(message, "WARNING")

def log_debug(message):
    """Records a debug message.
    
    Args:
        message (str): Debug message
    """
    log_message(message, "DEBUG")

def log_startup_messages():
    """Records system startup messages."""
    from config import STARTUP_MESSAGES
    
    log_message("", include_separator=True)
    log_message(STARTUP_MESSAGES['title'])
    log_message(STARTUP_MESSAGES['target'])
    log_message(STARTUP_MESSAGES['objective'])
    log_message(STARTUP_MESSAGES['mode'])
    log_message(STARTUP_MESSAGES['interval'])
    log_message(STARTUP_MESSAGES['interrupt'])
    log_message("", include_separator=True)

def update_scan_stats(scan_successful=True, scan_time=None):
    """Updates scan statistics.
    
    Args:
        scan_successful (bool): Whether the scan was completed successfully
        scan_time (float, optional): Time taken for the scan in seconds
    """
    stats['total_scans'] += 1
    
    if scan_successful:
        stats['successful_detections'] += 1
        stats['consecutive_failures'] = 0
    else:
        stats['failed_scans'] += 1
        stats['consecutive_failures'] += 1
        
        # Update maximum consecutive failures
        if stats['consecutive_failures'] > stats['max_consecutive_failures']:
            stats['max_consecutive_failures'] = stats['consecutive_failures']
    
    # Update performance metrics if time is provided
    if scan_time is not None:
        update_performance_stats(scan_time)

def update_performance_stats(scan_time):
    """Updates performance statistics with scan time.
    
    Args:
        scan_time (float): Scan time in seconds
    """
    try:
        metrics = stats['performance_metrics']
        
        # Add the new time to the list
        metrics['scan_times'].append(scan_time)
        
        # Keep only the last N times for efficiency
        if len(metrics['scan_times']) > MAX_SCAN_TIMES_HISTORY:
            metrics['scan_times'] = metrics['scan_times'][-MAX_SCAN_TIMES_HISTORY:]
        
        # Calculate statistics
        if metrics['scan_times']:
            metrics['avg_scan_time'] = sum(metrics['scan_times']) / len(metrics['scan_times'])
            metrics['max_scan_time'] = max(metrics['max_scan_time'], scan_time)
            
            if metrics['min_scan_time'] == float('inf'):
                metrics['min_scan_time'] = scan_time
            else:
                metrics['min_scan_time'] = min(metrics['min_scan_time'], scan_time)
        
        log_debug(f"Scan time: {scan_time:.2f}s (Average: {metrics['avg_scan_time']:.2f}s)")
        
    except Exception as e:
        log_error(f"Error updating performance statistics: {e}")

def record_successful_detection():
    """Records a successful detection."""
    stats['last_successful_detection'] = time.time()
    log_message("✅ Target message detection completed successfully!")

def record_click_performed():
    """Records a performed click."""
    stats['clicks_performed'] += 1
    stats['last_click_time'] = time.time()
    log_message(f"🖱️ Automatic click performed! (Total: {stats['clicks_performed']})")

def record_click_error():
    """Records a click error."""
    stats['click_errors'] += 1
    log_error("❌ Error during automatic click execution")

def record_screenshot_error():
    """Records a screenshot error."""
    stats['screenshot_errors'] += 1
    log_error("📸 Error during screenshot capture")

def record_ocr_error():
    """Records an OCR error."""
    stats['ocr_errors'] += 1
    log_error("🔍 Error during OCR text extraction")

def record_enhancement_error():
    """Records an image enhancement error."""
    stats['enhancement_errors'] += 1
    log_error("🎨 Error during image enhancement")

def get_uptime():
    """Calculates and returns system uptime in seconds.
    
    Returns:
        float: Uptime in seconds
    """
    return time.time() - stats['start_time']

def format_uptime(uptime_seconds):
    """Formats uptime in readable format.
    
    Args:
        uptime_seconds (float): Uptime in seconds
        
    Returns:
        str: Formatted uptime (e.g. "2h 30m 45s")
    """
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def calculate_success_rate():
    """Calculates scan success rate.
    
    Returns:
        float: Success rate as percentage (0-100)
    """
    if stats['total_scans'] == 0:
        return 0.0
    return (stats['successful_detections'] / stats['total_scans']) * 100

def get_time_since_last_detection():
    """Calculates time elapsed since last successful detection.
    
    Returns:
        str: Formatted time or "Never" if no detections occurred
    """
    if stats['last_successful_detection'] is None:
        return "Never"
    
    time_diff = time.time() - stats['last_successful_detection']
    return format_uptime(time_diff)

def get_time_since_last_click():
    """Calculates time elapsed since last click.
    
    Returns:
        str: Formatted time or "Never" if no clicks occurred
    """
    if stats['last_click_time'] is None:
        return "Never"
    
    time_diff = time.time() - stats['last_click_time']
    return format_uptime(time_diff)

def log_system_status():
    """Logs a complete system status report."""
    try:
        uptime = get_uptime()
        success_rate = calculate_success_rate()
        
        log_message("", include_separator=True)
        log_message("📊 SYSTEM STATUS REPORT")
        log_message(f"⏱️ Uptime: {format_uptime(uptime)}")
        log_message(f"🔍 Total scans: {stats['total_scans']}")
        log_message(f"✅ Successful detections: {stats['successful_detections']}")
        log_message(f"❌ Failed scans: {stats['failed_scans']}")
        log_message(f"📈 Success rate: {success_rate:.1f}%")
        log_message(f"🖱️ Clicks performed: {stats['clicks_performed']}")
        log_message(f"🔄 Consecutive failures: {stats['consecutive_failures']}")
        log_message(f"📊 Max consecutive failures: {stats['max_consecutive_failures']}")
        
        # Error statistics
        log_message(f"🚨 Total errors: {stats['total_errors']}")
        log_message(f"  📸 Screenshot errors: {stats['screenshot_errors']}")
        log_message(f"  🔍 OCR errors: {stats['ocr_errors']}")
        log_message(f"  🖱️ Click errors: {stats['click_errors']}")
        log_message(f"  🎨 Enhancement errors: {stats['enhancement_errors']}")
        
        # Performance metrics
        metrics = stats['performance_metrics']
        if metrics['scan_times']:
            log_message(f"⚡ Scan performance:")
            log_message(f"  📊 Average time: {metrics['avg_scan_time']:.2f}s")
            log_message(f"  ⚡ Minimum time: {metrics['min_scan_time']:.2f}s")
            log_message(f"  🐌 Maximum time: {metrics['max_scan_time']:.2f}s")
        
        # Last activity times
        log_message(f"🕐 Last detection: {get_time_since_last_detection()} ago")
        log_message(f"🕐 Last click: {get_time_since_last_click()} ago")
        
        log_message("", include_separator=True)
        
    except Exception as e:
        log_error(f"Error generating status report: {e}")

def should_log_status_report():
    """Determines if it's time to log a status report.
    
    Returns:
        bool: True if a report should be logged
    """
    return stats['total_scans'] > 0 and stats['total_scans'] % STATUS_REPORT_FREQUENCY == 0

def reset_consecutive_failures():
    """Resets the consecutive failures counter."""
    stats['consecutive_failures'] = 0
    log_message("🔄 Consecutive failures counter reset")

def get_stats_copy():
    """Returns a copy of current statistics.
    
    Returns:
        dict: Copy of statistics
    """
    return stats.copy()

def log_scan_start(scan_number):
    """Logs the start of a new scan.
    
    Args:
        scan_number (int): Scan number
    """
    log_message(f"🔍 Starting scan #{scan_number}...")

def log_scan_complete(scan_number, found_target=False, coordinates=None):
    """Logs the completion of a scan.
    
    Args:
        scan_number (int): Scan number
        found_target (bool): Whether target was found
        coordinates (tuple, optional): Found coordinates
    """
    if found_target and coordinates:
        log_message(f"✅ Scan #{scan_number} completed - Target found at coordinates {coordinates}")
    else:
        log_message(f"❌ Scan #{scan_number} completed - Target not found")

def log_enhancement_stats(method_name, detections_count):
    """Logs enhancement statistics for a specific method.
    
    Args:
        method_name (str): Enhancement method name
        detections_count (int): Number of detections found
    """
    log_debug(f"Enhancement {method_name}: {detections_count} valid detections")

def log_coordinates_found(word, coordinates):
    """Logs the finding of coordinates for a word.
    
    Args:
        word (str): Found word
        coordinates (tuple): Coordinates (x, y)
    """
    log_message(f"🎯 Coordinates found for '{word}': {coordinates}")

def log_extended_wait_start():
    """Logs the start of an extended wait."""
    from config import EXTENDED_WAIT_TIME
    log_message(f"⏳ Too many consecutive failures. Extended wait of {EXTENDED_WAIT_TIME//60} minutes...")

def log_extended_wait_complete():
    """Logs the completion of an extended wait."""
    log_message("✅ Extended wait completed. Resuming normal scans.")

def setup_logging():
    """Initializes the logging system.
    
    Creates the log file if it doesn't exist and logs system startup.
    """
    try:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Log system startup
        log_message("🚀 Automatic detection system started", include_separator=True)
        log_message(f"📁 Log file: {LOG_FILE}")
        
    except Exception as e:
        print(f"Error during logging initialization: {e}")

def log_system_startup():
    """Logs system startup with detailed information."""
    log_message("🚀 Automatic detection system started", include_separator=True)
    log_message(f"📁 Log file: {LOG_FILE}")
    log_message(f"⏰ Startup: {datetime.now().strftime(TIMESTAMP_FORMAT)}")

def log_system_shutdown():
    """Logs system shutdown."""
    uptime = get_uptime()
    log_message("🛑 Automatic detection system stopped", include_separator=True)
    log_message(f"⏱️ Total uptime: {format_uptime(uptime)}")
    log_message(f"🔍 Total scans: {stats['total_scans']}")
    log_message(f"✅ Successful detections: {stats['successful_detections']}")

def log_scan_interval(scan_number, interval_minutes):
    """Logs scan interval."""
    log_message(f"⏰ Next scan #{scan_number} in {interval_minutes} minutes...")

def should_log_status_report():
    """Determines if it's time to log a status report."""
    return stats['total_scans'] % STATUS_REPORT_FREQUENCY == 0

def get_stats_copy():
    """Returns a copy of current statistics."""
    return stats.copy()

def get_logger():
    """Returns a logger-like object with standard logging methods.
    
    Returns:
        object: Logger object with info, error, warning, debug methods
    """
    class Logger:
        def info(self, message):
            log_message(message, "INFO")
        
        def error(self, message):
            log_message(message, "ERROR")
        
        def warning(self, message):
            log_message(message, "WARNING")
        
        def debug(self, message):
            log_message(message, "DEBUG")
            
        def get_recent_logs(self, count=100):
            """Get recent log entries from the log file."""
            return get_recent_logs(count)
    
    return Logger()

def get_recent_logs(count=100):
    """Get recent log entries from the log file.
    
    Args:
        count (int): Number of recent log entries to retrieve
        
    Returns:
        list: List of dictionaries containing log entries with timestamp, level, and message
    """
    logs = []
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            # Get the last 'count' lines
            recent_lines = lines[-count:] if len(lines) > count else lines
            
            for line in recent_lines:
                line = line.strip()
                if line and line.startswith('['):
                    try:
                        # Parse log format: [timestamp] [level] message
                        parts = line.split('] ', 2)
                        if len(parts) >= 3:
                            timestamp = parts[0][1:]  # Remove opening bracket
                            level = parts[1][1:]      # Remove opening bracket
                            message = parts[2]
                            
                            logs.append({
                                'timestamp': timestamp,
                                'level': level,
                                'message': message
                            })
                        else:
                            # Handle malformed lines
                            logs.append({
                                'timestamp': datetime.now().strftime('%H:%M:%S'),
                                'level': 'INFO',
                                'message': line
                            })
                    except Exception:
                        # Handle parsing errors
                        logs.append({
                            'timestamp': datetime.now().strftime('%H:%M:%S'),
                            'level': 'INFO',
                            'message': line
                        })
                        
    except Exception as e:
        # Return error log if file reading fails
        logs.append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'level': 'ERROR',
            'message': f'Failed to read log file: {e}'
        })
        
    return logs