"""Module for text extraction via OCR.

This module provides complete functionality for:
- Text extraction from images with multiple OCR configurations
- Validation and processing of OCR results
- Error handling and retry for OCR operations
- Detection deduplication
"""

import re
import pytesseract
from PIL import Image

from config import (
    OCR_CONFIGS, MIN_CONFIDENCE_THRESHOLD,
    DEDUPLICATION_DISTANCE_THRESHOLD, FINAL_COORDINATES_TOLERANCE
)
from logger import (
    log_message, log_error, log_debug, log_enhancement_stats,
    record_ocr_error
)
from image_processing import validate_image

def extract_text_with_single_config(image, config):
    """Extracts text from an image using a single OCR configuration.
    
    Args:
        image (PIL.Image): Image to process
        config (str): OCR configuration to use
        
    Returns:
        dict or None: OCR data or None if it fails
    """
    try:
        if not validate_image(image):
            return None
        
        # Execute OCR with the specified configuration
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config=config
        )
        
        return data
        
    except Exception as e:
        log_error(f"OCR error with config '{config}': {e}")
        return None

def validate_ocr_data(data):
    """Validates OCR data returned by Tesseract.
    
    Args:
        data (dict): OCR data to validate
        
    Returns:
        bool: True if the data is valid
    """
    try:
        if not data or not isinstance(data, dict):
            return False
        
        # Check that necessary keys are present
        required_keys = ['text', 'left', 'top', 'width', 'height', 'conf']
        for key in required_keys:
            if key not in data:
                return False
            if not isinstance(data[key], list):
                return False
        
        # Check that all lists have the same length
        lengths = [len(data[key]) for key in required_keys]
        if not all(length == lengths[0] for length in lengths):
            return False
        
        return True
        
    except Exception:
        return False

