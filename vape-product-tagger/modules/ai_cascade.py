"""
AI Cascade Module
Multi-model fallback system for tag generation with confidence-based cascading
"""
import json
from typing import Dict, List, Optional
try:
    import requests
except Exception:
    requests = None


class AICascade:
    """Multi-model AI tagging system with confidence-based cascading"""
    
    def __init__(self, config, logger, ollama_processor=None):
        """
        Initialize AI cascade
        
        Args:
            config: Configuration object
            logger: Logger instance
            ollama_processor: Optional Ollama processor for primary model
        """
        self.config = config
        self.logger = logger
        self.ollama = ollama_processor
        
        # Model configuration from config
        self.primary_model = getattr(config, 'primary_ai_model', 'mistral:latest')
        self.secondary_model = getattr(config, 'secondary_ai_model', 'gpt-oss:latest')
        self.tertiary_model = getattr(config, 'tertiary_ai_model', 'llama3.1:latest')
        self.confidence_threshold = getattr(config, 'ai_confidence_threshold', 0.7)
        
        self.base_url = config.ollama_base_url
        self.timeout = config.ollama_timeout
    
    def _call_ollama_model(self, model: str, prompt: str, product_data: Dict) -> Optional[Dict]:
        """
        Call a specific Ollama model for tag generation
        
        Args:
            model: Model name to use
            prompt: Prompt to send
            product_data: Product information
        
        Returns:
            Dict with tags, confidence, reasoning or None if failed
        """
        if not requests:
            self.logger.error("requests library not available")
            return None
        
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            }
            
            self.logger.debug(f"Calling {model} for tag generation")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get('response', '')
            
            # Parse response - expecting JSON with tags, confidence, reasoning
            parsed = self._parse_ai_response(response_text)
            if parsed:
                return parsed
            
            self.logger.warning(f"Could not parse response from {model}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error calling {model}: {e}")
            return None
    
    def _parse_ai_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse AI response to extract tags, confidence, and reasoning
        
        Args:
            response_text: Raw AI response
        
        Returns:
            Dict with tags, confidence, reasoning or None if parsing failed
        """
        import re
        
        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present
            cleaned = re.sub(r'```json\s*', '', response_text)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            cleaned = cleaned.strip()
            
            # Look for JSON-like content
            if not cleaned.startswith('{'):
                json_match = re.search(r'(\{.*?\})', cleaned, re.DOTALL)
                if json_match:
                    cleaned = json_match.group(1)
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Validate structure
            if 'tags' in data and 'confidence' in data:
                return {
                    'tags': data.get('tags', []),
                    'confidence': float(data.get('confidence', 0.0)),
                    'reasoning': data.get('reasoning', '')
                }
            
        except Exception as e:
            self.logger.debug(f"JSON parsing failed: {e}")
        
        # Fallback: try to extract tags as a list
        try:
            # Look for array pattern
            array_match = re.search(r'\[([^\]]+)\]', response_text)
            if array_match:
                tags_text = array_match.group(1)
                # Split by comma and clean quotes
                tags = [t.strip().strip('"').strip("'") for t in tags_text.split(',')]
                tags = [t for t in tags if t]  # Remove empty
                
                return {
                    'tags': tags,
                    'confidence': 0.5,  # Default medium confidence for fallback parsing
                    'reasoning': 'Fallback parsing - could not extract confidence'
                }
        except Exception:
            pass
        
        return None
    
    def _build_tagging_prompt(self, product_data: Dict, category: str, approved_schema: Dict) -> str:
        """
        Build category-aware prompt for tag generation
        
        Args:
            product_data: Product information
            category: Detected product category
            approved_schema: Approved tags schema from approved_tags.json
        
        Returns:
            str: Formatted prompt
        """
        title = product_data.get('title', '')
        description = product_data.get('description', '')
        
        # Build category-specific context
        category_context = ""
        if category == "CBD":
            category_context = """
This is a CBD product. You MUST identify and tag all 3 dimensions:
1. CBD Strength (e.g., 1000mg, 5000mg) - range 0-50000mg
2. CBD Form (e.g., tincture, oil, gummy, capsule)
3. CBD Type (e.g., full_spectrum, broad_spectrum, isolate)
"""
        elif category in ["e-liquid", "disposable", "nicotine_pouches"]:
            category_context = """
