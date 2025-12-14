"""
Test tagging with real product data samples to identify quality issues.
"""

import sys
import os
import csv
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
    enable_compliance_tags = False
    enable_ai_tagging = False


class MockLogger:
    """Mock logger for testing"""
    def debug(self, msg, *args): pass
    def info(self, msg, *args): pass
    def warning(self, msg, *args): pass
    def error(self, msg, *args): pass


def test_real_products():
    """Test tagging with real product data"""
    config = MockConfig()
    logger = MockLogger()
    tagger = ProductTagger(config, logger)
    
    # Real product samples from the shop
    products = [
        {
            "handle": "realest-cbd-3000mg-cbg-isolate-buy-1-get-1-free",
            "title": "Realest CBD 3000mg CBG Isolate (BUY 1 GET 1 FREE)",
            "description": "99%+ pure CBG isolate from Realest CBD",
            "type": "CBD Products",
            "expected_category": "CBD",
            "expected_tags": ["isolate", "3000mg", "cbg"]
        },
        {
            "handle": "cbdna-1000mg-full-spectrum-cbd-oil-10ml",
            "title": "cbDNA 1000mg Full Spectrum CBD Oil - 10ml",
            "description": "Full Spectrum CBD Oil brings a unique terpene structure",
            "type": "CBD Products",
            "expected_category": "CBD",
            "expected_tags": ["full_spectrum", "1000mg", "oil"]  # oil is the primary form
        },
        {
            "handle": "elf-bar-600-strawberry-ice-20mg",
            "title": "Elf Bar 600 Strawberry Ice 20mg",
            "description": "Disposable vape with 600 puffs",
            "type": "",
            "expected_category": "disposable",
            "expected_tags": ["20mg", "fruity", "ice"]
        },
        {
            "handle": "vampire-vape-heisenberg-10ml",
            "title": "Vampire Vape Heisenberg 10ml Nic Salt",
            "description": "Premium nic salt e-liquid",
            "type": "",
            "expected_category": "e-liquid",
            "expected_tags": ["10ml", "nic_salt"]
        },
        {
            "handle": "smok-rpm-2-replacement-coil-0-4ohm",
            "title": "SMOK RPM 2 Replacement Coil 0.4ohm 5 Pack",
            "description": "Compatible with RPM 2 devices",
            "type": "",
            "expected_category": "coil",
            "expected_tags": ["0.4ohm"]
        },
        {
            "handle": "vaporesso-xros-3-replacement-pod",
            "title": "Vaporesso XROS 3 Replacement Pod 2ml",
            "description": "Refillable pod for XROS 3",
            "type": "",
            "expected_category": "pod",
            "expected_tags": ["replacement_pod", "2ml"]
        },
        {
            "handle": "pablo-nicotine-pouches-mint-20mg",
            "title": "Pablo Nicotine Pouches Mint 20mg",
            "description": "Strong nicotine pouches with mint flavor",
            "type": "",
            "expected_category": "nicotine_pouches",
            "expected_tags": ["20mg", "ice"]  # mint should be ice
        },
        {
            "handle": "18650-battery-samsung-3000mah",
            "title": "Samsung 18650 Battery 3000mAh 30A",
            "description": "High drain rechargeable battery",
            "type": "",
            "expected_category": "accessory",
            "expected_tags": ["battery"]
        },
    ]
    
    print("=" * 70)
    print("REAL PRODUCT TAGGING TEST")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for product in products:
        product_data = {
            "handle": product["handle"],
            "title": product["title"],
            "description": product["description"],
            "type": product.get("type", "")
        }
        
        # Test category detection
        category = tagger.tag_category(product_data)
        category_ok = category == product["expected_category"]
        
        # Collect all tags based on detected category
        all_tags = []
        
        if category == "CBD":
            cbd_strength = tagger.tag_cbd_strength(product_data, category)
            if cbd_strength:
                all_tags.append(cbd_strength)
            all_tags.extend(tagger.tag_cbd_form(product_data, category))
            all_tags.extend(tagger.tag_cbd_type(product_data, category))
        elif category == "e-liquid":
            nic_strength = tagger.tag_nicotine_strength(product_data, category)
            if nic_strength:
                all_tags.append(nic_strength)
            all_tags.extend(tagger.tag_nicotine_type(product_data, category))
            all_tags.extend(tagger.tag_bottle_size(product_data, category))
            vg_ratio = tagger.tag_vg_ratio(product_data, category)
            if vg_ratio:
                all_tags.append(vg_ratio)
            primary_flavors, _ = tagger.tag_flavors(product_data, category)
            all_tags.extend(primary_flavors)
        elif category == "disposable":
            nic_strength = tagger.tag_nicotine_strength(product_data, category)
            if nic_strength:
                all_tags.append(nic_strength)
            primary_flavors, _ = tagger.tag_flavors(product_data, category)
            all_tags.extend(primary_flavors)
        elif category == "coil":
            all_tags.extend(tagger.tag_coil_ohm(product_data, category))
        elif category == "pod":
            all_tags.extend(tagger.tag_capacity(product_data, category))
            all_tags.extend(tagger.tag_pod_type(product_data, category))
        elif category == "nicotine_pouches":
            nic_strength = tagger.tag_nicotine_strength(product_data, category)
            if nic_strength:
                all_tags.append(nic_strength)
            primary_flavors, _ = tagger.tag_flavors(product_data, category)
            all_tags.extend(primary_flavors)
        elif category == "accessory":
            # Check for specific accessory types
            text = f"{product_data['title']} {product_data['description']}".lower()
            if "battery" in text:
                all_tags.append("battery")
            if "charger" in text:
                all_tags.append("charger")
        
        # Check if expected tags are present
        missing_tags = []
        for expected in product["expected_tags"]:
            if expected not in all_tags:
                missing_tags.append(expected)
        
        tags_ok = len(missing_tags) == 0
        overall_ok = category_ok and tags_ok
        
        status = "✓" if overall_ok else "✗"
        
        if overall_ok:
            passed += 1
            print(f"{status} PASS: {product['title'][:50]}...")
        else:
            failed += 1
            print(f"{status} FAIL: {product['title'][:50]}...")
            if not category_ok:
                print(f"    Category - Expected: {product['expected_category']}, Got: {category}")
            if not tags_ok:
                print(f"    Missing tags: {missing_tags}")
                print(f"    Got tags: {all_tags}")
    
    print("\n" + "=" * 70)
    total = passed + failed
    pct = (passed / total * 100) if total > 0 else 0
    print(f"RESULT: {passed}/{total} ({pct:.0f}%)")
    
    return failed == 0


if __name__ == "__main__":
    success = test_real_products()
    sys.exit(0 if success else 1)
