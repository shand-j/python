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
        self._inventory_sku_lookup = None  # Cached inventory lookup
    
    def load_inventory_skus(self, inventory_csv_path: str) -> Dict[str, str]:
        """
        Load SKU lookup from inventory CSV.
        Creates a lookup dict keyed by (handle, option1_name, option1_value).
        
        Args:
            inventory_csv_path: Path to inventory CSV file
            
        Returns:
            Dict mapping (handle, option1_name, option1_value) tuple to SKU
        """
        try:
            # Read with dtype=str for SKU to preserve alphanumeric values
            inv_df = pd.read_csv(inventory_csv_path, low_memory=False, dtype={'SKU': str, 'Variant SKU': str})
            self.logger.info(f"Loading inventory SKUs from: {inventory_csv_path}")
            
            sku_lookup = {}
            for _, row in inv_df.iterrows():
                handle = str(row.get('Handle', '')).strip().lower()
                opt1_name = str(row.get('Option1 Name', '')).strip().lower()
                opt1_value = str(row.get('Option1 Value', '')).strip().lower()
                sku = str(row.get('SKU', '')).strip()
                
                if handle and sku and sku != 'nan':
                    # Primary key: handle + option1 name + option1 value
                    key = (handle, opt1_name, opt1_value)
                    sku_lookup[key] = sku
                    
                    # Also store by handle + option1 value only (fallback)
                    key_simple = (handle, opt1_value)
                    if key_simple not in sku_lookup:
                        sku_lookup[key_simple] = sku
                    
                    # Store by handle only for default variants
                    if opt1_value.lower() == 'default title' or not opt1_value:
                        sku_lookup[(handle,)] = sku
            
            self.logger.info(f"Loaded {len(sku_lookup)} SKU mappings from inventory")
            self._inventory_sku_lookup = sku_lookup
            return sku_lookup
            
        except Exception as e:
            self.logger.warning(f"Failed to load inventory CSV: {e}")
            return {}
    
    def get_sku_for_variant(self, handle: str, opt1_name: str = '', opt1_value: str = '',
                           opt2_name: str = '', opt2_value: str = '') -> str:
        """
        Look up SKU for a specific variant from inventory data.
        
        Args:
            handle: Product handle
            opt1_name: Option1 Name (e.g., 'Flavour', 'Size')
            opt1_value: Option1 Value (e.g., 'Strawberry', '10ml')
            opt2_name: Option2 Name (optional)
            opt2_value: Option2 Value (optional)
            
        Returns:
            SKU string or empty string if not found
        """
        if not self._inventory_sku_lookup:
            return ''
        
        handle_lower = str(handle).strip().lower()
        opt1_name_lower = str(opt1_name).strip().lower() if opt1_name else ''
        opt1_value_lower = str(opt1_value).strip().lower() if opt1_value else ''
        
        # Try exact match first: handle + option1 name + option1 value
        key = (handle_lower, opt1_name_lower, opt1_value_lower)
        if key in self._inventory_sku_lookup:
            return self._inventory_sku_lookup[key]
        
        # Try handle + option1 value only
        key_simple = (handle_lower, opt1_value_lower)
        if key_simple in self._inventory_sku_lookup:
            return self._inventory_sku_lookup[key_simple]
        
        # Try handle only (for default title variants)
        key_handle = (handle_lower,)
        if key_handle in self._inventory_sku_lookup:
            return self._inventory_sku_lookup[key_handle]
        
        return ''
    
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
            # Read with dtype=str for SKU columns to preserve alphanumeric values
            df = pd.read_csv(csv_path, dtype={'Variant SKU': str, 'SKU': str})
            
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
        Export tagged products to Shopify CSV format (legacy single-file export)
        For 3-tier export (clean/review/untagged), use export_to_csv_three_tier()
        
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
        
        # Add metadata columns to headers
        extended_headers = self.SHOPIFY_HEADERS + [
            'Needs Manual Review', 'AI Confidence', 'Model Used', 
            'Failure Reasons', 'Secondary Flavors', 'Category'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=extended_headers)
            writer.writeheader()
            
            for product in products:
                handle = product.get('handle') or self._generate_handle(product.get('title', 'product'))
                tags = self._format_tags(product.get('tags', []))
                images = product.get('images', [])
                
                # Metadata
                needs_review = 'YES' if product.get('needs_manual_review', False) else 'NO'
                ai_confidence = product.get('confidence_scores', {}).get('ai_confidence', 0.0)
                model_used = product.get('model_used', '')
                failure_reasons = '; '.join(product.get('failure_reasons', []))
                tag_breakdown = product.get('tag_breakdown', {})
                secondary_flavors = ', '.join(tag_breakdown.get('secondary_flavors', []))
                category = product.get('category', '')
                
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
                    'Status': 'active',
                    'Needs Manual Review': needs_review,
                    'AI Confidence': f"{ai_confidence:.2f}" if ai_confidence else '',
                    'Model Used': model_used,
                    'Failure Reasons': failure_reasons,
                    'Secondary Flavors': secondary_flavors,
                    'Category': category
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
    
    def export_to_csv_three_tier(self, products: List[Dict], output_dir: str = None) -> Dict[str, str]:
        """
        Export products to 3 separate CSV files based on tagging status:
        1. {timestamp}_tagged_clean.csv - Successfully tagged, no manual review needed
        2. {timestamp}_tagged_review.csv - Tagged but needs manual review
        3. {timestamp}_untagged.csv - No tags generated or failed validation
        
        Args:
            products: List of tagged product dictionaries
            output_dir: Optional output directory
        
        Returns:
            Dict[str, str]: Paths to the 3 created CSV files
        """
        if output_dir is None:
            output_dir = self.config.output_dir
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Separate products into 3 categories
        clean_products = []
        review_products = []
        untagged_products = []
        
        for product in products:
            tags = product.get('tags', [])
            needs_review = product.get('needs_manual_review', False)
            
            if not tags:
                untagged_products.append(product)
            elif needs_review:
                review_products.append(product)
            else:
                clean_products.append(product)
        
        self.logger.info(f"Separating products: {len(clean_products)} clean, {len(review_products)} review, {len(untagged_products)} untagged")
        
        # Export each category
        output_paths = {}
        
        if clean_products:
            clean_path = output_dir / f'{timestamp}_tagged_clean.csv'
            self._export_products_with_metadata(clean_products, clean_path)
            output_paths['clean'] = str(clean_path)
            self.logger.info(f"✅ Clean products exported: {clean_path}")
        
        if review_products:
            review_path = output_dir / f'{timestamp}_tagged_review.csv'
            self._export_products_with_metadata(review_products, review_path)
            output_paths['review'] = str(review_path)
            self.logger.info(f"⚠️  Review products exported: {review_path}")
        
        if untagged_products:
            untagged_path = output_dir / f'{timestamp}_untagged.csv'
            self._export_products_with_metadata(untagged_products, untagged_path)
            output_paths['untagged'] = str(untagged_path)
            self.logger.info(f"❌ Untagged products exported: {untagged_path}")
        
        return output_paths
    
    def _export_products_with_metadata(self, products: List[Dict], output_path: Path):
        """
        Helper to export products with full metadata columns
        
        Args:
            products: List of product dictionaries
            output_path: Output file path
        """
        # Extended headers with metadata
        extended_headers = self.SHOPIFY_HEADERS + [
            'Needs Manual Review', 'AI Confidence', 'Model Used', 
            'Failure Reasons', 'Secondary Flavors', 'Category',
            'Rule Based Tags', 'AI Suggested Tags'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=extended_headers)
            writer.writeheader()
            
            for product in products:
                handle = product.get('handle') or self._generate_handle(product.get('title', 'product'))
                tags = self._format_tags(product.get('tags', []))
                images = product.get('images', [])
                
                # Metadata
                needs_review = 'YES' if product.get('needs_manual_review', False) else 'NO'
                ai_confidence = product.get('confidence_scores', {}).get('ai_confidence', 0.0)
                model_used = product.get('model_used', '')
                failure_reasons = '; '.join(product.get('failure_reasons', []))
                tag_breakdown = product.get('tag_breakdown', {})
                secondary_flavors = ', '.join(tag_breakdown.get('secondary_flavors', []))
                rule_based_tags = ', '.join(tag_breakdown.get('rule_based_tags', []))
                ai_suggested_tags = ', '.join(tag_breakdown.get('ai_suggested_tags', []))
                category = product.get('category', '')
                
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
                    'Status': 'active',
                    'Needs Manual Review': needs_review,
                    'AI Confidence': f"{ai_confidence:.2f}" if ai_confidence else '',
                    'Model Used': model_used,
                    'Failure Reasons': failure_reasons,
                    'Secondary Flavors': secondary_flavors,
                    'Category': category,
                    'Rule Based Tags': rule_based_tags,
                    'AI Suggested Tags': ai_suggested_tags
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
    
    def export_with_original_variants(self, 
                                       products: List[Dict], 
                                       original_csv_path: str,
                                       output_dir: str = None,
                                       inventory_csv_path: str = None) -> Dict[str, str]:
        """
        Export tagged products while preserving ALL original variant rows.
        
        This is critical for Shopify imports - tags are applied at the product level
        but all variant rows must be preserved with the same tags.
        
        Args:
            products: List of tagged product dictionaries (keyed by handle)
            original_csv_path: Path to original input CSV with all variants
            output_dir: Output directory
            inventory_csv_path: Optional path to inventory CSV for SKU lookup
            
        Returns:
            Dict with paths to clean, review, and untagged CSVs
        """
        if output_dir is None:
            output_dir = self.config.output_dir
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Load inventory SKUs if path provided
        if inventory_csv_path:
            self.load_inventory_skus(inventory_csv_path)
        
        # Build lookup dict from tagged products
        products_by_handle = {}
        for product in products:
            handle = product.get('handle', '')
            if handle:
                products_by_handle[handle] = product
        
        self.logger.info(f"Merging tags for {len(products_by_handle)} products back to original CSV")
        
        # Read original CSV preserving all rows (dtype=str for SKU to preserve alphanumeric values)
        original_df = pd.read_csv(original_csv_path, low_memory=False, dtype={'Variant SKU': str, 'SKU': str})
        self.logger.info(f"Original CSV has {len(original_df)} rows")
        
        # Add metadata columns
        metadata_cols = [
            'Needs Manual Review', 'AI Confidence', 'Model Used',
            'Failure Reasons', 'Secondary Flavors', 'Category',
            'Rule Based Tags', 'AI Suggested Tags'
        ]
        for col in metadata_cols:
            if col not in original_df.columns:
                original_df[col] = ''
        
        # Categorize rows and apply tags
        clean_rows = []
        review_rows = []
        untagged_rows = []
        
        # Import taxonomy for variant-level flavor detection
        from modules.taxonomy import VapeTaxonomy
        import re
        
        # All possible flavor tags to potentially replace
        ALL_FLAVOR_TAGS = {'fruity', 'ice', 'tobacco', 'desserts/bakery', 'beverages', 
                          'nuts', 'spices_&_herbs', 'cereal', 'unflavoured', 'candy/sweets'}
        
        # All VG ratio tags (to replace at variant level)
        ALL_VG_RATIO_TAGS = {f"{vg}/{100-vg}" for vg in range(0, 101)}
        
        # Vaping style tags (derived from VG ratio)
        ALL_VAPING_STYLE_TAGS = {'mouth-to-lung', 'direct-to-lung', 'restricted-direct-to-lung'}
        
        def extract_vg_ratio_from_text(text: str) -> str:
            """Extract VG/PG ratio from variant text (e.g., '70VG/30PG', '50/50')"""
            if not text:
                return ""
            text_lower = text.lower()
            
            # Handle 100VG or 100PG
            if re.search(r'\b100\s*vg\b', text_lower):
                return "100/0"
            if re.search(r'\b100\s*pg\b', text_lower):
                return "0/100"
            
            # Pattern to find ratios
            patterns = [
                r'(\d+)\s*vg\s*/?\s*(\d+)\s*pg',  # 70VG/30PG or 70VG30PG
                r'(\d+)\s*/\s*(\d+)',              # 70/30
                r'(\d+)\s*vg\s+(\d+)\s*pg',        # 70VG 30PG
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    try:
                        vg = int(match.group(1))
                        pg = int(match.group(2))
                        # VG is usually the larger number in naming conventions
                        if vg < pg:
                            vg, pg = pg, vg
                        if vg + pg == 100:
                            return f"{vg}/{pg}"
                    except (ValueError, IndexError):
                        continue
            return ""
        
        def derive_vaping_style_from_ratio(ratio: str) -> str:
            """Derive vaping style from VG/PG ratio"""
            if not ratio:
                return ""
            try:
                vg = int(ratio.split('/')[0])
                # High VG (70%+) = Direct-to-lung (sub-ohm, bigger clouds)
                if vg >= 70:
                    return "direct-to-lung"
                # 50/50 or lower VG = Mouth-to-lung (tighter draw, more throat hit)
                elif vg <= 50:
                    return "mouth-to-lung"
                # 51-69% could be RDTL but we'll default to not adding a style tag
                # as it's ambiguous
                else:
                    return ""
            except (ValueError, IndexError):
                return ""
        
        # Track image-only rows filtered
        image_only_count = 0
        
        for idx, row in original_df.iterrows():
            handle = row.get('Handle', '')
            
            # Skip image-only rows (no Option1 Value AND no Variant Price)
            # These are additional image rows in Shopify format, not purchasable variants
            option1_value = row.get('Option1 Value', '')
            variant_price = row.get('Variant Price', '')
            is_image_only = (pd.isna(option1_value) or option1_value == '') and (pd.isna(variant_price) or variant_price == '')
            if is_image_only:
                image_only_count += 1
                continue
            
            row_dict = row.to_dict()
            
            if handle in products_by_handle:
                product = products_by_handle[handle]
                base_tags = list(product.get('tags', []))  # Copy to avoid mutation
                needs_review = product.get('needs_manual_review', False)
                category = product.get('category', '')
                
                # Detect variant-specific tags from Option1 Value
                option1_value = row.get('Option1 Value', '')
                option1_name = row.get('Option1 Name', '')
                option1_str = str(option1_value) if pd.notna(option1_value) and option1_value else ''
                
                if option1_str:
                    # Variant-level flavor detection
                    variant_flavors = VapeTaxonomy.detect_flavor_types(option1_str)
                    if variant_flavors:
                        # REPLACE product-level flavor tags with variant-specific ones
                        base_tags = [t for t in base_tags if t not in ALL_FLAVOR_TAGS]
                        base_tags.extend(variant_flavors)
                    
                    # Variant-level VG/PG ratio detection
                    variant_vg_ratio = extract_vg_ratio_from_text(option1_str)
                    if variant_vg_ratio:
                        # REPLACE product-level VG ratio with variant-specific one
                        base_tags = [t for t in base_tags if t not in ALL_VG_RATIO_TAGS]
                        base_tags.append(variant_vg_ratio)
                        
                        # Derive and apply vaping style from VG ratio
                        variant_vaping_style = derive_vaping_style_from_ratio(variant_vg_ratio)
                        if variant_vaping_style:
                            # REPLACE product-level vaping style with derived one
                            base_tags = [t for t in base_tags if t not in ALL_VAPING_STYLE_TAGS]
                            base_tags.append(variant_vaping_style)
                
                # Look up SKU from inventory if available
                if self._inventory_sku_lookup:
                    sku = self.get_sku_for_variant(
                        handle=handle,
                        opt1_name=str(option1_name) if pd.notna(option1_name) else '',
                        opt1_value=option1_str
                    )
                    if sku:
                        row_dict['Variant SKU'] = sku
                
                # Apply tags to this row
                row_dict['Tags'] = self._format_tags(base_tags)
                
                # Apply metadata
                tag_breakdown = product.get('tag_breakdown', {})
                row_dict['Needs Manual Review'] = 'YES' if needs_review else 'NO'
                row_dict['AI Confidence'] = f"{product.get('confidence_scores', {}).get('ai_confidence', 0.0):.2f}"
                row_dict['Model Used'] = product.get('model_used', '')
                row_dict['Failure Reasons'] = '; '.join(product.get('failure_reasons', []))
                row_dict['Secondary Flavors'] = ', '.join(tag_breakdown.get('secondary_flavors', []))
                row_dict['Category'] = category
                row_dict['Rule Based Tags'] = ', '.join(tag_breakdown.get('rule_based_tags', []))
                row_dict['AI Suggested Tags'] = ', '.join(tag_breakdown.get('ai_suggested_tags', []))
                
                # Categorize
                if not base_tags:
                    untagged_rows.append(row_dict)
                elif needs_review:
                    review_rows.append(row_dict)
                else:
                    clean_rows.append(row_dict)
            else:
                # Product not in tagged list - mark as untagged
                row_dict['Needs Manual Review'] = 'YES'
                row_dict['Category'] = 'unknown'
                untagged_rows.append(row_dict)
        
        self.logger.info(f"Filtered out {image_only_count} image-only rows (no variant/price data)")
        self.logger.info(f"Categorized: {len(clean_rows)} clean rows, {len(review_rows)} review rows, {len(untagged_rows)} untagged rows")
        
        # Get column order (original columns + metadata)
        all_columns = list(original_df.columns)
        
        # Export each category
        output_paths = {}
        
        if clean_rows:
            clean_df = pd.DataFrame(clean_rows)[all_columns]
            clean_path = output_dir / f'{timestamp}_tagged_clean.csv'
            clean_df.to_csv(clean_path, index=False)
            output_paths['clean'] = str(clean_path)
            unique_clean = clean_df['Handle'].nunique()
            self.logger.info(f"✅ Clean: {len(clean_rows)} rows ({unique_clean} products) → {clean_path}")
        
        if review_rows:
            review_df = pd.DataFrame(review_rows)[all_columns]
            review_path = output_dir / f'{timestamp}_tagged_review.csv'
            review_df.to_csv(review_path, index=False)
            output_paths['review'] = str(review_path)
            unique_review = review_df['Handle'].nunique()
            self.logger.info(f"⚠️  Review: {len(review_rows)} rows ({unique_review} products) → {review_path}")
        
        if untagged_rows:
            untagged_df = pd.DataFrame(untagged_rows)[all_columns]
            untagged_path = output_dir / f'{timestamp}_untagged.csv'
            untagged_df.to_csv(untagged_path, index=False)
            output_paths['untagged'] = str(untagged_path)
            unique_untagged = untagged_df['Handle'].nunique()
            self.logger.info(f"❌ Untagged: {len(untagged_rows)} rows ({unique_untagged} products) → {untagged_path}")
        
        return output_paths
    
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
