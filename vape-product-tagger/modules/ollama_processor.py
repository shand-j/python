"""
Ollama AI Integration Module
Handles semantic analysis and tag generation using Ollama
"""
import json
import requests
import re
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
                "stream": False
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

Return ONLY a valid JSON array of strings, no markdown formatting, no explanations.
Example format: ["Fruit", "Tropical", "Mango", "Ice", "Cool"]

Tags:"""
        
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
                
                # Cache the result
                if self.cache_enabled:
                    self._save_cached_tags(cache_key, {'flavor_tags': valid_tags})
                
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
        
        # Check cache
        cache_key = self._get_cache_key(product_data)
        cached = self._get_cached_tags(cache_key)
        if cached and 'device_tags' in cached:
            self.logger.debug("Using cached device tags")
            return cached['device_tags']
        
        prompt = f"""Analyze this vaping product and identify the device type, form factor, and usage level.

Product Title: {title}
Description: {description}

Device Types: Disposable, Pod System, Box Mod, Pen Style, AIO (All-in-One), Mechanical Mod
Form Factors: Compact, Pen, Box, Tube, Stick, Mini
Usage Levels: Beginner, Intermediate, Advanced, Professional
Power Types: Internal Battery, Removable Battery, USB Rechargeable, Non-Rechargeable
Features: Variable Wattage, Temperature Control, Sub-Ohm, MTL (Mouth-to-Lung), DTL (Direct-to-Lung)

Return ONLY a valid JSON array of strings, no markdown formatting, no explanations.
Example format: ["Pod System", "Compact", "Beginner", "USB Rechargeable", "MTL"]

Tags:"""
        
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
                
                # Update cache with device tags
                if self.cache_enabled:
                    existing_cache = self._get_cached_tags(cache_key) or {}
                    existing_cache['device_tags'] = valid_tags
                    self._save_cached_tags(cache_key, existing_cache)
                
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
        
        # Check cache
        cache_key = self._get_cache_key(product_data)
        cached = self._get_cached_tags(cache_key)
        if cached and 'category_tags' in cached:
            self.logger.debug("Using cached category tags")
            return cached['category_tags']
        
        prompt = f"""Analyze this vaping product and identify the main product category for e-commerce menu navigation.

Product Title: {title}
Description: {description}

Primary Categories:
- E-Liquid (bottled vape juice, shortfills, nicotine salts)
- Devices (mods, pod systems, disposables, starter kits)
- Accessories (chargers, cases, tools, stands, drip tips)
- Consumables (coils, pods, cartridges, atomizers)

Sub-Categories for E-Liquid:
- Shortfill, Longfill, Nic Salt, Freebase, TPD Compliant

Sub-Categories for Devices:
- Starter Kit, Advanced Kit, Pod System, Disposable, Mod Only

Sub-Categories for Consumables:
- Replacement Coil, Replacement Pod, Prefilled Pod, Cartridge

Return ONLY a valid JSON array of strings, no markdown formatting, no explanations.
Example format: ["E-Liquid", "Shortfill", "TPD Compliant"]

Tags:"""
        
        response = self._call_ollama(prompt)
        if not response:
            return []
        
        try:
            cleaned_response = self._clean_json_response(response)
            category_tags = json.loads(cleaned_response)
            
            if isinstance(category_tags, list):
                valid_tags = [tag.strip() for tag in category_tags if isinstance(tag, str) and tag.strip()]
                
                # Update cache
                if self.cache_enabled:
                    existing_cache = self._get_cached_tags(cache_key) or {}
                    existing_cache['category_tags'] = valid_tags
                    self._save_cached_tags(cache_key, existing_cache)
                
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
        
        # Check cache
        cache_key = self._get_cache_key(product_data)
        cached = self._get_cached_tags(cache_key)
        if cached and 'compatibility_tags' in cached:
            self.logger.debug("Using cached compatibility tags")
            return cached['compatibility_tags']
        
        prompt = f"""Analyze this vaping product and identify brand, device range, and cross-compatibility specifications.

Product Title: {title}
Description: {description}

IMPORTANT: Identify specific device compatibility and ranges:

Brand & Device Ranges:
- SMOK: Nord, RPM, TFV, Novo, Infinix, Stick, Morph, G-Priv
- Aspire: Nautilus, Cleito, Atlantis, PockeX, Breeze, K-Lite
- Vaporesso: XROS, Target, Gen, Luxe, Sky Solo, GTX, NRG
- GeekVape: Aegis, Zeus, Cerberus, Flint, Wenax, H45
- Uwell: Caliburn, Crown, Nunchaku, Whirl, Valyrian
- Voopoo: Drag, Vinci, Doric, Argus, PnP
- Innokin: Zlide, T18, T20S, Endura, Adept, Go S

