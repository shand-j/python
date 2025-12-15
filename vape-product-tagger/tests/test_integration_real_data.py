"""
Integration tests using real product data from data/input/products.csv
Tests the tagging system against actual Shopify product exports
"""

import sys
import csv
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import ControlledTagger


def load_sample_products(csv_path, limit=50):
    """Load sample products from CSV file"""
    products = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                # Only process rows with valid handles
                if row.get('Handle') and row['Handle'].strip():
                    products.append(row)
    except FileNotFoundError:
        return []
    return products


def test_integration_products_csv_exists():
    """Verify the products.csv file exists"""
    csv_path = Path(__file__).parent.parent / 'data' / 'input' / 'products.csv'
    assert csv_path.exists(), f"Products CSV not found at: {csv_path}"


def test_integration_sample_products_basic_tagging():
    """Test basic tagging on sample products from real data
    
    Note: Shopify CSVs have variant rows where only first row has title.
    We test 300 rows to get ~100+ unique products for statistical significance.
    """
    csv_path = Path(__file__).parent.parent / 'data' / 'input' / 'products.csv'
    
    if not csv_path.exists():
        # Skip test if file not available
        return
    
    products = load_sample_products(csv_path, limit=300)
    
    if not products:
        # Skip if no products loaded
        return
    
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    tagged_count = 0
    valid_products_count = 0
    category_counts = {}
    
    for product in products:
        handle = product.get('Handle', '')
        title = product.get('Title', '')
        description = product.get('Body (HTML)', '')
        
        if not handle or not title:
            continue
        
        valid_products_count += 1
        
        rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
        
        # Determine if product has a valid category
        has_category = forced or any(tag in [
            'e-liquid', 'CBD', 'disposable', 'pod', 'coil', 'tank', 
            'device', 'pod_system', 'accessory', 'nicotine_pouches',
            'box_mod', 'terpene', 'supplement', 'extraction_equipment'
        ] for tag in rule_tags)
        
        if has_category:
            tagged_count += 1
            
            # Count categories
            category = forced if forced else next((tag for tag in rule_tags if tag in [
                'e-liquid', 'CBD', 'disposable', 'pod', 'coil', 'tank', 
                'device', 'pod_system', 'accessory', 'nicotine_pouches',
                'box_mod', 'terpene', 'supplement', 'extraction_equipment'
            ]), None)
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1
    
    # Should successfully tag most products with high accuracy
    tag_rate = tagged_count / valid_products_count if valid_products_count else 0
    assert tag_rate > 0.9, f"Should tag >90% of products, got {tag_rate:.1%} ({tagged_count}/{valid_products_count})"
    
    # Should detect multiple categories
    assert len(category_counts) >= 2, \
        f"Should detect multiple categories, got: {list(category_counts.keys())}"


def test_integration_cbd_products():
    """Test CBD product detection in real data"""
    csv_path = Path(__file__).parent.parent / 'data' / 'input' / 'products.csv'
    
    if not csv_path.exists():
        return
    
    products = load_sample_products(csv_path, limit=100)
    
    if not products:
        return
    
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    cbd_products = []
    
    for product in products:
        handle = product.get('Handle', '')
        title = product.get('Title', '')
        description = product.get('Body (HTML)', '')
        
        # Look for CBD in title/handle
        if 'cbd' in handle.lower() or 'cbd' in title.lower():
            rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
            
            if forced == 'CBD' or 'CBD' in rule_tags:
                cbd_products.append({
                    'handle': handle,
                    'title': title,
                    'tags': rule_tags,
                    'forced': forced
                })
    
    # Should detect CBD products if they exist in data
    # This is an informational test - validates detection works on real data


