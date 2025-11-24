"""
Brand Asset Scraper Module
Main orchestrator for the brand asset discovery pipeline
"""
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json

from .brand_manager import BrandManager, Brand
from .media_pack_discovery import MediaPackDiscovery
from .media_pack_downloader import MediaPackDownloader
from .media_pack_extractor import MediaPackExtractor
from .competitor_site_manager import CompetitorSiteManager
from .product_discovery import ProductDiscovery
from .image_extractor import ImageExtractor
from .content_categorizer import ContentCategorizer
from .image_quality_assessor import ImageQualityAssessor
from .brand_consistency_validator import BrandConsistencyValidator
from .source_priority_deduplicator import SourcePriorityDeduplicator
from .media_catalog_builder import MediaCatalogBuilder
from .shopify_exporter import ShopifyExporter


class BrandAssetScraper:
    """Main orchestrator for brand asset discovery and processing"""

    def __init__(self, config, logger):
        """
        Initialize brand asset scraper
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger

        # Initialize components
        self.brand_manager = BrandManager(logger=logger)
        
        # Load brands from brands.txt if it exists
        brands_file = Path("brands.txt")
        if brands_file.exists():
            brands, errors = self.brand_manager.load_brands_from_file(brands_file)
            for brand in brands:
                self.brand_manager.add_brand(brand)
            if errors:
                self.logger.warning(f"Errors loading brands: {errors}")
            self.logger.info(f"Loaded {len(brands)} brands from {brands_file}")
        else:
            self.logger.warning("No brands.txt file found. Brands must be added manually.")
        
        self.media_pack_discovery = MediaPackDiscovery(config, logger)
        self.media_pack_downloader = MediaPackDownloader(
            download_dir=config.output_dir / "downloads", config=config, logger=logger
        )
        self.media_pack_extractor = MediaPackExtractor(
            extraction_dir=config.output_dir / "extracted", config=config, logger=logger
        )
        self.competitor_manager = CompetitorSiteManager(
            registry_file=config.data_dir / "competitor_sites.json", logger=logger
        )
        self.product_discovery = ProductDiscovery()
        self.image_extractor = ImageExtractor()
        self.content_categorizer = ContentCategorizer()
        self.quality_assessor = ImageQualityAssessor()
        self.consistency_validator = BrandConsistencyValidator()
        self.deduplicator = SourcePriorityDeduplicator()
        self.catalog_builder = MediaCatalogBuilder(output_dir=str(config.output_dir / "catalog"))
        self.shopify_exporter = ShopifyExporter(config, logger)

    def discover_brand_assets(self, brand_name: str, include_competitors: bool = True, uk_only: bool = False) -> Dict:
        """
        Discover and collect brand assets from official and competitor sources

        Args:
            brand_name: Name of the brand to discover assets for
            include_competitors: Whether to include competitor sources
            uk_only: If True, only discover UK-specific media packs

        Returns:
            dict: Discovery results with assets and metadata
        """
        self.logger.info(f"Starting brand asset discovery for: {brand_name}")

        results = {
            'brand': brand_name,
            'timestamp': datetime.now().isoformat(),
            'official_assets': [],
            'competitor_assets': [],
            'catalog_stats': {},
            'errors': []
        }

        try:
            # Get brand information
            brand = self.brand_manager.get_brand(brand_name)
            if not brand:
                raise ValueError(f"Brand '{brand_name}' not found in registry")

            # Discover official media packs
            self.logger.info("Discovering official media packs...")
            media_packs = self.media_pack_discovery.discover_media_packs(brand_name, brand.website, uk_only)

            for pack_info in media_packs:
                try:
                    # Download and extract media pack
                    download_result = self.media_pack_downloader.download_media_pack(pack_info.url, brand_name)
                    if download_result:
                        extracted_result = self.media_pack_extractor.extract_media_pack(
                            Path(download_result['filepath']), brand_name
                        )
                        
                        if extracted_result['success']:
                            # Get all image files from extraction directory
                            import glob
                            extraction_dir = Path(extracted_result['extraction_dir'])
                            extracted_assets = []
                            for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
                                extracted_assets.extend(extraction_dir.rglob(ext))
                            
                            # Process extracted assets
                            for asset_path in extracted_assets:
                                asset_data = self._process_asset(str(asset_path), 'official_brand', brand_name)
                                if asset_data:
                                    results['official_assets'].append(asset_data)
                
                except Exception as e:
                    self.logger.error(f"Error processing media pack {pack_info.url}: {e}")
                    results['errors'].append(f"Media pack error: {str(e)}")

            # Discover competitor assets if requested
            if include_competitors:
                self.logger.info("Discovering competitor assets...")
                # TODO: Implement competitor asset discovery
                results['competitor_assets'] = []
                # competitor_assets = self._discover_competitor_assets(brand_name)
                # results['competitor_assets'] = competitor_assets

            # Build unified catalog
            self.logger.info("Processing assets...")
            all_assets = results['official_assets'] + results['competitor_assets']
            # TODO: Implement full catalog building with deduplication
            results['catalog_stats'] = {
                'total_official': len(results['official_assets']),
                'total_competitor': len(results['competitor_assets']),
                'total_assets': len(all_assets)
            }

            self.logger.info(f"Discovery completed. Found {len(all_assets)} total assets")

        except Exception as e:
            self.logger.error(f"Error during brand asset discovery: {e}")
            results['errors'].append(f"Discovery error: {str(e)}")

        return results

    # def _discover_competitor_assets(self, brand_name: str) -> List[Dict]:
    #     """
    #     Discover assets from competitor websites

    #     Args:
    #     brand_name: Brand name to search for

    #     Returns:
    #         list: List of competitor assets
    #     """
    #     assets = []

    #     # Get competitor sites
    #     competitor_sites = self.competitor_manager.get_sites_for_brand(brand_name)

    #     for site in competitor_sites:
    #         try:
    #             # Discover products on competitor site
    #             products = self.product_discovery.discover_products(site, brand_name)

    #             for product in products:
    #                 try:
    #                     # Extract marketing images from product page
    #                     extracted_images = self.image_extractor.extract_images(product.url)

    #                     # Filter for high-quality marketing images
    #                     marketing_images = [
    #                         img for img in extracted_images
    #                         if img.priority == 'high' and not img.is_placeholder
    #                     ]

    #                     for image in marketing_images:
    #                         asset_data = self._process_asset(
    #                             image.url, 'competitor', brand_name,
    #                             source_url=product.url, metadata={'product_title': product.title}
    #                         )
    #                         if asset_data:
    #                             assets.append(asset_data)

    #                 except Exception as e:
    #                     self.logger.error(f"Error extracting images from {product.url}: {e}")

    #         except Exception as e:
    #             self.logger.error(f"Error processing competitor site {site.url}: {e}")

    #     return assets

    def _process_asset(self, asset_path_or_url: str, source_type: str, brand_name: str,
                      source_url: Optional[str] = None, metadata: Optional[Dict] = None) -> Optional[Dict]:
        """
        Process a single asset through quality validation and categorization

        Args:
            asset_path_or_url: Path to asset file or URL
            source_type: Type of source (official_brand, competitor, etc.)
            brand_name: Brand name
            source_url: Source URL if applicable
            metadata: Additional metadata

        Returns:
            dict: Processed asset data or None if invalid
        """
        try:
            # Assess quality
            quality_metrics = self.quality_assessor.assess_image(asset_path_or_url)

            # Categorize content
            content_metadata = self.content_categorizer.categorize_file(asset_path_or_url)

            # For now, skip brand consistency validation
            consistency_score = None

            # Create asset record
            asset_data = {
                'asset_id': f"{brand_name}_{source_type}_{hash(asset_path_or_url)}",
                'source': source_type,
                'source_url': source_url,
                'file_path': asset_path_or_url,
                'quality_score': quality_metrics.overall_score if quality_metrics else 0,
                'category': content_metadata.category if content_metadata else 'unknown',
                'tags': content_metadata.tags if content_metadata else [],
                'dimensions': content_metadata.dimensions if content_metadata else (0, 0),
                'file_size': content_metadata.file_size if content_metadata else 0,
                'brand_consistency': consistency_score,
                'metadata': metadata or {},
                'processed_at': datetime.now().isoformat()
            }

            return asset_data

        except Exception as e:
            self.logger.error(f"Error processing asset {asset_path_or_url}: {e}")
            return None

    def export_brand_catalog(self, brand_name: str, export_format: str = 'json') -> Optional[str]:
        """
        Export comprehensive brand catalog with all extracted assets

        Args:
            brand_name: Brand name
            export_format: Export format (json, etc.)

        Returns:
            str: Path to exported file or None if failed
        """
        try:
            # Generate timestamp for filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.config.output_dir / f"brand_assets_{brand_name}_{timestamp}.json"

            # Get brand information
            brand = self.brand_manager.get_brand(brand_name)
            if not brand:
                self.logger.warning(f"Brand '{brand_name}' not found in registry")

            # Scan extracted assets
            extracted_dir = self.config.output_dir / "extracted" / brand_name
            catalog_assets = []
            total_files = 0

            if extracted_dir.exists():
                self.logger.info(f"Scanning extracted assets in: {extracted_dir}")

                # Find all image files
                image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp', '*.bmp', '*.tiff']

                for ext in image_extensions:
                    for asset_path in extracted_dir.rglob(ext):
                        total_files += 1
                        try:
                            # Process asset through quality and categorization
                            asset_data = self._process_asset(
                                str(asset_path),
                                'official_brand',
                                brand_name
                            )

                            if asset_data:
                                # Add additional metadata
                                asset_data.update({
                                    'relative_path': str(asset_path.relative_to(extracted_dir)),
                                    'absolute_path': str(asset_path),
                                    'file_exists': asset_path.exists(),
                                    'file_modified': datetime.fromtimestamp(asset_path.stat().st_mtime).isoformat() if asset_path.exists() else None,
                                })
                                catalog_assets.append(asset_data)

                        except Exception as e:
                            self.logger.warning(f"Error processing asset {asset_path}: {e}")
                            continue

                self.logger.info(f"Processed {len(catalog_assets)}/{total_files} assets for catalog")
            else:
                self.logger.warning(f"Extracted directory not found: {extracted_dir}")

            # Calculate catalog statistics
            catalog_stats = {
                'total_assets': len(catalog_assets),
                'categories': {},
                'quality_distribution': {'high': 0, 'medium': 0, 'low': 0},
                'file_types': {},
                'source_types': {}
            }

            # Analyze assets for statistics
            for asset in catalog_assets:
                # Category breakdown
                category = asset.get('category', 'unknown')
                catalog_stats['categories'][category] = catalog_stats['categories'].get(category, 0) + 1

                # Quality distribution
                quality = asset.get('quality_score', 0)
                if quality >= 0.8:
                    catalog_stats['quality_distribution']['high'] += 1
                elif quality >= 0.6:
                    catalog_stats['quality_distribution']['medium'] += 1
                else:
                    catalog_stats['quality_distribution']['low'] += 1

                # File type breakdown
                file_ext = asset.get('relative_path', '').split('.')[-1].lower() if '.' in asset.get('relative_path', '') else 'unknown'
                catalog_stats['file_types'][file_ext] = catalog_stats['file_types'].get(file_ext, 0) + 1

                # Source type breakdown
                source = asset.get('source', 'unknown')
                catalog_stats['source_types'][source] = catalog_stats['source_types'].get(source, 0) + 1

            # Create comprehensive catalog data
            catalog_data = {
                'brand': brand_name,
                'brand_info': {
                    'name': brand.name if brand else brand_name,
                    'website': brand.website if brand else None,
                    'priority': brand.priority if brand else 'unknown'
                } if brand else None,
                'exported_at': datetime.now().isoformat(),
                'export_timestamp': timestamp,
                'extraction_directory': str(extracted_dir),
                'assets': catalog_assets,
                'statistics': catalog_stats,
                'processing_summary': {
                    'total_files_scanned': total_files,
                    'assets_processed': len(catalog_assets),
                    'processing_errors': total_files - len(catalog_assets)
                }
            }

            # Write catalog to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(catalog_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Brand catalog exported: {output_file}")
            self.logger.info(f"Catalog contains {len(catalog_assets)} assets across {len(catalog_stats['categories'])} categories")

            return str(output_file)

        except Exception as e:
            self.logger.error(f"Error exporting brand catalog: {e}", exc_info=True)
            return None