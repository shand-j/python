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
    RobotsTxtParser, SiteHealthMonitor, UserAgentRotator
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
