"""
Configuration Manager Module
Handles loading and accessing application configuration
"""
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except Exception:
    # Allow tests/environments without python-dotenv
    def load_dotenv(*args, **kwargs):
        return None


class Config:
    """Configuration manager for the vape product tagger application"""
    
    def __init__(self, config_file=None):
        """
        Initialize configuration
        
        Args:
            config_file: Path to .env configuration file
        """
        if config_file:
            load_dotenv(config_file)
        else:
            # Try to load from default locations
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / 'config.env'
            if config_path.exists():
                load_dotenv(config_path)
        
        # Ollama Configuration
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama2')
        self.ollama_timeout = int(os.getenv('OLLAMA_TIMEOUT', 60))
        
        # AI Processing Configuration
        self.ai_confidence_threshold = float(os.getenv('AI_CONFIDENCE_THRESHOLD', 0.7))
        self.enable_ai_tagging = os.getenv('ENABLE_AI_TAGGING', 'true').lower() == 'true'
        self.cache_ai_tags = os.getenv('CACHE_AI_TAGS', 'true').lower() == 'true'
        
        # Batch Processing Configuration
        self.batch_size = int(os.getenv('BATCH_SIZE', 10))
        self.parallel_processing = os.getenv('PARALLEL_PROCESSING', 'true').lower() == 'true'
        self.max_workers = int(os.getenv('MAX_WORKERS', 4))
        
        # Output Configuration
        self.output_dir = Path(os.getenv('OUTPUT_DIR', './output'))
        self.logs_dir = Path(os.getenv('LOGS_DIR', './logs'))
        self.cache_dir = Path(os.getenv('CACHE_DIR', './cache'))
        self.output_format = os.getenv('OUTPUT_FORMAT', 'csv')
        
        # Shopify Configuration
        self.shopify_vendor = os.getenv('SHOPIFY_VENDOR', 'Vape Store')
        self.shopify_product_type = os.getenv('SHOPIFY_PRODUCT_TYPE', 'Vaping Products')
        self.auto_publish = os.getenv('AUTO_PUBLISH', 'true').lower() == 'true'
        
        # Collection Generation Configuration
        self.auto_generate_collections = os.getenv('AUTO_GENERATE_COLLECTIONS', 'true').lower() == 'true'
        self.collection_prefix = os.getenv('COLLECTION_PREFIX', '')
        
        # Compliance Configuration
        self.enable_compliance_tags = os.getenv('ENABLE_COMPLIANCE_TAGS', 'true').lower() == 'true'
        self.default_age_restriction = os.getenv('DEFAULT_AGE_RESTRICTION', '18+')
        self.regional_compliance = os.getenv('REGIONAL_COMPLIANCE', 'US').split(',')
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.verbose_logging = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'
        
        # Create necessary directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        if self.cache_ai_tags:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def validate(self):
        """
        Validate configuration
        
        Returns:
            tuple: (is_valid, error_message)
        """
        errors = []
        
        if self.enable_ai_tagging:
            # Validate Ollama configuration
            if not self.ollama_base_url:
                errors.append("OLLAMA_BASE_URL is required when AI tagging is enabled")
            if not self.ollama_model:
                errors.append("OLLAMA_MODEL is required when AI tagging is enabled")
        
        if self.ai_confidence_threshold < 0 or self.ai_confidence_threshold > 1:
            errors.append("AI_CONFIDENCE_THRESHOLD must be between 0 and 1")
        
        if self.batch_size <= 0:
            errors.append("BATCH_SIZE must be a positive integer")
        
        if self.max_workers <= 0:
            errors.append("MAX_WORKERS must be a positive integer")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, ""
    
    def get_ollama_config(self):
        """Get Ollama configuration as a dictionary"""
        return {
            'base_url': self.ollama_base_url,
            'model': self.ollama_model,
            'timeout': self.ollama_timeout
        }
    
    def get_compliance_config(self):
        """Get compliance configuration as a dictionary"""
        return {
            'enabled': self.enable_compliance_tags,
            'age_restriction': self.default_age_restriction,
            'regional_compliance': self.regional_compliance
        }
