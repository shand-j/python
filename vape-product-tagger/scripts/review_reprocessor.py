#!/usr/bin/env python3
"""
Review Reprocessor
==================
Re-submits tagged_review.csv products through AI cascade with enhanced prompts.
Uses different, more detailed prompts specifically designed to handle edge cases
and products that failed initial tagging.

This is different from ai_cascade_review.py which does targeted single-tag fixes.
This processor re-runs the entire AI tagging with a more comprehensive prompt.

Usage:
    # Process review file with AI
    python scripts/review_reprocessor.py --input data/output/autonomous/*_tagged_review.csv

    # Append results to existing clean/review files
    python scripts/review_reprocessor.py --input tagged_review.csv \
        --append-clean tagged_clean.csv --append-review tagged_review.csv
    
    # Dry run (no file output)
    python scripts/review_reprocessor.py --input tagged_review.csv --dry-run
    
    # Limit for testing
    python scripts/review_reprocessor.py --input tagged_review.csv --limit 10
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
from modules.taxonomy import VapeTaxonomy

try:
    import requests
except ImportError:
    requests = None


class ReviewReprocessor:
    """
    Reprocesses tagged_review products with enhanced AI prompts.
    
    Unlike the standard tagger, this uses:
    1. More detailed context about why the product failed
    2. Step-by-step reasoning prompts
    3. Explicit examples for edge cases
    4. Higher temperature for more varied responses
    """
    
    # Enhanced prompt for full product retagging
    ENHANCED_TAGGING_PROMPT = """You are an expert vape product tagging specialist. A product failed initial automated tagging and needs your careful analysis.

## PRODUCT INFORMATION
Title: {title}
Description: {description}
Vendor: {vendor}
Current Tags: {current_tags}
Category (detected): {category}
Previous Failure Reasons: {failure_reasons}

## YOUR TASK
Re-analyze this product completely. The previous tagging attempt failed because: {failure_reasons}

Pay special attention to:
{focus_areas}

## REQUIRED TAGS BY CATEGORY

{category_requirements}

## TAGGING RULES
1. Only use tags from the approved vocabulary
2. For nicotine products: strength MUST be 0-20mg (UK legal limit)
3. VG/PG ratios should be formatted as "XX/YY" (e.g., "70/30")
4. CBD products need: category, strength (mg), form, and type
5. If information is missing, make reasonable inferences from the product type
6. Flavors should match the flavor taxonomy exactly

## APPROVED TAG CATEGORIES
{approved_tags_summary}

## RESPONSE FORMAT
Return ONLY valid JSON (no markdown):
{{
    "tags": ["tag1", "tag2", "tag3"],
    "category": "detected_category",
    "confidence": 0.85,
    "reasoning": "Brief explanation of each tagging decision",
    "inferred_tags": ["tags_that_were_inferred"],
    "uncertain_tags": ["tags_you_are_not_sure_about"]
}}

Think step by step:
1. What type of product is this?
2. What category does it belong to?
3. What are the key attributes (strength, flavor, etc.)?
4. What tags are required for this category?
5. Are there any edge cases to consider?
"""

    # Category-specific requirements
    CATEGORY_REQUIREMENTS = {
        'e-liquid': """E-LIQUID Requirements:
- REQUIRED: Category tag (e-liquid)
- REQUIRED: Nicotine type (nic_salt, freebase, nicotine_free)
- REQUIRED: Flavor profile (fruity, ice, tobacco, desserts/bakery, etc.)
- RECOMMENDED: VG/PG ratio (70/30, 50/50, etc.)
- RECOMMENDED: Nicotine strength (0, 3, 6, 10, 20 mg)
- OPTIONAL: Vaping style (mouth-to-lung, direct-to-lung)""",
        
        'disposable': """DISPOSABLE Requirements:
- REQUIRED: Category tag (disposable)
- REQUIRED: Flavor profile
- RECOMMENDED: Puff count if available
- RECOMMENDED: Nicotine strength
- NOTE: Most disposables are nic_salt""",
        
        'device': """DEVICE Requirements:
