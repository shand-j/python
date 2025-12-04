"""
Ollama AI Integration Module
Handles semantic analysis and tag generation using Ollama
"""
import json
try:
    import requests
except Exception:
    requests = None
import re
from typing import Dict, List, Optional
import hashlib
from pathlib import Path
from .unified_cache import UnifiedCache


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
        
        # Initialize unified cache system
        if self.cache_enabled:
            cache_file = config.cache_dir / "vape_tags.db"
            config.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache = UnifiedCache(cache_file, logger)
        else:
            self.cache = None
    
    def _get_cached_tags(self, product_data: Dict) -> Optional[Dict]:
        """
        Retrieve cached tags if available
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            Optional[Dict]: Cached tags or None
        """
        if not self.cache_enabled or not self.cache:
            return None
        
        return self.cache.get_cached_tags(product_data)
    
    def _save_cached_tags(self, product_data: Dict, ai_tags: List[str], rule_tags: List[str]):
        """
        Save tags to unified cache
        
        Args:
            product_data: Product information dictionary
            ai_tags: AI-generated tags
            rule_tags: Rule-based tags
        """
        if not self.cache_enabled or not self.cache:
            return
        
        self.cache.save_tags(product_data, ai_tags, rule_tags)
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Clean and extract JSON from AI response that might be wrapped in markdown
        
        Args:
            response_text: Raw response from AI model
            
        Returns:
            Cleaned JSON string ready for parsing
        """
        if not response_text:
            return "[]"
            
        # Remove markdown code blocks if present
        cleaned = re.sub(r'```json\s*', '', response_text)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        
        # Remove any leading/trailing whitespace
        cleaned = cleaned.strip()
        
        # If it doesn't look like JSON, try to extract it
        if not cleaned.startswith('[') and not cleaned.startswith('{'):
            # Look for JSON-like content
            json_match = re.search(r'(\[.*?\]|\{.*?\})', cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(1)
            else:
                self.logger.warning(f"Could not extract JSON from response: {response_text}")
                return "[]"
        
        return cleaned
    
    def check_ollama_availability(self) -> bool:
        """
        Check if Ollama service is available and test with a simple prompt
        
        Returns:
            bool: True if Ollama is available and responsive
        """
        try:
            # First check if service is up
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                self.logger.error(f"Ollama service returned status: {response.status_code}")
                return False
            
            # Test with a simple prompt to ensure model is working
            self.logger.info("Testing Ollama connectivity with simple prompt...")
            test_response = self._call_ollama("Return just: OK")
            
            if test_response and "OK" in test_response.upper():
                self.logger.info("Ollama test successful")
                return True
            else:
                self.logger.warning(f"Ollama test failed. Response: {test_response}")
                return True  # Still allow processing, might work for real prompts
                
        except Exception as e:
            self.logger.error(f"Ollama service not available: {e}")
            return False
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        """
        Call Ollama API for inference with improved logging and timeout handling
        
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
                "stream": False,
                "options": {
                    "num_predict": 500,     # High limit to account for model's thinking process + response
                    "temperature": 0.1,     # Lower temperature for consistent responses
                    "top_p": 0.9,          # Focus on most likely tokens
                    "repeat_penalty": 1.1,  # Reduce repetition
                    "stream": False         # Ensure we get complete responses
                }
            }
            
            self.logger.info(f"Calling Ollama API with model: {self.model} (timeout: {self.timeout}s)")
            self.logger.debug(f"Prompt length: {len(prompt)} characters")
            
            # Make the API call with progress logging
            response = requests.post(url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                self.logger.info(f"Ollama response received (length: {len(response_text)} chars)")
                
                # Debug logging for empty responses
                if not response_text:
                    self.logger.warning(f"Empty response from Ollama. Full result: {result}")
                    # Check if there's an error in the response
                    if 'error' in result:
                        self.logger.error(f"Ollama error: {result['error']}")
                
                return response_text
            else:
                self.logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error(f"Ollama request timed out after {self.timeout} seconds")
            return None
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error to Ollama: {e}")
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
        cached = self._get_cached_tags(product_data)
        if cached and 'ai_tags' in cached:
            # Look for flavor tags in cached AI tags
            ai_tags = cached['ai_tags']
            flavor_tags = [tag for tag in ai_tags if any(flavor in tag.lower() for flavor in ['fruit', 'dessert', 'menthol', 'tobacco', 'beverage'])]
            if flavor_tags:
                self.logger.debug("Using cached flavor tags")
                return flavor_tags
        
        prompt = f"""Product: {title}

Identify flavors from: Fruit, Dessert, Menthol, Tobacco, Beverage

CRITICAL: Output ONLY a JSON array, no other text or formatting.
Example: ["Dessert", "Beverage"]

JSON:"""
        
        response = self._call_ollama(prompt)
        if not response:
            return []
        
        # Parse JSON response with improved cleaning
        try:
            # Clean the response to handle markdown-wrapped JSON
            cleaned_response = self._clean_json_response(response)
            
            # Parse cleaned JSON
            flavor_tags = json.loads(cleaned_response)
            
            # Validate that we got a list
            if isinstance(flavor_tags, list):
                # Filter and clean tags
                valid_tags = [tag.strip() for tag in flavor_tags if isinstance(tag, str) and tag.strip()]
                
                # Note: Tags will be cached at the product level by main processor
                
                return valid_tags
            else:
                self.logger.warning(f"Expected list, got {type(flavor_tags)}: {flavor_tags}")
                return []
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse AI response: {response[:100]}... Error: {e}")
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
        
        # Check cache first (handled at comprehensive level)
        cached = self._get_cached_tags(product_data)
        if cached:
            return []  # Will be handled by comprehensive cache
        
        prompt = f"""Product: {title}

Device types: Disposable, Pod System, Box Mod, Pen Style, AIO
Forms: Compact, Pen, Box, Tube, Stick
Levels: Beginner, Intermediate, Advanced

CRITICAL: Output ONLY a JSON array, no other text.
Example: ["Pod System", "Compact"]

JSON:"""
        
        response = self._call_ollama(prompt)
        if not response:
            return []
        
        try:
            # Clean the response to handle markdown-wrapped JSON
            cleaned_response = self._clean_json_response(response)
            
            # Parse cleaned JSON
            device_tags = json.loads(cleaned_response)
            
            # Validate that we got a list
            if isinstance(device_tags, list):
                # Filter and clean tags
                valid_tags = [tag.strip() for tag in device_tags if isinstance(tag, str) and tag.strip()]
                
                # Note: Tags will be cached at the comprehensive level
                
                return valid_tags
            else:
                self.logger.warning(f"Expected list for device tags, got {type(device_tags)}: {device_tags}")
                return []
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse device tags from AI response: {response[:100]}... Error: {e}")
            return []
    
    def infer_product_category(self, product_data: Dict) -> List[str]:
        """
        Use AI to infer main product category for e-commerce navigation
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            List[str]: Inferred product category tags
        """
        title = product_data.get('title', '')
        description = product_data.get('description', '')
        
        if not title and not description:
            return []
        
        # Check cache first (handled at comprehensive level)
        cached = self._get_cached_tags(product_data)
        if cached:
            return []  # Will be handled by comprehensive cache
        
        prompt = f"""Product: {title}

Categories: E-Liquid, Devices, Accessories, Consumables
Sub-types: Shortfill, Pod System, Replacement Coil, etc.

CRITICAL: Output ONLY a JSON array, no other text.
Example: ["E-Liquid", "Shortfill"]

JSON:"""
        
        response = self._call_ollama(prompt)
        if not response:
            return []
        
        try:
            cleaned_response = self._clean_json_response(response)
            category_tags = json.loads(cleaned_response)
            
            if isinstance(category_tags, list):
                valid_tags = [tag.strip() for tag in category_tags if isinstance(tag, str) and tag.strip()]
                
                # Note: Tags will be cached at the comprehensive level
                
                return valid_tags
            else:
                self.logger.warning(f"Expected list for category tags, got {type(category_tags)}: {category_tags}")
                return []
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse category tags from AI response: {response[:100]}... Error: {e}")
            return []
    
    def infer_compatibility_tags(self, product_data: Dict) -> List[str]:
        """
        Use AI to infer compatibility and technical specification tags with device range identification
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            List[str]: Inferred compatibility and spec tags including device range compatibility
        """
        title = product_data.get('title', '')
        description = product_data.get('description', '')
        
        if not title and not description:
            return []
        
        # Check cache first (handled at comprehensive level)
        cached = self._get_cached_tags(product_data)
        if cached:
            return []  # Will be handled by comprehensive cache
        
        prompt = f"""Find compatibility for vape product: {title}

Identify: Brand, device series, coil type, battery, capacity, connection.
Brands: SMOK, Aspire, Vaporesso, GeekVape, Uwell, Voopoo, Innokin
Series: Nord, RPM, XROS, Caliburn, Drag, Aegis, GTX, PnP, TFV

CRITICAL: Output ONLY a JSON array, no other text.
Example: ["Brand", "Series", "Specs"]

JSON:"""
        
        response = self._call_ollama(prompt)
        if not response:
            return []
        
        try:
            cleaned_response = self._clean_json_response(response)
            compatibility_tags = json.loads(cleaned_response)
            
            if isinstance(compatibility_tags, list):
                valid_tags = [tag.strip() for tag in compatibility_tags if isinstance(tag, str) and tag.strip()]
                
                # Note: Tags will be cached at the comprehensive level
                
                return valid_tags
            else:
                self.logger.warning(f"Expected list for compatibility tags, got {type(compatibility_tags)}: {compatibility_tags}")
                return []
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse compatibility tags from AI response: {response[:100]}... Error: {e}")
            return []
    
    def infer_cross_compatibility(self, product_data: Dict) -> List[str]:
        """
        Use AI to identify what other products this item is compatible with for cross-selling
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            List[str]: Cross-compatibility tags for related product recommendations
        """
        title = product_data.get('title', '')
        description = product_data.get('description', '')
        
        if not title and not description:
            return []
        
        # Check cache first (handled at comprehensive level)
        cached = self._get_cached_tags(product_data)
        if cached:
            return []  # Will be handled by comprehensive cache
        
        prompt = f"""Find compatible products for: {title}

Coils → tanks/devices that use them
Pods → devices that use them  
Devices → coils/pods/tanks that work with them
Tanks → coils that fit them

CRITICAL: Output ONLY a JSON array, no other text.
Example: ["Compatible Product 1", "Compatible Product 2"]

JSON:"""
        
        response = self._call_ollama(prompt)
        if not response:
            return []
        
        try:
            cleaned_response = self._clean_json_response(response)
            cross_compatibility_tags = json.loads(cleaned_response)
            
            if isinstance(cross_compatibility_tags, list):
                valid_tags = [tag.strip() for tag in cross_compatibility_tags if isinstance(tag, str) and tag.strip()]
                
                # Note: Tags will be cached at the comprehensive level
                
                return valid_tags
            else:
                self.logger.warning(f"Expected list for cross-compatibility tags, got {type(cross_compatibility_tags)}: {cross_compatibility_tags}")
                return []
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse cross-compatibility tags from AI response: {response[:100]}... Error: {e}")
            return []

    def generate_comprehensive_tags(self, product_data: Dict) -> Dict[str, List[str]]:
        """
        Generate comprehensive tag set for a product using AI - Enhanced for E-commerce with Cross-Compatibility
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            Dict[str, List[str]]: Dictionary of tag categories and their tags
        """
        self.logger.info(f"Generating AI tags for: {product_data.get('title', 'Unknown')}")
        
        # Check unified cache first
        cached = self._get_cached_tags(product_data)
        if cached and 'ai_tags' in cached:
            self.logger.debug("Using cached AI tags")
            # Convert flat list back to categorized format
            ai_tags = cached['ai_tags']
            return {
                'category_tags': [tag for tag in ai_tags if any(cat in tag.lower() for cat in ['disposable', 'rechargeable', 'pod', 'cartridge'])],
                'flavor_tags': [tag for tag in ai_tags if any(flavor in tag.lower() for flavor in ['fruit', 'dessert', 'menthol', 'tobacco', 'beverage', 'ice', 'cream', 'vanilla', 'chocolate'])],
                'device_tags': [tag for tag in ai_tags if any(device in tag.lower() for device in ['pen', 'stick', 'pod', 'mod', 'tank'])],
                'compatibility_tags': [tag for tag in ai_tags if any(comp in tag.lower() for comp in ['510', 'threading', 'magnetic'])],
                'cross_compatibility_tags': [tag for tag in ai_tags if any(cross in tag.lower() for cross in ['universal', 'compatible', 'interchangeable'])]
            }
        
        # Generate new tags if not cached
        tags = {
            'category_tags': self.infer_product_category(product_data),
            'flavor_tags': self.infer_flavor_tags(product_data),
            'device_tags': self.infer_device_type(product_data),
            'compatibility_tags': self.infer_compatibility_tags(product_data),
            'cross_compatibility_tags': self.infer_cross_compatibility(product_data)
        }
        
        # Save to unified cache (flatten all AI tags)
        if self.cache_enabled and self.cache:
            all_ai_tags = []
            for category_tags in tags.values():
                all_ai_tags.extend(category_tags)
            
            # Save to unified cache (rule tags empty since this is AI-only)
            self._save_cached_tags(product_data, all_ai_tags, [])
        
        return tags
