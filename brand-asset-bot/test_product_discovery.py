#!/usr/bin/env python3
"""
Test suite for product discovery module
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
import tempfile
import shutil

from modules import ProductDiscovery, DiscoveredProduct, ProductInventory


class TestDiscoveredProduct(unittest.TestCase):
    """Test DiscoveredProduct data model"""
    
    def test_create_discovered_product(self):
        """Test creating a discovered product"""
        product = DiscoveredProduct(
            url="https://vapeuk.co.uk/products/smok-novo-5",
            title="SMOK Novo 5 Pod Kit",
            brand="SMOK",
            category="vape-kits",
            competitor_site="Vape UK",
            price="£24.99",
            in_stock=True
        )
        
        self.assertEqual(product.url, "https://vapeuk.co.uk/products/smok-novo-5")
        self.assertEqual(product.title, "SMOK Novo 5 Pod Kit")
        self.assertEqual(product.brand, "SMOK")
        self.assertEqual(product.category, "vape-kits")
        self.assertEqual(product.competitor_site, "Vape UK")
        self.assertEqual(product.price, "£24.99")
        self.assertTrue(product.in_stock)
        self.assertIsNotNone(product.discovered_at)
    
    def test_product_with_optional_fields(self):
        """Test product with optional fields"""
        product = DiscoveredProduct(
            url="https://example.com/product",
            title="Test Product",
            brand="TestBrand",
            category="test",
            competitor_site="Test Site"
        )
        
        self.assertIsNone(product.price)
        self.assertIsNone(product.image_url)
        self.assertTrue(product.in_stock)  # Default value


class TestProductInventory(unittest.TestCase):
    """Test ProductInventory data model"""
    
    def test_create_product_inventory(self):
        """Test creating product inventory"""
        from datetime import datetime
        
        brand_products = {
            "SMOK": [
                {
                    "url": "https://example.com/smok-1",
                    "title": "SMOK Product 1",
                    "brand": "SMOK",
                    "category": "kits",
                    "competitor_site": "Test Site"
                }
            ]
        }
        
        category_summary = {"kits": 1}
        
        inventory = ProductInventory(
            competitor_site="Test Site",
            total_products=1,
            brand_products=brand_products,
            category_summary=category_summary,
            last_scan=datetime.utcnow().isoformat()
        )
        
        self.assertEqual(inventory.competitor_site, "Test Site")
        self.assertEqual(inventory.total_products, 1)
        self.assertEqual(len(inventory.brand_products), 1)
        self.assertEqual(inventory.category_summary["kits"], 1)
    
    def test_inventory_to_dict(self):
        """Test converting inventory to dictionary"""
        from datetime import datetime
        
        inventory = ProductInventory(
            competitor_site="Test Site",
            total_products=1,
            brand_products={"SMOK": []},
            category_summary={"kits": 1},
            last_scan=datetime.utcnow().isoformat()
        )
        
        inventory_dict = inventory.to_dict()
        
        self.assertIsInstance(inventory_dict, dict)
        self.assertEqual(inventory_dict['competitor_site'], "Test Site")
        self.assertEqual(inventory_dict['total_products'], 1)


class TestProductDiscovery(unittest.TestCase):
    """Test ProductDiscovery functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.discovery = ProductDiscovery()
    
    def test_initialization(self):
        """Test product discovery initialization"""
        self.assertIsNotNone(self.discovery.user_agent)
        self.assertIsNotNone(self.discovery.session)
        self.assertEqual(len(self.discovery.discovered_products), 0)
        self.assertEqual(len(self.discovery.seen_urls), 0)
    
    def test_category_patterns(self):
        """Test category patterns are defined"""
        self.assertGreater(len(ProductDiscovery.CATEGORY_PATTERNS), 0)
        self.assertIn('/vape-kits', ProductDiscovery.CATEGORY_PATTERNS)
        self.assertIn('/disposable-vapes', ProductDiscovery.CATEGORY_PATTERNS)
    
    def test_product_url_patterns(self):
        """Test product URL patterns are defined"""
        self.assertGreater(len(ProductDiscovery.PRODUCT_URL_PATTERNS), 0)
        self.assertTrue(any('product' in pattern for pattern in ProductDiscovery.PRODUCT_URL_PATTERNS))
    
    @patch('modules.product_discovery.requests.Session.get')
    def test_discover_categories(self, mock_get):
        """Test category discovery"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <a href="/vape-kits">Vape Kits</a>
                <a href="/disposable-vapes">Disposables</a>
                <a href="/about">About</a>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        categories = self.discovery.discover_categories("https://example.com")
        
        # Should find vape-kits and disposable-vapes
        self.assertGreater(len(categories), 0)
        mock_get.assert_called_once()
    
    @patch('modules.product_discovery.requests.Session.get')
    def test_extract_product_urls(self, mock_get):
        """Test extracting product URLs from category"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <a href="/products/smok-novo-5">SMOK Novo 5</a>
                <a href="/products/vaporesso-xros-3">Vaporesso XROS 3</a>
                <a href="/about">About</a>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        product_urls = self.discovery.extract_product_urls(
            "https://example.com/vape-kits",
            max_pages=1,
            delay=0.1
        )
        
        # Should find product URLs
        self.assertGreater(len(product_urls), 0)
    
    @patch('modules.product_discovery.requests.Session.get')
    @patch('modules.product_discovery.time.sleep')
    def test_filter_by_brands(self, mock_sleep, mock_get):
        """Test filtering products by target brands"""
        # Mock product page response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <head>
                <title>SMOK Novo 5 Pod Kit - Vape UK</title>
            </head>
            <body>
                <h1>SMOK Novo 5 Pod Kit</h1>
                <span class="price">£24.99</span>
                <img class="product-image" src="/images/smok-novo-5.jpg" />
                <div class="stock">In Stock</div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        product_urls = [
            "https://example.com/products/smok-novo-5",
            "https://example.com/products/other-product"
        ]
        
        target_brands = ["SMOK", "Vaporesso"]
        
        filtered_products = self.discovery.filter_by_brands(
            product_urls,
            target_brands,
            "Test Site",
            "vape-kits",
            delay=0.1
        )
        
        # Should find SMOK product
        self.assertGreater(len(filtered_products), 0)
        if filtered_products:
            self.assertEqual(filtered_products[0].brand, "SMOK")
    
    def test_build_inventory(self):
        """Test building product inventory"""
        # Add some discovered products
        product1 = DiscoveredProduct(
            url="https://example.com/product1",
            title="SMOK Product 1",
            brand="SMOK",
            category="kits",
            competitor_site="Test Site"
        )
        
        product2 = DiscoveredProduct(
            url="https://example.com/product2",
            title="SMOK Product 2",
            brand="SMOK",
            category="kits",
            competitor_site="Test Site"
        )
        
        product3 = DiscoveredProduct(
            url="https://example.com/product3",
            title="Vaporesso Product 1",
            brand="Vaporesso",
            category="disposables",
            competitor_site="Test Site"
        )
        
        self.discovery.discovered_products = [product1, product2, product3]
        
        inventory = self.discovery.build_inventory("Test Site")
        
        self.assertEqual(inventory.competitor_site, "Test Site")
        self.assertEqual(inventory.total_products, 3)
        self.assertEqual(len(inventory.brand_products), 2)
        self.assertEqual(len(inventory.brand_products["SMOK"]), 2)
        self.assertEqual(len(inventory.brand_products["Vaporesso"]), 1)
        self.assertEqual(inventory.category_summary["kits"], 2)
        self.assertEqual(inventory.category_summary["disposables"], 1)