def test_integration_nicotine_range_validation():
    """Test that nicotine values in real data are within valid range"""
    csv_path = Path(__file__).parent.parent / 'data' / 'input' / 'products.csv'
    
    if not csv_path.exists():
        return
    
    products = load_sample_products(csv_path, limit=100)
    
    if not products:
        return
    
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    invalid_nic_tags = []
    
    for product in products:
        handle = product.get('Handle', '')
        title = product.get('Title', '')
        description = product.get('Body (HTML)', '')
        
        rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
        
        # Check nicotine tags are within valid range
        for tag in rule_tags:
            if tag.endswith('mg'):
                try:
                    # Extract numeric value
                    value = float(tag.replace('mg', ''))
                    
                    # Check if it's a nicotine value (0-20mg) vs CBD (>20mg)
                    if forced != 'CBD' and 'CBD' not in rule_tags:
                        # Should be nicotine range
                        if value > 20:
                            invalid_nic_tags.append({
                                'handle': handle,
                                'tag': tag,
                                'value': value
                            })
                except ValueError:
                    pass
    
    # Should not have any invalid nicotine values
    assert len(invalid_nic_tags) == 0, \
        f"Found {len(invalid_nic_tags)} invalid nicotine tags: {invalid_nic_tags[:5]}"


def test_integration_category_distribution():
    """Analyze category distribution in real data"""
    csv_path = Path(__file__).parent.parent / 'data' / 'input' / 'products.csv'
    
    if not csv_path.exists():
        return
    
    products = load_sample_products(csv_path, limit=200)
    
    if not products:
        return
    
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    category_stats = {
        'total_products': 0,
        'tagged_products': 0,
        'untagged_products': 0,
        'categories': {}
    }
    
    for product in products:
        handle = product.get('Handle', '')
        title = product.get('Title', '')
        description = product.get('Body (HTML)', '')
        
        if not handle or not title:
            continue
        
        category_stats['total_products'] += 1
        
        rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
        
        if rule_tags or forced:
            category_stats['tagged_products'] += 1
            
            category = forced if forced else (
                next((tag for tag in rule_tags if tag in [
                    'e-liquid', 'CBD', 'disposable', 'pod', 'coil', 'tank', 
                    'device', 'pod_system', 'accessory', 'nicotine_pouches',
                    'box_mod', 'terpene', 'supplement', 'extraction_equipment'
                ]), None)
            )
            
            if category:
                category_stats['categories'][category] = \
                    category_stats['categories'].get(category, 0) + 1
        else:
            category_stats['untagged_products'] += 1
    
    # Informational: print category distribution
    # This helps validate the tagger works across diverse real products
    total = category_stats['total_products']
    if total > 0:
        tag_rate = category_stats['tagged_products'] / total
        # Should tag at least 90% of real products
        assert tag_rate > 0.9, \
            f"Tag rate too low: {tag_rate:.1%} ({category_stats['tagged_products']}/{total})"


def test_integration_e_liquid_with_strength():
    """Test e-liquid products have appropriate strength tags"""
    csv_path = Path(__file__).parent.parent / 'data' / 'input' / 'products.csv'
    
    if not csv_path.exists():
        return
    
    products = load_sample_products(csv_path, limit=100)
    
    if not products:
        return
    
    ct = ControlledTagger(config_file=None, no_ai=True, verbose=False)
    
    eliquid_stats = {
        'total': 0,
        'with_strength': 0,
        'with_ratio': 0,
        'with_size': 0
    }
    
    for product in products:
        handle = product.get('Handle', '')
        title = product.get('Title', '')
        description = product.get('Body (HTML)', '')
        
        rule_tags, forced = ct.get_rule_based_tags(handle, title, description)
        
        if forced == 'e-liquid' or 'e-liquid' in rule_tags:
            eliquid_stats['total'] += 1
            
            # Check for nicotine strength
            if any(tag.endswith('mg') for tag in rule_tags):
                eliquid_stats['with_strength'] += 1
            
            # Check for VG/PG ratio
            if any('/' in tag for tag in rule_tags):
                eliquid_stats['with_ratio'] += 1
            
            # Check for bottle size
            if any(tag in ['10ml', '50ml', '100ml', 'shortfill'] for tag in rule_tags):
                eliquid_stats['with_size'] += 1
    
    # If we found e-liquids, many should have key attributes
    if eliquid_stats['total'] > 5:
        strength_rate = eliquid_stats['with_strength'] / eliquid_stats['total']
        # At least 40% should have strength tags (some may be nic-free)
        assert strength_rate > 0.4, \
            f"E-liquids should have strength tags: {strength_rate:.1%}"
