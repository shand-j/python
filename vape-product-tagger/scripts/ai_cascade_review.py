#!/usr/bin/env python3
"""
AI Cascade Review Script
=========================
Secondary review system for products that failed initial tagging.
Takes tagged_review.csv and attempts to fix specific tag issues.

Usage:
    python scripts/ai_cascade_review.py --input data/output/autonomous/*_tagged_review.csv
    python scripts/ai_cascade_review.py --input review.csv --output fixed/
    python scripts/ai_cascade_review.py --input review.csv --dry-run
"""

import argparse
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config import Config
from modules.logger import setup_logger
from modules.ollama_processor import OllamaProcessor
from modules.tag_validator import TagValidator


class AICascadeReviewer:
    """
    Reviews products that failed validation and attempts to fix specific tag issues.
    Uses targeted AI prompts to fill in missing required tags.
    """
    
    # Map failure reasons to specific tag fixes
    FAILURE_PATTERNS = {
        r'missing cbd_type': 'cbd_type',
        r'missing strength': 'strength',
        r'missing nicotine_type': 'nicotine_type',
        r'missing flavor_profile': 'flavor_profile',
        r'missing device_type': 'device_type',
        r'missing vaping_style': 'vaping_style',
        r'missing vg_ratio': 'vg_ratio',
        r'Category detection failed': 'category',
    }
    
    # Targeted prompts for specific tag fixes
    TAG_PROMPTS = {
        'cbd_type': """Analyze this CBD product and determine its CBD type.

Product: {title}
Description: {body}
Current Tags: {tags}

CBD Type Options (choose ONE):
- full_spectrum: Contains full range of cannabinoids, terpenes, THC < 0.3%
- broad_spectrum: Like full spectrum but THC-free
- isolate: Pure CBD, 99%+ purity
- cbg: Primarily contains CBG (cannabigerol)
- cbda: Contains CBDA (raw/acidic form)

If the description mentions "full spectrum" or "whole plant", choose full_spectrum.
If it mentions "broad spectrum" or "THC free", choose broad_spectrum.
If it mentions "isolate" or "pure CBD", choose isolate.
If it mentions "CBG", choose cbg.
If it mentions "CBDA" or "raw", choose cbda.

If unclear from description, common products:
- CBD e-liquids are typically broad_spectrum or isolate
- CBD oils/tinctures are typically full_spectrum
- CBD edibles are typically broad_spectrum or isolate

Return ONLY the cbd_type tag value (e.g., "broad_spectrum"). Nothing else.""",

        'nicotine_type': """Analyze this product and determine the nicotine type.

Product: {title}
Description: {body}
Current Tags: {tags}

Nicotine Type Options (choose ONE):
- nic_salt: Nicotine salts, smoother throat hit, typically 10-20mg
- freebase: Traditional nicotine, harsher at high strengths
- nicotine_free: 0mg, no nicotine
- synthetic: TFN (tobacco-free nicotine)

Key indicators:
- "salt" or "nic salt" in name → nic_salt
- "50vg" or "50/50" often indicates nic_salt
- "freebase" in name → freebase
- "shortfill" usually requires adding nicotine shots → nicotine_free (base product)
- "0mg" in title → nicotine_free
- "TFN" or "tobacco-free" → synthetic

Return ONLY the nicotine_type tag value (e.g., "nic_salt"). Nothing else.""",

        'category': """Analyze this product and determine its category.

Product: {title}
Description: {body}

Category Options (choose ONE primary):
- e-liquid: E-liquids, vape juice, nic salts, shortfills
- disposable: Single-use vapes, disposable pods
- pod_system: Pod devices, starter kits with pods
- device: Vape mods, box mods, kits
- tank: Tanks, atomizers
- coil: Replacement coils
- pod: Replacement pods, cartridges
- CBD: CBD products (e-liquids, oils, edibles)
- nicotine_pouches: Nicotine pouches, snus, nicotine candy

Analyze the title carefully:
- "e-liquid", "juice", "vape liquid" → e-liquid
- "disposable", "bar", "puff" → disposable  
- "pod kit", "starter kit" → pod_system
- "mod", "device", "kit" (without pod) → device
- "cbd", "cannabidiol" → CBD
- "pouch", "snus", "candy" with "nicotine" → nicotine_pouches

Return ONLY the category value (e.g., "e-liquid"). Nothing else.""",

        'flavor_profile': """Analyze this product and determine its primary flavor profile.

Product: {title}
Description: {body}
Current Tags: {tags}

Flavor Profile Options (choose ONE primary):
- fruity: Fruit flavors (strawberry, mango, apple, etc.)
- ice: Menthol, mint, cooling
- tobacco: Tobacco, cigarette-like
- desserts/bakery: Dessert, cake, custard, cream
- beverage: Coffee, cola, energy drink
- candy/sweets: Candy, gummy, sweet
- nuts: Nut flavors
- unflavoured: No flavor added

Look for flavor words in title and description.
"Menthol" or "Ice" indicates ice.
Fruit names indicate fruity.
"Custard", "Cake", "Cream" indicate desserts/bakery.

Return ONLY the flavor_profile tag value (e.g., "fruity"). Nothing else.""",

        'device_type': """Analyze this device and determine its type.

Product: {title}
Description: {body}
Current Tags: {tags}

Device Type Options (choose ONE):
- pod_system: Pod-based systems, refillable or prefilled
- starter_kit: Beginner kits, all-in-one
- box_mod: Box-shaped mods, usually with external batteries
- tube_mod: Cylindrical/pen-style mods
- disposable: Single-use vapes
- aio: All-in-one devices

Look for keywords:
- "pod" → pod_system
- "starter" or "kit" → starter_kit
- "box" or "mod" → box_mod
- "pen" or "stick" → tube_mod
- "disposable" → disposable
- "aio" or "all-in-one" → aio

Return ONLY the device_type tag value (e.g., "pod_system"). Nothing else.""",

        'strength': """Analyze this product and extract its nicotine/CBD strength.

Product: {title}
Description: {body}

Look for strength patterns in the title:
- "Xmg" where X is a number (e.g., "10mg", "20mg", "1000mg")
- "X mg" with space
- Nicotine typically: 0, 3, 6, 10, 12, 18, 20 mg
- CBD typically: 100, 250, 500, 1000, 1500, 2000 mg or higher

Return ONLY the numeric value without "mg" (e.g., "20"). Nothing else.
If multiple strengths, return the first/primary one.
If no strength found, return "unknown".""",

        'vg_ratio': """Analyze this e-liquid and determine its VG/PG ratio.

Product: {title}
Description: {body}

Common VG/PG Ratios:
- 70/30: 70% VG, 30% PG - common for sub-ohm
- 50/50: Equal ratio - common for nic salts, MTL
- 80/20: High VG for cloud production
- 100/0: Max VG

Look for patterns:
- "70VG/30PG" or "70/30" → 70/30
- "50/50" or "50VG" → 50/50
- "Max VG" or "100VG" → 100/0
- "Shortfill" often implies 70/30 or 80/20

Return ONLY the ratio in format "XX/YY" (e.g., "70/30"). Nothing else.
If not specified, return "unknown".""",

        'vaping_style': """Analyze this product and determine the recommended vaping style.

Product: {title}
Description: {body}
Current Tags: {tags}

Vaping Style Options:
- mouth-to-lung: MTL, tight draw, like cigarettes, typically high PG
- direct-to-lung: DTL/DL, open airflow, big clouds, typically high VG
- restricted-direct-to-lung: RDTL, between MTL and DTL

Key indicators:
- "MTL" or "mouth to lung" → mouth-to-lung
- "DTL" or "DL" or "direct lung" → direct-to-lung
- "50/50" ratio usually → mouth-to-lung
- "70/30" or higher VG → direct-to-lung
- "Nic salt" usually → mouth-to-lung
- "Sub-ohm" → direct-to-lung
- "Pod" devices typically → mouth-to-lung or restricted-direct-to-lung

Return ONLY the vaping_style value (e.g., "mouth-to-lung"). Nothing else.""",
    }
    
    def __init__(self, config: Config, logger, ollama: OllamaProcessor):
        self.config = config
        self.logger = logger
        self.ollama = ollama
        self.validator = TagValidator(
            schema_path=PROJECT_ROOT / "approved_tags.json",
            logger=logger
        )
        
        # Load approved tags for validation
        with open(PROJECT_ROOT / "approved_tags.json", 'r') as f:
            self.approved_tags = json.load(f)
    
    def parse_failure_reasons(self, failure_text: str) -> List[str]:
        """Extract which tags need fixing from failure reason text"""
        if pd.isna(failure_text) or not failure_text:
            return []
        
        tags_to_fix = []
        failure_lower = failure_text.lower()
        
        for pattern, tag_name in self.FAILURE_PATTERNS.items():
            if re.search(pattern, failure_lower, re.IGNORECASE):
                tags_to_fix.append(tag_name)
        
        return tags_to_fix
    
    def get_valid_options(self, tag_name: str) -> List[str]:
        """Get valid options for a tag from approved_tags.json"""
        # Check in tags array
        for tag_def in self.approved_tags.get('tags', []):
            if tag_def.get('name') == tag_name:
                return tag_def.get('allowed_values', [])
        
        return []
    
    def fix_missing_tag(self, 
                        handle: str,
                        title: str, 
                        body: str, 
                        current_tags: str,
                        tag_to_fix: str) -> Optional[str]:
        """
        Use AI to determine the correct value for a missing tag.
        
        Returns:
            Tag value if successfully determined, None otherwise
        """
        if tag_to_fix not in self.TAG_PROMPTS:
            self.logger.warning(f"No prompt defined for tag: {tag_to_fix}")
            return None
        
        # Format prompt
        prompt = self.TAG_PROMPTS[tag_to_fix].format(
            title=title,
            body=body[:1500] if body else "No description available",
            tags=current_tags or "None"
        )
        
        # Call AI using OllamaProcessor's internal method
        try:
            response = self.ollama._call_ollama(prompt)
            
            if not response:
                return None
            
            # Clean response
            value = response.strip().lower()
            
            # Remove common prefixes/suffixes
            value = re.sub(r'^(the |a |answer: |result: )', '', value)
            value = re.sub(r'[.,;:]$', '', value)
            value = value.strip()
            
            # Handle special tag types
            value = self._normalize_tag_value(tag_to_fix, value)
            
            # Validate against allowed values if applicable
            valid_options = self.get_valid_options(tag_to_fix)
            if valid_options and value not in valid_options:
                value = self._find_closest_match(value, valid_options, tag_to_fix)
            
            if value:
                self.logger.info(f"  ✓ Fixed {tag_to_fix} = {value}")
            return value
            
        except Exception as e:
            self.logger.error(f"AI call failed for {tag_to_fix}: {e}")
            return None
    
    def _normalize_tag_value(self, tag_name: str, value: str) -> str:
        """Normalize tag values based on tag type"""
        # Special handling for ratios
        if tag_name == 'vg_ratio':
            match = re.search(r'(\d+)\s*[/:]?\s*(\d+)?', value)
            if match:
                vg = match.group(1)
                pg = match.group(2) or str(100 - int(vg))
                return f"{vg}/{pg}"
        
        # Special handling for strength
        if tag_name == 'strength':
            match = re.search(r'(\d+(?:\.\d+)?)', value)
            if match:
                return match.group(1)
        
        return value
    
    def _find_closest_match(self, value: str, valid_options: List[str], tag_name: str) -> Optional[str]:
        """Find closest matching valid option for a value"""
        for option in valid_options:
            if option in value or value in option:
                return option
        
        self.logger.warning(f"AI returned invalid value '{value}' for {tag_name}. Valid: {valid_options}")
        return None
    
    def review_product(self, row: pd.Series) -> Tuple[pd.Series, bool]:
        """
        Review a single product and attempt to fix its tags.
        
        Args:
            row: DataFrame row with product data
            
        Returns:
            Tuple of (updated row, was_fixed)
        """
        handle = row.get('Handle', 'unknown')
        title = row.get('Title', '')
        body = row.get('Body (HTML)', '') or row.get('Body', '')
        current_tags = row.get('Tags', '')
        failure_reasons = row.get('Failure Reasons', '')
        category = row.get('Category', '')
        
        self.logger.info(f"\n📋 Reviewing: {handle}")
        self.logger.info(f"   Title: {title[:60]}...")
        self.logger.info(f"   Failure: {failure_reasons[:100]}...")
        
        # Parse what needs fixing
        tags_to_fix = self.parse_failure_reasons(failure_reasons)
        
        if not tags_to_fix:
            self.logger.warning(f"   Could not determine tags to fix from: {failure_reasons}")
            return row, False
        
        self.logger.info(f"   Tags to fix: {tags_to_fix}")
        
        # Fix each missing tag
        fixed_tags = {}
        for tag_name in tags_to_fix:
            new_value = self.fix_missing_tag(handle, title, body, current_tags, tag_name)
            if new_value:
                fixed_tags[tag_name] = new_value
        
        if not fixed_tags:
            self.logger.warning(f"   ✗ Could not fix any tags")
            return row, False
        
        # Update the Tags field
        existing_tags = [t.strip() for t in (current_tags or '').split(',') if t.strip()]
        
        # Add fixed tags
        for tag_name, tag_value in fixed_tags.items():
            existing_tags.append(tag_value)
        
        # Update row
        updated_row = row.copy()
        updated_row['Tags'] = ', '.join(existing_tags)
        
        # Update category if it was fixed
        if 'category' in fixed_tags:
            updated_row['Category'] = fixed_tags['category']
        
        # Clear failure reasons since we fixed the issues
        updated_row['Failure Reasons'] = f"Auto-fixed: {', '.join(fixed_tags.keys())}"
        
        self.logger.info(f"   ✅ Fixed! New tags: {updated_row['Tags']}")
        
        return updated_row, True
    
    def review_csv(self, 
                   input_path: Path, 
                   output_dir: Optional[Path] = None,
                   dry_run: bool = False) -> Dict:
        """
        Review all products in a review CSV file.
        
        Args:
            input_path: Path to tagged_review.csv
            output_dir: Output directory (defaults to input directory)
            dry_run: If True, don't write output files
            
        Returns:
            Dict with review statistics
        """
        self.logger.info("="*80)
        self.logger.info("🔍 AI Cascade Review - Starting")
        self.logger.info("="*80)
        
        # Load review CSV
        df = pd.read_csv(input_path, dtype={'Variant SKU': str, 'SKU': str})
        self.logger.info(f"Loaded {len(df)} rows from {input_path.name}")
        
        # Get unique handles (products, not variant rows)
        unique_handles = df['Handle'].unique()
        self.logger.info(f"Found {len(unique_handles)} unique products to review")
        
        # Track statistics
        stats = {
            'total_products': len(unique_handles),
            'fixed': 0,
            'unfixed': 0,
            'products_fixed': [],
            'products_unfixed': []
        }
        
        fixed_rows = []
        still_review_rows = []
        
        # Process each handle
        for handle in unique_handles:
            handle_rows = df[df['Handle'] == handle].copy()
            first_row = handle_rows.iloc[0]
            
            # Review the product (use first row for product-level data)
            updated_row, was_fixed = self.review_product(first_row)
            
            if was_fixed:
                stats['fixed'] += 1
                stats['products_fixed'].append(handle)
                
                # Apply fixes to all rows with this handle
                for idx, row in handle_rows.iterrows():
                    updated = row.copy()
                    updated['Tags'] = updated_row['Tags']
                    updated['Category'] = updated_row.get('Category', row.get('Category'))
                    updated['Failure Reasons'] = updated_row['Failure Reasons']
                    fixed_rows.append(updated)
            else:
                stats['unfixed'] += 1
                stats['products_unfixed'].append(handle)
                
                # Keep original rows in review
                for _, row in handle_rows.iterrows():
                    still_review_rows.append(row)
        
        # Summary
        self.logger.info("\n" + "="*80)
        self.logger.info("📊 Review Summary")
        self.logger.info("="*80)
        self.logger.info(f"Total products reviewed: {stats['total_products']}")
        self.logger.info(f"Successfully fixed: {stats['fixed']} ({100*stats['fixed']/max(1,stats['total_products']):.1f}%)")
        self.logger.info(f"Still need manual review: {stats['unfixed']}")
        
        if not dry_run and (fixed_rows or still_review_rows):
            output_dir = output_dir or input_path.parent
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Write fixed products (merge into clean)
            if fixed_rows:
                fixed_df = pd.DataFrame(fixed_rows)
                fixed_path = output_dir / f"{timestamp}_cascade_fixed.csv"
                fixed_df.to_csv(fixed_path, index=False)
                self.logger.info(f"✓ Wrote {len(fixed_rows)} fixed rows to {fixed_path.name}")
                stats['fixed_file'] = str(fixed_path)
            
            # Write still-needs-review products
            if still_review_rows:
                review_df = pd.DataFrame(still_review_rows)
                review_path = output_dir / f"{timestamp}_cascade_review.csv"
                review_df.to_csv(review_path, index=False)
                self.logger.info(f"✓ Wrote {len(still_review_rows)} review rows to {review_path.name}")
                stats['review_file'] = str(review_path)
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description='AI Cascade Review - Fix products that failed initial tagging'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Path to tagged_review.csv file'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output directory (defaults to input directory)'
    )
    parser.add_argument(
        '--config',
        default=str(PROJECT_ROOT / 'config.env'),
        help='Path to config file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Initialize
    config = Config(args.config)
    logger = setup_logger(
        name='cascade_review',
        log_dir=str(config.logs_dir),
        level='DEBUG' if args.verbose else config.log_level,
        verbose=args.verbose
    )
    
    # Initialize AI processor
    try:
        ollama = OllamaProcessor(config, logger)
        logger.info("✓ Ollama AI processor initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Ollama: {e}")
        sys.exit(1)
    
    # Create reviewer
    reviewer = AICascadeReviewer(config, logger, ollama)
    
    # Run review
    input_path = Path(args.input)
    output_dir = Path(args.output) if args.output else None
    
    stats = reviewer.review_csv(input_path, output_dir, dry_run=args.dry_run)
    
    # Exit code based on success
    if stats['fixed'] > 0:
        logger.info(f"\n✅ Successfully fixed {stats['fixed']} products!")
        sys.exit(0)
    elif stats['unfixed'] > 0:
        logger.warning(f"\n⚠️ {stats['unfixed']} products still need manual review")
        sys.exit(0)
    else:
        logger.error("\n❌ No products were processed")
        sys.exit(1)


if __name__ == '__main__':
    main()
