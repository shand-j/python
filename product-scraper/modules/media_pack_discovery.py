"""
Media Pack Discovery Module
Discovers and analyzes official media packs from brand websites
"""
import re
import time
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse, urlunparse
from dataclasses import dataclass, asdict
import requests
from bs4 import BeautifulSoup


@dataclass
class MediaPackInfo:
    """Information about a discovered media pack"""
    url: str
    file_type: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    accessible: bool = False
    restricted: bool = False
    restriction_type: Optional[str] = None
    estimated_download_time: Optional[float] = None
    discovered_from: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MediaPackInfo':
        """Create from dictionary"""
        return cls(**data)


class MediaPackDiscovery:
    """Discovers official media packs from brand websites"""
    
    # Standard media pack path patterns
    MEDIA_PACK_PATHS = [
        '/media-pack',
        '/media-packs',
        '/mediapack',
        '/mediapacks',
        '/press',
        '/press-kit',
        '/press-kits',
        '/presskit',
        '/presskits',
        '/resources',
        '/resource',
        '/downloads',
        '/download',
        '/assets',
        '/media',
        '/marketing',
        '/brand-assets',
        '/brand-resources',
    ]
    
    # Recognized media file extensions and their categories
    FILE_TYPES = {
        # Compressed archives (highest priority)
        '.zip': {'category': 'archive', 'priority': 1, 'content_type': 'Compressed archive'},
        '.rar': {'category': 'archive', 'priority': 1, 'content_type': 'Compressed archive'},
        '.7z': {'category': 'archive', 'priority': 1, 'content_type': 'Compressed archive'},
        '.tar.gz': {'category': 'archive', 'priority': 1, 'content_type': 'Compressed archive'},
        '.tgz': {'category': 'archive', 'priority': 1, 'content_type': 'Compressed archive'},
        
        # Documentation
        '.pdf': {'category': 'document', 'priority': 2, 'content_type': 'Documentation'},
        
        # High-res images
        '.jpg': {'category': 'image', 'priority': 3, 'content_type': 'High-res images'},
        '.jpeg': {'category': 'image', 'priority': 3, 'content_type': 'High-res images'},
        '.png': {'category': 'image', 'priority': 3, 'content_type': 'High-res images'},
        
        # Vector graphics
        '.svg': {'category': 'vector', 'priority': 3, 'content_type': 'Vector graphics'},
        '.ai': {'category': 'vector', 'priority': 3, 'content_type': 'Vector graphics'},
        '.eps': {'category': 'vector', 'priority': 3, 'content_type': 'Vector graphics'},
    }
    
    def __init__(self, config, logger):
        """
        Initialize media pack discovery
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.session = requests.Session()
        self.timeout = getattr(config, 'request_timeout', 30)
    
    def discover_media_packs(self, brand_name: str, website: str) -> List[MediaPackInfo]:
        """
        Discover media packs for a brand
        
        Args:
            brand_name: Brand name
            website: Brand website URL
        
        Returns:
            List of discovered media packs
        """
        if self.logger:
            self.logger.info(f"Discovering media packs for {brand_name} ({website})")
        
        media_packs = []
        discovered_urls = set()
        
        # Normalize URL
        base_url = self._normalize_url(website)
        
        # 1. Check standard media pack paths
        for path in self.MEDIA_PACK_PATHS:
            url = urljoin(base_url, path)
            packs = self._scan_url_for_media(url, base_url, discovered_urls)
            media_packs.extend(packs)
        
        # 2. Scan homepage for media pack links
        homepage_packs = self._scan_homepage(base_url, discovered_urls)
        media_packs.extend(homepage_packs)
        
        # 3. Search for alternative domains
        alt_domains = self._discover_alternative_domains(brand_name, base_url)
        for alt_domain in alt_domains:
            alt_packs = self._scan_url_for_media(alt_domain, alt_domain, discovered_urls)
            media_packs.extend(alt_packs)
        
        if self.logger:
            self.logger.info(f"Discovered {len(media_packs)} media pack(s) for {brand_name}")
        
        return media_packs
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to ensure it has a proper scheme"""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        return url
    
    def _scan_url_for_media(self, url: str, base_url: str, discovered_urls: Set[str]) -> List[MediaPackInfo]:
        """
        Scan a URL for media pack files
        
        Args:
            url: URL to scan
            base_url: Base URL for resolving relative links
            discovered_urls: Set of already discovered URLs to avoid duplicates
        
        Returns:
            List of discovered media packs
        """
        media_packs = []
        
        try:
            # Fetch the page
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                headers=self._get_headers()
            )
            
            if response.status_code != 200:
                return media_packs
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                if not href:
                    continue
                
                # Resolve relative URLs
                absolute_url = urljoin(base_url, href)
                
                # Skip if already discovered
                if absolute_url in discovered_urls:
                    continue
                
                # Check if it's a media file
                file_type = self._get_file_type(absolute_url)
                if file_type:
                    discovered_urls.add(absolute_url)
                    
                    # Analyze the media pack
                    media_info = self._analyze_media_pack(absolute_url, file_type, url)
                    if media_info:
                        media_packs.append(media_info)
                        
                        if self.logger:
                            self.logger.info(f"  Found: {absolute_url} ({file_type})")
        
        except requests.exceptions.RequestException as e:
            if self.logger:
                self.logger.debug(f"Could not scan {url}: {e}")
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error scanning {url}: {e}")
        
        return media_packs
    
    def _scan_homepage(self, base_url: str, discovered_urls: Set[str]) -> List[MediaPackInfo]:
        """
        Scan homepage for media pack links
        
        Args:
            base_url: Base URL to scan
            discovered_urls: Set of already discovered URLs
        
        Returns:
            List of discovered media packs
        """
        media_packs = []
        
        try:
            response = self.session.get(
                base_url,
                timeout=self.timeout,
                headers=self._get_headers()
            )
            
            if response.status_code != 200:
                return media_packs
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Search for keywords in links
            keywords = ['media', 'press', 'resource', 'download', 'asset', 'kit', 'marketing']
            
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                link_text = link.get_text().lower()
                
                # Check if link text contains keywords
                if any(keyword in link_text for keyword in keywords):
                    absolute_url = urljoin(base_url, href)
                    
                    # Scan this potential media page
                    packs = self._scan_url_for_media(absolute_url, base_url, discovered_urls)
                    media_packs.extend(packs)
        
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error scanning homepage {base_url}: {e}")
        
        return media_packs
    
    def _get_file_type(self, url: str) -> Optional[str]:
        """
        Get file type from URL
        
        Args:
            url: URL to check
        
        Returns:
            File extension if recognized, None otherwise
        """
        url_lower = url.lower()
        
        # Check for multi-part extensions first
        if '.tar.gz' in url_lower:
            return '.tar.gz'
        
        # Check single extensions
        for ext in self.FILE_TYPES.keys():
            if ext != '.tar.gz' and url_lower.endswith(ext):
                return ext
        
        return None
    
    def _analyze_media_pack(self, url: str, file_type: str, discovered_from: str) -> Optional[MediaPackInfo]:
        """
        Analyze a media pack before download
        
        Args:
            url: URL of media pack
            file_type: File type extension
            discovered_from: URL where this was discovered
        
        Returns:
            MediaPackInfo object or None if analysis fails
        """
        try:
            # Use HEAD request to get metadata without downloading
            response = self.session.head(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                headers=self._get_headers()
            )
            
            # Get file information
            file_size = None
            content_type = response.headers.get('Content-Type', '')
            
            if 'Content-Length' in response.headers:
                file_size = int(response.headers['Content-Length'])
            
            # Check accessibility
            accessible = response.status_code == 200
            
            # Check for access restrictions
            restricted = False
            restriction_type = None
            
            if response.status_code == 401:
                restricted = True
                restriction_type = "Authentication required"
            elif response.status_code == 403:
                restricted = True
                restriction_type = "Access forbidden"
            elif 'WWW-Authenticate' in response.headers:
                restricted = True
                restriction_type = "Authentication required"
            
            # Estimate download time (assuming 1 MB/s average)
            estimated_time = None
            if file_size:
                estimated_time = file_size / (1024 * 1024)  # seconds
            
            # Get content type description
            file_info = self.FILE_TYPES.get(file_type, {})
            content_type_desc = file_info.get('content_type', 'Unknown')
            
            return MediaPackInfo(
                url=url,
                file_type=file_type,
                file_size=file_size,
                content_type=content_type_desc,
                accessible=accessible,
                restricted=restricted,
                restriction_type=restriction_type,
                estimated_download_time=estimated_time,
                discovered_from=discovered_from
            )
        
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error analyzing {url}: {e}")
            
            # Return basic info even if analysis fails
            file_info = self.FILE_TYPES.get(file_type, {})
            return MediaPackInfo(
                url=url,
                file_type=file_type,
                content_type=file_info.get('content_type', 'Unknown'),
                accessible=False,
                discovered_from=discovered_from
            )
    
    def _discover_alternative_domains(self, brand_name: str, primary_domain: str) -> List[str]:
        """
        Discover alternative domains for a brand
        
        Args:
            brand_name: Brand name
            primary_domain: Primary domain URL
        
        Returns:
            List of alternative domain URLs
        """
        alternative_domains = []
        
        # Parse primary domain
        parsed = urlparse(primary_domain)
        domain_parts = parsed.netloc.split('.')
        
        if len(domain_parts) < 2:
            return alternative_domains
        
        # Get base name (e.g., 'smoktech' from 'smoktech.com')
        base_name = domain_parts[0]
        
        # Common alternative patterns
        patterns = [
            f"{base_name}store",
            f"{base_name}shop",
            f"{base_name}-store",
            f"{base_name}-shop",
            f"shop{base_name}",
            f"store{base_name}",
        ]
        
        tld = '.'.join(domain_parts[1:])
        
        for pattern in patterns:
            alt_domain = f"https://{pattern}.{tld}"
            
            # Quick check if domain exists
            try:
                response = self.session.head(
                    alt_domain,
                    timeout=5,
                    allow_redirects=True,
                    headers=self._get_headers()
                )
                
                if response.status_code in [200, 301, 302]:
                    alternative_domains.append(alt_domain)
                    
                    if self.logger:
                        self.logger.info(f"  Discovered alternative domain: {alt_domain}")
            
            except Exception:
                pass  # Domain doesn't exist or not accessible
        
        return alternative_domains
    
    def _get_headers(self) -> dict:
        """Get request headers"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    def get_prioritized_packs(self, media_packs: List[MediaPackInfo]) -> List[MediaPackInfo]:
        """
        Get media packs ordered by priority
        
        Args:
            media_packs: List of media packs
        
        Returns:
            List sorted by priority (archives first)
        """
        def get_priority(pack: MediaPackInfo) -> int:
            file_info = self.FILE_TYPES.get(pack.file_type, {})
            return file_info.get('priority', 99)
        
        return sorted(media_packs, key=get_priority)
    
    def format_file_size(self, size_bytes: Optional[int]) -> str:
        """
        Format file size in human-readable format
        
        Args:
            size_bytes: Size in bytes
        
        Returns:
            Formatted string
        """
        if size_bytes is None:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.1f} TB"
