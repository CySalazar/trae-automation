"""Global configurations for the automatic detection system.

This module contains all configurations, constants and global settings
used by the automatic detection system for the 'Continue' message.
"""

import time
import pytesseract
import pyautogui

# ============================================================================
# TESSERACT CONFIGURATIONS
# ============================================================================

# Path to Tesseract OCR executable
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ============================================================================
# PYAUTOGUI CONFIGURATIONS
# ============================================================================

# Safety configurations for pyautogui
FAILSAFE_ENABLED = True    # Move mouse to corner to interrupt
PAUSE_BETWEEN_ACTIONS = 0.5  # Pause between actions for stability

# Apply configurations
pyautogui.FAILSAFE = FAILSAFE_ENABLED
pyautogui.PAUSE = PAUSE_BETWEEN_ACTIONS

# ============================================================================
# RETRY AND TIMEOUT CONFIGURATIONS
# ============================================================================

# Configurations for automatic retries
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
CLICK_VALIDATION_TIMEOUT = 2  # seconds
SCREENSHOT_MAX_RETRIES = 3

# Configurations for consecutive failures handling
MAX_CONSECUTIVE_FAILURES = 5
EXTENDED_WAIT_TIME = 300  # 5 minutes in seconds

# ============================================================================
# SCANNING CONFIGURATIONS
# ============================================================================

# Interval between scans
SCAN_INTERVAL = 120  # 2 minutes in seconds

# System status report frequency
STATUS_REPORT_FREQUENCY = 10  # every N scans

# ============================================================================
# OCR CONFIGURATIONS
# ============================================================================

# OCR configurations to maximize detection
OCR_CONFIGS = [
    '--psm 6',   # Assume a single uniform block of text
    '--psm 8',   # Treat the image as a single word
    '--psm 7',   # Treat the image as a single text line
    '--psm 11',  # Sparse text. Find as much text as possible in no particular order
    '--psm 12',  # Sparse text with OSD
    '--psm 13'   # Raw line. Treat the image as a single text line
]

# Minimum confidence threshold to accept a detection
MIN_CONFIDENCE_THRESHOLD = 15

# ============================================================================
# DEDUPLICATION CONFIGURATIONS
# ============================================================================

# Minimum distance between detections to consider them duplicates
DEDUPLICATION_DISTANCE_THRESHOLD = 20
FINAL_COORDINATES_TOLERANCE = 5

# ============================================================================
# IMAGE ENHANCEMENT CONFIGURATIONS
# ============================================================================

# Parameters for CLAHE (Contrast Limited Adaptive Histogram Equalization)
CLAHE_CLIP_LIMIT = 3.0
CLAHE_TILE_GRID_SIZE = (8, 8)

# Parameters for adaptive threshold
ADAPTIVE_THRESHOLD_MAX_VALUE = 255
ADAPTIVE_THRESHOLD_BLOCK_SIZE = 11
ADAPTIVE_THRESHOLD_C = 2

# Parameters for filters
GAUSSIAN_BLUR_KERNEL_SIZE = (5, 5)
MORPHOLOGY_KERNEL_SIZE = (2, 2)
MEDIAN_BLUR_KERNEL_SIZE = 3
BILATERAL_FILTER_D = 9
BILATERAL_FILTER_SIGMA_COLOR = 75
BILATERAL_FILTER_SIGMA_SPACE = 75

# Kernel for sharpening
SHARPENING_KERNEL = [[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]

# ============================================================================
# SCREENSHOT MANAGEMENT CONFIGURATIONS
# ============================================================================

# Folder to save screenshots
SCREENSHOTS_FOLDER = "screenshots"

# Maximum number of screenshots to keep
MAX_SCREENSHOTS_TO_KEEP = 10

# Patterns for screenshot file names
SCREENSHOT_FULLSCREEN_PATTERN = "debug_fullscreen_{timestamp}.png"
SCREENSHOT_ENHANCED_PATTERN = "debug_enhanced_{method_name}_{timestamp}.png"

# ============================================================================
# LOGGING CONFIGURATIONS
# ============================================================================

# Main log file
LOG_FILE = "log.txt"

# Timestamp format for logs
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
FILE_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# ============================================================================
# TARGET MESSAGE CONFIGURATIONS
# ============================================================================

# Target message to search for
TARGET_MESSAGE = "Model thinking limit reached, please enter 'Continue' to"

# Regex pattern to find the target message
TARGET_PATTERN = r"Model\s+thinking\s+limit\s+reached.*?Continue.*?to"

# Final word to find coordinates for
TARGET_END_WORD = "to"

# ============================================================================
# STATISTICS CONFIGURATIONS
# ============================================================================

# Maximum number of scan times to keep for calculating average
MAX_SCAN_TIMES_HISTORY = 100

# ============================================================================
# GLOBAL STATISTICS INITIALIZATION
# ============================================================================

def get_initial_stats():
    """Returns the initial structure of global statistics."""
    return {
        'total_scans': 0,
        'successful_detections': 0,
        'clicks_performed': 0,
        'failed_scans': 0,
        'consecutive_failures': 0,
        'max_consecutive_failures': 0,
        'total_errors': 0,
        'screenshot_errors': 0,
        'ocr_errors': 0,
        'click_errors': 0,
        'enhancement_errors': 0,
        'start_time': time.time(),
        'last_successful_detection': None,
        'last_click_time': None,
        'performance_metrics': {
            'avg_scan_time': 0,
            'scan_times': [],
            'max_scan_time': 0,
            'min_scan_time': float('inf')
        }
    }

# ============================================================================
# MINIMUM SIZE CONFIGURATIONS
# ============================================================================

# Minimum dimensions to consider an image valid
MIN_IMAGE_WIDTH = 10
MIN_IMAGE_HEIGHT = 10

# ============================================================================
# SYSTEM MESSAGES
# ============================================================================

# Startup messages
STARTUP_MESSAGES = {
    'title': "🚀 STARTING AUTOMATIC SCANNER EVERY 2 MINUTES FOR 'Continue' MESSAGE",
    'target': f"Target: '{TARGET_MESSAGE}'",
    'objective': f"Objective: find coordinates of the end of word '{TARGET_END_WORD}' and click automatically",
    'mode': "Mode: AUTOMATIC - Automatic click without confirmation",
    'interval': f"Interval: every 2 minutes ({SCAN_INTERVAL} seconds)",
    'interrupt': "To interrupt: Ctrl+C"
}

# Log separators
LOG_SEPARATOR = "=" * 80
SUB_SEPARATOR = "-" * 40