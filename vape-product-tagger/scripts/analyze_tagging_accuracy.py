#!/usr/bin/env python3
"""
Analyze tagging accuracy on real product data
Identifies untagged products and suggests improvements
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import ControlledTagger


def analyze_products(csv_path, limit=500):
    """Analyze tagging performance on real products"""
    
    print(f"\n{'='*80}")
    print(f"TAGGING ACCURACY ANALYSIS")
    print(f"{'='*80}\n")
    
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    stats = {
        'total': 0,
        'tagged': 0,
        'untagged': 0,
        'categories': defaultdict(int),
        'untagged_examples': [],
        'partial_tags': 0
    }
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                
                handle = row.get('Handle', '').strip()
                title = row.get('Title', '').strip()
                description = row.get('Body (HTML)', '').strip()
                
                if not handle or not title:
                    continue
                
                stats['total'] += 1
                
                rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
                
                # Determine if product is tagged
                has_category = forced or any(tag in [
                    'e-liquid', 'CBD', 'disposable', 'pod', 'coil', 'tank', 
                    'device', 'pod_system', 'accessory', 'nicotine_pouches',
                    'box_mod', 'terpene', 'supplement', 'extraction_equipment'
                ] for tag in rule_tags)
                
                if has_category:
                    stats['tagged'] += 1
                    category = forced if forced else next((tag for tag in rule_tags if tag in [
                        'e-liquid', 'CBD', 'disposable', 'pod', 'coil', 'tank', 
                        'device', 'pod_system', 'accessory', 'nicotine_pouches',
                        'box_mod', 'terpene', 'supplement', 'extraction_equipment'
                    ]), None)
                    if category:
                        stats['categories'][category] += 1
                    
                    # Check if only partially tagged (has category but few other tags)
                    if len(rule_tags) <= 2:
                        stats['partial_tags'] += 1
                else:
                    stats['untagged'] += 1
                    if len(stats['untagged_examples']) < 20:
                        stats['untagged_examples'].append({
                            'handle': handle,
                            'title': title[:80],
                            'description': description[:100] if description else ''
                        })
    
    except FileNotFoundError:
        print(f"Error: File not found: {csv_path}")
        return None
    
    # Print results
    if stats['total'] > 0:
        tag_rate = (stats['tagged'] / stats['total']) * 100
        print(f"Products Analyzed: {stats['total']}")
        print(f"Successfully Tagged: {stats['tagged']} ({tag_rate:.1f}%)")
        print(f"Untagged: {stats['untagged']} ({(stats['untagged']/stats['total'])*100:.1f}%)")
        print(f"Partially Tagged: {stats['partial_tags']} ({(stats['partial_tags']/stats['total'])*100:.1f}%)")
        
        print(f"\n{'='*80}")
        print(f"CATEGORY DISTRIBUTION")
        print(f"{'='*80}\n")
        
        for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
            pct = (count / stats['tagged']) * 100 if stats['tagged'] > 0 else 0
            print(f"  {category:20s}: {count:4d} ({pct:5.1f}%)")
        
        if stats['untagged_examples']:
            print(f"\n{'='*80}")
            print(f"UNTAGGED PRODUCT EXAMPLES")
            print(f"{'='*80}\n")
            
            for i, example in enumerate(stats['untagged_examples'][:10], 1):
                print(f"{i}. Handle: {example['handle']}")
                print(f"   Title: {example['title']}")
                if example['description']:
                    print(f"   Desc: {example['description'][:80]}...")
                print()
        
        print(f"\n{'='*80}")
        print(f"RECOMMENDATIONS FOR >90% TAG RATE")
        print(f"{'='*80}\n")
        
        if tag_rate < 90:
            print("Current issues:")
            if stats['untagged'] > stats['total'] * 0.1:
                print(f"  - {stats['untagged']} products lack category detection")
                print(f"    → Add keywords or patterns for untagged products")
            if stats['partial_tags'] > stats['total'] * 0.2:
                print(f"  - {stats['partial_tags']} products only have basic tags")
                print(f"    → Enhance attribute extraction (strength, size, ratio)")
            print(f"\nTarget: {int(stats['total'] * 0.9)} products tagged (currently {stats['tagged']})")
            print(f"Gap: {int(stats['total'] * 0.9) - stats['tagged']} additional products needed")
        else:
            print(f"✅ Tag rate meets >90% threshold!")
    
    return stats


if __name__ == '__main__':
    csv_path = Path(__file__).parent.parent / 'data' / 'input' / 'products.csv'
    
    # Analyze first 500 products for faster feedback
    analyze_products(csv_path, limit=500)
