#!/usr/bin/env python3
"""Debug script to analyze OCR detection on the specific screenshot."""

import os
import sys
from PIL import Image
import pytesseract

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import TESSERACT_CMD, OCR_CONFIGS, MIN_CONFIDENCE_THRESHOLD
from ocr_engine import extract_all_text_with_positions
from image_processing import enhance_image_for_text_detection

def debug_screenshot_ocr():
    """Debug OCR on the latest screenshot."""
    screenshot_path = "screenshots/debug_fullscreen_20250825_120020.png"
    
    if not os.path.exists(screenshot_path):
        print(f"Screenshot not found: {screenshot_path}")
        return
    
    print(f"Analyzing screenshot: {screenshot_path}")
    
    # Load image
    image = Image.open(screenshot_path)
    print(f"Image size: {image.width}x{image.height}")
    
    # Test basic OCR first
    print("\n=== BASIC OCR TEST ===")
    try:
        basic_text = pytesseract.image_to_string(image)
        print(f"Basic OCR text (first 500 chars):\n{basic_text[:500]}...")
        
        # Search for 'Continue' in basic text
        if 'Continue' in basic_text:
            print("✅ 'Continue' found in basic OCR!")
        else:
            print("❌ 'Continue' NOT found in basic OCR")
            
        # Search for 'Model thinking' in basic text
        if 'Model thinking' in basic_text:
            print("✅ 'Model thinking' found in basic OCR!")
        else:
            print("❌ 'Model thinking' NOT found in basic OCR")
            
    except Exception as e:
        print(f"Basic OCR failed: {e}")
    
    # Test with different PSM modes
    print("\n=== PSM MODE TESTS ===")
    for config in OCR_CONFIGS:
        try:
            text = pytesseract.image_to_string(image, config=config)
            if 'Continue' in text or 'Model' in text:
                print(f"✅ Config {config}: Found relevant text")
                print(f"   Text snippet: {text[:200]}...")
            else:
                print(f"❌ Config {config}: No relevant text found")
        except Exception as e:
            print(f"❌ Config {config}: Error - {e}")
    
    # Test with image enhancement
    print("\n=== ENHANCED IMAGE TESTS ===")
    try:
        enhanced_images = enhance_image_for_text_detection(image)
        for method_name, enhanced_image in enhanced_images:
            print(f"\nTesting enhancement: {method_name}")
            try:
                text = pytesseract.image_to_string(enhanced_image)
                if 'Continue' in text or 'Model' in text:
                    print(f"✅ {method_name}: Found relevant text")
                    print(f"   Text snippet: {text[:200]}...")
                else:
                    print(f"❌ {method_name}: No relevant text found")
            except Exception as e:
                print(f"❌ {method_name}: Error - {e}")
    except Exception as e:
        print(f"Enhancement failed: {e}")
    
    # Test with our OCR engine
    print("\n=== OCR ENGINE TEST ===")
    try:
        detections = extract_all_text_with_positions(image)
        print(f"Total detections: {len(detections)}")
        
        # Look for Continue-related text
        continue_detections = [d for d in detections if 'continue' in d['text'].lower()]
        model_detections = [d for d in detections if 'model' in d['text'].lower()]
        thinking_detections = [d for d in detections if 'thinking' in d['text'].lower()]
        
        print(f"Detections with 'continue': {len(continue_detections)}")
        for det in continue_detections:
            print(f"  - '{det['text']}' @ ({det['center_x']}, {det['center_y']}) conf:{det['confidence']}")
            
        print(f"Detections with 'model': {len(model_detections)}")
        for det in model_detections:
            print(f"  - '{det['text']}' @ ({det['center_x']}, {det['center_y']}) conf:{det['confidence']}")
            
        print(f"Detections with 'thinking': {len(thinking_detections)}")
        for det in thinking_detections:
            print(f"  - '{det['text']}' @ ({det['center_x']}, {det['center_y']}) conf:{det['confidence']}")
            
        # Show all detections with high confidence
        high_conf_detections = [d for d in detections if d['confidence'] > 50]
        print(f"\nHigh confidence detections (>50): {len(high_conf_detections)}")
        for det in high_conf_detections[:20]:  # First 20
            print(f"  - '{det['text']}' @ ({det['center_x']}, {det['center_y']}) conf:{det['confidence']}")
            
    except Exception as e:
        print(f"OCR engine test failed: {e}")

if __name__ == "__main__":
    debug_screenshot_ocr()