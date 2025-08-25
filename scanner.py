"""Main module for scanning logic.

This module orchestrates all system components to:
- Execute complete screen scans
- Process images and extract text
- Search for target message
- Execute automatic clicks when necessary"""

import time
from datetime import datetime

from config import (
    TARGET_PATTERN, TARGET_END_WORD, SCREENSHOT_FULLSCREEN_PATTERN,
    MAX_RETRIES, RETRY_DELAY, MAX_CONSECUTIVE_FAILURES, EXTENDED_WAIT_TIME
)
from logger import (
    log_message, log_error, log_debug, log_scan_start, log_scan_complete,
    log_enhancement_stats, update_scan_stats, update_performance_stats,
    record_successful_detection, should_log_status_report, log_system_status,
    reset_consecutive_failures, log_extended_wait_start, log_extended_wait_complete,
    get_stats_copy
)
from image_processing import (
    manage_screenshots_folder, safe_screenshot, save_screenshot,
    enhance_image_for_text_detection, save_enhanced_image
)
from ocr_engine import (
    extract_all_text_with_positions, deduplicate_detections,
    find_target_pattern_in_detections, deduplicate_coordinates
)
from coordinate_manager import perform_automatic_click
from statistics_manager import get_stats_manager

def scan_entire_screen_for_continue_message():
    """Executes a complete screen scan to find the 'Continue' message.
    
    Returns:
        list: List of found coordinates or empty list if not found/error
    """
    try:
        log_debug("Starting complete screen scan")
        
        # Manage screenshot folder
        try:
            manage_screenshots_folder()
        except Exception as e:
            log_error(f"Error managing screenshot folder: {e}")
            # Continue anyway
        
        # Capture screenshot
        try:
            screenshot = safe_screenshot()
            if screenshot is None:
                log_error("Unable to capture screenshot")
                return []
        except Exception as e:
            log_error(f"Critical error during screenshot capture: {e}")
            return []
        
        # Save screenshot for debug
        try:
            save_screenshot(screenshot, SCREENSHOT_FULLSCREEN_PATTERN)
        except Exception as e:
            log_error(f"Error saving screenshot: {e}")
            # Continue anyway
        
        # Image enhancement
        try:
            enhanced_images = enhance_image_for_text_detection(screenshot)
            if not enhanced_images:
                log_error("No enhanced images generated")
                return []
        except Exception as e:
            log_error(f"Error during image enhancement: {e}")
            return []
        
        # Process each enhanced image
        all_detections = []
        for method_name, enhanced_image in enhanced_images:
            try:
                log_debug(f"Processing enhanced image: {method_name}")
                
                # Save enhanced image for debug
                try:
                    save_enhanced_image(enhanced_image, method_name)
                except Exception as e:
                    log_error(f"Error saving enhanced image {method_name}: {e}")
                    # Continue anyway
                
                # Extract text
                try:
                    detections = extract_all_text_with_positions(enhanced_image)
                    if detections:
                        all_detections.extend(detections)
                        log_enhancement_stats(method_name, len(detections))
                    else:
                        log_debug(f"No detections for method {method_name}")
                except Exception as e:
                    log_error(f"Error extracting text for {method_name}: {e}")
                    continue
                
            except Exception as e:
                log_error(f"Error processing method {method_name}: {e}")
                continue
        
        if not all_detections:
            log_debug("No detections found in all enhanced images")
            return []
        
        # Deduplicate detections
        try:
            unique_detections = deduplicate_detections(all_detections)
            log_debug(f"Detections after deduplication: {len(unique_detections)}")
        except Exception as e:
            log_error(f"Error deduplicating detections: {e}")
            unique_detections = all_detections  # Fallback
        
        # Log found detections (debug only)
        try:
            detected_words = [det['text'] for det in unique_detections[:10]]  # First 10
            if detected_words:
                log_debug(f"Detected words (first 10): {', '.join(detected_words)}")
        except Exception as e:
            log_error(f"Error logging detections: {e}")
        
        # Search for target pattern
        try:
            coordinates = find_target_pattern_in_detections(
                unique_detections, TARGET_PATTERN, TARGET_END_WORD
            )
            log_debug(f"Coordinates found by pattern: {len(coordinates)}")
        except Exception as e:
            log_error(f"Error searching target pattern: {e}")
            return []
        
        # Final coordinate deduplication
        try:
            final_coordinates = deduplicate_coordinates(coordinates)
            log_debug(f"Final coordinates after deduplication: {len(final_coordinates)}")
            return final_coordinates
        except Exception as e:
            log_error(f"Error deduplicating final coordinates: {e}")
            return coordinates if coordinates else []
        
    except Exception as e:
        log_error(f"Critical error during screen scan: {e}")
        return []

