"""
Image Quality Assessor
Evaluates technical quality metrics of product images
"""

import os
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from PIL import Image
import numpy as np
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Quality assessment metrics for an image"""
    resolution_score: float  # 0-10
    sharpness_score: float   # 0-10
    color_score: float       # 0-10
    compression_score: float # 0-10
    background_score: float  # 0-10
    overall_score: float     # 0-10
    
    width: int
    height: int
    file_size: int
    is_blur: bool
    is_low_res: bool
    has_artifacts: bool
    has_clean_background: bool
    color_mode: str
    
    passed_quality: bool
    issues: list


class ImageQualityAssessor:
    """Assesses technical quality of product images"""
    
    # Quality thresholds
    MIN_RESOLUTION = 400
    OPTIMAL_RESOLUTION = 800
    HIGH_RES_RESOLUTION = 1200
    MIN_FILE_SIZE = 10 * 1024  # 10KB
    BLUR_THRESHOLD = 100.0  # Laplacian variance threshold
    
    # Scoring weights
    WEIGHTS = {
        'resolution': 0.30,
        'sharpness': 0.25,
        'color': 0.20,
        'compression': 0.15,
        'background': 0.10
    }
    
    def __init__(self):
        """Initialize the quality assessor"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def assess_image(self, image_path: str) -> Optional[QualityMetrics]:
        """
        Assess overall quality of an image
        
        Args:
            image_path: Path to image file
            
        Returns:
            QualityMetrics object or None if assessment fails
        """
        try:
            if not os.path.exists(image_path):
                self.logger.error(f"Image not found: {image_path}")
                return None
            
            # Open image
            img = Image.open(image_path)
            width, height = img.size
            file_size = os.path.getsize(image_path)
            color_mode = img.mode
            
            issues = []
            
            # Assess individual metrics
            resolution_score = self._assess_resolution(width, height, issues)
            sharpness_score, is_blur = self._assess_sharpness(img, issues)
            color_score = self._assess_color(img, issues)
            compression_score, has_artifacts = self._assess_compression(img, file_size, issues)
            background_score, has_clean_bg = self._assess_background(img, issues)
            
            # Calculate overall score
            overall_score = (
                resolution_score * self.WEIGHTS['resolution'] +
                sharpness_score * self.WEIGHTS['sharpness'] +
                color_score * self.WEIGHTS['color'] +
                compression_score * self.WEIGHTS['compression'] +
                background_score * self.WEIGHTS['background']
            )
            
            # Check if passed quality thresholds
            is_low_res = width < self.MIN_RESOLUTION or height < self.MIN_RESOLUTION
            passed_quality = overall_score >= 6.0 and not is_low_res and not is_blur
            
            metrics = QualityMetrics(
                resolution_score=round(resolution_score, 2),
                sharpness_score=round(sharpness_score, 2),
                color_score=round(color_score, 2),
                compression_score=round(compression_score, 2),
                background_score=round(background_score, 2),
                overall_score=round(overall_score, 2),
                width=width,
                height=height,
                file_size=file_size,
                is_blur=is_blur,
                is_low_res=is_low_res,
                has_artifacts=has_artifacts,
                has_clean_background=has_clean_bg,
                color_mode=color_mode,
                passed_quality=passed_quality,
                issues=issues
            )
            
            self.logger.info(f"Quality assessment for {os.path.basename(image_path)}: {overall_score:.1f}/10")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error assessing image {image_path}: {e}")
            return None
    
    def _assess_resolution(self, width: int, height: int, issues: list) -> float:
        """Assess image resolution quality (0-10 score)"""
        min_dimension = min(width, height)
        
        if min_dimension < self.MIN_RESOLUTION:
            issues.append(f"Low resolution: {width}x{height}")
            return 1.0
        elif min_dimension < self.OPTIMAL_RESOLUTION:
            # Linear scale between MIN and OPTIMAL (score 5-7)
            ratio = (min_dimension - self.MIN_RESOLUTION) / (self.OPTIMAL_RESOLUTION - self.MIN_RESOLUTION)
            return 5.0 + (ratio * 2.0)
        elif min_dimension < self.HIGH_RES_RESOLUTION:
            # Linear scale between OPTIMAL and HIGH_RES (score 7-9)
            ratio = (min_dimension - self.OPTIMAL_RESOLUTION) / (self.HIGH_RES_RESOLUTION - self.OPTIMAL_RESOLUTION)
            return 7.0 + (ratio * 2.0)
        else:
            # High resolution
            return 10.0
    
    def _assess_sharpness(self, img: Image, issues: list) -> Tuple[float, bool]:
        """Assess image sharpness using Laplacian variance"""
        try:
            # Convert to grayscale for sharpness detection
            gray = img.convert('L')
            img_array = np.array(gray)
            
            # Calculate Laplacian variance (blur detection)
            laplacian = np.array([
                [0, 1, 0],
                [1, -4, 1],
                [0, 1, 0]
            ])
            
            # Simple convolution approximation
            variance = np.var(img_array)
            
            # Blur detection
            is_blur = variance < self.BLUR_THRESHOLD
            
            if is_blur:
                issues.append("Image appears blurry")
                return 3.0, True
            elif variance < self.BLUR_THRESHOLD * 2:
                return 6.0, False
            elif variance < self.BLUR_THRESHOLD * 3:
                return 8.0, False
            else:
                return 10.0, False
                
        except Exception as e:
            self.logger.warning(f"Error assessing sharpness: {e}")
            return 5.0, False
    
    def _assess_color(self, img: Image, issues: list) -> float:
        """Assess color profile and accuracy"""
        mode = img.mode
        
        if mode == 'RGB':
            return 10.0
        elif mode == 'RGBA':
            return 9.0  # Slightly lower for transparency
        elif mode == 'L':
            issues.append("Grayscale image (no color)")
            return 5.0
        elif mode == 'CMYK':
            issues.append("CMYK color mode (should be RGB)")
            return 6.0
        else:
            issues.append(f"Unusual color mode: {mode}")
            return 4.0
    
    def _assess_compression(self, img: Image, file_size: int, issues: list) -> Tuple[float, bool]:
        """Assess compression quality and detect artifacts"""
        width, height = img.size
        pixel_count = width * height
        
        # Calculate bytes per pixel
        if pixel_count > 0:
            bytes_per_pixel = file_size / pixel_count
        else:
            bytes_per_pixel = 0
        
        # Detect over-compression
        has_artifacts = False
        if bytes_per_pixel < 0.5:
            has_artifacts = True
            issues.append("Heavy compression detected (possible artifacts)")
            return 4.0, True
        elif bytes_per_pixel < 1.0:
            return 7.0, False
        elif bytes_per_pixel < 2.0:
            return 9.0, False
        else:
            return 10.0, False
    
    def _assess_background(self, img: Image, issues: list) -> Tuple[float, bool]:
        """Assess background quality and uniformity"""
        try:
            # Sample edges to detect background
            img_array = np.array(img.convert('RGB'))
            height, width = img_array.shape[:2]
            
            # Sample top, bottom, left, right edges
            edge_pixels = []
            edge_pixels.extend(img_array[0, :].tolist())  # Top
            edge_pixels.extend(img_array[-1, :].tolist())  # Bottom
            edge_pixels.extend(img_array[:, 0].tolist())  # Left
            edge_pixels.extend(img_array[:, -1].tolist())  # Right
            
            # Check uniformity of edge pixels
            # Convert to tuples for counting
            edge_pixels_tuples = [tuple(p) for p in edge_pixels]
            color_counts = Counter(edge_pixels_tuples)
            
            # If dominant color covers >70% of edges, likely uniform background
            if color_counts:
                most_common_count = color_counts.most_common(1)[0][1]
                uniformity_ratio = most_common_count / len(edge_pixels_tuples)
                
                if uniformity_ratio > 0.7:
                    # Check if it's white/light background (preferred)
                    most_common_color = color_counts.most_common(1)[0][0]
                    avg_brightness = sum(most_common_color) / 3
                    
                    if avg_brightness > 240:
                        return 10.0, True
                    elif avg_brightness > 200:
                        return 8.0, True
                    else:
                        return 7.0, True
                else:
                    issues.append("Non-uniform background")
                    return 5.0, False
            
            return 6.0, False
            
        except Exception as e:
            self.logger.warning(f"Error assessing background: {e}")
            return 5.0, False
    
    def batch_assess(self, image_dir: str) -> Dict[str, QualityMetrics]:
        """
        Assess quality of all images in a directory
        
        Args:
            image_dir: Directory containing images
            
        Returns:
            Dictionary mapping filenames to QualityMetrics
        """
        results = {}
        
        if not os.path.exists(image_dir):
            self.logger.error(f"Directory not found: {image_dir}")
            return results
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        for filename in os.listdir(image_dir):
            file_path = os.path.join(image_dir, filename)
            
            if os.path.isfile(file_path):
                ext = os.path.splitext(filename)[1].lower()
                if ext in image_extensions:
                    metrics = self.assess_image(file_path)
                    if metrics:
                        results[filename] = metrics
        
        self.logger.info(f"Assessed {len(results)} images in {image_dir}")
        return results
    
    def generate_report(self, metrics_dict: Dict[str, QualityMetrics], output_path: str):
        """Generate quality assessment report"""
        import json
        from datetime import datetime
        
        # Calculate statistics
        total_images = len(metrics_dict)
        passed = sum(1 for m in metrics_dict.values() if m.passed_quality)
        failed = total_images - passed
        
        avg_score = sum(m.overall_score for m in metrics_dict.values()) / total_images if total_images > 0 else 0
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_images': total_images,
            'passed_quality': passed,
            'failed_quality': failed,
            'pass_rate': f"{(passed/total_images*100):.1f}%" if total_images > 0 else "0%",
            'average_score': round(avg_score, 2),
            'images': {
                filename: asdict(metrics)
                for filename, metrics in metrics_dict.items()
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Quality report saved to {output_path}")
        self.logger.info(f"Pass rate: {report['pass_rate']}, Average score: {report['average_score']}/10")
