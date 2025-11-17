#!/usr/bin/env python3
"""
Vape Product Tagger - Main Application
Intelligent AI-powered tagging pipeline for vaping products in Shopify
"""
import sys
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules import (
    Config, setup_logger, VapeTaxonomy, OllamaProcessor,
    ProductTagger, ShopifyHandler
)


def parse_arguments():
    """
    Parse command line arguments
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Vape Product Tagger - Intelligent AI-powered tagging for vaping products',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Tag products from Shopify CSV export
  python main.py --input products.csv
  
  # Tag with custom config
  python main.py --input products.csv --config config.env
  
  # Export to JSON format
  python main.py --input products.csv --format json
  
  # Disable AI tagging (rule-based only)
  python main.py --input products.csv --no-ai
  
  # Generate collections
  python main.py --input products.csv --collections
        """
    )
    
    # Input options
    parser.add_argument(
        '--input', '-i',
        type=str,
        required=True,
        help='Input Shopify CSV file path'
    )
    
    # Configuration
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (config.env)'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (optional, auto-generated if not specified)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['csv', 'json'],
        default='csv',
        help='Output format (default: csv)'
    )
    
    # Processing options
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable AI-powered tagging (use only rule-based tagging)'
    )
    
    parser.add_argument(
        '--collections',
        action='store_true',
        help='Generate dynamic collections based on tags'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        help='Batch size for processing (overrides config)'
    )
    
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing'
    )
    
    # Logging
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Quiet mode (minimal output)'
    )
    
    return parser.parse_args()


def process_product(product, tagger, use_ai):
    """
    Process a single product
    
    Args:
        product: Product dictionary
        tagger: ProductTagger instance
        use_ai: Whether to use AI tagging
    
    Returns:
        Dict: Tagged product
    """
    return tagger.tag_product(product, use_ai=use_ai)


def main():
    """Main application entry point"""
    args = parse_arguments()
    
    # Initialize configuration
    try:
        config = Config(args.config)
        
        # Override config with command line arguments
        if args.batch_size:
            config.batch_size = args.batch_size
        if args.no_parallel:
            config.parallel_processing = False
        
        is_valid, error = config.validate()
        if not is_valid:
            print(f"Configuration error: {error}")
            return 1
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return 1
    
    # Set up logging
    log_level = 'DEBUG' if args.verbose else ('ERROR' if args.quiet else config.log_level)
    logger = setup_logger(
        name='vape-tagger',
        log_dir=str(config.logs_dir),
        level=log_level,
        verbose=args.verbose
    )
    
    logger.info("=" * 70)
    logger.info("Vape Product Tagger - Starting")
    logger.info("=" * 70)
    
    # Check input file
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1
    
    # Initialize components
    try:
        shopify_handler = ShopifyHandler(config, logger)
        
        # Initialize Ollama processor if AI is enabled
        ollama = None
        if not args.no_ai and config.enable_ai_tagging:
            logger.info("Initializing Ollama AI processor...")
            ollama = OllamaProcessor(config, logger)
            
            if not ollama.check_ollama_availability():
                logger.warning("Ollama service not available, falling back to rule-based tagging")
                ollama = None
            else:
                logger.info(f"Ollama connected successfully (model: {config.ollama_model})")
        
        # Initialize product tagger
        tagger = ProductTagger(config, logger, ollama)
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        return 1
    
    # Import products
    try:
        logger.info(f"Importing products from: {args.input}")
        products = shopify_handler.import_from_csv(args.input)
        logger.info(f"Loaded {len(products)} products")
    except Exception as e:
        logger.error(f"Failed to import products: {e}")
        return 1
    
    # Process products
    try:
        logger.info("Starting product tagging...")
        tagged_products = []
        use_ai = not args.no_ai and ollama is not None
        
        if config.parallel_processing and not args.no_parallel and len(products) > 1:
            # Parallel processing
            logger.info(f"Processing products in parallel (workers: {config.max_workers})")
            with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
                futures = {
                    executor.submit(process_product, product, tagger, use_ai): product
                    for product in products
                }
                
                for future in as_completed(futures):
                    try:
                        tagged_product = future.result()
                        tagged_products.append(tagged_product)
                        logger.info(f"Tagged: {tagged_product.get('title', 'Unknown')} "
                                  f"({len(tagged_product.get('tags', []))} tags)")
                    except Exception as e:
                        product = futures[future]
                        logger.error(f"Failed to tag product '{product.get('title')}': {e}")
        else:
            # Sequential processing
            logger.info("Processing products sequentially")
            for i, product in enumerate(products, 1):
                try:
                    tagged_product = tagger.tag_product(product, use_ai=use_ai)
                    tagged_products.append(tagged_product)
                    logger.info(f"[{i}/{len(products)}] Tagged: {tagged_product.get('title', 'Unknown')} "
                              f"({len(tagged_product.get('tags', []))} tags)")
                except Exception as e:
                    logger.error(f"Failed to tag product '{product.get('title')}': {e}")
        
        logger.info(f"Successfully tagged {len(tagged_products)} products")
        
    except Exception as e:
        logger.error(f"Error during product tagging: {e}")
        return 1
    
    # Export tagged products
    try:
        if args.format == 'json':
            output_path = shopify_handler.export_to_json(tagged_products, args.output)
        else:
            output_path = shopify_handler.export_to_csv(tagged_products, args.output)
        
        logger.info(f"Tagged products exported to: {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to export products: {e}")
        return 1
    
    # Generate collections if requested
    if args.collections:
        try:
            logger.info("Generating dynamic collections...")
            collections = tagger.generate_collections(tagged_products)
            
            if collections:
                collections_path = shopify_handler.export_collections(collections)
                logger.info(f"Collections exported to: {collections_path}")
            else:
                logger.info("No collections generated")
                
        except Exception as e:
            logger.error(f"Failed to generate collections: {e}")
    
    logger.info("=" * 70)
    logger.info("Vape Product Tagger - Completed Successfully")
    logger.info("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
