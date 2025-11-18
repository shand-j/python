"""
Product Scraper Modules
"""
from .config import Config
from .logger import setup_logger
from .scraper import WebScraper
from .image_processor import ImageProcessor
from .gpt_processor import GPTProcessor
from .shopify_exporter import ShopifyExporter
from .product_scraper import ProductScraper
from .brand_manager import Brand, BrandManager, Priority, BrandStatus
from .brand_validator import BrandValidator
from .media_pack_discovery import MediaPackDiscovery, MediaPackInfo
from .media_pack_downloader import MediaPackDownloader, DownloadProgress
from .media_pack_extractor import MediaPackExtractor
from .competitor_site_manager import (
    CompetitorSite, CompetitorSiteManager, 
    ScrapingParameters, SiteStructure, RobotsTxtInfo, SiteHealth,
    Priority as SitePriority, SiteStatus
)
from .robots_txt_parser import RobotsTxtParser
from .site_health_monitor import SiteHealthMonitor
from .user_agent_rotator import UserAgentRotator
from .product_discovery import ProductDiscovery, DiscoveredProduct, ProductInventory
from .image_extractor import ImageExtractor, ExtractedImage
from .competitor_image_downloader import CompetitorImageDownloader

__all__ = [
    'Config',
    'setup_logger',
    'WebScraper',
    'ImageProcessor',
    'GPTProcessor',
    'ShopifyExporter',
    'ProductScraper',
    'Brand',
    'BrandManager',
    'BrandValidator',
    'Priority',
    'BrandStatus',
    'MediaPackDiscovery',
    'MediaPackInfo',
    'MediaPackDownloader',
    'DownloadProgress',
    'MediaPackExtractor',
    'CompetitorSite',
    'CompetitorSiteManager',
    'ScrapingParameters',
    'SiteStructure',
    'RobotsTxtInfo',
    'SiteHealth',
    'SitePriority',
    'SiteStatus',
    'RobotsTxtParser',
    'SiteHealthMonitor',
    'UserAgentRotator',
    'ProductDiscovery',
    'DiscoveredProduct',
    'ProductInventory',
    'ImageExtractor',
    'ExtractedImage',
    'CompetitorImageDownloader'
]
