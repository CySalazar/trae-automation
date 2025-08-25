#!/usr/bin/env python3
"""Script to capture a screenshot for debugging."""

import os
from PIL import ImageGrab
from datetime import datetime

def capture_current_screenshot():
    """Capture current screen and save it."""
    # Create screenshots directory if it doesn't exist
    os.makedirs('screenshots', exist_ok=True)
    
    # Capture screenshot
    screenshot = ImageGrab.grab()
    
    # Save with the expected filename
    screenshot_path = "screenshots/debug_fullscreen_20250825_113618.png"
    screenshot.save(screenshot_path)
    
    print(f"Screenshot saved to: {screenshot_path}")
    print(f"Screenshot size: {screenshot.width}x{screenshot.height}")
    
    return screenshot_path

if __name__ == "__main__":
    capture_current_screenshot()