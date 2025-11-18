#!/usr/bin/env python3
"""
Demo Script - Product Scraper
Demonstrates the key features without requiring actual URLs
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import Config, setup_logger, ProductScraper
from modules.shopify_exporter import ShopifyExporter


def demo_without_web_scraping():
    """
    Demonstrate the product scraper capabilities using mock data
    This shows what the scraper does without requiring actual URLs
    """
    print("=" * 80)
    print("Product Scraper Demo")
    print("=" * 80)
    print()
    
    # Initialize configuration
    print("1. Loading configuration...")
    config = Config()
    print(f"   ✓ Image max size: {config.image_max_width}x{config.image_max_height}")
    print(f"   ✓ Request delay: {config.request_delay}s")
    print(f"   ✓ Output directory: {config.output_dir}")
    print()
    
    # Setup logger
    print("2. Setting up logger...")
    logger = setup_logger('demo', config.logs_dir, 'INFO')
    logger.info("Demo started")
    print("   ✓ Logger initialized")
    print()
    
    # Create mock product data (simulates scraped data)
    print("3. Simulating scraped product data...")
    mock_products = [
        {
            'title': 'Premium Leather Wallet',
            'enhanced_description': (
                '<p>Discover the perfect blend of style and functionality with our '
                'Premium Leather Wallet. Crafted from genuine full-grain leather, '
                'this wallet features multiple card slots, a bill compartment, and '
                'a sleek, minimalist design.</p>\n'
                '<p>Key Features:</p>\n'
                '<ul>'
                '<li>100% genuine leather construction</li>'
                '<li>8 card slots plus 2 hidden compartments</li>'
                '<li>RFID protection for security</li>'
                '<li>Slim profile fits comfortably in pocket</li>'
                '</ul>'
            ),
            'original_description': 'A high-quality leather wallet with card slots.',
            'price': '49.99',
            'tags': ['wallet', 'leather', 'premium', 'accessories', 'mens', 'gift'],
            'processed_images': ['wallet_image1.jpg', 'wallet_image2.jpg'],
            'summary': 'Premium leather wallet with RFID protection and multiple compartments',
            'seo_title': 'Premium Leather Wallet - RFID Protected',
            'seo_description': 'Genuine leather wallet with 8 card slots and RFID protection',
            'vendor': 'Premium Goods Co',
            'type': 'Accessories',
            'sku': 'WALLET-001',
            'source_url': 'https://example.com/products/leather-wallet'
        },
        {
            'title': 'Stainless Steel Water Bottle',
            'enhanced_description': (
                '<p>Stay hydrated in style with our Stainless Steel Water Bottle. '
                'This eco-friendly, reusable bottle keeps drinks cold for 24 hours '
                'and hot for 12 hours, making it perfect for any adventure.</p>\n'
                '<p>Specifications:</p>\n'
                '<ul>'
                '<li>Double-wall vacuum insulation</li>'
                '<li>BPA-free materials</li>'
                '<li>Leak-proof lid design</li>'
                '<li>Available in 20oz and 32oz sizes</li>'
                '</ul>'
            ),
            'original_description': 'Insulated water bottle that keeps drinks cold.',
            'price': '29.99',
            'tags': ['water bottle', 'insulated', 'stainless steel', 'eco-friendly', 'sports'],
            'processed_images': ['bottle_image1.jpg', 'bottle_image2.jpg', 'bottle_image3.jpg'],
            'summary': 'Insulated stainless steel bottle for hot and cold beverages',
            'seo_title': 'Insulated Stainless Steel Water Bottle',
            'seo_description': 'Keep drinks cold for 24h or hot for 12h with our vacuum-insulated bottle',
            'vendor': 'EcoLife',
            'type': 'Drinkware',
            'sku': 'BOTTLE-002',
            'source_url': 'https://example.com/products/water-bottle'
        }
    ]
    
    print(f"   ✓ Created {len(mock_products)} mock products")
    for product in mock_products:
        print(f"     - {product['title']}: ${product['price']}")
    print()
    
    # Export to CSV
    print("4. Exporting to Shopify CSV...")
    exporter = ShopifyExporter(config, logger)
    
    csv_path = config.output_dir / 'demo_products.csv'
    result = exporter.export_to_csv(mock_products, csv_path)
    print(f"   ✓ CSV exported to: {result}")
    
    # Display CSV preview
    with open(result, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"   ✓ Generated {len(lines)} lines (1 header + {len(lines)-1} data rows)")
    print()
    
    # Export to JSON
    print("5. Exporting to JSON (alternative format)...")
    json_path = config.output_dir / 'demo_products.json'
    result = exporter.export_to_json(mock_products, json_path)
    print(f"   ✓ JSON exported to: {result}")
    print()
    
    # Display what would happen with GPT (without API key)
    print("6. AI Features Demo (fallback mode - no API key)...")
    from modules.gpt_processor import GPTProcessor
    gpt = GPTProcessor(config, logger)
    
    sample_tags = gpt.generate_tags(
        "Premium Leather Wallet",
        "A high-quality leather wallet with card slots"
    )
    print(f"   ✓ Generated tags (fallback): {sample_tags}")
    
    sample_summary = gpt.generate_summary(
        "This is a long product description that needs to be summarized. " * 10,
        max_words=15
    )
    print(f"   ✓ Generated summary (fallback): {sample_summary[:80]}...")
    print()
    
    # Summary
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    print()
    print("What this demo showed:")
    print("  ✓ Configuration loading and validation")
    print("  ✓ Structured logging setup")
    print("  ✓ Product data structure (from web scraping)")
    print("  ✓ Shopify CSV export with complete schema")
    print("  ✓ JSON export alternative")
    print("  ✓ AI features (fallback mode without API key)")
    print()
    print("To scrape real products:")
    print("  python main.py https://example.com/product-url")
    print()
    print("For full AI features:")
    print("  1. Add OPENAI_API_KEY to config.env")
    print("  2. Run: python main.py https://example.com/product-url")
    print()
    print(f"Output files created in: {config.output_dir}/")
    print()


if __name__ == '__main__':
    try:
        demo_without_web_scraping()
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
