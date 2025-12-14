"""
Tests for extraction function fixes - verifying substring matching bugs are fixed.

These tests verify that:
1. Nicotine values like "20mg" don't incorrectly match as "0mg" 
2. Capacity values like "12ml" don't incorrectly match as "2ml"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.product_tagger import ProductTagger


class MockConfig:
    """Mock config for testing"""
    ollama_base_url = "http://localhost:11434"
    ollama_model = "llama3"
    ollama_timeout = 30
    third_opinion_model = "llama3"
    ai_confidence_threshold = 0.7
    enable_third_opinion = False


class MockLogger:
    """Mock logger for testing"""
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def create_tagger():
    """Create a ProductTagger with mock dependencies"""
    config = MockConfig()
    logger = MockLogger()
    return ProductTagger(config, logger)


def test_nicotine_extraction():
    """Test that nicotine extraction doesn't have substring matching bugs"""
    tagger = create_tagger()
    
    # Test cases: (input_text, expected_value, description)
    test_cases = [
        # Should NOT match as 0mg (the bug we fixed)
        ("Elf Bar 600 20mg", 20.0, "20mg should not match 0mg substring"),
        ("Crystal Bar 10mg Strawberry", 10.0, "10mg should not match 0mg substring"),
        ("Lost Mary BM600 600 Puffs - 20mg", 20.0, "20mg in complex title"),
        
        # Should correctly identify actual 0mg
        ("Elf Bar 600 0mg", 0.0, "Actual 0mg"),
        ("Zero nicotine e-liquid", 0.0, "Zero nicotine phrase"),
        ("Nicotine free juice", 0.0, "Nicotine free phrase"),
        
        # Edge cases
        ("5mg nicotine salt", 5.0, "Standard 5mg"),
        ("3mg freebase", 3.0, "Standard 3mg"),
        ("18mg traditional", 18.0, "18mg"),
        ("100mg CBD Oil", None, "100mg CBD should not be nicotine - returns None"),
        ("E-Liquid 50/50", None, "No mg value should return None"),
    ]
    
    print("\n=== Testing Nicotine Extraction ===")
    all_passed = True
    
    for text, expected, description in test_cases:
        result = tagger._extract_nicotine_value(text)
        
        # Handle None comparisons properly
        if expected is None:
            passed = result is None
        elif result is None:
            passed = False
        else:
            passed = abs(result - expected) < 0.01
        
        status = "✓" if passed else "✗"
        
        if not passed:
            all_passed = False
            print(f"{status} FAIL: {description}")
            print(f"    Input: '{text}'")
            print(f"    Expected: {expected}, Got: {result}")
        else:
            print(f"{status} PASS: {description}")
    
    return all_passed


def test_capacity_extraction():
    """Test that capacity extraction doesn't have substring matching bugs"""
    tagger = create_tagger()
    
    # Test cases: (title, expected_tags, description)
    test_cases = [
        # Should NOT match smaller values as substrings
        ("Vaporesso GTX 12ml Pod", [], "12ml should not incorrectly match 2ml - 12ml not in approved list"),
        ("SMOK RPM 13ml Tank", [], "13ml not in approved list"),
        ("Aspire Nautilus 22ml Pod", [], "22ml not in approved list"),
        
        # Should correctly match actual values  
        ("Vaporesso GTX 2ml Pod", ["2ml"], "Actual 2ml"),
        ("SMOK TFV 5ml Tank", ["5ml"], "Actual 5ml"),
        ("Uwell 10ml Pod", ["10ml"], "Actual 10ml"),
        
        # Multiple capacities
        ("Tank 2ml or 5ml options", ["2ml", "5ml"], "Multiple valid capacities"),
    ]
    
    print("\n=== Testing Capacity Extraction ===")
    all_passed = True
    
    for title, expected, description in test_cases:
        product_data = {"title": title, "description": ""}
        result = tagger.tag_capacity(product_data, category="pod")
        
        # Sort for comparison
        result_sorted = sorted(result)
        expected_sorted = sorted(expected)
        
        passed = result_sorted == expected_sorted
        status = "✓" if passed else "✗"
        
        if not passed:
            all_passed = False
            print(f"{status} FAIL: {description}")
            print(f"    Input: '{title}'")
            print(f"    Expected: {expected_sorted}, Got: {result_sorted}")
        else:
            print(f"{status} PASS: {description}")
    
    return all_passed


def test_bottle_size_extraction():
    """Test that bottle size extraction uses word boundaries correctly"""
    tagger = create_tagger()
    
    # Test cases: (title, expected_tags, description)
    test_cases = [
        # Should correctly match
        ("E-Liquid 10ml Bottle", ["10ml"], "Standard 10ml"),
        ("Shortfill 100ml", ["100ml", "shortfill"], "100ml shortfill"),
        ("50ml E-Juice", ["50ml"], "Standard 50ml"),
        
        # Multiple sizes
        ("Available in 10ml and 30ml", ["10ml", "30ml"], "Multiple sizes"),
        
        # Should not match incorrect substrings
        ("120ml bottle", [], "120ml not in approved list"),
    ]
    
    print("\n=== Testing Bottle Size Extraction ===")
    all_passed = True
    
    for title, expected, description in test_cases:
        product_data = {"title": title, "description": ""}
        result = tagger.tag_bottle_size(product_data, category="e-liquid")
        
        # Sort for comparison
        result_sorted = sorted(result)
        expected_sorted = sorted(expected)
        
        passed = result_sorted == expected_sorted
        status = "✓" if passed else "✗"
        
        if not passed:
            all_passed = False
            print(f"{status} FAIL: {description}")
            print(f"    Input: '{title}'")
            print(f"    Expected: {expected_sorted}, Got: {result_sorted}")
        else:
            print(f"{status} PASS: {description}")
    
    return all_passed


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Extraction Function Fixes")
    print("=" * 60)
    
    results = []
    results.append(("Nicotine Extraction", test_nicotine_extraction()))
    results.append(("Capacity Extraction", test_capacity_extraction()))
    results.append(("Bottle Size Extraction", test_bottle_size_extraction()))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed! ✓")
    else:
        print("Some tests failed! ✗")
    
    sys.exit(0 if all_passed else 1)
