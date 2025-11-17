#!/usr/bin/env python3
"""
Demo Script for Vape Product Tagger
Demonstrates tagging capabilities with sample products
"""
import sys
from pathlib import Path

from modules import (
    Config, setup_logger, VapeTaxonomy, OllamaProcessor,
    ProductTagger, ShopifyHandler
)


def create_sample_products():
    """Create sample vaping products for demonstration"""
    return [
        {
            'title': 'Tropical Mango Ice Disposable Vape 0mg',
            'description': 'Experience the exotic taste of ripe mango with a refreshing icy finish. This disposable vape offers a smooth, nicotine-free vaping experience perfect for on-the-go use.',
            'handle': 'tropical-mango-ice-disposable',
            'vendor': 'Vape Co',
            'price': '9.99',
            'sku': 'TMI-DISP-0MG',
            'images': []
        },
        {
            'title': 'Strawberry Cheesecake Pod System 50mg Salt Nicotine',
            'description': 'Indulge in the creamy richness of New York-style cheesecake paired with fresh strawberries. High-strength nicotine salt for quick satisfaction. Compact pod system design.',
            'handle': 'strawberry-cheesecake-pod',
            'vendor': 'Vape Co',
            'price': '24.99',
            'sku': 'SC-POD-50MG',
            'images': []
        },
        {
            'title': 'Classic Tobacco Rechargeable Vape Pen 6mg',
            'description': 'Traditional tobacco flavor for those who prefer authenticity. Rechargeable pen-style device with low nicotine strength, ideal for former light smokers.',
            'handle': 'classic-tobacco-pen',
            'vendor': 'Vape Co',
            'price': '19.99',
            'sku': 'CT-PEN-6MG',
            'images': []
        },
        {
            'title': 'Peppermint Arctic Blast AIO Device 12mg',
            'description': 'Intense cooling menthol with fresh peppermint. All-in-one device with moderate nicotine strength. Perfect for menthol lovers seeking an icy experience.',
            'handle': 'peppermint-arctic-aio',
            'vendor': 'Vape Co',
            'price': '29.99',
            'sku': 'PA-AIO-12MG',
            'images': []
        },
        {
            'title': 'Mixed Berry Fusion Box Mod 3mg Freebase',
            'description': 'A delicious blend of strawberries, raspberries, and blueberries. Advanced box mod for experienced users. Low nicotine freebase for smooth all-day vaping.',
            'handle': 'mixed-berry-box-mod',
            'vendor': 'Vape Co',
            'price': '49.99',
            'sku': 'MB-BOX-3MG',
            'images': []
        },
        {
            'title': 'Caramel Latte Coffee Vape Stick 18mg',
            'description': 'Rich espresso with sweet caramel and creamy notes. Stick-style device with high nicotine strength for heavy smokers transitioning to vaping.',
            'handle': 'caramel-latte-stick',
            'vendor': 'Vape Co',
            'price': '14.99',
            'sku': 'CL-STICK-18MG',
            'images': []
        }
    ]


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_product_tags(product):
    """Print product and its tags in a formatted way"""
    print(f"Product: {product['title']}")
    print(f"Price: ${product['price']}")
    print(f"SKU: {product['sku']}")
    print(f"\nGenerated Tags ({len(product['tags'])} total):")
    print(", ".join(product['tags']))
    
    print("\nTag Breakdown:")
    breakdown = product.get('tag_breakdown', {})
    
    if breakdown.get('device_type'):
        print(f"  Device Type: {', '.join(breakdown['device_type'])}")
    if breakdown.get('device_form'):
        print(f"  Device Form: {', '.join(breakdown['device_form'])}")
    if breakdown.get('flavors'):
        print("  Flavors:")
        for family, tags in breakdown['flavors'].items():
            print(f"    - {family}: {', '.join(tags)}")
    if breakdown.get('nicotine_strength'):
        print(f"  Nicotine Strength: {', '.join(breakdown['nicotine_strength'])}")
    if breakdown.get('nicotine_type'):
        print(f"  Nicotine Type: {', '.join(breakdown['nicotine_type'])}")
    if breakdown.get('compliance'):
        print(f"  Compliance: {', '.join(breakdown['compliance'][:3])}...")
    
    print("\n" + "-" * 70)


def main():
    """Main demo function"""
    print_section("Vape Product Tagger - Demo")
    
    print("This demo showcases the intelligent tagging capabilities")
    print("of the Vape Product Tagger with sample products.")
    print("\nNote: AI tagging is disabled for this demo (rule-based only)")
    
    # Initialize configuration (minimal)
    config = Config()
    config.enable_ai_tagging = False  # Disable AI for demo
    config.enable_compliance_tags = True
    
    # Set up logging
    logger = setup_logger(
        name='vape-tagger-demo',
        log_dir=str(config.logs_dir),
        level='INFO'
    )
    
    # Initialize components
    tagger = ProductTagger(config, logger, ollama_processor=None)
    shopify_handler = ShopifyHandler(config, logger)
    
    # Create sample products
    sample_products = create_sample_products()
    
    print_section("Processing Sample Products")
    
    # Tag each product
    tagged_products = []
    for i, product in enumerate(sample_products, 1):
        print(f"\n[{i}/{len(sample_products)}] Processing: {product['title']}")
        tagged_product = tagger.tag_product(product, use_ai=False)
        tagged_products.append(tagged_product)
        print(f"✓ Generated {len(tagged_product['tags'])} tags")
    
    print_section("Detailed Tag Analysis")
    
    # Display detailed tags for each product
    for tagged_product in tagged_products:
        print_product_tags(tagged_product)
        input("\nPress Enter to see next product...")
    
    print_section("Collection Generation")
    
    # Generate collections
    collections = tagger.generate_collections(tagged_products)
    print(f"Generated {len(collections)} dynamic collections:\n")
    for collection in collections:
        print(f"  • {collection['title']}")
        print(f"    Description: {collection['description']}")
        print(f"    Filter Tags: {', '.join(collection['filter_tags'])}")
        print()
    
    print_section("Export Options")
    
    # Ask if user wants to export
    export = input("Export tagged products to CSV? (y/n): ").lower().strip()
    if export == 'y':
        csv_path = shopify_handler.export_to_csv(tagged_products)
        print(f"\n✓ Products exported to: {csv_path}")
    
    export_json = input("Export to JSON format? (y/n): ").lower().strip()
    if export_json == 'y':
        json_path = shopify_handler.export_to_json(tagged_products)
        print(f"\n✓ Products exported to: {json_path}")
    
    export_coll = input("Export collections to JSON? (y/n): ").lower().strip()
    if export_coll == 'y':
        coll_path = shopify_handler.export_collections(collections)
        print(f"\n✓ Collections exported to: {coll_path}")
    
    print_section("Demo Complete")
    
    print("Key Features Demonstrated:")
    print("  ✓ Rule-based intelligent tagging")
    print("  ✓ Multi-dimensional taxonomy (device, flavor, nicotine)")
    print("  ✓ Hierarchical tag structure")
    print("  ✓ Compliance tag generation")
    print("  ✓ Dynamic collection creation")
    print("  ✓ Shopify CSV export compatibility")
    print("\nTo try with your own products:")
    print("  python main.py --input your_products.csv")
    print("\nFor AI-enhanced tagging:")
    print("  1. Install and start Ollama")
    print("  2. Configure ENABLE_AI_TAGGING=true in config.env")
    print("  3. Run: python main.py --input your_products.csv")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        sys.exit(1)
