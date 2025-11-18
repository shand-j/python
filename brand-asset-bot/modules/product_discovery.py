"""
Product Discovery Module

Discovers and catalogs products on competitor websites with brand-specific filtering
and systematic category navigation.
"""

import re
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredProduct:
    """Represents a discovered product from a competitor website"""
    url: str
    title: str
    brand: Optional[str]
    category: str
    competitor_site: str
    price: Optional[str] = None
    image_url: Optional[str] = None
    in_stock: bool = True
    variant_count: int = 1
    discovered_at: str = None
    
    def __post_init__(self):
        if self.discovered_at is None:
            from datetime import datetime
            self.discovered_at = datetime.utcnow().isoformat()


@dataclass
class ProductInventory:
    """Catalog of discovered products organized by brand and category"""
    competitor_site: str
    total_products: int
    brand_products: Dict[str, List[Dict]]  # brand_name -> list of products
    category_summary: Dict[str, int]  # category -> count
    last_scan: str
    
    def to_dict(self):
        return asdict(self)


class ProductDiscovery:
    """Discovers and catalogs products on competitor websites"""
    
    # Common category patterns for vape retailers
    CATEGORY_PATTERNS = [
        '/vape-kits', '/vape-kits/', '/kits',
        '/disposable-vapes', '/disposables', '/disposable',
        '/vape-mods', '/mods',
        '/e-liquids', '/e-liquid', '/liquids',
        '/tanks', '/vape-tanks',
        '/coils', '/replacement-coils',
        '/batteries', '/vape-batteries',
        '/accessories', '/vape-accessories'
    ]
    
    # Product URL patterns
    PRODUCT_URL_PATTERNS = [
        r'/products?/[a-z0-9\-]+',
        r'/[a-z\-]+/[a-z0-9\-]+\.html',
        r'/p/[a-z0-9\-]+',
        r'/product/[a-z0-9\-]+'
    ]
    
    def __init__(self, user_agent: str = None):
        """Initialize product discovery"""
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        self.discovered_products = []
        self.seen_urls = set()
    
    def discover_categories(self, base_url: str, timeout: int = 30) -> List[str]:
        """
        Discover category pages on a competitor website
        
        Args:
            base_url: Base URL of the competitor site
            timeout: Request timeout in seconds
            
        Returns:
            List of discovered category URLs
        """
        logger.info(f"Discovering categories on {base_url}")
        categories = []
        
        try:
            response = self.session.get(base_url, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)
                
                # Check if it matches category patterns
                for pattern in self.CATEGORY_PATTERNS:
                    if pattern.lower() in href.lower():
                        if full_url not in categories:
                            categories.append(full_url)
                            logger.debug(f"Found category: {full_url}")
            
            logger.info(f"Discovered {len(categories)} category pages")
            return categories
            
        except requests.RequestException as e:
            logger.error(f"Error discovering categories: {e}")
            return []
    
    def extract_product_urls(self, category_url: str, max_pages: int = 10, 
                            delay: float = 2.0, timeout: int = 30) -> List[str]:
        """
        Extract product URLs from a category page with pagination support
        
        Args:
            category_url: URL of the category page
            max_pages: Maximum pages to process
            delay: Delay between page requests
            timeout: Request timeout in seconds
            
        Returns:
            List of discovered product URLs
        """
        logger.info(f"Extracting products from {category_url}")
        product_urls = []
        current_page = 1
        
        while current_page <= max_pages:
            try:
                # Build page URL (handle common pagination patterns)
                if current_page == 1:
                    page_url = category_url
                else:
                    # Try common pagination patterns
                    if '?' in category_url:
                        page_url = f"{category_url}&page={current_page}"
                    else:
                        page_url = f"{category_url}?page={current_page}"
                
                logger.debug(f"Processing page {current_page}: {page_url}")
                response = self.session.get(page_url, timeout=timeout)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                page_products = []
                
                # Find product links using multiple methods
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(category_url, href)
                    
                    # Check if it matches product URL patterns
                    for pattern in self.PRODUCT_URL_PATTERNS:
                        if re.search(pattern, href, re.IGNORECASE):
                            if full_url not in product_urls and full_url not in self.seen_urls:
                                product_urls.append(full_url)
                                page_products.append(full_url)
                                self.seen_urls.add(full_url)
                                logger.debug(f"Found product: {full_url}")
                
                # If no products found on this page, assume end of pagination
                if not page_products:
                    logger.debug(f"No products found on page {current_page}, ending pagination")
                    break
                
                logger.info(f"Page {current_page}: Found {len(page_products)} products")
                current_page += 1
                
                # Respectful delay between pages
                if current_page <= max_pages:
                    time.sleep(delay)
                
            except requests.RequestException as e:
                logger.error(f"Error extracting products from page {current_page}: {e}")
                break
        
        logger.info(f"Total products extracted from category: {len(product_urls)}")
        return product_urls
    
    def filter_by_brands(self, product_urls: List[str], target_brands: List[str],
                        competitor_site: str, category: str, 
                        delay: float = 2.0, timeout: int = 30) -> List[DiscoveredProduct]:
        """
        Filter product URLs by target brands
        
        Args:
            product_urls: List of product URLs to check
            target_brands: List of brand names to filter for
            competitor_site: Name of competitor site
            category: Product category
            delay: Delay between requests
            timeout: Request timeout
            
        Returns:
            List of discovered products matching target brands
        """
        logger.info(f"Filtering {len(product_urls)} products for brands: {target_brands}")
        filtered_products = []
        
        # Normalize brand names for matching
        normalized_brands = [brand.lower() for brand in target_brands]
        
        for i, url in enumerate(product_urls):
            try:
                # Check URL for brand name first (fast check)
                url_lower = url.lower()
                matched_brand = None
                
                for j, brand in enumerate(target_brands):
                    brand_slug = brand.lower().replace(' ', '-')
                    if brand_slug in url_lower or normalized_brands[j] in url_lower:
                        matched_brand = brand
                        break
                
                # If not found in URL, fetch page and check content
                if not matched_brand:
                    response = self.session.get(url, timeout=timeout)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Check title
                    title_tag = soup.find('title')
                    title = title_tag.text if title_tag else ''
                    
                    # Check h1
                    h1_tag = soup.find('h1')
                    h1_text = h1_tag.text if h1_tag else ''
                    
                    # Check meta description
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    description = meta_desc.get('content', '') if meta_desc else ''
                    
                    # Check breadcrumbs
                    breadcrumbs = soup.find_all(['nav', 'ol', 'ul'], class_=re.compile(r'breadcrumb', re.I))
                    breadcrumb_text = ' '.join([bc.text for bc in breadcrumbs])
                    
                    # Combine all text for matching
                    combined_text = f"{title} {h1_text} {description} {breadcrumb_text}".lower()
                    
                    # Check for brand match
                    for brand in target_brands:
                        if brand.lower() in combined_text:
                            matched_brand = brand
                            title = title or h1_text
                            break
                    
                    # If still no match, skip
                    if not matched_brand:
                        continue
                    
                    # Extract additional info
                    price_elem = soup.find(['span', 'div'], class_=re.compile(r'price', re.I))
                    price = price_elem.text.strip() if price_elem else None
                    
                    image_elem = soup.find('img', class_=re.compile(r'product', re.I))
                    image_url = image_elem.get('src') if image_elem else None
                    if image_url:
                        image_url = urljoin(url, image_url)
                    
                    # Check stock status
                    in_stock = True
                    stock_elem = soup.find(['span', 'div'], class_=re.compile(r'stock|availability', re.I))
                    if stock_elem and any(term in stock_elem.text.lower() for term in ['out of stock', 'sold out', 'unavailable']):
                        in_stock = False
                    
                    time.sleep(delay)
                else:
                    # If matched in URL, we still need title
                    response = self.session.get(url, timeout=timeout)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    title_tag = soup.find('title')
                    title = title_tag.text if title_tag else url.split('/')[-1]
                    
                    price_elem = soup.find(['span', 'div'], class_=re.compile(r'price', re.I))
                    price = price_elem.text.strip() if price_elem else None
                    
                    image_elem = soup.find('img', class_=re.compile(r'product', re.I))
                    image_url = image_elem.get('src') if image_elem else None
                    if image_url:
                        image_url = urljoin(url, image_url)
                    
                    in_stock = True
                    stock_elem = soup.find(['span', 'div'], class_=re.compile(r'stock|availability', re.I))
                    if stock_elem and any(term in stock_elem.text.lower() for term in ['out of stock', 'sold out', 'unavailable']):
                        in_stock = False
                    
                    time.sleep(delay)
                
                # Create discovered product
                product = DiscoveredProduct(
                    url=url,
                    title=title,
                    brand=matched_brand,
                    category=category,
                    competitor_site=competitor_site,
                    price=price,
                    image_url=image_url,
                    in_stock=in_stock
                )
                
                filtered_products.append(product)
                self.discovered_products.append(product)
                logger.info(f"Matched product: {matched_brand} - {title}")
                
                # Progress update
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(product_urls)} URLs, found {len(filtered_products)} matches")
                
            except requests.RequestException as e:
                logger.error(f"Error checking product {url}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing {url}: {e}")
                continue
        
        logger.info(f"Filtering complete: {len(filtered_products)} products matched target brands")
        return filtered_products
    
    def build_inventory(self, competitor_site: str) -> ProductInventory:
        """
        Build product inventory from discovered products
        
        Args:
            competitor_site: Name of competitor site
            
        Returns:
            ProductInventory object
        """
        from datetime import datetime
        
        # Organize by brand
        brand_products = {}
        category_summary = {}
        
        for product in self.discovered_products:
            if product.competitor_site != competitor_site:
                continue
            
            # Add to brand products
            brand = product.brand or 'Unknown'
            if brand not in brand_products:
                brand_products[brand] = []
            brand_products[brand].append(asdict(product))
            
            # Update category summary
            category = product.category
            category_summary[category] = category_summary.get(category, 0) + 1
        
        inventory = ProductInventory(
            competitor_site=competitor_site,
            total_products=len([p for p in self.discovered_products if p.competitor_site == competitor_site]),
            brand_products=brand_products,
            category_summary=category_summary,
            last_scan=datetime.utcnow().isoformat()
        )
        
        return inventory
    
    def discover_products_for_site(self, competitor_site: str, base_url: str,
                                   target_brands: List[str], max_pages_per_category: int = 10,
                                   delay: float = 2.0, timeout: int = 30) -> ProductInventory:
        """
        Complete product discovery workflow for a competitor site
        
        Args:
            competitor_site: Name of competitor site
            base_url: Base URL of the site
            target_brands: List of brand names to filter for
            max_pages_per_category: Max pages to process per category
            delay: Delay between requests
            timeout: Request timeout
            
        Returns:
            ProductInventory object
        """
        logger.info(f"Starting product discovery for {competitor_site}")
        
        # Reset for this site
        self.discovered_products = [p for p in self.discovered_products if p.competitor_site != competitor_site]
        
        # Step 1: Discover categories
        categories = self.discover_categories(base_url, timeout)
        logger.info(f"Found {len(categories)} categories")
        
        # Step 2: Process each category
        for category_url in categories:
            category_name = category_url.split('/')[-1] or category_url.split('/')[-2]
            logger.info(f"Processing category: {category_name}")
            
            # Extract product URLs
            product_urls = self.extract_product_urls(
                category_url, 
                max_pages=max_pages_per_category,
                delay=delay,
                timeout=timeout
            )
            
            # Filter by target brands
            if product_urls:
                self.filter_by_brands(
                    product_urls,
                    target_brands,
                    competitor_site,
                    category_name,
                    delay=delay,
                    timeout=timeout
                )
        
        # Step 3: Build inventory
        inventory = self.build_inventory(competitor_site)
        logger.info(f"Discovery complete: {inventory.total_products} products found")
        
        return inventory
