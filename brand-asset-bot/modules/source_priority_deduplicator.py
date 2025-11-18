"""
Source priority-based deduplication module for selecting best media versions.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import IntEnum
import json


class SourcePriority(IntEnum):
    """Source priority levels (lower number = higher priority)"""
    OFFICIAL_BRAND = 1
    AUTHORIZED_DISTRIBUTOR = 2
    MAJOR_COMPETITOR = 3
    OTHER_SOURCE = 4


@dataclass
class MediaAsset:
    """Media asset with source and quality information"""
    asset_id: str
    source: str
    source_priority: int
    file_path: str
    quality_score: float  # 0.0-10.0
    file_size: int
    dimensions: Optional[tuple]
    metadata: Dict


@dataclass
class DeduplicationResult:
    """Result of deduplication process"""
    selected_asset: MediaAsset
    duplicate_assets: List[MediaAsset]
    selection_reason: str
    stats: Dict


class SourcePriorityDeduplicator:
    """Deduplicates media assets based on source priority and quality"""
    
    def __init__(self):
        self.source_priorities = {
            'official_brand': SourcePriority.OFFICIAL_BRAND,
            'authorized_distributor': SourcePriority.AUTHORIZED_DISTRIBUTOR,
            'major_competitor': SourcePriority.MAJOR_COMPETITOR,
            'other': SourcePriority.OTHER_SOURCE
        }
        
        # Quality thresholds for selection
        self.quality_thresholds = {
            SourcePriority.OFFICIAL_BRAND: 5.0,  # Accept anything 5.0+
            SourcePriority.AUTHORIZED_DISTRIBUTOR: 6.0,
            SourcePriority.MAJOR_COMPETITOR: 7.0,
            SourcePriority.OTHER_SOURCE: 8.0
        }
    
    def deduplicate_assets(self, assets: List[MediaAsset]) -> DeduplicationResult:
        """
        Deduplicate media assets by selecting best version.
        
        Args:
            assets: List of duplicate MediaAsset objects
            
        Returns:
            DeduplicationResult with selected asset and duplicates
        """
        if not assets:
            raise ValueError("No assets provided for deduplication")
        
        if len(assets) == 1:
            return DeduplicationResult(
                selected_asset=assets[0],
                duplicate_assets=[],
                selection_reason="Only one version available",
                stats={'total_versions': 1, 'duplicates_removed': 0}
            )
        
        # Sort by priority (lower number first), then by quality (higher first)
        sorted_assets = sorted(
            assets,
            key=lambda a: (a.source_priority, -a.quality_score)
        )
        
        # Select based on priority hierarchy
        selected = self._select_best_asset(sorted_assets)
        duplicates = [a for a in sorted_assets if a.asset_id != selected.asset_id]
        
        reason = self._get_selection_reason(selected, sorted_assets)
        
        stats = {
            'total_versions': len(assets),
            'duplicates_removed': len(duplicates),
            'priority_levels': len(set(a.source_priority for a in assets)),
            'quality_range': (
                min(a.quality_score for a in assets),
                max(a.quality_score for a in assets)
            )
        }
        
        return DeduplicationResult(
            selected_asset=selected,
            duplicate_assets=duplicates,
            selection_reason=reason,
            stats=stats
        )
    
    def _select_best_asset(self, sorted_assets: List[MediaAsset]) -> MediaAsset:
        """Select best asset based on priority and quality"""
        # Group by priority level
        priority_groups = {}
        for asset in sorted_assets:
            priority = asset.source_priority
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(asset)
        
        # Check each priority level in order
        for priority in sorted([SourcePriority.OFFICIAL_BRAND, 
                               SourcePriority.AUTHORIZED_DISTRIBUTOR,
                               SourcePriority.MAJOR_COMPETITOR,
                               SourcePriority.OTHER_SOURCE]):
            if priority in priority_groups:
                candidates = priority_groups[priority]
                threshold = self.quality_thresholds[priority]
                
                # Find assets meeting quality threshold
                qualified = [a for a in candidates if a.quality_score >= threshold]
                
                if qualified:
                    # Return highest quality from this priority level
                    return max(qualified, key=lambda a: a.quality_score)
        
        # Fallback: return highest quality overall
        return max(sorted_assets, key=lambda a: a.quality_score)
    
    def _get_selection_reason(self, selected: MediaAsset, all_assets: List[MediaAsset]) -> str:
        """Generate human-readable selection reason"""
        priority_name = self._get_priority_name(selected.source_priority)
        
        # Check if selected purely by priority
        higher_priority = [a for a in all_assets 
                          if a.source_priority < selected.source_priority]
        
        if not higher_priority:
            if selected.quality_score >= self.quality_thresholds[selected.source_priority]:
                return f"Selected from {priority_name} (highest priority, quality {selected.quality_score:.1f}/10)"
            else:
                return f"Selected from {priority_name} (best available quality {selected.quality_score:.1f}/10)"
        
        # Selected based on quality within priority level
        same_priority = [a for a in all_assets 
                        if a.source_priority == selected.source_priority]
        if len(same_priority) > 1:
            return f"Selected from {priority_name} (highest quality {selected.quality_score:.1f}/10 in priority level)"
        
        return f"Selected from {priority_name} (quality {selected.quality_score:.1f}/10)"
    
    def _get_priority_name(self, priority: int) -> str:
        """Get human-readable priority name"""
        names = {
            SourcePriority.OFFICIAL_BRAND: "official brand media",
            SourcePriority.AUTHORIZED_DISTRIBUTOR: "authorized distributor",
            SourcePriority.MAJOR_COMPETITOR: "major competitor",
            SourcePriority.OTHER_SOURCE: "other source"
        }
        return names.get(priority, "unknown source")
    
    def batch_deduplicate(self, asset_groups: Dict[str, List[MediaAsset]]) -> Dict[str, DeduplicationResult]:
        """
        Deduplicate multiple groups of assets.
        
        Args:
            asset_groups: Dict mapping product IDs to lists of duplicate assets
            
        Returns:
            Dict mapping product IDs to DeduplicationResult objects
        """
        results = {}
        
        for product_id, assets in asset_groups.items():
            if assets:
                results[product_id] = self.deduplicate_assets(assets)
        
        return results
    
    def generate_report(self, results: Dict[str, DeduplicationResult]) -> Dict:
        """Generate deduplication report"""
        total_assets = sum(r.stats['total_versions'] for r in results.values())
        total_removed = sum(r.stats['duplicates_removed'] for r in results.values())
        
        # Count by source priority
        priority_counts = {
            'official_brand': 0,
            'authorized_distributor': 0,
            'major_competitor': 0,
            'other': 0
        }
        
        for result in results.values():
            priority = result.selected_asset.source_priority
            if priority == SourcePriority.OFFICIAL_BRAND:
                priority_counts['official_brand'] += 1
            elif priority == SourcePriority.AUTHORIZED_DISTRIBUTOR:
                priority_counts['authorized_distributor'] += 1
            elif priority == SourcePriority.MAJOR_COMPETITOR:
                priority_counts['major_competitor'] += 1
            else:
                priority_counts['other'] += 1
        
        return {
            'summary': {
                'total_products': len(results),
                'total_asset_versions': total_assets,
                'duplicates_removed': total_removed,
                'deduplication_rate': f"{(total_removed / total_assets * 100):.1f}%" if total_assets > 0 else "0%"
            },
            'selected_by_priority': priority_counts,
            'products_processed': list(results.keys())
        }
    
    def classify_source(self, source_name: str) -> int:
        """
        Classify a source into a priority level.
        
        Args:
            source_name: Name of the source
            
        Returns:
            Priority level (1-4)
        """
        source_lower = source_name.lower()
        
        # Official brand indicators
        if any(term in source_lower for term in ['official', 'brand', 'manufacturer']):
            return SourcePriority.OFFICIAL_BRAND
        
        # Authorized distributor indicators
        if any(term in source_lower for term in ['authorized', 'distributor', 'wholesale']):
            return SourcePriority.AUTHORIZED_DISTRIBUTOR
        
        # Major competitor indicators
        if any(term in source_lower for term in ['vape uk', 'vape superstore', 'vapourism', 
                                                   'ecigarette direct', 'competitor']):
            return SourcePriority.MAJOR_COMPETITOR
        
        # Default to other
        return SourcePriority.OTHER_SOURCE
