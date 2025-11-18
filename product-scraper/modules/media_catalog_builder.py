"""
Media catalog builder for creating unified catalogs from multiple sources.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime
import json
import os


@dataclass
class CatalogProduct:
    """Product entry in unified catalog"""
    product_id: str
    name: str
    brand: str
    model_number: Optional[str]
    category: str
    primary_source: str
    source_count: int
    media_assets: List[Dict]
    quality_scores: Dict[str, float]
    metadata: Dict


@dataclass
class CatalogStats:
    """Statistics for unified catalog"""
    total_products: int
    total_assets: int
    duplicates_removed: int
    source_breakdown: Dict[str, int]
    category_breakdown: Dict[str, int]
    quality_metrics: Dict


class MediaCatalogBuilder:
    """Builds unified media catalogs from multiple sources"""
    
    def __init__(self, output_dir: str = "data/unified_catalog"):
        """
        Initialize catalog builder.
        
        Args:
            output_dir: Directory for catalog output
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def build_catalog(self, unified_products: List, 
                     deduplication_results: Dict,
                     quality_assessments: Optional[Dict] = None) -> Dict:
        """
        Build unified media catalog from integrated data.
        
        Args:
            unified_products: List of UnifiedProduct objects from ProductMatcher
            deduplication_results: Results from SourcePriorityDeduplicator
            quality_assessments: Optional quality scores from ImageQualityAssessor
            
        Returns:
            Catalog dictionary
        """
        catalog_products = []
        
        for product in unified_products:
            # Get media assets for this product
            assets = []
            quality_scores = {}
            
            # Check deduplication results
            if product.product_id in deduplication_results:
                dedup_result = deduplication_results[product.product_id]
                selected_asset = dedup_result.selected_asset
                
                assets.append({
                    'asset_id': selected_asset.asset_id,
                    'file_path': selected_asset.file_path,
                    'source': selected_asset.source,
                    'quality_score': selected_asset.quality_score,
                    'dimensions': selected_asset.dimensions,
                    'file_size': selected_asset.file_size,
                    'is_primary': True
                })
                
                quality_scores['primary'] = selected_asset.quality_score
                
                # Add alternate versions if quality is good
                for dup_asset in dedup_result.duplicate_assets:
                    if dup_asset.quality_score >= 7.0:  # Only high-quality alternates
                        assets.append({
                            'asset_id': dup_asset.asset_id,
                            'file_path': dup_asset.file_path,
                            'source': dup_asset.source,
                            'quality_score': dup_asset.quality_score,
                            'dimensions': dup_asset.dimensions,
                            'file_size': dup_asset.file_size,
                            'is_primary': False
                        })
            
            # Add quality assessments if available
            if quality_assessments and product.product_id in quality_assessments:
                quality_data = quality_assessments[product.product_id]
                quality_scores.update(quality_data)
            
            catalog_product = CatalogProduct(
                product_id=product.product_id,
                name=product.name,
                brand=product.brand,
                model_number=product.model_number,
                category=product.metadata.get('categories', ['unknown'])[0],
                primary_source=product.primary_source,
                source_count=len(product.sources),
                media_assets=assets,
                quality_scores=quality_scores,
                metadata={
                    'sources': product.sources,
                    'match_score': product.match_score,
                    'last_updated': datetime.now().isoformat()
                }
            )
            
            catalog_products.append(catalog_product)
        
        # Generate statistics
        stats = self._generate_stats(catalog_products, deduplication_results)
        
        catalog = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'version': '1.0',
                'total_products': len(catalog_products)
            },
            'statistics': asdict(stats),
            'products': [asdict(p) for p in catalog_products]
        }
        
        return catalog
    
    def _generate_stats(self, products: List[CatalogProduct], 
                       dedup_results: Dict) -> CatalogStats:
        """Generate statistics for catalog"""
        total_assets = sum(len(p.media_assets) for p in products)
        
        # Count duplicates removed
        duplicates_removed = sum(
            r.stats['duplicates_removed'] 
            for r in dedup_results.values()
        )
        
        # Source breakdown
        source_breakdown = {}
        for product in products:
            source = product.primary_source
            source_breakdown[source] = source_breakdown.get(source, 0) + 1
        
        # Category breakdown
        category_breakdown = {}
        for product in products:
            category = product.category
            category_breakdown[category] = category_breakdown.get(category, 0) + 1
        
        # Quality metrics
        all_quality_scores = []
        for product in products:
            if product.media_assets:
                primary_asset = next(
                    (a for a in product.media_assets if a.get('is_primary')), 
                    product.media_assets[0]
                )
                all_quality_scores.append(primary_asset['quality_score'])
        
        quality_metrics = {
            'average_quality': (
                sum(all_quality_scores) / len(all_quality_scores) 
                if all_quality_scores else 0.0
            ),
            'min_quality': min(all_quality_scores) if all_quality_scores else 0.0,
            'max_quality': max(all_quality_scores) if all_quality_scores else 0.0,
            'high_quality_count': len([s for s in all_quality_scores if s >= 8.0]),
            'medium_quality_count': len([s for s in all_quality_scores if 6.0 <= s < 8.0]),
            'low_quality_count': len([s for s in all_quality_scores if s < 6.0])
        }
        
        return CatalogStats(
            total_products=len(products),
            total_assets=total_assets,
            duplicates_removed=duplicates_removed,
            source_breakdown=source_breakdown,
            category_breakdown=category_breakdown,
            quality_metrics=quality_metrics
        )
    
    def save_catalog(self, catalog: Dict, filename: str = "unified_catalog.json") -> str:
        """
        Save catalog to JSON file.
        
        Args:
            catalog: Catalog dictionary
            filename: Output filename
            
        Returns:
            Path to saved catalog file
        """
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def load_catalog(self, filename: str = "unified_catalog.json") -> Dict:
        """
        Load catalog from JSON file.
        
        Args:
            filename: Catalog filename
            
        Returns:
            Catalog dictionary
        """
        catalog_path = os.path.join(self.output_dir, filename)
        
        if not os.path.exists(catalog_path):
            raise FileNotFoundError(f"Catalog not found: {catalog_path}")
        
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        
        return catalog
    
    def filter_catalog(self, catalog: Dict, 
                      brand: Optional[str] = None,
                      category: Optional[str] = None,
                      min_quality: Optional[float] = None,
                      source: Optional[str] = None) -> Dict:
        """
        Filter catalog by various criteria.
        
        Args:
            catalog: Catalog dictionary
            brand: Filter by brand name
            category: Filter by category
            min_quality: Minimum quality score
            source: Filter by primary source
            
        Returns:
            Filtered catalog dictionary
        """
        products = catalog['products']
        filtered = products
        
        if brand:
            filtered = [p for p in filtered if p['brand'].lower() == brand.lower()]
        
        if category:
            filtered = [p for p in filtered if p['category'].lower() == category.lower()]
        
        if min_quality is not None:
            filtered = [
                p for p in filtered 
                if p['media_assets'] and 
                any(a['quality_score'] >= min_quality for a in p['media_assets'])
            ]
        
        if source:
            filtered = [p for p in filtered if p['primary_source'].lower() == source.lower()]
        
        # Create filtered catalog
        filtered_catalog = {
            'metadata': {
                **catalog['metadata'],
                'filtered': True,
                'filters_applied': {
                    'brand': brand,
                    'category': category,
                    'min_quality': min_quality,
                    'source': source
                }
            },
            'statistics': {
                'total_products': len(filtered),
                'original_count': len(products)
            },
            'products': filtered
        }
        
        return filtered_catalog
    
    def generate_summary_report(self, catalog: Dict) -> str:
        """Generate human-readable summary report"""
        stats = catalog.get('statistics', {})
        
        report_lines = [
            "=" * 60,
            "UNIFIED MEDIA CATALOG SUMMARY",
            "=" * 60,
            "",
            f"Generated: {catalog['metadata'].get('generated_at', 'Unknown')}",
            "",
            "OVERVIEW:",
            f"  Total Products: {stats.get('total_products', 0)}",
            f"  Total Media Assets: {stats.get('total_assets', 0)}",
            f"  Duplicates Removed: {stats.get('duplicates_removed', 0)}",
            "",
            "SOURCE DISTRIBUTION:"
        ]
        
        source_breakdown = stats.get('source_breakdown', {})
        for source, count in sorted(source_breakdown.items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {source}: {count} products")
        
        report_lines.append("")
        report_lines.append("CATEGORY DISTRIBUTION:")
        
        category_breakdown = stats.get('category_breakdown', {})
        for category, count in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {category}: {count} products")
        
        report_lines.append("")
        report_lines.append("QUALITY METRICS:")
        
        quality = stats.get('quality_metrics', {})
        report_lines.extend([
            f"  Average Quality: {quality.get('average_quality', 0):.2f}/10",
            f"  Quality Range: {quality.get('min_quality', 0):.1f} - {quality.get('max_quality', 0):.1f}",
            f"  High Quality (8.0+): {quality.get('high_quality_count', 0)} products",
            f"  Medium Quality (6.0-8.0): {quality.get('medium_quality_count', 0)} products",
            f"  Low Quality (<6.0): {quality.get('low_quality_count', 0)} products",
            "",
            "=" * 60
        ])
        
        return "\n".join(report_lines)
