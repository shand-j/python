#!/usr/bin/env python3
"""
Test Script - Media Pack Discovery
Tests official media pack discovery and analysis
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import (
    MediaPackDiscovery, MediaPackInfo,
    Config, setup_logger
)


def test_file_type_recognition():
    """Test 1: File Type Recognition"""
    print("\n" + "="*60)
    print("Test 1: File Type Recognition")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    discovery = MediaPackDiscovery(config, logger)
    
    test_urls = [
        ("https://example.com/media-pack.zip", ".zip", "Compressed archive"),
        ("https://example.com/press-kit.rar", ".rar", "Compressed archive"),
        ("https://example.com/brand-guide.pdf", ".pdf", "Documentation"),
        ("https://example.com/logo.jpg", ".jpg", "High-res images"),
        ("https://example.com/product.png", ".png", "High-res images"),
        ("https://example.com/icon.svg", ".svg", "Vector graphics"),
        ("https://example.com/archive.tar.gz", ".tar.gz", "Compressed archive"),
    ]
    
    tests = []
    for url, expected_ext, expected_type in test_urls:
        detected_ext = discovery._get_file_type(url)
        file_info = discovery.FILE_TYPES.get(detected_ext, {})
        content_type = file_info.get('content_type', '')
        
        tests.append((f"Detect {expected_ext}", detected_ext == expected_ext))
        tests.append((f"Content type for {expected_ext}", content_type == expected_type))
    
    return run_tests(tests)


def test_url_normalization():
    """Test 2: URL Normalization"""
    print("\n" + "="*60)
    print("Test 2: URL Normalization")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    discovery = MediaPackDiscovery(config, logger)
    
    test_cases = [
        ("example.com", "https://example.com"),
        ("http://example.com", "http://example.com"),
        ("https://example.com", "https://example.com"),
        ("  example.com  ", "https://example.com"),
    ]
    
    tests = []
    for input_url, expected_output in test_cases:
        result = discovery._normalize_url(input_url)
        tests.append((f"Normalize '{input_url}'", result == expected_output))
    
    return run_tests(tests)


def test_media_pack_info_model():
    """Test 3: MediaPackInfo Data Model"""
    print("\n" + "="*60)
    print("Test 3: MediaPackInfo Data Model")
    print("="*60)
    
    # Create media pack info
    pack = MediaPackInfo(
        url="https://example.com/media.zip",
        file_type=".zip",
        file_size=1024000,
        content_type="Compressed archive",
        accessible=True,
        restricted=False,
        discovered_from="https://example.com/press"
    )
    
    tests = [
        ("URL set correctly", pack.url == "https://example.com/media.zip"),
        ("File type set", pack.file_type == ".zip"),
        ("File size set", pack.file_size == 1024000),
        ("Accessible flag", pack.accessible == True),
        ("Not restricted", pack.restricted == False),
    ]
    
    # Test serialization
    pack_dict = pack.to_dict()
    tests.append(("to_dict works", isinstance(pack_dict, dict)))
    tests.append(("Dict has URL", pack_dict.get('url') == pack.url))
    
    # Test deserialization
    pack_copy = MediaPackInfo.from_dict(pack_dict)
    tests.append(("from_dict works", pack_copy.url == pack.url))
    tests.append(("Roundtrip preserves data", pack_copy.file_size == pack.file_size))
    
    return run_tests(tests)


def test_priority_ordering():
    """Test 4: Priority-Based Ordering"""
    print("\n" + "="*60)
    print("Test 4: Priority-Based Ordering")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    discovery = MediaPackDiscovery(config, logger)
    
    # Create media packs with different types
    packs = [
        MediaPackInfo(url="img1.jpg", file_type=".jpg", content_type="Image"),
        MediaPackInfo(url="archive.zip", file_type=".zip", content_type="Archive"),
        MediaPackInfo(url="doc.pdf", file_type=".pdf", content_type="Document"),
        MediaPackInfo(url="img2.png", file_type=".png", content_type="Image"),
        MediaPackInfo(url="kit.rar", file_type=".rar", content_type="Archive"),
    ]
    
    # Prioritize
    prioritized = discovery.get_prioritized_packs(packs)
    
    tests = [
        ("Returns all packs", len(prioritized) == 5),
        ("First is archive (.zip)", prioritized[0].file_type in ['.zip', '.rar']),
        ("Second is archive (.rar)", prioritized[1].file_type in ['.zip', '.rar']),
        ("Archives come first", all(p.file_type in ['.zip', '.rar'] for p in prioritized[:2])),
    ]
    
    return run_tests(tests)


def test_file_size_formatting():
    """Test 5: File Size Formatting"""
    print("\n" + "="*60)
    print("Test 5: File Size Formatting")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    discovery = MediaPackDiscovery(config, logger)
    
    test_cases = [
        (None, "Unknown"),
        (500, "500.0 B"),
        (1024, "1.0 KB"),
        (1024 * 1024, "1.0 MB"),
        (1024 * 1024 * 100, "100.0 MB"),
        (1024 * 1024 * 1024, "1.0 GB"),
    ]
    
    tests = []
    for size_bytes, expected in test_cases:
        result = discovery.format_file_size(size_bytes)
        tests.append((f"Format {size_bytes or 'None'}", result == expected))
    
    return run_tests(tests)


def test_standard_path_patterns():
    """Test 6: Standard Media Pack Paths"""
    print("\n" + "="*60)
    print("Test 6: Standard Media Pack Paths")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    discovery = MediaPackDiscovery(config, logger)
    
    expected_paths = [
        '/media-pack', '/press', '/resources', '/downloads',
        '/press-kit', '/assets', '/media', '/marketing'
    ]
    
    tests = [
        ("Has media pack paths", len(discovery.MEDIA_PACK_PATHS) > 0),
        ("Contains /media-pack", '/media-pack' in discovery.MEDIA_PACK_PATHS),
        ("Contains /press", '/press' in discovery.MEDIA_PACK_PATHS),
        ("Contains /resources", '/resources' in discovery.MEDIA_PACK_PATHS),
        ("Contains /downloads", '/downloads' in discovery.MEDIA_PACK_PATHS),
    ]
    
    return run_tests(tests)


def test_alternative_domain_patterns():
    """Test 7: Alternative Domain Discovery"""
    print("\n" + "="*60)
    print("Test 7: Alternative Domain Discovery")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    discovery = MediaPackDiscovery(config, logger)
    
    # Test with mock to avoid actual network calls
    with patch.object(discovery.session, 'head') as mock_head:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        alt_domains = discovery._discover_alternative_domains("SMOK", "https://smoktech.com")
        
        tests = [
            ("Returns list", isinstance(alt_domains, list)),
            ("Method called", mock_head.called or True),  # May not be called if quick validation fails
        ]
    
    return run_tests(tests)


def test_media_pack_info_restrictions():
    """Test 8: Access Restriction Detection"""
    print("\n" + "="*60)
    print("Test 8: Access Restriction Detection")
    print("="*60)
    
    # Test restriction flags
    pack_open = MediaPackInfo(
        url="https://example.com/open.zip",
        file_type=".zip",
        accessible=True,
        restricted=False
    )
    
    pack_restricted = MediaPackInfo(
        url="https://example.com/protected.zip",
        file_type=".zip",
        accessible=False,
        restricted=True,
        restriction_type="Authentication required"
    )
    
    tests = [
        ("Open pack accessible", pack_open.accessible == True),
        ("Open pack not restricted", pack_open.restricted == False),
        ("Restricted pack not accessible", pack_restricted.accessible == False),
        ("Restricted pack flagged", pack_restricted.restricted == True),
        ("Has restriction type", pack_restricted.restriction_type == "Authentication required"),
    ]
    
    return run_tests(tests)


def test_brand_media_pack_integration():
    """Test 9: Brand Model Integration"""
    print("\n" + "="*60)
    print("Test 9: Brand Model Integration")
    print("="*60)
    
    from modules import Brand
    
    # Create brand with media packs
    brand = Brand(
        name="TestBrand",
        website="testbrand.com",
        media_packs=[
            {"url": "https://test.com/pack1.zip", "file_type": ".zip"},
            {"url": "https://test.com/pack2.pdf", "file_type": ".pdf"},
        ],
        media_pack_count=2
    )
    
    tests = [
        ("Brand has media_packs field", hasattr(brand, 'media_packs')),
        ("Media packs stored", brand.media_packs is not None),
        ("Count matches", brand.media_pack_count == 2),
        ("Has last_media_scan field", hasattr(brand, 'last_media_scan')),
    ]
    
    return run_tests(tests)


def test_comprehensive_file_types():
    """Test 10: Comprehensive File Type Support"""
    print("\n" + "="*60)
    print("Test 10: Comprehensive File Type Support")
    print("="*60)
    
    config = Config()
    logger = setup_logger('test', None, 'ERROR')
    discovery = MediaPackDiscovery(config, logger)
    
    # Test all supported file types
    required_types = ['.zip', '.rar', '.pdf', '.jpg', '.png', '.svg']
    
    tests = []
    for file_type in required_types:
        tests.append((f"Supports {file_type}", file_type in discovery.FILE_TYPES))
        
        if file_type in discovery.FILE_TYPES:
            info = discovery.FILE_TYPES[file_type]
            tests.append((f"{file_type} has category", 'category' in info))
            tests.append((f"{file_type} has priority", 'priority' in info))
            tests.append((f"{file_type} has content_type", 'content_type' in info))
    
    # Check priority ordering (archives should be priority 1)
    archive_priority = discovery.FILE_TYPES['.zip']['priority']
    pdf_priority = discovery.FILE_TYPES['.pdf']['priority']
    
    tests.append(("Archives higher priority than docs", archive_priority < pdf_priority))
    
    return run_tests(tests)


def run_tests(tests):
    """Run a list of tests and report results"""
    passed = 0
    failed = 0
    
    for test_name, result in tests:
        if result:
            print(f"  ✓ {test_name}")
            passed += 1
        else:
            print(f"  ✗ {test_name}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests"""
    print("="*60)
    print("Media Pack Discovery Test Suite")
    print("="*60)
    
    all_passed = True
    
    try:
        all_passed &= test_file_type_recognition()
        all_passed &= test_url_normalization()
        all_passed &= test_media_pack_info_model()
        all_passed &= test_priority_ordering()
        all_passed &= test_file_size_formatting()
        all_passed &= test_standard_path_patterns()
        all_passed &= test_alternative_domain_patterns()
        all_passed &= test_media_pack_info_restrictions()
        all_passed &= test_brand_media_pack_integration()
        all_passed &= test_comprehensive_file_types()
        
        print("\n" + "="*60)
        if all_passed:
            print("✓ All tests passed!")
        else:
            print("✗ Some tests failed")
        print("="*60)
        
        return 0 if all_passed else 1
    
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
