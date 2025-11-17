"""
Vape Product Tagger Modules
"""
from .config import Config
from .logger import setup_logger
from .taxonomy import VapeTaxonomy
from .ollama_processor import OllamaProcessor
from .product_tagger import ProductTagger
from .shopify_handler import ShopifyHandler

__all__ = [
    'Config',
    'setup_logger',
    'VapeTaxonomy',
    'OllamaProcessor',
    'ProductTagger',
    'ShopifyHandler'
]
