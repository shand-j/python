"""
Brand Validator Module
Validates brand websites for accessibility, SSL, and performance
"""
import time
import socket
import ssl
from urllib.parse import urlparse
from typing import Tuple, Dict
import requests
from requests.exceptions import RequestException, SSLError, Timeout


class BrandValidator:
    """Validates brand website information"""
    
    def __init__(self, timeout: int = 10, logger=None):
        """
        Initialize brand validator
        
        Args:
            timeout: Request timeout in seconds
            logger: Logger instance
        """
        self.timeout = timeout
        self.logger = logger
    
    def validate_brand(self, brand_name: str, website: str) -> Dict:
        """
        Validate brand website
        
        Args:
            brand_name: Brand name
            website: Brand website URL or domain
        
        Returns:
            Dictionary with validation results
        """
        if self.logger:
            self.logger.info(f"Validating brand: {brand_name} ({website})")
        
        # Normalize URL
        url = self._normalize_url(website)
        
        # Initialize results
        results = {
            "accessible": False,
            "ssl_valid": False,
            "response_time": None,
            "status_code": None,
            "error_message": None
        }
        
        # Check domain accessibility
        accessible, error = self._check_accessibility(url)
        results["accessible"] = accessible
        
        if not accessible:
            results["error_message"] = error
            if self.logger:
                self.logger.warning(f"Brand {brand_name} not accessible: {error}")
            return results
        
        # Check SSL certificate
        ssl_valid, ssl_error = self._check_ssl(url)
        results["ssl_valid"] = ssl_valid
        
        if not ssl_valid and ssl_error:
            if self.logger:
                self.logger.warning(f"Brand {brand_name} SSL issue: {ssl_error}")
        
        # Measure response time
        response_time, status_code, error = self._measure_response_time(url)
        results["response_time"] = response_time
        results["status_code"] = status_code
        
        if error and not results["error_message"]:
            results["error_message"] = error
        
        if self.logger:
            if results["accessible"] and results["response_time"]:
                self.logger.info(
                    f"Brand {brand_name} validated: "
                    f"Response time: {results['response_time']:.2f}s, "
                    f"SSL: {results['ssl_valid']}, "
                    f"Status: {results['status_code']}"
                )
        
        return results
    
    def _normalize_url(self, website: str) -> str:
        """
        Normalize website URL
        
        Args:
            website: Website URL or domain
        
        Returns:
            Normalized URL with protocol
        """
        # Remove whitespace
        website = website.strip()
        
        # Add protocol if missing
        if not website.startswith(('http://', 'https://')):
            website = f"https://{website}"
        
        return website
    
    def _check_accessibility(self, url: str) -> Tuple[bool, str]:
        """
        Check if domain is accessible
        
        Args:
            url: Website URL
        
        Returns:
            Tuple of (is_accessible, error_message)
        """
        try:
            # Parse URL
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            
            if not domain:
                return False, "Invalid URL format"
            
            # Try to resolve domain
            socket.gethostbyname(domain)
            return True, ""
        
        except socket.gaierror:
            return False, "Domain not found (DNS resolution failed)"
        except Exception as e:
            return False, f"Accessibility check failed: {str(e)}"
    
    def _check_ssl(self, url: str) -> Tuple[bool, str]:
        """
        Check SSL certificate validity
        
        Args:
            url: Website URL
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Only check SSL for HTTPS URLs
        if not url.startswith('https://'):
            return False, "Not using HTTPS"
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            if not domain:
                return False, "Invalid URL"
            
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect and verify certificate
            with socket.create_connection((domain, 443), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    # Get certificate
                    cert = ssock.getpeercert()
                    
                    if cert:
                        return True, ""
                    else:
                        return False, "No certificate found"
        
        except ssl.SSLError as e:
            return False, f"SSL error: {str(e)}"
        except socket.timeout:
            return False, "SSL check timeout"
        except Exception as e:
            return False, f"SSL check failed: {str(e)}"
    
    def _measure_response_time(self, url: str) -> Tuple[float, int, str]:
        """
        Measure website response time
        
        Args:
            url: Website URL
        
        Returns:
            Tuple of (response_time, status_code, error_message)
        """
        try:
            # Make HEAD request to minimize data transfer
            start_time = time.time()
            response = requests.head(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                verify=True  # Verify SSL certificates
            )
            end_time = time.time()
            
            response_time = end_time - start_time
            return response_time, response.status_code, ""
        
        except Timeout:
            return None, None, f"Request timeout after {self.timeout}s"
        except SSLError as e:
            return None, None, f"SSL error: {str(e)}"
        except RequestException as e:
            return None, None, f"Request failed: {str(e)}"
        except Exception as e:
            return None, None, f"Unexpected error: {str(e)}"
    
    def validate_url_format(self, url: str) -> Tuple[bool, str]:
        """
        Validate URL format
        
        Args:
            url: URL to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL is empty"
        
        url = url.strip()
        
        # Check basic format
        if ' ' in url:
            return False, "URL contains spaces"
        
        # Try to parse
        try:
            # Normalize first
            normalized_url = self._normalize_url(url)
            parsed = urlparse(normalized_url)
            
            if not parsed.scheme:
                return False, "Missing URL scheme"
            
            if parsed.scheme not in ['http', 'https']:
                return False, f"Invalid URL scheme: {parsed.scheme}"
            
            if not parsed.netloc and not parsed.path:
                return False, "Missing domain"
            
            return True, ""
        
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"
