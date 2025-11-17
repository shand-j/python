#!/usr/bin/env python3
"""
Brand Management Demo
Demonstrates the brand discovery and configuration feature
"""
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import (
    Brand, BrandManager, BrandValidator,
    Config, setup_logger
)


def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def demo_scenario_1():
    """Scenario 1: Basic Brand List Input"""
    print_header("Scenario 1: Basic Brand List Input")
    
    # Create temporary brands file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("# Test brands\n")
        f.write("SMOK|smoktech.com|high\n")
        f.write("Vaporesso|vaporesso.com|high\n")
        f.write("VOOPOO|voopoo.com|medium\n")
        brands_file = Path(f.name)
    
    try:
        # Initialize
        config = Config()
        logger = setup_logger('Demo', None, 'INFO')
        manager = BrandManager(logger=logger)
        
        print("\n1. Loading brands from file...")
        brands, errors = manager.load_brands_from_file(brands_file)
        
        print(f"   ✓ Loaded {len(brands)} brands")
        
        print("\n2. Storing in registry...")
        for brand in brands:
            manager.add_brand(brand)
        
        print(f"   ✓ Stored {len(manager.get_all_brands())} brands")
        
        print("\n3. Validation results:")
        for brand in manager.get_all_brands():
            print(f"   - {brand.name}: Status={brand.status}, Priority={brand.priority}")
        
        return True
    
    finally:
        brands_file.unlink()


def demo_scenario_2():
    """Scenario 2: Brand Website Validation"""
    print_header("Scenario 2: Brand Website Validation")
    
    config = Config()
    logger = setup_logger('Demo', None, 'INFO')
    validator = BrandValidator(timeout=10, logger=logger)
    
    print("\n1. Creating test brand...")
    brand = Brand("TestBrand", "example.com", "high")
    print(f"   ✓ Brand: {brand.name} ({brand.website})")
    
    print("\n2. Validating brand website...")
    print("   (Network may be restricted in sandbox environment)")
    results = validator.validate_brand(brand.name, brand.website)
    
    print(f"\n3. Validation Results:")
    print(f"   - Accessible: {results['accessible']}")
    print(f"   - SSL Valid: {results['ssl_valid']}")
    print(f"   - Response Time: {results['response_time']}")
    print(f"   - Status Code: {results['status_code']}")
    
    if results['error_message']:
        print(f"   - Error: {results['error_message']}")
    
    return True


def demo_scenario_3():
    """Scenario 3: Priority-Based Brand Queuing"""
    print_header("Scenario 3: Priority-Based Brand Queuing")
    
    config = Config()
    logger = setup_logger('Demo', None, 'INFO')
    manager = BrandManager(logger=logger)
    
    print("\n1. Adding brands with different priorities...")
    brands = [
        Brand("SMOK", "smoktech.com", "high"),
        Brand("VOOPOO", "voopoo.com", "medium"),
        Brand("Lost Vape", "lostvape.com", "low"),
        Brand("Vaporesso", "vaporesso.com", "high"),
        Brand("GeekVape", "geekvape.com", "medium"),
    ]
    
    for brand in brands:
        manager.add_brand(brand)
        print(f"   + {brand.name} (priority: {brand.priority})")
    
    print("\n2. Generating processing queue...")
    queue = manager.get_processing_queue()
    
    print(f"\n3. Processing Queue ({len(queue)} brands):")
    current_priority = None
    for i, brand in enumerate(queue, 1):
        if brand.priority != current_priority:
            current_priority = brand.priority
            print(f"\n   {current_priority.upper()} Priority:")
        print(f"   {i}. {brand.name} - {brand.website}")
    
    return True


def demo_scenario_4():
    """Scenario 4: Brand Registry Management"""
    print_header("Scenario 4: Brand Registry Management")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        registry_file = Path(temp_dir) / "test_registry.json"
        
        config = Config()
        logger = setup_logger('Demo', None, 'INFO')
        manager = BrandManager(registry_file, logger=logger)
        
        print("\n1. Adding new brands...")
        brand1 = Brand("SMOK", "smoktech.com", "high")
        brand2 = Brand("Vaporesso", "vaporesso.com", "medium")
        manager.add_brand(brand1)
        manager.add_brand(brand2)
        print(f"   ✓ Added 2 brands")
        
        print("\n2. Updating existing brand...")
        brand1_update = manager.get_brand("SMOK")
        brand1_update.priority = "low"
        manager.update_brand(brand1_update)
        print(f"   ✓ Updated SMOK priority to low")
        
        print("\n3. Removing inactive brand...")
        manager.remove_brand("Vaporesso")
        print(f"   ✓ Removed Vaporesso")
        
        print("\n4. Viewing registry history...")
        history = manager.get_history()
        print(f"   Registry has {len(history)} history entries:")
        for entry in history:
            print(f"   - {entry['action']}: {entry['brand']}")
        
        print("\n5. Saving registry...")
        manager.save_registry()
        print(f"   ✓ Saved to {registry_file}")
        
        print("\n6. Loading registry in new instance...")
        manager2 = BrandManager(registry_file, logger=logger)
        print(f"   ✓ Loaded {len(manager2.get_all_brands())} brands")
        
        return True


def demo_scenario_5():
    """Scenario 5: Configuration Error Handling"""
    print_header("Scenario 5: Configuration Error Handling")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("# Test brands with errors\n")
        f.write("BadBrand|invalid url with spaces\n")
        f.write("TestBrand|testbrand.com|high\n")
        f.write("InvalidFormat\n")
        f.write("GoodBrand|goodbrand.com|medium\n")
        brands_file = Path(f.name)
    
    try:
        config = Config()
        logger = setup_logger('Demo', None, 'INFO')
        manager = BrandManager(logger=logger)
        
        print("\n1. Processing configuration with errors...")
        brands, errors = manager.load_brands_from_file(brands_file)
        
        print(f"\n2. Results:")
        print(f"   - Valid brands: {len(brands)}")
        print(f"   - Errors: {len(errors)}")
        
        print("\n3. Valid brands processed:")
        for brand in brands:
            manager.add_brand(brand)
            print(f"   ✓ {brand.name}")
        
        print("\n4. Error summary:")
        if errors:
            for error in errors:
                print(f"   ✗ {error}")
        
        print("\n5. Generating error report...")
        summary = manager.generate_error_summary(errors)
        print(summary)
        
        return True
    
    finally:
        brands_file.unlink()


def main():
    """Run all demo scenarios"""
    print("="*70)
    print("  Brand Management Feature Demo")
    print("  Demonstrating Brand Discovery and Configuration")
    print("="*70)
    
    scenarios = [
        demo_scenario_1,
        demo_scenario_2,
        demo_scenario_3,
        demo_scenario_4,
        demo_scenario_5,
    ]
    
    passed = 0
    failed = 0
    
    for scenario in scenarios:
        try:
            if scenario():
                passed += 1
                print("\n✓ Scenario completed successfully")
            else:
                failed += 1
                print("\n✗ Scenario failed")
        except Exception as e:
            failed += 1
            print(f"\n✗ Scenario failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print(f"  Demo Results: {passed} passed, {failed} failed")
    print("="*70)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
