#!/usr/bin/env python3
"""
Brand Management CLI
Command-line interface for brand discovery and configuration
"""
import sys
import argparse
from pathlib import Path

from modules import (
    Config, setup_logger, 
    BrandManager, BrandValidator, 
    Brand, BrandStatus,
    MediaPackDiscovery
)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Brand Management - Configure and validate brand information',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load and validate brands from file
  python brand_manager.py load brands.txt
  
  # Validate all brands in registry
  python brand_manager.py validate
  
  # Show processing queue ordered by priority
  python brand_manager.py queue
  
  # List all brands
  python brand_manager.py list
  
  # Add a new brand
  python brand_manager.py add "SMOK" "smoktech.com" --priority high
  
  # Remove a brand
  python brand_manager.py remove "SMOK"
  
  # Show registry history
  python brand_manager.py history
  
  # Discover media packs for all brands
  python brand_manager.py discover-media --save
  
  # Discover media packs for specific brand
  python brand_manager.py discover-media --brand "SMOK" --save
  
  # Show discovered media packs
  python brand_manager.py media-packs
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--registry', '-r',
        type=str,
        default='brands_registry.json',
        help='Path to brand registry file (default: brands_registry.json)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Load command
    load_parser = subparsers.add_parser('load', help='Load brands from file')
    load_parser.add_argument('file', type=str, help='Path to brands.txt file')
    load_parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate brands after loading'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate all brands')
    validate_parser.add_argument(
        '--brand', '-b',
        type=str,
        help='Validate specific brand only'
    )
    
    # Queue command
    subparsers.add_parser('queue', help='Show processing queue')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List brands')
    list_parser.add_argument(
        '--priority', '-p',
        choices=['high', 'medium', 'low'],
        help='Filter by priority'
    )
    list_parser.add_argument(
        '--status', '-s',
        choices=['pending', 'validated', 'failed', 'inactive'],
        help='Filter by status'
    )
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add new brand')
    add_parser.add_argument('name', type=str, help='Brand name')
    add_parser.add_argument('website', type=str, help='Brand website')
    add_parser.add_argument(
        '--priority', '-p',
        choices=['high', 'medium', 'low'],
        default='medium',
        help='Brand priority (default: medium)'
    )
    add_parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate brand after adding'
    )
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update existing brand')
    update_parser.add_argument('name', type=str, help='Brand name')
    update_parser.add_argument(
        '--website', '-w',
        type=str,
        help='New website'
    )
    update_parser.add_argument(
        '--priority', '-p',
        choices=['high', 'medium', 'low'],
        help='New priority'
    )
    update_parser.add_argument(
        '--status', '-s',
        choices=['pending', 'validated', 'failed', 'inactive'],
        help='New status'
    )
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove brand')
    remove_parser.add_argument('name', type=str, help='Brand name')
    
    # History command
    subparsers.add_parser('history', help='Show registry history')
    
    # Discover media packs command
    discover_parser = subparsers.add_parser('discover-media', help='Discover media packs for brands')
    discover_parser.add_argument(
        '--brand', '-b',
        type=str,
        help='Discover for specific brand only'
    )
    discover_parser.add_argument(
        '--save',
        action='store_true',
        help='Save discovered media packs to registry'
    )
    
    # Show media packs command
    media_parser = subparsers.add_parser('media-packs', help='Show discovered media packs')
    media_parser.add_argument(
        '--brand', '-b',
        type=str,
        help='Show media packs for specific brand'
    )
    media_parser.add_argument(
        '--type', '-t',
        choices=['archive', 'document', 'image', 'vector'],
        help='Filter by file type category'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    return args


def cmd_load(args, brand_manager, validator, logger):
    """Load brands from file"""
    file_path = Path(args.file)
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return 1
    
    # Load brands
    brands, errors = brand_manager.load_brands_from_file(file_path)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Loaded {len(brands)} brands")
    
    if errors:
        logger.warning(f"\nErrors encountered: {len(errors)}")
        for error in errors:
            logger.warning(f"  - {error}")
        print(brand_manager.generate_error_summary(errors))
    
    # Add to registry
    for brand in brands:
        brand_manager.add_brand(brand)
    
    # Validate if requested
    if args.validate:
        logger.info(f"\n{'='*60}")
        logger.info("Validating brands...")
        cmd_validate_brands(brands, validator, brand_manager, logger)
    
    # Save registry
    brand_manager.save_registry()
    logger.info(f"Registry saved: {brand_manager.registry_file}")
    
    return 0


def cmd_validate(args, brand_manager, validator, logger):
    """Validate brands"""
    if args.brand:
        # Validate specific brand
        brand = brand_manager.get_brand(args.brand)
        if not brand:
            logger.error(f"Brand not found: {args.brand}")
            return 1
        brands = [brand]
    else:
        # Validate all brands
        brands = brand_manager.get_all_brands()
    
    if not brands:
        logger.warning("No brands to validate")
        return 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Validating {len(brands)} brand(s)...")
    
    cmd_validate_brands(brands, validator, brand_manager, logger)
    
    # Save registry
    brand_manager.save_registry()
    logger.info(f"Registry saved: {brand_manager.registry_file}")
    
    return 0


def cmd_validate_brands(brands, validator, brand_manager, logger):
    """Validate a list of brands"""
    for brand in brands:
        logger.info(f"\nValidating: {brand.name}")
        
        # Validate website
        results = validator.validate_brand(brand.name, brand.website)
        
        # Update brand with results
        brand.response_time = results['response_time']
        brand.ssl_valid = results['ssl_valid']
        
        if results['accessible'] and results['response_time']:
            brand.status = BrandStatus.VALIDATED.value
            logger.info(f"  ✓ Validated - Response: {results['response_time']:.2f}s, SSL: {results['ssl_valid']}")
        else:
            brand.status = BrandStatus.FAILED.value
            brand.error_message = results['error_message']
            logger.warning(f"  ✗ Failed - {results['error_message']}")
        
        # Update in registry
        brand_manager.update_brand(brand)


def cmd_queue(args, brand_manager, logger):
    """Show processing queue"""
    queue = brand_manager.get_processing_queue()
    
    if not queue:
        logger.info("Queue is empty")
        return 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing Queue ({len(queue)} brands)")
    logger.info('='*60)
    
    current_priority = None
    for i, brand in enumerate(queue, 1):
        if brand.priority != current_priority:
            current_priority = brand.priority
            logger.info(f"\n{current_priority.upper()} Priority:")
        
        status_icon = "✓" if brand.status == "validated" else "○"
        logger.info(f"  {i}. {status_icon} {brand.name} - {brand.website}")
    
    return 0


def cmd_list(args, brand_manager, logger):
    """List brands"""
    brands = brand_manager.get_all_brands()
    
    # Filter by priority
    if args.priority:
        brands = [b for b in brands if b.priority == args.priority]
    
    # Filter by status
    if args.status:
        brands = [b for b in brands if b.status == args.status]
    
    if not brands:
        logger.info("No brands found")
        return 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Brands ({len(brands)})")
    logger.info('='*60)
    
    for brand in sorted(brands, key=lambda b: (b.priority, b.name)):
        status_icon = {
            'validated': '✓',
            'failed': '✗',
            'pending': '○',
            'inactive': '-'
        }.get(brand.status, '?')
        
        logger.info(f"\n{brand.name}")
        logger.info(f"  Status: {status_icon} {brand.status}")
        logger.info(f"  Website: {brand.website}")
        logger.info(f"  Priority: {brand.priority}")
        
        if brand.response_time:
            logger.info(f"  Response Time: {brand.response_time:.2f}s")
        if brand.ssl_valid is not None:
            logger.info(f"  SSL Valid: {brand.ssl_valid}")
        if brand.error_message:
            logger.info(f"  Error: {brand.error_message}")
    
    return 0


def cmd_add(args, brand_manager, validator, logger):
    """Add new brand"""
    # Create brand
    brand = Brand(
        name=args.name,
        website=args.website,
        priority=args.priority
    )
    
    # Validate if requested
    if args.validate:
        logger.info(f"Validating: {brand.name}")
        results = validator.validate_brand(brand.name, brand.website)
        
        brand.response_time = results['response_time']
        brand.ssl_valid = results['ssl_valid']
        
        if results['accessible'] and results['response_time']:
            brand.status = BrandStatus.VALIDATED.value
            logger.info(f"  ✓ Validated")
        else:
            brand.status = BrandStatus.FAILED.value
            brand.error_message = results['error_message']
            logger.warning(f"  ✗ Failed - {results['error_message']}")
    
    # Add to registry
    brand_manager.add_brand(brand)
    brand_manager.save_registry()
    
    logger.info(f"Brand added: {brand.name}")
    return 0


def cmd_update(args, brand_manager, logger):
    """Update existing brand"""
    brand = brand_manager.get_brand(args.name)
    
    if not brand:
        logger.error(f"Brand not found: {args.name}")
        return 1
    
    # Update fields
    if args.website:
        brand.website = args.website
    if args.priority:
        brand.priority = args.priority
    if args.status:
        brand.status = args.status
    
    # Update in registry
    brand_manager.update_brand(brand)
    brand_manager.save_registry()
    
    logger.info(f"Brand updated: {brand.name}")
    return 0


def cmd_remove(args, brand_manager, logger):
    """Remove brand"""
    if not brand_manager.get_brand(args.name):
        logger.error(f"Brand not found: {args.name}")
        return 1
    
    brand_manager.remove_brand(args.name)
    brand_manager.save_registry()
    
    logger.info(f"Brand removed: {args.name}")
    return 0


def cmd_history(args, brand_manager, logger):
    """Show registry history"""
    history = brand_manager.get_history()
    
    if not history:
        logger.info("No history available")
        return 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Registry History ({len(history)} entries)")
    logger.info('='*60)
    
    for entry in history[-20:]:  # Show last 20 entries
        logger.info(f"\n{entry['timestamp']}")
        logger.info(f"  Action: {entry['action']}")
        logger.info(f"  Brand: {entry['brand']}")
    
    return 0


def cmd_discover_media(args, brand_manager, media_discovery, logger):
    """Discover media packs for brands"""
    from modules import MediaPackInfo
    from datetime import datetime
    
    if args.brand:
        # Discover for specific brand
        brand = brand_manager.get_brand(args.brand)
        if not brand:
            logger.error(f"Brand not found: {args.brand}")
            return 1
        brands = [brand]
    else:
        # Discover for all brands
        brands = brand_manager.get_all_brands()
    
    if not brands:
        logger.warning("No brands to process")
        return 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Discovering Media Packs ({len(brands)} brand(s))")
    logger.info('='*60)
    
    for brand in brands:
        logger.info(f"\n{brand.name} ({brand.website})")
        
        # Discover media packs
        media_packs = media_discovery.discover_media_packs(brand.name, brand.website)
        
        if media_packs:
            # Prioritize archives first
            prioritized = media_discovery.get_prioritized_packs(media_packs)
            
            logger.info(f"  Found {len(media_packs)} media pack(s):")
            for i, pack in enumerate(prioritized, 1):
                size_str = media_discovery.format_file_size(pack.file_size)
                status = "✓" if pack.accessible else "✗"
                restriction = f" [{pack.restriction_type}]" if pack.restricted else ""
                
                logger.info(f"    {i}. {status} {pack.content_type} ({pack.file_type})")
                logger.info(f"       {pack.url}")
                logger.info(f"       Size: {size_str}{restriction}")
            
            # Save to brand if requested
            if args.save:
                brand.media_packs = [pack.to_dict() for pack in media_packs]
                brand.media_pack_count = len(media_packs)
                brand.last_media_scan = datetime.now().isoformat()
                brand_manager.update_brand(brand)
                logger.info(f"  ✓ Saved {len(media_packs)} media pack(s) to registry")
        else:
            logger.info("  No media packs found")
    
    if args.save:
        brand_manager.save_registry()
        logger.info(f"\nRegistry saved: {brand_manager.registry_file}")
    
    return 0


def cmd_media_packs(args, brand_manager, media_discovery, logger):
    """Show discovered media packs"""
    from modules import MediaPackInfo
    
    if args.brand:
        # Show for specific brand
        brand = brand_manager.get_brand(args.brand)
        if not brand:
            logger.error(f"Brand not found: {args.brand}")
            return 1
        brands = [brand]
    else:
        # Show for all brands
        brands = brand_manager.get_all_brands()
    
    # Filter brands that have media packs
    brands_with_media = [b for b in brands if b.media_packs and len(b.media_packs) > 0]
    
    if not brands_with_media:
        logger.info("No media packs discovered yet. Use 'discover-media' command first.")
        return 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Discovered Media Packs ({len(brands_with_media)} brand(s))")
    logger.info('='*60)
    
    for brand in brands_with_media:
        logger.info(f"\n{brand.name}")
        logger.info(f"  Website: {brand.website}")
        logger.info(f"  Last scan: {brand.last_media_scan}")
        logger.info(f"  Media packs: {brand.media_pack_count}")
        
        if brand.media_packs:
            # Reconstruct MediaPackInfo objects
            packs = [MediaPackInfo.from_dict(p) for p in brand.media_packs]
            
            # Filter by type if requested
            if args.type:
                packs = [p for p in packs if media_discovery.FILE_TYPES.get(p.file_type, {}).get('category') == args.type]
            
            # Prioritize
            prioritized = media_discovery.get_prioritized_packs(packs)
            
            for i, pack in enumerate(prioritized, 1):
                size_str = media_discovery.format_file_size(pack.file_size)
                status = "✓" if pack.accessible else "✗"
                restriction = f" [{pack.restriction_type}]" if pack.restricted else ""
                
                logger.info(f"\n  {i}. {status} {pack.content_type} ({pack.file_type})")
                logger.info(f"     {pack.url}")
                logger.info(f"     Size: {size_str}{restriction}")
    
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
    logger = setup_logger('BrandManager', config.logs_dir, config.log_level)
    
    logger.info("="*60)
    logger.info("Brand Manager Started")
    logger.info("="*60)
    
    # Initialize brand manager
    registry_file = Path(args.registry)
    brand_manager = BrandManager(registry_file, logger)
    
    # Initialize validator
    validator = BrandValidator(config.request_timeout, logger)
    
    # Initialize media pack discovery
    media_discovery = MediaPackDiscovery(config, logger)
    
    # Execute command
    try:
        if args.command == 'load':
            return cmd_load(args, brand_manager, validator, logger)
        elif args.command == 'validate':
            return cmd_validate(args, brand_manager, validator, logger)
        elif args.command == 'queue':
            return cmd_queue(args, brand_manager, logger)
        elif args.command == 'list':
            return cmd_list(args, brand_manager, logger)
        elif args.command == 'add':
            return cmd_add(args, brand_manager, validator, logger)
        elif args.command == 'update':
            return cmd_update(args, brand_manager, logger)
        elif args.command == 'remove':
            return cmd_remove(args, brand_manager, logger)
        elif args.command == 'history':
            return cmd_history(args, brand_manager, logger)
        elif args.command == 'discover-media':
            return cmd_discover_media(args, brand_manager, media_discovery, logger)
        elif args.command == 'media-packs':
            return cmd_media_packs(args, brand_manager, media_discovery, logger)
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
