#!/usr/bin/env python3
"""
Product Data Scraper - Main Application
Scrapes product data from e-commerce websites and prepares for Shopify import
"""
import sys
import argparse
from pathlib import Path

from modules import Config, setup_logger, ProductScraper


def parse_arguments():
    """
    Parse command line arguments
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Product Data Scraper - Extract and process product data for Shopify import',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape a single product
  python main.py https://example.com/product-page
  
  # Scrape multiple products from a file
  python main.py --file urls.txt
  
  # Scrape with custom config
  python main.py --config config.env https://example.com/product-page
  
  # Export to JSON instead of CSV
  python main.py --format json https://example.com/product-page
  
  # Skip image processing
  python main.py --no-images https://example.com/product-page
        """
    )
    
    # URL input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        'urls',
        nargs='*',
        help='Product page URLs to scrape'
    )
    input_group.add_argument(
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
    
    # Handle URL input
    if args.file:
        args.urls = []
    elif not args.urls:
        parser.error('Either provide URLs or use --file option')
    
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
    logger = setup_logger('ProductScraper', config.logs_dir, config.log_level)
    
    logger.info("=" * 80)
    logger.info("Product Data Scraper Started")
    logger.info("=" * 80)
    
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


if __name__ == '__main__':
    sys.exit(main())
