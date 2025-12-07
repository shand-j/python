#!/usr/bin/env python3
"""
Prepare Training Data
Export training dataset from audit database for fine-tuning
"""
import argparse
import sys
import csv
import json
from pathlib import Path
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.tag_audit_db import TagAuditDB


def prepare_training_data(audit_db_path: str, output_path: str, min_confidence: float = 0.0,
                          include_human_corrected: bool = False, stratify: bool = True):
    """
    Export training dataset from audit database
    
    Args:
        audit_db_path: Path to audit database
        output_path: Output CSV path
        min_confidence: Minimum AI confidence to include
        include_human_corrected: Include human-corrected products
        stratify: Balance dataset by category
    """
    print("="*70)
    print("📚 Training Data Preparation")
    print("="*70)
    
    audit_db = TagAuditDB(audit_db_path)
    
    # Load all verified products
    print(f"\n📥 Loading products from: {audit_db_path}")
    
    # Get all products from database
    import sqlite3
    conn = audit_db._get_connection()
    cur = conn.cursor()
    
    query = '''
        SELECT handle, title, description, detected_category, 
               final_tags, ai_confidence, human_verified, human_corrected_tags,
               rule_tags, ai_tags
        FROM products
        WHERE 1=1
    '''
    
    conditions = []
    params = []
    
    if min_confidence > 0:
        conditions.append('ai_confidence >= ?')
        params.append(min_confidence)
    
    if include_human_corrected:
        conditions.append('(human_verified = 1 OR ai_confidence >= ?)')
        params.append(min_confidence)
    else:
        conditions.append('ai_confidence >= ?')
        params.append(min_confidence)
    
    if conditions:
        query += ' AND ' + ' AND '.join(conditions)
    
    cur.execute(query, params)
    rows = cur.fetchall()
    
    print(f"✓ Loaded {len(rows)} products")
    
    # Process products
    training_data = []
    category_counts = defaultdict(int)
    
    for row in rows:
        handle, title, description, category, final_tags, confidence, verified, corrected_tags, rule_tags, ai_tags = row
        
        # Parse JSON fields
        try:
            final_tags = json.loads(final_tags) if final_tags else []
            corrected_tags = json.loads(corrected_tags) if corrected_tags else []
            rule_tags = json.loads(rule_tags) if rule_tags else []
            ai_tags = json.loads(ai_tags) if ai_tags else []
        except:
            continue
        
        # Use human-corrected tags if available
        expected_tags = corrected_tags if corrected_tags else final_tags
        
        if not expected_tags:
            continue
        
        # Create input text
        input_text = f"Title: {title}\nDescription: {description[:500]}"
        
        # Create training example
        example = {
            'handle': handle,
            'input_text': input_text,
            'expected_tags': ', '.join(expected_tags),
            'category': category or 'unknown',
            'confidence': confidence or 0.0,
            'human_corrected': 1 if corrected_tags else 0,
            'rule_tags': ', '.join(rule_tags),
            'ai_tags': ', '.join(ai_tags)
        }
        
        training_data.append(example)
        category_counts[category or 'unknown'] += 1
    
    print(f"✓ Prepared {len(training_data)} training examples")
    
    # Category distribution
    print("\n📊 Category distribution:")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count} ({count/len(training_data)*100:.1f}%)")
    
    # Stratify if requested
    if stratify and len(training_data) > 100:
        print("\n⚖️  Stratifying dataset by category...")
        
        # Calculate target per category
        min_per_category = min(category_counts.values())
        max_per_category = max(category_counts.values())
        
        # If imbalanced, sample to balance
        if max_per_category > min_per_category * 2:
            stratified_data = []
            by_category = defaultdict(list)
            
            for example in training_data:
                by_category[example['category']].append(example)
            
            # Sample evenly
            target_per_category = min(min_per_category * 2, max_per_category)
            
            for category, examples in by_category.items():
                import random
                random.seed(42)  # Reproducible
                
                if len(examples) > target_per_category:
                    sampled = random.sample(examples, target_per_category)
                else:
                    sampled = examples
                
                stratified_data.extend(sampled)
            
            print(f"  Stratified to {len(stratified_data)} examples")
            training_data = stratified_data
    
    # Deduplicate by handle
    print("\n🔍 Deduplicating by handle...")
    seen_handles = set()
    deduplicated = []
    
    for example in training_data:
        if example['handle'] not in seen_handles:
            deduplicated.append(example)
            seen_handles.add(example['handle'])
    
    if len(deduplicated) < len(training_data):
        print(f"  Removed {len(training_data) - len(deduplicated)} duplicates")
        training_data = deduplicated
    
    # Export to CSV
    print(f"\n💾 Exporting to: {output_path}")
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['handle', 'input_text', 'expected_tags', 'category', 'confidence', 
                     'human_corrected', 'rule_tags', 'ai_tags']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(training_data)
    
    print(f"✓ Exported {len(training_data)} training examples")
    
    # Generate statistics
    human_corrected_count = sum(1 for ex in training_data if ex['human_corrected'])
    avg_confidence = sum(ex['confidence'] for ex in training_data) / len(training_data) if training_data else 0
    
    print("\n" + "="*70)
    print("📈 Training Data Summary")
    print("="*70)
    print(f"Total examples: {len(training_data)}")
    print(f"Human corrected: {human_corrected_count} ({human_corrected_count/len(training_data)*100:.1f}%)")
    print(f"Average confidence: {avg_confidence:.2f}")
    print(f"Categories: {len(category_counts)}")
    print(f"\nOutput: {output_path}")
    
    audit_db.close()
    
    print("\n✅ Training data preparation complete!")
    print("\n💡 Next steps:")
    print("   1. Review the exported CSV")
    print("   2. Use for fine-tuning with train_tag_model.py")
    print("   3. Deploy trained model for improved accuracy")


def main():
    parser = argparse.ArgumentParser(
        description='Prepare training data from audit database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic export
  python scripts/prepare_training_data.py --audit-db output/audit.db --output training.csv

  # High confidence only
  python scripts/prepare_training_data.py --audit-db output/audit.db --output training.csv --min-confidence 0.9

  # Include human corrections
  python scripts/prepare_training_data.py --audit-db output/audit.db --output training.csv --include-human-corrected

  # With stratification
  python scripts/prepare_training_data.py --audit-db output/audit.db --output training.csv --stratify
        """
    )
    
    parser.add_argument('--audit-db', required=True,
                       help='Path to audit database')
    parser.add_argument('--output', '-o', default='training.csv',
                       help='Output CSV path (default: training.csv)')
    parser.add_argument('--min-confidence', type=float, default=0.0,
                       help='Minimum AI confidence (0.0-1.0, default: 0.0)')
    parser.add_argument('--include-human-corrected', action='store_true',
                       help='Include human-corrected products')
    parser.add_argument('--stratify', action='store_true',
                       help='Balance dataset by category')
    
    args = parser.parse_args()
    
    try:
        prepare_training_data(
            args.audit_db,
            args.output,
            args.min_confidence,
            args.include_human_corrected,
            args.stratify
        )
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
