#!/usr/bin/env python3
"""
Tests for cross-source integration and deduplication modules.
"""

import unittest
from unittest.mock import Mock, patch
from modules.product_matcher import ProductMatcher, ProductMatch, UnifiedProduct
from modules.source_priority_deduplicator import (
    SourcePriorityDeduplicator, MediaAsset, DeduplicationResult, SourcePriority
)
from modules.image_similarity_detector import ImageSimilarityDetector, ImageHash, SimilarityMatch
from modules.media_catalog_builder import MediaCatalogBuilder, CatalogProduct


class TestProductMatcher(unittest.TestCase):
    """Test ProductMatcher functionality"""
    
    def setUp(self):
        self.matcher = ProductMatcher()
    
    def test_exact_name_matching(self):
        """Test exact product name matching"""
        p1 = {'title': 'SMOK NOVO 5 Vape Kit', 'brand': 'SMOK'}
        p2 = {'title': 'Smok Novo 5 Vape Kit', 'brand': 'SMOK'}
        
        score = self.matcher._match_exact_name(p1, p2)
        self.assertGreater(score, 0.95)
    
    def test_brand_model_matching(self):
        """Test brand + model number matching"""
        p1 = {'title': 'SMOK NOVO 5', 'brand': 'SMOK'}
        p2 = {'title': 'Smok Novo V5 Kit', 'brand': 'SMOK'}
        
        score = self.matcher._match_brand_model(p1, p2)
        self.assertGreater(score, 0.70)
    
    def test_extract_model_number(self):
        """Test model number extraction"""
        # Test various patterns
        self.assertEqual(self.matcher._extract_model_number('SMOK NOVO 5'), 'NOVO 5')
        self.assertEqual(self.matcher._extract_model_number('Vaporesso XROS-3 Pod Kit'), 'XROS-3')
        self.assertIsNotNone(self.matcher._extract_model_number('20mg Nic Salt'))
    
    def test_match_products(self):
        """Test matching products between two sources"""
        products_1 = [
            {'id': '1', 'title': 'SMOK NOVO 5', 'brand': 'SMOK', 'url': 'url1'},
            {'id': '2', 'title': 'Vaporesso XROS 3', 'brand': 'Vaporesso', 'url': 'url2'}
        ]
        products_2 = [
            {'id': '3', 'title': 'Smok Novo V5 Kit', 'brand': 'SMOK', 'url': 'url3'},
            {'id': '4', 'title': 'Vaporesso Xros 3 Pod', 'brand': 'Vaporesso', 'url': 'url4'}
        ]
        
        matches = self.matcher.match_products(products_1, products_2, 'source1', 'source2')
        
        self.assertEqual(len(matches), 2)
        self.assertIsInstance(matches[0], ProductMatch)
        self.assertGreater(matches[0].match_score, 0.70)
    
    def test_confidence_levels(self):
        """Test confidence level determination"""
        self.assertEqual(self.matcher._get_confidence_level(0.95), "high")
        self.assertEqual(self.matcher._get_confidence_level(0.80), "medium")
        self.assertEqual(self.matcher._get_confidence_level(0.72), "low")


