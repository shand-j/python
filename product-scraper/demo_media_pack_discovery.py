#!/usr/bin/env python3
"""
Media Pack Discovery Demo
Demonstrates the official media pack discovery feature
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import (
    MediaPackDiscovery, MediaPackInfo,
    Brand, BrandManager,
    Config, setup_logger
)


def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def demo_scenario_1():
    """Scenario 1: Media Pack URL Pattern Discovery"""
    print_header("Scenario 1: Media Pack URL Pattern Discovery")
    
    config = Config()
    logger = setup_logger('Demo', None, 'INFO')
    discovery = MediaPackDiscovery(config, logger)
    
    print("\n1. Standard media pack paths checked:")
    for i, path in enumerate(discovery.MEDIA_PACK_PATHS[:8], 1):
        print(f"   {i}. {path}")
    
    print(f"\n   Total paths: {len(discovery.MEDIA_PACK_PATHS)}")
    
    return True


def demo_scenario_2():
    """Scenario 2: File Type Recognition"""
    print_header("Scenario 2: File Type Recognition")
    
    config = Config()
    logger = setup_logger('Demo', None, 'INFO')
    discovery = MediaPackDiscovery(config, logger)
    
    print("\n1. Recognized media file extensions:")
    
    # Group by category
    categories = {}
    for ext, info in discovery.FILE_TYPES.items():
        category = info['category']
        if category not in categories:
            categories[category] = []
        categories[category].append((ext, info))
    
    for category, files in sorted(categories.items()):
        print(f"\n   {category.upper()}:")
        for ext, info in files:
            priority_marker = "★" * (4 - info['priority'])
            print(f"     {ext:<10} {info['content_type']:<20} {priority_marker}")
    
    print("\n2. Priority system:")
    print("   ★★★ = Highest priority (comprehensive archives)")
    print("   ★★  = Medium priority (documentation)")
    print("   ★   = Standard priority (individual files)")
    
    return True


def demo_scenario_3():
    """Scenario 3: Media Pack Content Preview"""
    print_header("Scenario 3: Media Pack Content Preview")
    
    config = Config()
    logger = setup_logger('Demo', None, 'INFO')
    discovery = MediaPackDiscovery(config, logger)
    
    print("\n1. Creating sample media pack...")
    
    # Create sample media pack
    pack = MediaPackInfo(
        url="https://vaporesso.com/media/press-kit-2024.zip",
        file_type=".zip",
        file_size=47185920,  # ~45 MB
        content_type="Compressed archive",
        accessible=True,
        restricted=False,
        discovered_from="https://vaporesso.com/press"
    )
    
    print(f"   URL: {pack.url}")
    print(f"   Type: {pack.content_type} ({pack.file_type})")
    print(f"   Size: {discovery.format_file_size(pack.file_size)}")
    print(f"   Accessible: {'✓' if pack.accessible else '✗'}")
    print(f"   Restricted: {'Yes' if pack.restricted else 'No'}")
    
    if pack.estimated_download_time:
        print(f"   Est. Download: {pack.estimated_download_time:.1f}s @ 1 MB/s")
    
    print("\n2. Metadata retrieved via HEAD request:")
    print("   ✓ File size")
    print("   ✓ Content type")
    print("   ✓ Accessibility status")
    print("   ✓ Access restrictions")
    print("   ✓ Download time estimate")
    
    return True


def demo_scenario_4():
    """Scenario 4: Priority-Based Ordering"""
    print_header("Scenario 4: Priority-Based Ordering")
    
    config = Config()
    logger = setup_logger('Demo', None, 'INFO')
    discovery = MediaPackDiscovery(config, logger)
    
    print("\n1. Creating mixed media pack collection...")
    
    # Create various media packs
    packs = [
        MediaPackInfo(url="logo.jpg", file_type=".jpg", content_type="High-res images"),
        MediaPackInfo(url="kit.zip", file_type=".zip", content_type="Compressed archive"),
        MediaPackInfo(url="guide.pdf", file_type=".pdf", content_type="Documentation"),
        MediaPackInfo(url="product.png", file_type=".png", content_type="High-res images"),
        MediaPackInfo(url="assets.rar", file_type=".rar", content_type="Compressed archive"),
        MediaPackInfo(url="icon.svg", file_type=".svg", content_type="Vector graphics"),
    ]
    
    print(f"   Created {len(packs)} media packs")
    
    print("\n2. Ordering by priority (archives first)...")
    prioritized = discovery.get_prioritized_packs(packs)
    
    print("\n3. Prioritized order:")
    for i, pack in enumerate(prioritized, 1):
        file_info = discovery.FILE_TYPES.get(pack.file_type, {})
        priority = file_info.get('priority', 99)
        print(f"   {i}. {pack.content_type:<20} ({pack.file_type}) - Priority {priority}")
    
    return True


def demo_scenario_5():
    """Scenario 5: Access Restriction Handling"""
    print_header("Scenario 5: Access Restriction Handling")
    
    config = Config()
    logger = setup_logger('Demo', None, 'INFO')
    discovery = MediaPackDiscovery(config, logger)
    
    print("\n1. Sample media packs with different access levels:")
    
    packs = [
        MediaPackInfo(
            url="https://brand.com/public/media.zip",
            file_type=".zip",
            accessible=True,
            restricted=False,
            content_type="Compressed archive"
        ),
        MediaPackInfo(
            url="https://brand.com/protected/premium.zip",
            file_type=".zip",
            accessible=False,
            restricted=True,
            restriction_type="Authentication required",
            content_type="Compressed archive"
        ),
        MediaPackInfo(
            url="https://brand.com/members/exclusive.rar",
            file_type=".rar",
            accessible=False,
            restricted=True,
            restriction_type="Access forbidden",
            content_type="Compressed archive"
        ),
    ]
    
    for i, pack in enumerate(packs, 1):
        status = "✓ Accessible" if pack.accessible else "✗ Restricted"
        restriction = f" - {pack.restriction_type}" if pack.restricted else ""
        
        print(f"\n   {i}. {pack.url}")
        print(f"      Status: {status}{restriction}")
    
    print("\n2. Restriction detection:")
    print("   ✓ HTTP 401 → Authentication required")
    print("   ✓ HTTP 403 → Access forbidden")
    print("   ✓ WWW-Authenticate header → Auth required")
    print("   ✓ Logs restriction type")
    print("   ✓ Continues with available sources")
    
    return True


def demo_scenario_6():
    """Scenario 6: Brand Integration"""
    print_header("Scenario 6: Brand Integration")
    
    config = Config()
    logger = setup_logger('Demo', None, 'INFO')
    
    print("\n1. Creating brand with media packs...")
    
    brand = Brand(
        name="Vaporesso",
        website="vaporesso.com",
        priority="high",
        status="validated",
        media_packs=[
            {
                "url": "https://vaporesso.com/media/press-kit.zip",
                "file_type": ".zip",
                "file_size": 52428800,
                "content_type": "Compressed archive",
                "accessible": True,
                "restricted": False
            },
            {
                "url": "https://vaporesso.com/resources/catalog.pdf",
                "file_type": ".pdf",
                "file_size": 15728640,
                "content_type": "Documentation",
                "accessible": True,
                "restricted": False
            }
        ],
        media_pack_count=2,
        last_media_scan="2025-11-17T20:30:00"
    )
    
    print(f"   Brand: {brand.name}")
    print(f"   Website: {brand.website}")
    print(f"   Media packs: {brand.media_pack_count}")
    print(f"   Last scan: {brand.last_media_scan}")
    
    print("\n2. Media pack details:")
    discovery = MediaPackDiscovery(config, logger)
    
    for i, pack_dict in enumerate(brand.media_packs, 1):
        pack = MediaPackInfo.from_dict(pack_dict)
        size = discovery.format_file_size(pack.file_size)
        print(f"\n   {i}. {pack.content_type}")
        print(f"      URL: {pack.url}")
        print(f"      Size: {size}")
    
    print("\n3. Brand model extended with:")
    print("   ✓ media_packs (list)")
    print("   ✓ media_pack_count (int)")
    print("   ✓ last_media_scan (timestamp)")
    
    return True


def demo_scenario_7():
    """Scenario 7: Alternative Domain Discovery"""
    print_header("Scenario 7: Alternative Domain Discovery")
    
    config = Config()
    logger = setup_logger('Demo', None, 'INFO')
    discovery = MediaPackDiscovery(config, logger)
    
    print("\n1. Primary domain: smoktech.com")
    
    print("\n2. Potential alternative domains:")
    alternatives = [
        "smoktechstore.com",
        "smoktech-store.com",
        "shopsmoketech.com",
        "storesmoketech.com",
        "smoktechshop.com",
        "smoktech-shop.com",
    ]
    
    for domain in alternatives:
        print(f"   • {domain}")
    
    print("\n3. Domain discovery process:")
    print("   1. Generate domain variations")
    print("   2. Validate domain existence")
    print("   3. Verify authenticity")
    print("   4. Scan for media packs")
    print("   5. Maintain domain relationships")
    
    return True


def main():
    """Run all demo scenarios"""
    print("="*70)
    print("  Media Pack Discovery Feature Demo")
    print("  Official Brand Media Pack Detection and Analysis")
    print("="*70)
    
    scenarios = [
        demo_scenario_1,
        demo_scenario_2,
        demo_scenario_3,
        demo_scenario_4,
        demo_scenario_5,
        demo_scenario_6,
        demo_scenario_7,
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
    
    print("\n📚 Documentation:")
    print("   • MEDIA_PACK_DISCOVERY.md - Complete guide")
    print("   • BRAND_MANAGEMENT.md - Brand management")
    print("   • README.md - Project overview")
    
    print("\n🔧 Commands:")
    print("   python brand_manager.py discover-media --save")
    print("   python brand_manager.py media-packs")
    print("   python brand_manager.py media-packs --type archive")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
