"""Module for image processing and enhancement.

This module provides complete functionality for:
- Screenshot capture and management
- Image enhancement to improve OCR
- Image format conversions
- Screenshot folder management
"""

import os
import time
import numpy as np
from PIL import Image, ImageEnhance
import cv2
import pyautogui
from datetime import datetime

from config import (
    SCREENSHOTS_FOLDER, MAX_SCREENSHOTS_TO_KEEP,
    SCREENSHOT_FULLSCREEN_PATTERN, SCREENSHOT_ENHANCED_PATTERN,
    FILE_TIMESTAMP_FORMAT, SCREENSHOT_MAX_RETRIES,
    CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID_SIZE,
    ADAPTIVE_THRESHOLD_MAX_VALUE, ADAPTIVE_THRESHOLD_BLOCK_SIZE, ADAPTIVE_THRESHOLD_C,
    GAUSSIAN_BLUR_KERNEL_SIZE, MORPHOLOGY_KERNEL_SIZE, MEDIAN_BLUR_KERNEL_SIZE,
    BILATERAL_FILTER_D, BILATERAL_FILTER_SIGMA_COLOR, BILATERAL_FILTER_SIGMA_SPACE,
    SHARPENING_KERNEL, MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT
)
from logger import log_message, log_error, log_debug, record_screenshot_error, record_enhancement_error

def manage_screenshots_folder():
    """Manages the screenshots folder, creating it if necessary and cleaning it."""
    try:
        # Create folder if it doesn't exist
        if not os.path.exists(SCREENSHOTS_FOLDER):
            os.makedirs(SCREENSHOTS_FOLDER)
            log_debug(f"Folder '{SCREENSHOTS_FOLDER}' created")
        
        # Clean old screenshots if necessary
        cleanup_old_screenshots()
        
    except Exception as e:
        log_error(f"Error managing screenshot folder: {e}")

def cleanup_old_screenshots():
    """Removes old screenshots keeping only the last MAX_SCREENSHOTS_TO_KEEP."""
    try:
        if not os.path.exists(SCREENSHOTS_FOLDER):
            return
        
        # Get all screenshot files
        files = []
        for filename in os.listdir(SCREENSHOTS_FOLDER):
            if filename.endswith('.png'):
                filepath = os.path.join(SCREENSHOTS_FOLDER, filename)
                files.append((filepath, os.path.getmtime(filepath)))
        
        # Sort by modification date (most recent first)
        files.sort(key=lambda x: x[1], reverse=True)
        
        # Remove older files
        if len(files) > MAX_SCREENSHOTS_TO_KEEP:
            files_to_remove = files[MAX_SCREENSHOTS_TO_KEEP:]
            for filepath, _ in files_to_remove:
                try:
                    os.remove(filepath)
                    log_debug(f"Screenshot removed: {os.path.basename(filepath)}")
                except Exception as e:
                    log_error(f"Error removing screenshot {filepath}: {e}")
        
    except Exception as e:
        log_error(f"Error cleaning screenshots: {e}")

def safe_screenshot():
    """Captures a screenshot with automatic retries in case of error.
    
    Returns:
        PIL.Image or None: Captured screenshot or None if it fails
    """
    for attempt in range(SCREENSHOT_MAX_RETRIES):
        try:
            log_debug(f"Screenshot attempt #{attempt + 1}")
            screenshot = pyautogui.screenshot()
            
            if screenshot is None:
                raise Exception("Screenshot returned None")
            
            # Check minimum dimensions
            if screenshot.width < MIN_IMAGE_WIDTH or screenshot.height < MIN_IMAGE_HEIGHT:
                raise Exception(f"Screenshot too small: {screenshot.width}x{screenshot.height}")
            
            log_debug(f"Screenshot captured successfully: {screenshot.width}x{screenshot.height}")
            return screenshot
            
        except Exception as e:
            log_error(f"Screenshot attempt #{attempt + 1} failed: {e}")
            if attempt < SCREENSHOT_MAX_RETRIES - 1:
                time.sleep(1)  # Wait before retry
            else:
                record_screenshot_error()
                return None
    
    return None

