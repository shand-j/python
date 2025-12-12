#!/usr/bin/env python3
"""
Generate Final Import File
==========================
Merges tagged_clean, tagged_review, and remaining untagged files
into a single import-ready CSV with only Handle, SKU, and Tags columns.

Usage:
    python scripts/generate_import.py \
        --clean data/output/autonomous/20251212_193757_tagged_clean.csv \
        --review data/output/autonomous/20251212_193757_tagged_review.csv \
        --untagged data/output/autonomous/20251212_193757_untagged_updated.csv \
        --output data/output/final_import.csv
    
    # Or use a directory to auto-detect files by timestamp prefix
    python scripts/generate_import.py \
        --dir data/output/autonomous \
        --prefix 20251212_193757
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(line_buffering=True)


def load_and_extract(filepath: Path, source_name: str) -> pd.DataFrame:
    """Load CSV and extract required columns"""
    if not filepath.exists():
        print(f"⚠️  {source_name} not found: {filepath}")
        return pd.DataFrame()
    
    print(f"📥 Loading {source_name}: {filepath}")
    try:
        df = pd.read_csv(filepath, low_memory=False, dtype={'Variant SKU': str, 'SKU': str},
                        on_bad_lines='skip')
    except Exception as e:
        print(f"   ❌ Error loading: {e}")
        return pd.DataFrame()
    
    # Find SKU column (could be 'Variant SKU' or 'SKU')
    sku_col = None
    for col in ['Variant SKU', 'SKU', 'sku']:
        if col in df.columns:
            sku_col = col
            break
    
    if sku_col is None:
        print(f"   ⚠️  No SKU column found in {source_name}")
        sku_col = 'Variant SKU'
        df[sku_col] = ''
    
    # Extract required columns
    result = pd.DataFrame({
        'Handle': df['Handle'],
        'Title': df.get('Title', ''),
        'Variant SKU': df[sku_col],
        'Tags': df.get('Tags', '')
    })
    
    rows = len(result)
    products = result['Handle'].nunique()
    print(f"   ✓ {rows} rows, {products} products")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Generate final import CSV with Handle, SKU, Tags only'
    )
    parser.add_argument('--clean', '-c',
                       help='Path to tagged_clean CSV')
    parser.add_argument('--review', '-r',
                       help='Path to tagged_review CSV')
    parser.add_argument('--untagged', '-u',
                       help='Path to untagged CSV (optional)')
    parser.add_argument('--dir', '-d',
                       help='Directory containing output files')
    parser.add_argument('--prefix', '-p',
                       help='Timestamp prefix to find files (e.g., 20251212_193757)')
    parser.add_argument('--output', '-o', default='final_import.csv',
                       help='Output file path')
    parser.add_argument('--include-untagged', action='store_true',
                       help='Include untagged products (with empty tags)')
    parser.add_argument('--include-review', action='store_true', default=True,
                       help='Include review products (default: True)')
    parser.add_argument('--skip-review', action='store_true',
                       help='Skip review products')
    
    args = parser.parse_args()
    
    # Determine file paths
    clean_path = None
    review_path = None
    untagged_path = None
    
    if args.dir and args.prefix:
        # Auto-detect files by prefix
        dir_path = Path(args.dir)
        prefix = args.prefix
        
        clean_candidates = list(dir_path.glob(f"{prefix}*_tagged_clean.csv"))
        if clean_candidates:
            clean_path = clean_candidates[0]
        
        review_candidates = list(dir_path.glob(f"{prefix}*_tagged_review.csv"))
        if review_candidates:
            review_path = review_candidates[0]
        
        # Try updated untagged first, then remaining, then original
        for pattern in [f"{prefix}*_untagged_updated.csv", 
                       f"{prefix}*_untagged_remaining.csv",
                       f"{prefix}*_untagged.csv"]:
            candidates = list(dir_path.glob(pattern))
            if candidates:
                untagged_path = candidates[0]
                break
    
    # Override with explicit paths
    if args.clean:
        clean_path = Path(args.clean)
    if args.review:
        review_path = Path(args.review)
    if args.untagged:
        untagged_path = Path(args.untagged)
    
    # Validate we have at least clean
    if not clean_path:
        print("❌ No clean CSV specified. Use --clean or --dir with --prefix")
        sys.exit(1)
    
    print("="*60)
    print("📦 GENERATING FINAL IMPORT FILE")
    print("="*60)
    
    # Load files
    dfs = []
    
    # Clean (always include)
    clean_df = load_and_extract(clean_path, "Clean")
    if not clean_df.empty:
        clean_df['Source'] = 'clean'
        dfs.append(clean_df)
    
    # Review (include unless skipped)
    if review_path and not args.skip_review:
        review_df = load_and_extract(review_path, "Review")
        if not review_df.empty:
            review_df['Source'] = 'review'
            dfs.append(review_df)
    
    # Untagged (only if explicitly requested)
    if untagged_path and args.include_untagged:
        untagged_df = load_and_extract(untagged_path, "Untagged")
        if not untagged_df.empty:
            untagged_df['Source'] = 'untagged'
            dfs.append(untagged_df)
    
    if not dfs:
        print("❌ No data loaded")
        sys.exit(1)
    
    # Combine
    print("\n📊 Combining files...")
    combined = pd.concat(dfs, ignore_index=True)
    
    # Remove duplicates (keep first occurrence - clean > review > untagged)
    before_dedup = len(combined)
    combined = combined.drop_duplicates(subset=['Handle', 'Variant SKU'], keep='first')
    after_dedup = len(combined)
    
    if before_dedup != after_dedup:
        print(f"   Removed {before_dedup - after_dedup} duplicate rows")
    
    # Summary by source
    print("\n📊 Summary by source:")
    for source in ['clean', 'review', 'untagged']:
        count = len(combined[combined['Source'] == source])
        if count > 0:
            print(f"   {source}: {count} rows")
    
    # Final output columns (drop Source)
    final_df = combined[['Handle', 'Title', 'Variant SKU', 'Tags']].copy()
    
    # Clean up Tags column
    final_df['Tags'] = final_df['Tags'].fillna('')
    final_df['Title'] = final_df['Title'].fillna('')
    
    # Stats
    total_rows = len(final_df)
    total_products = final_df['Handle'].nunique()
    rows_with_tags = len(final_df[final_df['Tags'].str.len() > 0])
    
    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(output_path, index=False)
    
    print("\n" + "="*60)
    print("✅ FINAL IMPORT FILE GENERATED")
    print("="*60)
    print(f"Output: {output_path}")
    print(f"Total rows: {total_rows}")
    print(f"Total products: {total_products}")
    print(f"Rows with tags: {rows_with_tags}")
    print(f"Rows without tags: {total_rows - rows_with_tags}")
    
    # Preview
    print("\n📋 Preview (first 5 rows):")
    print(final_df.head().to_string(index=False))


if __name__ == '__main__':
    main()
