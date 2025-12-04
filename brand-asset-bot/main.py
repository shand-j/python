#!/usr/bin/env python3
"""
Product Data Scraper - Main Application
Scrapes product data from e-commerce websites and prepares for Shopify import
"""
import sys
import argparse
from pathlib import Path

from modules import Config, setup_logger, ProductScraper, BrandAssetScraper


def parse_arguments():
    """
    Parse command line arguments
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Brand Asset Bot - Discover and process brand marketing imagery',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Product scraping mode (legacy)
  python main.py --mode product https://example.com/product-page
  
  # Brand asset discovery mode
  python main.py --mode brand-asset --brand SMOK
  
  # Brand asset with competitor sources
  python main.py --mode brand-asset --brand SMOK --include-competitors
  
  # UK-only brand assets
  python main.py --mode brand-asset --brand Vape-bars --uk-only
  
  # Process all brands from brands.txt
  python main.py --mode brand-asset --all-brands
        """
    )
    
    # Mode selection
    parser.add_argument(
        '--mode',
        choices=['product', 'brand-asset'],
        default='product',
        help='Operation mode (default: product)'
    )
    
    # Brand asset mode options
    parser.add_argument(
        '--brand', '-b',
        type=str,
        help='Brand name for asset discovery (brand-asset mode)'
    )
    parser.add_argument(
        '--all-brands',
        action='store_true',
        help='Process all brands from brands.txt file'
    )
    parser.add_argument(
        '--include-competitors',
        action='store_true',
        help='Include competitor sources in brand asset discovery'
    )
    parser.add_argument(
        '--uk-only',
        action='store_true',
        help='Only discover UK-specific media packs'
    )
    
    # URL input options
    parser.add_argument(
        'urls',
        nargs='*',
        help='Product page URLs to scrape (product mode)'
    )
    parser.add_argument(
        '--file', '-f',
        type=str,
        help='File containing product URLs (one per line)'
    )
    
    # Configuration options
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (default: config.env)'
    )
    
    # Processing options
    parser.add_argument(
        '--no-enhance',
        action='store_true',
        help='Skip GPT description enhancement'
    )
    parser.add_argument(
        '--no-tags',
        action='store_true',
        help='Skip GPT tag generation'
    )
    parser.add_argument(
        '--no-images',
        action='store_true',
        help='Skip image downloading and processing'
    )
    
    # Output options
    parser.add_argument(
        '--format',
        choices=['csv', 'json'],
        default='csv',
        help='Output format (default: csv)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (default: auto-generated in output directory)'
    )
    
    # Other options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Validate arguments based on mode
    if args.mode == 'product':
        if not args.urls and not args.file:
            parser.error('Product mode requires URLs or --file option')
        if args.urls and args.file:
            parser.error('Cannot use both URL arguments and --file option. Choose one.')
    elif args.mode == 'brand-asset':
        if not args.brand and not args.all_brands:
            parser.error('Brand-asset mode requires --brand or --all-brands option')
        if args.brand and args.all_brands:
            parser.error('Cannot use both --brand and --all-brands options. Choose one.')
    
    return args


def load_urls_from_file(file_path):
    """
    Load URLs from a text file
    
    Args:
        file_path: Path to file containing URLs
    
    Returns:
        list: List of URLs
    """
    urls = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)
    return urls


def load_brands_from_file(file_path):
    """
    Load brands from brands.txt file
    
    Args:
        file_path: Path to brands.txt file
    
    Returns:
        list: List of brand names
    """
    brands = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse brand|website|priority format, extract brand name
                parts = line.split('|')
                if len(parts) >= 1:
                    brands.append(parts[0].strip())
    return brands


def _run_product_scraper(args, config, logger):
    """Run product scraping mode"""
    # Load URLs
    try:
        if args.file:
            logger.info(f"Loading URLs from file: {args.file}")
            urls = load_urls_from_file(args.file)
        else:
            urls = args.urls
        
        if not urls:
            logger.error("No URLs provided")
            return 1
        
        logger.info(f"Processing {len(urls)} URL(s)")
        
    except Exception as e:
        logger.error(f"Error loading URLs: {e}")
        return 1
    
    # Initialize scraper
    try:
        scraper = ProductScraper(config, logger)
    except Exception as e:
        logger.error(f"Error initializing scraper: {e}")
        return 1
    
    # Scrape and export products
    try:
        logger.info("Starting product scraping...")
        
        products, output_file = scraper.scrape_and_export(
            urls,
            export_format=args.format,
            output_path=args.output,
            enhance_description=not args.no_enhance,
            generate_tags=not args.no_tags,
            process_images=not args.no_images
        )
        
        if products:
            logger.info(f"Successfully processed {len(products)} product(s)")
            if output_file:
                logger.info(f"Output file created: {output_file}")
                print(f"\n✓ Success! Output file: {output_file}")
            else:
                logger.warning("No output file created")
        else:
            logger.error("No products were successfully processed")
            return 1
        
        logger.info("=" * 80)
        logger.info("Product Data Scraper Completed")
        logger.info("=" * 80)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error during scraping: {e}", exc_info=True)
        return 1


