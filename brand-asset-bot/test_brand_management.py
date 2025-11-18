#!/usr/bin/env python3
"""
Test Script - Brand Management
Tests brand discovery and configuration functionality
"""
import sys
import tempfile
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import (
    Brand, BrandManager, BrandValidator,
    Priority, BrandStatus,
    Config, setup_logger
)


def test_brand_model():
    """Test Brand data model"""
    print("\n" + "="*60)
    print("Test 1: Brand Data Model")
    print("="*60)
    
    # Create brand
    brand = Brand(
        name="SMOK",
        website="smoktech.com",
        priority="high"
    )
    
    tests = [
        ("Brand name", brand.name == "SMOK"),
        ("Brand website", brand.website == "smoktech.com"),
        ("Brand priority", brand.priority == "high"),
        ("Brand status default", brand.status == "pending"),
        ("Has created_at", brand.created_at is not None),
        ("Has updated_at", brand.updated_at is not None),
    ]
    
    # Test to_dict and from_dict
    brand_dict = brand.to_dict()
    brand_copy = Brand.from_dict(brand_dict)
    tests.append(("to_dict/from_dict roundtrip", brand_copy.name == brand.name))
    
    return run_tests(tests)


def test_brand_file_parsing():
    """Test loading brands from file"""
    print("\n" + "="*60)
    print("Test 2: Brand File Parsing")
    print("="*60)
    
    # Create temporary file with brand data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("# Test brands\n")
        f.write("SMOK|smoktech.com|high\n")
        f.write("Vaporesso|vaporesso.com|medium\n")
        f.write("VOOPOO|voopoo.com\n")  # No priority specified
        f.write("\n")  # Empty line
        f.write("# Comment\n")
        f.write("Invalid|")  # Invalid format
        temp_file = Path(f.name)
    
    try:
        # Load brands
        config = Config()
        logger = setup_logger('test', None, 'ERROR')
        manager = BrandManager(logger=logger)
        
        brands, errors = manager.load_brands_from_file(temp_file)
        
        tests = [
            ("Loaded 3 valid brands", len(brands) == 3),
            ("First brand name", brands[0].name == "SMOK"),
            ("First brand priority", brands[0].priority == "high"),
            ("Second brand name", brands[1].name == "Vaporesso"),
            ("Third brand default priority", brands[2].priority == "medium"),
            ("Has parsing errors", len(errors) > 0),
            ("Skipped invalid line", any("Missing website" in e or "Invalid format" in e for e in errors)),
        ]
        
        return run_tests(tests)
    
    finally:
        temp_file.unlink()


def test_brand_registry_operations():
    """Test brand registry CRUD operations"""
    print("\n" + "="*60)
    print("Test 3: Brand Registry Operations")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        registry_file = Path(temp_dir) / "test_registry.json"
        
        config = Config()
        logger = setup_logger('test', None, 'ERROR')
        manager = BrandManager(registry_file, logger)
        
        # Add brands
        brand1 = Brand("SMOK", "smoktech.com", "high")
        brand2 = Brand("Vaporesso", "vaporesso.com", "medium")
        
        manager.add_brand(brand1)
        manager.add_brand(brand2)
        
        tests = [
            ("Added 2 brands", len(manager.get_all_brands()) == 2),
            ("Get brand by name", manager.get_brand("SMOK") is not None),
            ("Get non-existent brand", manager.get_brand("NonExistent") is None),
        ]
        
        # Update brand
        brand1_update = manager.get_brand("SMOK")
        brand1_update.priority = "low"
        manager.update_brand(brand1_update)
        
        updated_brand = manager.get_brand("SMOK")
        tests.append(("Brand updated", updated_brand.priority == "low"))
        
        # Remove brand
        manager.remove_brand("Vaporesso")
        tests.append(("Brand removed", len(manager.get_all_brands()) == 1))
        tests.append(("Removed brand not found", manager.get_brand("Vaporesso") is None))
        
        # History tracking
        history = manager.get_history()
        tests.append(("Has history", len(history) > 0))
        tests.append(("Add action in history", any(h['action'] == 'add' for h in history)))
        tests.append(("Update action in history", any(h['action'] == 'update' for h in history)))
        tests.append(("Remove action in history", any(h['action'] == 'remove' for h in history)))
        
        return run_tests(tests)


def test_brand_registry_persistence():
    """Test brand registry save/load"""
    print("\n" + "="*60)
    print("Test 4: Brand Registry Persistence")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        registry_file = Path(temp_dir) / "test_registry.json"
        
        config = Config()
        logger = setup_logger('test', None, 'ERROR')
        
        # Create and save registry
        manager1 = BrandManager(registry_file, logger)
        brand1 = Brand("SMOK", "smoktech.com", "high")
        brand2 = Brand("Vaporesso", "vaporesso.com", "medium")
        manager1.add_brand(brand1)
        manager1.add_brand(brand2)
        manager1.save_registry()
        
        tests = [
            ("Registry file created", registry_file.exists()),
        ]
        
        # Load registry in new manager
        manager2 = BrandManager(registry_file, logger)
        loaded_brands = manager2.get_all_brands()
        
        tests.extend([
            ("Loaded 2 brands", len(loaded_brands) == 2),
            ("Brand 1 preserved", manager2.get_brand("SMOK") is not None),
            ("Brand 2 preserved", manager2.get_brand("Vaporesso") is not None),
            ("Priority preserved", manager2.get_brand("SMOK").priority == "high"),
        ])
        
        return run_tests(tests)


