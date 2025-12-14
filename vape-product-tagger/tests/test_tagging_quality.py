"""
Comprehensive tagging quality tests to identify issues.
Tests a variety of real-world product scenarios.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.product_tagger import ProductTagger
from modules.taxonomy import VapeTaxonomy


class MockConfig:
    """Mock config for testing"""
    ollama_base_url = "http://localhost:11434"
    ollama_model = "llama3"
    ollama_timeout = 30
    third_opinion_model = "llama3"
    ai_confidence_threshold = 0.7
    enable_third_opinion = False
    enable_compliance_tags = False
    enable_ai_tagging = False


class MockLogger:
    """Mock logger for testing"""
    def debug(self, msg, *args): pass
    def info(self, msg, *args): pass
    def warning(self, msg, *args): pass
    def error(self, msg, *args): pass


def create_tagger():
    """Create a ProductTagger with mock dependencies"""
    config = MockConfig()
    logger = MockLogger()
    return ProductTagger(config, logger)


def test_category_detection():
    """Test category detection accuracy"""
    tagger = create_tagger()
    
    test_cases = [
        # (product_data, expected_category, description)
        ({"title": "Elf Bar 600 Strawberry Ice 20mg", "description": ""}, "disposable", "Basic disposable"),
        ({"title": "Crystal Bar 600 Puffs Blue Razz", "description": ""}, "disposable", "Puffs indicator"),
        ({"title": "SMOK Nord 5 Pod Kit", "description": ""}, "pod_system", "Pod system kit"),
        ({"title": "Vampire Vape Heisenberg 10ml", "description": ""}, "e-liquid", "10ml e-liquid"),
        ({"title": "SMOK RPM 2 Replacement Coil 0.4ohm", "description": ""}, "coil", "Replacement coil"),
        ({"title": "Vaporesso XROS 3 Replacement Pod", "description": ""}, "pod", "Replacement pod"),
        ({"title": "CBD Oil 1000mg Full Spectrum", "description": ""}, "CBD", "CBD oil product"),
        ({"title": "18650 Battery 3000mAh", "description": ""}, "accessory", "Battery accessory"),
        ({"title": "USB-C Vape Charger", "description": ""}, "accessory", "Charger accessory"),
        ({"title": "Pablo Nicotine Pouches 20mg", "description": ""}, "nicotine_pouches", "Nicotine pouches"),
    ]
    
    print("\n=== Testing Category Detection ===")
    passed = 0
    failed = 0
    
    for product_data, expected, description in test_cases:
        result = tagger.tag_category(product_data)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
            print(f"{status} PASS: {description}")
        else:
            failed += 1
            print(f"{status} FAIL: {description}")
            print(f"    Title: '{product_data['title']}'")
            print(f"    Expected: {expected}, Got: {result}")
    
    return passed, failed


def test_flavor_detection():
    """Test flavor tagging accuracy"""
    tagger = create_tagger()
    
    test_cases = [
        # (product_data, expected_flavors, description)
        ({"title": "Strawberry Ice 10ml", "description": ""}, ["fruity", "ice"], "Strawberry Ice should be fruity+ice"),
        ({"title": "Blue Razz Lemonade", "description": ""}, ["candy/sweets", "beverages"], "Blue Razz (candy) + Lemonade (beverage)"),
        ({"title": "Mango Peach", "description": ""}, ["fruity"], "Pure fruit combo"),
        ({"title": "Menthol Blast", "description": ""}, ["ice"], "Menthol should be ice"),
        ({"title": "Classic Tobacco", "description": ""}, ["tobacco"], "Tobacco flavor"),
        ({"title": "Vanilla Custard", "description": ""}, ["desserts/bakery"], "Custard is dessert"),
        ({"title": "Cola Ice", "description": ""}, ["beverages", "ice"], "Cola is beverage"),
        ({"title": "Bubblegum", "description": ""}, ["candy/sweets"], "Bubblegum is candy"),
        ({"title": "Spearmint", "description": ""}, ["ice"], "Spearmint should be ice/menthol"),
        ({"title": "Unflavoured Base", "description": ""}, ["unflavoured"], "Unflavoured"),
    ]
    
    print("\n=== Testing Flavor Detection ===")
    passed = 0
    failed = 0
    
    for product_data, expected, description in test_cases:
        primary, secondary = tagger.tag_flavors(product_data, category="e-liquid")
        
        # Check if all expected flavors are detected
        all_detected = all(f in primary for f in expected)
        status = "✓" if all_detected else "✗"
        
        if all_detected:
            passed += 1
            print(f"{status} PASS: {description}")
        else:
            failed += 1
            print(f"{status} FAIL: {description}")
            print(f"    Title: '{product_data['title']}'")
            print(f"    Expected: {expected}, Got: {primary}")
    
    return passed, failed


def test_nicotine_strength():
    """Test nicotine strength extraction"""
    tagger = create_tagger()
    
    test_cases = [
        # (product_data, expected_tag, description)
        ({"title": "Elf Bar 600 Strawberry 20mg", "description": ""}, "20mg", "20mg in title"),
        ({"title": "Crystal Bar 10mg Blue Razz", "description": ""}, "10mg", "10mg in title"),
        ({"title": "Lost Mary 0mg Nicotine Free", "description": ""}, "0mg", "0mg explicit"),
        ({"title": "Nicotine Salt 3mg", "description": ""}, "3mg", "3mg nic salt"),
        ({"title": "Zero Nicotine E-Liquid", "description": ""}, "0mg", "Zero nicotine phrase"),
        ({"title": "E-Liquid 50/50", "description": ""}, None, "No mg value should return None"),
    ]
    
    print("\n=== Testing Nicotine Strength ===")
    passed = 0
    failed = 0
    
    for product_data, expected, description in test_cases:
        result = tagger.tag_nicotine_strength(product_data, category="e-liquid")
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
            print(f"{status} PASS: {description}")
        else:
            failed += 1
            print(f"{status} FAIL: {description}")
            print(f"    Title: '{product_data['title']}'")
            print(f"    Expected: {expected}, Got: {result}")
    
    return passed, failed


def test_vg_ratio():
    """Test VG/PG ratio detection"""
    tagger = create_tagger()
    
    test_cases = [
        # (product_data, expected_ratio, description)
        ({"title": "E-Liquid 70VG/30PG", "description": ""}, "70/30", "Standard format"),
        ({"title": "50/50 VG PG E-Liquid", "description": ""}, "50/50", "Ratio first"),
        ({"title": "E-Liquid 80VG 20PG", "description": ""}, "80/20", "Space separated"),
        ({"title": "Max VG E-Liquid", "description": ""}, None, "Max VG (no ratio)"),
        ({"title": "70/30 Nic Salt", "description": ""}, "70/30", "Ratio only"),
    ]
    
    print("\n=== Testing VG/PG Ratio ===")
    passed = 0
    failed = 0
    
    for product_data, expected, description in test_cases:
        result = tagger.tag_vg_ratio(product_data, category="e-liquid")
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
            print(f"{status} PASS: {description}")
        else:
            failed += 1
            print(f"{status} FAIL: {description}")
            print(f"    Title: '{product_data['title']}'")
            print(f"    Expected: {expected}, Got: {result}")
    
    return passed, failed


def test_bottle_size():
    """Test bottle size detection"""
    tagger = create_tagger()
    
    test_cases = [
        # (product_data, expected_sizes, description)
        ({"title": "E-Liquid 10ml", "description": ""}, ["10ml"], "Standard 10ml"),
        ({"title": "Shortfill 100ml", "description": ""}, ["100ml", "shortfill"], "100ml shortfill"),
        ({"title": "50ml E-Juice", "description": ""}, ["50ml"], "50ml"),
        ({"title": "E-Liquid 120ml", "description": ""}, [], "120ml not approved"),
    ]
    
    print("\n=== Testing Bottle Size ===")
    passed = 0
    failed = 0
    
    for product_data, expected, description in test_cases:
        result = tagger.tag_bottle_size(product_data, category="e-liquid")
        
        # Sort for comparison
        result_sorted = sorted(result)
        expected_sorted = sorted(expected)
        
        status = "✓" if result_sorted == expected_sorted else "✗"
        
        if result_sorted == expected_sorted:
            passed += 1
            print(f"{status} PASS: {description}")
        else:
            failed += 1
            print(f"{status} FAIL: {description}")
            print(f"    Title: '{product_data['title']}'")
            print(f"    Expected: {expected_sorted}, Got: {result_sorted}")
    
    return passed, failed


def test_cbd_products():
    """Test CBD product tagging"""
    tagger = create_tagger()
    
    test_cases = [
        # (product_data, expected_form, expected_type, expected_strength, description)
        ({"title": "CBD Oil 1000mg Full Spectrum", "description": ""}, ["oil"], ["full_spectrum"], "1000mg", "CBD oil full spectrum"),
        ({"title": "CBD Gummies 25mg", "description": ""}, ["gummy"], [], "25mg", "CBD gummies"),
        ({"title": "CBD Isolate 99% Pure 500mg", "description": ""}, ["isolate"], ["isolate"], "500mg", "CBD isolate with strength"),
        ({"title": "Broad Spectrum CBD Capsules 500mg", "description": ""}, ["capsule"], ["broad_spectrum"], "500mg", "Broad spectrum capsules"),
    ]
    
    print("\n=== Testing CBD Products ===")
    passed = 0
    failed = 0
    
    for product_data, expected_form, expected_type, expected_strength, description in test_cases:
        form = tagger.tag_cbd_form(product_data, category="CBD")
        cbd_type = tagger.tag_cbd_type(product_data, category="CBD")
        strength = tagger.tag_cbd_strength(product_data, category="CBD")
        
        form_ok = all(f in form for f in expected_form)
        type_ok = all(t in cbd_type for t in expected_type)
        strength_ok = strength == expected_strength
        
        all_ok = form_ok and type_ok and strength_ok
        status = "✓" if all_ok else "✗"
        
        if all_ok:
            passed += 1
            print(f"{status} PASS: {description}")
        else:
            failed += 1
            print(f"{status} FAIL: {description}")
            print(f"    Title: '{product_data['title']}'")
            if not form_ok:
                print(f"    Form - Expected: {expected_form}, Got: {form}")
            if not type_ok:
                print(f"    Type - Expected: {expected_type}, Got: {cbd_type}")
            if not strength_ok:
                print(f"    Strength - Expected: {expected_strength}, Got: {strength}")
    
    return passed, failed


def run_all_tests():
    """Run all tagging quality tests"""
    print("=" * 60)
    print("TAGGING QUALITY ASSESSMENT")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    results = []
    
    # Run each test suite
    p, f = test_category_detection()
    results.append(("Category Detection", p, f))
    total_passed += p
    total_failed += f
    
    p, f = test_flavor_detection()
    results.append(("Flavor Detection", p, f))
    total_passed += p
    total_failed += f
    
    p, f = test_nicotine_strength()
    results.append(("Nicotine Strength", p, f))
    total_passed += p
    total_failed += f
    
    p, f = test_vg_ratio()
    results.append(("VG/PG Ratio", p, f))
    total_passed += p
    total_failed += f
    
    p, f = test_bottle_size()
    results.append(("Bottle Size", p, f))
    total_passed += p
    total_failed += f
    
    p, f = test_cbd_products()
    results.append(("CBD Products", p, f))
    total_passed += p
    total_failed += f
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed, failed in results:
        total = passed + failed
        pct = (passed / total * 100) if total > 0 else 0
        status = "✓" if failed == 0 else "✗"
        print(f"{status} {name}: {passed}/{total} ({pct:.0f}%)")
    
    print("-" * 60)
    grand_total = total_passed + total_failed
    grand_pct = (total_passed / grand_total * 100) if grand_total > 0 else 0
    print(f"TOTAL: {total_passed}/{grand_total} ({grand_pct:.0f}%)")
    
    if total_failed > 0:
        print("\n⚠️  Some tests failed - tagging logic needs improvement")
    else:
        print("\n✓ All tests passed!")
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
