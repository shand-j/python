#!/usr/bin/env python3
"""
Integration Tests for Refactored Vape Product Tagger
Tests the complete pipeline with AI cascade, validation, and recovery
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.config import Config
from modules.logger import setup_logger
from modules.product_tagger import ProductTagger
from modules.tag_validator import TagValidator
from modules.ai_cascade import AICascade
from modules.third_opinion import ThirdOpinionRecovery


class TestRefactoredTagger:
    """Test suite for refactored tagger system"""
    
    def __init__(self):
        """Initialize test environment"""
        self.config = Config()
        self.logger = setup_logger(self.config)
        self.tagger = ProductTagger(self.config, self.logger, ollama_processor=None)
        self.validator = TagValidator(logger=self.logger)
        
        self.passed = 0
        self.failed = 0
        self.test_results = []
    
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result_str = f"{status}: {test_name}"
        if message:
            result_str += f" - {message}"
        
        print(result_str)
        self.test_results.append((test_name, passed, message))
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def test_e_liquid_with_secondary_flavors(self):
        """Test: E-liquid with secondary flavors ('Strawberry Banana Ice 50ml 0mg 70/30')"""
        product = {
            'title': 'Strawberry Banana Ice 50ml',
            'description': 'Delicious strawberry and banana flavored e-liquid with cooling ice. 0mg nicotine. 70VG/30PG ratio. 50ml shortfill bottle.',
            'handle': 'strawberry-banana-ice-50ml'
        }
        
        # Tag without AI
        result = self.tagger.tag_product(product, use_ai=False)
        
        category = result.get('category', '')
        tags = result.get('tags', [])
        tag_breakdown = result.get('tag_breakdown', {})
        secondary_flavors = tag_breakdown.get('secondary_flavors', [])
        
        # Assertions
        checks = []
        checks.append(('Category is e-liquid', category == 'e-liquid'))
        checks.append(('Has 0mg nicotine tag', '0mg' in tags))
        checks.append(('Has 50ml bottle size', '50ml' in tags))
        checks.append(('Has VG/PG ratio 70/30', '70/30' in tags))
        checks.append(('Has fruity flavor', 'fruity' in tags))
        checks.append(('Has ice flavor', 'ice' in tags))
        checks.append(('Has secondary flavors', len(secondary_flavors) > 0))
        checks.append(('Strawberry in secondary', 'strawberry' in [f.lower() for f in secondary_flavors]))
        checks.append(('Banana in secondary', 'banana' in [f.lower() for f in secondary_flavors]))
        
        all_passed = all(check[1] for check in checks)
        details = ', '.join([f"{check[0]}: {check[1]}" for check in checks])
        
        self.log_result('E-liquid with secondary flavors', all_passed, details)
        return all_passed
    
    def test_cbd_three_dimension_validation(self):
        """Test: CBD 3-dimension validation ('1000mg Full Spectrum CBD Gummies')"""
        product = {
            'title': '1000mg Full Spectrum CBD Gummies',
            'description': 'Premium full spectrum CBD gummies. 1000mg total CBD. Made with organic ingredients.',
            'handle': 'cbd-gummies-1000mg'
        }
        
        # Tag without AI
        result = self.tagger.tag_product(product, use_ai=False)
        
        category = result.get('category', '')
        tags = result.get('tags', [])
        
        # Check for 3 CBD dimensions
        has_strength = any('mg' in tag for tag in tags)
        has_form = any(tag in ['gummy', 'tincture', 'oil', 'capsule', 'topical', 'patch', 'paste', 'shot', 'isolate', 'edible', 'beverage'] for tag in tags)
        has_type = any(tag in ['full_spectrum', 'broad_spectrum', 'isolate', 'cbg', 'cbda'] for tag in tags)
        
        # Validate
        is_valid, failures = self.validator.validate_all_tags(tags, category)
        
        checks = []
        checks.append(('Category is CBD', category == 'CBD'))
        checks.append(('Has CBD strength', has_strength))
        checks.append(('Has CBD form', has_form))
        checks.append(('Has CBD type', has_type))
        checks.append(('Passes validation', is_valid))
        
        all_passed = all(check[1] for check in checks)
        details = ', '.join([f"{check[0]}: {check[1]}" for check in checks])
        if failures:
            details += f" | Failures: {failures}"
        
        self.log_result('CBD 3-dimension validation', all_passed, details)
        return all_passed
    
    def test_illegal_nicotine_rejection(self):
        """Test: Illegal nicotine rejection (25mg should be rejected)"""
        product = {
            'title': 'Extra Strong E-liquid 25mg',
            'description': '25mg nicotine e-liquid. Very strong.',
            'handle': 'extra-strong-25mg'
        }
        
        # Tag without AI
        result = self.tagger.tag_product(product, use_ai=False)
        
        category = result.get('category', '')
        tags = result.get('tags', [])
        
        # Should NOT have 25mg tag (illegal)
        has_25mg = '25mg' in tags
        has_illegal_warning = any('illegal' in str(reason).lower() for reason in result.get('failure_reasons', []))
        
        # Should have 0mg as fallback
        has_0mg = '0mg' in tags
        
        checks = []
        checks.append(('Category detected', category in ['e-liquid', 'disposable']))
        checks.append(('No 25mg tag (illegal)', not has_25mg))
        checks.append(('Has 0mg fallback', has_0mg))
        
        all_passed = all(check[1] for check in checks)
        details = ', '.join([f"{check[0]}: {check[1]}" for check in checks])
        
        self.log_result('Illegal nicotine rejection (25mg)', all_passed, details)
        return all_passed
    
    def test_category_detection_failures(self):
        """Test: Category detection handles unclear products"""
        product = {
            'title': 'Mystery Product XYZ',
            'description': 'A product with no clear category indicators.',
            'handle': 'mystery-product'
        }
        
        # Tag without AI
        result = self.tagger.tag_product(product, use_ai=False)
        
        category = result.get('category', '')
        tags = result.get('tags', [])
        
        # Should have minimal or no tags
        checks = []
        checks.append(('Empty or undetected category', category == '' or category is None))
        checks.append(('Few or no tags', len(tags) <= 2))
        
        all_passed = all(check[1] for check in checks)
        details = f"Category: '{category}', Tags: {len(tags)}"
        
        self.log_result('Category detection failure handling', all_passed, details)
        return all_passed
    
    def test_vg_pg_ratio_parsing(self):
        """Test: VG/PG ratio parsing ('70VG/30PG' vs '70/30')"""
        test_cases = [
            ('70VG/30PG', '70/30'),
            ('70/30', '70/30'),
            ('50/50', '50/50'),
            ('80VG 20PG', '80/20'),
        ]
        
        all_passed = True
        for input_text, expected in test_cases:
            product = {
                'title': f'E-liquid {input_text}',
                'description': f'VG/PG ratio: {input_text}',
                'handle': 'test-eliquid'
            }
            
            result = self.tagger.tag_product(product, use_ai=False)
            category = result.get('category', '')
            tags = result.get('tags', [])
            
            has_ratio = expected in tags
            if not has_ratio:
                all_passed = False
                print(f"  ⚠️  Failed to parse '{input_text}' as '{expected}'. Got: {tags}")
        
        self.log_result('VG/PG ratio parsing variations', all_passed, 
                       f"Tested {len(test_cases)} variations")
        return all_passed
    
    def test_tag_validator_functionality(self):
        """Test: TagValidator validates tags correctly"""
        schema = self.validator.get_approved_schema()
        
        # Test valid tags
        valid_tests = [
            ('0mg', 'e-liquid', True),
            ('fruity', 'e-liquid', True),
            ('50ml', 'e-liquid', True),
            ('rechargeable', 'device', True),
            ('gummy', 'CBD', True),
        ]
        
        # Test invalid tags
        invalid_tests = [
            ('50ml', 'device', False),  # bottle_size doesn't apply to device
            ('fruity', 'tank', False),  # flavor doesn't apply to tank
            ('rechargeable', 'e-liquid', False),  # power_supply doesn't apply to e-liquid
        ]
        
        all_passed = True
        for tag, category, should_be_valid in valid_tests + invalid_tests:
            is_valid, reason = self.validator.validate_tag(tag, category)
            if is_valid != should_be_valid:
                all_passed = False
                print(f"  ⚠️  Tag '{tag}' for category '{category}': expected {should_be_valid}, got {is_valid}")
        
        self.log_result('TagValidator applies_to rules', all_passed,
                       f"Tested {len(valid_tests + invalid_tests)} cases")
        return all_passed
    
    def test_manual_review_flagging(self):
        """Test: Products are correctly flagged for manual review"""
        # Product with clear validation failures should be flagged
        product = {
            'title': 'CBD Product Missing Info',
            'description': 'CBD product but missing strength and form information',
            'handle': 'cbd-missing-info'
        }
        
        result = self.tagger.tag_product(product, use_ai=False)
        
        category = result.get('category', '')
        needs_review = result.get('needs_manual_review', False)
        failure_reasons = result.get('failure_reasons', [])
        
        checks = []
        checks.append(('Category is CBD', category == 'CBD'))
        checks.append(('Flagged for review', needs_review or len(failure_reasons) > 0))
        
        all_passed = all(check[1] for check in checks)
        details = f"Needs review: {needs_review}, Failures: {len(failure_reasons)}"
        
        self.log_result('Manual review flagging', all_passed, details)
        return all_passed
    
    def test_device_style_tagging(self):
        """Test: Device style tagging with applies_to rules"""
        product = {
            'title': 'Compact Pod System Device',
            'description': 'Compact pod-style vaping device with rechargeable battery. MTL vaping style.',
            'handle': 'compact-pod-device'
        }
        
        result = self.tagger.tag_product(product, use_ai=False)
        
        category = result.get('category', '')
        tags = result.get('tags', [])
        
        checks = []
        checks.append(('Category is device or pod_system', category in ['device', 'pod_system']))
        checks.append(('Has device style tag', any(tag in ['compact', 'pod_style', 'pen_style'] for tag in tags)))
        checks.append(('Has power supply', 'rechargeable' in tags))
        checks.append(('Has vaping style', 'mouth-to-lung' in tags))
        
        all_passed = all(check[1] for check in checks)
        details = ', '.join([f"{check[0]}: {check[1]}" for check in checks])
        
        self.log_result('Device style tagging with applies_to', all_passed, details)
        return all_passed
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*70)
        print("🧪 Refactored Vape Product Tagger Integration Tests")
        print("="*70 + "\n")
        
        # Run tests
        tests = [
            self.test_e_liquid_with_secondary_flavors,
            self.test_cbd_three_dimension_validation,
            self.test_illegal_nicotine_rejection,
            self.test_category_detection_failures,
            self.test_vg_pg_ratio_parsing,
            self.test_tag_validator_functionality,
            self.test_manual_review_flagging,
            self.test_device_style_tagging,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_result(test.__name__, False, f"Exception: {str(e)}")
        
        # Summary
        print("\n" + "="*70)
        print(f"📊 Test Summary: {self.passed} passed, {self.failed} failed")
        print("="*70 + "\n")
        
        if self.failed > 0:
            print("❌ Some tests failed. Review the output above for details.\n")
            return False
        else:
            print("✅ All tests passed!\n")
            return True


if __name__ == '__main__':
    tester = TestRefactoredTagger()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
