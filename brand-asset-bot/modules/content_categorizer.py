"""
Content Categorizer
Intelligent categorization and tagging of media assets
"""

import os
import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict
from PIL import Image
import re

logger = logging.getLogger(__name__)


@dataclass
class ContentMetadata:
    """Metadata for categorized content"""
    filename: str
    category: str
    tags: List[str]
    content_type: str
    dimensions: tuple
    file_size: int
    confidence: float  # 0-1


class ContentCategorizer:
    """Intelligently categorizes and tags media content"""
    
    # Content categories
    CATEGORIES = {
        'product': ['product', 'item', 'device', 'kit', 'mod'],
        'lifestyle': ['lifestyle', 'user', 'person', 'vaping', 'using'],
        'technical': ['specs', 'specification', 'diagram', 'schematic', 'manual'],
        'marketing': ['banner', 'promo', 'promotion', 'marketing', 'campaign'],
        'branding': ['logo', 'brand', 'trademark', 'identity']
    }
    
    # Auto-tagging keywords
    TAG_KEYWORDS = {
        'product-shot': ['product', 'white-background', 'isolated'],
        'unboxing': ['box', 'packaging', 'unbox'],
        'comparison': ['vs', 'compare', 'comparison'],
        'infographic': ['info', 'graphic', 'chart', 'diagram'],
        'lifestyle-photo': ['lifestyle', 'person', 'user'],
        'close-up': ['closeup', 'close-up', 'detail', 'macro'],
        'hero-image': ['hero', 'main', 'featured'],
        'thumbnail': ['thumb', 'thumbnail', 'small'],
        'banner': ['banner', 'header', 'cover'],
        'social-media': ['social', 'instagram', 'facebook', 'twitter'],
        'e-liquid': ['liquid', 'juice', 'flavor', 'flavour'],
        'coil': ['coil', 'atomizer', 'head'],
        'battery': ['battery', 'power', 'cell'],
        'pod': ['pod', 'cartridge'],
        'tank': ['tank', 'reservoir'],
        'drip-tip': ['drip', 'tip', 'mouthpiece'],
        'accessories': ['accessory', 'accessories', 'cable', 'charger'],
        'color-variant': ['color', 'colour', 'variant', 'variation'],
        'kit-contents': ['contents', 'includes', 'package'],
        'size-comparison': ['size', 'dimension', 'measurement']
    }
    
    def __init__(self):
        """Initialize the content categorizer"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def categorize_file(self, file_path: str) -> Optional[ContentMetadata]:
        """
        Categorize and tag a single file
        
        Args:
            file_path: Path to file
            
        Returns:
            ContentMetadata or None
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return None
            
            filename = os.path.basename(file_path)
            filename_lower = filename.lower()
            
            # Determine category
            category, category_confidence = self._determine_category(filename_lower)
            
            # Generate tags
            tags = self._generate_tags(filename_lower)
            
            # Determine content type
            content_type = self._determine_content_type(file_path)
            
            # Get file metadata
            dimensions = (0, 0)
            if content_type.startswith('image'):
                try:
                    # Disable PIL size limits to handle large images
                    Image.MAX_IMAGE_PIXELS = None
                    img = Image.open(file_path)
                    dimensions = img.size
                except:
                    pass
            
            file_size = os.path.getsize(file_path)
            
            metadata = ContentMetadata(
                filename=filename,
                category=category,
                tags=tags,
                content_type=content_type,
                dimensions=dimensions,
                file_size=file_size,
                confidence=category_confidence
            )
            
            self.logger.debug(f"Categorized {filename} as '{category}' with {len(tags)} tags")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error categorizing file {file_path}: {e}")
            return None
    
    def _determine_category(self, filename: str) -> tuple:
        """Determine primary category of content"""
        scores = {}
        
        for category, keywords in self.CATEGORIES.items():
            score = 0
            for keyword in keywords:
                if keyword in filename:
                    score += 1
            scores[category] = score
        
        # Find category with highest score
        if scores:
            best_category = max(scores.items(), key=lambda x: x[1])
            if best_category[1] > 0:
                confidence = min(best_category[1] / 3.0, 1.0)
                return best_category[0], confidence
        
        # Default category
        return 'product', 0.5
    
    def _generate_tags(self, filename: str) -> List[str]:
        """Generate tags based on filename and content"""
        tags = []
        
        for tag, keywords in self.TAG_KEYWORDS.items():
            for keyword in keywords:
                if keyword in filename:
                    if tag not in tags:
                        tags.append(tag)
                    break
        
        # Add dimension-based tags
        if any(word in filename for word in ['small', 'mini', 'compact']):
            tags.append('compact-size')
        if any(word in filename for word in ['large', 'big', 'xl']):
            tags.append('large-size')
        
        # Add quality tags
        if any(word in filename for word in ['hd', 'high-res', 'highres', '4k']):
            tags.append('high-resolution')
        
        # Add format tags
        if filename.endswith('.png'):
            tags.append('png-format')
        elif filename.endswith(('.jpg', '.jpeg')):
            tags.append('jpg-format')
        elif filename.endswith('.svg'):
            tags.append('vector-format')
        
        return tags
    
    def _determine_content_type(self, file_path: str) -> str:
        """Determine MIME type of content"""
        ext = os.path.splitext(file_path)[1].lower()
        
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.pdf': 'application/pdf',
            '.ai': 'application/postscript',
            '.eps': 'application/postscript',
            '.psd': 'image/vnd.adobe.photoshop'
        }
        
        return content_types.get(ext, 'application/octet-stream')
    
    def batch_categorize(self, directory: str) -> Dict[str, ContentMetadata]:
        """
        Categorize all files in a directory
        
        Args:
            directory: Directory to process
            
        Returns:
            Dictionary mapping filenames to ContentMetadata
        """
        results = {}
        
        if not os.path.exists(directory):
            self.logger.error(f"Directory not found: {directory}")
            return results
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                metadata = self.categorize_file(file_path)
                if metadata:
                    rel_path = os.path.relpath(file_path, directory)
                    results[rel_path] = metadata
        
        self.logger.info(f"Categorized {len(results)} files in {directory}")
        return results
    
    def generate_catalog(self, metadata_dict: Dict[str, ContentMetadata], output_path: str):
        """Generate content catalog with categorization"""
        import json
        from datetime import datetime
        
        # Group by category
        by_category = {}
        for filename, metadata in metadata_dict.items():
            category = metadata.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(asdict(metadata))
        
        # Generate tag statistics
        all_tags = []
        for metadata in metadata_dict.values():
            all_tags.extend(metadata.tags)
        
        from collections import Counter
        tag_counts = Counter(all_tags)
        
        catalog = {
            'generated_at': datetime.now().isoformat(),
            'total_files': len(metadata_dict),
            'categories': {
                category: len(items)
                for category, items in by_category.items()
            },
            'top_tags': dict(tag_counts.most_common(20)),
            'content_by_category': by_category
        }
        
        with open(output_path, 'w') as f:
            json.dump(catalog, f, indent=2)
        
        self.logger.info(f"Content catalog saved to {output_path}")
        self.logger.info(f"Categories: {', '.join(by_category.keys())}")
    
    def enrich_metadata(self, metadata: ContentMetadata, additional_info: dict) -> ContentMetadata:
        """Enrich metadata with additional information"""
        # This could be extended with:
        # - EXIF data extraction
        # - Color palette extraction
        # - Face detection
        # - Text recognition (OCR)
        # - Object detection
        
        return metadata