def save_screenshot(screenshot, filename_pattern, **format_kwargs):
    """Saves a screenshot with a formatted filename.
    
    Args:
        screenshot (PIL.Image): Screenshot to save
        filename_pattern (str): Filename pattern with placeholders
        **format_kwargs: Arguments to format the filename
        
    Returns:
        str or None: Path of saved file or None if it fails
    """
    try:
        if screenshot is None:
            log_error("Attempt to save None screenshot")
            return None
        
        # Add timestamp if not present
        if 'timestamp' not in format_kwargs:
            format_kwargs['timestamp'] = datetime.now().strftime(FILE_TIMESTAMP_FORMAT)
        
        # Format filename
        filename = filename_pattern.format(**format_kwargs)
        filepath = os.path.join(SCREENSHOTS_FOLDER, filename)
        
        # Save screenshot
        screenshot.save(filepath)
        log_debug(f"Screenshot saved: {filename}")
        return filepath
        
    except Exception as e:
        log_error(f"Error saving screenshot: {e}")
        return None

def validate_image(image):
    """Validates that an image is usable.
    
    Args:
        image: Image to validate (PIL.Image or numpy.ndarray)
        
    Returns:
        bool: True if the image is valid
    """
    try:
        if image is None:
            return False
        
        # Check PIL Image
        if isinstance(image, Image.Image):
            if image.width < MIN_IMAGE_WIDTH or image.height < MIN_IMAGE_HEIGHT:
                return False
            return True
        
        # Check numpy array
        if isinstance(image, np.ndarray):
            if len(image.shape) < 2:
                return False
            height, width = image.shape[:2]
            if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                return False
            return True
        
        return False
        
    except Exception:
        return False

def pil_to_cv2(pil_image):
    """Converts a PIL image to OpenCV format.
    
    Args:
        pil_image (PIL.Image): PIL image to convert
        
    Returns:
        numpy.ndarray or None: OpenCV image or None if it fails
    """
    try:
        if not validate_image(pil_image):
            return None
        
        # Convert to RGB if necessary
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Convert to numpy array
        cv2_image = np.array(pil_image)
        
        # OpenCV uses BGR, PIL uses RGB
        cv2_image = cv2.cvtColor(cv2_image, cv2.COLOR_RGB2BGR)
        
        return cv2_image
        
    except Exception as e:
        log_error(f"Error converting PIL->CV2: {e}")
        return None

def cv2_to_pil(cv2_image):
    """Converts an OpenCV image to PIL format.
    
    Args:
        cv2_image (numpy.ndarray): OpenCV image to convert
        
    Returns:
        PIL.Image or None: PIL image or None if it fails
    """
    try:
        if not validate_image(cv2_image):
            return None
        
        # OpenCV uses BGR, PIL uses RGB
        if len(cv2_image.shape) == 3:
            rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = cv2_image
        
        # Convert to PIL
        pil_image = Image.fromarray(rgb_image)
        
        return pil_image
        
    except Exception as e:
        log_error(f"Error converting CV2->PIL: {e}")
        return None

def enhance_with_clahe(image):
    """Applies CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image (numpy.ndarray): Image to process
        
    Returns:
        numpy.ndarray or None: Processed image or None if it fails
    """
    try:
        if not validate_image(image):
            return None
        
        # Convert to grayscale if necessary
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply CLAHE
        clahe = cv2.createCLAHE(
            clipLimit=CLAHE_CLIP_LIMIT,
            tileGridSize=CLAHE_TILE_GRID_SIZE
        )
        enhanced = clahe.apply(gray)
        
        return enhanced
        
    except Exception as e:
        log_error(f"Error in CLAHE enhancement: {e}")
        return None

def enhance_dark_on_light(image):
    """Enhancement for dark text on light background.
    
    Args:
        image (numpy.ndarray): Image to process
        
    Returns:
        numpy.ndarray or None: Processed image or None if it fails
    """
    try:
        if not validate_image(image):
            return None
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply adaptive threshold
        enhanced = cv2.adaptiveThreshold(
            gray,
            ADAPTIVE_THRESHOLD_MAX_VALUE,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            ADAPTIVE_THRESHOLD_BLOCK_SIZE,
            ADAPTIVE_THRESHOLD_C
        )
        
        return enhanced
        
    except Exception as e:
        log_error(f"Error in dark-on-light enhancement: {e}")
        return None

def enhance_light_on_dark(image):
    """Enhancement for light text on dark background.
    
    Args:
        image (numpy.ndarray): Image to process
        
    Returns:
        numpy.ndarray or None: Processed image or None if it fails
    """
    try:
        if not validate_image(image):
            return None
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply inverted adaptive threshold
        enhanced = cv2.adaptiveThreshold(
            gray,
            ADAPTIVE_THRESHOLD_MAX_VALUE,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            ADAPTIVE_THRESHOLD_BLOCK_SIZE,
            ADAPTIVE_THRESHOLD_C
        )
        
        return enhanced
        
    except Exception as e:
        log_error(f"Error in light-on-dark enhancement: {e}")
        return None

