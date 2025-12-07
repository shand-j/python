"""
Tag Validator Module
Validates tags against approved_tags.json schema with applies_to rules
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import threading
import time


class TagValidator:
    """Validates product tags against approved schema"""
    
    # Singleton pattern for schema cache
    _instance = None
    _lock = threading.Lock()
    _approved_tags = None
    _last_load_time = 0
    _schema_path = None
    
    def __new__(cls, schema_path: Path = None, logger=None):
        """Singleton pattern to cache approved tags"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, schema_path: Path = None, logger=None):
        """
        Initialize tag validator
        
        Args:
            schema_path: Path to approved_tags.json
            logger: Logger instance
        """
        if not hasattr(self, '_initialized'):
            self.logger = logger
            self._initialized = True
            
            if schema_path:
                TagValidator._schema_path = schema_path
            elif TagValidator._schema_path is None:
                # Default path
                TagValidator._schema_path = Path(__file__).parent.parent / "approved_tags.json"
            
            # Load on first init
            self.load_approved_tags()
    
    def load_approved_tags(self, force_reload: bool = False) -> Dict:
        """
        Load approved tags schema with caching and file watching
        
        Args:
            force_reload: Force reload even if cached
        
        Returns:
            Dict: Approved tags schema
        """
        current_time = time.time()
        
        # Check if reload needed (every 60 seconds or forced)
        if (TagValidator._approved_tags is None or 
            force_reload or 
            current_time - TagValidator._last_load_time > 60):
            
            with TagValidator._lock:
                try:
                    with open(TagValidator._schema_path, 'r') as f:
                        TagValidator._approved_tags = json.load(f)
                    TagValidator._last_load_time = current_time
                    
                    if self.logger:
                        self.logger.debug(f"Loaded approved tags from {TagValidator._schema_path}")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Failed to load approved tags: {e}")
                    TagValidator._approved_tags = {}
        
        return TagValidator._approved_tags
    
    def get_approved_schema(self) -> Dict:
        """Get the approved tags schema"""
        return self.load_approved_tags()
    
    def validate_tag(self, tag: str, category: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a single tag against approved schema
        
        Args:
            tag: Tag to validate
            category: Product category
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, failure_reason)
        """
        schema = self.get_approved_schema()
        
        if not schema:
            return False, "Approved tags schema not loaded"
        
        # Check if tag is a category tag
        if tag in schema.get('category', []):
            return True, None
        
        # Check each tag dimension
        for dimension, config in schema.items():
            if dimension == 'category' or dimension == 'rules':
                continue
            
            # For range-based tags (nicotine_strength, cbd_strength)
            if 'range' in config:
                # Check if tag matches pattern (e.g., "3mg", "1000mg")
                import re
                match = re.match(r'^(\d+(?:\.\d+)?)mg$', tag)
                if match:
                    value = float(match.group(1))
                    min_val = config['range']['min']
                    max_val = config['range']['max']
                    
                    if min_val <= value <= max_val:
                        # Check applies_to
                        applies_to = config.get('applies_to', [])
                        if not applies_to or category in applies_to:
                            return True, None
                        else:
                            return False, f"Tag '{tag}' does not apply to category '{category}'"
                    else:
                        return False, f"Tag '{tag}' value {value} outside range [{min_val}, {max_val}]"
            
            # For enumerated tags
            if 'tags' in config:
                if tag in config['tags']:
                    # Check applies_to
                    applies_to = config.get('applies_to', [])
                    if not applies_to or category in applies_to:
                        return True, None
                    else:
                        return False, f"Tag '{tag}' does not apply to category '{category}'"
        
        return False, f"Tag '{tag}' not found in approved schema"
    
    def validate_applies_to(self, tag: str, category: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a tag applies to the given category
        
        Args:
            tag: Tag to check
            category: Product category
        
        Returns:
            Tuple[bool, Optional[str]]: (applies, failure_reason)
        """
        schema = self.get_approved_schema()
        
        # Find which dimension this tag belongs to
        for dimension, config in schema.items():
            if dimension == 'category' or dimension == 'rules':
                continue
            
            # Check if tag is in this dimension
            is_in_dimension = False
            
            if 'tags' in config and tag in config['tags']:
                is_in_dimension = True
            elif 'range' in config:
                # Check if it's a range-based tag
                import re
                match = re.match(r'^(\d+(?:\.\d+)?)mg$', tag)
                if match:
                    is_in_dimension = True
            
            if is_in_dimension:
                applies_to = config.get('applies_to', [])
                if not applies_to:
                    # No restriction
                    return True, None
                elif category in applies_to:
                    return True, None
                else:
                    return False, f"Tag '{tag}' (dimension: {dimension}) does not apply to category '{category}'. Applies to: {applies_to}"
        
        # Tag not found in any dimension
        return False, f"Tag '{tag}' not found in schema"
    
    def validate_cbd_product(self, tags: List[str], category: str) -> Tuple[bool, List[str]]:
        """
        Validate CBD product has all 3 required dimensions:
        1. CBD Strength (e.g., 1000mg)
        2. CBD Form (e.g., tincture, oil, gummy)
        3. CBD Type (e.g., full_spectrum, broad_spectrum, isolate)
        
        Args:
            tags: List of product tags
            category: Product category
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, failure_reasons)
        """
        if category != "CBD":
            return True, []  # Not a CBD product, validation passes
        
        schema = self.get_approved_schema()
        failures = []
        
        # Check for CBD strength
        has_strength = False
        import re
        for tag in tags:
            match = re.match(r'^(\d+(?:\.\d+)?)mg$', tag)
            if match:
                value = float(match.group(1))
                if 0 <= value <= 50000:  # Valid CBD strength range
                    has_strength = True
                    break
        
        if not has_strength:
            failures.append("CBD product missing cbd_strength tag (0-50000mg)")
        
        # Check for CBD form
        cbd_forms = schema.get('cbd_form', {}).get('tags', [])
        has_form = any(tag in cbd_forms for tag in tags)
        if not has_form:
            failures.append(f"CBD product missing cbd_form tag. Valid options: {cbd_forms}")
        
        # Check for CBD type
        cbd_types = schema.get('cbd_type', {}).get('tags', [])
        has_type = any(tag in cbd_types for tag in tags)
        if not has_type:
            failures.append(f"CBD product missing cbd_type tag. Valid options: {cbd_types}")
        
        return len(failures) == 0, failures
    
    def validate_all_tags(self, tags: List[str], category: str) -> Tuple[bool, List[str]]:
        """
        Validate all tags for a product
        
        Args:
            tags: List of product tags
            category: Product category
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, failure_reasons)
        """
        if not tags:
            return False, ["No tags provided"]
        
        failures = []
        
        # Validate each tag
        for tag in tags:
            is_valid, reason = self.validate_tag(tag, category)
            if not is_valid:
                failures.append(reason)
        
        # CBD-specific validation
        if category == "CBD":
            cbd_valid, cbd_failures = self.validate_cbd_product(tags, category)
            failures.extend(cbd_failures)
        
        # Check for illegal nicotine (>20mg)
        if category in ["e-liquid", "disposable", "nicotine_pouches", "device", "pod_system"]:
            import re
            for tag in tags:
                match = re.match(r'^(\d+(?:\.\d+)?)mg$', tag)
                if match:
                    value = float(match.group(1))
                    if value > 20:
                        failures.append(f"Illegal nicotine strength {value}mg detected (max 20mg)")
        
        return len(failures) == 0, failures
    
    def get_applicable_dimensions(self, category: str) -> Dict[str, List[str]]:
        """
        Get all tag dimensions that apply to a given category
        
        Args:
            category: Product category
        
        Returns:
            Dict mapping dimension names to applicable tags
        """
        schema = self.get_approved_schema()
        applicable = {}
        
        for dimension, config in schema.items():
            if dimension == 'category' or dimension == 'rules':
                continue
            
            applies_to = config.get('applies_to', [])
            if not applies_to or category in applies_to:
                if 'tags' in config:
                    applicable[dimension] = config['tags']
                elif 'range' in config:
                    applicable[dimension] = config['range']
        
        return applicable