def perform_single_scan(scan_number):
    """Executes a single complete scan.
    
    Args:
        scan_number (int): Scan number
        
    Returns:
        tuple: (success, coordinates_found)
    """
    try:
        log_scan_start(scan_number)
        scan_start_time = time.time()
        
        # Execute scan
        coordinates = scan_entire_screen_for_continue_message()
        
        # Calculate scan time
        scan_time = time.time() - scan_start_time
        update_performance_stats(scan_time)
        
        # Determine if the scan was successful
        success = len(coordinates) > 0
        
        # Log result
        log_scan_complete(scan_number, success, coordinates)

        # Update statistics (both logger and statistics_manager)
        update_scan_stats(success, scan_time)
        
        # Update statistics manager
        try:
            stats_manager = get_stats_manager()
            stats_manager.record_scan(
                scan_number=scan_number,
                success=success,
                duration=scan_time,
                detections_found=len(coordinates) if coordinates else 0,
                error_message=None if success else "No detections found"
            )
            
            if success:
                stats_manager.record_detection(coordinates)
        except Exception as e:
            log_error(f"Error updating statistics manager: {e}")
        
        if success:
            record_successful_detection()
        
        return success, coordinates
        
    except Exception as e:
        log_error(f"Error during scan #{scan_number}: {e}")
        return False, []

