#!/usr/bin/env python3
"""
Integration Tests for Brand Asset Bot
End-to-end testing of brand asset discovery pipeline
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from modules import Config, setup_logger, BrandAssetScraper, BrandManager


class TestBrandAssetIntegration(unittest.TestCase):
    """Integration tests for brand asset discovery"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.logger = setup_logger('test', None, 'DEBUG')

        # Create temporary directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config.output_dir = self.temp_dir / "output"
        self.config.download_dir = self.temp_dir / "downloads"
        self.config.extracted_dir = self.temp_dir / "extracted"

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('modules.media_pack_discovery.MediaPackDiscovery.discover_media_packs')
    @patch('modules.media_pack_downloader.MediaPackDownloader.download_media_pack')
    @patch('modules.media_pack_extractor.MediaPackExtractor.extract_media_pack')
    def test_brand_asset_discovery_pipeline(self, mock_extract, mock_download, mock_discover):
        """Test the complete brand asset discovery pipeline"""
        # Mock media pack discovery
        mock_discover.return_value = [
            Mock(url="https://example.com/media-pack.zip", file_type="zip")
        ]

        # Mock download result
        mock_download.return_value = {"filepath": "/tmp/test.zip", "success": True}

        # Mock extraction result with fake extracted files
        mock_extract.return_value = {
            "success": True,
            "extraction_dir": "/tmp/extracted",
            "extracted_files": ["/tmp/extracted/image1.jpg", "/tmp/extracted/image2.png"]
        }

        # Initialize scraper
        scraper = BrandAssetScraper(self.config, self.logger)

        # Add test brand to registry
        from modules.brand_manager import Brand
        test_brand = Brand(name="TestBrand", website="https://testbrand.com", priority="high")
        scraper.brand_manager.add_brand(test_brand)

        # Mock the glob operation to return fake extracted files only for .jpg pattern
        def mock_rglob(pattern):
            if pattern == '*.jpg':
                return [
                    Path("/tmp/extracted/image1.jpg"),
                    Path("/tmp/extracted/image2.jpg")
                ]
            else:
                return []
        
        with patch('pathlib.Path.rglob', side_effect=mock_rglob):
            
            # Mock the _process_asset method to avoid file operations
            with patch.object(scraper, '_process_asset') as mock_process:
                mock_process.return_value = {
                    'asset_id': 'test_asset_001',
                    'source': 'official_brand',
                    'category': 'marketing',
                    'quality_score': 8.5,
                    'tags': ['hero-image'],
                    'dimensions': (1920, 1080),
                    'file_size': 2048000
                }

                # Run discovery
                results = scraper.discover_brand_assets("TestBrand", include_competitors=False)

                # Assertions
                self.assertEqual(results['brand'], 'TestBrand')
                self.assertIn('official_assets', results)
                self.assertIn('catalog_stats', results)
                self.assertEqual(len(results['official_assets']), 2)  # Should have 2 assets now

                # Verify the asset was processed twice
                self.assertEqual(mock_process.call_count, 2)

    def test_brand_manager_integration(self):
        """Test brand manager integration"""
        brand_manager = BrandManager(logger=self.logger)

        # Test brand creation
        from modules.brand_manager import Brand
        test_brand = Brand(
            name="Test Vape Brand",
            website="https://test-vape-brand.com",
            priority="high"
        )

        # Test brand storage and retrieval
        success = brand_manager.add_brand(test_brand)
        self.assertTrue(success)

        retrieved = brand_manager.get_brand("Test Vape Brand")
        self.assertIsNotNone(retrieved)
        if retrieved:
            self.assertEqual(retrieved.name, "Test Vape Brand")
            self.assertEqual(retrieved.website, "https://test-vape-brand.com")

    def test_content_categorization(self):
        """Test content categorization functionality"""
        from modules.content_categorizer import ContentCategorizer

        categorizer = ContentCategorizer()

        # Test categorization (would need actual image file in real test)
        # For now, just test initialization
        self.assertIsInstance(categorizer, ContentCategorizer)

    def test_image_quality_assessment(self):
        """Test image quality assessment"""
        from modules.image_quality_assessor import ImageQualityAssessor

        assessor = ImageQualityAssessor()

        # Test initialization
        self.assertIsInstance(assessor, ImageQualityAssessor)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)