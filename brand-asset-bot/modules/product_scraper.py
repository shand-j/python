"""
Product Scraper Module
Main orchestrator for the product scraping pipeline
"""
from pathlib import Path
from .scraper import WebScraper
from .image_processor import ImageProcessor
from .gpt_processor import GPTProcessor
from .shopify_exporter import ShopifyExporter


class ProductScraper:
    """Main product scraper orchestrator"""
    
    def __init__(self, config, logger):
        """
        Initialize product scraper
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        
        # Initialize components
        self.web_scraper = WebScraper(config, logger)
        self.image_processor = ImageProcessor(config, logger)
        self.gpt_processor = GPTProcessor(config, logger)
        self.shopify_exporter = ShopifyExporter(config, logger)
    
    def scrape_product(self, url, enhance_description=True, generate_tags=True, process_images=True):
        """
        Scrape a single product from URL
        
        Args:
            url: Product page URL
            enhance_description: Whether to enhance description with GPT
            generate_tags: Whether to generate tags with GPT
            process_images: Whether to download and process images
        
        Returns:
            dict: Product data
        """
        self.logger.info(f"Starting product scrape: {url}")
        
        try:
            # Extract product data
            product_data = self.web_scraper.extract_product_data(url)
            
            # Use the best available title
            title = (product_data.get('product_name') or 
                    product_data.get('og_title') or 
                    product_data.get('title') or 
                    'Untitled Product')
            
            # Use the best available description
            description = (product_data.get('description') or 
                          product_data.get('og_description') or 
                          '')
            
            # Build product object
            product = {
                'title': title,
                'original_description': description,
                'enhanced_description': description,
                'summary': '',
                'price': product_data.get('price', ''),
                'source_url': url,
                'metadata': product_data,
                'tags': [],
                'processed_images': []
            }
            
            # Enhance description if enabled
            if enhance_description and description:
                self.logger.info("Enhancing product description")
                enhanced_desc = self.gpt_processor.enhance_description(
                    description,
                    product_name=title,
                    additional_context=str(product_data.get('breadcrumbs', []))
                )
                product['enhanced_description'] = enhanced_desc
                
                # Generate summary
                product['summary'] = self.gpt_processor.generate_summary(enhanced_desc)
            
            # Generate tags if enabled
            if generate_tags:
                self.logger.info("Generating product tags")
                tags = self.gpt_processor.generate_tags(
                    title,
                    product['enhanced_description'],
                    metadata=product_data
                )
                product['tags'] = tags
            
            # Process images if enabled
            if process_images and product_data.get('images'):
                self.logger.info(f"Processing {len(product_data['images'])} images")
                
                # Create product-specific image directory
                product_image_dir = self.config.images_dir / self._sanitize_filename(title)
                
                processed_images = self.image_processor.process_images(
                    product_data['images'],
                    product_image_dir
                )
                product['processed_images'] = processed_images
                self.logger.info(f"Processed {len(processed_images)} images")
            
            # Add SEO fields
            product['seo_title'] = title
            product['seo_description'] = product['summary'] or description[:160]
            
            self.logger.info(f"Successfully scraped product: {title}")
            return product
            
        except Exception as e:
            self.logger.error(f"Error scraping product {url}: {e}", exc_info=True)
            raise
    
    def scrape_products(self, urls, **kwargs):
        """
        Scrape multiple products from URLs
        
        Args:
            urls: List of product page URLs
            **kwargs: Arguments passed to scrape_product
        
        Returns:
            list: List of product data dictionaries
        """
        self.logger.info(f"Starting batch scrape of {len(urls)} products")
        
        products = []
        failed_urls = []
        
        for idx, url in enumerate(urls, 1):
            self.logger.info(f"Processing product {idx}/{len(urls)}")
            
            try:
                product = self.scrape_product(url, **kwargs)
                products.append(product)
            except Exception as e:
                self.logger.error(f"Failed to scrape {url}: {e}")
                failed_urls.append(url)
        
        self.logger.info(f"Batch scrape completed. Success: {len(products)}, Failed: {len(failed_urls)}")
        
        if failed_urls:
            self.logger.warning(f"Failed URLs: {failed_urls}")
        
        return products
    
    def export_products(self, products, format='csv', output_path=None):
        """
        Export products to file
        
        Args:
            products: List of product dictionaries
            format: Export format ('csv' or 'json')
            output_path: Path to output file
        
        Returns:
            str: Path to created file
        """
        return self.shopify_exporter.export(products, format, output_path)
    
    def scrape_and_export(self, urls, export_format='csv', output_path=None, **kwargs):
        """
        Scrape products and export to file
        
        Args:
            urls: List of product page URLs
            export_format: Export format ('csv' or 'json')
            output_path: Path to output file
            **kwargs: Arguments passed to scrape_product
        
        Returns:
            tuple: (products list, output file path)
        """
        products = self.scrape_products(urls, **kwargs)
        
        if products:
            output_file = self.export_products(products, export_format, output_path)
            return products, output_file
        
        return products, None
    
    def _sanitize_filename(self, name):
        """
        Sanitize a string for use as filename
        
        Args:
            name: String to sanitize
        
        Returns:
            str: Sanitized string
        """
        import re
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length
