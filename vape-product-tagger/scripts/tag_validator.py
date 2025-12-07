#!/usr/bin/env python3
"""
Tag Validation and Consistency Analysis Tool

Analyzes tagging results from audit database to validate:
- Adherence to approved tag vocabulary
- Consistency across similar products
- Tag distribution and coverage
- Potential tagging issues
"""

import sqlite3
import json
import csv
from pathlib import Path
from collections import defaultdict, Counter
import re
from typing import Dict, List, Set, Tuple
import argparse


class TagValidator:
    def __init__(self, audit_db_path='audit.db', approved_tags_path='approved_tags.json'):
        self.audit_db_path = audit_db_path
        self.approved_tags_path = approved_tags_path
        self.approved_tags = self._load_approved_tags()
        self.all_approved_tags = self._flatten_approved_tags()
        self.tag_to_category = self._build_tag_to_category()

    def _load_approved_tags(self):
        """Load approved tags structure"""
        with open(self.approved_tags_path) as f:
            data = json.load(f)
            self.rules = data.pop('rules', {})
            return data

    def _flatten_approved_tags(self):
        """Create flat list of all approved tags"""
        tags = []
        for cat_data in self.approved_tags.values():
            if isinstance(cat_data, dict):
                tags.extend(cat_data.get('tags', []))
            else:
                tags.extend(cat_data)
        return tags

    def _build_tag_to_category(self):
        """Build mapping from tag to category"""
        tag_to_cat = {}
        for cat, cat_data in self.approved_tags.items():
            if isinstance(cat_data, dict):
                tags = cat_data.get('tags', [])
                # Handle range-based categories
                if cat_data.get('range'):
                    # For range-based, we'll handle dynamically
                    pass
                else:
                    for tag in tags:
                        tag_to_cat[tag] = cat
            else:
                for tag in cat_data:
                    tag_to_cat[tag] = cat
        return tag_to_cat

    def get_tag_category(self, tag, product_category=None):
        """Get category for a tag, including range-based logic"""
        # Check explicit mapping first
        if tag in self.tag_to_category:
            return self.tag_to_category[tag]

        # Check range-based categories
        if re.match(r'^\d+mg$', tag) and product_category == 'CBD':
            return 'cbd_strength'

        return 'unknown'

    def get_products_from_db(self, run_id=None):
        """Get all products from audit database"""
        conn = sqlite3.connect(self.audit_db_path)
        cur = conn.cursor()

        if run_id:
            cur.execute('SELECT * FROM products WHERE run_id = ?', (run_id,))
        else:
            # Get latest run
            cur.execute('SELECT run_id FROM runs WHERE is_latest = 1')
            latest_run = cur.fetchone()
            if latest_run:
                cur.execute('SELECT * FROM products WHERE run_id = ?', (latest_run[0],))
            else:
                cur.execute('SELECT * FROM products')

        columns = [desc[0] for desc in cur.description]
        products = []
        for row in cur.fetchall():
            product = dict(zip(columns, row))
            # Parse JSON fields
            for field in ['rule_tags', 'ai_tags', 'final_tags']:
                if product[field]:
                    try:
                        product[field] = json.loads(product[field])
                    except:
                        product[field] = []
                else:
                    product[field] = []
            products.append(product)

        conn.close()
        return products

    def validate_tag_adherence(self, products):
        """Check that all final tags are from approved vocabulary"""
        issues = []
        for product in products:
            for tag in product['final_tags']:
                if not self._is_tag_approved(tag, product['effective_type']):
                    issues.append({
                        'product_id': product['id'],
                        'handle': product['handle'],
                        'invalid_tag': tag,
                        'issue': 'Tag not in approved vocabulary'
                    })
        return issues

    def _is_tag_approved(self, tag, product_category):
        """Check if a tag is approved, including range-based categories"""
        # Check explicit tags first
        if tag in self.all_approved_tags:
            return True

        # Check range-based categories
        if re.match(r'^\d+mg$', tag):
            # CBD strength pattern
            cbd_config = self.approved_tags.get('cbd_strength', {})
            if cbd_config.get('range') and product_category == 'CBD':
                try:
                    mg_value = int(tag[:-2])  # Remove 'mg'
                    range_config = cbd_config['range']
                    min_val = range_config.get('min', 0)
                    max_val = range_config.get('max', 50000)
                    return min_val <= mg_value <= max_val
                except ValueError:
                    pass

        return False

    def analyze_tag_consistency(self, products):
        """Analyze consistency across similar products"""
        # Group products by category
        category_groups = defaultdict(list)
        for product in products:
            category = product['effective_type'] or 'unknown'
            category_groups[category].append(product)

        consistency_report = {}

        for category, prods in category_groups.items():
            if len(prods) < 2:
                continue

            # Analyze tag patterns within category
            tag_patterns = []
            for prod in prods:
                pattern = {
                    'handle': prod['handle'],
                    'final_tags': set(prod['final_tags']),
                    'tag_categories': {self.get_tag_category(tag, prod['effective_type']) for tag in prod['final_tags']}
                }
                tag_patterns.append(pattern)

            # Find common tags
            all_tags = [set(p['final_tags']) for p in tag_patterns]
            common_tags = set.intersection(*all_tags) if all_tags else set()

            # Find tag category coverage
            category_coverage = Counter()
            for pattern in tag_patterns:
                for cat in pattern['tag_categories']:
                    category_coverage[cat] += 1

            # Identify outliers (products with very different tag sets)
            avg_tag_count = sum(len(p['final_tags']) for p in tag_patterns) / len(tag_patterns)
            outliers = []
            for pattern in tag_patterns:
                if abs(len(pattern['final_tags']) - avg_tag_count) > 2:  # More than 2 tags difference
                    outliers.append({
                        'handle': pattern['handle'],
                        'tag_count': len(pattern['final_tags']),
                        'tags': sorted(pattern['final_tags'])
                    })

            consistency_report[category] = {
                'product_count': len(prods),
                'avg_tags_per_product': avg_tag_count,
                'common_tags': sorted(common_tags),
                'category_coverage': dict(category_coverage),
                'outliers': outliers
            }

        return consistency_report

    def analyze_similar_products(self, products):
        """Find products with similar names and check tag consistency"""
        # Group by similar handles (remove size/variant info)
        similar_groups = defaultdict(list)

        for product in products:
            handle = product['handle']
            # Normalize handle by removing common variant patterns
            normalized = re.sub(r'-\d+(ml|mg|pcs?|pack).*', '', handle.lower())
            normalized = re.sub(r'\d+(ml|mg|pcs?|pack).*', '', normalized)
            normalized = re.sub(r'[-_\s]+', ' ', normalized).strip()
            similar_groups[normalized].append(product)

        similarity_issues = []

        for group_key, group_products in similar_groups.items():
            if len(group_products) < 2:
                continue

            # Check if similar products have consistent categories
            categories = set(p['effective_type'] for p in group_products)
            if len(categories) > 1:
                similarity_issues.append({
                    'group': group_key,
                    'issue': 'Inconsistent categories',
                    'categories': list(categories),
                    'products': [{'handle': p['handle'], 'category': p['effective_type']} for p in group_products]
                })

            # Check tag consistency
            tag_sets = [set(p['final_tags']) for p in group_products]
            if len(set(frozenset(ts) for ts in tag_sets)) > 1:  # Different tag combinations
                similarity_issues.append({
                    'group': group_key,
                    'issue': 'Inconsistent tagging',
                    'tag_combinations': [sorted(ts) for ts in tag_sets],
                    'products': [{'handle': p['handle'], 'tags': sorted(p['final_tags'])} for p in group_products]
                })

        return similarity_issues

    def analyze_tag_coverage(self, products):
        """Analyze overall tag distribution and coverage"""
        tag_usage = Counter()
        category_usage = Counter()
        products_by_category = defaultdict(list)

        for product in products:
            products_by_category[product['effective_type']].append(product)
            for tag in product['final_tags']:
                tag_usage[tag] += 1
                category_usage[self.tag_to_category.get(tag, 'unknown')] += 1

        coverage_report = {
            'total_products': len(products),
            'total_tags_used': sum(tag_usage.values()),
            'unique_tags_used': len(tag_usage),
            'categories_represented': len(category_usage),
            'most_common_tags': tag_usage.most_common(10),
            'category_distribution': dict(category_usage),
            'products_per_category': {cat: len(prods) for cat, prods in products_by_category.items()},
            'untagged_products': len([p for p in products if not p['final_tags']])
        }

        return coverage_report

    def generate_report(self, products):
        """Generate comprehensive validation report"""
        print("🔍 TAG VALIDATION REPORT")
        print("=" * 50)

        # 1. Tag Adherence
        print("\n1. TAG ADHERENCE CHECK")
        adherence_issues = self.validate_tag_adherence(products)
        if adherence_issues:
            print(f"❌ Found {len(adherence_issues)} tags not in approved vocabulary:")
            for issue in adherence_issues[:5]:  # Show first 5
                print(f"   - {issue['handle']}: '{issue['invalid_tag']}'")
            if len(adherence_issues) > 5:
                print(f"   ... and {len(adherence_issues) - 5} more")
        else:
            print("✅ All tags are from approved vocabulary")

        # 2. Tag Coverage
        print("\n2. TAG COVERAGE ANALYSIS")
        coverage = self.analyze_tag_coverage(products)
        print(f"   Total products: {coverage['total_products']}")
        print(f"   Tagged products: {coverage['total_products'] - coverage['untagged_products']}")
        print(f"   Untagged products: {coverage['untagged_products']}")
        print(f"   Total tags applied: {coverage['total_tags_used']}")
        print(f"   Unique tags used: {coverage['unique_tags_used']}")
        print(f"   Categories represented: {coverage['categories_represented']}")

        print("\n   Most common tags:")
        for tag, count in coverage['most_common_tags']:
            print(f"     - {tag}: {count} products")

        print("\n   Products per category:")
        for cat, count in sorted(coverage['products_per_category'].items()):
            print(f"     - {cat}: {count} products")

        # 3. Consistency Analysis
        print("\n3. CONSISTENCY ANALYSIS")
        consistency = self.analyze_tag_consistency(products)
        for category, data in consistency.items():
            print(f"\n   Category: {category} ({data['product_count']} products)")
            print(f"     Average tags per product: {data['avg_tags_per_product']:.1f}")
            if data['common_tags']:
                print(f"     Common tags: {', '.join(data['common_tags'])}")
            if data['outliers']:
                print(f"     Outliers (tag count differs by >2): {len(data['outliers'])}")
                for outlier in data['outliers'][:3]:  # Show first 3
                    print(f"       - {outlier['handle']}: {outlier['tag_count']} tags")

        # 4. Similar Products Analysis
        print("\n4. SIMILAR PRODUCTS ANALYSIS")
        similarity_issues = self.analyze_similar_products(products)
        if similarity_issues:
            print(f"⚠️  Found {len(similarity_issues)} potential consistency issues:")
            for issue in similarity_issues[:5]:  # Show first 5
                print(f"   - {issue['group']}: {issue['issue']}")
                if issue['issue'] == 'Inconsistent categories':
                    print(f"     Categories: {', '.join(issue['categories'])}")
                elif issue['issue'] == 'Inconsistent tagging':
                    print(f"     Tag combinations: {len(set(str(tc) for tc in issue['tag_combinations']))} different patterns")
        else:
            print("✅ No major consistency issues found")

        # 5. Recommendations
        print("\n5. RECOMMENDATIONS")
        recommendations = []

        if adherence_issues:
            recommendations.append("Review and fix non-approved tags")

        if coverage['untagged_products'] > 0:
            recommendations.append(f"Investigate {coverage['untagged_products']} untagged products")

        if len(coverage['category_distribution']) < 5:
            recommendations.append("Consider expanding tag category coverage")

        consistency_issues = sum(1 for data in consistency.values() if data['outliers'])
        if consistency_issues > 0:
            recommendations.append(f"Review {consistency_issues} categories with tagging outliers")

        if similarity_issues:
            recommendations.append(f"Address {len(similarity_issues)} similar product consistency issues")

        if recommendations:
            for rec in recommendations:
                print(f"   - {rec}")
        else:
            print("   ✅ No major issues found - tagging looks good!")

        return {
            'adherence_issues': adherence_issues,
            'coverage': coverage,
            'consistency': consistency,
            'similarity_issues': similarity_issues,
            'recommendations': recommendations
        }