class TestSourcePriorityDeduplicator(unittest.TestCase):
    """Test SourcePriorityDeduplicator functionality"""
    
    def setUp(self):
        self.deduplicator = SourcePriorityDeduplicator()
    
    def test_priority_classification(self):
        """Test source priority classification"""
        self.assertEqual(
            self.deduplicator.classify_source('official brand media'),
            SourcePriority.OFFICIAL_BRAND
        )
        self.assertEqual(
            self.deduplicator.classify_source('vape uk competitor'),
            SourcePriority.MAJOR_COMPETITOR
        )
        self.assertEqual(
            self.deduplicator.classify_source('unknown source'),
            SourcePriority.OTHER_SOURCE
        )
    
    def test_deduplicate_by_priority(self):
        """Test deduplication based on source priority"""
        assets = [
            MediaAsset('asset1', 'competitor', 3, '/path1', 8.5, 1000, None, {}),
            MediaAsset('asset2', 'official', 1, '/path2', 7.0, 2000, None, {}),
            MediaAsset('asset3', 'other', 4, '/path3', 9.0, 1500, None, {})
        ]
        
        result = self.deduplicator.deduplicate_assets(assets)
        
        self.assertIsInstance(result, DeduplicationResult)
        # Official should be selected despite lower quality
        self.assertEqual(result.selected_asset.source, 'official')
        self.assertEqual(len(result.duplicate_assets), 2)
    
    def test_quality_within_priority(self):
        """Test quality selection within same priority level"""
        assets = [
            MediaAsset('asset1', 'competitor1', 3, '/path1', 8.0, 1000, None, {}),
            MediaAsset('asset2', 'competitor2', 3, '/path2', 9.5, 2000, None, {})
        ]
        
        result = self.deduplicator.deduplicate_assets(assets)
        
        # Higher quality within same priority should be selected
        self.assertEqual(result.selected_asset.asset_id, 'asset2')
        self.assertEqual(result.selected_asset.quality_score, 9.5)
    
    def test_single_asset(self):
        """Test deduplication with single asset"""
        assets = [MediaAsset('asset1', 'source', 2, '/path', 7.5, 1000, None, {})]
        
        result = self.deduplicator.deduplicate_assets(assets)
        
        self.assertEqual(result.selected_asset.asset_id, 'asset1')
        self.assertEqual(len(result.duplicate_assets), 0)
        self.assertEqual(result.stats['duplicates_removed'], 0)
    
    def test_batch_deduplicate(self):
        """Test batch deduplication"""
        asset_groups = {
            'product1': [
                MediaAsset('a1', 'source1', 1, '/p1', 8.0, 1000, None, {}),
                MediaAsset('a2', 'source2', 2, '/p2', 9.0, 2000, None, {})
            ],
            'product2': [
                MediaAsset('a3', 'source1', 1, '/p3', 7.0, 1500, None, {})
            ]
        }
        
        results = self.deduplicator.batch_deduplicate(asset_groups)
        
        self.assertEqual(len(results), 2)
        self.assertIn('product1', results)
        self.assertIn('product2', results)
    
    def test_generate_report(self):
        """Test deduplication report generation"""
        results = {
            'product1': DeduplicationResult(
                selected_asset=MediaAsset('a1', 'official', 1, '/p1', 8.0, 1000, None, {}),
                duplicate_assets=[MediaAsset('a2', 'competitor', 3, '/p2', 7.0, 1000, None, {})],
                selection_reason="test",
                stats={'total_versions': 2, 'duplicates_removed': 1}
            )
        }
        
        report = self.deduplicator.generate_report(results)
        
        self.assertIn('summary', report)
        self.assertIn('selected_by_priority', report)
        self.assertEqual(report['summary']['total_products'], 1)
        self.assertEqual(report['summary']['duplicates_removed'], 1)


class TestImageSimilarityDetector(unittest.TestCase):
    """Test ImageSimilarityDetector functionality"""
    
    def setUp(self):
        self.detector = ImageSimilarityDetector(hash_size=8, similarity_threshold=0.90)
    
    def test_compute_hash(self):
        """Test image hash computation"""
        hash_obj = self.detector.compute_image_hash('/path/to/image.jpg', 'source1')
        
        self.assertIsInstance(hash_obj, ImageHash)
        self.assertEqual(hash_obj.image_path, '/path/to/image.jpg')
        self.assertEqual(hash_obj.source, 'source1')
        self.assertEqual(hash_obj.hash_bits, 64)
    
    def test_hamming_distance(self):
        """Test Hamming distance calculation"""
        hash1 = self.detector.compute_image_hash('/path1.jpg', 'source1')
        hash2 = self.detector.compute_image_hash('/path1.jpg', 'source2')  # Same path = similar hash
        
        distance = self.detector.calculate_hamming_distance(hash1, hash2)
        
        # Same image should have 0 distance
        self.assertEqual(distance, 0)
    
    def test_similarity_score(self):
        """Test similarity score calculation"""
        hash1 = self.detector.compute_image_hash('/path1.jpg', 'source1')
        hash2 = self.detector.compute_image_hash('/path1.jpg', 'source2')
        
        similarity = self.detector.calculate_similarity(hash1, hash2)
        
        # Identical images should have similarity = 1.0
        self.assertEqual(similarity, 1.0)
    
    def test_find_similar_images(self):
        """Test finding similar images"""
        hashes = [
            self.detector.compute_image_hash('/img1.jpg', 'source1'),
            self.detector.compute_image_hash('/img1.jpg', 'source2'),  # Duplicate
            self.detector.compute_image_hash('/img2.jpg', 'source1')
        ]
        
        matches = self.detector.find_similar_images(hashes)
        
        self.assertIsInstance(matches, list)
        if matches:
            self.assertIsInstance(matches[0], SimilarityMatch)
    
    def test_find_duplicates(self):
        """Test duplicate grouping"""
        hashes = [
            self.detector.compute_image_hash('/img1.jpg', 'source1'),
            self.detector.compute_image_hash('/img1.jpg', 'source2'),
            self.detector.compute_image_hash('/img2.jpg', 'source1')
        ]
        
        duplicates = self.detector.find_duplicates(hashes)
        
        self.assertIsInstance(duplicates, dict)
    
    def test_cross_source_detection(self):
        """Test cross-source duplicate detection"""
        images_by_source = {
            'source1': ['/img1.jpg', '/img2.jpg'],
            'source2': ['/img1.jpg', '/img3.jpg']  # img1 is duplicate
        }
        
        matches = self.detector.detect_near_duplicates(images_by_source, similarity_threshold=0.99)
        
        self.assertIsInstance(matches, list)
    
    def test_similarity_report(self):
        """Test similarity report generation"""
        matches = [
            SimilarityMatch('/img1.jpg', '/img2.jpg', 'src1', 'src2', 0.95, 3, True),
            SimilarityMatch('/img3.jpg', '/img4.jpg', 'src1', 'src3', 0.75, 16, False)
        ]
        
        report = self.detector.generate_similarity_report(matches)
        
        self.assertIn('summary', report)
        self.assertIn('cross_source_duplicates', report)
        self.assertEqual(report['summary']['total_matches'], 2)


