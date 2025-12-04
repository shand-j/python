"""
Vape Product Tagger Modules
"""
from .config import Config
from .logger import setup_logger
from .taxonomy import VapeTaxonomy
from .ollama_processor import OllamaProcessor
from .product_tagger import ProductTagger
try:
    from .shopify_handler import ShopifyHandler
except Exception:
    ShopifyHandler = None

try:
    from .unified_cache import UnifiedCache
except Exception:
    UnifiedCache = None

__all__ = [
    'Config',
    'setup_logger',
    'VapeTaxonomy',
    'OllamaProcessor',
    'ProductTagger',
    'ShopifyHandler',
    'UnifiedCache'
]
