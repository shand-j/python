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

Designed for continuous operation on Vast.ai infrastructure.
"""

import argparse
import sys
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

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
            return {'overall_accuracy': 0.0, 'clean_count': 0, 'review_count': 0, 'untagged_count': 0}
        
        clean_count = len([p for p in products if p.get('tags') and not p.get('needs_manual_review')])
        review_count = len([p for p in products if p.get('tags') and p.get('needs_manual_review')])
        untagged_count = len([p for p in products if not p.get('tags')])
        
        # Calculate confidence distribution
        confidences = [p.get('ai_confidence', 0.0) for p in products if p.get('ai_confidence')]
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
            'overall_accuracy': clean_count / total,
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
                       limit: int = None) -> int:
        """
        Run autonomous pipeline with continuous improvement
        
        Args:
            input_csv: Input CSV path
            output_dir: Output directory
            use_ai: Enable AI tagging
            limit: Limit processing
            
        Returns:
            Exit code (0 = success)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # Export final results
        self.logger.info("="*80)
        self.logger.info("📤 Exporting Final Results")
        self.logger.info("="*80)
        
        output_paths = self.shopify_handler.export_to_csv_three_tier(products, str(output_dir))
        
        for tier, path in output_paths.items():
            self.logger.info(f"✓ {tier}: {path}")
        
        # Final summary
        self.logger.info("="*80)
        self.logger.info("🎯 Final Summary")
        self.logger.info("="*80)
        self.logger.info(f"Target Accuracy: {self.accuracy_target*100}%")
        self.logger.info(f"Achieved Accuracy: {metrics['overall_accuracy']*100:.1f}%")
        self.logger.info(f"Total Iterations: {iteration + 1}")
        self.logger.info(f"Clean Products: {metrics['clean_count']}/{metrics['total_products']}")
        
        # Category breakdown
        self.logger.info("\nCategory Breakdown:")
        for cat, stats in metrics['categories'].items():
            accuracy = stats['clean'] / stats['total'] if stats['total'] > 0 else 0
            self.logger.info(f"  {cat}: {accuracy*100:.1f}% ({stats['clean']}/{stats['total']} clean)")
        
        if metrics['overall_accuracy'] >= self.accuracy_target:
            self.logger.info("\n✅ PIPELINE SUCCEEDED - Target accuracy achieved!")
            return 0
        else:
            self.logger.warning(f"\n⚠️  PIPELINE INCOMPLETE - Target accuracy not achieved after {self.max_iterations} iterations")
            return 1


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
        """
    )
    
    parser.add_argument('--input', '-i', required=True,
                       help='Input CSV file path')
    parser.add_argument('--output', '-o', default='output',
                       help='Output directory (default: output/)')
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
        
        # Run autonomous pipeline
        exit_code = pipeline.run_autonomous(
            input_csv=Path(args.input),
            output_dir=Path(args.output),
            use_ai=use_ai,
            limit=args.limit
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