class TestMediaCatalogBuilder(unittest.TestCase):
    """Test MediaCatalogBuilder functionality"""
    
    def setUp(self):
        self.builder = MediaCatalogBuilder(output_dir='/tmp/test_catalog')
    
    def test_build_catalog(self):
        """Test catalog building"""
        unified_products = [
            Mock(
                product_id='prod1',
                name='Test Product',
                brand='TestBrand',
                model_number='V1',
                sources=[{'source': 'official', 'url': 'url1'}],
                primary_source='official',
                match_score=0.95,
                metadata={'categories': ['vape-kits']}
            )
        ]
        
        dedup_results = {
            'prod1': Mock(
                selected_asset=Mock(
                    asset_id='asset1',
                    file_path='/path',
                    source='official',
                    quality_score=8.5,
                    dimensions=(800, 800),
                    file_size=50000
                ),
                duplicate_assets=[],
                stats={'total_versions': 1, 'duplicates_removed': 0}
            )
        }
        
        catalog = self.builder.build_catalog(unified_products, dedup_results)
        
        self.assertIn('metadata', catalog)
        self.assertIn('statistics', catalog)
        self.assertIn('products', catalog)
        self.assertEqual(catalog['metadata']['total_products'], 1)
    
    def test_filter_catalog(self):
        """Test catalog filtering"""
        catalog = {
            'metadata': {},
            'products': [
                {'brand': 'SMOK', 'category': 'vape-kits', 'media_assets': [{'quality_score': 8.0}]},
                {'brand': 'Vaporesso', 'category': 'pods', 'media_assets': [{'quality_score': 6.0}]}
            ]
        }
        
        # Filter by brand
        filtered = self.builder.filter_catalog(catalog, brand='SMOK')
        self.assertEqual(len(filtered['products']), 1)
        
        # Filter by quality
        filtered = self.builder.filter_catalog(catalog, min_quality=7.0)
        self.assertEqual(len(filtered['products']), 1)
    
    def test_summary_report(self):
        """Test summary report generation"""
        catalog = {
            'metadata': {'generated_at': '2024-01-01'},
            'statistics': {
                'total_products': 10,
                'total_assets': 25,
                'duplicates_removed': 5,
                'source_breakdown': {'official': 6, 'competitor': 4},
                'category_breakdown': {'vape-kits': 7, 'pods': 3},
                'quality_metrics': {
                    'average_quality': 7.5,
                    'min_quality': 5.0,
                    'max_quality': 9.5,
                    'high_quality_count': 4,
                    'medium_quality_count': 5,
                    'low_quality_count': 1
                }
            }
        }
        
        report = self.builder.generate_summary_report(catalog)
        
        self.assertIsInstance(report, str)
        self.assertIn('UNIFIED MEDIA CATALOG SUMMARY', report)
        self.assertIn('Total Products: 10', report)
        self.assertIn('QUALITY METRICS', report)


if __name__ == '__main__':
    # Run tests
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*60)