Cross-Compatibility Identification:
- Coil Series (e.g., "GTX Coils", "PnP Coils", "Nord Coils")
- Pod Compatibility (e.g., "XROS Pods", "Caliburn Pods")
- Tank Series (e.g., "TFV16", "Crown 5", "Zeus Tank")
- Universal Standards ("510 Thread", "Magnetic Connection")

Technical Specifications:
- Battery: mAh capacity, removable/internal
- Capacity: ml for tanks/pods
- Resistance: ohm ranges for coils
- Connection: USB-C, Type-C, Micro-USB
- Power: Wattage range, voltage output

E-liquid Specs (if applicable):
- Nicotine: 0mg, 3mg, 6mg, 12mg, 18mg, 20mg
- VG/PG: 50/50, 70/30, Max VG, High VG
- Size: 10ml, 30ml, 50ml, 100ml, 120ml

Return ONLY a valid JSON array of strings focusing on specific compatibility.
Example format: ["SMOK", "Nord Series", "Nord Coils", "RPM Coils", "510 Thread", "2000mAh", "USB-C"]

Tags:"""
        
        response = self._call_ollama(prompt)
        if not response:
            return []
        
        try:
            cleaned_response = self._clean_json_response(response)
            compatibility_tags = json.loads(cleaned_response)
            
            if isinstance(compatibility_tags, list):
                valid_tags = [tag.strip() for tag in compatibility_tags if isinstance(tag, str) and tag.strip()]
                
                # Update cache
                if self.cache_enabled:
                    existing_cache = self._get_cached_tags(cache_key) or {}
                    existing_cache['compatibility_tags'] = valid_tags
                    self._save_cached_tags(cache_key, existing_cache)
                
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
        
        # Check cache
        cache_key = self._get_cache_key(product_data)
        cached = self._get_cached_tags(cache_key)
        if cached and 'cross_compatibility_tags' in cached:
            self.logger.debug("Using cached cross-compatibility tags")
            return cached['cross_compatibility_tags']
        
        prompt = f"""Analyze this vaping product and identify what OTHER products it's compatible with for cross-selling.

Product Title: {title}
Description: {description}

If this is a COIL/ATOMIZER, identify compatible:
- Tank models, Pod systems, Devices that use these coils
- Example: "TFV16 Coils" → compatible with "TFV16 Tank", "SMOK Morph", "SMOK G-Priv 3"

If this is a POD/CARTRIDGE, identify compatible:
- Device models that use these pods
- Example: "XROS Pods" → compatible with "XROS", "XROS 2", "XROS Mini"

If this is a DEVICE/KIT, identify compatible:
- Coil series, Pod types, Tanks that work with this device
- Example: "SMOK Nord 4" → compatible with "Nord Coils", "RPM Coils", "Nord Pods"

If this is a TANK, identify compatible:
- Coil series, Device compatibility (510 thread devices)
- Example: "TFV16 Tank" → compatible with "TFV16 Coils", "510 Thread Devices"

Focus on SPECIFIC model compatibility for cross-selling opportunities.

Return ONLY a valid JSON array of compatible product names/series.
Example format: ["TFV16 Tank", "SMOK Morph 219", "SMOK G-Priv 3", "TFV16 Mesh Coils"]

Tags:"""
        
        response = self._call_ollama(prompt)
        if not response:
            return []
        
        try:
            cleaned_response = self._clean_json_response(response)
            cross_compatibility_tags = json.loads(cleaned_response)
            
            if isinstance(cross_compatibility_tags, list):
                valid_tags = [tag.strip() for tag in cross_compatibility_tags if isinstance(tag, str) and tag.strip()]
                
                # Update cache
                if self.cache_enabled:
                    existing_cache = self._get_cached_tags(cache_key) or {}
                    existing_cache['cross_compatibility_tags'] = valid_tags
                    self._save_cached_tags(cache_key, existing_cache)
                
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
        
        tags = {
            'category_tags': self.infer_product_category(product_data),
            'flavor_tags': self.infer_flavor_tags(product_data),
            'device_tags': self.infer_device_type(product_data),
            'compatibility_tags': self.infer_compatibility_tags(product_data),
            'cross_compatibility_tags': self.infer_cross_compatibility(product_data)
        }
        
        return tags