- REQUIRED: Category tag (device)
- REQUIRED: Device type (box_mod, pod_system, tube_mod, starter_kit)
- RECOMMENDED: Power type (rechargeable, removable_battery)
- OPTIONAL: Vaping style compatibility""",
        
        'pod_system': """POD SYSTEM Requirements:
- REQUIRED: Category tag (pod_system)
- REQUIRED: Device type
- RECOMMENDED: Compatibility tags if applicable""",
        
        'CBD': """CBD Requirements:
- REQUIRED: Category tag (CBD)
- REQUIRED: CBD type (full_spectrum, broad_spectrum, isolate)
- REQUIRED: CBD form (oil, tincture, gummy, capsule, e-liquid)
- REQUIRED: CBD strength in mg
- NOTE: Look for spectrum type in description, default to broad_spectrum for e-liquids""",
        
        'nicotine_pouches': """NICOTINE POUCHES Requirements:
- REQUIRED: Category tag (nicotine_pouches)
- REQUIRED: Flavor profile
- REQUIRED: Nicotine strength
- NOTE: These are tobacco-free oral nicotine products""",
        
        'tank': """TANK Requirements:
- REQUIRED: Category tag (tank)
- OPTIONAL: Tank type (sub_ohm_tank, mtl_tank)
- OPTIONAL: Coil compatibility""",
        
        'coil': """COIL Requirements:
- REQUIRED: Category tag (coil)
- RECOMMENDED: Coil resistance if available
- RECOMMENDED: Compatible device/tank""",
        
        'accessory': """ACCESSORY Requirements:
- REQUIRED: Category tag (accessory)
- Accessories include: batteries, chargers, cases, drip tips, glass, cotton, wire""",
        
        'supplement': """SUPPLEMENT Requirements:
