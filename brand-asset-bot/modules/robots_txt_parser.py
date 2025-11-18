"""
Robots.txt Parser Module
Parses and enforces robots.txt compliance for ethical scraping
"""
import re
from typing import List, Optional, Dict, Tuple
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import requests


class RobotsTxtParser:
    """Parser for robots.txt files with compliance checking"""
    
    def __init__(self, logger=None):
        """
        Initialize parser
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.parsers: Dict[str, RobotFileParser] = {}  # domain -> parser
        self.crawl_delays: Dict[str, float] = {}  # domain -> delay
    
    def fetch_and_parse(self, base_url: str, user_agent: str = "*") -> Tuple[bool, Optional[Dict]]:
        """
        Fetch and parse robots.txt for a website
        
        Args:
            base_url: Base URL of website
            user_agent: User agent to check rules for
        
        Returns:
            Tuple of (success, robots_info_dict)
        """
        try:
            # Normalize URL
            parsed = urlparse(base_url)
            if not parsed.scheme:
                base_url = f"https://{base_url}"
                parsed = urlparse(base_url)
            
            domain = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = urljoin(domain, "/robots.txt")
            
            if self.logger:
                self.logger.debug(f"Fetching robots.txt from: {robots_url}")
            
            # Fetch robots.txt
            response = requests.get(robots_url, timeout=10)
            
            if response.status_code == 404:
                # No robots.txt - assume everything is allowed
                if self.logger:
                    self.logger.info(f"No robots.txt found at {domain} - assuming allowed")
                
                return True, {
                    'allowed_paths': ['*'],
                    'disallowed_paths': [],
                    'crawl_delay': None,
                    'user_agent': user_agent,
                    'compliant': True
                }
            
            if response.status_code != 200:
                if self.logger:
                    self.logger.warning(f"Failed to fetch robots.txt: HTTP {response.status_code}")
                return False, None
            
            # Parse robots.txt
            parser = RobotFileParser()
            parser.parse(response.text.splitlines())
            
            # Store parser
            self.parsers[domain] = parser
            
            # Extract crawl-delay
            crawl_delay = self._extract_crawl_delay(response.text, user_agent)
            if crawl_delay:
                self.crawl_delays[domain] = crawl_delay
            
            # Extract allowed/disallowed paths
            allowed_paths, disallowed_paths = self._extract_paths(response.text, user_agent)
            
            robots_info = {
                'allowed_paths': allowed_paths,
                'disallowed_paths': disallowed_paths,
                'crawl_delay': crawl_delay,
                'user_agent': user_agent,
                'compliant': True
            }
            
            if self.logger:
                self.logger.info(f"Parsed robots.txt for {domain}")
                if crawl_delay:
                    self.logger.info(f"  Crawl-delay: {crawl_delay}s")
                if disallowed_paths:
                    self.logger.info(f"  Disallowed paths: {len(disallowed_paths)}")
            
            return True, robots_info
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to fetch/parse robots.txt: {e}")
            return False, None
    
    def _extract_crawl_delay(self, robots_txt: str, user_agent: str) -> Optional[float]:
        """Extract crawl-delay directive for user agent"""
        lines = robots_txt.lower().splitlines()
        current_agent = None
        
        for line in lines:
            line = line.strip()
            
            # Check for user-agent
            if line.startswith('user-agent:'):
                agent = line.split(':', 1)[1].strip()
                current_agent = agent
            
            # Check for crawl-delay
            elif line.startswith('crawl-delay:'):
                if current_agent == '*' or current_agent == user_agent.lower():
                    try:
                        delay = float(line.split(':', 1)[1].strip())
                        return delay
                    except ValueError:
                        pass
        
        return None
    
    def _extract_paths(self, robots_txt: str, user_agent: str) -> Tuple[List[str], List[str]]:
        """Extract allowed and disallowed paths for user agent"""
        lines = robots_txt.lower().splitlines()
        current_agent = None
        allowed_paths = []
        disallowed_paths = []
        
        for line in lines:
            line = line.strip()
            
            # Check for user-agent
            if line.startswith('user-agent:'):
                agent = line.split(':', 1)[1].strip()
                current_agent = agent
            
            # Check for allow
            elif line.startswith('allow:'):
                if current_agent == '*' or current_agent == user_agent.lower():
                    path = line.split(':', 1)[1].strip()
                    if path:
                        allowed_paths.append(path)
            
            # Check for disallow
            elif line.startswith('disallow:'):
                if current_agent == '*' or current_agent == user_agent.lower():
                    path = line.split(':', 1)[1].strip()
                    if path:
                        disallowed_paths.append(path)
        
        return allowed_paths, disallowed_paths
    
    def can_fetch(self, base_url: str, path: str, user_agent: str = "*") -> bool:
        """
        Check if a path can be fetched according to robots.txt
        
        Args:
            base_url: Base URL of website
            path: Path to check
            user_agent: User agent to check for
        
        Returns:
            True if fetching is allowed
        """
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"https://{base_url}"
            parsed = urlparse(base_url)
        
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # If we haven't parsed robots.txt for this domain, fetch it
        if domain not in self.parsers:
            success, _ = self.fetch_and_parse(base_url, user_agent)
            if not success:
                # If we can't fetch robots.txt, be conservative and allow
                return True
        
        parser = self.parsers.get(domain)
        if not parser:
            return True
        
        # Check if path is allowed
        full_url = urljoin(domain, path)
        return parser.can_fetch(user_agent, full_url)
    
    def get_crawl_delay(self, base_url: str) -> Optional[float]:
        """
        Get crawl-delay for a domain
        
        Args:
            base_url: Base URL of website
        
        Returns:
            Crawl delay in seconds, or None if not specified
        """
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"https://{base_url}"
            parsed = urlparse(base_url)
        
        domain = f"{parsed.scheme}://{parsed.netloc}"
        return self.crawl_delays.get(domain)
    
    def check_compliance(self, base_url: str, paths_to_scrape: List[str], user_agent: str = "*") -> Dict:
        """
        Check compliance for a list of paths
        
        Args:
            base_url: Base URL of website
            paths_to_scrape: List of paths to check
            user_agent: User agent to check for
        
        Returns:
            Dictionary with compliance results
        """
        # Fetch robots.txt if not already done
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"https://{base_url}"
            parsed = urlparse(base_url)
        
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        if domain not in self.parsers:
            success, robots_info = self.fetch_and_parse(base_url, user_agent)
            if not success:
                return {
                    'compliant': False,
                    'error': 'Failed to fetch robots.txt',
                    'allowed_paths': [],
                    'blocked_paths': paths_to_scrape
                }
        
        # Check each path
        allowed = []
        blocked = []
        
        for path in paths_to_scrape:
            if self.can_fetch(base_url, path, user_agent):
                allowed.append(path)
            else:
                blocked.append(path)
        
        crawl_delay = self.get_crawl_delay(base_url)
        
        return {
            'compliant': len(blocked) == 0,
            'allowed_paths': allowed,
            'blocked_paths': blocked,
            'crawl_delay': crawl_delay,
            'total_paths': len(paths_to_scrape),
            'allowed_count': len(allowed),
            'blocked_count': len(blocked)
        }
