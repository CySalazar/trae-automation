#!/usr/bin/env python3
"""Test script to verify pattern matching with OCR results."""

import re
import os
import sys
from PIL import Image

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import TARGET_PATTERN, TARGET_END_WORD
from ocr_engine import extract_all_text_with_positions, find_target_pattern_in_detections

def test_pattern_matching():
    """Test pattern matching with known OCR results."""
    
    print(f"Current TARGET_PATTERN: {TARGET_PATTERN}")
    print(f"Current TARGET_END_WORD: {TARGET_END_WORD}")
    
    # Test strings we know are in the OCR results
    test_strings = [
        "'Model\s+thinking\s+limit\s+reached.*?Continue.*?t0'",
        "Model thinking limit reached.*?Continue.*?t0",
        "Model thinking limit reached, please enter 'Continue' t0",
        "Model thinking limit reached, please enter 'Continue' to",
        "'Model\s+thinking\s+limit\s+reached.*?Continue.*?t0\"",
    ]
    
    print("\n=== PATTERN MATCHING TESTS ===")
    pattern = re.compile(TARGET_PATTERN, re.IGNORECASE | re.DOTALL)
    
    for test_str in test_strings:
        print(f"\nTesting: {test_str}")
        match = pattern.search(test_str)
        if match:
            print(f"✅ MATCH found: '{match.group()}'")
            print(f"   Start: {match.start()}, End: {match.end()}")
        else:
            print(f"❌ NO MATCH")
    
    # Test with actual OCR results if screenshot exists
    screenshot_path = "screenshots/debug_fullscreen_20250825_120020.png"
    if os.path.exists(screenshot_path):
        print("\n=== ACTUAL OCR TEST (ORIGINAL IMAGE) ===")
        try:
            image = Image.open(screenshot_path)
            detections = extract_all_text_with_positions(image)
            
            print(f"Total detections: {len(detections)}")
            
            # Test our pattern matching function
            coordinates = find_target_pattern_in_detections(detections, TARGET_PATTERN, TARGET_END_WORD)
            
            if coordinates:
                print(f"✅ TARGET FOUND IN ORIGINAL!")
                print(f"   Coordinates found: {len(coordinates)}")
                for i, coord in enumerate(coordinates):
                    print(f"   Coordinate {i+1}: ({coord[0]}, {coord[1]})")
            else:
                print(f"❌ TARGET NOT FOUND IN ORIGINAL")
                
        except Exception as e:
            print(f"OCR test failed: {e}")
            
        # Test with enhanced images (like the real system does)
        print("\n=== ENHANCED IMAGES TEST (LIKE REAL SYSTEM) ===")
        try:
            from image_processing import enhance_image_for_text_detection
            
            image = Image.open(screenshot_path)
            enhanced_images = enhance_image_for_text_detection(image)
            
            print(f"Enhanced images generated: {len(enhanced_images)}")
            
            all_detections = []
            for method_name, enhanced_image in enhanced_images:
                print(f"\nTesting enhanced image: {method_name}")
                try:
                    detections = extract_all_text_with_positions(enhanced_image)
                    print(f"  Detections: {len(detections)}")
                    all_detections.extend(detections)
                    
                    # Test pattern on this enhanced image
                    coordinates = find_target_pattern_in_detections(detections, TARGET_PATTERN, TARGET_END_WORD)
                    if coordinates:
                        print(f"  ✅ TARGET FOUND in {method_name}!")
                        for i, coord in enumerate(coordinates):
                            print(f"    Coordinate {i+1}: ({coord[0]}, {coord[1]})")
                    else:
                        print(f"  ❌ TARGET NOT FOUND in {method_name}")
                        
                except Exception as e:
                    print(f"  Error processing {method_name}: {e}")
            
            # Test with all detections combined (like real system)
            print(f"\n=== COMBINED ENHANCED DETECTIONS ===")
            print(f"Total combined detections: {len(all_detections)}")
            
            # Deduplicate like the real system
            from scanner import deduplicate_detections
            unique_detections = deduplicate_detections(all_detections)
            print(f"After deduplication: {len(unique_detections)}")
            
            coordinates = find_target_pattern_in_detections(unique_detections, TARGET_PATTERN, TARGET_END_WORD)
            if coordinates:
                print(f"✅ TARGET FOUND IN COMBINED ENHANCED!")
                print(f"   Coordinates found: {len(coordinates)}")
                for i, coord in enumerate(coordinates):
                    print(f"   Coordinate {i+1}: ({coord[0]}, {coord[1]})")
            else:
                print(f"❌ TARGET NOT FOUND IN COMBINED ENHANCED")
                
                # Debug: show detections that contain relevant words
                relevant_detections = []
                for det in unique_detections:
                    text_lower = det['text'].lower()
                    if any(word in text_lower for word in ['model', 'thinking', 'continue', 'limit', 'reached']):
                        relevant_detections.append(det)
                
                print(f"\nRelevant detections ({len(relevant_detections)}):")
                for det in relevant_detections[:10]:  # First 10
                    print(f"  - '{det['text']}' @ ({det['center_x']}, {det['center_y']}) conf:{det['confidence']}")
                    
                    # Test pattern on this specific detection
                    match = pattern.search(det['text'])
                    if match:
                        print(f"    ✅ This detection matches the pattern!")
                        
        except Exception as e:
            print(f"Enhanced images test failed: {e}")
    else:
        print(f"\nScreenshot not found: {screenshot_path}")

if __name__ == "__main__":
    test_pattern_matching()