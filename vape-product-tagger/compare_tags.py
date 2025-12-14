#!/usr/bin/env python3
"""
Compare tags between imported file and exported file to find discrepancies.
"""

import csv
from collections import defaultdict

# Load final_import.csv (the imported tags)
imported_tags = {}
with open('data/output/final_import.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        handle = row.get('Handle', '').strip()
        tags = row.get('Tags', '').strip()
        if handle:
            # Normalize tags: lowercase, sorted, strip whitespace
            tag_set = frozenset(t.strip().lower() for t in tags.split(',') if t.strip())
            imported_tags[handle] = tag_set

# Load currently_tagged.csv (the export)
exported_tags = {}
seen_handles = set()
with open('data/input/currently_tagged.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        handle = row.get('Handle', '').strip()
        if handle in seen_handles:
            continue
        seen_handles.add(handle)
        tags = row.get('Tags', '').strip()
        tag_set = frozenset(t.strip().lower() for t in tags.split(',') if t.strip())
        exported_tags[handle] = tag_set

print(f'Products in final_import.csv: {len(imported_tags)}')
print(f'Products in currently_tagged.csv: {len(exported_tags)}')

# Find matches
common_handles = set(imported_tags.keys()) & set(exported_tags.keys())
print(f'Products in both files: {len(common_handles)}')

# Compare tags
matching = 0
mismatched = []

for handle in common_handles:
    imp_tags = imported_tags[handle]
    exp_tags = exported_tags[handle]
    
    if imp_tags == exp_tags:
        matching += 1
    else:
        mismatched.append({
            'handle': handle,
            'imported': imp_tags,
            'exported': exp_tags,
            'added': exp_tags - imp_tags,
            'removed': imp_tags - exp_tags
        })

# Products in import but not in export
only_in_import = set(imported_tags.keys()) - set(exported_tags.keys())
only_in_export = set(exported_tags.keys()) - set(imported_tags.keys())

print(f'\n{"="*70}')
print('COMPARISON RESULTS')
print(f'{"="*70}')
print(f'Tags MATCH:              {matching} products')
print(f'Tags MISMATCH:           {len(mismatched)} products')
print(f'Only in import:          {len(only_in_import)}')
print(f'Only in export:          {len(only_in_export)}')

# Analyze mismatch patterns
if mismatched:
    print(f'\n{"="*70}')
    print(f'MISMATCH ANALYSIS')
    print(f'{"="*70}')
    
    tags_added_count = 0
    tags_removed_count = 0
    completely_different = 0
    
    for m in mismatched:
        if m['added'] and not m['removed']:
            tags_added_count += 1
        elif m['removed'] and not m['added']:
            tags_removed_count += 1
        else:
            completely_different += 1
    
    print(f'Products with tags ADDED in export:     {tags_added_count}')
    print(f'Products with tags REMOVED in export:   {tags_removed_count}')
    print(f'Products with both added and removed:   {completely_different}')
    
    print(f'\n{"="*70}')
    print(f'FIRST 30 MISMATCHES')
    print(f'{"="*70}')
    
    for m in mismatched[:30]:
        print(f"\nHandle: {m['handle']}")
        print(f"  Imported:  {sorted(m['imported'])}")
        print(f"  Exported:  {sorted(m['exported'])}")
        if m['added']:
            print(f"  ADDED in export:   {sorted(m['added'])}")
        if m['removed']:
            print(f"  REMOVED in export: {sorted(m['removed'])}")

    if len(mismatched) > 30:
        print(f"\n... and {len(mismatched) - 30} more mismatches")

# Summary of what tags were most commonly removed
if mismatched:
    removed_tags = defaultdict(int)
    added_tags = defaultdict(int)
    
    for m in mismatched:
        for tag in m['removed']:
            removed_tags[tag] += 1
        for tag in m['added']:
            added_tags[tag] += 1
    
    if removed_tags:
        print(f'\n{"="*70}')
        print('MOST COMMONLY REMOVED TAGS')
        print(f'{"="*70}')
        for tag, count in sorted(removed_tags.items(), key=lambda x: -x[1])[:20]:
            print(f'  {tag}: {count} products')
    
    if added_tags:
        print(f'\n{"="*70}')
        print('MOST COMMONLY ADDED TAGS')
        print(f'{"="*70}')
        for tag, count in sorted(added_tags.items(), key=lambda x: -x[1])[:20]:
            print(f'  {tag}: {count} products')

if only_in_import:
    print(f'\n{"="*70}')
    print(f'PRODUCTS ONLY IN IMPORT (first 20)')
    print(f'{"="*70}')
    for h in list(only_in_import)[:20]:
        print(f'  {h}')
