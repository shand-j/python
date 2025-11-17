"""
Image Processor Module
Handles downloading and resizing product images with smart filtering
"""
import os
import time
import hashlib
import requests
import json
import re
from pathlib import Path
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Any, Tuple
from datetime import datetime


class ImageProcessor:
    """Image processor for downloading and resizing product images with smart filtering"""
    
    def __init__(self, config, logger):
        """
        Initialize image processor
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.session = requests.Session()
        
        # Create images directory if it doesn't exist
        self.images_dir = Path(getattr(config, 'images_dir', './images'))
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Product image indicators (higher score = more likely to be product image)
        self.product_indicators = {
            'alt_keywords': ['product', 'main', 'hero', 'primary', 'detail', 'zoom', 'large', 'gallery'],
            'class_keywords': ['product', 'main', 'hero', 'primary', 'detail', 'zoom', 'gallery', 'carousel', 'slideshow'],
            'id_keywords': ['product', 'main', 'hero', 'primary', 'detail', 'zoom'],
            'src_keywords': ['product', 'main', 'hero', 'primary', 'detail', 'zoom', 'large'],
            'parent_keywords': ['product', 'gallery', 'carousel', 'slideshow', 'images']
        }
        
        # Non-product image indicators (negative scoring)
        self.non_product_indicators = {
            'alt_keywords': ['logo', 'icon', 'payment', 'shipping', 'security', 'badge', 'award', 'social', 'related', 'recommended', 'similar', 'upsell', 'banner', 'ad', 'advertisement'],
            'class_keywords': ['logo', 'icon', 'payment', 'shipping', 'security', 'badge', 'award', 'social', 'related', 'recommended', 'similar', 'upsell', 'banner', 'ad', 'advertisement', 'footer', 'header', 'nav'],
            'id_keywords': ['logo', 'icon', 'payment', 'shipping', 'security', 'badge', 'award', 'social', 'related', 'recommended', 'similar', 'upsell', 'banner', 'ad'],
            'src_keywords': ['logo', 'icon', 'payment', 'shipping', 'security', 'badge', 'award', 'social', 'related', 'recommended', 'similar', 'upsell', 'banner', 'ad'],
            'parent_keywords': ['footer', 'header', 'nav', 'sidebar', 'related', 'recommended', 'similar', 'upsell', 'banner', 'ad']
        }
        
        # Common non-product image file patterns
        self.non_product_patterns = [
            r'logo', r'icon', r'payment', r'shipping', r'security', r'badge', r'award',
            r'social', r'facebook', r'twitter', r'instagram', r'youtube', r'tiktok',
            r'visa', r'mastercard', r'paypal', r'apple_?pay', r'google_?pay', r'amex',
            r'ssl', r'secure', r'trust', r'verified', r'guarantee',
            r'banner', r'ad\d*', r'promo', r'sale', r'offer',
            r'arrow', r'chevron', r'close', r'menu', r'search', r'cart',
            r'\d+x\d+', r'placeholder', r'loading', r'spinner'
        ]
    
    def score_image_relevance(self, img_element, base_url: str) -> Dict[str, Any]:
        """Score how likely an image is to be a product image"""
        score = 0
        reasons = []
        
        # Get image attributes
        src = img_element.get('src', '')
        alt = img_element.get('alt', '').lower()
        class_attr = ' '.join(img_element.get('class', [])).lower()
        img_id = img_element.get('id', '').lower()
        
        # Get parent element context
        parent = img_element.parent
        parent_class = ' '.join(parent.get('class', [])).lower() if parent else ''
        parent_id = parent.get('id', '').lower() if parent else ''
        
        # Check for product indicators
        for keyword in self.product_indicators['alt_keywords']:
            if keyword in alt:
                score += 3
                reasons.append(f"alt contains '{keyword}'")
                
        for keyword in self.product_indicators['class_keywords']:
            if keyword in class_attr:
                score += 2
                reasons.append(f"class contains '{keyword}'")
                
        for keyword in self.product_indicators['id_keywords']:
            if keyword in img_id:
                score += 2
                reasons.append(f"id contains '{keyword}'")
                
        for keyword in self.product_indicators['src_keywords']:
            if keyword in src.lower():
                score += 2
                reasons.append(f"src contains '{keyword}'")
                
        for keyword in self.product_indicators['parent_keywords']:
            if keyword in parent_class or keyword in parent_id:
                score += 1
                reasons.append(f"parent contains '{keyword}'")
        
        # Check for non-product indicators (negative scoring)
        for keyword in self.non_product_indicators['alt_keywords']:
            if keyword in alt:
                score -= 5
                reasons.append(f"alt contains non-product '{keyword}'")
                
        for keyword in self.non_product_indicators['class_keywords']:
            if keyword in class_attr:
                score -= 3
                reasons.append(f"class contains non-product '{keyword}'")
                
        for keyword in self.non_product_indicators['id_keywords']:
            if keyword in img_id:
                score -= 3
                reasons.append(f"id contains non-product '{keyword}'")
                
        for keyword in self.non_product_indicators['src_keywords']:
            if keyword in src.lower():
                score -= 3
                reasons.append(f"src contains non-product '{keyword}'")
                
        for keyword in self.non_product_indicators['parent_keywords']:
            if keyword in parent_class or keyword in parent_id:
                score -= 2
                reasons.append(f"parent contains non-product '{keyword}'")
        
        # Check filename patterns
        filename = os.path.basename(urlparse(src).path).lower()
        for pattern in self.non_product_patterns:
            if re.search(pattern, filename):
                score -= 4
                reasons.append(f"filename matches non-product pattern '{pattern}'")
        
        # Size-based scoring (if data attributes available)
        width = img_element.get('width')
        height = img_element.get('height')
        if width and height:
            try:
                w, h = int(width), int(height)
                # Very small images are likely icons/logos
                if w < 50 or h < 50:
                    score -= 3
                    reasons.append(f"small dimensions ({w}x{h})")
                # Very large images are likely product images
                elif w > 300 and h > 300:
                    score += 2
                    reasons.append(f"large dimensions ({w}x{h})")
            except ValueError:
                pass
        
        # Position-based scoring (first few images more likely to be products)
        img_index = len(img_element.find_all_previous('img'))
        if img_index < 3:
            score += 1
            reasons.append(f"early position (index {img_index})")
        
        return {
            'score': score,
            'reasons': reasons,
            'src': src,
            'alt': alt,
            'class': class_attr,
            'id': img_id
        }

    def categorize_images(self, soup, base_url: str) -> Dict[str, List[Dict]]:
        """Categorize all images into product vs non-product with scoring"""
        img_elements = soup.find_all('img', src=True)
        
        if not img_elements:
            return {'product': [], 'alternative': []}
        
        # Score all images
        all_images = []
        for img in img_elements:
            score_data = self.score_image_relevance(img, base_url)
            if score_data['src']:
                score_data['url'] = urljoin(base_url, score_data['src'])
                all_images.append(score_data)
        
        # Sort by score (highest first)
        all_images.sort(key=lambda x: x['score'], reverse=True)
        
        # Categorize: positive scores are likely product images
        product_images = [img for img in all_images if img['score'] > 0][:10]  # Top 10 product images
        alternative_images = [img for img in all_images if img['score'] <= 0][:20]  # Up to 20 alternative images
        
        return {
            'product': product_images,
            'alternative': alternative_images
        }

    def _get_image_filename(self, url, prefix="", img_data=None):
        """
        Generate a unique filename for an image with category prefix
        
        Args:
            url: Image URL
            prefix: Filename prefix (e.g., "PRODUCT_01", "ALT_01")
            img_data: Image data dictionary with score
        
        Returns:
            str: Filename
        """
        # Create hash of URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Extract extension from URL
        parsed = urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1]
        
        if not ext or len(ext) > 5:
            ext = '.jpg'
        
        # Include score in filename for easy identification
        if img_data and 'score' in img_data:
            score = img_data['score']
            return f"{prefix}_score{score:+d}_{url_hash}{ext}"
        else:
            return f"{prefix}_{url_hash}{ext}"
    
    def _download_and_process_image(self, image_url: str, prefix: str, img_data: Dict) -> str:
        """Download and process a single image"""
        try:
            # Download image
            response = self.session.get(
                image_url, 
                timeout=self.config.request_timeout,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; ProductScraper/1.0)'}
            )
            response.raise_for_status()
            
            # Add delay between image downloads
            time.sleep(self.config.request_delay)
            
            # Generate filename with category prefix
            filename = self._get_image_filename(image_url, prefix, img_data)
            filepath = self.images_dir / filename
            
            # Process and save image
            image = Image.open(BytesIO(response.content))
            processed_image = self._resize_and_optimize(image)
            processed_image.save(filepath, optimize=True, quality=self.config.image_quality)
            
            score = img_data.get('score', 0)
            self.logger.info(f"Saved: {filename} (score: {score})")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to download {image_url}: {e}")
            return None

    def download_image(self, url, output_dir, index=0):
        """
        Legacy download method for backward compatibility
        """
        try:
            response = self.session.get(
                url,
                timeout=self.config.request_timeout,
                stream=True
            )
            response.raise_for_status()
            
            time.sleep(self.config.request_delay)
            
            filename = self._get_image_filename(url, f"image_{index}")
            output_path = Path(output_dir) / filename
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error downloading image {url}: {e}")
            return None
    
    def _resize_and_optimize(self, image: Image.Image) -> Image.Image:
        """Resize and optimize image while maintaining aspect ratio"""
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Calculate resize dimensions
        width, height = image.size
        max_width = self.config.image_max_width
        max_height = self.config.image_max_height
        
        if width > max_width or height > max_height:
            # Calculate aspect ratio
            aspect = width / height
            
            if aspect > 1:  # Landscape
                new_width = min(width, max_width)
                new_height = int(new_width / aspect)
            else:  # Portrait or square
                new_height = min(height, max_height)
                new_width = int(new_height * aspect)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image

    def resize_image(self, image_path, max_width=None, max_height=None):
        """
        Legacy resize method for backward compatibility
        """
        try:
            if max_width is None:
                max_width = self.config.image_max_width
            if max_height is None:
                max_height = self.config.image_max_height
            
            with Image.open(image_path) as img:
                processed = self._resize_and_optimize(img)
                processed.save(
                    image_path,
                    quality=self.config.image_quality,
                    optimize=True
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error resizing image {image_path}: {e}")
            return False
    
    def process_images(self, soup, base_url: str) -> Tuple[List[str], Dict[str, Any]]:
        """
        Process and download all images, returning shopify images and metadata
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative image URLs
        
        Returns:
            Tuple of (shopify_image_paths, image_metadata)
        """
        # Categorize images
        categorized = self.categorize_images(soup, base_url)
        
        # Download and process all images
        shopify_images = []
        all_processed = []
        
        self.logger.info(f"Found {len(categorized['product'])} product images and {len(categorized['alternative'])} alternative images")
        
        # Process product images (for Shopify)
        for i, img_data in enumerate(categorized['product']):
            try:
                filepath = self._download_and_process_image(
                    img_data['url'], 
                    f"PRODUCT_{i+1:02d}",
                    img_data
                )
                if filepath:
                    shopify_images.append(filepath)
                    all_processed.append({
                        'filepath': filepath,
                        'category': 'product',
                        'score': img_data['score'],
                        'reasons': img_data['reasons']
                    })
                    
            except Exception as e:
                self.logger.error(f"Failed to process product image {i+1}: {e}")
        
        # Process alternative images (for review only)
        for i, img_data in enumerate(categorized['alternative']):
            try:
                filepath = self._download_and_process_image(
                    img_data['url'], 
                    f"ALT_{i+1:02d}",
                    img_data
                )
                if filepath:
                    all_processed.append({
                        'filepath': filepath,
                        'category': 'alternative',
                        'score': img_data['score'],
                        'reasons': img_data['reasons']
                    })
                    
            except Exception as e:
                self.logger.error(f"Failed to process alternative image {i+1}: {e}")
        
        # Create image processing metadata
        metadata = {
            'total_images_found': len(categorized['product']) + len(categorized['alternative']),
            'product_images_count': len(categorized['product']),
            'alternative_images_count': len(categorized['alternative']),
            'shopify_images_count': len(shopify_images),
            'processed_images': all_processed
        }
        
        # Save image processing report
        self._save_image_report(metadata, base_url)
        
        self.logger.info(f"Processed {len(shopify_images)} product images for Shopify import")
        self.logger.info(f"Saved {len(all_processed) - len(shopify_images)} alternative images for review")
        
        return shopify_images, metadata

    def _save_image_report(self, metadata: Dict, base_url: str):
        """Save detailed image processing report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'source_url': base_url,
            'summary': {
                'total_found': metadata['total_images_found'],
                'product_images': metadata['product_images_count'],
                'alternative_images': metadata['alternative_images_count'],
                'shopify_ready': metadata['shopify_images_count']
            },
            'images': []
        }
        
        # Add detailed image information
        for img in metadata['processed_images']:
            report['images'].append({
                'filename': os.path.basename(img['filepath']),
                'category': img['category'],
                'score': img['score'],
                'reasons': img['reasons'],
                'shopify_eligible': img['category'] == 'product'
            })
        
        # Save report
        report_filename = f"image_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = self.images_dir / report_filename
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Image processing report saved: {report_filename}")

    def process_images_legacy(self, image_urls, output_dir):
        """
        Legacy method for backward compatibility
        """
        processed_images = []
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for index, url in enumerate(image_urls):
            # Download image
            image_path = self.download_image(url, output_dir, index)
            
            if image_path:
                # Resize image
                if self.resize_image(image_path):
                    processed_images.append(image_path)
                else:
                    # Keep original if resize fails
                    processed_images.append(image_path)
        
        return processed_images