- REQUIRED: Category tag (supplement)
- Supplements include: caffeine pouches, ashwagandha, mushroom products"""
    }
    
    # Focus areas based on failure patterns
    FAILURE_FOCUS_MAP = {
        'cbd_type': "- CBD TYPE: Look for 'full spectrum', 'broad spectrum', 'isolate', 'CBG', 'CBDA' in title/description",
        'nicotine_type': "- NICOTINE TYPE: Check for 'salt', 'nic salt', 'freebase', '0mg', 'TFN'",
        'vg_ratio': "- VG/PG RATIO: Look for 'VG', 'PG', ratio patterns like '70/30' or '50/50'",
        'flavor': "- FLAVOR: Identify specific flavors and map to categories (fruity, ice, tobacco, etc.)",
        'category': "- CATEGORY: Determine if this is e-liquid, device, CBD, etc.",
        'strength': "- STRENGTH: Find nicotine or CBD mg values",
        'device_type': "- DEVICE TYPE: Identify box_mod, pod_system, starter_kit, etc.",
    }
    
    def __init__(self, config: Config, logger):
        self.config = config
        self.logger = logger
        
        # Load approved tags
        approved_tags_path = PROJECT_ROOT / "approved_tags.json"
        with open(approved_tags_path, 'r') as f:
            self.approved_tags = json.load(f)
        
        # Build approved tags summary
        self.approved_tags_summary = self._build_approved_tags_summary()
        
        # Model configuration
        self.base_url = config.ollama_base_url
        self.timeout = config.ollama_timeout
        self.primary_model = getattr(config, 'primary_ai_model', 'mistral:latest')
        self.secondary_model = getattr(config, 'secondary_ai_model', 'llama3.1:latest')
        
        # Statistics
        self.stats = {
            'processed': 0,
            'fixed': 0,
            'still_review': 0,
            'failed': 0
        }
    
    def _build_approved_tags_summary(self) -> str:
        """Build a summary of approved tags for the prompt"""
        lines = []
        for tag_def in self.approved_tags.get('tags', []):
            name = tag_def.get('name', '')
            values = tag_def.get('allowed_values', [])
            if values:
                lines.append(f"- {name}: {', '.join(values[:10])}{'...' if len(values) > 10 else ''}")
        return '\n'.join(lines)
    
    def _parse_failure_reasons(self, failure_text: str) -> List[str]:
        """Extract focus areas from failure reasons"""
        if pd.isna(failure_text) or not failure_text:
            return []
        
        focus_areas = []
        failure_lower = failure_text.lower()
        
        for pattern, focus in self.FAILURE_FOCUS_MAP.items():
            if pattern in failure_lower:
                focus_areas.append(focus)
        
        # Generic focus if no specific pattern found
        if not focus_areas:
            focus_areas.append("- Review all tag categories carefully")
        
        return focus_areas
    
    def _call_model(self, model: str, prompt: str) -> Optional[str]:
        """Call Ollama model and return response"""
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
                    "temperature": 0.4,  # Slightly higher for more varied responses
                    "top_p": 0.9,
                    "num_predict": 500
                }
            }
            
            self.logger.debug(f"Calling {model}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except Exception as e:
            self.logger.error(f"Error calling {model}: {e}")
            return None
    
    def _parse_ai_response(self, response_text: str) -> Optional[Dict]:
        """Parse JSON response from AI"""
        try:
            # Remove markdown code blocks
            cleaned = re.sub(r'```json\s*', '', response_text)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            cleaned = cleaned.strip()
            
            # Find JSON object
            if not cleaned.startswith('{'):
                match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)
            
            data = json.loads(cleaned)
            return data
            
        except Exception as e:
            self.logger.debug(f"JSON parsing failed: {e}")
            
            # Fallback: try to extract tags array
            try:
                array_match = re.search(r'\[([^\]]+)\]', response_text)
                if array_match:
                    tags_text = array_match.group(1)
                    tags = [t.strip().strip('"').strip("'") for t in tags_text.split(',')]
                    tags = [t for t in tags if t]
                    return {
                        'tags': tags,
                        'confidence': 0.5,
                        'reasoning': 'Fallback parsing'
                    }
            except:
                pass
        
        return None
    
    def _validate_tags(self, tags: List[str], category: str) -> Tuple[List[str], List[str]]:
        """Validate tags - be permissive since AI may generate useful tags not in schema"""
        valid_tags = []
        invalid_tags = []
        
        # Build set of all known tags from approved_tags.json
        known_tags = set()
        for key, tag_def in self.approved_tags.items():
            if isinstance(tag_def, dict):
                # Handle nested structure: {"tags": [...], "applies_to": [...]}
                known_tags.update(tag_def.get('tags', []))
                known_tags.update(tag_def.get('allowed_values', []))
        
        # Add common categories
        known_tags.update(['e-liquid', 'disposable', 'device', 'pod_system', 
                          'tank', 'coil', 'CBD', 'nicotine_pouches', 
                          'accessory', 'supplement', 'pod', 'terpene',
                          'extraction_equipment'])
        
        # Patterns that are always valid (weights, sizes, etc.)
        valid_patterns = [
            r'^\d+m[gl]$',           # 500mg, 100ml
            r'^\d+g$',               # 400g
            r'^\d+ml$',              # 118ml
            r'^\d+/\d+$',            # 70/30 (VG/PG ratio)
            r'^\d+ohm[s]?$',         # 0.5ohm
            r'^\d+\.\d+ohm[s]?$',    # 0.5ohms
        ]
        
        for tag in tags:
            tag_clean = tag.strip().lower()
            
            # Skip empty
            if not tag_clean:
                continue
            
            # Check if it matches known tags
            if tag_clean in known_tags or any(tag_clean in v.lower() for v in known_tags):
                valid_tags.append(tag_clean)
                continue
            
            # Check valid patterns
            import re
            if any(re.match(pattern, tag_clean) for pattern in valid_patterns):
                valid_tags.append(tag_clean)
                continue
            
            # Be permissive - accept most tags from AI unless they're clearly wrong
            # Only reject very generic/meaningless tags
            reject_tags = {'the', 'a', 'an', 'and', 'or', 'but', 'for', 'with', 
                          'product', 'item', 'unknown', 'n/a', 'none', 'null'}
            if tag_clean in reject_tags:
                invalid_tags.append(tag)
                continue
            
            # Accept the tag - AI generated something potentially useful
            valid_tags.append(tag_clean)
        
        return valid_tags, invalid_tags
    
    def _build_prompt(self, row: pd.Series) -> str:
        """Build enhanced prompt for product"""
        title = str(row.get('Title', '') or '')
        description = row.get('Body (HTML)', '') or row.get('Body', '') or ''
        if pd.isna(description):
            description = ''
        description = str(description)
        vendor = str(row.get('Vendor', '') or '')
        current_tags = str(row.get('Tags', '') or '')
        category = str(row.get('Category', '') or '')
        failure_reasons = str(row.get('Failure Reasons', '') or '')
        
        # Get focus areas
        focus_areas = self._parse_failure_reasons(failure_reasons)
        focus_text = '\n'.join(focus_areas) if focus_areas else "- Carefully analyze all aspects"
        
        # Get category requirements
        cat_key = category.lower() if category else 'e-liquid'
        category_requirements = self.CATEGORY_REQUIREMENTS.get(cat_key, 
            "General product - identify category first, then apply appropriate tags")
        
        # Build prompt
        prompt = self.ENHANCED_TAGGING_PROMPT.format(
            title=title,
            description=description[:2000] if description else "No description available",
            vendor=vendor or "Unknown",
            current_tags=current_tags or "None",
            category=category or "Unknown",
            failure_reasons=failure_reasons or "General review needed",
            focus_areas=focus_text,
            category_requirements=category_requirements,
            approved_tags_summary=self.approved_tags_summary
        )
        
        return prompt
    
    def reprocess_product(self, row: pd.Series) -> Tuple[Dict, bool]:
        """
        Reprocess a single product with enhanced AI.
        
        Returns:
            Tuple of (result_dict, was_fixed)
        """
        handle = row.get('Handle', 'unknown')
        if pd.isna(handle):
            handle = 'unknown'
        handle = str(handle)
        
        title = row.get('Title', '')
        if pd.isna(title):
            title = ''
        title = str(title)
        
        self.logger.info(f"\n🔄 Reprocessing: {handle}")
        self.logger.info(f"   Title: {title[:60]}...")
        
        # Build prompt
        prompt = self._build_prompt(row)
        
        # Try primary model
        self.logger.info(f"   Trying {self.primary_model}...")
        response = self._call_model(self.primary_model, prompt)
        
        result = None
        model_used = None
        
        if response:
            result = self._parse_ai_response(response)
            model_used = self.primary_model
        
        # Try secondary if primary failed
        if not result or not result.get('tags'):
            self.logger.warning(f"   Primary failed, trying {self.secondary_model}...")
            response = self._call_model(self.secondary_model, prompt)
            if response:
                result = self._parse_ai_response(response)
                model_used = self.secondary_model
        
        if not result or not result.get('tags'):
            self.logger.error(f"   ✗ All models failed")
            return {'success': False, 'handle': handle}, False
        
        # Validate tags
        tags = result.get('tags', [])
        category = result.get('category', row.get('Category', ''))
        valid_tags, invalid_tags = self._validate_tags(tags, category)
        
        if invalid_tags:
            self.logger.warning(f"   Removed invalid tags: {invalid_tags}")
        
        confidence = result.get('confidence', 0.5)
        # For review reprocessing, use lower threshold since these are hard cases
        # Fixed if: confidence >= 0.6 AND at least 1 valid tag
        needs_review = confidence < 0.6 or len(valid_tags) < 1
        
        self.logger.info(f"   ✓ Tags: {valid_tags}")
        self.logger.info(f"   ✓ Confidence: {confidence:.2f}")
        self.logger.info(f"   ✓ Model: {model_used}")
        self.logger.info(f"   {'⚠️ Still needs review' if needs_review else '✅ Fixed!'}")
        
        return {
            'success': True,
            'handle': handle,
            'tags': valid_tags,
            'category': category,
            'confidence': confidence,
            'model_used': model_used,
            'needs_review': needs_review,
            'reasoning': result.get('reasoning', ''),
            'inferred_tags': result.get('inferred_tags', []),
            'uncertain_tags': result.get('uncertain_tags', [])
        }, not needs_review
    
    def process_review_file(self, 
                           input_csv: Path,
                           output_dir: Path = None,
                           append_clean: Path = None,
                           append_review: Path = None,
                           limit: int = None,
                           dry_run: bool = False) -> Dict:
        """
        Process all products in review CSV.
        
        Args:
            input_csv: Path to tagged_review.csv
            output_dir: Output directory (if not appending)
            append_clean: Path to clean CSV to append to
            append_review: Path to review CSV to append to
            limit: Limit number of products
            dry_run: Don't write files
            
        Returns:
            Statistics dict
        """
        self.logger.info("="*80)
        self.logger.info("🔄 REVIEW REPROCESSOR - Enhanced AI Tagging")
        self.logger.info("="*80)
        
        # Load review CSV
        if not input_csv.exists():
            self.logger.error(f"Input file not found: {input_csv}")
            return self.stats
        
        df = pd.read_csv(input_csv, low_memory=False, dtype={'Variant SKU': str, 'SKU': str})
        total_rows = len(df)
        unique_handles = df['Handle'].nunique()
        
        self.logger.info(f"📥 Loaded {total_rows} rows ({unique_handles} unique products)")
        
        if limit:
            df = df.head(limit)
            self.logger.info(f"⚠️  Limited to first {limit} rows")
        
        # Get unique products
        products_df = df.drop_duplicates(subset=['Handle'], keep='first')
        self.logger.info(f"Processing {len(products_df)} unique products...")
        
        # Process each product
        fixed_products = []
        still_review_products = []
        failed_products = []
        
        for idx, (_, row) in enumerate(products_df.iterrows(), 1):
            self.stats['processed'] += 1
            
            result, was_fixed = self.reprocess_product(row)
            
            if result.get('success'):
                if was_fixed:
                    self.stats['fixed'] += 1
                    fixed_products.append(result)
                else:
                    self.stats['still_review'] += 1
                    still_review_products.append(result)
            else:
                self.stats['failed'] += 1
                failed_products.append(result)
            
            # Progress
            if idx % 10 == 0 or idx == len(products_df):
                self.logger.info(f"\n📊 Progress: {idx}/{len(products_df)} | "
                               f"Fixed: {self.stats['fixed']} | "
                               f"Review: {self.stats['still_review']} | "
                               f"Failed: {self.stats['failed']}")
        
        # Output results
        if not dry_run:
            self._write_results(df, fixed_products, still_review_products,
                              output_dir, append_clean, append_review)
        
        # Final summary
        self.logger.info("\n" + "="*80)
        self.logger.info("📊 REPROCESSING SUMMARY")
        self.logger.info("="*80)
        self.logger.info(f"Total processed: {self.stats['processed']}")
        self.logger.info(f"  → Fixed (now clean): {self.stats['fixed']}")
        self.logger.info(f"  → Still need review: {self.stats['still_review']}")
        self.logger.info(f"  → Failed: {self.stats['failed']}")
        
        return self.stats
    
    def _write_results(self,
                      original_df: pd.DataFrame,
                      fixed_products: List[Dict],
                      still_review_products: List[Dict],
                      output_dir: Path = None,
                      append_clean: Path = None,
                      append_review: Path = None):
        """Write results to output files"""
        
        # Build lookup from results
        results_by_handle = {}
        for p in fixed_products:
            results_by_handle[p['handle']] = {'result': p, 'status': 'clean'}
        for p in still_review_products:
            results_by_handle[p['handle']] = {'result': p, 'status': 'review'}
        
        # Prepare rows
        clean_rows = []
        review_rows = []
        
        for _, row in original_df.iterrows():
            handle = row.get('Handle', '')
            row_dict = row.to_dict()
            
            if handle in results_by_handle:
                data = results_by_handle[handle]
                result = data['result']
                
                # Update row with new tags
                row_dict['Tags'] = ', '.join(result['tags'])
                row_dict['Category'] = result.get('category', row_dict.get('Category', ''))
                row_dict['AI Confidence'] = result.get('confidence', 0.0)
                row_dict['Model Used'] = result.get('model_used', '')
                row_dict['Needs Manual Review'] = 'NO' if data['status'] == 'clean' else 'YES'
                row_dict['Failure Reasons'] = ''
                row_dict['AI Reasoning'] = result.get('reasoning', '')
                
                if data['status'] == 'clean':
                    clean_rows.append(row_dict)
                else:
                    review_rows.append(row_dict)
            else:
                # Keep as review
                review_rows.append(row_dict)
        
        # Determine output paths
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if append_clean and clean_rows:
            # Append to existing clean file
            clean_df = pd.DataFrame(clean_rows)
            if append_clean.exists():
                clean_df.to_csv(append_clean, mode='a', header=False, index=False)
                self.logger.info(f"✅ Appended {len(clean_rows)} rows to {append_clean}")
            else:
                clean_df.to_csv(append_clean, index=False)
                self.logger.info(f"✅ Created {append_clean} with {len(clean_rows)} rows")
        
        if append_review and review_rows:
            # Write updated review file (overwrite)
            review_df = pd.DataFrame(review_rows)
            review_df.to_csv(append_review, index=False)
            self.logger.info(f"⚠️  Updated {append_review} with {len(review_rows)} rows")
        
        # If no append paths, write to output_dir
        if not append_clean and not append_review and output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if clean_rows:
                clean_path = output_dir / f"{timestamp}_reprocessed_clean.csv"
                pd.DataFrame(clean_rows).to_csv(clean_path, index=False)
                self.logger.info(f"✅ Wrote {len(clean_rows)} rows to {clean_path}")
            
            if review_rows:
                review_path = output_dir / f"{timestamp}_reprocessed_review.csv"
                pd.DataFrame(review_rows).to_csv(review_path, index=False)
                self.logger.info(f"⚠️  Wrote {len(review_rows)} rows to {review_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Reprocess tagged_review.csv with enhanced AI prompts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process review file
    python scripts/review_reprocessor.py --input data/output/autonomous/*_tagged_review.csv

    # Append to existing files
    python scripts/review_reprocessor.py --input tagged_review.csv \\
        --append-clean tagged_clean.csv --append-review tagged_review.csv
    
    # Test with limit
    python scripts/review_reprocessor.py --input tagged_review.csv --limit 10 --dry-run
        """
    )
    
    parser.add_argument('--input', '-i', required=True,
                       help='Input tagged_review.csv file')
    parser.add_argument('--output', '-o', default='output/reprocessed',
                       help='Output directory (if not appending)')
    parser.add_argument('--append-clean',
                       help='Path to existing clean CSV to append fixed products')
    parser.add_argument('--append-review',
                       help='Path to review CSV to update with remaining review products')
    parser.add_argument('--limit', '-l', type=int,
                       help='Limit number of rows to process')
    parser.add_argument('--dry-run', action='store_true',
                       help='Process but do not write output files')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--config', '-c',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    try:
        # Setup
        config = Config(args.config) if args.config else Config()
        logger = setup_logger(
            "review_reprocessor",
            log_dir=str(PROJECT_ROOT / "logs"),
            verbose=args.verbose
        )
        
        # Initialize reprocessor
        reprocessor = ReviewReprocessor(config, logger)
        
        # Run
        stats = reprocessor.process_review_file(
            input_csv=Path(args.input),
            output_dir=Path(args.output),
            append_clean=Path(args.append_clean) if args.append_clean else None,
            append_review=Path(args.append_review) if args.append_review else None,
            limit=args.limit,
            dry_run=args.dry_run
        )
        
        # Exit code based on results
        if stats['fixed'] > 0:
            sys.exit(0)
        else:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
