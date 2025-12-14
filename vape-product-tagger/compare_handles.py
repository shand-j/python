#!/usr/bin/env python3
"""
Compare handles, SKUs, and titles between imported and exported files.
"""

import csv

# Load final_import.csv
imported = {}
with open('data/output/final_import.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        handle = row.get('Handle', '').strip()
        sku = row.get('Variant SKU', '').strip()
        title = row.get('Title', '').strip()
        if handle:
            if handle not in imported:
                imported[handle] = {'skus': set(), 'title': title}
            if sku:
                imported[handle]['skus'].add(sku)

# Load currently_tagged.csv
exported = {}
with open('data/input/currently_tagged.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        handle = row.get('Handle', '').strip()
        sku = row.get('Variant SKU', '').strip()
        title = row.get('Title', '').strip()
        if handle:
            if handle not in exported:
                exported[handle] = {'skus': set(), 'title': title}
            if sku:
                exported[handle]['skus'].add(sku)

print(f"Products in import: {len(imported)}")
print(f"Products in export: {len(exported)}")

common = set(imported.keys()) & set(exported.keys())
print(f"Common handles: {len(common)}")

# Check for title mismatches
title_mismatches = []
for handle in common:
    imp_title = imported[handle]['title']
    exp_title = exported[handle]['title']
    if imp_title != exp_title:
        title_mismatches.append({
            'handle': handle,
            'imported': imp_title,
            'exported': exp_title
        })

print(f"\n{'='*70}")
print(f"TITLE MISMATCHES: {len(title_mismatches)}")
print(f"{'='*70}")
if title_mismatches:
    for m in title_mismatches[:20]:
        print(f"\nHandle: {m['handle']}")
        print(f"  Import: {m['imported'][:80]}")
        print(f"  Export: {m['exported'][:80]}")
    if len(title_mismatches) > 20:
        print(f"\n... and {len(title_mismatches) - 20} more")

# Check for SKU mismatches
sku_mismatches = []
for handle in common:
    imp_skus = imported[handle]['skus']
    exp_skus = exported[handle]['skus']
    if imp_skus != exp_skus:
        sku_mismatches.append({
            'handle': handle,
            'imported': imp_skus,
            'exported': exp_skus,
            'only_import': imp_skus - exp_skus,
            'only_export': exp_skus - imp_skus
        })

print(f"\n{'='*70}")
print(f"SKU MISMATCHES: {len(sku_mismatches)}")
print(f"{'='*70}")
if sku_mismatches:
    for m in sku_mismatches[:20]:
        print(f"\nHandle: {m['handle']}")
        print(f"  Import SKUs: {m['imported']}")
        print(f"  Export SKUs: {m['exported']}")
    if len(sku_mismatches) > 20:
        print(f"\n... and {len(sku_mismatches) - 20} more")

# Handles only in one file
only_import = set(imported.keys()) - set(exported.keys())
only_export = set(exported.keys()) - set(imported.keys())

print(f"\n{'='*70}")
print(f"HANDLES ONLY IN IMPORT: {len(only_import)}")
print(f"{'='*70}")
for h in list(only_import)[:10]:
    print(f"  {h}")

print(f"\n{'='*70}")
print(f"HANDLES ONLY IN EXPORT (new products): {len(only_export)}")
print(f"{'='*70}")
for h in list(only_export)[:20]:
    print(f"  {h}")
if len(only_export) > 20:
    print(f"\n... and {len(only_export) - 20} more")

# Summary
print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print(f"  Handle matches:     {len(common)} / {len(imported)} ({100*len(common)/len(imported):.1f}%)")
print(f"  Title mismatches:   {len(title_mismatches)}")
print(f"  SKU mismatches:     {len(sku_mismatches)}")
print(f"  Only in import:     {len(only_import)}")
print(f"  Only in export:     {len(only_export)}")
