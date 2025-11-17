#!/usr/bin/env python3
"""
Test script for smart image filtering functionality
"""
import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import Config, setup_logger, ProductScraper

def test_smart_image_filtering():
    """Test the new smart image filtering"""
    
    # Sample URL - you can change this to test different sites
    test_url = "https://www.vapourism.co.uk/products/20mg-lost-mary-4in1-pod-vape-kit-2400-puffs?Flavour=Menthol"
    
    print("🧪 Testing Smart Image Filtering")
    print("=" * 50)
    print(f"URL: {test_url}")
    print()
    
    try:
        # Setup
        config = Config()
        logger = setup_logger(config)
        scraper = ProductScraper(config, logger)
        
        # Scrape product with image processing
        print("🚀 Starting product scrape...")
        product = scraper.scrape_product(test_url, process_images=True)
        
        print("✅ Scrape completed!")
        print()
        
        # Display results
        print("📊 Image Processing Results:")
        print("-" * 30)
        
        shopify_images = product.get('processed_images', [])
        image_metadata = product.get('image_metadata', {})
        
        print(f"Product Images (Shopify): {len(shopify_images)}")
        for i, img_path in enumerate(shopify_images[:5], 1):  # Show first 5
            print(f"  {i}. {Path(img_path).name}")
        
        if len(shopify_images) > 5:
            print(f"  ... and {len(shopify_images) - 5} more")
        
        print()
        print("📈 Processing Summary:")
        if image_metadata:
            print(f"  Total found: {image_metadata.get('total_images_found', 0)}")
            print(f"  Product images: {image_metadata.get('product_images_count', 0)}")
            print(f"  Alternative images: {image_metadata.get('alternative_images_count', 0)}")
            print(f"  Shopify ready: {image_metadata.get('shopify_images_count', 0)}")
        
        print()
        print("📁 Check the ./images/ directory for:")
        print("  • PRODUCT_XX_scoreY_hash.jpg - Images for Shopify import")
        print("  • ALT_XX_scoreY_hash.jpg - Alternative images for review")
        print("  • image_report_timestamp.json - Detailed processing report")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_smart_image_filtering()