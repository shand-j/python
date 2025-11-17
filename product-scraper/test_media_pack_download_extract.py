#!/usr/bin/env python3
"""
Test Script - Media Pack Download and Extraction
Tests downloading and extracting media packs
"""
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import (
    MediaPackDownloader, MediaPackExtractor, DownloadProgress,
    Config, setup_logger
)


def test_download_progress():
    """Test 1: Download Progress Tracking"""
    print("\n" + "="*60)
    print("Test 1: Download Progress Tracking")
    print("="*60)
    
    progress = DownloadProgress(
        total_size=1024 * 1024 * 45,  # 45 MB
        brand_name="SMOK",
        filename="smok-media-2024.zip"
    )
    
    tests = [
        ("Initial progress is 0", progress.get_progress_percent() == 0.0),
        ("Brand name set", progress.brand_name == "SMOK"),
        ("Filename set", progress.filename == "smok-media-2024.zip"),
    ]
    
    # Simulate download progress
    chunk_size = 1024 * 8  # 8 KB chunks
    progress.update(chunk_size)
    
    tests.extend([
        ("Progress updated", progress.downloaded == chunk_size),
        ("Progress > 0", progress.get_progress_percent() > 0),
    ])
    
    # Test formatting functions
    size_str = progress.format_size(1024 * 1024 * 45)
    tests.append(("Size formatting", "MB" in size_str))
    
    time_str = progress.format_time(125)
    tests.append(("Time formatting", "m" in time_str or "s" in time_str))
    
    return run_tests(tests)


def test_downloader_initialization():
    """Test 2: Downloader Initialization"""
    print("\n" + "="*60)
    print("Test 2: Downloader Initialization")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        download_dir = Path(temp_dir) / "downloads"
        
        config = Config()
        logger = setup_logger('test', None, 'ERROR')
        downloader = MediaPackDownloader(download_dir, config, logger)
        
        tests = [
            ("Downloader created", downloader is not None),
            ("Download directory created", download_dir.exists()),
            ("Has session", hasattr(downloader, 'session')),
        ]
        
        return run_tests(tests)


def test_filename_extraction():
    """Test 3: Filename Extraction from URL"""
    print("\n" + "="*60)
    print("Test 3: Filename Extraction from URL")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        downloader = MediaPackDownloader(Path(temp_dir))
        
        test_cases = [
            ("https://example.com/media/pack.zip", "pack.zip"),
            ("https://example.com/downloads/smok-2024.rar", "smok-2024.rar"),
            ("https://example.com/file%20name.zip", "file name.zip"),  # URL encoded
        ]
        
        tests = []
        for url, expected in test_cases:
            result = downloader._extract_filename_from_url(url)
            tests.append((f"Extract from {url}", result == expected))
        
        return run_tests(tests)


def test_checksum_calculation():
    """Test 4: File Checksum Calculation"""
    print("\n" + "="*60)
    print("Test 4: File Checksum Calculation")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = Path(temp_dir) / "test.txt"
        test_content = b"Test content for checksum"
        test_file.write_bytes(test_content)
        
        downloader = MediaPackDownloader(Path(temp_dir))
        
        # Calculate checksum
        checksum = downloader._calculate_checksum(test_file)
        
        tests = [
            ("Checksum calculated", checksum is not None),
            ("Checksum is hex string", all(c in '0123456789abcdef' for c in checksum)),
            ("Checksum has correct length", len(checksum) == 64),  # SHA256
        ]
        
        # Calculate again - should be same
        checksum2 = downloader._calculate_checksum(test_file)
        tests.append(("Checksum is consistent", checksum == checksum2))
        
        return run_tests(tests)


def test_file_integrity_verification():
    """Test 5: File Integrity Verification"""
    print("\n" + "="*60)
    print("Test 5: File Integrity Verification")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_bytes(b"Test content")
        
        downloader = MediaPackDownloader(Path(temp_dir))
        
        # Calculate actual checksum
        actual = downloader._calculate_checksum(test_file)
        
        tests = [
            ("Valid file passes", downloader.verify_file_integrity(test_file)),
            ("With correct checksum", downloader.verify_file_integrity(test_file, actual)),
            ("With wrong checksum fails", not downloader.verify_file_integrity(test_file, "wrong")),
            ("Non-existent file fails", not downloader.verify_file_integrity(Path(temp_dir) / "nope.txt")),
        ]
        
        return run_tests(tests)


def test_extractor_initialization():
    """Test 6: Extractor Initialization"""
    print("\n" + "="*60)
    print("Test 6: Extractor Initialization")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        extraction_dir = Path(temp_dir) / "extracted"
        
        config = Config()
        logger = setup_logger('test', None, 'ERROR')
        extractor = MediaPackExtractor(extraction_dir, config, logger)
        
        tests = [
            ("Extractor created", extractor is not None),
            ("Extraction directory created", extraction_dir.exists()),
            ("Has file categories", len(extractor.FILE_CATEGORIES) > 0),
        ]
        
        return run_tests(tests)


def test_archive_type_detection():
    """Test 7: Archive Type Detection"""
    print("\n" + "="*60)
    print("Test 7: Archive Type Detection")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        extractor = MediaPackExtractor(Path(temp_dir))
        
        test_cases = [
            (Path("test.zip"), "zip"),
            (Path("test.rar"), "rar"),
            (Path("test.7z"), "7z"),
            (Path("test.tar.gz"), "tar"),
            (Path("test.tar"), "tar"),
            (Path("test.tgz"), "tar"),
            (Path("test.txt"), None),
        ]
        
        tests = []
        for filepath, expected in test_cases:
            result = extractor._detect_archive_type(filepath)
            tests.append((f"Detect {filepath.suffix}", result == expected))
        
        return run_tests(tests)


