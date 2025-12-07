#!/usr/bin/env python3
"""
Master Pipeline Orchestrator
Coordinates the complete tagging pipeline with validation, progress tracking, and 3-tier output
"""
import argparse
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config import Config
from modules.logger import setup_logger
from modules.product_tagger import ProductTagger
from modules.shopify_handler import ShopifyHandler
from modules.ollama_processor import OllamaProcessor
from scripts.tag_audit_db import TagAuditDB


def validate_input_csv(csv_path: Path, logger) -> bool:
    """Validate input CSV file exists and has required columns"""
    if not csv_path.exists():
        logger.error(f"Input CSV not found: {csv_path}")
        return False
    
    import pandas as pd
    try:
        df = pd.read_csv(csv_path)
        required_columns = ['Handle', 'Title']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            logger.error(f"Missing required columns: {missing}")
            return False
        
        logger.info(f"✓ Input CSV validated: {len(df)} products found")
        return True
    except Exception as e:
        logger.error(f"Failed to validate CSV: {e}")
        return False


def run_pipeline(args):
    """Execute the complete tagging pipeline"""
    
    # Load configuration
    config_file = args.config if args.config else None
    config = Config(config_file)
    
    # Setup logger
    logger = setup_logger(
        name='pipeline',
        log_dir=str(config.logs_dir),
        level=config.log_level,
        verbose=args.verbose
    )
    
    logger.info("="*70)
    logger.info("🚀 Vape Product Tagger Pipeline - Starting")
    logger.info("="*70)
    
    # Validate input
    input_path = Path(args.input)
    if not validate_input_csv(input_path, logger):
        return 1
    
    # Initialize output directory
    output_dir = Path(args.output_dir) if args.output_dir else config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"✓ Output directory: {output_dir}")
    
    # Initialize audit database
    audit_db_path = args.audit_db if args.audit_db else output_dir / 'audit.db'
    audit_db = TagAuditDB(str(audit_db_path), thread_safe=True)
    
    # Check for resume
    run_id = None
    if args.run_id:
        run_id = args.run_id
        status = audit_db.get_run_status(run_id)
        if status:
            logger.info(f"✓ Resuming run: {run_id} (status: {status})")
        else:
            logger.warning(f"Run ID {run_id} not found, starting new run")
            run_id = None
    
    if not run_id:
        run_id = audit_db.start_run(config={
            'use_ai': not args.no_ai,
            'limit': args.limit,
            'input': str(input_path),
            'output_dir': str(output_dir)
        })
        logger.info(f"✓ Started new run: {run_id}")
    
    # Initialize components
    use_ai = not args.no_ai
    ollama = None
    if use_ai:
        try:
            ollama = OllamaProcessor(config, logger)
            logger.info("✓ AI tagging enabled")
        except Exception as e:
            logger.warning(f"Failed to initialize AI processor: {e}")
            logger.info("Continuing with rule-based tagging only")
            use_ai = False
    else:
        logger.info("✓ Rule-based tagging only (--no-ai)")
    
    tagger = ProductTagger(config, logger, ollama)
    shopify_handler = ShopifyHandler(config, logger)
    
    # Import products
    logger.info(f"📥 Importing products from: {input_path}")
    products = shopify_handler.import_from_csv(str(input_path))
    
    if args.limit:
        products = products[:args.limit]
        logger.info(f"⚠️  Limited to first {args.limit} products")
    
    total = len(products)
    logger.info(f"✓ {total} products to process")
    
    # Process products with progress tracking
    logger.info("="*70)
    logger.info("🏷️  Tagging products...")
    logger.info("="*70)
    
    tagged_products = []
    start_time = time.time()
    
    for idx, product in enumerate(products, 1):
        try:
            # Tag product
            enhanced = tagger.tag_product(product, use_ai=use_ai)
            tagged_products.append(enhanced)
            
            # Save to audit DB
            audit_db.save_product_tagging(run_id, enhanced)
            
            # Progress update
            if idx % 10 == 0 or idx == total:
                elapsed = time.time() - start_time
                rate = idx / elapsed
                eta = (total - idx) / rate if rate > 0 else 0
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | "
                          f"Rate: {rate:.1f} products/s | ETA: {eta:.0f}s")
        
        except Exception as e:
            logger.error(f"Failed to tag product {product.get('handle', 'unknown')}: {e}")
            continue
    
    elapsed_total = time.time() - start_time
    logger.info(f"✓ Completed in {elapsed_total:.1f}s ({total/elapsed_total:.1f} products/s)")
    
    # Generate 3-tier output
    logger.info("="*70)
    logger.info("📊 Generating output files...")
    logger.info("="*70)
    
    output_paths = shopify_handler.export_to_csv_three_tier(tagged_products, str(output_dir))
    
    for tier, path in output_paths.items():
        logger.info(f"✓ {tier}: {path}")
    
    # Generate summary report
    clean_count = len([p for p in tagged_products if p.get('tags') and not p.get('needs_manual_review')])
    review_count = len([p for p in tagged_products if p.get('tags') and p.get('needs_manual_review')])
    untagged_count = len([p for p in tagged_products if not p.get('tags')])
    
    logger.info("="*70)
    logger.info("📈 Summary Report")
    logger.info("="*70)
    logger.info(f"Total products processed: {total}")
    logger.info(f"✅ Clean (ready for import): {clean_count} ({clean_count/total*100:.1f}%)")
    logger.info(f"⚠️  Needs review: {review_count} ({review_count/total*100:.1f}%)")
    logger.info(f"❌ Untagged: {untagged_count} ({untagged_count/total*100:.1f}%)")
    
    # Model usage stats
    if use_ai:
        model_counts = {}
        for p in tagged_products:
            model = p.get('model_used', 'none')
            model_counts[model] = model_counts.get(model, 0) + 1
        
        if model_counts:
            logger.info("\nModel usage:")
            for model, count in sorted(model_counts.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {model}: {count} ({count/total*100:.1f}%)")
    
    # Complete run
    audit_db.complete_run(run_id)
    logger.info(f"\n✓ Run completed: {run_id}")
    logger.info(f"✓ Audit database: {audit_db_path}")
    
    # Prompt for review interface
    if args.auto_review and review_count > 0:
        logger.info("\n" + "="*70)
        logger.info(f"⚠️  {review_count} products need manual review")
        logger.info("To launch review interface:")
        logger.info(f"  python scripts/review_interface.py --audit-db {audit_db_path}")
        logger.info("="*70)
    
    audit_db.close()
    
    logger.info("\n🎉 Pipeline completed successfully!")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Master pipeline orchestrator for vape product tagging',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python scripts/run_pipeline.py --input products.csv --output-dir output/

  # Limit processing for testing
  python scripts/run_pipeline.py --input products.csv --output-dir output/ --limit 100

  # Rule-based only (no AI)
  python scripts/run_pipeline.py --input products.csv --no-ai

  # Resume previous run
  python scripts/run_pipeline.py --run-id <uuid> --input products.csv

  # With parallel processing
  python scripts/run_pipeline.py --input products.csv --workers 8
        """
    )
    
    parser.add_argument('--input', '-i', required=True,
                       help='Input CSV file path')
    parser.add_argument('--output-dir', '-o', default='output',
                       help='Output directory (default: output/)')
    parser.add_argument('--config', '-c',
                       help='Configuration file path')
    parser.add_argument('--no-ai', action='store_true',
                       help='Disable AI tagging (rule-based only)')
    parser.add_argument('--limit', '-l', type=int,
                       help='Limit processing to first N products')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--run-id',
                       help='Resume previous run by ID')
    parser.add_argument('--audit-db',
                       help='Audit database path (default: output/audit.db)')
    parser.add_argument('--workers', '-w', type=int, default=1,
                       help='Number of parallel workers (default: 1)')
    parser.add_argument('--auto-review', action='store_true',
                       help='Prompt to launch review interface after completion')
    
    args = parser.parse_args()
    
    try:
        sys.exit(run_pipeline(args))
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
