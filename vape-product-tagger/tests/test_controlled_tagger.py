"""
Test the ControlledTagger from 1_main.py with sample products
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import *  # Import all from scripts

# Need to import directly
import importlib.util
spec = importlib.util.spec_from_file_location("main", os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "1_main.py"))
main_module = importlib.util.module_from_spec(spec)

# Mock the TagAuditDB import
class MockTagAuditDB:
    def __init__(self, *args, **kwargs): pass
    def start_run(self, *args, **kwargs): return 1
    def get_run_status(self, *args, **kwargs): return None

# Patch it
sys.modules['scripts.tag_audit_db'] = type(sys)('scripts.tag_audit_db')
sys.modules['scripts.tag_audit_db'].TagAuditDB = MockTagAuditDB

spec.loader.exec_module(main_module)
ControlledTagger = main_module.ControlledTagger


def test_controlled_tagger():
    """Test the ControlledTagger class"""
    # Create tagger with no AI
    tagger = ControlledTagger(no_ai=True, verbose=False)
    
    test_cases = [
        {
            "handle": "elf-bar-600-strawberry-ice-20mg",
            "title": "Elf Bar 600 Strawberry Ice 20mg",
            "description": "Disposable vape",
            "expected_flavors": ["fruity", "ice"],
            "expected_category": "disposable",
            "expected_nic": "20mg"
        },
        {
            "handle": "smok-rpm-2-coil-0-4ohm",
            "title": "SMOK RPM 2 Replacement Coil 0.4ohm",
            "description": "Compatible with devices",
            "expected_flavors": [],
            "expected_category": "coil",
            "expected_nic": None
        },
        {
            "handle": "vampire-vape-heisenberg-10ml",
            "title": "Vampire Vape Heisenberg 10ml 3mg",
            "description": "Premium nic salt e-liquid with blue razz",
            "expected_flavors": ["candy/sweets"],  # blue razz is candy
            "expected_category": "e-liquid",
            "expected_nic": "3mg"
        }
    ]
    
    print("=" * 60)
    print("CONTROLLED TAGGER TEST")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        # Get rule-based tags
        rule_tags, forced_category = tagger.get_rule_based_tags(
            test["handle"], 
            test["title"], 
            test["description"]
        )
        
        print(f"\nProduct: {test['title'][:40]}...")
        print(f"  Rule tags: {rule_tags}")
        print(f"  Forced category: {forced_category}")
        
        # Check category
        cat_ok = forced_category == test["expected_category"]
        if not cat_ok:
            # Check if category is in rule_tags
            cat_ok = test["expected_category"] in rule_tags
        
        # Check flavors
        flavor_ok = all(f in rule_tags for f in test["expected_flavors"])
        
        # Check nicotine
        nic_ok = True
        if test["expected_nic"]:
            nic_ok = test["expected_nic"] in rule_tags
        
        all_ok = cat_ok and flavor_ok and nic_ok
        
        if all_ok:
            passed += 1
            print(f"  ✓ PASS")
        else:
            failed += 1
            print(f"  ✗ FAIL")
            if not cat_ok:
                print(f"    Category: expected {test['expected_category']}, got {forced_category}")
            if not flavor_ok:
                print(f"    Flavors: expected {test['expected_flavors']} in {rule_tags}")
            if not nic_ok:
                print(f"    Nicotine: expected {test['expected_nic']} in {rule_tags}")
    
    print(f"\n{'=' * 60}")
    print(f"RESULT: {passed}/{passed + failed}")
    
    return failed == 0


if __name__ == "__main__":
    test_controlled_tagger()