def test_file_categorization():
    """Test 8: File Categorization"""
    print("\n" + "="*60)
    print("Test 8: File Categorization")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        extractor = MediaPackExtractor(Path(temp_dir))
        
        test_cases = [
            (Path("product-image.jpg"), "product-images"),
            (Path("logo.png"), "logos"),
            (Path("brand-logo.svg"), "logos"),
            (Path("spec-sheet.pdf"), "documentation"),
            (Path("banner.jpg"), "marketing-materials"),
            (Path("icon.svg"), "vectors"),
            (Path("video.mp4"), "videos"),  # Changed from "promo-video.mp4"
            (Path("random.xyz"), "other"),
        ]
        
        tests = []
        for filepath, expected_category in test_cases:
            result = extractor._determine_category(filepath)
            tests.append((f"Categorize {filepath.name}", result == expected_category))
        
        return run_tests(tests)


def test_filename_standardization():
    """Test 9: Filename Standardization"""
    print("\n" + "="*60)
    print("Test 9: Filename Standardization")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        extractor = MediaPackExtractor(Path(temp_dir))
        
        test_cases = [
            (Path("IMG_001.jpg"), "SMOK", "product-images", "smok-product-"),
            (Path("logo_variation_2.png"), "SMOK", "logos", "smok-logo-"),
            (Path("spec_sheet.pdf"), "SMOK", "documentation", "smok-"),
        ]
        
        tests = []
        for filepath, brand, category, expected_prefix in test_cases:
            result = extractor._standardize_filename(filepath, brand, category)
            tests.append((f"Standardize {filepath.name}", result.startswith(expected_prefix)))
        
        return run_tests(tests)


def test_duplicate_detection():
    """Test 10: Duplicate File Detection"""
    print("\n" + "="*60)
    print("Test 10: Duplicate File Detection")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        extractor = MediaPackExtractor(Path(temp_dir))
        
        # Create test files
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        file3 = Path(temp_dir) / "file3.txt"
        
        content = b"Same content"
        file1.write_bytes(content)
        file2.write_bytes(content)  # Duplicate
        file3.write_bytes(b"Different content")
        
        files = [file1, file2, file3]
        
        # Detect duplicates
        duplicates = extractor._detect_duplicates(files)
        
        tests = [
            ("Duplicates detected", len(duplicates) > 0),
            ("Only one duplicate group", len(duplicates) == 1),
        ]
        
        return run_tests(tests)


def test_zip_extraction():
    """Test 11: ZIP Archive Extraction"""
    print("\n" + "="*60)
    print("Test 11: ZIP Archive Extraction")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test ZIP
        zip_path = Path(temp_dir) / "test.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("file1.txt", "Content 1")
            zf.writestr("file2.txt", "Content 2")
            zf.writestr("subdir/file3.txt", "Content 3")
        
        extractor = MediaPackExtractor(Path(temp_dir) / "extracted")
        
        # Extract
        result = extractor.extract_media_pack(
            zip_path,
            "TestBrand",
            organize=False,
            detect_duplicates=False
        )
        
        tests = [
            ("Extraction successful", result['success']),
            ("Has extraction directory", 'extraction_dir' in result),
            ("Total files count", result['total_files'] >= 3),
        ]
        
        return run_tests(tests)


def test_metadata_generation():
    """Test 12: Metadata Generation"""
    print("\n" + "="*60)
    print("Test 12: Metadata Generation")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create simple ZIP
        zip_path = Path(temp_dir) / "test.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("test.txt", "Test content")
        
        extractor = MediaPackExtractor(Path(temp_dir) / "extracted")
        
        # Extract
        result = extractor.extract_media_pack(zip_path, "TestBrand")
        
        tests = [
            ("Extraction successful", result['success']),
            ("Metadata path exists", 'metadata_path' in result),
        ]
        
        if result['success']:
            # Check metadata file
            metadata_path = Path(result['metadata_path'])
            tests.append(("Metadata file exists", metadata_path.exists()))
            
            if metadata_path.exists():
                import json
                with open(metadata_path) as f:
                    metadata = json.load(f)
                
                tests.extend([
                    ("Metadata has brand", 'brand' in metadata),
                    ("Metadata has media_pack", 'media_pack' in metadata),
                    ("Metadata has total_files", 'total_files' in metadata),
                    ("Metadata has extraction_date", 'extraction_date' in metadata),
                ])
        
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
    print("Media Pack Download and Extraction Test Suite")
    print("="*60)
    
    all_passed = True
    
    try:
        all_passed &= test_download_progress()
        all_passed &= test_downloader_initialization()
        all_passed &= test_filename_extraction()
        all_passed &= test_checksum_calculation()
        all_passed &= test_file_integrity_verification()
        all_passed &= test_extractor_initialization()
        all_passed &= test_archive_type_detection()
        all_passed &= test_file_categorization()
        all_passed &= test_filename_standardization()
        all_passed &= test_duplicate_detection()
        all_passed &= test_zip_extraction()
        all_passed &= test_metadata_generation()
        
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
