"""
Third Opinion Recovery Module
AI-powered recovery for failed tag validation with category-specific prompts
"""
import json
from typing import Dict, List, Optional
try:
    import requests
except Exception:
    requests = None


class ThirdOpinionRecovery:
    """Third opinion AI recovery for failed tag validation"""
    
    def __init__(self, config, logger):
        """
        Initialize third opinion recovery
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.base_url = config.ollama_base_url
        self.timeout = config.ollama_timeout
        
        # Use tertiary model for third opinion (different from cascade models)
        self.recovery_model = getattr(config, 'tertiary_ai_model', 'llama3.1:latest')
        self.enabled = getattr(config, 'enable_third_opinion', True)
    
    def _build_recovery_prompt(
        self,
        product_data: Dict,
        suggested_ai_tags: List[str],
        suggested_rule_tags: List[str],
        failure_reasons: List[str],
        approved_schema: Dict,
        category: str
    ) -> str:
        """
        Build category-specific recovery prompt
        
        Args:
            product_data: Product information
            suggested_ai_tags: Tags suggested by AI cascade
            suggested_rule_tags: Tags from rule-based system
            failure_reasons: List of validation failures
            approved_schema: Approved tags schema
            category: Product category
        
        Returns:
            str: Recovery prompt
        """
        title = product_data.get('title', '')
        description = product_data.get('description', '')
        
        # Category-specific guidance
        category_guidance = ""
        
        if category == "CBD":
            category_guidance = """
CBD PRODUCT REQUIREMENTS:
You MUST provide all 3 dimensions for CBD products:
1. CBD Strength: Extract mg value (0-50000mg) - format as "1000mg", "5000mg", etc.
2. CBD Form: One of [tincture, oil, gummy, capsule, topical, patch, paste, shot, isolate, edible, beverage]
3. CBD Type: One of [full_spectrum, broad_spectrum, isolate, cbg, cbda]

Example valid CBD tags: ["1000mg", "tincture", "full_spectrum"]
CRITICAL: All 3 dimensions are mandatory for CBD products.
"""
        elif category in ["e-liquid", "disposable", "nicotine_pouches"]:
            category_guidance = f"""
NICOTINE PRODUCT REQUIREMENTS:
- Nicotine strength: 0-20mg ONLY (anything >20mg is ILLEGAL)
  Format: "0mg", "3mg", "6mg", "12mg", "18mg", "20mg"
- Nicotine type (if identifiable): nic_salt, freebase_nicotine, traditional_nicotine, pouch
- Flavor type (for {category}): fruity, ice, tobacco, desserts/bakery, beverages, nuts, spices_&_herbs, cereal, unflavoured
- VG/PG ratio (for e-liquid): format "70/30", "50/50", etc.
- Bottle size (for e-liquid): 5ml, 10ml, 20ml, 30ml, 50ml, 100ml, shortfill

CRITICAL: Never suggest nicotine >20mg. If product shows >20mg, use "0mg" and flag for review.
"""
        elif category in ["device", "pod_system"]:
            category_guidance = """
DEVICE PRODUCT REQUIREMENTS:
- Device style: pen_style, pod_style, box_style, stick_style, compact, mini
- Power supply: rechargeable, removable_battery
- Vaping style: mouth-to-lung, direct-to-lung, restricted-direct-to-lung
- Capacity (for tanks/pods): 2ml, 2.5ml, 3ml, 4ml, 5ml, 6ml, 7ml, 8ml, 9ml, 10ml

Only tag dimensions that are clearly identifiable from the product information.
"""
        elif category == "pod":
            category_guidance = """
POD PRODUCT REQUIREMENTS:
- Pod type: prefilled_pod OR replacement_pod (choose one)
- Capacity: 2ml, 2.5ml, 3ml, 4ml, 5ml, 6ml, 7ml, 8ml, 9ml, 10ml
- If prefilled: include flavor_type and nicotine info
- VG/PG ratio (if applicable): format "70/30", "50/50", etc.
"""
        
        # Build failure context
        failure_context = ""
        if failure_reasons:
            failure_context = f"""
VALIDATION FAILURES TO FIX:
{chr(10).join(f"- {reason}" for reason in failure_reasons)}

These failures indicate the suggested tags violate schema rules. Your job is to correct them.
"""
        
        # Build suggested tags context
        suggested_context = ""
        if suggested_ai_tags or suggested_rule_tags:
            suggested_context = f"""
