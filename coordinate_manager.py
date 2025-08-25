"""Module for coordinate management and automatic clicks.

This module provides complete functionality for:
- Coordinate validation
- Automatic click execution with retry
- Error handling during clicks
- Post-click validation
"""

import time
import pyautogui

from config import (
    CLICK_VALIDATION_TIMEOUT, MAX_RETRIES, RETRY_DELAY
)
from logger import (
    log_message, log_error, log_debug, log_coordinates_found,
    record_click_performed, record_click_error
)
from config_manager import get_config

def validate_coordinates(coordinates):
    """Validates that coordinates are usable for a click.
    
    Args:
        coordinates (tuple or list): Coordinates (x, y) to validate
        
    Returns:
        bool: True if coordinates are valid
    """
    try:
        if not coordinates:
            return False
        
        if not isinstance(coordinates, (tuple, list)):
            return False
        
        if len(coordinates) != 2:
            return False
        
        x, y = coordinates
        
        # Check that they are numbers
        if not all(isinstance(coord, (int, float)) for coord in [x, y]):
            return False
        
        # Check that they are positive
        if x < 0 or y < 0:
            return False
        
        # Get screen dimensions
        try:
            screen_width, screen_height = pyautogui.size()
            
            # Check that they are within screen bounds
            if x >= screen_width or y >= screen_height:
                log_error(f"Coordinates {coordinates} outside screen bounds {screen_width}x{screen_height}")
                return False
                
        except Exception as e:
            log_error(f"Error getting screen dimensions: {e}")
            # Continue anyway with basic validation
        
        return True
        
    except Exception as e:
        log_error(f"Error validating coordinates {coordinates}: {e}")
        return False

def safe_click(coordinates, validate_after_click=True):
    """Performs a safe click with validation and error handling.
    
    Args:
        coordinates (tuple): Coordinates (x, y) where to click
        validate_after_click (bool): Whether to validate the click after execution
        
    Returns:
        bool: True if the click was executed successfully
    """
    try:
        # Coordinate validation
        if not validate_coordinates(coordinates):
            log_error(f"Invalid coordinates for click: {coordinates}")
            return False
        
        x, y = coordinates
        
        # Apply click offsets from configuration
        try:
            offset_x = get_config("click_offset_x")
            offset_y = get_config("click_offset_y")
            x += offset_x
            y += offset_y
            log_debug(f"Applied offsets: ({offset_x}, {offset_y}), final coordinates: ({x}, {y})")
        except Exception as e:
            log_error(f"Error applying click offsets: {e}")
            # Continue with original coordinates if offset fails
        
        log_debug(f"Attempting click at coordinates ({x}, {y})")
        
        # Execute the click
        try:
            pyautogui.click(x, y)
            log_debug(f"Click executed at coordinates ({x}, {y})")
            
            # Post-click validation if requested
            if validate_after_click:
                time.sleep(CLICK_VALIDATION_TIMEOUT)
                # Here you could add additional validations if necessary
            
            record_click_performed()
            return True
            
        except pyautogui.FailSafeException as e:
            log_error(f"FailSafe activated during click: {e}")
            record_click_error()
            return False
            
        except Exception as e:
            log_error(f"Error during click execution: {e}")
            record_click_error()
            return False
        
    except Exception as e:
        log_error(f"Critical error during safe_click: {e}")
        record_click_error()
        return False

