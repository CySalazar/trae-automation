#!/usr/bin/env python3
"""
Statistics Manager Module

This module provides comprehensive statistics tracking and performance monitoring
for the automatic detection system. It collects, stores, and provides access
to various metrics including scan performance, detection rates, system health,
and historical data.

Features:
- Real-time performance metrics
- Historical data tracking
- Detection success/failure rates
- System resource monitoring
- Configurable data retention
- Export capabilities

Author: Matteo Sala
Version: 1.0.0
"""

import time
import json
import threading
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
import psutil
import os

# Import static config for default values
try:
    import config as static_config
except ImportError:
    static_config = None

@dataclass
class ScanMetrics:
    """Data class for individual scan metrics"""
    timestamp: float
    scan_number: int
    duration: float
    success: bool
    coordinates_found: int
    cpu_usage: float
    memory_usage: float
    confidence_score: Optional[float] = None
    error_message: Optional[str] = None

@dataclass
class SystemHealth:
    """System health metrics snapshot"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_usage: float
    active_threads: int
    uptime: float
    temperature: Optional[float] = None

class StatisticsManager:
    """Manages all statistics and performance monitoring for the detection system"""
    
    def __init__(self, max_history_size: int = None, data_retention_hours: int = None):
        """
        Initialize the statistics manager
        
        Args:
            max_history_size: Maximum number of records to keep in memory
            data_retention_hours: Hours to retain historical data
        """
        if max_history_size is None:
            max_history_size = getattr(static_config, 'MAX_SCAN_TIMES_HISTORY', 10000) if static_config else 10000
        if data_retention_hours is None:
            data_retention_hours = getattr(static_config, 'DATA_RETENTION_HOURS', 24) if static_config else 24
        self.max_history_size = max_history_size
        self.data_retention_hours = data_retention_hours
        self.start_time = time.time()
        
        # Thread-safe data structures
        self._lock = threading.RLock()
        
        # Scan metrics storage
        self.scan_history: deque = deque(maxlen=max_history_size)
        self.system_health_history: deque = deque(maxlen=max_history_size)
        
        # Initialize statistics from config if available
        initial_stats = getattr(static_config, 'get_initial_stats', lambda: {})() if static_config else {}
        
        # Real-time counters
        self.total_scans = initial_stats.get('total_scans', 0)
        self.successful_scans = initial_stats.get('successful_scans', 0)
        self.failed_scans = initial_stats.get('failed_scans', 0)
        self.total_detections = initial_stats.get('total_detections', 0)
        
        # Performance metrics
        initial_performance = initial_stats.get('performance_metrics', {}) if initial_stats else {}
        self.avg_scan_time = initial_performance.get('avg_scan_time', 0.0)
        self.min_scan_time = initial_performance.get('min_scan_time', float('inf'))
        self.max_scan_time = initial_performance.get('max_scan_time', 0.0)
        self.last_scan_time = initial_performance.get('last_scan_time', 0.0)
        
        # Session statistics
        self.session_start = datetime.now()
        self.last_detection_time = None
        self.detection_streak = 0
        self.longest_streak = 0
        
        # Click tracking
        self.total_clicks = 0
        self.successful_clicks = 0
        self.failed_clicks = 0
        
        # Error tracking
        self.error_counts = defaultdict(int)
        self.recent_errors = deque(maxlen=100)
        
        # Next scan timing
        self.next_scan_time = None
        self.scan_interval = 0
        
        # Process-specific metrics
        self.process = psutil.Process(os.getpid())
        self.process_cpu_percent = 0.0
        self.process_memory_mb = 0.0
        self.process_memory_percent = 0.0
        
        # System monitoring
        self.system_monitor_active = True
        self.system_monitor_thread = threading.Thread(target=self._monitor_system_health, daemon=True)
        self.system_monitor_thread.start()
    
    def record_scan(self, scan_number: int, duration: float, success: bool, 
                   coordinates_count: int = 0, confidence_score: Optional[float] = None,
                   error_message: Optional[str] = None):
        """Record metrics for a completed scan"""
        with self._lock:
            # Get current system metrics
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            
            # Create scan metrics record
            metrics = ScanMetrics(
                timestamp=time.time(),
                scan_number=scan_number,
                duration=duration,
                success=success,
                coordinates_found=coordinates_count,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                confidence_score=confidence_score,
                error_message=error_message
            )
            
            # Add to history
            self.scan_history.append(metrics)
            
            # Update counters
            self.total_scans += 1
            if success:
                self.successful_scans += 1
                self.total_detections += coordinates_count
                self.last_detection_time = datetime.now()
                self.detection_streak += 1
                self.longest_streak = max(self.longest_streak, self.detection_streak)
            else:
                self.failed_scans += 1
                self.detection_streak = 0
                if error_message:
                    self.error_counts[error_message] += 1
                    self.recent_errors.append({
                        'timestamp': time.time(),
                        'scan_number': scan_number,
                        'error': error_message
                    })
            
            # Update performance metrics
            self.last_scan_time = duration
            self.min_scan_time = min(self.min_scan_time, duration)
            self.max_scan_time = max(self.max_scan_time, duration)
            
            # Calculate rolling average
            recent_scans = list(self.scan_history)[-100:]  # Last 100 scans
            if recent_scans:
                self.avg_scan_time = sum(s.duration for s in recent_scans) / len(recent_scans)
    
    def record_click(self, coordinates: Optional[Tuple[int, int]] = None, success: bool = True):
        """Record a click event"""
        with self._lock:
            self.total_clicks += 1
            if success:
                self.successful_clicks += 1
            else:
                self.failed_clicks += 1
    
    def _monitor_system_health(self):
        """Background thread to monitor system health"""
        while self.system_monitor_active:
            try:
                with self._lock:
                    # Update process-specific metrics
                    try:
                        # Get CPU percent with interval for more accurate reading
                        # Divide by CPU count to normalize to system-wide percentage
                        raw_cpu = self.process.cpu_percent()
                        cpu_count = psutil.cpu_count()
                        self.process_cpu_percent = raw_cpu / cpu_count if cpu_count > 0 else raw_cpu
                        
                        memory_info = self.process.memory_info()
                        self.process_memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
                        self.process_memory_percent = self.process.memory_percent()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # Process might have changed, reinitialize
                        self.process = psutil.Process(os.getpid())
                    
                    # Get system memory info
                    memory_info = psutil.virtual_memory()
                    
                    health = SystemHealth(
                        timestamp=time.time(),
                        cpu_percent=psutil.cpu_percent(),
                        memory_percent=memory_info.percent,
                        memory_used_mb=memory_info.used / 1024 / 1024,  # Convert to MB
                        memory_total_mb=memory_info.total / 1024 / 1024,  # Convert to MB
                        disk_usage=psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
                        active_threads=threading.active_count(),
                        uptime=time.time() - self.start_time
                    )
                    
                    # Try to get CPU temperature (if available)
                    try:
                        temps = psutil.sensors_temperatures()
                        if temps:
                            # Get first available temperature sensor
                            for name, entries in temps.items():
                                if entries:
                                    health.temperature = entries[0].current
                                    break
                    except (AttributeError, OSError):
                        pass  # Temperature monitoring not available
                    
                    self.system_health_history.append(health)
                
                time.sleep(5)  # Update every 5 seconds
            except Exception as e:
                print(f"Error in system health monitoring: {e}")
                time.sleep(10)  # Wait longer on error
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current statistics summary"""
        with self._lock:
            uptime = time.time() - self.start_time
            success_rate = (self.successful_scans / self.total_scans * 100) if self.total_scans > 0 else 0
            
            # Get recent system health
            recent_health = list(self.system_health_history)[-1] if self.system_health_history else None
            
            return {
                'session': {
                    'start_time': self.session_start.isoformat(),
                    'uptime_seconds': uptime,
                    'uptime_formatted': self._format_duration(uptime)
                },
                'scans': {
                    'total': self.total_scans,
                    'successful': self.successful_scans,
                    'failed': self.failed_scans,
                    'success_rate': round(success_rate, 2),
                    'total_detections': self.total_detections
                },
                'clicks': {
                    'total': self.total_clicks,
                    'successful': self.successful_clicks,
                    'failed': self.failed_clicks,
                    'success_rate': round((self.successful_clicks / self.total_clicks * 100) if self.total_clicks > 0 else 0, 2)
                },
                'performance': {
                    'avg_scan_time': round(self.avg_scan_time, 3),
                    'min_scan_time': round(self.min_scan_time, 3) if self.min_scan_time != float('inf') else 0,
                    'max_scan_time': round(self.max_scan_time, 3),
                    'last_scan_time': round(self.last_scan_time, 3)
                },
                'detection': {
                    'last_detection': self.last_detection_time.isoformat() if self.last_detection_time else None,
                    'current_streak': self.detection_streak,
                    'longest_streak': self.longest_streak
                },
                'system': {
                    'cpu_percent': recent_health.cpu_percent if recent_health else 0,
                    'memory_percent': recent_health.memory_percent if recent_health else 0,
                    'memory_used_mb': round(recent_health.memory_used_mb, 2) if recent_health else 0,
                    'memory_total_mb': round(recent_health.memory_total_mb, 2) if recent_health else 0,
                    'disk_usage': recent_health.disk_usage if recent_health else 0,
                    'active_threads': recent_health.active_threads if recent_health else 0,
                    'temperature': recent_health.temperature if recent_health and recent_health.temperature else None
                },
                'process': {
                    'cpu_percent': round(self.process_cpu_percent, 2),
                    'memory_mb': round(self.process_memory_mb, 2),
                    'memory_percent': round(self.process_memory_percent, 2)
                },
                'next_scan': {
                    'scheduled_time': self.next_scan_time.isoformat() if self.next_scan_time else None,
                    'seconds_remaining': max(0, int((self.next_scan_time - datetime.now()).total_seconds())) if self.next_scan_time else None,
                    'interval_seconds': self.scan_interval
                },
                'errors': {
                    'total_errors': len(self.recent_errors),
                    'error_types': dict(self.error_counts),
                    'recent_errors': list(self.recent_errors)[-10:]  # Last 10 errors
                }
            }
    
    def get_historical_data(self, hours: int = 1) -> Dict[str, List[Dict]]:
        """Get historical data for the specified time period"""
        with self._lock:
            cutoff_time = time.time() - (hours * 3600)
            
            # Filter scan history
            recent_scans = [
                asdict(scan) for scan in self.scan_history 
                if scan.timestamp >= cutoff_time
            ]
            
            # Filter system health history
            recent_health = [
                asdict(health) for health in self.system_health_history 
                if health.timestamp >= cutoff_time
            ]
            
            return {
                'scans': recent_scans,
                'system_health': recent_health,
                'time_range': {
                    'start': cutoff_time,
                    'end': time.time(),
                    'hours': hours
                }
            }
    
    def export_data(self, filepath: str, format: str = 'json'):
        """Export statistics data to file"""
        with self._lock:
            data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'format': format,
                    'total_scans': len(self.scan_history),
                    'total_health_records': len(self.system_health_history)
                },
                'current_stats': self.get_current_stats(),
                'scan_history': [asdict(scan) for scan in self.scan_history],
                'system_health_history': [asdict(health) for health in self.system_health_history]
            }
            
            if format.lower() == 'json':
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported export format: {format}")
    
    def reset_statistics(self):
        """Reset all statistics (keep system health monitoring active)"""
        with self._lock:
            self.scan_history.clear()
            self.total_scans = 0
            self.successful_scans = 0
            self.failed_scans = 0
            self.total_detections = 0
            self.total_clicks = 0
            self.successful_clicks = 0
            self.failed_clicks = 0
            self.avg_scan_time = 0.0
            self.min_scan_time = float('inf')
            self.max_scan_time = 0.0
            self.last_scan_time = 0.0
            self.session_start = datetime.now()
            self.last_detection_time = None
            self.detection_streak = 0
            self.longest_streak = 0
            self.error_counts.clear()
            self.recent_errors.clear()
            self.start_time = time.time()
    
    def cleanup_old_data(self):
        """Remove data older than retention period"""
        with self._lock:
            cutoff_time = time.time() - (self.data_retention_hours * 3600)
            
            # Clean scan history
            while self.scan_history and self.scan_history[0].timestamp < cutoff_time:
                self.scan_history.popleft()
            
            # Clean system health history
            while self.system_health_history and self.system_health_history[0].timestamp < cutoff_time:
                self.system_health_history.popleft()
    
    def stop_monitoring(self):
        """Stop system health monitoring"""
        self.system_monitor_active = False
        if self.system_monitor_thread.is_alive():
            self.system_monitor_thread.join(timeout=5)
    
    def set_next_scan_time(self, scan_interval: float):
        """Set the time for the next scan"""
        with self._lock:
            self.scan_interval = scan_interval
            self.next_scan_time = datetime.now() + timedelta(seconds=scan_interval)
    
    def get_time_until_next_scan(self) -> Optional[float]:
        """Get seconds remaining until next scan"""
        with self._lock:
            if self.next_scan_time:
                remaining = (self.next_scan_time - datetime.now()).total_seconds()
                return max(0, remaining)
            return None
    
    def update_scan_interval(self, new_interval: float):
        """Update the scan interval and recalculate next scan time"""
        with self._lock:
            self.scan_interval = new_interval
            if self.next_scan_time:
                # Adjust next scan time based on new interval
                self.next_scan_time = datetime.now() + timedelta(seconds=new_interval)
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to human-readable string"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_monitoring()

# Global statistics manager instance
stats_manager = StatisticsManager()

def get_stats_manager() -> StatisticsManager:
    """Get the global statistics manager instance"""
    return stats_manager