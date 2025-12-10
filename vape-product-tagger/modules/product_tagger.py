"""
Product Tagging Engine Module
Core logic for intelligent vaping product tagging
"""
import re
from typing import Dict, List, Set, Tuple, Optional
from .taxonomy import VapeTaxonomy
from .ai_cascade import AICascade
from .tag_validator import TagValidator
from .third_opinion import ThirdOpinionRecovery


class ProductTagger:
    """Intelligent product tagging engine with rule-based and AI-powered capabilities"""
    
    def __init__(self, config, logger, ollama_processor=None):
        """
        Initialize product tagger
        
        Args:
            config: Configuration object
            logger: Logger instance
            ollama_processor: Optional Ollama AI processor
        """
        self.config = config
        self.logger = logger
        self.ollama = ollama_processor
        self.taxonomy = VapeTaxonomy()
        
        # Access unified cache through ollama processor
        self.cache = ollama_processor.cache if ollama_processor and hasattr(ollama_processor, 'cache') else None
        
        # Initialize new components
        from pathlib import Path
        schema_path = Path(__file__).parent.parent / "approved_tags.json"
        self.tag_validator = TagValidator(schema_path, logger)
        self.ai_cascade = AICascade(config, logger, ollama_processor) if ollama_processor else None
        self.third_opinion = ThirdOpinionRecovery(config, logger)
    
    def _extract_nicotine_value(self, text: str, category: str = None) -> float:
        """
        Extract nicotine value from text
        
        Args:
            text: Text to search
            category: Product category (CBD products have 0mg by default)
        
        Returns:
            float: Nicotine value in mg or 0 if not found
        """
        if not text:
            return 0.0
        
        # CBD products are always 0mg nicotine
        if category == "CBD":
            return 0.0
        
        text = text.lower()
        
        # Check for zero nicotine keywords
        if any(keyword in text for keyword in ['0mg', 'zero nicotine', 'no nicotine', 'nicotine free']):
            return 0.0
        
        # Pattern to find nicotine values like "20mg", "3.5mg", etc.
        patterns = [
            r'(\d+\.?\d*)\s*mg',
            r'(\d+\.?\d*)\s*%',
            r'nicotine:\s*(\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    # Validate max 20mg for nicotine
                    if value > 20:
                        self.logger.warning(f"Illegal nicotine value {value}mg detected (max 20mg)")
                        return 0.0
                    return value
                except ValueError:
                    continue
        
        return 0.0
    
    def _match_keywords(self, text: str, keywords: List[str]) -> bool:
        """
        Check if any keywords match in text
        
        Args:
            text: Text to search
            keywords: List of keywords
        
        Returns:
            bool: True if any keyword matches
        """
        if not text:
            return False

        text = text.lower()

        # Build a safe regex for each keyword to match word boundaries and some punctuation
        for keyword in keywords:
            if not keyword:
                continue
            k = keyword.lower().strip()

            # Escape regex metacharacters but allow loose matching for punctuation/spacing
            escaped = re.escape(k)

            # Support keywords that contain spaces (phrase match) and simple plurals
            # Match as whole word or phrase using word boundaries on ends
            pattern = r"(?<!\w)" + escaped + r"(?!\w)"

            try:
                if re.search(pattern, text):
                    return True
                # Also try a plural form if single word and not ending with s
                if ' ' not in k and not k.endswith('s'):
                    plural_pat = r"(?<!\w)" + re.escape(k + 's') + r"(?!\w)"
                    if re.search(plural_pat, text):
                        return True
            except re.error:
                # Fallback to safe substring search if regex fails for some reason
                if k in text:
                    return True

        return False
    
    def _extract_cbd_value(self, text: str) -> float:
        """
        Extract CBD strength value from text
        
        Args:
            text: Text to search
        
        Returns:
            float: CBD value in mg or 0 if not found
        """
        if not text:
            return 0.0
        
        text = text.lower()
        
        # Pattern to find CBD values like "1000mg", "5000mg", etc.
        patterns = [
            r'(\d+\.?\d*)\s*mg\s*cbd',
            r'cbd\s*(\d+\.?\d*)\s*mg',
            r'(\d+\.?\d*)mg',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    # Validate max 50000mg for CBD
                    if value > 50000:
                        self.logger.warning(f"CBD value {value}mg exceeds max 50000mg")
                        return 0.0
                    return value
                except ValueError:
                    continue
        
        return 0.0
    
    def _extract_vg_ratio(self, text: str) -> str:
        """
        Extract VG/PG ratio from text
        
        Args:
            text: Text to search
        
        Returns:
            str: VG/PG ratio in format "70/30" or empty string if not found
        """
        if not text:
            return ""
        
        text = text.lower()
        
        # Pattern to find ratios like "70/30", "70VG/30PG", "70vg 30pg", etc.
        patterns = [
            r'(\d+)\s*vg\s*/\s*(\d+)\s*pg',
            r'(\d+)\s*/\s*(\d+)',
            r'(\d+)\s*vg\s*(\d+)\s*pg',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    vg = int(match.group(1))
                    pg = int(match.group(2))
                    
                    # VG is usually the larger number
                    if vg < pg:
                        vg, pg = pg, vg
                    
                    # Validate they sum to 100
                    if vg + pg == 100:
                        return f"{vg}/{pg}"
                except (ValueError, IndexError):
                    continue
        
        return ""
    
    def _extract_secondary_flavors(self, text: str, primary_flavor_types: List[str]) -> List[str]:
        """
        Extract secondary flavor keywords opportunistically
        
        Args:
            text: Text to search
            primary_flavor_types: Already detected primary flavor types
        
        Returns:
            List[str]: Secondary flavor keywords found
        """
        if not text:
            return []
        
        text = text.lower()
        secondary_flavors = []
        
        # For each detected primary flavor type, check for secondary keywords
        for flavor_type in primary_flavor_types:
            secondary_keywords = self.taxonomy.get_flavor_secondary_keywords(flavor_type)
            for keyword in secondary_keywords:
                if self._match_keywords(text, [keyword]):
                    secondary_flavors.append(keyword)
        
        return list(set(secondary_flavors))  # Remove duplicates
    
    def tag_category(self, product_data: Dict) -> str:
        """
        Detect product category from approved_tags.json categories
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            str: Primary category tag (or CBD for CBD products)
        """
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        # Check each category in priority order (CBD first, then others)
        # CBD products can have dual category (CBD + one other)
        detected_categories = []
        
        for category, keywords in self.taxonomy.CATEGORY_KEYWORDS.items():
            if self._match_keywords(text, keywords):
                detected_categories.append(category)
        
        # If CBD detected, return it (dual categories handled elsewhere)
        if "CBD" in detected_categories:
            return "CBD"
        
        # Return first detected category
        if detected_categories:
            return detected_categories[0]
        
        return ""
    
    def tag_device_style(self, product_data: Dict, category: str = None) -> List[str]:
        """
        Tag device style (applies_to: device, pod_system)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            List[str]: Device style tags
        """
        # Check applies_to rule
        if category and category not in ["device", "pod_system"]:
            return []
        
        tags = []
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        for style, keywords in self.taxonomy.DEVICE_STYLE_KEYWORDS.items():
            if self._match_keywords(text, keywords):
                tags.append(style)
        
        return list(set(tags))
    
    def tag_capacity(self, product_data: Dict, category: str = None) -> List[str]:
        """
        Tag capacity for tanks/pods (applies_to: tank, pod)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            List[str]: Capacity tags (e.g., ["2ml", "5ml"])
        """
        # Check applies_to rule
        if category and category not in ["tank", "pod"]:
            return []
        
        tags = []
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        # Match capacity patterns
        for capacity in self.taxonomy.CAPACITY_KEYWORDS:
            if capacity in text:
                tags.append(capacity)
        
        return list(set(tags))
    
    def tag_bottle_size(self, product_data: Dict, category: str = None) -> List[str]:
        """
        Tag bottle size for e-liquids (applies_to: e-liquid)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            List[str]: Bottle size tags
        """
        # Check applies_to rule
        if category and category != "e-liquid":
            return []
        
        tags = []
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        for size, keywords in self.taxonomy.BOTTLE_SIZE_KEYWORDS.items():
            if self._match_keywords(text, keywords):
                tags.append(size)
        
        return list(set(tags))
    
    def tag_nicotine_strength(self, product_data: Dict, category: str = None) -> Optional[str]:
        """
        Tag nicotine strength (applies_to: e-liquid, disposable, device, pod_system, nicotine_pouches)
        Returns at most ONE tag per product (range: 0-20mg)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            Optional[str]: Nicotine strength tag (e.g., "3mg", "0mg") or None
        """
        # Check applies_to rule
        if category and category not in ["e-liquid", "disposable", "device", "pod_system", "nicotine_pouches"]:
            return None
        
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        # Extract nicotine value
        nic_value = self._extract_nicotine_value(text, category)
        
        # Convert to tag using taxonomy helper
        tag = self.taxonomy.get_nicotine_strength_tag(nic_value)
        
        return tag
    
    def tag_nicotine_type(self, product_data: Dict, category: str = None) -> List[str]:
        """
        Tag nicotine type (applies_to: e-liquid, disposable, device, pod_system, nicotine_pouches)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            List[str]: Nicotine type tags
        """
        # Check applies_to rule
        if category and category not in ["e-liquid", "disposable", "device", "pod_system", "nicotine_pouches"]:
            return []
        
        tags = []
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        for nic_type, keywords in self.taxonomy.NICOTINE_TYPE_KEYWORDS.items():
            if self._match_keywords(text, keywords):
                tags.append(nic_type)
        
        return list(set(tags))
    
    def tag_vg_ratio(self, product_data: Dict, category: str = None) -> Optional[str]:
        """
        Tag VG/PG ratio (applies_to: e-liquid)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            Optional[str]: VG/PG ratio tag (e.g., "70/30") or None
        """
        # Check applies_to rule
        if category and category != "e-liquid":
            return None
        
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        ratio = self._extract_vg_ratio(text)
        return ratio if ratio else None
    
    def tag_cbd_strength(self, product_data: Dict, category: str = None) -> Optional[str]:
        """
        Tag CBD strength (applies_to: CBD)
        Returns at most ONE tag per product (range: 0-50000mg)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            Optional[str]: CBD strength tag (e.g., "1000mg") or None
        """
        # Check applies_to rule
        if category and category != "CBD":
            return None
        
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        # Extract CBD value
        cbd_value = self._extract_cbd_value(text)
        
        # Convert to tag using taxonomy helper
        tag = self.taxonomy.get_cbd_strength_tag(cbd_value)
        
        return tag
    
    def tag_cbd_form(self, product_data: Dict, category: str = None) -> List[str]:
        """
        Tag CBD form (applies_to: CBD)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            List[str]: CBD form tags
        """
        # Check applies_to rule
        if category and category != "CBD":
            return []
        
        tags = []
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        for form, keywords in self.taxonomy.CBD_FORM_KEYWORDS.items():
            if self._match_keywords(text, keywords):
                tags.append(form)
        
        return list(set(tags))
    
    def tag_cbd_type(self, product_data: Dict, category: str = None) -> List[str]:
        """
        Tag CBD type (applies_to: CBD)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            List[str]: CBD type tags
        """
        # Check applies_to rule
        if category and category != "CBD":
            return []
        
        tags = []
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        for cbd_type, keywords in self.taxonomy.CBD_TYPE_KEYWORDS.items():
            if self._match_keywords(text, keywords):
                tags.append(cbd_type)
        
        return list(set(tags))
    
    def tag_power_supply(self, product_data: Dict, category: str = None) -> List[str]:
        """
        Tag power supply (applies_to: device, pod_system)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            List[str]: Power supply tags
        """
        # Check applies_to rule
        if category and category not in ["device", "pod_system"]:
            return []
        
        tags = []
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        for supply_type, keywords in self.taxonomy.POWER_SUPPLY_KEYWORDS.items():
            if self._match_keywords(text, keywords):
                tags.append(supply_type)
        
        return list(set(tags))
    
    def tag_pod_type(self, product_data: Dict, category: str = None) -> List[str]:
        """
        Tag pod type (applies_to: pod)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            List[str]: Pod type tags
        """
        # Check applies_to rule
        if category and category != "pod":
            return []
        
        tags = []
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        for pod_type, keywords in self.taxonomy.POD_TYPE_KEYWORDS.items():
            if self._match_keywords(text, keywords):
                tags.append(pod_type)
        
        return list(set(tags))
    
    def tag_vaping_style(self, product_data: Dict, category: str = None) -> List[str]:
        """
        Tag vaping style (applies_to: device, pod_system, e-liquid)
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            List[str]: Vaping style tags
        """
        # Check applies_to rule
        if category and category not in ["device", "pod_system", "e-liquid"]:
            return []
        
        tags = []
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        for style, keywords in self.taxonomy.VAPING_STYLE_KEYWORDS.items():
            if self._match_keywords(text, keywords):
                tags.append(style)
        
        return list(set(tags))
    
    def tag_flavors(self, product_data: Dict, category: str = None) -> Tuple[List[str], List[str]]:
        """
        Tag flavors (applies_to: e-liquid, disposable, nicotine_pouches, pod)
        Returns both primary flavor types and secondary flavor keywords
        
        Args:
            product_data: Product information dictionary
            category: Product category (for validation)
        
        Returns:
            Tuple[List[str], List[str]]: (primary_flavor_types, secondary_flavors)
        """
        # Check applies_to rule
        if category and category not in ["e-liquid", "disposable", "nicotine_pouches", "pod"]:
            return [], []
        
        primary_flavors = []
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        # Check each flavor type
        for flavor_type, data in self.taxonomy.FLAVOR_KEYWORDS.items():
            primary_keywords = data.get('primary_keywords', [])
            if self._match_keywords(text, primary_keywords):
                primary_flavors.append(flavor_type)
        
        # Extract secondary flavors opportunistically
        secondary_flavors = self._extract_secondary_flavors(text, primary_flavors)
        
        return primary_flavors, secondary_flavors
    
    def tag_compliance(self, product_data: Dict, category: str = None) -> List[str]:
        """
        Generate compliance and age verification tags
        Note: This method is kept for backwards compatibility but may be disabled via config
        
        Args:
            product_data: Product information dictionary
            category: Product category
        
        Returns:
            List[str]: Compliance tags
        """
        if not self.config.enable_compliance_tags:
            return []
        
        # Compliance tags are not in approved_tags.json
        # This is optional and can be disabled
        return []
    
    def tag_product(self, product_data: Dict, use_ai: bool = True, force_third_opinion: bool = False) -> Dict:
        """
        Generate comprehensive tags for a product using new refactored pipeline
        
        Pipeline:
        1. Detect category
        2. Run all applicable rule-based tagging methods based on category
        3. Invoke AI cascade if use_ai=True
        4. Validate all tags via TagValidator
        5. Attempt ThirdOpinionRecovery if validation fails
        6. Return enhanced product with comprehensive metadata
        
        Args:
            product_data: Product information dictionary
            use_ai: Whether to use AI enhancement
            force_third_opinion: Force third opinion recovery even if validation passes
        
        Returns:
            Dict: Enhanced product data with tags and metadata
        """
        self.logger.info(f"Tagging product: {product_data.get('title', 'Unknown')}")
        
        # Step 1: Detect category
        category = self.tag_category(product_data)
        self.logger.debug(f"Detected category: {category}")
        
        # Step 2: Run all applicable rule-based tagging methods
        rule_tags = []
        
        # Device-related tags
        if category in ["device", "pod_system"]:
            rule_tags.extend(self.tag_device_style(product_data, category))
            rule_tags.extend(self.tag_power_supply(product_data, category))
            rule_tags.extend(self.tag_vaping_style(product_data, category))
        
        # Capacity tags
        if category in ["tank", "pod"]:
            rule_tags.extend(self.tag_capacity(product_data, category))
        
        # Pod-specific tags
        if category == "pod":
            rule_tags.extend(self.tag_pod_type(product_data, category))
        
        # E-liquid tags
        if category == "e-liquid":
            rule_tags.extend(self.tag_bottle_size(product_data, category))
            vg_ratio = self.tag_vg_ratio(product_data, category)
            if vg_ratio:
                rule_tags.append(vg_ratio)
            rule_tags.extend(self.tag_vaping_style(product_data, category))
        
        # Flavor tags (for applicable categories)
        primary_flavors, secondary_flavors = self.tag_flavors(product_data, category)
        rule_tags.extend(primary_flavors)
        
        # Nicotine tags (for applicable categories)
        if category in ["e-liquid", "disposable", "device", "pod_system", "nicotine_pouches"]:
            nic_strength = self.tag_nicotine_strength(product_data, category)
            if nic_strength:
                rule_tags.append(nic_strength)
            rule_tags.extend(self.tag_nicotine_type(product_data, category))
        
        # CBD tags (for CBD products)
        if category == "CBD":
            cbd_strength = self.tag_cbd_strength(product_data, category)
            if cbd_strength:
                rule_tags.append(cbd_strength)
            rule_tags.extend(self.tag_cbd_form(product_data, category))
            rule_tags.extend(self.tag_cbd_type(product_data, category))
        
        # Compliance tags (optional)
        compliance_tags = self.tag_compliance(product_data, category)
        
        # Remove duplicates from rule tags
        rule_tags = list(set(rule_tags))
        
        self.logger.info(f"Rule-based tagging generated {len(rule_tags)} tags")
        
        # Step 3: AI-powered enhancement (if enabled and available)
        ai_result = None
        ai_tags = []
        ai_confidence = 0.0
        model_used = 'none'
        ai_reasoning = ''
        
        if use_ai and self.ai_cascade and self.config.enable_ai_tagging:
            try:
                approved_schema = self.tag_validator.get_approved_schema()
                ai_result = self.ai_cascade.generate_tags_with_cascade(
                    product_data, 
                    category,
                    approved_schema
                )
                ai_tags = ai_result.get('tags', [])
                ai_confidence = ai_result.get('confidence', 0.0)
                model_used = ai_result.get('model_used', 'none')
                ai_reasoning = ai_result.get('reasoning', '')
                
                self.logger.info(f"AI cascade generated {len(ai_tags)} tags with confidence {ai_confidence:.2f} using {model_used}")
            except Exception as e:
                self.logger.warning(f"AI cascade failed: {e}")
        
        # Step 4: Combine and validate all tags
        all_tags = list(set(rule_tags + ai_tags))
        
        is_valid, failure_reasons = self.tag_validator.validate_all_tags(all_tags, category)
        
        needs_manual_review = False
        final_tags = all_tags
        
        # Step 5: Attempt third opinion recovery if validation failed OR forced
        if not is_valid or force_third_opinion:
            reason_msg = "forced recovery" if force_third_opinion and is_valid else f"{len(failure_reasons)} validation failures"
            self.logger.warning(f"Attempting recovery due to: {reason_msg}")
            
            recovery_result = self.third_opinion.attempt_recovery(
                product_data,
                ai_tags,
                rule_tags,
                failure_reasons if not is_valid else [],
                self.tag_validator.get_approved_schema(),
                category
            )
            
            if recovery_result:
                recovered_tags = recovery_result.get('tags', [])
                # Re-validate recovered tags
                recovered_valid, recovered_failures = self.tag_validator.validate_all_tags(recovered_tags, category)
                
                if recovered_valid:
                    self.logger.info("Third opinion recovery succeeded!")
                    final_tags = recovered_tags
                    needs_manual_review = True  # Recovery always requires review
                    failure_reasons = []
                    ai_confidence = recovery_result.get('confidence', 0.0)
                    model_used = f"{model_used}+recovery"
                else:
                    self.logger.warning("Third opinion recovery also failed validation")
                    needs_manual_review = True
                    # Keep combined tags but flag for review
            else:
                self.logger.error("Third opinion recovery returned no result")
                needs_manual_review = True
        else:
            # Check if AI flagged for manual review
            if ai_result and ai_result.get('needs_manual_review', False):
                needs_manual_review = True
        
        # Remove duplicates while preserving order
        unique_tags = []
        seen = set()
        for tag in final_tags:
            if tag not in seen:
                unique_tags.append(tag)
                seen.add(tag)
        
        # Step 6: Prepare enhanced product data
        enhanced_product = product_data.copy()
        enhanced_product['tags'] = unique_tags
        enhanced_product['category'] = category
        enhanced_product['needs_manual_review'] = needs_manual_review
        enhanced_product['confidence_scores'] = {
            'ai_confidence': ai_confidence,
        }
        enhanced_product['model_used'] = model_used
        enhanced_product['tag_breakdown'] = {
            'rule_based_tags': rule_tags,
            'ai_suggested_tags': ai_tags,
            'secondary_flavors': secondary_flavors,
            'final_tags': unique_tags,
        }
        enhanced_product['failure_reasons'] = failure_reasons if failure_reasons else []
        enhanced_product['ai_reasoning'] = ai_reasoning
        
        self.logger.info(f"Final tagging: {len(unique_tags)} tags, needs_review={needs_manual_review}")
        
        # Save to cache if available
        if self.cache and use_ai:
            self.cache.save_tags(product_data, ai_tags, rule_tags)
        
        return enhanced_product
    
    def generate_collections(self, tagged_products: List[Dict]) -> List[Dict]:
        """
        Generate Shopify collections based on product tags
        
        Args:
            tagged_products: List of tagged product dictionaries
        
        Returns:
            List[Dict]: Collection definitions
        """
        if not self.config.auto_generate_collections:
            return []
        
        self.logger.info("Generating dynamic collections from tagged products")
        
        collections = []
        
        # Flavor-based collections
        flavor_families = set()
        for product in tagged_products:
            flavors = product.get('tag_breakdown', {}).get('flavors', {})
            flavor_families.update(flavors.keys())
        
        for family in flavor_families:
            collection_title = f"{self.config.collection_prefix}{family} Flavors".strip()
            collections.append({
                'title': collection_title,
                'description': f"Explore our {family.lower()} flavored vaping products",
                'filter_tags': [family]
            })
        
        # Nicotine-based collections
        collections.extend([
            {
                'title': f"{self.config.collection_prefix}Zero Nicotine Devices".strip(),
                'description': "Nicotine-free vaping options",
                'filter_tags': ['Zero Nicotine', '0mg']
            },
            {
                'title': f"{self.config.collection_prefix}High Strength Nicotine".strip(),
                'description': "High strength nicotine vaping products",
                'filter_tags': ['High Strength', 'Strong']
            }
        ])
        
        # Device-based collections
        collections.extend([
            {
                'title': f"{self.config.collection_prefix}Disposable Vapes".strip(),
                'description': "Convenient disposable vaping devices",
                'filter_tags': ['Disposable']
            },
            {
                'title': f"{self.config.collection_prefix}Beginner Vape Kits".strip(),
                'description': "Perfect starter kits for beginners",
                'filter_tags': ['Pod System', 'AIO', 'Compact']
            }
        ])
        
        self.logger.info(f"Generated {len(collections)} collections")
        
        return collections
