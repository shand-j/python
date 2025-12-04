"""
Product Tagging Engine Module
Core logic for intelligent vaping product tagging
"""
import re
from typing import Dict, List, Set
from .taxonomy import VapeTaxonomy


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
    
    def _extract_nicotine_value(self, text: str) -> float:
        """
        Extract nicotine value from text
        
        Args:
            text: Text to search
        
        Returns:
            float: Nicotine value in mg or 0 if not found
        """
        if not text:
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
                    return float(match.group(1))
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
    
    def tag_device_type(self, product_data: Dict) -> List[str]:
        """
        Tag device type based on product data
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            List[str]: Device type tags
        """
        tags = set()
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        # Check each device type
        for device_type, data in self.taxonomy.DEVICE_TYPES.items():
            if self._match_keywords(text, data['keywords']):
                tags.update(data['tags'])
        
        return list(tags)
    
    def tag_device_form(self, product_data: Dict, device_type_tags: List[str] = None) -> List[str]:
        """
        Tag device form based on product data
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            List[str]: Device form tags
        """
        tags = set()
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()

        # If caller provided device_type_tags, use it; otherwise compute. We only want
        # device-form tags if there's evidence the product is a device/hardware.
        if device_type_tags is None:
            device_type_tags = self.tag_device_type(product_data)

        # If no device-type evidence, check for some strong device cue keywords
        device_cues = [
            'battery', 'coil', 'pod', 'cartridge', 'kit', 'charger', 'prefilled',
            'refill', 'atomizer', 'vape', 'device', 'mod'
        ]

        has_device_evidence = bool(device_type_tags) or self._match_keywords(text, device_cues)
        if not has_device_evidence:
            return []
        
        # Check each device form
        for form, data in self.taxonomy.DEVICE_FORMS.items():
            if self._match_keywords(text, data['keywords']):
                tags.update(data['tags'])
        
        return list(tags)
    
    def tag_flavors(self, product_data: Dict) -> Dict[str, List[str]]:
        """
        Tag flavors with family and sub-category hierarchy
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            Dict[str, List[str]]: Flavor tags organized by family
        """
        flavor_tags = {}
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        # Check each flavor family
        for family, family_data in self.taxonomy.FLAVOR_TAXONOMY.items():
            family_matches = []
            
            # Check main family keywords
            if self._match_keywords(text, family_data['keywords']):
                family_matches.extend(family_data['tags'])
            
            # Check sub-categories
            sub_categories = family_data.get('sub_categories', {})
            for sub_name, sub_data in sub_categories.items():
                if self._match_keywords(text, sub_data['keywords']):
                    family_matches.extend(sub_data['tags'])
            
            if family_matches:
                flavor_tags[family] = list(set(family_matches))
        
        return flavor_tags
    
    def tag_nicotine(self, product_data: Dict) -> Dict[str, List[str]]:
        """
        Tag nicotine strength and type
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            Dict[str, List[str]]: Nicotine tags (strength and type)
        """
        nicotine_tags = {
            'strength': [],
            'type': []
        }
        
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        
        # Extract nicotine value
        nic_value = self._extract_nicotine_value(text)
        
        # Determine strength level
        level, strength_tags = self.taxonomy.get_nicotine_strength_level(nic_value)
        if strength_tags:
            nicotine_tags['strength'] = strength_tags
        
        # Determine nicotine type
        for nic_type, type_data in self.taxonomy.NICOTINE_TYPES.items():
            if self._match_keywords(text, type_data['keywords']):
                nicotine_tags['type'].extend(type_data['tags'])
        
        return nicotine_tags
    
    def tag_compliance(self, product_data: Dict) -> List[str]:
        """
        Generate compliance and age verification tags
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            List[str]: Compliance tags
        """
        if not self.config.enable_compliance_tags:
            return []
        
        tags = []
        
        # Age restriction (always apply for vaping products)
        tags.extend(self.taxonomy.COMPLIANCE_TAGS['age_restriction'])
        
        # Regional compliance
        for region in self.config.regional_compliance:
            if region.upper() == 'US':
                tags.append('US Compliant')
            elif region.upper() == 'EU':
                tags.extend(['EU Compliant', 'TPD Compliant'])
        
        # Nicotine warnings
        text = f"{product_data.get('title', '')} {product_data.get('description', '')}".lower()
        nic_value = self._extract_nicotine_value(text)
        if nic_value > 0:
            tags.extend(self.taxonomy.COMPLIANCE_TAGS['nicotine_warnings'])
        
        # Shipping restrictions
        tags.extend(self.taxonomy.COMPLIANCE_TAGS['shipping_restriction'])
        
        return list(set(tags))
    
    def tag_product(self, product_data: Dict, use_ai: bool = True) -> Dict:
        """
        Generate comprehensive tags for a product
        
        Args:
            product_data: Product information dictionary
            use_ai: Whether to use AI enhancement
        
        Returns:
            Dict: Enhanced product data with tags
        """
        self.logger.info(f"Tagging product: {product_data.get('title', 'Unknown')}")
        
        # Rule-based tagging
        device_type_tags = self.tag_device_type(product_data)
        device_form_tags = self.tag_device_form(product_data, device_type_tags=device_type_tags)
        flavor_tags = self.tag_flavors(product_data)
        nicotine_tags = self.tag_nicotine(product_data)
        compliance_tags = self.tag_compliance(product_data)
        
        # AI-powered enhancement (if enabled and available)
        ai_tags = {}
        if use_ai and self.ollama and self.config.enable_ai_tagging:
            try:
                ai_tags = self.ollama.generate_comprehensive_tags(product_data)
            except Exception as e:
                self.logger.warning(f"AI tagging failed: {e}")
        
        # Combine all tags
        all_tags = []
        all_tags.extend(device_type_tags)
        all_tags.extend(device_form_tags)
        
        # Flatten flavor tags
        for family, tags in flavor_tags.items():
            all_tags.extend(tags)
        
        # Add nicotine tags
        all_tags.extend(nicotine_tags.get('strength', []))
        all_tags.extend(nicotine_tags.get('type', []))
        
        # Add compliance tags
        all_tags.extend(compliance_tags)
        
        # Merge AI tags
        if ai_tags:
            all_tags.extend(ai_tags.get('flavor_tags', []))
            all_tags.extend(ai_tags.get('device_tags', []))
        
        # Remove duplicates while preserving order
        unique_tags = []
        seen = set()
        for tag in all_tags:
            if tag not in seen:
                unique_tags.append(tag)
                seen.add(tag)
        
        # Prepare enhanced product data
        enhanced_product = product_data.copy()
        enhanced_product['tags'] = unique_tags
        enhanced_product['tag_breakdown'] = {
            'device_type': device_type_tags,
            'device_form': device_form_tags,
            'flavors': flavor_tags,
            'nicotine_strength': nicotine_tags.get('strength', []),
            'nicotine_type': nicotine_tags.get('type', []),
            'compliance': compliance_tags,
            'ai_enhanced': ai_tags
        }
        
        self.logger.info(f"Generated {len(unique_tags)} tags for product")
        
        # Save final tags to unified cache if available
        if self.cache and use_ai:
            # Separate AI and rule-based tags for cache storage
            rule_tags = []
            rule_tags.extend(device_type_tags)
            rule_tags.extend(device_form_tags)
            for family, tags in flavor_tags.items():
                rule_tags.extend(tags)
            rule_tags.extend(nicotine_tags.get('strength', []))
            rule_tags.extend(nicotine_tags.get('type', []))
            rule_tags.extend(compliance_tags)
            
            ai_tag_list = []
            if ai_tags:
                ai_tag_list.extend(ai_tags.get('flavor_tags', []))
                ai_tag_list.extend(ai_tags.get('device_tags', []))
                ai_tag_list.extend(ai_tags.get('category_tags', []))
                ai_tag_list.extend(ai_tags.get('compatibility_tags', []))
                ai_tag_list.extend(ai_tags.get('cross_compatibility_tags', []))
            
            # Save to unified cache
            self.cache.save_tags(product_data, ai_tag_list, rule_tags)
        
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
