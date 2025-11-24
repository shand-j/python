"""
Configuration Manager Module
Handles loading and accessing application configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration manager for the product scraper application"""
    
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
        
        # OpenAI Configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4')
        
        # Image Processing Configuration
        self.image_max_width = int(os.getenv('IMAGE_MAX_WIDTH', 1024))
        self.image_max_height = int(os.getenv('IMAGE_MAX_HEIGHT', 1024))
        self.image_quality = int(os.getenv('IMAGE_QUALITY', 85))
        
        # Scraping Configuration
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', 30))
        self.request_delay = int(os.getenv('REQUEST_DELAY', 2))
        self.max_retries = int(os.getenv('MAX_RETRIES', 3))
        self.user_agent_rotation = os.getenv('USER_AGENT_ROTATION', 'true').lower() == 'true'
        
        # Proxy Configuration
        self.use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
        self.proxy_url = os.getenv('PROXY_URL', '')
        
        # Output Configuration
        self.output_dir = Path(os.getenv('OUTPUT_DIR', './output'))
        self.images_dir = Path(os.getenv('IMAGES_DIR', './images'))
        self.logs_dir = Path(os.getenv('LOGS_DIR', './logs'))
        self.data_dir = Path(os.getenv('DATA_DIR', './data'))
        
        # Brand Asset Configuration
        self.brand_registry_file = Path(os.getenv('BRAND_REGISTRY_FILE', './data/brands.json'))
        self.competitor_sites_file = Path(os.getenv('COMPETITOR_SITES_FILE', './data/competitor_sites.json'))
        self.download_dir = Path(os.getenv('DOWNLOAD_DIR', './downloads'))
        self.extracted_dir = Path(os.getenv('EXTRACTED_DIR', './extracted'))
        self.catalog_dir = Path(os.getenv('CATALOG_DIR', './catalog'))
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Create necessary directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_dir.mkdir(parents=True, exist_ok=True)
    
    def validate(self):
        """
        Validate configuration
        
        Returns:
            tuple: (is_valid, error_message)
        """
        errors = []
        
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required for description enhancement and tagging")
        
        if self.image_max_width <= 0 or self.image_max_height <= 0:
            errors.append("Image dimensions must be positive integers")
        
        if self.request_timeout <= 0:
            errors.append("Request timeout must be a positive integer")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, ""
