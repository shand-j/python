"""
Competitor Site Manager Module
Manages competitor website configuration for ethical product scraping
"""
import json
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    """Site priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SiteStatus(str, Enum):
    """Site status"""
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    INACTIVE = "inactive"


@dataclass
class ScrapingParameters:
    """Scraping parameters for a competitor site"""
    request_delay: float = 2.0  # seconds between requests
    max_pages_per_session: int = 100  # maximum pages to scrape in one session
    concurrent_requests: int = 1  # number of concurrent requests
    timeout_seconds: int = 30  # request timeout
    respect_robots_txt: bool = True  # respect robots.txt
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScrapingParameters':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def validate(self) -> List[str]:
        """Validate parameters and return list of errors"""
        errors = []
        
        if self.request_delay < 0.5:
            errors.append("request_delay must be at least 0.5 seconds")
        if self.request_delay > 60:
            errors.append("request_delay cannot exceed 60 seconds")
        
        if self.max_pages_per_session < 1:
            errors.append("max_pages_per_session must be at least 1")
        if self.max_pages_per_session > 10000:
            errors.append("max_pages_per_session cannot exceed 10000")
        
        if self.concurrent_requests < 1:
            errors.append("concurrent_requests must be at least 1")
        if self.concurrent_requests > 5:
            errors.append("concurrent_requests cannot exceed 5 (avoid overwhelming servers)")
        
        if self.timeout_seconds < 5:
            errors.append("timeout_seconds must be at least 5")
        if self.timeout_seconds > 300:
            errors.append("timeout_seconds cannot exceed 300")
        
        return errors


@dataclass
class SiteStructure:
    """Site structure information"""
    categories: Dict[str, str] = field(default_factory=dict)  # category name -> URL pattern
    pagination_pattern: Optional[str] = None
    product_url_pattern: Optional[str] = None
    analyzed_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SiteStructure':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RobotsTxtInfo:
    """Robots.txt compliance information"""
    allowed_paths: List[str] = field(default_factory=list)
    disallowed_paths: List[str] = field(default_factory=list)
    crawl_delay: Optional[float] = None
    user_agent: str = "*"
    last_checked: Optional[str] = None
    compliant: bool = True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RobotsTxtInfo':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SiteHealth:
    """Site health monitoring data"""
    last_check: Optional[str] = None
    response_time_ms: Optional[float] = None
    status_code: Optional[int] = None
    is_blocked: bool = False
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SiteHealth':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CompetitorSite:
    """Competitor website configuration"""
    name: str
    base_url: str
    priority: str = Priority.MEDIUM.value
    status: str = SiteStatus.PENDING.value
    scraping_params: ScrapingParameters = field(default_factory=ScrapingParameters)
    site_structure: SiteStructure = field(default_factory=SiteStructure)
    robots_txt_info: RobotsTxtInfo = field(default_factory=RobotsTxtInfo)
    site_health: SiteHealth = field(default_factory=SiteHealth)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = {
            'name': self.name,
            'base_url': self.base_url,
            'priority': self.priority,
            'status': self.status,
            'scraping_params': self.scraping_params.to_dict(),
            'site_structure': self.site_structure.to_dict(),
            'robots_txt_info': self.robots_txt_info.to_dict(),
            'site_health': self.site_health.to_dict(),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'notes': self.notes
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CompetitorSite':
        """Create from dictionary"""
        site = cls(
            name=data['name'],
            base_url=data['base_url'],
            priority=data.get('priority', Priority.MEDIUM.value),
            status=data.get('status', SiteStatus.PENDING.value),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            notes=data.get('notes', '')
        )
        
        if 'scraping_params' in data:
            site.scraping_params = ScrapingParameters.from_dict(data['scraping_params'])
        
        if 'site_structure' in data:
            site.site_structure = SiteStructure.from_dict(data['site_structure'])
        
        if 'robots_txt_info' in data:
            site.robots_txt_info = RobotsTxtInfo.from_dict(data['robots_txt_info'])
        
        if 'site_health' in data:
            site.site_health = SiteHealth.from_dict(data['site_health'])
        
        return site


class CompetitorSiteManager:
    """Manages competitor site registry"""
    
    def __init__(self, registry_file: Path, logger=None):
        """
        Initialize site manager
        
        Args:
            registry_file: Path to JSON registry file
            logger: Logger instance
        """
        self.registry_file = Path(registry_file)
        self.logger = logger
        self.sites: Dict[str, CompetitorSite] = {}
        self.history: List[Dict] = []
        
        # Load existing registry
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from file"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load sites
                    for site_data in data.get('sites', []):
                        site = CompetitorSite.from_dict(site_data)
                        self.sites[site.name] = site
                    
                    # Load history
                    self.history = data.get('history', [])
                
                if self.logger:
                    self.logger.info(f"Loaded {len(self.sites)} competitor sites from registry")
            
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to load registry: {e}")
    
    def _save_registry(self):
        """Save registry to file"""
        try:
            # Create parent directory if needed
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'sites': [site.to_dict() for site in self.sites.values()],
                'history': self.history[-1000:]  # Keep last 1000 history entries
            }
            
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            if self.logger:
                self.logger.debug(f"Saved {len(self.sites)} sites to registry")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save registry: {e}")
            raise
    
    def _add_history(self, action: str, site_name: str, details: str = ""):
        """Add entry to history"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'site': site_name,
            'details': details
        }
        self.history.append(entry)
    
    def add_site(self, site: CompetitorSite) -> bool:
        """
        Add competitor site
        
        Args:
            site: CompetitorSite to add
        
        Returns:
            True if added successfully
        """
        if site.name in self.sites:
            if self.logger:
                self.logger.warning(f"Site already exists: {site.name}")
            return False
        
        # Validate parameters
        errors = site.scraping_params.validate()
        if errors:
            if self.logger:
                self.logger.error(f"Invalid scraping parameters: {', '.join(errors)}")
            return False
        
        self.sites[site.name] = site
        self._add_history('add', site.name, f"Added site: {site.base_url}")
        self._save_registry()
        
        if self.logger:
            self.logger.info(f"Added competitor site: {site.name}")
        
        return True
    
    def update_site(self, name: str, **kwargs) -> bool:
        """
        Update competitor site
        
        Args:
            name: Site name
            **kwargs: Fields to update
        
        Returns:
            True if updated successfully
        """
        if name not in self.sites:
            if self.logger:
                self.logger.error(f"Site not found: {name}")
            return False
        
        site = self.sites[name]
        updated_fields = []
        
        # Update simple fields
        for field_name in ['base_url', 'priority', 'status', 'notes']:
            if field_name in kwargs:
                setattr(site, field_name, kwargs[field_name])
                updated_fields.append(field_name)
        
        # Update scraping parameters
        if 'scraping_params' in kwargs:
            site.scraping_params = kwargs['scraping_params']
            updated_fields.append('scraping_params')
        
        # Update timestamp
        site.updated_at = datetime.now().isoformat()
        
        self._add_history('update', name, f"Updated: {', '.join(updated_fields)}")
        self._save_registry()
        
        if self.logger:
            self.logger.info(f"Updated site: {name}")
        
        return True
    
    def remove_site(self, name: str) -> bool:
        """
        Remove competitor site
        
        Args:
            name: Site name
        
        Returns:
            True if removed successfully
        """
        if name not in self.sites:
            if self.logger:
                self.logger.error(f"Site not found: {name}")
            return False
        
        del self.sites[name]
        self._add_history('remove', name, "Removed site")
        self._save_registry()
        
        if self.logger:
            self.logger.info(f"Removed site: {name}")
        
        return True
    
    def get_site(self, name: str) -> Optional[CompetitorSite]:
        """Get site by name"""
        return self.sites.get(name)
    
    def get_all_sites(self) -> List[CompetitorSite]:
        """Get all sites"""
        return list(self.sites.values())
    
    def get_sites_by_priority(self, priority: str) -> List[CompetitorSite]:
        """Get sites filtered by priority"""
        return [s for s in self.sites.values() if s.priority == priority]
    
    def get_sites_by_status(self, status: str) -> List[CompetitorSite]:
        """Get sites filtered by status"""
        return [s for s in self.sites.values() if s.status == status]
    
    def get_active_sites(self) -> List[CompetitorSite]:
        """Get all active sites"""
        return self.get_sites_by_status(SiteStatus.ACTIVE.value)
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get history entries"""
        return self.history[-limit:]
    
    def load_sites_from_file(self, filepath: Path) -> int:
        """
        Load sites from file (pipe-delimited: Name|URL|Priority)
        
        Args:
            filepath: Path to file
        
        Returns:
            Number of sites loaded
        """
        if not filepath.exists():
            if self.logger:
                self.logger.error(f"File not found: {filepath}")
            return 0
        
        loaded = 0
        errors = []
        
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse pipe-delimited line
                parts = [p.strip() for p in line.split('|')]
                
                if len(parts) < 2:
                    errors.append(f"Line {line_num}: Invalid format (need at least Name|URL)")
                    continue
                
                name = parts[0]
                base_url = parts[1]
                priority = parts[2] if len(parts) > 2 else Priority.MEDIUM.value
                
                # Validate priority
                if priority not in [Priority.HIGH.value, Priority.MEDIUM.value, Priority.LOW.value]:
                    errors.append(f"Line {line_num}: Invalid priority '{priority}'")
                    continue
                
                # Create site
                site = CompetitorSite(
                    name=name,
                    base_url=base_url,
                    priority=priority,
                    status=SiteStatus.PENDING.value
                )
                
                if self.add_site(site):
                    loaded += 1
                else:
                    errors.append(f"Line {line_num}: Failed to add site '{name}'")
        
        if errors and self.logger:
            self.logger.warning(f"Loaded {loaded} sites with {len(errors)} errors")
            for error in errors[:10]:  # Log first 10 errors
                self.logger.warning(f"  {error}")
        
        return loaded
