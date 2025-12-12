#!/usr/bin/env python3
"""
Update Untagged File
====================
Simple script to update an untagged CSV after reprocessing.
Removes products that now have tags in the clean/review files.

Usage:
    python scripts/update_untagged.py \
        --untagged data/output/autonomous/20251212_193757_untagged.csv \
        --clean data/output/autonomous/20251212_193757_tagged_clean.csv \
        --review data/output/autonomous/20251212_193757_tagged_review.csv
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)


def main():
    parser = argparse.ArgumentParser(
        description='Update untagged CSV by removing products now in clean/review files'
    )
    parser.add_argument('--untagged', '-u', required=True,
                       help='Path to untagged CSV to update')
    parser.add_argument('--clean', '-c', required=True,
                       help='Path to tagged_clean CSV')
    parser.add_argument('--review', '-r', required=True,
                       help='Path to tagged_review CSV')
    parser.add_argument('--output', '-o',
                       help='Output path (default: overwrites untagged with _updated suffix)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be removed without writing')
    
    args = parser.parse_args()
    
    # Load files
    untagged_path = Path(args.untagged)
    clean_path = Path(args.clean)
    review_path = Path(args.review)
    
    if not untagged_path.exists():
        print(f"❌ Untagged file not found: {untagged_path}")
        sys.exit(1)
    
    print(f"📥 Loading untagged: {untagged_path}")
    untagged_df = pd.read_csv(untagged_path, low_memory=False, dtype={'Variant SKU': str, 'SKU': str})
    original_count = len(untagged_df)
    original_products = untagged_df['Handle'].nunique()
    print(f"   {original_count} rows, {original_products} unique products")
    
    # Get handles from clean and review files
    tagged_handles = set()
    
    if clean_path.exists():
        print(f"📥 Loading clean: {clean_path}")
        clean_df = pd.read_csv(clean_path, low_memory=False, usecols=['Handle'])
        clean_handles = set(clean_df['Handle'].dropna().unique())
        tagged_handles.update(clean_handles)
        print(f"   {len(clean_handles)} unique products")
    else:
        print(f"⚠️  Clean file not found: {clean_path}")
    
    if review_path.exists():
        print(f"📥 Loading review: {review_path}")
        review_df = pd.read_csv(review_path, low_memory=False, usecols=['Handle'])
        review_handles = set(review_df['Handle'].dropna().unique())
        tagged_handles.update(review_handles)
        print(f"   {len(review_handles)} unique products")
    else:
        print(f"⚠️  Review file not found: {review_path}")
    
    # Find handles to remove
    untagged_handles = set(untagged_df['Handle'].dropna().unique())
    handles_to_remove = untagged_handles & tagged_handles
    
    print(f"\n📊 Analysis:")
    print(f"   Products in untagged: {len(untagged_handles)}")
    print(f"   Products now tagged: {len(handles_to_remove)}")
    print(f"   Products still untagged: {len(untagged_handles) - len(handles_to_remove)}")
    
    if handles_to_remove:
        print(f"\n🗑️  Removing {len(handles_to_remove)} products:")
        for h in list(handles_to_remove)[:10]:
            print(f"      - {h}")
        if len(handles_to_remove) > 10:
            print(f"      ... and {len(handles_to_remove) - 10} more")
    
    if args.dry_run:
        print("\n⚠️  DRY RUN - no files modified")
        sys.exit(0)
    
    # Filter out tagged products
    updated_df = untagged_df[~untagged_df['Handle'].isin(handles_to_remove)]
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = untagged_path.parent / f"{untagged_path.stem}_updated{untagged_path.suffix}"
    
    # Write updated file
    updated_df.to_csv(output_path, index=False)
    
    final_count = len(updated_df)
    final_products = updated_df['Handle'].nunique()
    
    print(f"\n✅ Updated untagged file written: {output_path}")
    print(f"   Before: {original_count} rows, {original_products} products")
    print(f"   After:  {final_count} rows, {final_products} products")
    print(f"   Removed: {original_count - final_count} rows, {original_products - final_products} products")


if __name__ == '__main__':
    main()