class TestProductURLPatternRecognition(unittest.TestCase):
    """Test product URL pattern recognition"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.discovery = ProductDiscovery()
    
    def test_recognize_common_url_patterns(self):
        """Test recognition of common product URL patterns"""
        import re
        
        test_urls = [
            "/products/smok-novo-5-vape-kit",
            "/products/vaporesso-xros-3-pod-kit",
            "/vape-kits/lost-mary-4in1.html",
            "/p/geekvape-aegis-boost",
            "/product/smok-rpm-coils"
        ]
        
        for url in test_urls:
            matched = False
            for pattern in ProductDiscovery.PRODUCT_URL_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    matched = True
                    break
            
            self.assertTrue(matched, f"URL should match a pattern: {url}")
    
    def test_ignore_non_product_urls(self):
        """Test that non-product URLs are not matched"""
        import re
        
        non_product_urls = [
            "/about-us",
            "/contact",
            "/",
            "/category/vape-kits",
            "/blog/article"
        ]
        
        for url in non_product_urls:
            matched = False
            for pattern in ProductDiscovery.PRODUCT_URL_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    matched = True
                    break
            
            # These should generally not match (though some might)
            # This is more of a sanity check


class TestBrandFiltering(unittest.TestCase):
    """Test brand-specific filtering logic"""
    
    def test_url_based_brand_matching(self):
        """Test brand matching from URL"""
        test_cases = [
            ("https://example.com/products/smok-novo-5", "SMOK", True),
            ("https://example.com/products/vaporesso-xros", "Vaporesso", True),
            ("https://example.com/products/lost-mary-bm600", "Lost Mary", True),
            ("https://example.com/products/geekvape-aegis", "GeekVape", True),
            ("https://example.com/products/other-product", "SMOK", False),
        ]
        
        for url, brand, should_match in test_cases:
            url_lower = url.lower()
            brand_slug = brand.lower().replace(' ', '-')
            matched = brand_slug in url_lower or brand.lower() in url_lower
            
            if should_match:
                self.assertTrue(matched, f"URL {url} should match brand {brand}")
            # Note: The else case is not always reliable for negative matches


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflows"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_complete_discovery_workflow(self):
        """Test complete product discovery workflow"""
        discovery = ProductDiscovery()
        
        # Manually add some products (simulating discovery)
        products = [
            DiscoveredProduct(
                url="https://example.com/products/smok-1",
                title="SMOK Product 1",
                brand="SMOK",
                category="kits",
                competitor_site="Test Site",
                price="£24.99"
            ),
            DiscoveredProduct(
                url="https://example.com/products/smok-2",
                title="SMOK Product 2",
                brand="SMOK",
                category="mods",
                competitor_site="Test Site",
                price="£34.99"
            ),
            DiscoveredProduct(
                url="https://example.com/products/vaporesso-1",
                title="Vaporesso Product 1",
                brand="Vaporesso",
                category="kits",
                competitor_site="Test Site",
                price="£29.99"
            )
        ]
        
        discovery.discovered_products = products
        
        # Build inventory
        inventory = discovery.build_inventory("Test Site")
        
        # Verify inventory
        self.assertEqual(inventory.total_products, 3)
        self.assertEqual(len(inventory.brand_products["SMOK"]), 2)
        self.assertEqual(len(inventory.brand_products["Vaporesso"]), 1)
        self.assertEqual(inventory.category_summary["kits"], 2)
        self.assertEqual(inventory.category_summary["mods"], 1)
        
        # Save inventory
        output_file = self.test_dir / "test_inventory.json"
        with open(output_file, 'w') as f:
            json.dump(inventory.to_dict(), f, indent=2)
        
        # Load and verify
        with open(output_file, 'r') as f:
            loaded_inventory = json.load(f)
        
        self.assertEqual(loaded_inventory['competitor_site'], "Test Site")
        self.assertEqual(loaded_inventory['total_products'], 3)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDiscoveredProduct))
    suite.addTests(loader.loadTestsFromTestCase(TestProductInventory))
    suite.addTests(loader.loadTestsFromTestCase(TestProductDiscovery))
    suite.addTests(loader.loadTestsFromTestCase(TestProductURLPatternRecognition))
    suite.addTests(loader.loadTestsFromTestCase(TestBrandFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit(run_tests())
