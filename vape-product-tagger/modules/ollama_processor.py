"""
Ollama AI Integration Module
Handles semantic analysis and tag generation using Ollama
"""
import json
import requests
from typing import Dict, List, Optional
import hashlib
from pathlib import Path


class OllamaProcessor:
    """Ollama AI processor for semantic tag generation"""
    
    def __init__(self, config, logger):
        """
        Initialize Ollama processor
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.base_url = config.ollama_base_url
        self.model = config.ollama_model
        self.timeout = config.ollama_timeout
        self.cache_enabled = config.cache_ai_tags
        self.cache_dir = config.cache_dir if config.cache_ai_tags else None
        
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, product_data: Dict) -> str:
        """
        Generate cache key for product data
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            str: MD5 hash for cache key
        """
        # Create a stable string representation
        cache_string = f"{product_data.get('title', '')}_{product_data.get('description', '')}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_cached_tags(self, cache_key: str) -> Optional[Dict]:
        """
        Retrieve cached tags if available
        
        Args:
            cache_key: Cache key
        
        Returns:
            Optional[Dict]: Cached tags or None
        """
        if not self.cache_enabled:
            return None
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.logger.debug(f"Cache hit for key: {cache_key}")
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to read cache file: {e}")
        
        return None
    
    def _save_cached_tags(self, cache_key: str, tags: Dict):
        """
        Save tags to cache
        
        Args:
            cache_key: Cache key
            tags: Tags dictionary
        """
        if not self.cache_enabled:
            return
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(tags, f, indent=2)
            self.logger.debug(f"Cached tags for key: {cache_key}")
        except Exception as e:
            self.logger.warning(f"Failed to write cache file: {e}")
    
    def check_ollama_availability(self) -> bool:
        """
        Check if Ollama service is available
        
        Returns:
            bool: True if Ollama is available
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama service not available: {e}")
            return False
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        """
        Call Ollama API for inference
        
        Args:
            prompt: Prompt text
        
        Returns:
            Optional[str]: Generated response or None
        """
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            self.logger.debug(f"Calling Ollama with model: {self.model}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                self.logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("Ollama request timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error calling Ollama: {e}")
            return None
    
    def infer_flavor_tags(self, product_data: Dict) -> List[str]:
        """
        Use AI to infer flavor tags from product description
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            List[str]: Inferred flavor tags
        """
        title = product_data.get('title', '')
        description = product_data.get('description', '')
        
        if not title and not description:
            return []
        
        # Check cache first
        cache_key = self._get_cache_key(product_data)
        cached = self._get_cached_tags(cache_key)
        if cached and 'flavor_tags' in cached:
            self.logger.debug("Using cached flavor tags")
            return cached['flavor_tags']
        
        prompt = f"""Analyze this vaping product and identify the flavor profile.

Product Title: {title}
Description: {description}

Based on the product information, identify the flavor tags from these categories:
- Fruit (Citrus, Berry, Tropical, Stone Fruit)
- Dessert (Custard, Bakery, Cream, Pudding)
- Menthol (Cool, Mint, Arctic, Herbal Mint)
- Tobacco (Classic, Sweet, Blend, Dark)
- Beverage (Coffee, Soda, Cocktail, Tea)

Return only a JSON array of specific flavor tags, for example:
["Fruit", "Tropical", "Mango", "Ice", "Cool"]

JSON array:"""
        
        response = self._call_ollama(prompt)
        if not response:
            return []
        
        # Parse JSON response
        try:
            # Extract JSON array from response
            response = response.strip()
            if response.startswith('[') and response.endswith(']'):
                flavor_tags = json.loads(response)
                
                # Cache the result
                if self.cache_enabled:
                    self._save_cached_tags(cache_key, {'flavor_tags': flavor_tags})
                
                return flavor_tags
            else:
                self.logger.warning(f"Unexpected response format: {response[:100]}")
                return []
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse AI response: {e}")
            return []
    
    def infer_device_type(self, product_data: Dict) -> List[str]:
        """
        Use AI to infer device type tags
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            List[str]: Inferred device type tags
        """
        title = product_data.get('title', '')
        description = product_data.get('description', '')
        
        if not title and not description:
            return []
        
        # Check cache
        cache_key = self._get_cache_key(product_data)
        cached = self._get_cached_tags(cache_key)
        if cached and 'device_tags' in cached:
            self.logger.debug("Using cached device tags")
            return cached['device_tags']
        
        prompt = f"""Analyze this vaping product and identify the device type and form.

Product Title: {title}
Description: {description}

Device Types: Disposable, Rechargeable, Pod, Mod, AIO
Device Forms: Pen, Box Mod, Stick, Compact

Return only a JSON array of applicable tags, for example:
["Disposable", "Compact", "Pen"]

JSON array:"""
        
        response = self._call_ollama(prompt)
        if not response:
            return []
        
        try:
            response = response.strip()
            if response.startswith('[') and response.endswith(']'):
                device_tags = json.loads(response)
                
                # Update cache with device tags
                if self.cache_enabled:
                    existing_cache = self._get_cached_tags(cache_key) or {}
                    existing_cache['device_tags'] = device_tags
                    self._save_cached_tags(cache_key, existing_cache)
                
                return device_tags
            else:
                return []
        except json.JSONDecodeError:
            return []
    
    def generate_comprehensive_tags(self, product_data: Dict) -> Dict[str, List[str]]:
        """
        Generate comprehensive tag set for a product using AI
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            Dict[str, List[str]]: Dictionary of tag categories and their tags
        """
        self.logger.info(f"Generating AI tags for: {product_data.get('title', 'Unknown')}")
        
        tags = {
            'flavor_tags': self.infer_flavor_tags(product_data),
            'device_tags': self.infer_device_type(product_data)
        }
        
        return tags
