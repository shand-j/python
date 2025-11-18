"""
Competitor Image Downloader Module

Downloads product images from competitor websites with organization and deduplication.
"""

import os
import time
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Dict
from urllib.parse import urlparse
import requests

from .image_extractor import ExtractedImage
from .logger import setup_logger

logger = setup_logger(__name__)


class CompetitorImageDownloader:
    """Downloads and organizes product images from competitor sites"""
    
    def __init__(self, base_dir: str = "competitor_images", user_agent: Optional[str] = None):
        """
        Initialize image downloader
        
        Args:
            base_dir: Base directory for downloaded images
            user_agent: User agent string for requests
        """
        self.base_dir = base_dir
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        self.downloaded_hashes = set()  # Track downloaded files by hash
    
    def download_product_images(self, 
                                brand: str,
                                product_name: str,
                                images: List[ExtractedImage],
                                competitor_site: str,
                                max_images: int = 10,
                                skip_duplicates: bool = True) -> Dict:
        """
        Download images for a product
        
        Args:
            brand: Brand name
            product_name: Product name
            images: List of ExtractedImage objects
            competitor_site: Competitor site name
            max_images: Maximum images to download
            skip_duplicates: Whether to skip duplicate images
            
        Returns:
            Download summary dictionary
        """
        # Create directory structure
        brand_dir = self._create_brand_directory(brand, competitor_site)
        
        # Sanitize product name for filename
        safe_product_name = self._sanitize_filename(product_name)
        
        downloaded = []
        skipped = []
        failed = []
        
        for i, image in enumerate(images[:max_images]):
            try:
                logger.info(f"Downloading image {i+1}/{min(len(images), max_images)}: {image.url[:60]}...")
                
                # Download image
                response = self.session.get(image.url, timeout=30, stream=True)
                response.raise_for_status()
                
                # Get image content
                content = response.content
                
                # Check for duplicates
                if skip_duplicates:
                    content_hash = hashlib.md5(content).hexdigest()
                    if content_hash in self.downloaded_hashes:
                        logger.debug(f"Skipping duplicate image: {image.url[:60]}...")
                        skipped.append(image.url)
                        continue
                    self.downloaded_hashes.add(content_hash)
                
                # Generate filename
                file_ext = self._get_file_extension(image.url, response.headers.get('content-type'))
                filename = f"{safe_product_name}-{i+1:02d}{file_ext}"
                filepath = brand_dir / filename
                
                # Save image
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                downloaded.append({
                    'filename': filename,
                    'url': image.url,
                    'type': image.image_type,
                    'quality_score': image.quality_score,
                    'size': len(content),
                    'width': image.width,
                    'height': image.height
                })
                
                logger.info(f"Downloaded: {filename}")
                
                # Small delay between downloads
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error downloading image {image.url}: {e}")
                failed.append({'url': image.url, 'error': str(e)})
        
        # Create metadata file
        metadata = {
            'brand': brand,
            'product_name': product_name,
            'competitor_site': competitor_site,
            'downloaded_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'total_images': len(images),
            'downloaded': len(downloaded),
            'skipped': len(skipped),
            'failed': len(failed),
            'images': downloaded
        }
        
        metadata_path = brand_dir / f"{safe_product_name}-metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Download complete: {len(downloaded)} downloaded, {len(skipped)} skipped, {len(failed)} failed")
        
        return metadata
    
    def batch_download(self, 
                      products: List[Dict],
                      images_per_product: int = 5,
                      delay_between_products: float = 2.0) -> Dict:
        """
        Batch download images for multiple products
        
        Args:
            products: List of product dictionaries with 'brand', 'name', 'images', 'competitor_site'
            images_per_product: Max images per product
            delay_between_products: Delay between products (seconds)
            
        Returns:
            Batch download summary
        """
        results = {
            'total_products': len(products),
            'successful': 0,
            'failed': 0,
            'total_images_downloaded': 0,
            'products': []
        }
        
        for i, product in enumerate(products):
            try:
                logger.info(f"\nProcessing product {i+1}/{len(products)}: {product['name']}")
                
                metadata = self.download_product_images(
                    brand=product['brand'],
                    product_name=product['name'],
                    images=product['images'],
                    competitor_site=product['competitor_site'],
                    max_images=images_per_product
                )
                
                results['successful'] += 1
                results['total_images_downloaded'] += metadata['downloaded']
                results['products'].append({
                    'name': product['name'],
                    'status': 'success',
                    'images_downloaded': metadata['downloaded']
                })
                
                # Delay between products
                if i < len(products) - 1:
                    time.sleep(delay_between_products)
                
            except Exception as e:
                logger.error(f"Error processing product {product['name']}: {e}")
                results['failed'] += 1
                results['products'].append({
                    'name': product['name'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    def _create_brand_directory(self, brand: str, competitor_site: str) -> Path:
        """Create and return brand-specific directory"""
        safe_brand = self._sanitize_filename(brand)
        safe_site = self._sanitize_filename(competitor_site)
        
        brand_path = Path(self.base_dir) / safe_brand / safe_site
        brand_path.mkdir(parents=True, exist_ok=True)
        
        return brand_path
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for use as filename"""
        # Remove/replace invalid characters
        name = name.lower()
        name = name.replace(' ', '-')
        # Remove multiple consecutive dashes
        import re
        name = re.sub(r'-+', '-', name)
        name = ''.join(c for c in name if c.isalnum() or c in ['-', '_'])
        # Limit length
        return name[:100]
    
    def _get_file_extension(self, url: str, content_type: Optional[str] = None) -> str:
        """Get file extension from URL or content type"""
        # Try to get from URL
        parsed = urlparse(url)
        path = parsed.path
        
        if '.' in path:
            ext = path.rsplit('.', 1)[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']:
                return f'.{ext}'
        
        # Try to get from content type
        if content_type:
            type_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'image/svg+xml': '.svg'
            }
            return type_map.get(content_type.lower(), '.jpg')
        
        return '.jpg'  # Default
    
    def get_download_summary(self, brand: Optional[str] = None) -> Dict:
        """
        Get summary of downloaded images
        
        Args:
            brand: Optional brand name to filter
            
        Returns:
            Summary dictionary
        """
        base_path = Path(self.base_dir)
        
        if not base_path.exists():
            return {'total_brands': 0, 'total_images': 0, 'brands': {}}
        
        summary = {
            'total_brands': 0,
            'total_images': 0,
            'total_size_mb': 0,
            'brands': {}
        }
        
        # Iterate through brand directories
        for brand_dir in base_path.iterdir():
            if not brand_dir.is_dir():
                continue
            
            if brand and brand_dir.name != self._sanitize_filename(brand):
                continue
            
            brand_stats = {
                'total_images': 0,
                'total_size_mb': 0,
                'competitor_sites': {}
            }
            
            # Count images in each competitor site subdirectory
            for site_dir in brand_dir.iterdir():
                if not site_dir.is_dir():
                    continue
                
                image_files = [f for f in site_dir.iterdir() 
                             if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']]
                
                site_size = sum(f.stat().st_size for f in image_files) / (1024 * 1024)
                
                brand_stats['competitor_sites'][site_dir.name] = {
                    'image_count': len(image_files),
                    'size_mb': round(site_size, 2)
                }
                
                brand_stats['total_images'] += len(image_files)
                brand_stats['total_size_mb'] += site_size
            
            brand_stats['total_size_mb'] = round(brand_stats['total_size_mb'], 2)
            summary['brands'][brand_dir.name] = brand_stats
            summary['total_images'] += brand_stats['total_images']
            summary['total_size_mb'] += brand_stats['total_size_mb']
        
        summary['total_brands'] = len(summary['brands'])
        summary['total_size_mb'] = round(summary['total_size_mb'], 2)
        
        return summary
