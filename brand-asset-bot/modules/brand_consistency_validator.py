"""
Brand Consistency Validator
Validates brand consistency across media from multiple sources
"""

import os
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from PIL import Image
import numpy as np
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class ColorPalette:
    """Represents a color palette"""
    dominant_colors: List[Tuple[int, int, int]]
    color_count: int
    hex_colors: List[str]


@dataclass
class BrandConsistencyReport:
    """Brand consistency validation report"""
    brand_name: str
    total_assets: int
    logo_variations: int
    color_consistency_score: float  # 0-10
    typography_score: float  # 0-10
    overall_consistency_score: float  # 0-10
    
    detected_palettes: List[ColorPalette]
    inconsistencies: List[str]
    warnings: List[str]
    counterfeit_indicators: List[str]
    
    passed_validation: bool


class BrandConsistencyValidator:
    """Validates brand consistency across media assets"""
    
    def __init__(self):
        """Initialize the brand consistency validator"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.brand_palettes = {}  # Store known brand color palettes
    
    def validate_brand_assets(self, brand_name: str, assets_dir: str) -> Optional[BrandConsistencyReport]:
        """
        Validate brand consistency across all assets in a directory
        
        Args:
            brand_name: Name of the brand
            assets_dir: Directory containing brand assets
            
        Returns:
            BrandConsistencyReport or None
        """
        try:
            if not os.path.exists(assets_dir):
                self.logger.error(f"Assets directory not found: {assets_dir}")
                return None
            
            # Collect all images
            images = self._collect_images(assets_dir)
            
            if not images:
                self.logger.warning(f"No images found in {assets_dir}")
                return None
            
            inconsistencies = []
            warnings = []
            counterfeit_indicators = []
            
            # Detect logo variations
            logo_variations = self._detect_logo_variations(images, inconsistencies)
            
            # Extract and validate color palettes
            palettes = self._extract_color_palettes(images)
            color_score = self._validate_color_consistency(palettes, inconsistencies)
            
            # Check for typography (placeholder - requires OCR)
            typography_score = 7.0  # Default score
            
            # Check for counterfeit indicators
            self._detect_counterfeit_indicators(images, brand_name, counterfeit_indicators)
            
            # Calculate overall consistency score
            overall_score = (color_score * 0.6 + typography_score * 0.4)
            
            # Determine if passed validation
            passed = (
                overall_score >= 7.0 and
                len(counterfeit_indicators) == 0 and
                len(inconsistencies) <= 2
            )
            
            report = BrandConsistencyReport(
                brand_name=brand_name,
                total_assets=len(images),
                logo_variations=logo_variations,
                color_consistency_score=round(color_score, 2),
                typography_score=round(typography_score, 2),
                overall_consistency_score=round(overall_score, 2),
                detected_palettes=palettes,
                inconsistencies=inconsistencies,
                warnings=warnings,
                counterfeit_indicators=counterfeit_indicators,
                passed_validation=passed
            )
            
            self.logger.info(f"Brand consistency validation for {brand_name}: {overall_score:.1f}/10")
            return report
            
        except Exception as e:
            self.logger.error(f"Error validating brand assets: {e}")
            return None
    
    def _collect_images(self, directory: str) -> List[str]:
        """Collect all image files from directory"""
        images = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in image_extensions:
                    images.append(os.path.join(root, filename))
        
        return images
    
    def _detect_logo_variations(self, images: List[str], inconsistencies: List[str]) -> int:
        """Detect logo variations across images"""
        # Simplified logo detection - look for files with 'logo' in name
        logo_files = [img for img in images if 'logo' in os.path.basename(img).lower()]
        
        if len(logo_files) > 3:
            inconsistencies.append(f"Multiple logo variations detected ({len(logo_files)} files)")
        
        return len(logo_files)
    
    def _extract_color_palettes(self, images: List[str], max_colors: int = 5) -> List[ColorPalette]:
        """Extract dominant color palettes from images"""
        palettes = []
        
        for image_path in images[:10]:  # Sample first 10 images
            try:
                # Disable PIL size limits to handle large images
                Image.MAX_IMAGE_PIXELS = None
                img = Image.open(image_path)
                img = img.convert('RGB')
                img = img.resize((150, 150))  # Reduce size for faster processing
                
                # Get all colors
                img_array = np.array(img)
                pixels = img_array.reshape(-1, 3)
                
                # Count colors
                colors = [tuple(p) for p in pixels.tolist()]
                color_counts = Counter(colors)
                
                # Get dominant colors
                dominant = color_counts.most_common(max_colors)
                dominant_colors = [color for color, count in dominant]
                hex_colors = [self._rgb_to_hex(color) for color in dominant_colors]
                
                palette = ColorPalette(
                    dominant_colors=dominant_colors,
                    color_count=len(dominant_colors),
                    hex_colors=hex_colors
                )
                palettes.append(palette)
                
            except Exception as e:
                self.logger.warning(f"Error extracting palette from {image_path}: {e}")
        
        return palettes
    
    def _rgb_to_hex(self, rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex color"""
        return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
    
    def _validate_color_consistency(self, palettes: List[ColorPalette], inconsistencies: List[str]) -> float:
        """Validate color consistency across palettes"""
        if len(palettes) < 2:
            return 8.0  # Not enough data, give benefit of doubt
        
        # Collect all dominant colors
        all_colors = []
        for palette in palettes:
            all_colors.extend(palette.dominant_colors)
        
        # Count unique colors
        unique_colors = set(all_colors)
        
        # Check consistency - fewer unique colors indicates better consistency
        consistency_ratio = 1.0 - (len(unique_colors) / (len(all_colors) + 1))
        
        score = 5.0 + (consistency_ratio * 5.0)
        
        if score < 6.0:
            inconsistencies.append("Significant color palette variations detected")
        
        return score
    
    def _detect_counterfeit_indicators(self, images: List[str], brand_name: str, indicators: List[str]):
        """Detect potential counterfeit indicators"""
        # Check for suspicious patterns in filenames
        suspicious_keywords = ['fake', 'replica', 'copy', 'clone', 'knockoff']
        
        for image_path in images:
            filename_lower = os.path.basename(image_path).lower()
            for keyword in suspicious_keywords:
                if keyword in filename_lower:
                    indicators.append(f"Suspicious keyword in filename: {keyword}")
        
        # Additional heuristics could be added:
        # - Watermark detection
        # - Quality inconsistencies
        # - Mismatched branding elements
    
    def register_brand_palette(self, brand_name: str, colors: List[str]):
        """Register official color palette for a brand"""
        self.brand_palettes[brand_name] = colors
        self.logger.info(f"Registered {len(colors)} colors for brand {brand_name}")
    
    def generate_report(self, report: BrandConsistencyReport, output_path: str):
        """Generate brand consistency report"""
        import json
        from datetime import datetime
        
        report_dict = asdict(report)
        report_dict['generated_at'] = datetime.now().isoformat()
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        self.logger.info(f"Brand consistency report saved to {output_path}")
