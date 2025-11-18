"""
Image Extractor Module

Extracts product images from competitor websites with quality analysis
and dynamic image handling.
"""

import re
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

from .logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ExtractedImage:
    """Represents an extracted image with metadata"""
    url: str
    image_type: str  # gallery, thumbnail, zoom, carousel, alternative
    priority: str  # high, medium, low
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    aspect_ratio: Optional[float] = None
    quality_score: int = 0  # 0-100
    is_high_res: bool = False
    is_placeholder: bool = False
    source_selector: Optional[str] = None
    discovered_at: Optional[str] = None


class ImageExtractor:
    """Extracts and analyzes product images from competitor websites"""
    
    # CSS selectors for different image types
    IMAGE_SELECTORS = {
        'gallery': [
            '.product-gallery img',
            '.product-image-gallery img',
            '.product-photos img',
            '.gallery-image img',
            '[data-gallery] img',
            '.main-image img',
            '.product-main-image img',
        ],
        'thumbnails': [
            '.product-thumbnails img',
            '.product-thumb img',
            '.thumbnail-list img',
            '.thumbs img',
            '[data-thumbnail] img',
        ],
        'zoom': [
            '[data-zoom-image]',
            '[data-large-image]',
            '[data-full-image]',
            '.zoom-image',
            '[data-zoom]',
        ],
        'carousel': [
            '.carousel img',
            '.slider img',
            '.swiper-slide img',
            '.product-carousel img',
            '[data-carousel] img',
        ],
        'alternative': [
            '.product-image img',
            '.product-media img',
            '.media-gallery img',
            'picture img',
            '[data-role="gallery"] img',
        ]
    }
    
    # Patterns to detect placeholder images
    PLACEHOLDER_PATTERNS = [
        r'placeholder',
        r'no-image',
        r'default',
        r'loading',
        r'spinner',
        r'1x1',
        r'blank',
        r'dummy',
    ]
    
    # Patterns to detect logo images
    LOGO_PATTERNS = [
        r'logo',
        r'brand-icon',
        r'watermark',
    ]
    
    # Minimum quality thresholds
    MIN_WIDTH = 400
    MIN_HEIGHT = 400
    MIN_FILE_SIZE = 10240  # 10KB
    HIGH_RES_WIDTH = 800
    HIGH_RES_HEIGHT = 800
    
    def __init__(self, user_agent: Optional[str] = None):
        """
        Initialize image extractor
        
        Args:
            user_agent: User agent string for requests
        """
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
    
    def extract_images(self, product_url: str, timeout: int = 30) -> List[ExtractedImage]:
        """
        Extract all product images from a product page
        
        Args:
            product_url: URL of product page
            timeout: Request timeout in seconds
            
        Returns:
            List of ExtractedImage objects
        """
        try:
            logger.info(f"Extracting images from: {product_url}")
            
            # Fetch page content
            response = self.session.get(product_url, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            images = []
            seen_urls = set()
            
            # Extract images by type
            for image_type, selectors in self.IMAGE_SELECTORS.items():
                priority = self._get_priority_for_type(image_type)
                
                for selector in selectors:
                    elements = soup.select(selector)
                    
                    for element in elements:
                        image_urls = self._extract_image_urls(element, product_url)
                        
                        for img_url in image_urls:
                            if img_url and img_url not in seen_urls:
                                seen_urls.add(img_url)
                                
                                # Create extracted image
                                extracted = ExtractedImage(
                                    url=img_url,
                                    image_type=image_type,
                                    priority=priority,
                                    source_selector=selector,
                                    discovered_at=time.strftime("%Y-%m-%d %H:%M:%S")
                                )
                                
                                # Check if placeholder
                                if self._is_placeholder_or_logo(img_url):
                                    extracted.is_placeholder = True
                                    extracted.quality_score = 0
                                else:
                                    images.append(extracted)
            
            logger.info(f"Extracted {len(images)} images (excluding {len(seen_urls) - len(images)} placeholders/logos)")
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images from {product_url}: {e}")
            return []
    
    def _extract_image_urls(self, element, base_url: str) -> List[str]:
        """Extract image URLs from an element"""
        urls = []
        
        # Check various attributes for image URLs
        attrs_to_check = [
            'src',
            'data-src',
            'data-lazy',
            'data-lazy-src',
            'data-original',
            'data-zoom-image',
            'data-large-image',
            'data-full-image',
            'data-srcset',
            'srcset',
        ]
        
        for attr in attrs_to_check:
            value = element.get(attr)
            if value:
                # Handle srcset (multiple URLs)
                if attr in ['srcset', 'data-srcset']:
                    srcset_urls = self._parse_srcset(value)
                    urls.extend([urljoin(base_url, url) for url in srcset_urls])
                else:
                    urls.append(urljoin(base_url, value))
        
        # Check for URLs in style attribute
        style = element.get('style')
        if style:
            url_match = re.search(r'url\([\'"]?([^\'"]+)[\'"]?\)', style)
            if url_match:
                urls.append(urljoin(base_url, url_match.group(1)))
        
        return urls
    
    def _parse_srcset(self, srcset: str) -> List[str]:
        """Parse srcset attribute to extract URLs"""
        urls = []
        parts = srcset.split(',')
        
        for part in parts:
            part = part.strip()
            # Extract URL (everything before size descriptor)
            url_match = re.match(r'([^\s]+)', part)
            if url_match:
                urls.append(url_match.group(1))
        
        return urls
    
    def _get_priority_for_type(self, image_type: str) -> str:
        """Get priority level for image type"""
        high_priority = ['gallery', 'zoom', 'carousel']
        medium_priority = ['thumbnails', 'alternative']
        
        if image_type in high_priority:
            return 'high'
        elif image_type in medium_priority:
            return 'medium'
        else:
            return 'low'
    
    def _is_placeholder_or_logo(self, url: str) -> bool:
        """Check if image URL indicates a placeholder or logo"""
        url_lower = url.lower()
        
        # Check placeholder patterns
        for pattern in self.PLACEHOLDER_PATTERNS:
            if re.search(pattern, url_lower):
                return True
        
        # Check logo patterns
        for pattern in self.LOGO_PATTERNS:
            if re.search(pattern, url_lower):
                return True
        
        return False
    
    def analyze_image_quality(self, image: ExtractedImage, fetch_metadata: bool = True) -> ExtractedImage:
        """
        Analyze image quality and update metadata
        
        Args:
            image: ExtractedImage to analyze
            fetch_metadata: Whether to fetch actual image file for analysis
            
        Returns:
            Updated ExtractedImage with quality metrics
        """
        try:
            if fetch_metadata:
                # Fetch image file
                response = self.session.get(image.url, timeout=10, stream=True)
                response.raise_for_status()
                
                # Get file size
                image.file_size = int(response.headers.get('content-length', 0))
                
                # Load image and get dimensions
                img_data = BytesIO(response.content)
                with Image.open(img_data) as img:
                    image.width, image.height = img.size
                    
                    # Calculate aspect ratio
                    if image.height > 0:
                        image.aspect_ratio = image.width / image.height
            
            # Calculate quality score
            image.quality_score = self._calculate_quality_score(image)
            
            # Check if high resolution
            if image.width and image.height:
                image.is_high_res = (image.width >= self.HIGH_RES_WIDTH and 
                                    image.height >= self.HIGH_RES_HEIGHT)
            
            logger.debug(f"Analyzed image: {image.url[:50]}... Quality: {image.quality_score}")
            
        except Exception as e:
            logger.warning(f"Error analyzing image {image.url}: {e}")
            image.quality_score = 50  # Default medium quality
        
        return image
    
    def _calculate_quality_score(self, image: ExtractedImage) -> int:
        """Calculate quality score (0-100) based on image metrics"""
        score = 0
        
        # Resolution score (0-40 points)
        if image.width and image.height:
            min_dimension = min(image.width, image.height)
            if min_dimension >= self.HIGH_RES_WIDTH:
                score += 40
            elif min_dimension >= self.MIN_WIDTH:
                score += 20 + int((min_dimension - self.MIN_WIDTH) / (self.HIGH_RES_WIDTH - self.MIN_WIDTH) * 20)
            else:
                score += int(min_dimension / self.MIN_WIDTH * 20)
        
        # File size score (0-20 points)
        if image.file_size:
            if image.file_size >= 100000:  # 100KB+
                score += 20
            elif image.file_size >= self.MIN_FILE_SIZE:
                score += 10 + int((image.file_size - self.MIN_FILE_SIZE) / (100000 - self.MIN_FILE_SIZE) * 10)
            else:
                score += int(image.file_size / self.MIN_FILE_SIZE * 10)
        
        # Aspect ratio score (0-20 points)
        if image.aspect_ratio:
            # Prefer square images (ratio close to 1.0)
            ratio_diff = abs(1.0 - image.aspect_ratio)
            if ratio_diff <= 0.1:
                score += 20
            elif ratio_diff <= 0.3:
                score += 15
            elif ratio_diff <= 0.5:
                score += 10
            else:
                score += 5
        
        # Priority bonus (0-20 points)
        if image.priority == 'high':
            score += 20
        elif image.priority == 'medium':
            score += 10
        else:
            score += 5
        
        return min(score, 100)
    
    def filter_quality_images(self, images: List[ExtractedImage], 
                             min_quality: int = 50,
                             analyze: bool = True) -> List[ExtractedImage]:
        """
        Filter images by quality threshold
        
        Args:
            images: List of ExtractedImage objects
            min_quality: Minimum quality score (0-100)
            analyze: Whether to analyze images first
            
        Returns:
            Filtered list of quality images
        """
        if analyze:
            # Analyze each image
            for i, image in enumerate(images):
                logger.info(f"Analyzing image {i+1}/{len(images)}")
                self.analyze_image_quality(image, fetch_metadata=True)
                time.sleep(0.1)  # Small delay between requests
        
        # Filter by quality
        quality_images = [img for img in images if img.quality_score >= min_quality]
        
        logger.info(f"Filtered {len(quality_images)} quality images from {len(images)} total")
        return quality_images
    
    def get_best_images(self, images: List[ExtractedImage], 
                       max_images: int = 10,
                       prefer_high_res: bool = True) -> List[ExtractedImage]:
        """
        Get the best N images based on quality
        
        Args:
            images: List of ExtractedImage objects
            max_images: Maximum number of images to return
            prefer_high_res: Whether to prefer high-resolution images
            
        Returns:
            List of best quality images
        """
        # Sort by quality score (and high-res preference)
        sorted_images = sorted(
            images,
            key=lambda x: (x.is_high_res if prefer_high_res else 0, x.quality_score),
            reverse=True
        )
        
        return sorted_images[:max_images]
