#!/usr/bin/env python3
"""
Competitor Site Manager CLI
Command-line interface for managing competitor website configurations
"""
import sys
import argparse
from pathlib import Path

from modules import (
    Config, setup_logger,
    CompetitorSite, CompetitorSiteManager,
    ScrapingParameters, SitePriority, SiteStatus,
    RobotsTxtParser, SiteHealthMonitor, UserAgentRotator,
    ProductDiscovery, DiscoveredProduct, ProductInventory,
    BrandManager, ImageExtractor, ExtractedImage, CompetitorImageDownloader
)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Competitor Site Manager - Configure competitor websites for ethical scraping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load competitor sites from file
  python competitor_manager.py load sites.txt
  
  # Check site health
  python competitor_manager.py health
  
  # Check robots.txt compliance
  python competitor_manager.py robots --site "Vape UK"
  
  # List all sites
  python competitor_manager.py list
  
  # Add a new site
  python competitor_manager.py add "Vape UK" "https://vapeuk.co.uk" --priority high
  
  # Analyze site structure
  python competitor_manager.py analyze --site "Vape UK"
  
  # Discover products on competitor sites
  python competitor_manager.py discover --brands brands_registry.json --save
  
  # Discover from specific site
  python competitor_manager.py discover --site "Vape UK" --brands brands.txt --max-pages 20
  
  # View discovered products
  python competitor_manager.py products --brand "SMOK"
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.env',
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--registry', '-r',
        type=str,
        default='competitor_sites_registry.json',
        help='Competitor sites registry file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Load command
    load_parser = subparsers.add_parser('load', help='Load sites from file')
    load_parser.add_argument('file', type=str, help='File path (pipe-delimited: Name|URL|Priority)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List competitor sites')
    list_parser.add_argument(
        '--priority', '-p',
        choices=['high', 'medium', 'low'],
        help='Filter by priority'
    )
    list_parser.add_argument(
        '--status', '-s',
        choices=['pending', 'active', 'blocked', 'inactive'],
        help='Filter by status'
    )
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add competitor site')
    add_parser.add_argument('name', type=str, help='Site name')
    add_parser.add_argument('url', type=str, help='Base URL')
    add_parser.add_argument(
        '--priority', '-p',
        choices=['high', 'medium', 'low'],
        default='medium',
        help='Priority (default: medium)'
    )
    add_parser.add_argument(
        '--delay', '-d',
        type=float,
        default=2.0,
        help='Request delay in seconds (default: 2.0)'
    )
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update site')
    update_parser.add_argument('name', type=str, help='Site name')
    update_parser.add_argument(
        '--priority', '-p',
        choices=['high', 'medium', 'low'],
        help='New priority'
    )
    update_parser.add_argument(
        '--status', '-s',
        choices=['pending', 'active', 'blocked', 'inactive'],
        help='New status'
    )
    update_parser.add_argument(
        '--delay', '-d',
        type=float,
        help='New request delay'
    )
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove site')
    remove_parser.add_argument('name', type=str, help='Site name')
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Check site health')
    health_parser.add_argument(
        '--site', '-s',
        type=str,
        help='Check specific site only'
    )
    
    # Robots command
    robots_parser = subparsers.add_parser('robots', help='Check robots.txt compliance')
    robots_parser.add_argument(
        '--site', '-s',
        type=str,
        required=True,
        help='Site name to check'
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze site structure')
    analyze_parser.add_argument(
        '--site', '-s',
        type=str,
        required=True,
        help='Site name to analyze'
    )
    
    # History command
    subparsers.add_parser('history', help='Show registry history')
    
    # Discover command
    discover_parser = subparsers.add_parser('discover', help='Discover products on competitor sites')
    discover_parser.add_argument(
        '--site', '-s',
        type=str,
        help='Discover from specific site only'
    )
    discover_parser.add_argument(
        '--brands', '-b',
        type=str,
        help='Brand list file (one brand per line) or brands_registry.json'
    )
    discover_parser.add_argument(
        '--max-pages', '-m',
        type=int,
        default=10,
        help='Max pages per category (default: 10)'
    )
    discover_parser.add_argument(
        '--save', '-o',
        action='store_true',
        help='Save discovered products to inventory'
    )
    
    # Products command
    products_parser = subparsers.add_parser('products', help='View discovered products')
    products_parser.add_argument(
        '--site', '-s',
        type=str,
        help='Filter by competitor site'
    )
    products_parser.add_argument(
        '--brand', '-b',
        type=str,
        help='Filter by brand'
    )
    products_parser.add_argument(
        '--category', '-c',
        type=str,
        help='Filter by category'
    )
    
    # Extract-images command
    extract_parser = subparsers.add_parser('extract-images', help='Extract images from discovered products')
    extract_parser.add_argument(
        '--brand', '-b',
        type=str,
        help='Extract images for specific brand only'
    )
    extract_parser.add_argument(
        '--site', '-s',
        type=str,
        help='Extract from specific competitor site only'
    )
    extract_parser.add_argument(
        '--max-products', '-p',
        type=int,
        default=10,
        help='Maximum products to process (default: 10)'
    )
    extract_parser.add_argument(
        '--images-per-product', '-i',
        type=int,
        default=5,
        help='Maximum images per product (default: 5)'
    )
    extract_parser.add_argument(
        '--min-quality', '-q',
        type=int,
        default=50,
        help='Minimum quality score 0-100 (default: 50)'
    )
    extract_parser.add_argument(
        '--save', '-o',
        action='store_true',
        help='Download and save images'
    )
    
    # Images command
    images_parser = subparsers.add_parser('images', help='View downloaded images summary')
    images_parser.add_argument(
        '--brand', '-b',
        type=str,
        help='Filter by brand'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    return args


def cmd_load(args, site_manager, logger):
    """Load sites from file"""
    file_path = Path(args.file)
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return 1
    
    logger.info(f"Loading competitor sites from: {file_path}")
    
    count = site_manager.load_sites_from_file(file_path)
    
    if count > 0:
        logger.info(f"✓ Loaded {count} competitor sites")
        return 0
    else:
        logger.error("No sites loaded")
        return 1


def cmd_list(args, site_manager, logger):
    """List competitor sites"""
    # Get sites based on filters
    if args.priority:
        sites = site_manager.get_sites_by_priority(args.priority)
    elif args.status:
        sites = site_manager.get_sites_by_status(args.status)
    else:
        sites = site_manager.get_all_sites()
    
    if not sites:
        logger.info("No competitor sites found")
        return 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Competitor Sites ({len(sites)} site(s))")
    logger.info('='*60)
    
    for site in sites:
        logger.info(f"\n{site.name}")
        logger.info(f"  URL: {site.base_url}")
        logger.info(f"  Priority: {site.priority}")
        logger.info(f"  Status: {site.status}")
        logger.info(f"  Request Delay: {site.scraping_params.request_delay}s")
        
        if site.robots_txt_info.crawl_delay:
            logger.info(f"  Crawl Delay: {site.robots_txt_info.crawl_delay}s")
        
        if site.site_health.last_check:
            logger.info(f"  Last Health Check: {site.site_health.last_check}")
            if site.site_health.response_time_ms:
                logger.info(f"  Response Time: {site.site_health.response_time_ms:.0f}ms")
    
    return 0


def cmd_add(args, site_manager, logger):
    """Add competitor site"""
    # Create scraping parameters
    params = ScrapingParameters(request_delay=args.delay)
    
    # Create site
    site = CompetitorSite(
        name=args.name,
        base_url=args.url,
        priority=args.priority,
        scraping_params=params
    )
    
    if site_manager.add_site(site):
        logger.info(f"✓ Added competitor site: {args.name}")
        return 0
    else:
        logger.error(f"Failed to add site: {args.name}")
        return 1


def cmd_update(args, site_manager, logger):
    """Update competitor site"""
    updates = {}
    
    if args.priority:
        updates['priority'] = args.priority
    
    if args.status:
        updates['status'] = args.status
    
    if args.delay:
        site = site_manager.get_site(args.name)
        if site:
            site.scraping_params.request_delay = args.delay
            updates['scraping_params'] = site.scraping_params
    
    if not updates:
        logger.error("No updates specified")
        return 1
    
    if site_manager.update_site(args.name, **updates):
        logger.info(f"✓ Updated site: {args.name}")
        return 0
    else:
        logger.error(f"Failed to update site: {args.name}")
        return 1


def cmd_remove(args, site_manager, logger):
    """Remove competitor site"""
    if site_manager.remove_site(args.name):
        logger.info(f"✓ Removed site: {args.name}")
        return 0
    else:
        logger.error(f"Failed to remove site: {args.name}")
        return 1


def cmd_health(args, site_manager, health_monitor, logger):
    """Check site health"""
    if args.site:
        site = site_manager.get_site(args.site)
        if not site:
            logger.error(f"Site not found: {args.site}")
            return 1
        sites = [site]
    else:
        sites = site_manager.get_all_sites()
    
    if not sites:
        logger.info("No sites to check")
        return 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Site Health Check ({len(sites)} site(s))")
    logger.info('='*60)
    
    for site in sites:
        health = health_monitor.check_site_health(site.name, site.base_url)
        
        # Update site health in registry
        site.site_health = SiteHealth.from_dict(health)
        site_manager.update_site(site.name, site_health=site.site_health)
    
    return 0


def cmd_robots(args, site_manager, robots_parser, logger):
    """Check robots.txt compliance"""
    site = site_manager.get_site(args.site)
    if not site:
        logger.error(f"Site not found: {args.site}")
        return 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Robots.txt Compliance: {site.name}")
    logger.info('='*60)
    
    success, robots_info = robots_parser.fetch_and_parse(site.base_url)
    
    if not success:
        logger.error("Failed to fetch/parse robots.txt")
        return 1
    
    logger.info(f"\n✓ Robots.txt parsed successfully")
    logger.info(f"  Allowed paths: {len(robots_info['allowed_paths'])}")
    logger.info(f"  Disallowed paths: {len(robots_info['disallowed_paths'])}")
    
    if robots_info['crawl_delay']:
        logger.info(f"  Crawl-delay: {robots_info['crawl_delay']}s")
    
    # Update site with robots info
    site.robots_txt_info = RobotsTxtInfo.from_dict(robots_info)
    site_manager.update_site(site.name, robots_txt_info=site.robots_txt_info)
    
    return 0


def cmd_analyze(args, site_manager, logger):
    """Analyze site structure"""
    site = site_manager.get_site(args.site)
    if not site:
        logger.error(f"Site not found: {args.site}")
        return 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Site Structure Analysis: {site.name}")
    logger.info('='*60)
    logger.info(f"\nBase URL: {site.base_url}")
    logger.info("\n⚠ Structure analysis requires manual configuration")
    logger.info("   Use 'update' command to set categories and patterns")
    
    return 0


def cmd_history(args, site_manager, logger):
    """Show registry history"""
    history = site_manager.get_history()
    
    if not history:
        logger.info("No history available")
        return 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Registry History ({len(history)} entries)")
    logger.info('='*60)
    
    for entry in history[-20:]:  # Show last 20 entries
        logger.info(f"\n{entry['timestamp']}")
        logger.info(f"  Action: {entry['action']}")
        logger.info(f"  Site: {entry['site']}")
        if entry.get('details'):
            logger.info(f"  Details: {entry['details']}")
    
    return 0


def cmd_discover(args, site_manager, logger):
    """Discover products on competitor sites"""
    import json
    from pathlib import Path
    
    # Load target brands
    if args.brands:
        brands_file = Path(args.brands)
        if not brands_file.exists():
            logger.error(f"Brands file not found: {brands_file}")
            return 1
        
        # Check if it's the brands registry JSON
        if brands_file.suffix == '.json':
            with open(brands_file, 'r') as f:
                brands_data = json.load(f)
                target_brands = [brand['name'] for brand in brands_data.get('brands', [])]
        else:
            # Plain text file, one brand per line
            target_brands = []
            with open(brands_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        target_brands.append(line)
    else:
        # Try to load from default brands registry
        default_registry = Path('brands_registry.json')
        if default_registry.exists():
            with open(default_registry, 'r') as f:
                brands_data = json.load(f)
                target_brands = [brand['name'] for brand in brands_data.get('brands', [])]
        else:
            logger.error("No brands specified. Use --brands to specify target brands")
            return 1
    
    if not target_brands:
        logger.error("No target brands loaded")
        return 1
    
    logger.info(f"Target brands ({len(target_brands)}): {', '.join(target_brands)}")
    
    # Get sites to process
    if args.site:
        site = site_manager.get_site(args.site)
        if not site:
            logger.error(f"Site not found: {args.site}")
            return 1
        sites = [site]
    else:
        sites = site_manager.get_sites_by_status('active')
        if not sites:
            logger.info("No active sites found. Using all sites...")
            sites = site_manager.get_all_sites()
    
    if not sites:
        logger.error("No sites to process")
        return 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Product Discovery ({len(sites)} site(s))")
    logger.info('='*60)
    
    # Initialize product discovery
    discovery = ProductDiscovery()
    
    # Process each site
    all_inventories = []
    for site in sites:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {site.name}")
        logger.info('='*60)
        
        try:
            inventory = discovery.discover_products_for_site(
                competitor_site=site.name,
                base_url=site.base_url,
                target_brands=target_brands,
                max_pages_per_category=args.max_pages,
                delay=site.scraping_params.request_delay,
                timeout=site.scraping_params.timeout_seconds
            )
            
            all_inventories.append(inventory)
            
            # Display summary
            logger.info(f"\n{'='*60}")
            logger.info(f"Discovery Summary: {site.name}")
            logger.info('='*60)
            logger.info(f"Total products found: {inventory.total_products}")
            logger.info(f"\nBy Brand:")
            for brand, products in inventory.brand_products.items():
                logger.info(f"  {brand}: {len(products)} products")
            logger.info(f"\nBy Category:")
            for category, count in inventory.category_summary.items():
                logger.info(f"  {category}: {count} products")
            
            # Save if requested
            if args.save:
                output_dir = Path('data/product_inventory')
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = output_dir / f"{site.name.lower().replace(' ', '_')}_inventory.json"
                with open(output_file, 'w') as f:
                    json.dump(inventory.to_dict(), f, indent=2)
                
                logger.info(f"\n✓ Inventory saved: {output_file}")
        
        except Exception as e:
            logger.error(f"Error processing {site.name}: {e}", exc_info=True)
            continue
    
    # Overall summary
    if all_inventories:
        total_products = sum(inv.total_products for inv in all_inventories)
        logger.info(f"\n{'='*60}")
        logger.info(f"Overall Discovery Summary")
        logger.info('='*60)
        logger.info(f"Sites processed: {len(all_inventories)}")
        logger.info(f"Total products discovered: {total_products}")
    
    return 0


def cmd_products(args, logger):
    """View discovered products"""
    import json
    from pathlib import Path
    
    inventory_dir = Path('data/product_inventory')
    if not inventory_dir.exists():
        logger.info("No product inventory found. Run 'discover' command first.")
        return 0
    
    # Load all inventories
    inventories = []
    for inventory_file in inventory_dir.glob('*_inventory.json'):
        with open(inventory_file, 'r') as f:
            inventories.append(json.load(f))
    
    if not inventories:
        logger.info("No product inventory found")
        return 0
    
    # Filter by site if specified
    if args.site:
        inventories = [inv for inv in inventories if inv['competitor_site'] == args.site]
    
    # Display products
    logger.info(f"\n{'='*60}")
    logger.info(f"Discovered Products")
    logger.info('='*60)
    
    for inventory in inventories:
        site_name = inventory['competitor_site']
        
        if args.brand:
            # Filter by brand
            if args.brand not in inventory['brand_products']:
                continue
            products = inventory['brand_products'][args.brand]
            logger.info(f"\n{site_name} - {args.brand} ({len(products)} products)")
        else:
            # Show all brands
            logger.info(f"\n{site_name} ({inventory['total_products']} products)")
            for brand, products in inventory['brand_products'].items():
                if args.category:
                    # Filter by category
                    products = [p for p in products if p['category'] == args.category]
                    if not products:
                        continue
                
                logger.info(f"\n  {brand} ({len(products)} products):")
                for product in products[:10]:  # Show first 10
                    status = "✓" if product.get('in_stock', True) else "✗"
                    logger.info(f"    {status} {product['title']}")
                    logger.info(f"      {product['url']}")
                    if product.get('price'):
                        logger.info(f"      Price: {product['price']}")
                
                if len(products) > 10:
                    logger.info(f"    ... and {len(products) - 10} more")
    
    return 0


def cmd_extract_images(args, site_manager, logger):
    """Extract images from discovered products"""
    import json
    from pathlib import Path
    
    logger.info("="*60)
    logger.info("Extracting Product Images")
    logger.info("="*60)
    
    # Initialize extractors
    image_extractor = ImageExtractor()
    image_downloader = CompetitorImageDownloader()
    
    # Load product inventory
    inventory_dir = Path("data/product_inventory")
    
    if not inventory_dir.exists():
        logger.error("No product inventory found. Run 'discover' first.")
        return 1
    
    # Collect products to process
    products_to_process = []
    
    for inventory_file in inventory_dir.glob("*.json"):
        try:
            with open(inventory_file, 'r') as f:
                inventory = json.load(f)
            
            competitor_site = inventory.get('competitor_site', 'unknown')
            
            # Filter by site if specified
            if args.site and args.site.lower() not in competitor_site.lower():
                continue
            
            for brand, brand_data in inventory.get('brands', {}).items():
                # Filter by brand if specified
                if args.brand and args.brand.lower() != brand.lower():
                    continue
                
                for category, products in brand_data.get('categories', {}).items():
                    for product in products:
                        products_to_process.append({
                            'brand': brand,
                            'name': product['title'],
                            'url': product['url'],
                            'competitor_site': competitor_site
                        })
                        
                        # Limit products
                        if len(products_to_process) >= args.max_products:
                            break
                    
                    if len(products_to_process) >= args.max_products:
                        break
                
                if len(products_to_process) >= args.max_products:
                    break
        
        except Exception as e:
            logger.warning(f"Error loading inventory {inventory_file}: {e}")
            continue
    
    if not products_to_process:
        logger.info("No products found matching filters")
        return 0
    
    logger.info(f"Processing {len(products_to_process)} products")
    
    # Extract and download images
    total_extracted = 0
    total_downloaded = 0
    
    for i, product in enumerate(products_to_process):
        logger.info(f"\n{'='*60}")
        logger.info(f"Product {i+1}/{len(products_to_process)}: {product['name']}")
        logger.info(f"{'='*60}")
        
        try:
            # Extract images
            images = image_extractor.extract_images(product['url'])
            
            if not images:
                logger.warning(f"No images found for {product['name']}")
                continue
            
            total_extracted += len(images)
            logger.info(f"Extracted {len(images)} images")
            
            # Filter by quality
            quality_images = image_extractor.filter_quality_images(
                images,
                min_quality=args.min_quality,
                analyze=True
            )
            
            if not quality_images:
                logger.warning(f"No quality images found (min quality: {args.min_quality})")
                continue
            
            logger.info(f"Quality images: {len(quality_images)}")
            
            # Get best images
            best_images = image_extractor.get_best_images(
                quality_images,
                max_images=args.images_per_product
            )
            
            logger.info(f"Selected {len(best_images)} best images")
            
            # Show image info
            for j, img in enumerate(best_images[:3]):  # Show first 3
                logger.info(f"  Image {j+1}: {img.image_type} (quality: {img.quality_score})")
                if img.width and img.height:
                    logger.info(f"    Size: {img.width}x{img.height}px")
            
            # Download if requested
            if args.save:
                metadata = image_downloader.download_product_images(
                    brand=product['brand'],
                    product_name=product['name'],
                    images=best_images,
                    competitor_site=product['competitor_site'],
                    max_images=args.images_per_product
                )
                
                total_downloaded += metadata['downloaded']
                logger.info(f"✓ Downloaded {metadata['downloaded']} images")
            
            # Small delay between products
            import time
            time.sleep(1.0)
            
        except Exception as e:
            logger.error(f"Error processing product {product['name']}: {e}")
            continue
    
    logger.info(f"\n{'='*60}")
    logger.info("Extraction Summary")
    logger.info('='*60)
    logger.info(f"Total images extracted: {total_extracted}")
    if args.save:
        logger.info(f"Total images downloaded: {total_downloaded}")
    
    return 0


def cmd_images(args, logger):
    """View downloaded images summary"""
    downloader = CompetitorImageDownloader()
    summary = downloader.get_download_summary(brand=args.brand)
    
    if summary['total_images'] == 0:
        logger.info("No downloaded images found")
        return 0
    
    logger.info("\n"+"="*60)
    logger.info("Downloaded Images Summary")
    logger.info("="*60)
    logger.info(f"Total Brands: {summary['total_brands']}")
    logger.info(f"Total Images: {summary['total_images']}")
    logger.info(f"Total Size: {summary['total_size_mb']} MB")
    
    for brand_name, brand_stats in summary['brands'].items():
        logger.info(f"\n{brand_name.upper()}")
        logger.info(f"  Total Images: {brand_stats['total_images']}")
        logger.info(f"  Total Size: {brand_stats['total_size_mb']} MB")
        
        for site_name, site_stats in brand_stats['competitor_sites'].items():
            logger.info(f"    {site_name}: {site_stats['image_count']} images ({site_stats['size_mb']} MB)")
    
    return 0


def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Load configuration
    try:
        config = Config(args.config)
        
        if args.verbose:
            config.log_level = 'DEBUG'
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return 1
    
    # Setup logger
    logger = setup_logger('CompetitorManager', config.logs_dir, config.log_level)
    
    logger.info("="*60)
    logger.info("Competitor Site Manager Started")
    logger.info("="*60)
    
    # Initialize managers
    registry_file = Path(args.registry)
    site_manager = CompetitorSiteManager(registry_file, logger)
    
    robots_parser = RobotsTxtParser(logger)
    health_monitor = SiteHealthMonitor(logger)
    
    # Execute command
    try:
        if args.command == 'load':
            return cmd_load(args, site_manager, logger)
        elif args.command == 'list':
            return cmd_list(args, site_manager, logger)
        elif args.command == 'add':
            return cmd_add(args, site_manager, logger)
        elif args.command == 'update':
            return cmd_update(args, site_manager, logger)
        elif args.command == 'remove':
            return cmd_remove(args, site_manager, logger)
        elif args.command == 'health':
            return cmd_health(args, site_manager, health_monitor, logger)
        elif args.command == 'robots':
            return cmd_robots(args, site_manager, robots_parser, logger)
        elif args.command == 'analyze':
            return cmd_analyze(args, site_manager, logger)
        elif args.command == 'history':
            return cmd_history(args, site_manager, logger)
        elif args.command == 'discover':
            return cmd_discover(args, site_manager, logger)
        elif args.command == 'products':
            return cmd_products(args, logger)
        elif args.command == 'extract-images':
            return cmd_extract_images(args, site_manager, logger)
        elif args.command == 'images':
            return cmd_images(args, logger)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