def apply_noise_reduction(image):
    """Applies noise reduction to the image.
    
    Args:
        image (numpy.ndarray): Image to process
        
    Returns:
        numpy.ndarray or None: Processed image or None if it fails
    """
    try:
        if not validate_image(image):
            return None
        
        # Apply bilateral filter to reduce noise while preserving edges
        if len(image.shape) == 3:
            denoised = cv2.bilateralFilter(
                image,
                BILATERAL_FILTER_D,
                BILATERAL_FILTER_SIGMA_COLOR,
                BILATERAL_FILTER_SIGMA_SPACE
            )
        else:
            # For grayscale images, use medianBlur
            denoised = cv2.medianBlur(image, MEDIAN_BLUR_KERNEL_SIZE)
        
        return denoised
        
    except Exception as e:
        log_error(f"Error in noise reduction: {e}")
        return None

def apply_sharpening(image):
    """Applies sharpening to the image.
    
    Args:
        image (numpy.ndarray): Image to process
        
    Returns:
        numpy.ndarray or None: Processed image or None if it fails
    """
    try:
        if not validate_image(image):
            return None
        
        # Create sharpening kernel
        kernel = np.array(SHARPENING_KERNEL, dtype=np.float32)
        
        # Apply the filter
        sharpened = cv2.filter2D(image, -1, kernel)
        
        return sharpened
        
    except Exception as e:
        log_error(f"Error in sharpening: {e}")
        return None

def enhance_image_for_text_detection(screenshot):
    """Applies various enhancement methods to improve text detection.
    
    Args:
        screenshot (PIL.Image): Original screenshot
        
    Returns:
        list: List of tuples (method_name, enhanced_image_pil) or empty list if it fails
    """
    enhanced_images = []
    
    try:
        # Input validation
        if not validate_image(screenshot):
            log_error("Invalid screenshot for enhancement")
            return []
        
        log_debug(f"Starting image enhancement {screenshot.width}x{screenshot.height}")
        
        # Convert to OpenCV format
        cv2_image = pil_to_cv2(screenshot)
        if cv2_image is None:
            log_error("Error converting screenshot for enhancement")
            return []
        
        # Enhancement methods
        enhancement_methods = [
            ('CLAHE', enhance_with_clahe),
            ('DARK_ON_LIGHT', enhance_dark_on_light),
            ('LIGHT_ON_DARK', enhance_light_on_dark)
        ]
        
        for method_name, enhance_func in enhancement_methods:
            try:
                log_debug(f"Applying enhancement: {method_name}")
                
                # Apply enhancement
                enhanced_cv2 = enhance_func(cv2_image)
                if enhanced_cv2 is None:
                    log_error(f"Enhancement {method_name} returned None")
                    continue
                
                # Apply optional post-processing
                try:
                    # Noise reduction
                    enhanced_cv2 = apply_noise_reduction(enhanced_cv2)
                    if enhanced_cv2 is None:
                        log_error(f"Noise reduction failed for {method_name}")
                        continue
                    
                    # Sharpening
                    enhanced_cv2 = apply_sharpening(enhanced_cv2)
                    if enhanced_cv2 is None:
                        log_error(f"Sharpening failed for {method_name}")
                        continue
                        
                except Exception as e:
                    log_error(f"Post-processing error for {method_name}: {e}")
                    # Continue without post-processing
                
                # Convert back to PIL
                enhanced_pil = cv2_to_pil(enhanced_cv2)
                if enhanced_pil is None:
                    log_error(f"PIL conversion failed for {method_name}")
                    continue
                
                enhanced_images.append((method_name, enhanced_pil))
                log_debug(f"Enhancement {method_name} completed successfully")
                
            except Exception as e:
                log_error(f"Error during enhancement {method_name}: {e}")
                record_enhancement_error()
                continue
        
        log_debug(f"Enhancement completed: {len(enhanced_images)} images generated")
        return enhanced_images
        
    except Exception as e:
        log_error(f"Critical error during enhancement: {e}")
        record_enhancement_error()
        return []

def save_enhanced_image(enhanced_image, method_name):
    """Saves an enhanced image for debugging.
    
    Args:
        enhanced_image (PIL.Image): Enhanced image to save
        method_name (str): Name of the enhancement method
        
    Returns:
        str or None: Path of saved file or None if it fails
    """
    try:
        return save_screenshot(
            enhanced_image,
            SCREENSHOT_ENHANCED_PATTERN,
            method_name=method_name
        )
    except Exception as e:
        log_error(f"Error saving enhanced image {method_name}: {e}")
        return None