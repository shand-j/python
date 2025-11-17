"""
Shopify Exporter Module
Handles exporting product data to Shopify-compatible CSV format
"""
import csv
import json
from pathlib import Path
from datetime import datetime


class ShopifyExporter:
    """Exporter for Shopify product import CSV format"""
    
    # Shopify CSV column headers
    SHOPIFY_HEADERS = [
        'Handle',
        'Title',
        'Body (HTML)',
        'Vendor',
        'Product Category',
        'Type',
        'Tags',
        'Published',
        'Option1 Name',
        'Option1 Value',
        'Option2 Name',
        'Option2 Value',
        'Option3 Name',
        'Option3 Value',
        'Variant SKU',
        'Variant Grams',
        'Variant Inventory Tracker',
        'Variant Inventory Qty',
        'Variant Inventory Policy',
        'Variant Fulfillment Service',
        'Variant Price',
        'Variant Compare At Price',
        'Variant Requires Shipping',
        'Variant Taxable',
        'Variant Barcode',
        'Image Src',
        'Image Position',
        'Image Alt Text',
        'Gift Card',
        'SEO Title',
        'SEO Description',
        'Google Shopping / Google Product Category',
        'Google Shopping / Gender',
        'Google Shopping / Age Group',
        'Google Shopping / MPN',
        'Google Shopping / AdWords Grouping',
        'Google Shopping / AdWords Labels',
        'Google Shopping / Condition',
        'Google Shopping / Custom Product',
        'Google Shopping / Custom Label 0',
        'Google Shopping / Custom Label 1',
        'Google Shopping / Custom Label 2',
        'Google Shopping / Custom Label 3',
        'Google Shopping / Custom Label 4',
        'Variant Image',
        'Variant Weight Unit',
        'Variant Tax Code',
        'Cost per item',
        'Status'
    ]
    
    def __init__(self, config, logger):
        """
        Initialize Shopify exporter
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
    
    def _generate_handle(self, title):
        """
        Generate a Shopify handle from title
        
        Args:
            title: Product title
        
        Returns:
            str: Handle (URL-friendly identifier)
        """
        import re
        # Convert to lowercase and replace spaces with hyphens
        handle = title.lower()
        handle = re.sub(r'[^a-z0-9\s-]', '', handle)
        handle = re.sub(r'\s+', '-', handle)
        handle = re.sub(r'-+', '-', handle)
        return handle.strip('-')
    
    def _format_tags(self, tags):
        """
        Format tags for Shopify
        
        Args:
            tags: List of tags
        
        Returns:
            str: Comma-separated tags
        """
        if isinstance(tags, list):
            return ', '.join(tags)
        return str(tags)
    
    def _format_html_description(self, description):
        """
        Format description as HTML for Shopify
        
        Args:
            description: Plain text description
        
        Returns:
            str: HTML formatted description
        """
        if not description:
            return ''
        
        # Split into paragraphs and wrap in <p> tags
        paragraphs = description.split('\n\n')
        html_paragraphs = [f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()]
        return '\n'.join(html_paragraphs)
    
    def export_to_csv(self, products, output_path=None):
        """
        Export products to Shopify CSV format
        
        Args:
            products: List of product dictionaries
            output_path: Path to output CSV file
        
        Returns:
            str: Path to created CSV file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.config.output_dir / f'shopify_products_{timestamp}.csv'
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Exporting {len(products)} products to CSV: {output_path}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.SHOPIFY_HEADERS)
            writer.writeheader()
            
            for product in products:
                # Process each product and its images
                images = product.get('processed_images', [])
                tags = self._format_tags(product.get('tags', []))
                handle = self._generate_handle(product.get('title', 'product'))
                
                # First row includes all product data
                first_row = {
                    'Handle': handle,
                    'Title': product.get('title', ''),
                    'Body (HTML)': self._format_html_description(product.get('enhanced_description', '')),
                    'Vendor': product.get('vendor', ''),
                    'Product Category': product.get('category', ''),
                    'Type': product.get('type', ''),
                    'Tags': tags,
                    'Published': 'TRUE',
                    'Variant SKU': product.get('sku', ''),
                    'Variant Inventory Tracker': 'shopify',
                    'Variant Inventory Qty': product.get('inventory_qty', '0'),
                    'Variant Inventory Policy': 'deny',
                    'Variant Fulfillment Service': 'manual',
                    'Variant Price': product.get('price', ''),
                    'Variant Requires Shipping': 'TRUE',
                    'Variant Taxable': 'TRUE',
                    'SEO Title': product.get('seo_title', product.get('title', '')),
                    'SEO Description': product.get('seo_description', product.get('summary', '')),
                    'Status': 'active'
                }
                
                # Add first image to first row
                if images:
                    first_row['Image Src'] = images[0]
                    first_row['Image Position'] = '1'
                    first_row['Image Alt Text'] = product.get('title', '')
                
                writer.writerow(first_row)
                
                # Additional rows for additional images
                for idx, image in enumerate(images[1:], start=2):
                    image_row = {
                        'Handle': handle,
                        'Image Src': image,
                        'Image Position': str(idx),
                        'Image Alt Text': product.get('title', '')
                    }
                    writer.writerow(image_row)
        
        self.logger.info(f"CSV export completed: {output_path}")
        return str(output_path)
    
    def export_to_json(self, products, output_path=None):
        """
        Export products to JSON format
        
        Args:
            products: List of product dictionaries
            output_path: Path to output JSON file
        
        Returns:
            str: Path to created JSON file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.config.output_dir / f'products_{timestamp}.json'
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Exporting {len(products)} products to JSON: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(products, jsonfile, indent=2, ensure_ascii=False)
        
        self.logger.info(f"JSON export completed: {output_path}")
        return str(output_path)
    
    def export(self, products, format='csv', output_path=None):
        """
        Export products in specified format
        
        Args:
            products: List of product dictionaries
            format: Export format ('csv' or 'json')
            output_path: Path to output file
        
        Returns:
            str: Path to created file
        """
        if format.lower() == 'json':
            return self.export_to_json(products, output_path)
        else:
            return self.export_to_csv(products, output_path)