def test_priority_queue():
    """Test priority-based brand queuing"""
    print("\n" + "="*60)
    print("Test 5: Priority-Based Brand Queuing")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    manager = BrandManager(logger=logger)
    
    # Add brands with different priorities
    brands = [
        Brand("Low1", "low1.com", "low"),
        Brand("High1", "high1.com", "high"),
        Brand("Medium1", "medium1.com", "medium"),
        Brand("High2", "high2.com", "high"),
        Brand("Low2", "low2.com", "low"),
        Brand("Medium2", "medium2.com", "medium"),
    ]
    
    for brand in brands:
        manager.add_brand(brand)
    
    # Get processing queue
    queue = manager.get_processing_queue()
    
    tests = [
        ("Queue has all brands", len(queue) == 6),
        ("First brand is high priority", queue[0].priority == "high"),
        ("Last brand is low priority", queue[-1].priority == "low"),
    ]
    
    # Verify priority ordering
    high_count = 0
    medium_count = 0
    low_count = 0
    
    for brand in queue:
        if brand.priority == "high":
            high_count += 1
            # All high priority should come before medium and low
            tests.append((f"High priority {brand.name} before medium/low", 
                         medium_count == 0 and low_count == 0))
        elif brand.priority == "medium":
            medium_count += 1
            # All medium priority should come before low
            tests.append((f"Medium priority {brand.name} before low", 
                         low_count == 0))
        else:
            low_count += 1
    
    tests.extend([
        ("High priority count", high_count == 2),
        ("Medium priority count", medium_count == 2),
        ("Low priority count", low_count == 2),
    ])
    
    return run_tests(tests)


def test_url_validation():
    """Test URL format validation"""
    print("\n" + "="*60)
    print("Test 6: URL Validation")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    validator = BrandValidator(timeout=5, logger=logger)
    
    test_cases = [
        ("Valid domain", "smoktech.com", True),
        ("Valid http URL", "http://smoktech.com", True),
        ("Valid https URL", "https://smoktech.com", True),
        ("Empty URL", "", False),
        ("URL with spaces", "smoke tech.com", False),
    ]
    
    tests = []
    for test_name, url, expected_valid in test_cases:
        is_valid, error = validator.validate_url_format(url)
        tests.append((test_name, is_valid == expected_valid))
    
    return run_tests(tests)


def test_brand_validation():
    """Test brand website validation"""
    print("\n" + "="*60)
    print("Test 7: Brand Website Validation")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    validator = BrandValidator(timeout=10, logger=logger)
    
    # Test with commonly accessible domain (may fail in restricted environments)
    print("\nValidating example.com (should succeed if network available)...")
    results = validator.validate_brand("Example", "example.com")
    
    tests = []
    
    # If we can reach the domain, test positive validation
    if results['accessible']:
        tests.extend([
            ("Domain accessible", results['accessible']),
            ("Has response time", results['response_time'] is not None),
            ("Has status code", results['status_code'] is not None),
        ])
        print("  Network validation succeeded")
    else:
        # In restricted network, just verify error handling works
        tests.extend([
            ("Validation attempted", True),
            ("Error message present", results['error_message'] is not None),
        ])
        print(f"  Network restricted: {results['error_message']}")
    
    # Test with invalid domain (should always fail)
    print("\nValidating invalid domain (should fail)...")
    results_invalid = validator.validate_brand("Invalid", "this-domain-definitely-does-not-exist-12345.com")
    
    tests.extend([
        ("Invalid domain not accessible", not results_invalid['accessible']),
        ("Has error message for invalid", results_invalid['error_message'] is not None),
    ])
    
    # Test URL format validation (doesn't require network)
    is_valid, _ = validator.validate_url_format("google.com")
    tests.append(("URL format validation works", is_valid))
    
    return run_tests(tests)


def test_error_handling():
    """Test configuration error handling"""
    print("\n" + "="*60)
    print("Test 8: Error Handling")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    manager = BrandManager(logger=logger)
    
    # Test loading non-existent file
    brands, errors = manager.load_brands_from_file(Path("nonexistent_file.txt"))
    
    tests = [
        ("No brands loaded", len(brands) == 0),
        ("Has error", len(errors) > 0),
        ("File not found error", any("not found" in e.lower() for e in errors)),
    ]
    
    # Test removing non-existent brand
    result = manager.remove_brand("NonExistent")
    tests.append(("Cannot remove non-existent brand", not result))
    
    # Test updating non-existent brand
    fake_brand = Brand("NonExistent", "test.com")
    result = manager.update_brand(fake_brand)
    tests.append(("Cannot update non-existent brand", not result))
    
    # Test error summary generation
    test_errors = ["Error 1", "Error 2", "Error 3"]
    summary = manager.generate_error_summary(test_errors)
    tests.extend([
        ("Error summary generated", len(summary) > 0),
        ("Contains error count", "3 errors" in summary),
    ])
    
    return run_tests(tests)


def run_tests(tests):
    """Run a list of tests and report results"""
    passed = 0
    failed = 0
    
    for test_name, result in tests:
        if result:
            print(f"  ✓ {test_name}")
            passed += 1
        else:
            print(f"  ✗ {test_name}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests"""
    print("="*60)
    print("Brand Management Test Suite")
    print("="*60)
    
    all_passed = True
    
    try:
        all_passed &= test_brand_model()
        all_passed &= test_brand_file_parsing()
        all_passed &= test_brand_registry_operations()
        all_passed &= test_brand_registry_persistence()
        all_passed &= test_priority_queue()
        all_passed &= test_url_validation()
        all_passed &= test_brand_validation()
        all_passed &= test_error_handling()
        
        print("\n" + "="*60)
        if all_passed:
            print("✓ All tests passed!")
        else:
            print("✗ Some tests failed")
        print("="*60)
        
        return 0 if all_passed else 1
    
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