def perform_scan_with_retry(scan_number, max_retries=None, retry_delay=None):
    """Executes a scan with automatic retries.
    
    Args:
        scan_number (int): Scan number
        max_retries (int, optional): Maximum number of retries
        retry_delay (float, optional): Delay between retries
        
    Returns:
        tuple: (success, coordinates_found)
    """
    if max_retries is None:
        max_retries = MAX_RETRIES
    if retry_delay is None:
        retry_delay = RETRY_DELAY
    
    try:
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    log_debug(f"Retry scan #{scan_number}, attempt {attempt + 1}/{max_retries + 1}")
                
                success, coordinates = perform_single_scan(scan_number)
                
                if success:
                    if attempt > 0:
                        log_message(f"✅ Scan #{scan_number} successful on attempt {attempt + 1}")
                    return True, coordinates
                
                # If not the last attempt, wait before retry
                if attempt < max_retries:
                    log_debug(f"Scan failed, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                
            except Exception as e:
                log_error(f"Error during attempt {attempt + 1} of scan #{scan_number}: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                continue
        
        log_debug(f"All scan attempts #{scan_number} failed")
        return False, []
        
    except Exception as e:
        log_error(f"Critical error during scan_with_retry #{scan_number}: {e}")
        return False, []

def handle_scan_result(scan_number, success, coordinates):
    """Handles the result of a scan.
    
    Args:
        scan_number (int): Scan number
        success (bool): Whether the scan was successful
        coordinates (list): Found coordinates
        
    Returns:
        bool: True if an automatic click was performed
    """
    try:
        if success and coordinates:
            log_message(f"🎯 Target message found in scan #{scan_number}!")
            
            # Execute automatic click
            click_success = perform_automatic_click(coordinates)
            
            # Update statistics manager for click
            try:
                stats_manager = get_stats_manager()
                stats_manager.record_click(coordinates[0] if coordinates else None, success=click_success)
            except Exception as e:
                log_error(f"Error updating click statistics: {e}")
            
            if click_success:
                log_message(f"✅ Automatic click executed successfully for scan #{scan_number}")
                return True
            else:
                log_error(f"❌ Automatic click failed for scan #{scan_number}")
                return False
        else:
            log_debug(f"Target message not found in scan #{scan_number}")
            return False
            
    except Exception as e:
        log_error(f"Error handling scan result #{scan_number}: {e}")
        return False

def handle_consecutive_failures():
    """Handles consecutive failures by implementing extended wait.
    
    Returns:
        bool: True if an extended wait was performed
    """
    try:
        stats = get_stats_copy()
        consecutive_failures = stats.get('consecutive_failures', 0)
        
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            log_extended_wait_start()
            
            # Extended wait
            try:
                time.sleep(EXTENDED_WAIT_TIME)
            except KeyboardInterrupt:
                log_message("⚠️ Interruption during extended wait")
                raise
            except Exception as e:
                log_error(f"Error during extended wait: {e}")
            
            log_extended_wait_complete()
            reset_consecutive_failures()
            return True
        
        return False
        
    except Exception as e:
        log_error(f"Error handling consecutive failures: {e}")
        return False

def should_perform_extended_wait():
    """Determines if an extended wait should be performed.
    
    Returns:
        bool: True if an extended wait should be performed
    """
    try:
        stats = get_stats_copy()
        consecutive_failures = stats.get('consecutive_failures', 0)
        return consecutive_failures >= MAX_CONSECUTIVE_FAILURES
    except Exception:
        return False

def log_scan_summary(scan_number, success, click_performed, scan_time=None):
    """Logs a scan summary.
    
    Args:
        scan_number (int): Scan number
        success (bool): Whether the scan was successful
        click_performed (bool): Whether a click was performed
        scan_time (float, optional): Scan time in seconds
    """
    try:
        status_icon = "✅" if success else "❌"
        click_icon = "🖱️" if click_performed else ""
        
        summary = f"{status_icon} Scan #{scan_number}"
        
        if success:
            summary += " - Target found"
            if click_performed:
                summary += " - Click performed"
        else:
            summary += " - Target not found"
        
        if scan_time:
            summary += f" ({scan_time:.2f}s)"
        
        log_message(summary)
        
        # Log status report if necessary
        if should_log_status_report():
            log_system_status()
            
    except Exception as e:
        log_error(f"Error logging scan summary: {e}")

def get_next_scan_number():
    """Gets the next scan number.
    
    Returns:
        int: Next scan number
    """
    try:
        stats = get_stats_copy()
        return stats.get('total_scans', 0) + 1
    except Exception:
        return 1

def is_system_healthy():
    """Checks if the system is in a healthy state.
    
    Returns:
        bool: True if the system is healthy
    """
    try:
        stats = get_stats_copy()
        
        # Check if there are too many errors
        total_errors = stats.get('total_errors', 0)
        total_scans = stats.get('total_scans', 1)
        
        error_rate = total_errors / total_scans if total_scans > 0 else 0
        
        # If error rate is above 50%, consider the system unhealthy
        if error_rate > 0.5 and total_scans > 10:
            log_error(f"System unhealthy: error rate {error_rate:.1%} over {total_scans} scans")
            return False
        
        return True
        
    except Exception as e:
        log_error(f"Error checking system health: {e}")
        return True  # Assume healthy in case of error

def log_scan_summary():
    """Logs a summary of performed scans."""
    try:
        stats = get_stats_copy()
        total_scans = stats.get('total_scans', 0)
        successful_detections = stats.get('successful_detections', 0)
        total_clicks = stats.get('total_clicks', 0)
        
        if total_scans > 0:
            success_rate = (successful_detections / total_scans) * 100
            log_message(f"📊 Summary: {total_scans} scans, {successful_detections} detections ({success_rate:.1f}%), {total_clicks} clicks")
        
    except Exception as e:
        log_error(f"Error during scan summary logging: {e}")