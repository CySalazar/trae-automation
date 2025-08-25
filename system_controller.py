#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Controller Module

This module provides a centralized controller for the detection system that can be
used by both GUI and CLI interfaces. It manages the system state and provides
thread-safe operations for starting, stopping, pausing, and monitoring the system.

Features:
- Thread-safe system control
- State management
- Integration with existing detection modules
- Event callbacks for UI updates
- Emergency stop functionality

Author: Matteo Sala
Version: 1.0.0
"""

import threading
import time
import signal
import sys
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from enum import Enum

# Import detection system modules
try:
    from config import (
        SCAN_INTERVAL, TARGET_PATTERN, TARGET_END_WORD,
        MAX_CONSECUTIVE_FAILURES, EXTENDED_WAIT_TIME
    )
    from logger import (
        setup_logging, log_message, log_error, log_debug,
        log_system_startup, log_system_shutdown, log_scan_interval,
        should_log_status_report, log_system_status, get_stats_copy
    )
    from scanner import (
        perform_scan_with_retry, handle_scan_result, handle_consecutive_failures,
        get_next_scan_number, is_system_healthy, log_scan_summary
    )
except ImportError as e:
    print(f"Error importing detection modules: {e}")
    raise

# Configure pyautogui safety settings
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
except ImportError:
    print("Warning: pyautogui not available")

class SystemState(Enum):
    """Enumeration of possible system states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    STOPPING = "stopping"
    ERROR = "error"

