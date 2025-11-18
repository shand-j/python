"""
Web Scraper Module
Handles fetching and parsing product pages
"""
import time
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib.parse import urljoin, urlparse


class WebScraper:
    """Web scraper for product pages"""
    
    def __init__(self, config, logger):
        """
        Initialize web scraper
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.session = requests.Session()
        
        if config.user_agent_rotation:
            self.ua = UserAgent()
        else:
            self.ua = None
    
    def _get_headers(self):
        """
        Get request headers with user agent
        
        Returns:
            dict: Request headers
        """
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        if self.ua:
            headers['User-Agent'] = self.ua.random
        else:
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        return headers
    
    def _get_proxies(self):
        """
        Get proxy configuration
        
        Returns:
            dict: Proxy configuration or None
        """
        if self.config.use_proxy and self.config.proxy_url:
            return {
                'http': self.config.proxy_url,
                'https': self.config.proxy_url
            }
        return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_page(self, url):
        """
        Fetch a web page with retry logic
        
        Args:
            url: URL to fetch
        
        Returns:
            requests.Response: Response object
        
        Raises:
            requests.RequestException: If request fails after retries
        """
        self.logger.info(f"Fetching page: {url}")
        
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                proxies=self._get_proxies(),
                timeout=self.config.request_timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Add delay between requests
            time.sleep(self.config.request_delay)
            
            return response
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error fetching {url}: {e}")
            raise
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error fetching {url}: {e}")
            raise
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Timeout fetching {url}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error fetching {url}: {e}")
            raise
    
    def parse_html(self, html_content):
        """
        Parse HTML content using BeautifulSoup
        
        Args:
            html_content: HTML string to parse
        
        Returns:
            BeautifulSoup: Parsed HTML
        """
        return BeautifulSoup(html_content, 'lxml')
    
    def extract_metadata(self, soup, base_url):
        """
        Extract metadata from parsed HTML
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative URLs
        
        Returns:
            dict: Extracted metadata
        """
        metadata = {
            'title': '',
            'description': '',
            'keywords': '',
            'og_title': '',
            'og_description': '',
            'og_image': '',
            'product_name': '',
            'price': '',
            'specifications': {},
            'images': [],
            'breadcrumbs': [],
            'categories': []
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
        
        # Extract meta tags
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            metadata['description'] = meta_desc['content']
        
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            metadata['keywords'] = meta_keywords['content']
        
        # Extract Open Graph metadata
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            metadata['og_title'] = og_title['content']
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            metadata['og_description'] = og_desc['content']
        
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            metadata['og_image'] = urljoin(base_url, og_image['content'])
        
        # Extract product-specific metadata
        # Schema.org structured data
        structured_data = soup.find_all('script', type='application/ld+json')
        for script in structured_data:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    metadata['product_name'] = data.get('name', '')
                    metadata['description'] = data.get('description', metadata['description'])
                    if 'offers' in data:
                        offers = data['offers']
                        if isinstance(offers, dict):
                            metadata['price'] = offers.get('price', '')
            except:
                pass
        
        # Extract images
        metadata['images'] = self._extract_images(soup, base_url)
        
        # Extract breadcrumbs/navigation
        metadata['breadcrumbs'] = self._extract_breadcrumbs(soup)
        
        return metadata
    
    def _extract_images(self, soup, base_url):
        """
        Extract product images from page
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative URLs
        
        Returns:
            list: List of image URLs
        """
        images = []
        
        # Look for common product image patterns
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if src:
                # Filter out small icons and logos
                width = img.get('width')
                height = img.get('height')
                
                # Skip very small images (likely icons)
                if width and height:
                    try:
                        if int(width) < 100 or int(height) < 100:
                            continue
                    except:
                        pass
                
                full_url = urljoin(base_url, src)
                
                # Filter out common non-product images
                if not any(x in full_url.lower() for x in ['logo', 'icon', 'sprite', 'badge']):
                    images.append(full_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_images = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)
        
        return unique_images
    
    def _extract_breadcrumbs(self, soup):
        """
        Extract breadcrumb navigation
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            list: List of breadcrumb items
        """
        breadcrumbs = []
        
        # Try common breadcrumb patterns
        breadcrumb_container = soup.find('nav', class_=lambda x: x and 'breadcrumb' in x.lower())
        if not breadcrumb_container:
            breadcrumb_container = soup.find('ol', class_=lambda x: x and 'breadcrumb' in x.lower())
        if not breadcrumb_container:
            breadcrumb_container = soup.find('ul', class_=lambda x: x and 'breadcrumb' in x.lower())
        
        if breadcrumb_container:
            items = breadcrumb_container.find_all(['li', 'a', 'span'])
            for item in items:
                text = item.get_text(strip=True)
                if text and text not in ['>', '/', '»']:
                    breadcrumbs.append(text)
        
        return breadcrumbs
    
    def extract_product_data(self, url):
        """
        Extract comprehensive product data from URL
        
        Args:
            url: Product page URL
        
        Returns:
            dict: Extracted product data
        """
        try:
            response = self.fetch_page(url)
            soup = self.parse_html(response.text)
            metadata = self.extract_metadata(soup, url)
            
            # Additional heuristic extraction if structured data is missing
            if not metadata['product_name']:
                # Try H1 tag
                h1 = soup.find('h1')
                if h1:
                    metadata['product_name'] = h1.get_text(strip=True)
            
            if not metadata['description']:
                # Try to find product description div
                desc_selectors = [
                    'div.product-description',
                    'div.description',
                    'div[itemprop="description"]',
                    'div.product-details'
                ]
                for selector in desc_selectors:
                    desc_elem = soup.select_one(selector)
                    if desc_elem:
                        metadata['description'] = desc_elem.get_text(strip=True)
                        break
            
            if not metadata['price']:
                # Try to find price
                price_selectors = [
                    'span.price',
                    'div.price',
                    '[itemprop="price"]',
                    '.product-price'
                ]
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        metadata['price'] = price_elem.get_text(strip=True)
                        break
            
            metadata['source_url'] = url
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting product data from {url}: {e}")
            raise
