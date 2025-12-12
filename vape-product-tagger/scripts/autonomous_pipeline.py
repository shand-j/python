#!/usr/bin/env python3
"""
Autonomous AI Tagging Pipeline
================================
Self-improving product tagging pipeline that:
1. Tags products with AI cascade
2. Validates and tracks accuracy
3. Reviews low-confidence tags
4. Iteratively improves until 90%+ accuracy
5. Exports clean Shopify CSV

Supports cleanup mode to re-process only untagged products and append to existing outputs.

Designed for continuous operation on Vast.ai infrastructure.
"""

import argparse
import sys
import time
import json
import sqlite3
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config import Config
from modules.logger import setup_logger
from modules.product_tagger import ProductTagger
from modules.shopify_handler import ShopifyHandler
from modules.ollama_processor import OllamaProcessor
from modules.tag_validator import TagValidator
from scripts.tag_audit_db import TagAuditDB


class AutonomousPipeline:
    """Orchestrates autonomous tagging with continuous improvement"""
    
    def __init__(self, config_path: str = None, verbose: bool = False):
        """
        Initialize autonomous pipeline
        
        Args:
            config_path: Path to config file
            verbose: Enable verbose logging
        """
        self.config = Config(config_path)
        self.logger = setup_logger(
            name='autonomous_pipeline',
            log_dir=str(self.config.logs_dir),
            level=self.config.log_level,
            verbose=verbose
        )
        
        # Initialize components
        self.ollama = None
        self.tagger = None
        self.shopify_handler = None
        self.validator = None
        self.audit_db = None
        
        # Performance tracking
        self.accuracy_target = 0.90  # 90% target
        self.max_iterations = 3  # Max review/retry cycles
        self.current_iteration = 0
        
    def initialize(self, use_ai: bool = True):
        """Initialize all pipeline components"""
        self.logger.info("="*80)
        self.logger.info("🚀 Autonomous AI Tagging Pipeline - Initializing")
        self.logger.info("="*80)
        
        # Initialize AI processor
        if use_ai:
            try:
                self.ollama = OllamaProcessor(self.config, self.logger)
                self.logger.info("✓ AI cascade enabled")
            except Exception as e:
                self.logger.warning(f"AI initialization failed: {e}")
                self.logger.info("Continuing with rule-based only")
                use_ai = False
        
        # Initialize other components
        self.tagger = ProductTagger(self.config, self.logger, self.ollama)
        self.shopify_handler = ShopifyHandler(self.config, self.logger)
        self.validator = TagValidator(
            schema_path=PROJECT_ROOT / "approved_tags.json",
            logger=self.logger
        )
        
        self.logger.info("✓ All components initialized")
        return use_ai
    
    def calculate_accuracy_metrics(self, products: List[Dict]) -> Dict:
        """
        Calculate comprehensive accuracy metrics
        
        Args:
            products: List of tagged products
            
        Returns:
            Dict with accuracy metrics
        """
        total = len(products)
        if total == 0:
            return {'overall_accuracy': 0.0, 'clean_count': 0, 'review_count': 0, 'untagged_count': 0, 'tagging_rate': 0.0}
        
        clean_count = len([p for p in products if p.get('tags') and not p.get('needs_manual_review')])
        review_count = len([p for p in products if p.get('tags') and p.get('needs_manual_review')])
        untagged_count = len([p for p in products if not p.get('tags')])
        tagged_count = clean_count + review_count
        
        # Calculate confidence distribution
        confidences = [p.get('confidence_scores', {}).get('ai_confidence', 0.0) for p in products]
        confidences = [c for c in confidences if c and c > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Calculate category coverage
        categories = {}
        for p in products:
            cat = p.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {'total': 0, 'clean': 0, 'review': 0, 'untagged': 0}
            categories[cat]['total'] += 1
            if p.get('tags') and not p.get('needs_manual_review'):
                categories[cat]['clean'] += 1
            elif p.get('tags') and p.get('needs_manual_review'):
                categories[cat]['review'] += 1
            else:
                categories[cat]['untagged'] += 1
        
        metrics = {
            'total_products': total,
            'clean_count': clean_count,
            'review_count': review_count,
            'untagged_count': untagged_count,
            'tagged_count': tagged_count,
            'overall_accuracy': clean_count / total,  # Clean rate (target: 90%)
            'tagging_rate': tagged_count / total,     # Any tags rate
            'avg_confidence': avg_confidence,
            'categories': categories
        }
        
        return metrics
    
    def review_and_retry_low_confidence(self, products: List[Dict], audit_db: TagAuditDB, run_id: str) -> List[Dict]:
        """
        Review products needing manual review and attempt to improve them
        
        Args:
            products: List of products
            audit_db: Audit database
            run_id: Current run ID
            
        Returns:
            List of improved products
        """
        needs_review = [p for p in products if p.get('needs_manual_review')]
        
        if not needs_review:
            self.logger.info("✓ No products need review")
            return products
        
        self.logger.info(f"🔍 Reviewing {len(needs_review)} low-confidence products...")
        
        improved_products = []
        for product in products:
            if not product.get('needs_manual_review'):
                improved_products.append(product)
                continue
            
            # Try to improve with third opinion or rule-based reinforcement
            try:
                # Re-tag with adjusted parameters
                improved = self.tagger.tag_product(
                    product,
                    use_ai=True,
                    force_third_opinion=True  # Force third opinion for review items
                )
                
                # Check if improved
                if improved.get('ai_confidence', 0) > product.get('ai_confidence', 0):
                    self.logger.debug(f"Improved confidence for {product.get('handle')}")
                    improved_products.append(improved)
                    
                    # Update audit DB
                    audit_db.save_product_tagging(run_id, improved)
                else:
                    improved_products.append(product)
                    
            except Exception as e:
                self.logger.warning(f"Failed to improve {product.get('handle')}: {e}")
                improved_products.append(product)
        
        return improved_products
    
    def run_tagging_cycle(self, 
                          input_csv: Path, 
                          output_dir: Path,
                          use_ai: bool = True,
                          limit: int = None,
                          iteration: int = 0) -> Tuple[List[Dict], Dict]:
        """
        Run a single tagging cycle
        
        Args:
            input_csv: Input CSV path
            output_dir: Output directory
            use_ai: Enable AI tagging
            limit: Limit processing
            iteration: Current iteration number
            
        Returns:
            Tuple of (tagged_products, metrics)
        """
        self.logger.info("="*80)
        self.logger.info(f"🏷️  Tagging Cycle {iteration + 1}/{self.max_iterations}")
        self.logger.info("="*80)
        
        # Initialize audit DB
        audit_db_path = output_dir / f'audit_iteration_{iteration}.db'
        audit_db = TagAuditDB(str(audit_db_path), thread_safe=True)
        
        run_id = audit_db.start_run(config={
            'use_ai': use_ai,
            'limit': limit,
            'iteration': iteration,
            'input': str(input_csv),
            'timestamp': datetime.now().isoformat()
        })
        
        # Import products
        self.logger.info(f"📥 Importing products from: {input_csv}")
        products = self.shopify_handler.import_from_csv(str(input_csv))
        
        if limit:
            products = products[:limit]
            self.logger.info(f"⚠️  Limited to {limit} products")
        
        total = len(products)
        self.logger.info(f"✓ Processing {total} products")
        
        # Tag products
        tagged_products = []
        start_time = time.time()
        
        for idx, product in enumerate(products, 1):
            try:
                enhanced = self.tagger.tag_product(product, use_ai=use_ai)
                tagged_products.append(enhanced)
                
                # Save to audit DB
                audit_db.save_product_tagging(run_id, enhanced)
                
                # Progress
                if idx % 10 == 0 or idx == total:
                    elapsed = time.time() - start_time
                    rate = idx / elapsed if elapsed > 0 else 0
                    eta = (total - idx) / rate if rate > 0 else 0
                    self.logger.info(
                        f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | "
                        f"Rate: {rate:.1f}/s | ETA: {eta:.0f}s"
                    )
            
            except Exception as e:
                self.logger.error(f"Failed to tag {product.get('handle')}: {e}")
                continue
        
        # Calculate metrics
        metrics = self.calculate_accuracy_metrics(tagged_products)
        
        # Complete run
        audit_db.complete_run(run_id)
        audit_db.close()
        
        self.logger.info(f"✓ Cycle completed in {time.time() - start_time:.1f}s")
        
        return tagged_products, metrics
    
    def run_autonomous(self,
                       input_csv: Path,
                       output_dir: Path,
                       use_ai: bool = True,
                       limit: int = None,
                       inventory_csv: Path = None) -> int:
        """
        Run autonomous pipeline with continuous improvement
        
        Args:
            input_csv: Input CSV path
            output_dir: Output directory
            use_ai: Enable AI tagging
            limit: Limit processing
            inventory_csv: Optional inventory CSV for SKU lookup
            
        Returns:
            Exit code (0 = success)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Store inventory path for export
        self.inventory_csv = inventory_csv
        
        # Initial tagging cycle
        products, metrics = self.run_tagging_cycle(
            input_csv, output_dir, use_ai, limit, iteration=0
        )
        
        self.logger.info("="*80)
        self.logger.info("📊 Initial Results")
        self.logger.info("="*80)
        self.logger.info(f"Overall Accuracy: {metrics['overall_accuracy']*100:.1f}%")
        self.logger.info(f"Clean: {metrics['clean_count']} ({metrics['clean_count']/metrics['total_products']*100:.1f}%)")
        self.logger.info(f"Review: {metrics['review_count']} ({metrics['review_count']/metrics['total_products']*100:.1f}%)")
        self.logger.info(f"Untagged: {metrics['untagged_count']} ({metrics['untagged_count']/metrics['total_products']*100:.1f}%)")
        
        # Check if target met
        iteration = 0  # Initialize iteration counter
        if metrics['overall_accuracy'] >= self.accuracy_target:
            self.logger.info(f"✅ Target accuracy {self.accuracy_target*100}% achieved!")
        else:
            self.logger.info(f"⚠️  Target accuracy {self.accuracy_target*100}% not met, initiating improvement cycles...")
            
            # Improvement iterations
            iteration = 1
            while iteration < self.max_iterations and metrics['overall_accuracy'] < self.accuracy_target:
                self.logger.info(f"\n🔄 Improvement Iteration {iteration + 1}")
                
                # Review and retry
                audit_db_path = output_dir / f'audit_iteration_{iteration - 1}.db'
                audit_db = TagAuditDB(str(audit_db_path), thread_safe=True)
                
                run_id = f"iteration_{iteration}_improvement"
                products = self.review_and_retry_low_confidence(products, audit_db, run_id)
                audit_db.close()
                
                # Recalculate metrics
                metrics = self.calculate_accuracy_metrics(products)
                
                self.logger.info(f"Accuracy after iteration {iteration + 1}: {metrics['overall_accuracy']*100:.1f}%")
                
                if metrics['overall_accuracy'] >= self.accuracy_target:
                    self.logger.info(f"✅ Target accuracy achieved after {iteration + 1} iterations!")
                    break
                
                iteration += 1
        
        # Export final results - use new method that preserves all variant rows
        self.logger.info("="*80)
        self.logger.info("📤 Exporting Final Results")
        self.logger.info("="*80)
        
        output_paths = self.shopify_handler.export_with_original_variants(
            products, 
            str(input_csv), 
            str(output_dir),
            inventory_csv_path=str(self.inventory_csv) if self.inventory_csv else None
        )
        
        for tier, path in output_paths.items():
            self.logger.info(f"✓ {tier}: {path}")
        
        # Final summary
        self.logger.info("="*80)
        self.logger.info("🎯 Final Summary")
        self.logger.info("="*80)
        self.logger.info(f"Target Accuracy: {self.accuracy_target*100:.0f}%")
        self.logger.info(f"Achieved Accuracy: {metrics['overall_accuracy']*100:.1f}% (clean products)")
        self.logger.info(f"Tagging Rate: {metrics.get('tagging_rate', 0)*100:.1f}% (any tags)")
        self.logger.info(f"Avg Confidence: {metrics.get('avg_confidence', 0)*100:.1f}%")
        self.logger.info(f"Total Iterations: {iteration + 1}")
        self.logger.info(f"Products: {metrics['clean_count']} clean, {metrics['review_count']} review, {metrics['untagged_count']} untagged / {metrics['total_products']} total")
        
        # Category breakdown
        self.logger.info("\nCategory Breakdown:")
        for cat, stats in metrics['categories'].items():
            accuracy = stats['clean'] / stats['total'] if stats['total'] > 0 else 0
            self.logger.info(f"  {cat}: {accuracy*100:.1f}% clean ({stats['clean']}/{stats['total']})")
        
        if metrics['overall_accuracy'] >= self.accuracy_target:
            self.logger.info("\n✅ PIPELINE SUCCEEDED - Target accuracy achieved!")
            return 0
        else:
            self.logger.warning(f"\n⚠️  PIPELINE INCOMPLETE - Target accuracy not achieved after {self.max_iterations} iterations")
            return 1

    def run_cleanup(self,
                    untagged_csv: Path,
                    clean_csv: Path,
                    review_csv: Path,
                    use_ai: bool = True,
                    limit: int = None) -> int:
        """
        Run cleanup mode: process untagged products and append to existing outputs.
        
        This avoids re-processing the entire dataset when only a few products need fixing.
        
        Args:
            untagged_csv: Path to previously untagged CSV
            clean_csv: Path to existing clean CSV (will be appended)
            review_csv: Path to existing review CSV (will be appended)
            use_ai: Enable AI tagging
            limit: Limit processing
            
        Returns:
            Exit code (0 = success)
        """
        self.logger.info("="*80)
        self.logger.info("🧹 CLEANUP MODE - Processing Previously Untagged Products")
        self.logger.info("="*80)
        
        # Validate input files exist
        if not untagged_csv.exists():
            self.logger.error(f"Untagged CSV not found: {untagged_csv}")
            return 1
        
        if not clean_csv.exists():
            self.logger.warning(f"Clean CSV not found, will create new: {clean_csv}")
        
        if not review_csv.exists():
            self.logger.warning(f"Review CSV not found, will create new: {review_csv}")
        
        # Import untagged products
        self.logger.info(f"📥 Importing untagged products from: {untagged_csv}")
        products = self.shopify_handler.import_from_csv(str(untagged_csv))
        
        if limit:
            products = products[:limit]
            self.logger.info(f"⚠️  Limited to {limit} products")
        
        total = len(products)
        self.logger.info(f"✓ Processing {total} previously untagged products")
        
        # Tag products
        tagged_products = []
        start_time = time.time()
        
        for idx, product in enumerate(products, 1):
            try:
                enhanced = self.tagger.tag_product(product, use_ai=use_ai)
                tagged_products.append(enhanced)
                
                # Progress
                if idx % 10 == 0 or idx == total:
                    elapsed = time.time() - start_time
                    rate = idx / elapsed if elapsed > 0 else 0
                    eta = (total - idx) / rate if rate > 0 else 0
                    self.logger.info(
                        f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | "
                        f"Rate: {rate:.1f}/s | ETA: {eta:.0f}s"
                    )
            
            except Exception as e:
                self.logger.error(f"Failed to tag {product.get('handle')}: {e}")
                continue
        
        # Calculate metrics
        metrics = self.calculate_accuracy_metrics(tagged_products)
        
        self.logger.info(f"✓ Tagging completed in {time.time() - start_time:.1f}s")
        self.logger.info(f"Results: {metrics['clean_count']} clean, {metrics['review_count']} review, {metrics['untagged_count']} still untagged")
        
        # Append results to existing files
        self.logger.info("="*80)
        self.logger.info("📤 Appending Results to Existing Files")
        self.logger.info("="*80)
        
        appended_stats = self._append_cleanup_results(
            tagged_products, 
            untagged_csv,
            clean_csv,
            review_csv
        )
        
        # Final summary
        self.logger.info("="*80)
        self.logger.info("🎯 Cleanup Summary")
        self.logger.info("="*80)
        self.logger.info(f"Products processed: {total}")
        self.logger.info(f"  → Now clean: {appended_stats['clean_appended']} (appended to {clean_csv.name})")
        self.logger.info(f"  → Now review: {appended_stats['review_appended']} (appended to {review_csv.name})")
        self.logger.info(f"  → Still untagged: {appended_stats['still_untagged']}")
        
        if appended_stats['still_untagged'] > 0:
            self.logger.info(f"  → Updated untagged file: {appended_stats['untagged_path']}")
        
        return 0 if appended_stats['still_untagged'] == 0 else 1

    def _append_cleanup_results(self,
                                 tagged_products: List[Dict],
                                 untagged_csv: Path,
                                 clean_csv: Path,
                                 review_csv: Path) -> Dict:
        """
        Append newly tagged products to existing clean/review files.
        
        Args:
            tagged_products: List of newly tagged products
            untagged_csv: Original untagged CSV (for structure)
            clean_csv: Clean CSV to append to
            review_csv: Review CSV to append to
            
        Returns:
            Dict with stats about what was appended
        """
        import pandas as pd
        from modules.taxonomy import VapeTaxonomy
        import re
        
        stats = {
            'clean_appended': 0,
            'review_appended': 0,
            'still_untagged': 0,
            'untagged_path': None
        }
        
        # Build lookup from tagged products
        products_by_handle = {}
        for product in tagged_products:
            handle = product.get('handle', '')
            if handle:
                products_by_handle[handle] = product
        
        # Read original untagged CSV to get all variant rows
        untagged_df = pd.read_csv(untagged_csv, low_memory=False, dtype={'Variant SKU': str, 'SKU': str})
        self.logger.info(f"Untagged CSV has {len(untagged_df)} rows ({untagged_df['Handle'].nunique()} unique products)")
        
        # Get column structure from existing clean CSV (or untagged if clean doesn't exist)
        if clean_csv.exists():
            existing_clean_df = pd.read_csv(clean_csv, nrows=0)
            all_columns = list(existing_clean_df.columns)
        else:
            all_columns = list(untagged_df.columns)
        
        # Ensure metadata columns exist
        metadata_cols = [
            'Needs Manual Review', 'AI Confidence', 'Model Used',
            'Failure Reasons', 'Secondary Flavors', 'Category',
            'Rule Based Tags', 'AI Suggested Tags'
        ]
        for col in metadata_cols:
            if col not in all_columns:
                all_columns.append(col)
        
        # Prepare rows for each category
        clean_rows = []
        review_rows = []
        still_untagged_rows = []
        
        # Flavor and VG ratio tags for variant-level replacement
        ALL_FLAVOR_TAGS = {'fruity', 'ice', 'tobacco', 'desserts/bakery', 'beverages', 
                          'nuts', 'spices_&_herbs', 'cereal', 'unflavoured', 'candy/sweets'}
        
        for _, row in untagged_df.iterrows():
            handle = row.get('Handle', '')
            row_dict = row.to_dict()
            
            # Ensure all columns exist
            for col in all_columns:
                if col not in row_dict:
                    row_dict[col] = ''
            
            if handle in products_by_handle:
                product = products_by_handle[handle]
                
                # Get tags and metadata
                base_tags = product.get('tags', [])
                category = product.get('category', '')
                needs_review = product.get('needs_manual_review', False)
                confidence_scores = product.get('confidence_scores', {})
                failure_reasons = product.get('failure_reasons', [])
                tag_breakdown = product.get('tag_breakdown', {})
                secondary_flavors = tag_breakdown.get('secondary_flavors', [])
                
                # Apply variant-level flavor detection if applicable
                if category in ['e-liquid', 'disposable', 'pod', 'nicotine_pouches']:
                    option1_value = str(row.get('Option1 Value', '')).strip()
                    if option1_value and option1_value.lower() not in ['default title', 'nan', '']:
                        variant_flavors = VapeTaxonomy.detect_flavor_types(option1_value)
                        if variant_flavors:
                            variant_tags = [t for t in base_tags if t not in ALL_FLAVOR_TAGS]
                            variant_tags.extend(variant_flavors)
                            base_tags = list(set(variant_tags))
                
                # Apply tags
                row_dict['Tags'] = ', '.join(base_tags) if base_tags else ''
                row_dict['Category'] = category
                row_dict['Needs Manual Review'] = 'YES' if needs_review else 'NO'
                row_dict['AI Confidence'] = confidence_scores.get('ai_confidence', 0.0)
                row_dict['Model Used'] = product.get('model_used', 'rule-based')
                row_dict['Failure Reasons'] = '; '.join(failure_reasons) if failure_reasons else ''
                row_dict['Secondary Flavors'] = ', '.join(secondary_flavors) if secondary_flavors else ''
                row_dict['Rule Based Tags'] = ', '.join(tag_breakdown.get('rule_based_tags', []))
                row_dict['AI Suggested Tags'] = ', '.join(tag_breakdown.get('ai_suggested_tags', []))
                
                # Categorize
                if not base_tags:
                    still_untagged_rows.append(row_dict)
                elif needs_review:
                    review_rows.append(row_dict)
                else:
                    clean_rows.append(row_dict)
            else:
                # Product not processed - keep as untagged
                still_untagged_rows.append(row_dict)
        
        # Append to clean CSV
        if clean_rows:
            clean_df = pd.DataFrame(clean_rows)
            # Reorder columns to match existing
            clean_df = clean_df.reindex(columns=all_columns, fill_value='')
            
            if clean_csv.exists():
                clean_df.to_csv(clean_csv, mode='a', header=False, index=False)
                self.logger.info(f"✅ Appended {len(clean_rows)} rows to {clean_csv}")
            else:
                clean_df.to_csv(clean_csv, index=False)
                self.logger.info(f"✅ Created {clean_csv} with {len(clean_rows)} rows")
            
            stats['clean_appended'] = len(clean_rows)
        
        # Append to review CSV
        if review_rows:
            review_df = pd.DataFrame(review_rows)
            review_df = review_df.reindex(columns=all_columns, fill_value='')
            
            if review_csv.exists():
                review_df.to_csv(review_csv, mode='a', header=False, index=False)
                self.logger.info(f"⚠️  Appended {len(review_rows)} rows to {review_csv}")
            else:
                review_df.to_csv(review_csv, index=False)
                self.logger.info(f"⚠️  Created {review_csv} with {len(review_rows)} rows")
            
            stats['review_appended'] = len(review_rows)
        
        # Update untagged CSV with remaining untagged
        if still_untagged_rows:
            untagged_df_new = pd.DataFrame(still_untagged_rows)
            untagged_df_new = untagged_df_new.reindex(columns=all_columns, fill_value='')
            
            # Write to new untagged file (overwrite)
            new_untagged_path = untagged_csv.parent / f"{untagged_csv.stem}_remaining{untagged_csv.suffix}"
            untagged_df_new.to_csv(new_untagged_path, index=False)
            self.logger.info(f"❌ {len(still_untagged_rows)} rows still untagged → {new_untagged_path}")
            
            stats['still_untagged'] = len(still_untagged_rows)
            stats['untagged_path'] = str(new_untagged_path)
        else:
            self.logger.info("🎉 All previously untagged products now tagged!")
            stats['still_untagged'] = 0
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description='Autonomous AI Tagging Pipeline with Continuous Improvement',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run autonomous pipeline
  python scripts/autonomous_pipeline.py --input products.csv --output output/

  # With accuracy target and max iterations
  python scripts/autonomous_pipeline.py --input products.csv --output output/ --target 0.92 --max-iterations 5

  # Test with limited dataset
  python scripts/autonomous_pipeline.py --input products.csv --output output/ --limit 100

  # Rule-based only
  python scripts/autonomous_pipeline.py --input products.csv --no-ai

  # Verbose logging
  python scripts/autonomous_pipeline.py --input products.csv --verbose

  # CLEANUP MODE - Process previously untagged products and append to existing outputs
  python scripts/autonomous_pipeline.py --cleanup \\
    --input data/output/autonomous/20251212_193757_untagged.csv \\
    --append-clean data/output/autonomous/20251212_193757_tagged_clean.csv \\
    --append-review data/output/autonomous/20251212_193757_tagged_review.csv
        """
    )
    
    parser.add_argument('--input', '-i', required=True,
                       help='Input CSV file path')
    parser.add_argument('--output', '-o', default='output',
                       help='Output directory (default: output/)')
    parser.add_argument('--inventory', '-inv',
                       help='Inventory CSV file path for SKU lookup')
    parser.add_argument('--config', '-c',
                       help='Configuration file path')
    parser.add_argument('--no-ai', action='store_true',
                       help='Disable AI tagging (rule-based only)')
    parser.add_argument('--limit', '-l', type=int,
                       help='Limit processing to first N products')
    parser.add_argument('--target', '-t', type=float, default=0.90,
                       help='Target accuracy (default: 0.90)')
    parser.add_argument('--max-iterations', '-m', type=int, default=3,
                       help='Maximum improvement iterations (default: 3)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    # Cleanup mode arguments
    parser.add_argument('--cleanup', action='store_true',
                       help='Run in cleanup mode: process untagged and append to existing outputs')
    parser.add_argument('--append-clean',
                       help='Path to existing tagged_clean.csv to append to (cleanup mode)')
    parser.add_argument('--append-review',
                       help='Path to existing tagged_review.csv to append to (cleanup mode)')
    
    args = parser.parse_args()
    
    try:
        # Initialize pipeline
        pipeline = AutonomousPipeline(
            config_path=args.config,
            verbose=args.verbose
        )
        
        # Set parameters
        pipeline.accuracy_target = args.target
        pipeline.max_iterations = args.max_iterations
        
        # Initialize components
        use_ai = pipeline.initialize(use_ai=not args.no_ai)
        
        # Check for cleanup mode
        if args.cleanup:
            # Validate cleanup arguments
            if not args.append_clean or not args.append_review:
                parser.error("Cleanup mode requires --append-clean and --append-review arguments")
            
            # Run cleanup mode
            exit_code = pipeline.run_cleanup(
                untagged_csv=Path(args.input),
                clean_csv=Path(args.append_clean),
                review_csv=Path(args.append_review),
                use_ai=use_ai,
                limit=args.limit
            )
        else:
            # Run autonomous pipeline
            exit_code = pipeline.run_autonomous(
                input_csv=Path(args.input),
                output_dir=Path(args.output),
                use_ai=use_ai,
                limit=args.limit,
                inventory_csv=Path(args.inventory) if args.inventory else None
            )
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
