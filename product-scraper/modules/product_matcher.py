"""
Cross-source product matching module for identifying the same products across different sources.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
import hashlib


@dataclass
class MatchCriteria:
    """Criteria for matching products across sources"""
    name: str
    weight: float  # 0.0-1.0
    threshold: float  # 0.0-1.0 (minimum similarity to consider a match)


@dataclass
class ProductMatch:
    """A match between products from different sources"""
    product_id_1: str
    product_id_2: str
    source_1: str
    source_2: str
    match_score: float  # 0.0-1.0
    match_method: str
    confidence: str  # high, medium, low


@dataclass
class UnifiedProduct:
    """Unified product profile combining data from multiple sources"""
    product_id: str
    name: str
    brand: str
    model_number: Optional[str]
    sources: List[Dict]  # List of source attributions
    primary_source: str  # Highest priority source
    match_score: float
    metadata: Dict


class ProductMatcher:
    """Matches products across different sources"""
    
    def __init__(self):
        self.match_criteria = [
            MatchCriteria("exact_name", 1.0, 0.95),
            MatchCriteria("brand_model", 0.9, 0.85),
            MatchCriteria("image_hash", 0.8, 0.75),
            MatchCriteria("specifications", 0.7, 0.70)
        ]
    
    def match_products(self, products_1: List[Dict], products_2: List[Dict], 
                      source_1: str, source_2: str) -> List[ProductMatch]:
        """
        Match products between two sources using multiple criteria.
        
        Args:
            products_1: List of products from first source
            products_2: List of products from second source
            source_1: Name of first source
            source_2: Name of second source
            
        Returns:
            List of ProductMatch objects
        """
        matches = []
        
        for p1 in products_1:
            best_match = None
            best_score = 0.0
            best_method = None
            
            for p2 in products_2:
                # Try each matching method
                score, method = self._calculate_match_score(p1, p2)
                
                if score > best_score:
                    best_score = score
                    best_match = p2
                    best_method = method
            
            # Create match if score exceeds threshold
            if best_match and best_score >= 0.70:  # Minimum threshold
                confidence = self._get_confidence_level(best_score)
                
                matches.append(ProductMatch(
                    product_id_1=p1.get('id', p1.get('url', '')),
                    product_id_2=best_match.get('id', best_match.get('url', '')),
                    source_1=source_1,
                    source_2=source_2,
                    match_score=best_score,
                    match_method=best_method,
                    confidence=confidence
                ))
        
        return matches
    
    def _calculate_match_score(self, product_1: Dict, product_2: Dict) -> Tuple[float, str]:
        """Calculate match score between two products"""
        scores = []
        
        # 1. Exact product name matching
        name_score = self._match_exact_name(product_1, product_2)
        scores.append((name_score, "exact_name", 1.0))
        
        # 2. Brand + model number matching
        brand_model_score = self._match_brand_model(product_1, product_2)
        scores.append((brand_model_score, "brand_model", 0.9))
        
        # 3. Image hash similarity
        image_score = self._match_image_hash(product_1, product_2)
        scores.append((image_score, "image_hash", 0.8))
        
        # 4. Feature specifications
        spec_score = self._match_specifications(product_1, product_2)
        scores.append((spec_score, "specifications", 0.7))
        
        # Find best matching method
        best_score = 0.0
        best_method = None
        
        for score, method, weight in scores:
            weighted_score = score * weight
            if weighted_score > best_score:
                best_score = weighted_score
                best_method = method
        
        return best_score, best_method
    
    def _match_exact_name(self, p1: Dict, p2: Dict) -> float:
        """Match products by exact name similarity"""
        name1 = self._normalize_name(p1.get('title', p1.get('name', '')))
        name2 = self._normalize_name(p2.get('title', p2.get('name', '')))
        
        if not name1 or not name2:
            return 0.0
        
        return SequenceMatcher(None, name1, name2).ratio()
    
    def _match_brand_model(self, p1: Dict, p2: Dict) -> float:
        """Match products by brand and model number"""
        brand1 = self._normalize_name(p1.get('brand', ''))
        brand2 = self._normalize_name(p2.get('brand', ''))
        
        if not brand1 or not brand2:
            return 0.0
        
        # Extract model numbers
        model1 = self._extract_model_number(p1.get('title', p1.get('name', '')))
        model2 = self._extract_model_number(p2.get('title', p2.get('name', '')))
        
        brand_match = 1.0 if brand1 == brand2 else SequenceMatcher(None, brand1, brand2).ratio()
        
        if model1 and model2:
            model_match = 1.0 if model1 == model2 else SequenceMatcher(None, model1, model2).ratio()
            return (brand_match + model_match) / 2
        
        return brand_match * 0.7  # Lower score if no model number
    
    def _match_image_hash(self, p1: Dict, p2: Dict) -> float:
        """Match products by image hash similarity"""
        # Get image URLs
        img1 = p1.get('image_url', p1.get('image', ''))
        img2 = p2.get('image_url', p2.get('image', ''))
        
        if not img1 or not img2:
            return 0.0
        
        # Simple hash-based comparison (in practice, would use perceptual hashing)
        hash1 = hashlib.md5(img1.encode()).hexdigest()
        hash2 = hashlib.md5(img2.encode()).hexdigest()
        
        if hash1 == hash2:
            return 1.0
        
        # Count matching hex digits for similarity
        matches = sum(c1 == c2 for c1, c2 in zip(hash1, hash2))
        return matches / len(hash1)
    
    def _match_specifications(self, p1: Dict, p2: Dict) -> float:
        """Match products by specifications"""
        # Extract key specifications
        specs1 = self._extract_specs(p1)
        specs2 = self._extract_specs(p2)
        
        if not specs1 or not specs2:
            return 0.0
        
        # Count matching specifications
        common_keys = set(specs1.keys()) & set(specs2.keys())
        if not common_keys:
            return 0.0
        
        matches = sum(specs1[k] == specs2[k] for k in common_keys)
        return matches / len(common_keys)
    
    def _normalize_name(self, name: str) -> str:
        """Normalize product name for comparison"""
        name = name.lower().strip()
        # Remove common noise words
        noise_words = ['the', 'kit', 'vape', 'e-cigarette', 'device']
        for word in noise_words:
            name = re.sub(rf'\b{word}\b', '', name)
        # Remove extra whitespace
        name = ' '.join(name.split())
        return name
    
    def _extract_model_number(self, text: str) -> Optional[str]:
        """Extract model number from product name"""
        # Common model number patterns
        patterns = [
            r'\b([A-Z]+[\s-]?\d+[A-Z]?)\b',  # e.g., XROS-3, NOVO5
            r'\b(V\d+)\b',  # e.g., V5
            r'\b(\d+(?:mg|ml|w))\b'  # e.g., 20mg, 5ml, 80w
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def _extract_specs(self, product: Dict) -> Dict:
        """Extract specifications from product data"""
        specs = {}
        
        # Look for specifications in various fields
        if 'specifications' in product:
            specs = product['specifications']
        elif 'details' in product:
            specs = product['details']
        
        # Extract common specs from description
        desc = product.get('description', '')
        if desc:
            # Look for capacity
            capacity_match = re.search(r'(\d+(?:\.\d+)?)\s*ml', desc, re.IGNORECASE)
            if capacity_match:
                specs['capacity'] = capacity_match.group(1) + 'ml'
            
            # Look for power
            power_match = re.search(r'(\d+)\s*w', desc, re.IGNORECASE)
            if power_match:
                specs['power'] = power_match.group(1) + 'w'
        
        return specs
    
    def _get_confidence_level(self, score: float) -> str:
        """Determine confidence level based on match score"""
        if score >= 0.90:
            return "high"
        elif score >= 0.75:
            return "medium"
        else:
            return "low"
    
    def create_unified_products(self, matches: List[ProductMatch], 
                               all_products: Dict[str, List[Dict]]) -> List[UnifiedProduct]:
        """
        Create unified product profiles from matches.
        
        Args:
            matches: List of product matches
            all_products: Dict mapping source names to product lists
            
        Returns:
            List of UnifiedProduct objects
        """
        unified = []
        processed = set()
        
        for match in matches:
            match_key = (match.product_id_1, match.product_id_2)
            if match_key in processed:
                continue
            
            # Find products from sources
            product_1 = self._find_product(match.product_id_1, all_products[match.source_1])
            product_2 = self._find_product(match.product_id_2, all_products[match.source_2])
            
            if product_1 and product_2:
                unified_product = self._merge_products(
                    product_1, product_2, match.source_1, match.source_2, match.match_score
                )
                unified.append(unified_product)
                processed.add(match_key)
        
        return unified
    
    def _find_product(self, product_id: str, products: List[Dict]) -> Optional[Dict]:
        """Find product by ID in product list"""
        for product in products:
            if product.get('id') == product_id or product.get('url') == product_id:
                return product
        return None
    
    def _merge_products(self, p1: Dict, p2: Dict, source_1: str, source_2: str, 
                       score: float) -> UnifiedProduct:
        """Merge two products into a unified profile"""
        # Use first product as base
        name = p1.get('title', p1.get('name', ''))
        brand = p1.get('brand', p2.get('brand', ''))
        model = self._extract_model_number(name)
        
        sources = [
            {
                'source': source_1,
                'product_id': p1.get('id', p1.get('url', '')),
                'url': p1.get('url', ''),
                'title': p1.get('title', p1.get('name', '')),
                'price': p1.get('price'),
                'image': p1.get('image_url', p1.get('image'))
            },
            {
                'source': source_2,
                'product_id': p2.get('id', p2.get('url', '')),
                'url': p2.get('url', ''),
                'title': p2.get('title', p2.get('name', '')),
                'price': p2.get('price'),
                'image': p2.get('image_url', p2.get('image'))
            }
        ]
        
        return UnifiedProduct(
            product_id=hashlib.md5(f"{brand}_{name}".encode()).hexdigest()[:16],
            name=name,
            brand=brand,
            model_number=model,
            sources=sources,
            primary_source=source_1,  # First source is primary
            match_score=score,
            metadata={
                'match_count': 2,
                'categories': list(set([p1.get('category', ''), p2.get('category', '')]))
            }
        )
