#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatic Detection and Click System for "Continue" Messages

This script automatically scans the screen for specific text patterns and performs
automatic clicks when the target message is detected. It's designed to be robust,
with comprehensive error handling, retry mechanisms, and performance monitoring.

Features:
- Automatic screen scanning with configurable intervals
- Multiple image enhancement techniques for better OCR accuracy
- Robust error handling and retry mechanisms
- Performance monitoring and statistics
- Safe coordinate validation and click operations
- Comprehensive logging system
- Modular architecture with separated responsibilities

Usage:
    python detect.py

The script will run continuously, scanning for the target message every 2 minutes
and automatically clicking when found.
"""

import sys
import time
import signal
from datetime import datetime

# Import modular components
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
    print(f"Error importing modular components: {e}")
    print("Please ensure all required modules are in the same directory:")
    print("- config.py")
    print("- logger.py")
    print("- image_processing.py")
    print("- ocr_engine.py")
    print("- coordinate_manager.py")
    print("- scanner.py")
    sys.exit(1)

# Third-party imports for safety configuration
try:
    import pyautogui
except ImportError as e:
    print(f"Error importing pyautogui: {e}")
    print("Please install required packages: pip install pyautogui")
    sys.exit(1)

# Configure pyautogui safety settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# ============================================================================
# SIGNAL HANDLERS
# ============================================================================

def signal_handler(signum, frame):
    """Handles interruption signals for clean shutdown."""
    try:
        log_message("\n\n🛑 INTERRUPTION RECEIVED")
        log_system_status()
        log_system_shutdown()
        sys.exit(0)
    except Exception as e:
        print(f"Error during shutdown: {e}")
        sys.exit(1)

# ============================================================================
# MAIN SCANNING LOOP
# ============================================================================

def run_continuous_scanner():
    """Runs the main continuous scanning loop."""
    try:
        log_system_startup()
        log_message(f"🎯 Target: '{TARGET_PATTERN}'")
        log_message(f"🔍 Final word: '{TARGET_END_WORD}'")
        log_message("🤖 Mode: AUTOMATIC - Automatic click without confirmation")
        log_message("💡 To interrupt: Ctrl+C")
        log_message("\n" + "="*80)
        
        while True:
            try:
                # Check system health
                if not is_system_healthy():
                    log_error("System unhealthy, continuing with caution...")
                
                # Get scan number
                scan_number = get_next_scan_number()
                
                # Execute scan with retry
                scan_start_time = time.time()
                success, coordinates = perform_scan_with_retry(scan_number)
                scan_time = time.time() - scan_start_time
                
                # Handle scan result
                click_performed = False
                if success:
                    click_performed = handle_scan_result(scan_number, success, coordinates)
                
                # Log scan summary
                log_scan_summary(scan_number, success, click_performed, scan_time)
                
                # Handle consecutive failures
                if not success:
                    extended_wait_performed = handle_consecutive_failures()
                    if extended_wait_performed:
                        continue  # Skip normal wait if extended wait was performed
                
                # Log periodic status report
                if should_log_status_report():
                    log_system_status()
                
                # Wait before next scan
                try:
                    next_scan_number = get_next_scan_number()
                    log_message(f"\n⏰ Next scan #{next_scan_number} in {SCAN_INTERVAL//60} minutes...")
                    log_message("💡 Press Ctrl+C to interrupt")
                    time.sleep(SCAN_INTERVAL)
                except KeyboardInterrupt:
                    raise  # Re-raise for handling in outer block
                except Exception as e:
                    log_error(f"Error during wait: {e}")
                    time.sleep(10)  # Reduced wait in case of error
                
            except KeyboardInterrupt:
                raise  # Re-raise for handling in outer block
            except Exception as e:
                log_error(f"Error in main loop: {e}")
                time.sleep(5)  # Brief pause before continuing
                continue
                
    except KeyboardInterrupt:
        log_message("\n\n🛑 MANUAL INTERRUPTION RECEIVED (Ctrl+C)")
        log_system_status()
        log_system_shutdown()
    except pyautogui.FailSafeException:
        log_message("\n\n🛑 FAILSAFE ACTIVATED - Mouse moved to corner")
        log_system_status()
        log_system_shutdown()
    except Exception as e:
        log_error(f"\n\n❌ UNHANDLED CRITICAL ERROR: {e}")
        log_system_status()
        log_message("🏁 AUTOMATIC SCANNER TERMINATED DUE TO CRITICAL ERROR")
        sys.exit(1)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_system_requirements():
    """Validates that all system requirements are satisfied."""
    try:
        # Test import of all modules
        from config import TESSERACT_CMD
        from image_processing import safe_screenshot
        from ocr_engine import extract_all_text_with_positions
        from coordinate_manager import validate_coordinates
        
        # Test Tesseract
        import os
        if not os.path.exists(TESSERACT_CMD):
            log_error(f"Tesseract not found at: {TESSERACT_CMD}")
            return False
        
        # Test screenshot
        test_screenshot = safe_screenshot()
        if test_screenshot is None:
            log_error("Unable to capture test screenshot")
            return False
        
        log_message("✅ All system requirements are satisfied")
        return True
        
    except Exception as e:
        log_error(f"Error validating system requirements: {e}")
        return False

def cleanup_on_exit():
    """Cleanup resources before exit."""
    try:
        log_debug("Resource cleanup in progress...")
        # Additional cleanup operations can be added here
        log_debug("Cleanup completed")
    except Exception as e:
        log_error(f"Error during cleanup: {e}")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point of the application."""
    try:
        # Setup logging
        setup_logging()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Validate system requirements
        if not validate_system_requirements():
            log_error("System requirements validation failed")
            sys.exit(1)
        
        # Start continuous scanner
        run_continuous_scanner()
        
    except Exception as e:
        print(f"Critical error during startup: {e}")
        sys.exit(1)
    finally:
        cleanup_on_exit()

if __name__ == "__main__":
    main()