This is a nicotine product. Important:
- Nicotine strength MUST be 0-20mg (anything >20mg is ILLEGAL and should be flagged)
- Include nicotine type if identifiable (nic_salt, freebase_nicotine, traditional_nicotine)
- For e-liquids: include VG/PG ratio if present (format: "70/30")
- Include flavor types if present
"""
        elif category in ["device", "pod_system"]:
            category_context = """
This is a vaping device. Focus on:
- Device style (pen_style, pod_style, box_style, etc.)
- Power supply (rechargeable, removable_battery)
- Vaping style if identifiable (mouth-to-lung, direct-to-lung, restricted-direct-to-lung)
"""
        
        prompt = f"""You are a vaping product tagging expert. Analyze the product and generate appropriate tags.

Product Category: {category}
{category_context}

Product Title: {title}
Product Description: {description}

Generate tags from the approved vocabulary. Return your response as JSON:
{{
    "tags": ["tag1", "tag2", "tag3"],
    "confidence": 0.85,
    "reasoning": "Brief explanation of tagging decisions"
}}

Confidence scoring guide (vary your scores to prevent bias):
- 0.95: Perfect information, all details clear
- 0.85: Good information, minor ambiguity
- 0.75: Adequate information, some guesswork
- 0.65: Limited information, significant guesswork
- 0.50: Minimal information, mostly assumptions

Only use tags from the approved schema. Be conservative with confidence scores.
"""
        return prompt
    
    def generate_tags_with_cascade(
        self, 
        product_data: Dict, 
        category: str,
        approved_schema: Dict
    ) -> Dict:
        """
        Generate tags with multi-model cascade fallback
        
        Attempts primary → secondary → tertiary models based on confidence threshold
        
        Args:
            product_data: Product information
            category: Detected product category
            approved_schema: Approved tags schema
        
        Returns:
            Dict with keys: tags, confidence, model_used, needs_manual_review, reasoning
        """
        self.logger.info(f"Starting AI cascade for product: {product_data.get('title', 'Unknown')}")
        
        # Build prompt
        prompt = self._build_tagging_prompt(product_data, category, approved_schema)
        
        # Try primary model
        result = self._call_ollama_model(self.primary_model, prompt, product_data)
        if result and result['confidence'] >= self.confidence_threshold:
            self.logger.info(f"Primary model {self.primary_model} succeeded with confidence {result['confidence']:.2f}")
            return {
                'tags': result['tags'],
                'confidence': result['confidence'],
                'model_used': self.primary_model,
                'needs_manual_review': False,
                'reasoning': result.get('reasoning', '')
            }
        
        # Primary failed or low confidence - try secondary
        self.logger.warning(f"Primary model failed or low confidence, trying secondary: {self.secondary_model}")
        result = self._call_ollama_model(self.secondary_model, prompt, product_data)
        if result and result['confidence'] >= self.confidence_threshold:
            self.logger.info(f"Secondary model {self.secondary_model} succeeded with confidence {result['confidence']:.2f}")
            return {
                'tags': result['tags'],
                'confidence': result['confidence'],
                'model_used': self.secondary_model,
                'needs_manual_review': False,
                'reasoning': result.get('reasoning', '')
            }
        
        # Secondary failed - try tertiary
        self.logger.warning(f"Secondary model failed or low confidence, trying tertiary: {self.tertiary_model}")
        result = self._call_ollama_model(self.tertiary_model, prompt, product_data)
        if result:
            needs_review = result['confidence'] < self.confidence_threshold
            self.logger.info(f"Tertiary model {self.tertiary_model} returned confidence {result['confidence']:.2f}, needs_review={needs_review}")
            return {
                'tags': result['tags'],
                'confidence': result['confidence'],
                'model_used': self.tertiary_model,
                'needs_manual_review': needs_review,
                'reasoning': result.get('reasoning', '')
            }
        
        # All models failed
        self.logger.error("All AI models failed to generate tags")
        return {
            'tags': [],
            'confidence': 0.0,
            'model_used': 'none',
            'needs_manual_review': True,
            'reasoning': 'All AI models failed to generate tags'
        }