PREVIOUSLY SUGGESTED TAGS (failed validation):
- AI suggested: {suggested_ai_tags}
- Rule-based: {suggested_rule_tags}

These tags had issues. Generate corrected tags that pass validation.
"""
        
        prompt = f"""You are a product tagging expert performing RECOVERY VALIDATION.

Previous tagging attempts failed validation. Your task is to analyze the product and generate CORRECT tags that will pass validation.

Product Category: {category}
Product Title: {title}
Product Description: {description}

{category_guidance}

{suggested_context}

{failure_context}

IMPORTANT RULES:
1. Only use tags from the approved schema
2. Respect applies_to rules (each tag dimension has allowed categories)
3. For CBD: ALL 3 dimensions are mandatory
4. For nicotine: NEVER exceed 20mg (illegal)
5. Be conservative - only tag what you can clearly identify

Return JSON response:
{{
    "tags": ["tag1", "tag2", "tag3"],
    "confidence": 0.75,
    "reasoning": "Explanation of corrections made and why"
}}

Confidence should be lower than initial attempts since this is recovery (suggest 0.6-0.8 range).
This is a RECOVERY attempt - manual review will be required regardless.
"""
        return prompt
    
    def _call_recovery_model(self, prompt: str) -> Optional[Dict]:
        """
        Call recovery model with prompt
        
        Args:
            prompt: Recovery prompt
        
        Returns:
            Dict with tags, confidence, reasoning or None
        """
        if not requests:
            self.logger.error("requests library not available")
            return None
        
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.recovery_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.5,  # Slightly higher for creative recovery
                    "top_p": 0.9
                }
            }
            
            self.logger.debug(f"Calling recovery model {self.recovery_model}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get('response', '')
            
            # Parse response
            parsed = self._parse_recovery_response(response_text)
            return parsed
            
        except Exception as e:
            self.logger.error(f"Error calling recovery model: {e}")
            return None
    
    def _parse_recovery_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse recovery model response
        
        Args:
            response_text: Raw response
        
        Returns:
            Dict with tags, confidence, reasoning or None
        """
        import re
        
        try:
            # Remove markdown code blocks
            cleaned = re.sub(r'```json\s*', '', response_text)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            cleaned = cleaned.strip()
            
            # Extract JSON
            if not cleaned.startswith('{'):
                json_match = re.search(r'(\{.*?\})', cleaned, re.DOTALL)
                if json_match:
                    cleaned = json_match.group(1)
            
            # Parse JSON
            data = json.loads(cleaned)
            
            if 'tags' in data and 'confidence' in data:
                return {
                    'tags': data.get('tags', []),
                    'confidence': float(data.get('confidence', 0.0)),
                    'reasoning': data.get('reasoning', '')
                }
        except Exception as e:
            self.logger.debug(f"Recovery response parsing failed: {e}")
        
        return None
    
    def attempt_recovery(
        self,
        product_data: Dict,
        suggested_ai_tags: List[str],
        suggested_rule_tags: List[str],
        failure_reasons: List[str],
        approved_schema: Dict,
        category: str
    ) -> Optional[Dict]:
        """
        Attempt third opinion recovery for failed validation
        
        Args:
            product_data: Product information
            suggested_ai_tags: Tags from AI cascade (failed validation)
            suggested_rule_tags: Tags from rule-based system
            failure_reasons: List of validation failures
            approved_schema: Approved tags schema
            category: Product category
        
        Returns:
            Dict with tags, confidence, needs_manual_review=True or None if failed
        """
        if not self.enabled:
            self.logger.debug("Third opinion recovery disabled")
            return None
        
        self.logger.info("Attempting third opinion recovery")
        
        # Build recovery prompt
        prompt = self._build_recovery_prompt(
            product_data,
            suggested_ai_tags,
            suggested_rule_tags,
            failure_reasons,
            approved_schema,
            category
        )
        
        # Call recovery model
        result = self._call_recovery_model(prompt)
        
        if result:
            self.logger.info(f"Third opinion recovery returned {len(result['tags'])} tags with confidence {result['confidence']:.2f}")
            
            # Always flag for manual review since this is recovery
            return {
                'tags': result['tags'],
                'confidence': result['confidence'],
                'needs_manual_review': True,  # Always true for recovery
                'reasoning': result.get('reasoning', '')
            }
        else:
            self.logger.warning("Third opinion recovery failed")
            return None
