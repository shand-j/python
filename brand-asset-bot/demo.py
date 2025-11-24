#!/usr/bin/env python3
"""
Demo Script - Brand Asset Bot
Demonstrates the key features for brand asset discovery
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import Config, setup_logger, BrandAssetScraper, BrandManager


def demo_brand_asset_discovery():
    """
    Demonstrate brand asset discovery capabilities
    """
    print("=" * 80)
    print("Brand Asset Bot Demo")
    print("=" * 80)
    print()
    
    # Initialize configuration
    print("1. Loading configuration...")
    config = Config()
    print(f"   ✓ Download directory: {config.download_dir}")
    print(f"   ✓ Extracted directory: {config.extracted_dir}")
    print(f"   ✓ Output directory: {config.output_dir}")
    print()
    
    # Setup logger
    print("2. Setting up logger...")
    logger = setup_logger('demo', config.logs_dir, 'INFO')
    logger.info("Demo started")
    print("   ✓ Logger initialized")
    print()
    
    # Initialize brand manager
    print("3. Setting up brand management...")
    brand_manager = BrandManager(logger=logger)
    print("   ✓ Brand manager initialized")
    print()
    
    # Create mock brand data
    print("4. Simulating brand registry...")
    from modules.brand_manager import Brand
    mock_brand = Brand(
        name="Demo Vape Brand",
        website="https://demo-vape-brand.com",
        priority="high"
    )
    print(f"   ✓ Created brand: {mock_brand.name}")
    print(f"   ✓ Website: {mock_brand.website}")
    print(f"   ✓ Priority: {mock_brand.priority}")
    print()
    
    # Initialize brand asset scraper
    print("5. Initializing brand asset scraper...")
    scraper = BrandAssetScraper(config, logger)
    print("   ✓ Brand asset scraper ready")
    print()
    
    # Simulate asset discovery results
    print("6. Simulating asset discovery results...")
    mock_results = {
        'brand': 'Demo Vape Brand',
        'timestamp': '2025-11-22T12:00:00',
        'official_assets': [
            {
                'asset_id': 'demo_brand_official_hero_001',
                'source': 'official_brand',
                'category': 'marketing',
                'tags': ['hero-image', 'banner', 'lifestyle'],
                'quality_score': 9.2,
                'dimensions': (1920, 1080),
                'file_size': 2457600
            },
            {
                'asset_id': 'demo_brand_official_pack_002',
                'source': 'official_brand',
                'category': 'branding',
                'tags': ['logo', 'brand-identity'],
                'quality_score': 9.8,
                'dimensions': (1200, 1200),
                'file_size': 512000
            }
        ],
        'competitor_assets': [
            {
                'asset_id': 'competitor_marketing_003',
                'source': 'competitor',
                'category': 'marketing',
                'tags': ['promo-banner', 'campaign'],
                'quality_score': 8.5,
                'dimensions': (1600, 900),
                'file_size': 1843200
            }
        ],
        'catalog_stats': {
            'total_official': 2,
            'total_competitor': 1,
            'total_assets': 3
        },
        'errors': []
    }
    
    print(f"   ✓ Official assets discovered: {len(mock_results['official_assets'])}")
    print(f"   ✓ Competitor assets discovered: {len(mock_results['competitor_assets'])}")
    print(f"   ✓ Total assets: {mock_results['catalog_stats']['total_assets']}")
    print()
    
    # Show asset details
    print("7. Asset Details:")
    for asset in mock_results['official_assets'] + mock_results['competitor_assets']:
        print(f"   • {asset['asset_id']}: {asset['category']} ({asset['quality_score']}/10)")
        print(f"     Tags: {', '.join(asset['tags'])}")
        print(f"     Dimensions: {asset['dimensions'][0]}x{asset['dimensions'][1]}")
        print()
    
    print("8. Exporting catalog...")
    # In a real scenario, this would create an actual file
    print("   ✓ Catalog exported to: output/brand_assets_Demo_Vape_Brand_20251122_120000.json")
    print()
    
    print("=" * 80)
    print("Demo completed successfully!")
    print("The Brand Asset Bot can discover marketing imagery from:")
    print("• Official brand media packs (ZIP/RAR archives)")
    print("• Hero banners and promotional content")
    print("• Competitor websites with brand products")
    print("• Quality assessment and content categorization")
    print("=" * 80)


if __name__ == '__main__':
    try:
        demo_brand_asset_discovery()
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
