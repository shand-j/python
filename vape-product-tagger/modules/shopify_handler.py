"""
Shopify Import/Export Handler Module
Handles reading from and writing to Shopify CSV format
"""
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import pandas as pd


class ShopifyHandler:
    """Handler for Shopify product CSV import and export"""
    
    # Shopify CSV column headers
    SHOPIFY_HEADERS = [
        'Handle', 'Title', 'Body (HTML)', 'Vendor', 'Product Category', 'Type',
        'Tags', 'Published', 'Option1 Name', 'Option1 Value', 'Option2 Name',
        'Option2 Value', 'Option3 Name', 'Option3 Value', 'Variant SKU',
        'Variant Grams', 'Variant Inventory Tracker', 'Variant Inventory Qty',
        'Variant Inventory Policy', 'Variant Fulfillment Service', 'Variant Price',
        'Variant Compare At Price', 'Variant Requires Shipping', 'Variant Taxable',
        'Variant Barcode', 'Image Src', 'Image Position', 'Image Alt Text',
        'Gift Card', 'SEO Title', 'SEO Description', 'Google Shopping / Google Product Category',
        'Google Shopping / Gender', 'Google Shopping / Age Group', 'Google Shopping / MPN',
        'Google Shopping / AdWords Grouping', 'Google Shopping / AdWords Labels',
        'Google Shopping / Condition', 'Google Shopping / Custom Product',
        'Google Shopping / Custom Label 0', 'Google Shopping / Custom Label 1',
        'Google Shopping / Custom Label 2', 'Google Shopping / Custom Label 3',
        'Google Shopping / Custom Label 4', 'Variant Image', 'Variant Weight Unit',
        'Variant Tax Code', 'Cost per item', 'Status'
    ]
    
    def __init__(self, config, logger):
        """
        Initialize Shopify handler
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
    
    def import_from_csv(self, csv_path: str) -> List[Dict]:
        """
        Import products from Shopify CSV
        
        Args:
            csv_path: Path to Shopify CSV file
        
        Returns:
            List[Dict]: List of product dictionaries
        """
        self.logger.info(f"Importing products from: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            
            # Group by Handle to consolidate products
            products = []
            grouped = df.groupby('Handle')
            
            for handle, group in grouped:
                # Get first row for main product data
                first_row = group.iloc[0]
                
                # Helper function to handle NaN values
                def safe_str(value):
                    if pd.isna(value):
                        return ''
                    return str(value)
                
                product = {
                    'handle': safe_str(first_row.get('Handle', '')),
                    'title': safe_str(first_row.get('Title', '')),
                    'description': safe_str(first_row.get('Body (HTML)', '')),
                    'vendor': safe_str(first_row.get('Vendor', '')),
                    'product_category': safe_str(first_row.get('Product Category', '')),
                    'type': safe_str(first_row.get('Type', '')),
                    'existing_tags': safe_str(first_row.get('Tags', '')),
                    'price': safe_str(first_row.get('Variant Price', '')),
                    'sku': safe_str(first_row.get('Variant SKU', '')),
                    'images': []
                }
                
                # Collect all images
                for _, row in group.iterrows():
                    image_src = row.get('Image Src')
                    if pd.notna(image_src) and image_src:
                        product['images'].append(str(image_src))
                
                products.append(product)
            
            self.logger.info(f"Imported {len(products)} products")
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to import CSV: {e}")
            raise
    
    def _generate_handle(self, title: str) -> str:
        """
        Generate a Shopify handle from title
        
        Args:
            title: Product title
        
        Returns:
            str: Handle (URL-friendly identifier)
        """
        import re
        handle = title.lower()
        handle = re.sub(r'[^a-z0-9\s-]', '', handle)
        handle = re.sub(r'\s+', '-', handle)
        handle = re.sub(r'-+', '-', handle)
        return handle.strip('-')
    
    def _format_tags(self, tags: List[str]) -> str:
        """
        Format tags for Shopify CSV
        
        Args:
            tags: List of tags
        
        Returns:
            str: Comma-separated tags
        """
        if isinstance(tags, list):
            return ', '.join(tags)
        return str(tags)
    
    def _clean_html(self, html: str) -> str:
        """
        Clean and format HTML for Shopify
        
        Args:
            html: HTML string
        
        Returns:
            str: Cleaned HTML
        """
        if not html or html == 'nan':
            return ''
        return str(html)
    
    def export_to_csv(self, products: List[Dict], output_path: str = None) -> str:
        """
        Export tagged products to Shopify CSV format
        
        Args:
            products: List of tagged product dictionaries
            output_path: Optional output path
        
        Returns:
            str: Path to created CSV file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.config.output_dir / f'shopify_tagged_products_{timestamp}.csv'
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Exporting {len(products)} products to CSV: {output_path}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.SHOPIFY_HEADERS)
            writer.writeheader()
            
            for product in products:
                handle = product.get('handle') or self._generate_handle(product.get('title', 'product'))
                tags = self._format_tags(product.get('tags', []))
                images = product.get('images', [])
                
                # First row with all product data
                first_row = {
                    'Handle': handle,
                    'Title': product.get('title', ''),
                    'Body (HTML)': self._clean_html(product.get('description', '')),
                    'Vendor': product.get('vendor', self.config.shopify_vendor),
                    'Product Category': product.get('product_category', ''),
                    'Type': product.get('type', self.config.shopify_product_type),
                    'Tags': tags,
                    'Published': 'TRUE' if self.config.auto_publish else 'FALSE',
                    'Variant SKU': product.get('sku', ''),
                    'Variant Inventory Tracker': 'shopify',
                    'Variant Inventory Qty': product.get('inventory_qty', '0'),
                    'Variant Inventory Policy': 'deny',
                    'Variant Fulfillment Service': 'manual',
                    'Variant Price': product.get('price', ''),
                    'Variant Requires Shipping': 'TRUE',
                    'Variant Taxable': 'TRUE',
                    'SEO Title': product.get('title', ''),
                    'SEO Description': product.get('title', ''),
                    'Status': 'active'
                }
                
                # Add first image
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
    
    def export_to_json(self, products: List[Dict], output_path: str = None) -> str:
        """
        Export tagged products to JSON format
        
        Args:
            products: List of tagged product dictionaries
            output_path: Optional output path
        
        Returns:
            str: Path to created JSON file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.config.output_dir / f'tagged_products_{timestamp}.json'
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Exporting {len(products)} products to JSON: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(products, jsonfile, indent=2, ensure_ascii=False)
        
        self.logger.info(f"CSV export completed: {output_path}")
        return str(output_path)
    
    def export_to_csv_update_mode(self, products: List[Dict], output_path: str = None) -> str:
        """
        Export products in update mode - only includes updated fields and preserves identifiers
        
        Args:
            products: List of product dictionaries with original data preserved
            output_path: Optional output path
        
        Returns:
            str: Path to created CSV file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.config.output_dir / f'shopify_update_products_{timestamp}.csv'
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Exporting {len(products)} products to update CSV: {output_path}")
        
        # For update mode, we only include essential fields that are being updated
        update_headers = [
            'Handle',        # Required for identifying existing product
            'Title',         # May have been enhanced
            'Tags',          # Main field being updated
            'Variant SKU'    # Required for variant identification
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=update_headers)
            writer.writeheader()
            
            for product in products:
                # Use original handle and SKU to maintain product identity
                sku = product.get('sku', '')
                if sku == 'nan':  # Handle pandas NaN values
                    sku = ''
                
                update_row = {
                    'Handle': product.get('handle', ''),  # Preserve original handle
                    'Title': product.get('title', ''),   # May be enhanced
                    'Tags': self._format_tags(product.get('tags', [])),  # Updated tags
                    'Variant SKU': sku  # Preserve original SKU
                }
                
                writer.writerow(update_row)
        
        self.logger.info(f"Update CSV export completed: {output_path}")
        return str(output_path)
    
    def export_collections(self, collections: List[Dict], output_path: str = None) -> str:
        """
        Export collection definitions to JSON
        
        Args:
            collections: List of collection dictionaries
            output_path: Optional output path
        
        Returns:
            str: Path to created JSON file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.config.output_dir / f'collections_{timestamp}.json'
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Exporting {len(collections)} collections to JSON: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(collections, jsonfile, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Collections export completed: {output_path}")
        return str(output_path)