def _run_brand_asset_bot(args, config, logger):
    """Run brand asset discovery mode"""
    try:
        # Initialize brand asset scraper
        scraper = BrandAssetScraper(config, logger)
    except Exception as e:
        logger.error(f"Error initializing brand asset scraper: {e}")
        return 1
    
    # Discover brand assets
    try:
        logger.info(f"Starting brand asset discovery for: {args.brand}")
        
        results = scraper.discover_brand_assets(
            args.brand,
            include_competitors=args.include_competitors,
            uk_only=args.uk_only
        )
        
        if results['official_assets'] or results['competitor_assets']:
            total_assets = len(results['official_assets']) + len(results['competitor_assets'])
            logger.info(f"Successfully discovered {total_assets} asset(s)")
            
            # Export catalog
            export_file = scraper.export_brand_catalog(args.brand)
            if export_file:
                logger.info(f"Catalog exported: {export_file}")
                print(f"\n✓ Success! Catalog exported: {export_file}")
            else:
                logger.warning("Catalog export failed")
        else:
            logger.warning("No assets were discovered")
        
        logger.info("=" * 80)
        logger.info("Brand Asset Bot Completed")
        logger.info("=" * 80)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error during brand asset discovery: {e}", exc_info=True)
        return 1


def _run_brand_asset_bot_for_brand(args, config, logger, brand_name):
    """Run brand asset discovery mode for a specific brand"""
    try:
        # Initialize brand asset scraper
        scraper = BrandAssetScraper(config, logger)
    except Exception as e:
        logger.error(f"Error initializing brand asset scraper for {brand_name}: {e}")
        return 1
    
    # Discover brand assets
    try:
        logger.info(f"Starting brand asset discovery for: {brand_name}")
        
        results = scraper.discover_brand_assets(
            brand_name,
            include_competitors=args.include_competitors,
            uk_only=args.uk_only
        )
        
        if results['official_assets'] or results['competitor_assets']:
            total_assets = len(results['official_assets']) + len(results['competitor_assets'])
            logger.info(f"Successfully discovered {total_assets} asset(s) for {brand_name}")
            
            # Export catalog
            export_file = scraper.export_brand_catalog(brand_name)
            if export_file:
                logger.info(f"Catalog exported for {brand_name}: {export_file}")
            else:
                logger.warning(f"Catalog export failed for {brand_name}")
        else:
            logger.warning(f"No assets were discovered for {brand_name}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error during brand asset discovery for {brand_name}: {e}", exc_info=True)
        return 1


def main():
    """Main application entry point"""
    args = parse_arguments()
    
    # Load configuration
    try:
        config = Config(args.config)
        
        # Override log level if verbose
        if args.verbose:
            config.log_level = 'DEBUG'
        
        # Validate configuration
        is_valid, error_msg = config.validate()
        if not is_valid:
            print(f"Configuration error: {error_msg}")
            print("\nNote: Some features may be disabled without proper configuration.")
            print("Create a config.env file based on config.env.example")
            
            # Allow to continue if only OpenAI key is missing
            if "OPENAI_API_KEY" not in error_msg:
                return 1
            else:
                print("\nContinuing with limited functionality (no GPT features)...")
    
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return 1
    
    # Setup logger
    if args.mode == 'product':
        logger = setup_logger('ProductScraper', config.logs_dir, config.log_level)
        logger.info("=" * 80)
        logger.info("Product Data Scraper Started")
        logger.info("=" * 80)
    else:
        logger = setup_logger('BrandAssetBot', config.logs_dir, config.log_level)
        logger.info("=" * 80)
        logger.info("Brand Asset Bot Started")
        logger.info("=" * 80)
    
    # Execute based on mode
    if args.mode == 'product':
        return _run_product_scraper(args, config, logger)
    else:
        if args.all_brands:
            # Load all brands from brands.txt
            brands_file = Path("brands.txt")
            if not brands_file.exists():
                logger.error(f"Brands file not found: {brands_file}")
                return 1
            
            brands = load_brands_from_file(brands_file)
            if not brands:
                logger.error("No brands found in brands.txt")
                return 1
            
            logger.info(f"Processing {len(brands)} brands from brands.txt")
            
            # Process each brand
            success_count = 0
            for brand_name in brands:
                logger.info(f"Starting batch processing for brand: {brand_name}")
                try:
                    result = _run_brand_asset_bot_for_brand(args, config, logger, brand_name)
                    if result == 0:
                        success_count += 1
                    # Continue processing other brands even if one fails
                except Exception as e:
                    logger.error(f"Failed to process brand {brand_name}: {e}")
                    continue
            
            logger.info(f"Batch processing completed. Successfully processed {success_count}/{len(brands)} brands")
            logger.info("=" * 80)
            logger.info("Brand Asset Bot Batch Processing Completed")
            logger.info("=" * 80)
            
            return 0 if success_count > 0 else 1
        else:
            return _run_brand_asset_bot(args, config, logger)


if __name__ == '__main__':
    sys.exit(main())
