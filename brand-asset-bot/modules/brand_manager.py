"""
Brand Manager Module
Handles brand configuration, validation, and registry management
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class Priority(Enum):
    """Brand priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BrandStatus(Enum):
    """Brand validation status"""
    PENDING = "pending"
    VALIDATED = "validated"
    FAILED = "failed"
    INACTIVE = "inactive"


@dataclass
class Brand:
    """Brand data model"""
    name: str
    website: str
    priority: str = "medium"
    status: str = "pending"
    response_time: Optional[float] = None
    ssl_valid: Optional[bool] = None
    last_validated: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    media_packs: Optional[List[Dict]] = None
    media_pack_count: int = 0
    last_media_scan: Optional[str] = None
    
    def __post_init__(self):
        """Validate and normalize fields after initialization"""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
        
        # Normalize priority
        if self.priority not in [p.value for p in Priority]:
            self.priority = Priority.MEDIUM.value
        
        # Normalize status
        if self.status not in [s.value for s in BrandStatus]:
            self.status = BrandStatus.PENDING.value
    
    def to_dict(self) -> dict:
        """Convert brand to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Brand':
        """Create brand from dictionary"""
        return cls(**data)


class BrandManager:
    """Manages brand configuration and registry"""
    
    def __init__(self, registry_file: Optional[Path] = None, logger=None):
        """
        Initialize brand manager
        
        Args:
            registry_file: Path to brand registry JSON file
            logger: Logger instance
        """
        self.logger = logger
        self.registry_file = registry_file or Path("brands_registry.json")
        self.brands: Dict[str, Brand] = {}
        self.history: List[Dict] = []
        
        # Load existing registry if available
        if self.registry_file.exists():
            self.load_registry()
    
    def load_brands_from_file(self, file_path: Path) -> Tuple[List[Brand], List[str]]:
        """
        Load brands from text file
        
        Args:
            file_path: Path to brands.txt file
        
        Returns:
            Tuple of (brands list, errors list)
        """
        brands = []
        errors = []
        
        if self.logger:
            self.logger.info(f"Loading brands from: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse line format: "BrandName|website.com|priority"
                # or simple format: "BrandName|website.com"
                parts = [p.strip() for p in line.split('|')]
                
                if len(parts) < 2:
                    errors.append(f"Line {line_num}: Invalid format - {line}")
                    continue
                
                name = parts[0]
                website = parts[1]
                priority = parts[2] if len(parts) > 2 else "medium"
                
                # Basic validation
                if not name:
                    errors.append(f"Line {line_num}: Missing brand name")
                    continue
                
                if not website:
                    errors.append(f"Line {line_num}: Missing website for {name}")
                    continue
                
                # Create brand object
                brand = Brand(
                    name=name,
                    website=website,
                    priority=priority
                )
                brands.append(brand)
            
            if self.logger:
                self.logger.info(f"Loaded {len(brands)} brands, {len(errors)} errors")
        
        except FileNotFoundError:
            error_msg = f"Brands file not found: {file_path}"
            errors.append(error_msg)
            if self.logger:
                self.logger.error(error_msg)
        except Exception as e:
            error_msg = f"Error loading brands file: {e}"
            errors.append(error_msg)
            if self.logger:
                self.logger.error(error_msg)
        
        return brands, errors
    
    def add_brand(self, brand: Brand) -> bool:
        """
        Add brand to registry
        
        Args:
            brand: Brand object to add
        
        Returns:
            bool: True if added successfully
        """
        if brand.name in self.brands:
            if self.logger:
                self.logger.warning(f"Brand {brand.name} already exists, updating instead")
            return self.update_brand(brand)
        
        self.brands[brand.name] = brand
        self._add_to_history("add", brand.name, brand.to_dict())
        
        if self.logger:
            self.logger.info(f"Added brand: {brand.name}")
        
        return True
    
    def update_brand(self, brand: Brand) -> bool:
        """
        Update existing brand
        
        Args:
            brand: Brand object with updated data
        
        Returns:
            bool: True if updated successfully
        """
        if brand.name not in self.brands:
            if self.logger:
                self.logger.error(f"Brand {brand.name} not found")
            return False
        
        old_data = self.brands[brand.name].to_dict()
        brand.updated_at = datetime.now().isoformat()
        self.brands[brand.name] = brand
        
        self._add_to_history("update", brand.name, {
            "old": old_data,
            "new": brand.to_dict()
        })
        
        if self.logger:
            self.logger.info(f"Updated brand: {brand.name}")
        
        return True
    
    def remove_brand(self, brand_name: str) -> bool:
        """
        Remove brand from registry
        
        Args:
            brand_name: Name of brand to remove
        
        Returns:
            bool: True if removed successfully
        """
        if brand_name not in self.brands:
            if self.logger:
                self.logger.error(f"Brand {brand_name} not found")
            return False
        
        brand_data = self.brands[brand_name].to_dict()
        del self.brands[brand_name]
        
        self._add_to_history("remove", brand_name, brand_data)
        
        if self.logger:
            self.logger.info(f"Removed brand: {brand_name}")
        
        return True
    
    def get_brand(self, brand_name: str) -> Optional[Brand]:
        """
        Get brand by name
        
        Args:
            brand_name: Name of brand
        
        Returns:
            Brand object or None
        """
        return self.brands.get(brand_name)
    
    def get_all_brands(self) -> List[Brand]:
        """Get all brands"""
        return list(self.brands.values())
    
    def get_brands_by_priority(self, priority: str) -> List[Brand]:
        """
        Get brands filtered by priority
        
        Args:
            priority: Priority level (high, medium, low)
        
        Returns:
            List of brands with specified priority
        """
        return [b for b in self.brands.values() if b.priority == priority]
    
    def get_processing_queue(self) -> List[Brand]:
        """
        Get brands ordered by priority for processing
        
        Returns:
            List of brands ordered by priority (high -> medium -> low)
        """
        queue = []
        
        # Add in priority order
        for priority in [Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
            brands = self.get_brands_by_priority(priority.value)
            # Sort by name within same priority for consistency
            brands.sort(key=lambda b: b.name)
            queue.extend(brands)
        
        if self.logger:
            self.logger.info(f"Processing queue prepared: {len(queue)} brands")
        
        return queue
    
    def save_registry(self) -> bool:
        """
        Save brand registry to file
        
        Returns:
            bool: True if saved successfully
        """
        try:
            data = {
                "brands": {name: brand.to_dict() for name, brand in self.brands.items()},
                "history": self.history,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            if self.logger:
                self.logger.info(f"Registry saved: {self.registry_file}")
            
            return True
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error saving registry: {e}")
            return False
    
    def load_registry(self) -> bool:
        """
        Load brand registry from file
        
        Returns:
            bool: True if loaded successfully
        """
        try:
            with open(self.registry_file, 'r') as f:
                data = json.load(f)
            
            # Load brands
            self.brands = {}
            for name, brand_data in data.get("brands", {}).items():
                self.brands[name] = Brand.from_dict(brand_data)
            
            # Load history
            self.history = data.get("history", [])
            
            if self.logger:
                self.logger.info(f"Registry loaded: {len(self.brands)} brands")
            
            return True
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error loading registry: {e}")
            return False
    
    def get_history(self) -> List[Dict]:
        """Get registry modification history"""
        return self.history
    
    def generate_error_summary(self, errors: List[str]) -> str:
        """
        Generate error summary report
        
        Args:
            errors: List of error messages
        
        Returns:
            Formatted error summary
        """
        if not errors:
            return "No errors"
        
        summary = f"Error Summary ({len(errors)} errors):\n"
        summary += "=" * 60 + "\n"
        for i, error in enumerate(errors, 1):
            summary += f"{i}. {error}\n"
        summary += "=" * 60
        
        return summary
    
    def _add_to_history(self, action: str, brand_name: str, data: dict):
        """Add entry to history"""
        self.history.append({
            "action": action,
            "brand": brand_name,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