class SystemController:
    """Central controller for the detection system"""
    
    def __init__(self):
        """Initialize the system controller"""
        self._state = SystemState.STOPPED
        self._state_lock = threading.RLock()
        self._scan_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        
        # Callbacks for state changes
        self._state_callbacks: Dict[str, Callable] = {}
        self._scan_callbacks: Dict[str, Callable] = {}
        
        # Statistics
        self._start_time: Optional[datetime] = None
        self._last_scan_time: Optional[datetime] = None
        self._scan_count = 0
        
        # Setup logging
        setup_logging()
        
    def get_state(self) -> SystemState:
        """Get current system state"""
        with self._state_lock:
            return self._state
    
    def is_running(self) -> bool:
        """Check if system is running"""
        return self.get_state() == SystemState.RUNNING
    
    def is_paused(self) -> bool:
        """Check if system is paused"""
        return self.get_state() == SystemState.PAUSED
    
    def is_stopped(self) -> bool:
        """Check if system is stopped"""
        return self.get_state() == SystemState.STOPPED
    
    def can_start(self) -> bool:
        """Check if system can be started"""
        state = self.get_state()
        return state in [SystemState.STOPPED, SystemState.ERROR]
    
    def can_stop(self) -> bool:
        """Check if system can be stopped"""
        state = self.get_state()
        return state in [SystemState.RUNNING, SystemState.PAUSED, SystemState.ERROR]
    
    def can_pause(self) -> bool:
        """Check if system can be paused"""
        return self.get_state() == SystemState.RUNNING
    
    def can_resume(self) -> bool:
        """Check if system can be resumed"""
        return self.get_state() == SystemState.PAUSED
    
    def _set_state(self, new_state: SystemState):
        """Set system state and notify callbacks"""
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            log_debug(f"System state changed: {old_state.value} -> {new_state.value}")
            
            # Notify state change callbacks
            for callback in self._state_callbacks.values():
                try:
                    callback(old_state, new_state)
                except Exception as e:
                    log_error(f"Error in state callback: {e}")
    
    def add_state_callback(self, name: str, callback: Callable):
        """Add a callback for state changes"""
        self._state_callbacks[name] = callback
    
    def remove_state_callback(self, name: str):
        """Remove a state change callback"""
        self._state_callbacks.pop(name, None)
    
    def add_scan_callback(self, name: str, callback: Callable):
        """Add a callback for scan events"""
        self._scan_callbacks[name] = callback
    
    def remove_scan_callback(self, name: str):
        """Remove a scan event callback"""
        self._scan_callbacks.pop(name, None)
    
    def start_system(self) -> bool:
        """Start the detection system"""
        if not self.can_start():
            log_error(f"Cannot start system in state: {self.get_state().value}")
            return False
        
        try:
            self._set_state(SystemState.STARTING)
            
            # Reset events
            self._stop_event.clear()
            self._pause_event.clear()
            
            # Start scan thread
            self._scan_thread = threading.Thread(
                target=self._scan_loop,
                name="DetectionScanThread",
                daemon=True
            )
            self._scan_thread.start()
            
            # Wait a moment to ensure thread started
            time.sleep(0.1)
            
            if self._scan_thread.is_alive():
                self._set_state(SystemState.RUNNING)
                self._start_time = datetime.now()
                log_system_startup()
                log_message(f"🎯 Target: '{TARGET_PATTERN}'")
                log_message(f"🔍 Final word: '{TARGET_END_WORD}'")
                log_message("🤖 Mode: AUTOMATIC - Automatic click without confirmation")
                return True
            else:
                self._set_state(SystemState.ERROR)
                log_error("Failed to start scan thread")
                return False
                
        except Exception as e:
            self._set_state(SystemState.ERROR)
            log_error(f"Error starting system: {e}")
            return False
    
    def stop_system(self) -> bool:
        """Stop the detection system"""
        current_state = self.get_state()
        
        # Allow stopping if already stopped (idempotent operation)
        if current_state == SystemState.STOPPED:
            log_message("System is already stopped")
            return True
            
        if not self.can_stop():
            log_error(f"Cannot stop system in state: {current_state.value}")
            return False
        
        try:
            self._set_state(SystemState.STOPPING)
            
            # Signal stop
            self._stop_event.set()
            self._pause_event.set()  # Also unpause if paused
            
            # Wait for thread to finish
            if self._scan_thread and self._scan_thread.is_alive():
                self._scan_thread.join(timeout=5.0)
                
                if self._scan_thread.is_alive():
                    log_error("Scan thread did not stop gracefully")
                    # Force terminate would go here if needed
            
            self._scan_thread = None
            self._set_state(SystemState.STOPPED)
            log_system_shutdown()
            return True
            
        except Exception as e:
            self._set_state(SystemState.ERROR)
            log_error(f"Error stopping system: {e}")
            return False
    
    def pause_system(self) -> bool:
        """Pause the detection system"""
        if not self.can_pause():
            log_error(f"Cannot pause system in state: {self.get_state().value}")
            return False
        
        try:
            self._set_state(SystemState.PAUSING)
            self._pause_event.set()
            self._set_state(SystemState.PAUSED)
            log_message("🔄 System paused")
            return True
            
        except Exception as e:
            log_error(f"Error pausing system: {e}")
            return False
    
    def resume_system(self) -> bool:
        """Resume the detection system"""
        if not self.can_resume():
            log_error(f"Cannot resume system in state: {self.get_state().value}")
            return False
        
        try:
            self._set_state(SystemState.RESUMING)
            self._pause_event.clear()
            self._set_state(SystemState.RUNNING)
            log_message("▶️ System resumed")
            return True
            
        except Exception as e:
            log_error(f"Error resuming system: {e}")
            return False
    
    def emergency_stop(self) -> bool:
        """Emergency stop - force stop all operations"""
        try:
            log_message("🚨 EMERGENCY STOP ACTIVATED")
            
            # Set stop events
            self._stop_event.set()
            self._pause_event.set()
            
            # Force state to stopping
            self._set_state(SystemState.STOPPING)
            
            # Try to join thread with short timeout
            if self._scan_thread and self._scan_thread.is_alive():
                self._scan_thread.join(timeout=2.0)
            
            self._scan_thread = None
            self._set_state(SystemState.STOPPED)
            log_message("🛑 Emergency stop completed")
            return True
            
        except Exception as e:
            log_error(f"Error during emergency stop: {e}")
            self._set_state(SystemState.ERROR)
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        with self._state_lock:
            info = {
                'state': self._state.value,
                'start_time': self._start_time.isoformat() if self._start_time else None,
                'last_scan_time': self._last_scan_time.isoformat() if self._last_scan_time else None,
                'scan_count': self._scan_count,
                'uptime_seconds': (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
                'thread_alive': self._scan_thread.is_alive() if self._scan_thread else False,
                'can_start': self.can_start(),
                'can_stop': self.can_stop(),
                'can_pause': self.can_pause(),
                'can_resume': self.can_resume()
            }
            
            # Add statistics from logger
            try:
                stats = get_stats_copy()
                info.update(stats)
            except Exception as e:
                log_error(f"Error getting stats: {e}")
            
            return info
    
    def _scan_loop(self):
        """Main scanning loop running in separate thread"""
        try:
            consecutive_failures = 0
            
            while not self._stop_event.is_set():
                try:
                    # Check if paused
                    if self._pause_event.is_set():
                        time.sleep(0.5)  # Short sleep while paused
                        continue
                    
                    # Check system health
                    if not is_system_healthy():
                        log_error("System unhealthy, continuing with caution...")
                    
                    # Get scan number
                    scan_number = get_next_scan_number()
                    self._scan_count = scan_number
                    
                    # Notify scan start callbacks
                    for callback in self._scan_callbacks.values():
                        try:
                            callback('scan_start', {'scan_number': scan_number})
                        except Exception as e:
                            log_error(f"Error in scan callback: {e}")
                    
                    # Execute scan with retry
                    scan_start_time = time.time()
                    success, coordinates = perform_scan_with_retry(scan_number)
                    scan_time = time.time() - scan_start_time
                    
                    self._last_scan_time = datetime.now()
                    
                    # Handle scan result
                    click_performed = False
                    if success:
                        click_performed = handle_scan_result(scan_number, success, coordinates)
                        consecutive_failures = 0  # Reset on success
                    else:
                        consecutive_failures += 1
                    
                    # Log scan summary
                    log_scan_summary(scan_number, success, click_performed, scan_time)
                    
                    # Notify scan complete callbacks
                    for callback in self._scan_callbacks.values():
                        try:
                            callback('scan_complete', {
                                'scan_number': scan_number,
                                'success': success,
                                'click_performed': click_performed,
                                'scan_time': scan_time,
                                'coordinates': coordinates
                            })
                        except Exception as e:
                            log_error(f"Error in scan callback: {e}")
                    
                    # Handle consecutive failures
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        handle_consecutive_failures(consecutive_failures)
                        consecutive_failures = 0  # Reset after handling
                    
                    # Status report
                    if should_log_status_report():
                        log_system_status()
                    
                    # Wait for next scan (with interruption check)
                    self._wait_for_next_scan()
                    
                except Exception as e:
                    log_error(f"Error in scan loop: {e}")
                    consecutive_failures += 1
                    
                    # If too many errors, stop the system
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES * 2:
                        log_error("Too many consecutive errors, stopping system")
                        self._set_state(SystemState.ERROR)
                        break
                    
                    # Short wait before retry
                    time.sleep(1.0)
            
        except Exception as e:
            log_error(f"Critical error in scan loop: {e}")
            self._set_state(SystemState.ERROR)
        
        finally:
            log_debug("Scan loop terminated")
    
    def _wait_for_next_scan(self):
        """Wait for next scan with interruption support"""
        wait_time = SCAN_INTERVAL
        start_time = time.time()
        
        while time.time() - start_time < wait_time:
            if self._stop_event.is_set():
                break
            
            # Sleep in small increments to allow interruption
            time.sleep(min(0.5, wait_time - (time.time() - start_time)))

# Global instance
_system_controller: Optional[SystemController] = None

def get_system_controller() -> SystemController:
    """Get the global system controller instance"""
    global _system_controller
    if _system_controller is None:
        _system_controller = SystemController()
    return _system_controller

def cleanup_system_controller():
    """Cleanup the global system controller"""
    global _system_controller
    if _system_controller is not None:
        _system_controller.stop_system()
        _system_controller = None

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    try:
        controller = get_system_controller()
        controller.emergency_stop()
        cleanup_system_controller()
        sys.exit(0)
    except Exception as e:
        print(f"Error during signal handling: {e}")
        sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)