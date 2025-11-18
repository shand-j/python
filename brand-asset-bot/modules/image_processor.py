"""
Image Processor Module
Handles downloading and resizing product images
"""
import os
import time
import hashlib
import requests
from pathlib import Path
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse


class ImageProcessor:
    """Image processor for downloading and resizing product images"""
    
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
    
    def _get_image_filename(self, url, index=0):
        """
        Generate a unique filename for an image
        
        Args:
            url: Image URL
            index: Image index
        
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
        
        return f"image_{index}_{url_hash}{ext}"
    
    def download_image(self, url, output_dir, index=0):
        """
        Download an image from URL
        
        Args:
            url: Image URL
            output_dir: Directory to save image
            index: Image index
        
        Returns:
            str: Path to downloaded image or None if failed
        """
        try:
            self.logger.info(f"Downloading image: {url}")
            
            response = self.session.get(
                url,
                timeout=self.config.request_timeout,
                stream=True
            )
            response.raise_for_status()
            
            # Add delay between image downloads
            time.sleep(self.config.request_delay)
            
            filename = self._get_image_filename(url, index)
            output_path = Path(output_dir) / filename
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.logger.info(f"Downloaded image to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error downloading image {url}: {e}")
            return None
    
    def resize_image(self, image_path, max_width=None, max_height=None):
        """
        Resize an image while maintaining aspect ratio
        
        Args:
            image_path: Path to image file
            max_width: Maximum width (default from config)
            max_height: Maximum height (default from config)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if max_width is None:
                max_width = self.config.image_max_width
            if max_height is None:
                max_height = self.config.image_max_height
            
            self.logger.info(f"Resizing image: {image_path}")
            
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (handles RGBA, P, etc.)
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                # Get current dimensions
                width, height = img.size
                
                # Calculate new dimensions maintaining aspect ratio
                if width > max_width or height > max_height:
                    aspect_ratio = width / height
                    
                    if width > height:
                        new_width = max_width
                        new_height = int(new_width / aspect_ratio)
                    else:
                        new_height = max_height
                        new_width = int(new_height * aspect_ratio)
                    
                    # Ensure dimensions don't exceed maximums
                    if new_width > max_width:
                        new_width = max_width
                        new_height = int(new_width / aspect_ratio)
                    if new_height > max_height:
                        new_height = max_height
                        new_width = int(new_height * aspect_ratio)
                    
                    # Resize using high-quality Lanczos filter
                    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Save with quality setting
                    img_resized.save(
                        image_path,
                        quality=self.config.image_quality,
                        optimize=True
                    )
                    
                    self.logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")
                else:
                    self.logger.info(f"Image already within size limits: {width}x{height}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error resizing image {image_path}: {e}")
            return False
    
    def process_images(self, image_urls, output_dir):
        """
        Download and resize multiple images
        
        Args:
            image_urls: List of image URLs
            output_dir: Directory to save images
        
        Returns:
            list: List of processed image paths
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
