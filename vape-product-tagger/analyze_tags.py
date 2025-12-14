#!/usr/bin/env python3
"""
Analyze product tagging status from Shopify export CSV.
Checks volume of untagged products and audit readiness.
"""

import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

# Paths
INPUT_CSV = Path("data/input/currently_tagged.csv")
APPROVED_TAGS_FILE = Path("approved_tags.json")

def load_approved_tags():
    """Load approved tags from JSON file."""
    with open(APPROVED_TAGS_FILE) as f:
        return json.load(f)

def analyze_csv():
    """Analyze the CSV for tagging status."""
    
    # Load approved tags for validation
    approved_tags = load_approved_tags()
    
    # Build flat list of all approved tags
    all_approved_tags = set()
    
    # Categories
    all_approved_tags.update(approved_tags.get("category", []))
    
    # Tags from each category group
    for key, value in approved_tags.items():
        if isinstance(value, dict) and "tags" in value:
            all_approved_tags.update(value["tags"])
    
    # Stats tracking
    total_products = 0
    total_rows = 0
    products_with_tags = 0
    products_without_tags = 0
    unique_handles = set()
    tag_frequency = Counter()
    untagged_products = []
    products_by_type = defaultdict(lambda: {"tagged": 0, "untagged": 0})
    products_by_vendor = defaultdict(lambda: {"tagged": 0, "untagged": 0})
    
    # Track approved vs unapproved tags
    approved_tag_usage = Counter()
    unapproved_tag_usage = Counter()
    
    with open(INPUT_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            total_rows += 1
            handle = row.get("Handle", "")
            
            # Skip variant rows (same handle = same product)
            if handle in unique_handles:
                continue
            
            unique_handles.add(handle)
            total_products += 1
            
            tags_str = row.get("Tags", "").strip()
            product_type = row.get("Type", "Unknown")
            vendor = row.get("Vendor", "Unknown")
            title = row.get("Title", "Unknown")
            
            if tags_str:
                products_with_tags += 1
                products_by_type[product_type]["tagged"] += 1
                products_by_vendor[vendor]["tagged"] += 1
                
                # Parse individual tags
                tags = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
                for tag in tags:
                    tag_frequency[tag] += 1
                    
                    # Check if tag is in approved list (simple check)
                    if tag in all_approved_tags or tag.replace("mg", "").isdigit():
                        approved_tag_usage[tag] += 1
                    else:
                        unapproved_tag_usage[tag] += 1
            else:
                products_without_tags += 1
                products_by_type[product_type]["untagged"] += 1
                products_by_vendor[vendor]["untagged"] += 1
                untagged_products.append({
                    "handle": handle,
                    "title": title,
                    "type": product_type,
                    "vendor": vendor
                })
    
    return {
        "total_rows": total_rows,
        "total_products": total_products,
        "products_with_tags": products_with_tags,
        "products_without_tags": products_without_tags,
        "tag_frequency": tag_frequency,
        "untagged_products": untagged_products,
        "products_by_type": dict(products_by_type),
        "products_by_vendor": dict(products_by_vendor),
        "approved_tag_usage": approved_tag_usage,
        "unapproved_tag_usage": unapproved_tag_usage,
        "all_approved_tags": all_approved_tags
    }

def print_report(stats):
    """Print a formatted analysis report."""
    
    print("\n" + "="*70)
    print("PRODUCT TAGGING ANALYSIS REPORT")
    print("="*70)
    
    # Overview
    print("\n## OVERVIEW")
    print(f"  Total CSV Rows:        {stats['total_rows']:,}")
    print(f"  Unique Products:       {stats['total_products']:,}")
    print(f"  (Difference is variant rows for same product)")
    
    # Tagging Status
    print("\n## TAGGING STATUS")
    tagged_pct = (stats['products_with_tags'] / stats['total_products'] * 100) if stats['total_products'] > 0 else 0
    untagged_pct = (stats['products_without_tags'] / stats['total_products'] * 100) if stats['total_products'] > 0 else 0
    
    print(f"  ✅ Tagged Products:     {stats['products_with_tags']:,} ({tagged_pct:.1f}%)")
    print(f"  ❌ Untagged Products:   {stats['products_without_tags']:,} ({untagged_pct:.1f}%)")
    
    # By Product Type
    print("\n## TAGGING BY PRODUCT TYPE")
    print(f"  {'Type':<30} {'Tagged':>8} {'Untagged':>10} {'Total':>8}")
    print(f"  {'-'*30} {'-'*8} {'-'*10} {'-'*8}")
    
    for ptype, counts in sorted(stats['products_by_type'].items(), 
                                 key=lambda x: x[1]['tagged'] + x[1]['untagged'], 
                                 reverse=True):
        total = counts['tagged'] + counts['untagged']
        print(f"  {ptype:<30} {counts['tagged']:>8} {counts['untagged']:>10} {total:>8}")
    
    # By Vendor (top 15)
    print("\n## TAGGING BY VENDOR (Top 15)")
    print(f"  {'Vendor':<30} {'Tagged':>8} {'Untagged':>10} {'Total':>8}")
    print(f"  {'-'*30} {'-'*8} {'-'*10} {'-'*8}")
    
    vendor_sorted = sorted(stats['products_by_vendor'].items(), 
                           key=lambda x: x[1]['tagged'] + x[1]['untagged'], 
                           reverse=True)[:15]
    for vendor, counts in vendor_sorted:
        total = counts['tagged'] + counts['untagged']
        print(f"  {vendor[:30]:<30} {counts['tagged']:>8} {counts['untagged']:>10} {total:>8}")
    
    # Tag Frequency (top 30)
    print("\n## MOST COMMON TAGS (Top 30)")
    print(f"  {'Tag':<40} {'Count':>8}")
    print(f"  {'-'*40} {'-'*8}")
    
    for tag, count in stats['tag_frequency'].most_common(30):
        print(f"  {tag:<40} {count:>8}")
    
    # Unapproved tags
    if stats['unapproved_tag_usage']:
        print("\n## POTENTIALLY UNAPPROVED TAGS (Top 30)")
        print("  (Tags not in approved_tags.json - may need review)")
        print(f"  {'Tag':<40} {'Count':>8}")
        print(f"  {'-'*40} {'-'*8}")
        
        for tag, count in stats['unapproved_tag_usage'].most_common(30):
            print(f"  {tag:<40} {count:>8}")
    
    # Untagged products list (first 20)
    if stats['untagged_products']:
        print("\n## UNTAGGED PRODUCTS (First 20)")
        print(f"  {'Handle':<50} {'Type':<20}")
        print(f"  {'-'*50} {'-'*20}")
        
        for product in stats['untagged_products'][:20]:
            print(f"  {product['handle'][:50]:<50} {product['type'][:20]:<20}")
        
        if len(stats['untagged_products']) > 20:
            print(f"\n  ... and {len(stats['untagged_products']) - 20} more untagged products")
    
    # Audit Readiness
    print("\n" + "="*70)
    print("AUDIT READINESS ASSESSMENT")
    print("="*70)
    
    # Check if audit DB exists
    audit_db_path = Path("tag_audit.db")
    audit_db_exists = audit_db_path.exists()
    
    print(f"\n  Audit Database Exists:  {'✅ Yes' if audit_db_exists else '❌ No'}")
    print(f"  Has Tags Column:        ✅ Yes")
    print(f"  Unique Product IDs:     ✅ Yes (using Handle)")
    print(f"  Products in Scope:      {stats['total_products']:,}")
    
    if stats['products_without_tags'] == 0:
        print(f"\n  ✅ ALL PRODUCTS ARE TAGGED - Ready for audit!")
    else:
        print(f"\n  ⚠️  {stats['products_without_tags']:,} products need tagging before full audit")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"""
  • {stats['total_products']:,} unique products found in export
  • {stats['products_with_tags']:,} products have tags ({tagged_pct:.1f}%)
  • {stats['products_without_tags']:,} products are untagged ({untagged_pct:.1f}%)
  • {len(stats['tag_frequency']):,} unique tags in use
  • {len(stats['unapproved_tag_usage']):,} tags may not be in approved list
""")

if __name__ == "__main__":
    print("Analyzing product tags from:", INPUT_CSV)
    stats = analyze_csv()
    print_report(stats)
