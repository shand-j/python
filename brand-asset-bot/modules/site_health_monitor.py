"""
Site Health Monitor Module
Monitors competitor site health and implements intelligent backoff strategies
"""
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import requests
from requests.exceptions import RequestException


class SiteHealthMonitor:
    """Monitors site health and implements exponential backoff"""
    
    def __init__(self, logger=None):
        """
        Initialize health monitor
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.site_metrics: Dict[str, Dict] = {}  # site_name -> metrics
        self.backoff_state: Dict[str, Dict] = {}  # site_name -> backoff state
    
    def check_site_health(self, site_name: str, base_url: str, timeout: int = 30) -> Dict:
        """
        Check site health
        
        Args:
            site_name: Site name
            base_url: Base URL to check
            timeout: Request timeout
        
        Returns:
            Dictionary with health metrics
        """
        start_time = time.time()
        
        try:
            response = requests.head(base_url, timeout=timeout, allow_redirects=True)
            elapsed_ms = (time.time() - start_time) * 1000
            
            status_code = response.status_code
            is_healthy = 200 <= status_code < 400
            is_blocked = status_code in [403, 429] or status_code == 503
            
            health = {
                'last_check': datetime.now().isoformat(),
                'response_time_ms': elapsed_ms,
                'status_code': status_code,
                'is_blocked': is_blocked,
                'is_healthy': is_healthy,
                'consecutive_failures': 0 if is_healthy else self._get_failures(site_name) + 1,
                'last_error': None
            }
            
            # Update metrics
            self._update_metrics(site_name, health)
            
            # Reset backoff if healthy
            if is_healthy and site_name in self.backoff_state:
                del self.backoff_state[site_name]
            
            # Apply backoff if blocked
            elif is_blocked:
                self._apply_backoff(site_name)
            
            if self.logger:
                status_icon = "✓" if is_healthy else "✗"
                self.logger.info(
                    f"{status_icon} {site_name}: {status_code} - {elapsed_ms:.0f}ms"
                )
            
            return health
        
        except RequestException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            
            health = {
                'last_check': datetime.now().isoformat(),
                'response_time_ms': elapsed_ms,
                'status_code': None,
                'is_blocked': False,
                'is_healthy': False,
                'consecutive_failures': self._get_failures(site_name) + 1,
                'last_error': str(e)
            }
            
            self._update_metrics(site_name, health)
            self._apply_backoff(site_name)
            
            if self.logger:
                self.logger.error(f"✗ {site_name}: {e}")
            
            return health
    
    def _get_failures(self, site_name: str) -> int:
        """Get current consecutive failure count"""
        if site_name in self.site_metrics:
            return self.site_metrics[site_name].get('consecutive_failures', 0)
        return 0
    
    def _update_metrics(self, site_name: str, health: Dict):
        """Update site metrics"""
        if site_name not in self.site_metrics:
            self.site_metrics[site_name] = {
                'checks': [],
                'consecutive_failures': 0,
                'total_checks': 0,
                'successful_checks': 0
            }
        
        metrics = self.site_metrics[site_name]
        
        # Add to check history (keep last 100)
        metrics['checks'].append({
            'timestamp': health['last_check'],
            'response_time_ms': health['response_time_ms'],
            'status_code': health['status_code'],
            'is_healthy': health['is_healthy']
        })
        metrics['checks'] = metrics['checks'][-100:]
        
        # Update counters
        metrics['total_checks'] += 1
        if health['is_healthy']:
            metrics['successful_checks'] += 1
            metrics['consecutive_failures'] = 0
        else:
            metrics['consecutive_failures'] = health['consecutive_failures']
    
    def _apply_backoff(self, site_name: str):
        """Apply exponential backoff for failing site"""
        if site_name not in self.backoff_state:
            self.backoff_state[site_name] = {
                'failures': 1,
                'backoff_seconds': 60,  # Start with 1 minute
                'next_allowed_time': datetime.now() + timedelta(seconds=60)
            }
        else:
            state = self.backoff_state[site_name]
            state['failures'] += 1
            
            # Exponential backoff: 1m, 2m, 4m, 8m, 16m, 32m, max 1 hour
            state['backoff_seconds'] = min(state['backoff_seconds'] * 2, 3600)
            state['next_allowed_time'] = datetime.now() + timedelta(seconds=state['backoff_seconds'])
            
            if self.logger:
                self.logger.warning(
                    f"Applied backoff to {site_name}: {state['backoff_seconds']}s "
                    f"(failures: {state['failures']})"
                )
    
    def can_access_site(self, site_name: str) -> bool:
        """
        Check if site can be accessed (not in backoff)
        
        Args:
            site_name: Site name
        
        Returns:
            True if site can be accessed
        """
        if site_name not in self.backoff_state:
            return True
        
        state = self.backoff_state[site_name]
        now = datetime.now()
        
        if now >= state['next_allowed_time']:
            # Backoff period has passed
            del self.backoff_state[site_name]
            return True
        
        return False
    
    def get_backoff_remaining(self, site_name: str) -> Optional[float]:
        """
        Get remaining backoff time in seconds
        
        Args:
            site_name: Site name
        
        Returns:
            Remaining seconds, or None if not in backoff
        """
        if site_name not in self.backoff_state:
            return None
        
        state = self.backoff_state[site_name]
        remaining = (state['next_allowed_time'] - datetime.now()).total_seconds()
        return max(0, remaining)
    
    def get_site_metrics(self, site_name: str) -> Optional[Dict]:
        """Get metrics for a site"""
        return self.site_metrics.get(site_name)
    
    def get_average_response_time(self, site_name: str) -> Optional[float]:
        """Get average response time for a site"""
        metrics = self.site_metrics.get(site_name)
        if not metrics or not metrics['checks']:
            return None
        
        response_times = [c['response_time_ms'] for c in metrics['checks'] if c['response_time_ms'] is not None]
        if not response_times:
            return None
        
        return sum(response_times) / len(response_times)
    
    def get_success_rate(self, site_name: str) -> Optional[float]:
        """Get success rate for a site (0.0 to 1.0)"""
        metrics = self.site_metrics.get(site_name)
        if not metrics or metrics['total_checks'] == 0:
            return None
        
        return metrics['successful_checks'] / metrics['total_checks']
    
    def is_site_blocked(self, site_name: str) -> bool:
        """Check if site appears to be blocking requests"""
        metrics = self.site_metrics.get(site_name)
        if not metrics:
            return False
        
        # Consider blocked if:
        # 1. In backoff state, OR
        # 2. High consecutive failures (5+), OR
        # 3. Recent checks show blocking status codes
        if site_name in self.backoff_state:
            return True
        
        if metrics['consecutive_failures'] >= 5:
            return True
        
        # Check recent checks for blocking patterns
        recent_checks = metrics['checks'][-10:]
        if recent_checks:
            blocking_statuses = [403, 429, 503]
            blocked_count = sum(1 for c in recent_checks 
                              if c['status_code'] in blocking_statuses)
            if blocked_count >= 3:
                return True
        
        return False
    
    def adjust_request_frequency(self, site_name: str, base_delay: float) -> float:
        """
        Adjust request frequency based on site health
        
        Args:
            site_name: Site name
            base_delay: Base delay between requests
        
        Returns:
            Adjusted delay in seconds
        """
        metrics = self.site_metrics.get(site_name)
        if not metrics:
            return base_delay
        
        # Get average response time
        avg_response = self.get_average_response_time(site_name)
        
        # If site is slow, increase delay
        if avg_response and avg_response > 3000:  # > 3 seconds
            multiplier = 2.0
        elif avg_response and avg_response > 1000:  # > 1 second
            multiplier = 1.5
        else:
            multiplier = 1.0
        
        # If success rate is low, increase delay
        success_rate = self.get_success_rate(site_name)
        if success_rate and success_rate < 0.5:  # < 50% success
            multiplier *= 2.0
        elif success_rate and success_rate < 0.8:  # < 80% success
            multiplier *= 1.5
        
        adjusted = base_delay * multiplier
        
        if multiplier > 1.0 and self.logger:
            self.logger.debug(
                f"Adjusted delay for {site_name}: {base_delay}s -> {adjusted:.1f}s "
                f"(multiplier: {multiplier:.1f}x)"
            )
        
        return adjusted
    
    def reset_site_metrics(self, site_name: str):
        """Reset metrics for a site"""
        if site_name in self.site_metrics:
            del self.site_metrics[site_name]
        if site_name in self.backoff_state:
            del self.backoff_state[site_name]
        
        if self.logger:
            self.logger.info(f"Reset metrics for {site_name}")