def process_single_detection(i, data):
    """Processes a single OCR detection.
    
    Args:
        i (int): Detection index
        data (dict): Complete OCR data
        
    Returns:
        dict or None: Processed detection or None if invalid
    """
    try:
        text = data['text'][i].strip()
        confidence = data['conf'][i]
        left = data['left'][i]
        top = data['top'][i]
        width = data['width'][i]
        height = data['height'][i]
        
        # Basic validation
        if not text or confidence < MIN_CONFIDENCE_THRESHOLD:
            return None
        
        # Coordinate validation
        if not all(isinstance(val, (int, float)) for val in [left, top, width, height]):
            return None
        
        if left < 0 or top < 0 or width <= 0 or height <= 0:
            return None
        
        # Calculate center coordinates
        center_x = int(left + width // 2)
        center_y = int(top + height // 2)
        
        return {
            'text': text,
            'confidence': float(confidence),
            'left': int(left),
            'top': int(top),
            'width': int(width),
            'height': int(height),
            'center_x': center_x,
            'center_y': center_y
        }
        
    except Exception as e:
        log_error(f"Error processing detection {i}: {e}")
        return None

def extract_all_text_with_positions(image):
    """Extracts all text with positions from an image using multiple OCR configurations.
    
    Args:
        image (PIL.Image): Image to process
        
    Returns:
        list: List of valid detections
    """
    all_detections = []
    
    try:
        # Input validation
        if not validate_image(image):
            log_error("Invalid image for text extraction")
            return []
        
        log_debug(f"Starting text extraction from image {image.width}x{image.height}")
        
        # Try all OCR configurations
        for config in OCR_CONFIGS:
            try:
                log_debug(f"OCR attempt with config: {config}")
                
                # Extract OCR data
                data = extract_text_with_single_config(image, config)
                if not validate_ocr_data(data):
                    log_debug(f"Invalid OCR data for config: {config}")
                    continue
                
                # Process each detection
                valid_detections = 0
                for i in range(len(data['text'])):
                    try:
                        detection = process_single_detection(i, data)
                        if detection:
                            all_detections.append(detection)
                            valid_detections += 1
                    except Exception as e:
                        log_error(f"Error processing detection {i} with config {config}: {e}")
                        continue
                
                log_debug(f"Config {config}: {valid_detections} valid detections")
                
            except Exception as e:
                log_error(f"OCR error with configuration {config}: {e}")
                record_ocr_error()
                continue
        
        log_debug(f"Text extraction completed: {len(all_detections)} total detections")
        return all_detections
        
    except Exception as e:
        log_error(f"Critical error during text extraction: {e}")
        record_ocr_error()
        return []

def calculate_distance(det1, det2):
    """Calculates the Euclidean distance between two detections.
    
    Args:
        det1 (dict): First detection
        det2 (dict): Second detection
        
    Returns:
        float: Euclidean distance
    """
    try:
        dx = det1['center_x'] - det2['center_x']
        dy = det1['center_y'] - det2['center_y']
        return (dx * dx + dy * dy) ** 0.5
    except Exception:
        return float('inf')

def deduplicate_detections(detections):
    """Removes duplicate detections based on distance and confidence.
    
    Args:
        detections (list): List of detections to deduplicate
        
    Returns:
        list: List of deduplicated detections
    """
    try:
        # Input validation
        if not detections or not isinstance(detections, list):
            log_debug("Empty or invalid detection list")
            return []
        
        log_debug(f"Starting deduplication of {len(detections)} detections")
        
        # Filter invalid detections
        valid_detections = []
        for det in detections:
            try:
                if not isinstance(det, dict):
                    continue
                
                required_fields = ['text', 'confidence', 'center_x', 'center_y']
                if not all(field in det for field in required_fields):
                    continue
                
                # Value validation
                if not det['text'] or det['text'].isspace():
                    continue
                
                if not isinstance(det['confidence'], (int, float)) or det['confidence'] < 0:
                    continue
                
                if not all(isinstance(det[field], (int, float)) for field in ['center_x', 'center_y']):
                    continue
                
                if det['center_x'] < 0 or det['center_y'] < 0:
                    continue
                
                valid_detections.append(det)
                
            except Exception as e:
                log_error(f"Error validating detection: {e}")
                continue
        
        if not valid_detections:
            log_debug("No valid detections after filtering")
            return []
        
        log_debug(f"Valid detections after filtering: {len(valid_detections)}")
        
        # Sort by confidence (highest first)
        try:
            valid_detections.sort(key=lambda x: x['confidence'], reverse=True)
        except Exception as e:
            log_error(f"Error sorting detections: {e}")
            return valid_detections  # Return without sorting
        
        # Deduplication
        deduplicated = []
        for current in valid_detections:
            try:
                is_duplicate = False
                
                for existing in deduplicated:
                    try:
                        # Check if text is identical
                        if current['text'].lower() == existing['text'].lower():
                            distance = calculate_distance(current, existing)
                            if distance < DEDUPLICATION_DISTANCE_THRESHOLD:
                                is_duplicate = True
                                break
                    except Exception as e:
                        log_error(f"Error comparing detections: {e}")
                        continue
                
                if not is_duplicate:
                    deduplicated.append(current)
                    
            except Exception as e:
                log_error(f"Error during deduplication: {e}")
                continue
        
        log_debug(f"Deduplication completed: {len(deduplicated)} unique detections")
        return deduplicated
        
    except Exception as e:
        log_error(f"Critical error during deduplication: {e}")
        # Fallback: return original detections
        return detections if isinstance(detections, list) else []

def find_target_pattern_in_detections(detections, target_pattern, target_end_word):
    """Searches for target pattern in detections and finds coordinates of the final word.
    
    Args:
        detections (list): List of detections
        target_pattern (str): Regex pattern to search for
        target_end_word (str): Final word to find coordinates for
        
    Returns:
        list: List of found coordinates (x, y)
    """
    coordinates = []
    
    try:
        if not detections:
            return coordinates
        
        log_debug(f"Searching pattern '{target_pattern}' in {len(detections)} detections")
        
        # Create a string with all detected text
        all_text_parts = []
        text_to_detection = {}  # Map text position -> detection
        
        current_pos = 0
        for det in detections:
            try:
                text = det['text']
                all_text_parts.append(text)
                
                # Map each character to its detection
                for i in range(len(text)):
                    text_to_detection[current_pos + i] = det
                
                current_pos += len(text) + 1  # +1 for space
                all_text_parts.append(' ')  # Add space between detections
                
            except Exception as e:
                log_error(f"Error processing detection for pattern: {e}")
                continue
        
        full_text = ''.join(all_text_parts)
        log_debug(f"Full text for search: '{full_text[:100]}...'")
        
        # Search for the pattern
        try:
            pattern_matches = list(re.finditer(target_pattern, full_text, re.IGNORECASE))
            log_debug(f"Found {len(pattern_matches)} pattern matches")
            
            for match in pattern_matches:
                try:
                    # Find all occurrences of target word in the match
                    match_text = match.group()
                    word_pattern = r'\b' + re.escape(target_end_word) + r'\b'
                    word_matches = list(re.finditer(word_pattern, match_text, re.IGNORECASE))
                    
                    for word_match in word_matches:
                        try:
                            # Calculate absolute position of the word
                            word_start_pos = match.start() + word_match.start()
                            word_end_pos = match.start() + word_match.end() - 1
                            
                            # Find detection corresponding to end of word
                            if word_end_pos in text_to_detection:
                                det = text_to_detection[word_end_pos]
                                coord = (det['center_x'], det['center_y'])
                                coordinates.append(coord)
                                log_debug(f"Coordinates found for '{target_end_word}': {coord}")
                            
                        except Exception as e:
                            log_error(f"Error extracting word coordinates: {e}")
                            continue
                            
                except Exception as e:
                    log_error(f"Error processing pattern match: {e}")
                    continue
                    
        except Exception as e:
            log_error(f"Error searching regex pattern: {e}")
        
        log_debug(f"Pattern search completed: {len(coordinates)} coordinates found")
        return coordinates
        
    except Exception as e:
        log_error(f"Critical error during pattern search: {e}")
        return []

def deduplicate_coordinates(coordinates, tolerance=None):
    """Final deduplication of found coordinates.
    
    Args:
        coordinates (list): List of coordinates (x, y)
        tolerance (int, optional): Tolerance for considering coordinates as duplicates
        
    Returns:
        list: List of deduplicated coordinates
    """
    if tolerance is None:
        tolerance = FINAL_COORDINATES_TOLERANCE
    
    try:
        if not coordinates:
            return []
        
        log_debug(f"Deduplicating {len(coordinates)} coordinates with tolerance {tolerance}")
        
        deduplicated = []
        for coord in coordinates:
            try:
                if not isinstance(coord, (tuple, list)) or len(coord) != 2:
                    continue
                
                x, y = coord
                if not all(isinstance(val, (int, float)) for val in [x, y]):
                    continue
                
                is_duplicate = False
                for existing_coord in deduplicated:
                    try:
                        ex_x, ex_y = existing_coord
                        distance = ((x - ex_x) ** 2 + (y - ex_y) ** 2) ** 0.5
                        if distance <= tolerance:
                            is_duplicate = True
                            break
                    except Exception:
                        continue
                
                if not is_duplicate:
                    deduplicated.append((int(x), int(y)))
                    
            except Exception as e:
                log_error(f"Error deduplicating coordinate {coord}: {e}")
                continue
        
        log_debug(f"Coordinate deduplication completed: {len(deduplicated)} unique coordinates")
        return deduplicated
        
    except Exception as e:
        log_error(f"Critical error in coordinate deduplication: {e}")
        return coordinates if isinstance(coordinates, list) else []