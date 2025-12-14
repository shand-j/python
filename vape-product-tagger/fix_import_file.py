#!/usr/bin/env python3
"""
Create a corrected import file with one row per product and merged tags.
This fixes the issue where Shopify clears tags when multiple variant rows have different tags.
"""

import csv
from collections import defaultdict
from pathlib import Path

INPUT_FILE = Path('data/output/final_import.csv')
OUTPUT_FILE = Path('data/output/final_import_fixed.csv')

print("="*70)
print("CREATING FIXED IMPORT FILE")
print("="*70)

# Read all rows and merge tags per product
products = defaultdict(lambda: {'title': '', 'vendor': '', 'tags': set()})

with open(INPUT_FILE, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    row_count = 0
    for row in reader:
        row_count += 1
        handle = row.get('Handle', '').strip()
        title = row.get('Title', '').strip()
        tags_str = row.get('Tags', '').strip()
        
        if not handle:
            continue
            
        # Store title from first occurrence
        if not products[handle]['title']:
            products[handle]['title'] = title
        
        # Merge tags from all variants
        if tags_str:
            tags = [t.strip() for t in tags_str.split(',') if t.strip()]
            products[handle]['tags'].update(tags)

# Get vendor from the export file (not in original import)
EXPORT_FILE = Path('data/input/currently_tagged.csv')
with open(EXPORT_FILE, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    seen = set()
    for row in reader:
        handle = row.get('Handle', '').strip()
        if handle in seen:
            continue
        seen.add(handle)
        vendor = row.get('Vendor', '').strip()
        if handle in products and vendor:
            products[handle]['vendor'] = vendor

print(f"\nRead {row_count} rows from input file")
print(f"Found {len(products)} unique products")

# Write the fixed file - one row per product with merged tags
with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Handle', 'Title', 'Vendor', 'Tags'])  # Include Title and Vendor as required by Shopify
    
    for handle, data in sorted(products.items()):
        # Sort tags for consistency
        merged_tags = ', '.join(sorted(data['tags']))
        writer.writerow([handle, data['title'], data['vendor'], merged_tags])

print(f"Wrote {len(products)} rows to {OUTPUT_FILE}")

# Verification
print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

# Compare tag counts
original_tags = defaultdict(set)
with open(INPUT_FILE, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        handle = row.get('Handle', '').strip()
        tags_str = row.get('Tags', '').strip()
        if tags_str:
            tags = [t.strip() for t in tags_str.split(',') if t.strip()]
            original_tags[handle].update(tags)

fixed_tags = {}
with open(OUTPUT_FILE, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        handle = row.get('Handle', '').strip()
        tags_str = row.get('Tags', '').strip()
        tags = set(t.strip() for t in tags_str.split(',') if t.strip())
        fixed_tags[handle] = tags

# Check all tags preserved
all_preserved = True
for handle in original_tags:
    if handle in fixed_tags:
        if original_tags[handle] != fixed_tags[handle]:
            all_preserved = False
            print(f"MISMATCH: {handle}")
            print(f"  Original: {original_tags[handle]}")
            print(f"  Fixed:    {fixed_tags[handle]}")

if all_preserved:
    print("✅ All tags preserved correctly in merged file")

# Sample output
print("\n" + "="*70)
print("SAMPLE OUTPUT (first 10 rows)")
print("="*70)

with open(OUTPUT_FILE, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 10:
            break
        print(f"\nHandle: {row['Handle']}")
        print(f"Title: {row['Title'][:60]}...")
        print(f"Vendor: {row['Vendor']}")
        print(f"Tags: {row['Tags'][:80]}...")

# Create restore-only file for products that lost tags
print("\n" + "="*70)
print("CREATING RESTORE FILE")
print("="*70)

# Load currently exported tags
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

# Find products that need restoration
needs_restore = []
for handle, data in products.items():
    if handle in exported_tags:
        if data['tags'] and not exported_tags[handle]:
            needs_restore.append((handle, data['title'], data['vendor'], ', '.join(sorted(data['tags']))))

# Write restore file
RESTORE_FILE = Path('data/output/restore_tags.csv')
with open(RESTORE_FILE, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Handle', 'Title', 'Vendor', 'Tags'])
    for handle, title, vendor, tags in sorted(needs_restore):
        writer.writerow([handle, title, vendor, tags])

print(f"Products that need tags restored: {len(needs_restore)}")
print(f"Created: {RESTORE_FILE}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"""
Original file:
  - Rows: {row_count}
  - Unique products: {len(products)}
  - Multiple rows per product: {row_count - len(products)}

Fixed file:
  - Rows: {len(products)} (one per product)
  - All variant tags merged per product
  - File: {OUTPUT_FILE}

Import this file to Shopify to update tags without the variant row conflict.
""")
