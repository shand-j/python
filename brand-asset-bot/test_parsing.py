#!/usr/bin/env python3
"""
Test Script - Web Scraper HTML Parsing
Tests the HTML parsing capabilities with sample HTML
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import Config, setup_logger, WebScraper
from bs4 import BeautifulSoup


def test_html_parsing():
    """Test HTML parsing with sample product page HTML"""
    
    # Sample HTML that mimics a product page
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Premium Leather Wallet - Shop Now</title>
        <meta name="description" content="High-quality leather wallet with multiple card slots">
        <meta name="keywords" content="wallet, leather, premium, accessories">
        <meta property="og:title" content="Premium Leather Wallet">
        <meta property="og:description" content="Handcrafted leather wallet">
        <meta property="og:image" content="https://example.com/images/wallet.jpg">
        <script type="application/ld+json">
        {
            "@type": "Product",
            "name": "Premium Leather Wallet",
            "description": "Handcrafted from genuine leather",
            "offers": {
                "price": "49.99",
                "priceCurrency": "USD"
            }
        }
        </script>
    </head>
    <body>
        <nav class="breadcrumb">
            <a href="/">Home</a>
            <span>/</span>
            <a href="/accessories">Accessories</a>
            <span>/</span>
            <a href="/wallets">Wallets</a>
        </nav>
        
        <div class="product">
            <h1>Premium Leather Wallet</h1>
            
            <div class="product-images">
                <img src="https://example.com/images/wallet-front.jpg" width="800" height="600" alt="Wallet Front">
                <img src="https://example.com/images/wallet-back.jpg" width="800" height="600" alt="Wallet Back">
                <img src="https://example.com/images/wallet-interior.jpg" width="800" height="600" alt="Wallet Interior">
                <img src="https://example.com/logo.png" width="50" height="50" alt="Logo">
            </div>
            
            <div class="product-description">
                <p>Experience luxury with our handcrafted leather wallet. Made from premium full-grain leather,
                this wallet combines timeless elegance with modern functionality.</p>
                <p>Features include 8 card slots, 2 bill compartments, and RFID protection.</p>
            </div>
            
            <div class="product-price">
                <span class="price">$49.99</span>
            </div>
        </div>
    </body>
    </html>
    """
    
    print("=" * 80)
    print("Web Scraper HTML Parsing Test")
    print("=" * 80)
    print()
    
    # Setup
    print("1. Initializing scraper...")
    config = Config()
    logger = setup_logger('test', None, 'ERROR')  # Suppress logs
    scraper = WebScraper(config, logger)
    print("   ✓ Scraper initialized")
    print()
    
    # Parse HTML
    print("2. Parsing sample HTML...")
    soup = scraper.parse_html(sample_html)
    print("   ✓ HTML parsed successfully")
    print()
    
    # Extract metadata
    print("3. Extracting metadata...")
    base_url = "https://example.com/products/wallet"
    metadata = scraper.extract_metadata(soup, base_url)
    
    print("   Title:", metadata['title'])
    print("   Description:", metadata['description'][:60] + "...")
    print("   Keywords:", metadata['keywords'])
    print("   OG Title:", metadata['og_title'])
    print("   OG Description:", metadata['og_description'])
    print("   OG Image:", metadata['og_image'])
    print("   Product Name:", metadata['product_name'])
    print("   Price:", metadata['price'])
    print("   Images found:", len(metadata['images']))
    print("   Breadcrumbs:", metadata['breadcrumbs'])
    print()
    
    # Verify extraction
    print("4. Verifying extraction results...")
    tests = [
        ("Title extraction", bool(metadata['title'])),
        ("Description extraction", bool(metadata['description'])),
        ("Product name from structured data", metadata['product_name'] == "Premium Leather Wallet"),
        ("Price extraction", metadata['price'] == "49.99"),
        ("Image filtering (should skip logo)", len(metadata['images']) == 3),
        ("Breadcrumb extraction", len(metadata['breadcrumbs']) > 0),
        ("OG metadata extraction", bool(metadata['og_title'])),
    ]
    
    passed = 0
    failed = 0
    for test_name, result in tests:
        if result:
            print(f"   ✓ {test_name}")
            passed += 1
        else:
            print(f"   ✗ {test_name}")
            failed += 1
    
    print()
    print("=" * 80)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return failed == 0


if __name__ == '__main__':
    try:
        success = test_html_parsing()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
