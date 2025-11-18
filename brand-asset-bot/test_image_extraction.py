#!/usr/bin/env python3
"""
Tests for Competitor Image Extraction

Tests image extraction from competitor product pages with quality analysis
and batch downloading capabilities.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path
import tempfile
import shutil

from modules import (
    ImageExtractor, ExtractedImage,
    CompetitorImageDownloader
)


class TestImageExtractor(unittest.TestCase):
    """Test ImageExtractor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.extractor = ImageExtractor()
    
    def test_image_extractor_initialization(self):
        """Test ImageExtractor initializes correctly"""
        self.assertIsNotNone(self.extractor)
        self.assertIsNotNone(self.extractor.session)
    
    def test_get_priority_for_type(self):
        """Test priority assignment for image types"""
        self.assertEqual(self.extractor._get_priority_for_type('gallery'), 'high')
        self.assertEqual(self.extractor._get_priority_for_type('zoom'), 'high')
        self.assertEqual(self.extractor._get_priority_for_type('thumbnails'), 'medium')
        self.assertEqual(self.extractor._get_priority_for_type('other'), 'low')
    
    def test_is_placeholder_or_logo_detection(self):
        """Test placeholder and logo detection"""
        # Placeholder URLs
        self.assertTrue(self.extractor._is_placeholder_or_logo('https://example.com/placeholder.jpg'))
        self.assertTrue(self.extractor._is_placeholder_or_logo('https://example.com/no-image.png'))
        self.assertTrue(self.extractor._is_placeholder_or_logo('https://example.com/loading-spinner.gif'))
        
        # Logo URLs
        self.assertTrue(self.extractor._is_placeholder_or_logo('https://example.com/logo.png'))
        self.assertTrue(self.extractor._is_placeholder_or_logo('https://example.com/brand-icon.svg'))
        
        # Valid product images
        self.assertFalse(self.extractor._is_placeholder_or_logo('https://example.com/product-image.jpg'))
        self.assertFalse(self.extractor._is_placeholder_or_logo('https://example.com/vape-kit-blue.png'))
    
    def test_parse_srcset(self):
        """Test srcset parsing"""
        srcset = "image-300.jpg 300w, image-600.jpg 600w, image-900.jpg 900w"
        urls = self.extractor._parse_srcset(srcset)
        
        self.assertEqual(len(urls), 3)
        self.assertIn('image-300.jpg', urls)
        self.assertIn('image-600.jpg', urls)
        self.assertIn('image-900.jpg', urls)
    
    def test_calculate_quality_score(self):
        """Test quality score calculation"""
        # High quality image
        high_quality = ExtractedImage(
            url='https://example.com/image.jpg',
            image_type='gallery',
            priority='high',
            width=1200,
            height=1200,
            file_size=150000,
            aspect_ratio=1.0
        )
        score = self.extractor._calculate_quality_score(high_quality)
        self.assertGreater(score, 80)
        
        # Low quality image
        low_quality = ExtractedImage(
            url='https://example.com/image.jpg',
            image_type='thumbnail',
            priority='low',
            width=200,
            height=200,
            file_size=5000,
            aspect_ratio=1.0
        )
        score = self.extractor._calculate_quality_score(low_quality)
        self.assertLess(score, 50)
    
    @patch('modules.image_extractor.requests.Session.get')
    def test_extract_images_from_html(self, mock_get):
        """Test image extraction from HTML"""
        html_content = """
        <html>
            <div class="product-gallery">
                <img src="product-main.jpg" alt="Main product" />
                <img src="product-alt-1.jpg" alt="Alternative view" />
            </div>
            <div class="product-thumbnails">
                <img src="thumb-1.jpg" />
                <img src="thumb-2.jpg" />
            </div>
            <img src="placeholder.jpg" />
            <img src="logo.png" />
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = html_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        images = self.extractor.extract_images('https://example.com/product')
        
        # Should extract 4 non-placeholder images
        self.assertGreater(len(images), 0)
        
        # Check that images have required attributes
        for img in images:
            self.assertIsNotNone(img.url)
            self.assertIsNotNone(img.image_type)
            self.assertIsNotNone(img.priority)
    
    def test_filter_quality_images(self):
        """Test quality filtering"""
        images = [
            ExtractedImage(url='img1.jpg', image_type='gallery', priority='high', quality_score=80),
            ExtractedImage(url='img2.jpg', image_type='thumbnail', priority='low', quality_score=30),
            ExtractedImage(url='img3.jpg', image_type='zoom', priority='high', quality_score=90),
            ExtractedImage(url='img4.jpg', image_type='carousel', priority='medium', quality_score=45),
        ]
        
        # Filter with min quality 50
        filtered = self.extractor.filter_quality_images(images, min_quality=50, analyze=False)
        
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].url, 'img1.jpg')
        self.assertEqual(filtered[1].url, 'img3.jpg')
    
    def test_get_best_images(self):
        """Test getting best images"""
        images = [
            ExtractedImage(url='img1.jpg', image_type='gallery', priority='high', 
                         quality_score=80, is_high_res=True),
            ExtractedImage(url='img2.jpg', image_type='thumbnail', priority='low', 
                         quality_score=90, is_high_res=False),
            ExtractedImage(url='img3.jpg', image_type='zoom', priority='high', 
                         quality_score=70, is_high_res=True),
        ]
        
        # Get best 2 images with high-res preference
        best = self.extractor.get_best_images(images, max_images=2, prefer_high_res=True)
        
        self.assertEqual(len(best), 2)
        # High-res images should be preferred
        self.assertTrue(best[0].is_high_res)


class TestCompetitorImageDownloader(unittest.TestCase):
    """Test CompetitorImageDownloader functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = CompetitorImageDownloader(base_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_downloader_initialization(self):
        """Test downloader initializes correctly"""
        self.assertIsNotNone(self.downloader)
        self.assertEqual(self.downloader.base_dir, self.temp_dir)
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        self.assertEqual(self.downloader._sanitize_filename('SMOK Novo 5'), 'smok-novo-5')
        self.assertEqual(self.downloader._sanitize_filename('Test@Product#123'), 'testproduct123')
        self.assertEqual(self.downloader._sanitize_filename('Multiple   Spaces'), 'multiple-spaces')
    
    def test_get_file_extension(self):
        """Test file extension detection"""
        self.assertEqual(self.downloader._get_file_extension('https://example.com/image.jpg'), '.jpg')
        self.assertEqual(self.downloader._get_file_extension('https://example.com/photo.png'), '.png')
        self.assertEqual(self.downloader._get_file_extension('https://example.com/pic.webp'), '.webp')
        
        # Test with content type
        self.assertEqual(self.downloader._get_file_extension('https://example.com/image', 
                                                            'image/png'), '.png')
    
    def test_create_brand_directory(self):
        """Test brand directory creation"""
        brand_dir = self.downloader._create_brand_directory('SMOK', 'Vape UK')
        
        self.assertTrue(brand_dir.exists())
        self.assertTrue(brand_dir.is_dir())
        self.assertIn('smok', str(brand_dir))
        self.assertIn('vape-uk', str(brand_dir))
    
    @patch('modules.competitor_image_downloader.requests.Session.get')
    def test_download_product_images(self, mock_get):
        """Test product image downloading"""
        # Create unique mock responses for each image
        call_count = [0]
        
        def side_effect_func(*args, **kwargs):
            call_count[0] += 1
            mock_response = Mock()
            # Different content for each image to avoid duplicate detection
            mock_response.content = f'fake_image_data_{call_count[0]}'.encode()
            mock_response.headers = {'content-type': 'image/jpeg'}
            mock_response.raise_for_status = Mock()
            return mock_response
        
        mock_get.side_effect = side_effect_func
        
        images = [
            ExtractedImage(url='https://example.com/img1.jpg', image_type='gallery', 
                         priority='high', quality_score=80, width=800, height=800),
            ExtractedImage(url='https://example.com/img2.jpg', image_type='zoom', 
                         priority='high', quality_score=90, width=1200, height=1200),
        ]
        
        metadata = self.downloader.download_product_images(
            brand='SMOK',
            product_name='Novo 5 Kit',
            images=images,
            competitor_site='Vape UK',
            max_images=2
        )
        
        self.assertEqual(metadata['brand'], 'SMOK')
        self.assertEqual(metadata['product_name'], 'Novo 5 Kit')
        self.assertEqual(metadata['total_images'], 2)
        self.assertEqual(metadata['downloaded'], 2)
        
        # Check files were created
        brand_dir = Path(self.temp_dir) / 'smok' / 'vape-uk'
        self.assertTrue(brand_dir.exists())
        
        # Check metadata file exists
        metadata_file = brand_dir / 'novo-5-kit-metadata.json'
        self.assertTrue(metadata_file.exists())
    
    def test_get_download_summary(self):
        """Test download summary generation"""
        # Create some test files
        brand_dir = Path(self.temp_dir) / 'smok' / 'vape-uk'
        brand_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test image files
        (brand_dir / 'test-01.jpg').write_bytes(b'test_data_1')
        (brand_dir / 'test-02.jpg').write_bytes(b'test_data_2')
        
        summary = self.downloader.get_download_summary()
        
        self.assertEqual(summary['total_brands'], 1)
        self.assertEqual(summary['total_images'], 2)
        self.assertIn('smok', summary['brands'])


class TestImageExtractionIntegration(unittest.TestCase):
    """Integration tests for image extraction workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = CompetitorImageDownloader(base_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('modules.competitor_image_downloader.requests.Session.get')
    def test_complete_extraction_workflow(self, mock_download_get):
        """Test complete extraction and download workflow"""
        # Create mock images directly (skip extraction for this test)
        images = [
            ExtractedImage(
                url='https://example.com/product-1.jpg',
                image_type='gallery',
                priority='high',
                quality_score=80,
                width=800,
                height=800
            ),
            ExtractedImage(
                url='https://example.com/product-2.jpg',
                image_type='zoom',
                priority='high',
                quality_score=90,
                width=1200,
                height=1200
            )
        ]
        
        # Mock image download with unique content for each
        call_count = [0]
        
        def side_effect_func(*args, **kwargs):
            call_count[0] += 1
            mock_download_response = Mock()
            mock_download_response.content = f'fake_image_data_{call_count[0]}'.encode()
            mock_download_response.headers = {'content-type': 'image/jpeg'}
            mock_download_response.raise_for_status = Mock()
            return mock_download_response
        
        mock_download_get.side_effect = side_effect_func
        
        # Download images
        metadata = self.downloader.download_product_images(
            brand='TestBrand',
            product_name='Test Product',
            images=images,
            competitor_site='Test Site',
            max_images=5
        )
        
        self.assertGreater(metadata['downloaded'], 0)
        self.assertEqual(metadata['brand'], 'TestBrand')


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestImageExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestCompetitorImageDownloader))
    suite.addTests(loader.loadTestsFromTestCase(TestImageExtractionIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    import sys
    sys.exit(run_tests())