def click_with_retry(coordinates, max_retries=None, retry_delay=None):
    """Performs a click with automatic retries in case of failure.
    
    Args:
        coordinates (tuple): Coordinates (x, y) where to click
        max_retries (int, optional): Maximum number of retries
        retry_delay (float, optional): Delay between retries in seconds
        
    Returns:
        bool: True if the click was executed successfully
    """
    if max_retries is None:
        max_retries = MAX_RETRIES
    if retry_delay is None:
        retry_delay = RETRY_DELAY
    
    try:
        for attempt in range(max_retries + 1):  # +1 to include initial attempt
            try:
                log_debug(f"Click attempt #{attempt + 1}/{max_retries + 1}")
                
                if safe_click(coordinates, validate_after_click=True):
                    log_message(f"✅ Click executed successfully on attempt #{attempt + 1}")
                    return True
                
                # If not the last attempt, wait before retry
                if attempt < max_retries:
                    log_debug(f"Click failed, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                
            except Exception as e:
                log_error(f"Error during click attempt #{attempt + 1}: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                continue
        
        log_error(f"❌ All {max_retries + 1} click attempts failed")
        return False
        
    except Exception as e:
        log_error(f"Critical error during click_with_retry: {e}")
        return False

def get_screen_dimensions():
    """Gets the screen dimensions.
    
    Returns:
        tuple: (width, height) or (0, 0) if it fails
    """
    try:
        return pyautogui.size()
    except Exception as e:
        log_error(f"Error getting screen dimensions: {e}")
        return (0, 0)

def is_coordinate_on_screen(x, y):
    """Checks if a coordinate is within screen bounds.
    
    Args:
        x (int): X coordinate
        y (int): Y coordinate
        
    Returns:
        bool: True if the coordinate is on screen
    """
    try:
        screen_width, screen_height = get_screen_dimensions()
        if screen_width == 0 or screen_height == 0:
            return False
        
        return 0 <= x < screen_width and 0 <= y < screen_height
        
    except Exception as e:
        log_error(f"Error checking coordinate on screen: {e}")
        return False

def filter_valid_coordinates(coordinates_list):
    """Filters a list of coordinates keeping only valid ones.
    
    Args:
        coordinates_list (list): List of coordinates to filter
        
    Returns:
        list: List of valid coordinates
    """
    valid_coordinates = []
    
    try:
        if not coordinates_list or not isinstance(coordinates_list, list):
            return valid_coordinates
        
        for coord in coordinates_list:
            try:
                if validate_coordinates(coord):
                    valid_coordinates.append(coord)
                    log_coordinates_found("target", coord)
                else:
                    log_debug(f"Invalid coordinate filtered: {coord}")
            except Exception as e:
                log_error(f"Error validating coordinate {coord}: {e}")
                continue
        
        log_debug(f"Coordinate filter: {len(valid_coordinates)}/{len(coordinates_list)} valid")
        return valid_coordinates
        
    except Exception as e:
        log_error(f"Critical error during coordinate filtering: {e}")
        return []

def select_best_coordinate(coordinates_list):
    """Selects the best coordinate from a list.
    
    Args:
        coordinates_list (list): List of coordinates
        
    Returns:
        tuple or None: Best coordinate or None if none valid
    """
    try:
        valid_coords = filter_valid_coordinates(coordinates_list)
        
        if not valid_coords:
            log_debug("No valid coordinates found")
            return None
        
        if len(valid_coords) == 1:
            log_debug(f"Only one valid coordinate: {valid_coords[0]}")
            return valid_coords[0]
        
        # If there are multiple coordinates, select the first one (they might all be similar after deduplication)
        selected = valid_coords[0]
        log_debug(f"Selected coordinate: {selected} from {len(valid_coords)} options")
        return selected
        
    except Exception as e:
        log_error(f"Error selecting best coordinate: {e}")
        return None

def perform_automatic_click(coordinates_list):
    """Performs an automatic click on the best available coordinate.
    
    Args:
        coordinates_list (list): List of candidate coordinates
        
    Returns:
        bool: True if the click was executed successfully
    """
    try:
        if not coordinates_list:
            log_debug("No coordinates provided for automatic click")
            return False
        
        log_debug(f"Automatic click attempt on {len(coordinates_list)} candidate coordinates")
        
        # Select the best coordinate
        best_coord = select_best_coordinate(coordinates_list)
        if not best_coord:
            log_error("❌ No valid coordinates for automatic click")
            return False
        
        # Execute the click with retry
        log_message(f"🖱️ Executing automatic click at coordinates {best_coord}")
        success = click_with_retry(best_coord)
        
        if success:
            log_message(f"✅ Automatic click executed successfully at coordinates {best_coord}")
        else:
            log_error(f"❌ Automatic click failed at coordinates {best_coord}")
        
        return success
        
    except Exception as e:
        log_error(f"Critical error during automatic click: {e}")
        return False

def get_mouse_position():
    """Gets the current mouse position.
    
    Returns:
        tuple: (x, y) mouse position or (0, 0) if it fails
    """
    try:
        return pyautogui.position()
    except Exception as e:
        log_error(f"Error getting mouse position: {e}")
        return (0, 0)

def move_mouse_to_coordinate(coordinates, duration=0.5):
    """Moves the mouse to a specific coordinate.
    
    Args:
        coordinates (tuple): Destination coordinates (x, y)
        duration (float): Movement duration in seconds
        
    Returns:
        bool: True if the movement was executed successfully
    """
    try:
        if not validate_coordinates(coordinates):
            return False
        
        x, y = coordinates
        pyautogui.moveTo(x, y, duration=duration)
        log_debug(f"Mouse moved to coordinates ({x}, {y})")
        return True
        
    except Exception as e:
        log_error(f"Error moving mouse: {e}")
        return False

def calculate_coordinate_center(coordinates_list):
    """Calculates the geometric center of a list of coordinates.
    
    Args:
        coordinates_list (list): List of coordinates
        
    Returns:
        tuple or None: Center coordinates or None if it fails
    """
    try:
        valid_coords = filter_valid_coordinates(coordinates_list)
        
        if not valid_coords:
            return None
        
        if len(valid_coords) == 1:
            return valid_coords[0]
        
        # Calculate the center
        total_x = sum(coord[0] for coord in valid_coords)
        total_y = sum(coord[1] for coord in valid_coords)
        
        center_x = int(total_x / len(valid_coords))
        center_y = int(total_y / len(valid_coords))
        
        center = (center_x, center_y)
        
        # Validate the calculated center
        if validate_coordinates(center):
            log_debug(f"Calculated center: {center} from {len(valid_coords)} coordinates")
            return center
        else:
            log_error(f"Calculated center not valid: {center}")
            return None
        
    except Exception as e:
        log_error(f"Error calculating coordinate center: {e}")
        return None