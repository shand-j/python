#!/usr/bin/env python3
"""
Analyze import file format and compare with Shopify export format.
Identify potential issues with the import file.
"""

import csv

print("="*70)
print("IMPORT FILE FORMAT ANALYSIS")
print("="*70)

# Check import file structure
with open('data/output/final_import.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    print(f"\n## Import File Headers:")
    for h in headers:
        print(f"  - {h}")
    
    # Check first few rows
    rows = list(reader)
    print(f"\n## Total rows in import: {len(rows)}")
    
    # Check for products with multiple variants (same handle)
    from collections import Counter
    handle_counts = Counter(r['Handle'] for r in rows)
    multi_variant = [(h, c) for h, c in handle_counts.items() if c > 1]
    print(f"## Products with multiple variant rows: {len(multi_variant)}")

print("\n" + "="*70)
print("SHOPIFY EXPORT FILE FORMAT")
print("="*70)

with open('data/input/currently_tagged.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    print(f"\n## Export File Headers (first 20):")
    for h in headers[:20]:
        print(f"  - {h}")
    print(f"  ... and {len(headers) - 20} more columns")

print("\n" + "="*70)
print("CRITICAL FORMAT COMPARISON")
print("="*70)

# Key findings
print("""
## Issue Analysis:

Your IMPORT file has columns:
  - Handle
  - Title  
  - Variant SKU
  - Tags

Shopify's EXPORT file has column:
  - Tags (column 7)

## Potential Problems:

1. **VARIANT ROW ISSUE**: Your import has multiple rows per product (one per variant).
   Shopify may only apply tags from the FIRST row, or may be confused by duplicate handles.

2. **MISSING 'Published' COLUMN**: Shopify import format typically requires a 'Published' 
   column. Without it, products might not update correctly.

3. **TAG FORMAT**: Check if tags need to be without spaces after commas.
""")

# Check for variant rows with different tags
print("\n" + "="*70)
print("CHECKING: Same product with different tags across variants")
print("="*70)

with open('data/output/final_import.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

product_tags = {}
for row in rows:
    handle = row['Handle']
    tags = row.get('Tags', '')
    if handle not in product_tags:
        product_tags[handle] = set()
    product_tags[handle].add(tags)

inconsistent = [(h, tags) for h, tags in product_tags.items() if len(tags) > 1]
print(f"\nProducts with DIFFERENT tags across variant rows: {len(inconsistent)}")

if inconsistent:
    print("\nFirst 10 examples:")
    for h, tags in inconsistent[:10]:
        print(f"\n  Handle: {h}")
        for t in tags:
            print(f"    Tags: {t[:80]}...")

# Check products where tags were lost
print("\n" + "="*70)
print("CROSS-CHECK: Products that lost tags")
print("="*70)

# Load exported (current) tags
exported_tags = {}
with open('data/input/currently_tagged.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    seen = set()
    for row in reader:
        handle = row.get('Handle', '').strip()
        if handle in seen:
            continue
        seen.add(handle)
        exported_tags[handle] = row.get('Tags', '').strip()

# Load imported tags (first variant only)
imported_tags = {}
with open('data/output/final_import.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    seen = set()
    for row in reader:
        handle = row.get('Handle', '').strip()
        if handle in seen:
            continue  # Only first variant
        seen.add(handle)
        imported_tags[handle] = row.get('Tags', '').strip()

# Find products where import had tags but export is empty
lost_tags = []
for handle in imported_tags:
    if handle in exported_tags:
        imp = imported_tags[handle]
        exp = exported_tags[handle]
        if imp and not exp:
            lost_tags.append(handle)

print(f"\nProducts where tags were COMPLETELY LOST: {len(lost_tags)}")
print(f"(Import had tags, export is empty)")

if lost_tags:
    print("\nFirst 20 examples:")
    for h in lost_tags[:20]:
        print(f"  {h}")
        print(f"    Imported tags: {imported_tags[h][:60]}...")