def main():
    parser = argparse.ArgumentParser(description='Validate tag consistency and adherence')
    parser.add_argument('--audit-db', default='audit.db', help='Path to audit database')
    parser.add_argument('--approved-tags', default='approved_tags.json', help='Path to approved tags file')
    parser.add_argument('--run-id', help='Specific run ID to analyze')
    parser.add_argument('--output', help='Output CSV file for detailed issues')

    args = parser.parse_args()

    validator = TagValidator(args.audit_db, args.approved_tags)
    products = validator.get_products_from_db(args.run_id)

    if not products:
        print("❌ No products found in database")
        return

    print(f"📊 Analyzing {len(products)} products...")

    report = validator.generate_report(products)

    # Save detailed issues to CSV if requested
    if args.output and (report['adherence_issues'] or report['similarity_issues']):
        with open(args.output, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Issue Type', 'Product Handle', 'Details'])

            for issue in report['adherence_issues']:
                writer.writerow(['Invalid Tag', issue['handle'], f"Tag '{issue['invalid_tag']}' not approved"])

            for issue in report['similarity_issues']:
                writer.writerow(['Consistency Issue', issue['group'], f"{issue['issue']} - {len(issue['products'])} products"])

        print(f"\n📄 Detailed issues saved to {args.output}")


if __name__ == "__main__":
    main()