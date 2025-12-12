#!/usr/bin/env python3
"""
AI vs Rule Tag Audit Tool

Analyzes tagging accuracy and AI/rule tag contribution patterns
"""

import sqlite3
import json
import csv
from pathlib import Path
from collections import defaultdict, Counter
import argparse
from typing import Dict, List, Set, Tuple


class TagAuditor:
    def __init__(self, audit_db_path='audit.db', approved_tags_path='approved_tags.json'):
        self.audit_db_path = audit_db_path
        self.approved_tags = self._load_approved_tags()

    def _load_approved_tags(self):
        """Load approved tags structure"""
        with open('approved_tags.json') as f:
            data = json.load(f)
            self.rules = data.pop('rules', {})
            return data

    def get_products_from_db(self, run_id=None, all_runs=False):
        """Get all products from audit database"""
        conn = sqlite3.connect(self.audit_db_path)
        cur = conn.cursor()

        if run_id:
            cur.execute('SELECT * FROM products WHERE run_id = ?', (run_id,))
        elif all_runs:
            cur.execute('SELECT * FROM products')
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

    def analyze_ai_vs_rule_contribution(self, products):
        """Analyze how AI and rule tags contribute to final tags"""
        contribution_stats = {
            'total_products': len(products),
            'products_with_ai_tags': 0,
            'products_with_rule_tags': 0,
            'products_with_both': 0,
            'products_with_neither': 0,
            'ai_only_contribution': 0,
            'rule_only_contribution': 0,
            'both_contribute': 0,
            'tag_sources': defaultdict(int),  # 'ai_only', 'rule_only', 'both', 'neither'
            'category_performance': defaultdict(lambda: {'ai': 0, 'rule': 0, 'both': 0, 'total': 0})
        }
        
        for product in products:
            rule_tags = set(product['rule_tags'])
            ai_tags = set(product['ai_tags'])
            final_tags = set(product['final_tags'])

            # Count products with different tag sources
            has_rule = len(rule_tags) > 0
            has_ai = len(ai_tags) > 0

            if has_ai:
                contribution_stats['products_with_ai_tags'] += 1
            if has_rule:
                contribution_stats['products_with_rule_tags'] += 1
            if has_ai and has_rule:
                contribution_stats['products_with_both'] += 1
            elif not has_ai and not has_rule:
                contribution_stats['products_with_neither'] += 1

            # Analyze contribution to final tags
            ai_contribution = ai_tags.intersection(final_tags)
            rule_contribution = rule_tags.intersection(final_tags)

            category = product['effective_type'] or 'unknown'
            contribution_stats['category_performance'][category]['total'] += 1

            if ai_contribution and rule_contribution:
                contribution_stats['both_contribute'] += 1
                contribution_stats['tag_sources']['both'] += len(final_tags)
                contribution_stats['category_performance'][category]['both'] += 1
            elif ai_contribution:
                contribution_stats['ai_only_contribution'] += 1
                contribution_stats['tag_sources']['ai_only'] += len(final_tags)
                contribution_stats['category_performance'][category]['ai'] += 1
            elif rule_contribution:
                contribution_stats['rule_only_contribution'] += 1
                contribution_stats['tag_sources']['rule_only'] += len(final_tags)
                contribution_stats['category_performance'][category]['rule'] += 1
            else:
                contribution_stats['tag_sources']['neither'] += len(final_tags)

        return contribution_stats

    def analyze_tag_accuracy(self, products):
        """Analyze potential accuracy issues in tagging"""
        accuracy_issues = {
            'missing_expected_tags': [],
            'unexpected_tag_combinations': [],
            'category_mismatches': [],
            'inconsistent_similar_products': []
        }

        # Group by category for analysis
        category_groups = defaultdict(list)
        for product in products:
            category = product['effective_type'] or 'unknown'
            category_groups[category].append(product)

        # Check for category-specific issues
        for category, prods in category_groups.items():
            if category == 'e-liquid':
                self._check_eliquid_accuracy(prods, accuracy_issues)
            elif category == 'CBD':
                self._check_cbd_accuracy(prods, accuracy_issues)
            elif category == 'pod':
                self._check_pod_accuracy(prods, accuracy_issues)

        # Check for similar products with different tagging
        self._check_similar_product_consistency(products, accuracy_issues)

        return accuracy_issues

    def _check_eliquid_accuracy(self, products, accuracy_issues):
        """Check e-liquid specific tagging accuracy"""
        for product in products:
            final_tags = set(product['final_tags'])
            handle = product['handle'].lower()

            # E-liquids should typically have nicotine strength or be 0mg
            nic_tags = [tag for tag in final_tags if 'mg' in tag and tag != 'cbd' and not tag.endswith('ml')]
            if not nic_tags and '0mg' not in final_tags:
                # Check if it should have nicotine info
                if any(word in handle for word in ['nic', 'salt', 'mg']):
                    accuracy_issues['missing_expected_tags'].append({
                        'product': product['handle'],
                        'category': 'e-liquid',
                        'issue': 'Missing nicotine strength tag',
                        'expected': 'nicotine_strength category tag'
                    })

            # Check for VG/PG ratio tags (skip if "various" ratio)
            ratio_tags = [tag for tag in final_tags if '/' in tag and tag[0].isdigit()]
            has_various_ratio = 'various' in handle or 'various' in product.get('title', '').lower()
            if not ratio_tags and not has_various_ratio and any(word in handle for word in ['vg', 'pg']):
                # Only flag if there's a specific ratio pattern in the handle
                import re
                if re.search(r'\d+vg|\d+pg', handle):
                    accuracy_issues['missing_expected_tags'].append({
                        'product': product['handle'],
                        'category': 'e-liquid',
                        'issue': 'Missing VG/PG ratio tag',
                        'expected': 'vg_ratio category tag'
                    })

    def _check_cbd_accuracy(self, products, accuracy_issues):
        """Check CBD specific tagging accuracy"""
        for product in products:
            final_tags = set(product['final_tags'])
            handle = product['handle'].lower()

            # CBD products should have strength tags
            strength_tags = [tag for tag in final_tags if tag.endswith('mg') and tag != 'cbd']
            if not strength_tags and any(word in handle for word in ['mg', 'cbd', 'cbg']):
                accuracy_issues['missing_expected_tags'].append({
                    'product': product['handle'],
                    'category': 'CBD',
                    'issue': 'Missing CBD strength tag',
                    'expected': 'cbd_strength category tag'
                })

            # CBD products should have form tags (oil, capsule, etc.)
            valid_form_tags = {'oil', 'capsule', 'topical', 'tincture', 'gummy', 'shot', 'patch', 
                              'paste', 'isolate', 'edible', 'beverage', 'crumble', 'shatter', 'wax'}
            form_tags = [tag for tag in final_tags if tag in valid_form_tags]
            if not form_tags:
                accuracy_issues['missing_expected_tags'].append({
                    'product': product['handle'],
                    'category': 'CBD',
                    'issue': 'Missing CBD form tag',
                    'expected': 'cbd_form category tag'
                })

    def _check_pod_accuracy(self, products, accuracy_issues):
        """Check pod specific tagging accuracy"""
        for product in products:
            final_tags = set(product['final_tags'])
            handle = product['handle'].lower()

            # Pods should have capacity tags
            capacity_tags = [tag for tag in final_tags if tag.endswith('ml') and tag != 'cbd']
            if not capacity_tags and any(word in handle for word in ['ml', 'pod']):
                accuracy_issues['missing_expected_tags'].append({
                    'product': product['handle'],
                    'category': 'pod',
                    'issue': 'Missing capacity tag',
                    'expected': 'capacity category tag'
                })

    def _check_similar_product_consistency(self, products, accuracy_issues):
        """Check for similar products with inconsistent tagging"""
        # Group by normalized names
        similar_groups = defaultdict(list)

        for product in products:
            handle = product['handle']
            # Normalize handle by removing common variant patterns
            normalized = handle.lower()
            normalized = normalized.replace('-', ' ').replace('_', ' ')
            # Remove size patterns
            import re
            normalized = re.sub(r'\d+(ml|mg|pcs?|pack).*', '', normalized)
            normalized = re.sub(r'\d+(ml|mg|pcs?|pack)', '', normalized)
            normalized = ' '.join(normalized.split())  # normalize spaces

            similar_groups[normalized].append(product)

        for group_key, group_products in similar_groups.items():
            if len(group_products) < 2:
                continue

            # Check if similar products have different categories
            categories = set(p['effective_type'] for p in group_products)
            if len(categories) > 1:
                accuracy_issues['inconsistent_similar_products'].append({
                    'group': group_key,
                    'issue': 'Different categories for similar products',
                    'categories': list(categories),
                    'products': [{'handle': p['handle'], 'category': p['effective_type']} for p in group_products]
                })

            # Check if similar products have very different tag sets
            tag_sets = [set(p['final_tags']) for p in group_products]
            if len(set(frozenset(ts) for ts in tag_sets)) > 1:
                # Calculate similarity
                common_tags = set.intersection(*tag_sets) if tag_sets else set()
                total_unique_tags = set.union(*tag_sets) if tag_sets else set()

                if len(common_tags) / len(total_unique_tags) < 0.5:  # Less than 50% overlap
                    accuracy_issues['inconsistent_similar_products'].append({
                        'group': group_key,
                        'issue': 'Inconsistent tagging for similar products',
                        'common_tags': sorted(common_tags),
                        'unique_tags': sorted(total_unique_tags - common_tags),
                        'products': [{'handle': p['handle'], 'tags': sorted(p['final_tags'])} for p in group_products]
                    })

    def analyze_ai_performance(self, products):
        """Analyze AI tagging performance and patterns"""
        ai_performance = {
            'ai_suggestions': [],
            'ai_accuracy_by_category': defaultdict(lambda: {'correct': 0, 'incorrect': 0, 'total': 0}),
            'common_ai_mistakes': Counter(),
            'ai_vs_rule_agreement': {'agree': 0, 'disagree': 0, 'ai_only': 0, 'rule_only': 0}
        }

        for product in products:
            rule_tags = set(product['rule_tags'])
            ai_tags = set(product['ai_tags'])
            final_tags = set(product['final_tags'])
            category = product['effective_type'] or 'unknown'

            # Track AI suggestions
            ai_performance['ai_suggestions'].extend(ai_tags)

            # Analyze agreement between AI and rules
            ai_in_final = ai_tags.intersection(final_tags)
            rule_in_final = rule_tags.intersection(final_tags)

            if ai_in_final and rule_in_final:
                ai_performance['ai_vs_rule_agreement']['agree'] += 1
            elif ai_in_final and not rule_in_final:
                ai_performance['ai_vs_rule_agreement']['ai_only'] += 1
            elif not ai_in_final and rule_in_final:
                ai_performance['ai_vs_rule_agreement']['rule_only'] += 1
            else:
                ai_performance['ai_vs_rule_agreement']['disagree'] += 1

            # Simple accuracy measure: AI tags that made it to final
            ai_performance['ai_accuracy_by_category'][category]['total'] += len(ai_tags)
            ai_performance['ai_accuracy_by_category'][category]['correct'] += len(ai_in_final)

        # Calculate percentages
        for category, stats in ai_performance['ai_accuracy_by_category'].items():
            if stats['total'] > 0:
                stats['accuracy'] = stats['correct'] / stats['total']
            else:
                stats['accuracy'] = 0

        return ai_performance

    def generate_audit_report(self, products):
        """Generate comprehensive audit report"""
        print("🔍 AI vs RULE TAG AUDIT REPORT")
        print("=" * 60)

        # 1. Overall Statistics
        contribution = self.analyze_ai_vs_rule_contribution(products)
        print(f"\n📊 OVERALL STATISTICS")
        print(f"   Total products analyzed: {contribution['total_products']}")
        print(f"   Products with AI tags: {contribution['products_with_ai_tags']} ({contribution['products_with_ai_tags']/contribution['total_products']*100:.1f}%)")
        print(f"   Products with rule tags: {contribution['products_with_rule_tags']} ({contribution['products_with_rule_tags']/contribution['total_products']*100:.1f}%)")
        print(f"   Products with both AI and rule tags: {contribution['products_with_both']} ({contribution['products_with_both']/contribution['total_products']*100:.1f}%)")
        print(f"   Products with neither: {contribution['products_with_neither']} ({contribution['products_with_neither']/contribution['total_products']*100:.1f}%)")

        # 2. Contribution to Final Tags
        print(f"\n🤖 AI vs RULE CONTRIBUTION")
        total_contributing = contribution['ai_only_contribution'] + contribution['rule_only_contribution'] + contribution['both_contribute']
        if total_contributing > 0:
            print(f"   AI-only contribution: {contribution['ai_only_contribution']} ({contribution['ai_only_contribution']/total_contributing*100:.1f}%)")
            print(f"   Rule-only contribution: {contribution['rule_only_contribution']} ({contribution['rule_only_contribution']/total_contributing*100:.1f}%)")
            print(f"   Both contribute: {contribution['both_contribute']} ({contribution['both_contribute']/total_contributing*100:.1f}%)")

        print(f"\n   Tag source breakdown:")
        total_tags = sum(contribution['tag_sources'].values())
        for source, count in contribution['tag_sources'].items():
            print(f"     {source}: {count} tags ({count/total_tags*100:.1f}%)")

        # 3. Category Performance
        print(f"\n📂 CATEGORY PERFORMANCE")
        for category, stats in sorted(contribution['category_performance'].items()):
            if stats['total'] > 0:
                ai_pct = stats['ai'] / stats['total'] * 100
                rule_pct = stats['rule'] / stats['total'] * 100
                both_pct = stats['both'] / stats['total'] * 100
                print(f"   {category} ({stats['total']} products):")
                print(f"     AI-only: {stats['ai']} ({ai_pct:.1f}%)")
                print(f"     Rule-only: {stats['rule']} ({rule_pct:.1f}%)")
                print(f"     Both: {stats['both']} ({both_pct:.1f}%)")

        # 4. AI Performance Analysis
        ai_perf = self.analyze_ai_performance(products)
        print(f"\n🎯 AI PERFORMANCE ANALYSIS")
        print(f"   AI vs Rule agreement:")
        total_agreements = sum(ai_perf['ai_vs_rule_agreement'].values())
        for agreement_type, count in ai_perf['ai_vs_rule_agreement'].items():
            pct = count / total_agreements * 100 if total_agreements > 0 else 0
            print(f"     {agreement_type}: {count} ({pct:.1f}%)")

        print(f"\n   AI accuracy by category:")
        for category, stats in sorted(ai_perf['ai_accuracy_by_category'].items()):
            if stats['total'] > 0:
                print(f"     {category}: {stats['correct']}/{stats['total']} ({stats['accuracy']*100:.1f}%)")

        # 5. Accuracy Issues
        accuracy_issues = self.analyze_tag_accuracy(products)
        print(f"\n⚠️  ACCURACY ISSUES FOUND")

        issue_counts = {k: len(v) for k, v in accuracy_issues.items()}
        total_issues = sum(issue_counts.values())
        print(f"   Total accuracy issues: {total_issues}")

        for issue_type, count in issue_counts.items():
            if count > 0:
                print(f"   {issue_type}: {count}")

        # Show top issues
        if accuracy_issues['missing_expected_tags']:
            print(f"\n   Top missing expected tags:")
            for issue in accuracy_issues['missing_expected_tags'][:3]:
                print(f"     - {issue['product']}: {issue['expected']}")

        if accuracy_issues['inconsistent_similar_products']:
            print(f"\n   Top similar product inconsistencies:")
            for issue in accuracy_issues['inconsistent_similar_products'][:3]:
                print(f"     - {issue['group']}: {issue['issue']}")

        # 6. Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        recommendations = []

        ai_pct = (contribution['products_with_ai_tags'] / contribution['total_products']) * 100
        if contribution['products_with_ai_tags'] == 0:
            recommendations.append("AI tags never made it into the audit; verify model configuration and rerun tagging")
        elif ai_pct < 30:
            recommendations.append(f"Increase AI tagging coverage (currently {ai_pct:.1f}% of products contain AI tags)")
        elif ai_pct > 85:
            recommendations.append("AI tagging coverage is strong—focus on accuracy next")

        if total_agreements == 0:
            recommendations.append("No AI vs rule comparisons available; ensure both taggers run for the same batch")
        else:
            agreement_pct = (ai_perf['ai_vs_rule_agreement']['agree'] / total_agreements) * 100
            if agreement_pct < 60:
                recommendations.append(f"Review AI-rule disagreement patterns (agreement only {agreement_pct:.1f}%)")
            else:
                recommendations.append("AI and rule-based tagging generally agree")

        missing_expected = accuracy_issues['missing_expected_tags']
        inconsistent_groups = accuracy_issues['inconsistent_similar_products']

        if missing_expected:
            top_missing = missing_expected[0]
            recommendations.append(
                f"Backfill required tags such as {top_missing['expected']} (example: {top_missing['product']})"
            )

        if inconsistent_groups:
            top_group = inconsistent_groups[0]
            recommendations.append(
                f"Normalize tagging for similar products (e.g., group '{top_group['group']}')"
            )

        if not missing_expected and not inconsistent_groups:
            if total_issues > 0:
                recommendations.append(f"Address the remaining {total_issues} accuracy issues")
            else:
                recommendations.append("No blocking accuracy issues detected")

        for rec in recommendations:
            print(f"   - {rec}")

        return {
            'contribution': contribution,
            'ai_performance': ai_perf,
            'accuracy_issues': accuracy_issues,
            'recommendations': recommendations
        }


def main():
    parser = argparse.ArgumentParser(description='Audit AI vs rule tag usage and accuracy')
    parser.add_argument('--audit-db', default='audit.db', help='Path to audit database')
    parser.add_argument('--run-id', help='Specific run ID to analyze')
    parser.add_argument('--all-runs', action='store_true', help='Analyze all runs instead of latest')
    parser.add_argument('--output', help='Output CSV file for detailed issues')

    args = parser.parse_args()

    auditor = TagAuditor(args.audit_db)
    products = auditor.get_products_from_db(args.run_id, args.all_runs)

    if not products:
        print("❌ No products found in database")
        return

    print(f"📊 Auditing {len(products)} products...")

    report = auditor.generate_audit_report(products)


    # Save detailed issues to CSV if requested
    if args.output:
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Training dataset header
            writer.writerow([
                'Handle', 'Title', 'Description', 'Rule Tags', 'AI Tags', 'Final Tags',
                'Category', 'Audit Error Type', 'Audit Error Details', 'Correction',
                'AI Prompt', 'Model Output'
            ])

            # Map product handle to audit errors for quick lookup
            error_map = defaultdict(list)
            for issue in report['accuracy_issues']['missing_expected_tags']:
                error_map[issue['product']].append((issue['issue'], issue['expected']))
            for issue in report['accuracy_issues']['inconsistent_similar_products']:
                error_map[issue['group']].append((issue['issue'], str(issue.get('products', ''))))

            # Export all products, including those with errors
            for product in products:
                handle = product.get('handle', '')
                title = product.get('title', '')
                description = product.get('description', '')
                rule_tags = ','.join(product.get('rule_tags', []))
                ai_tags = ','.join(product.get('ai_tags', []))
                final_tags = ','.join(product.get('final_tags', []))
                category = product.get('effective_type', '')
                # Audit error info
                error_type = ''
                error_details = ''
                if handle in error_map:
                    error_type = '; '.join([e[0] for e in error_map[handle]])
                    error_details = '; '.join([e[1] for e in error_map[handle]])
                # Correction (manual true tag, blank for now)
                correction = ''
                # AI prompt/model output (if available)
                ai_prompt = product.get('ai_prompt', '')
                model_output = product.get('ai_model_output', '')
                writer.writerow([
                    handle, title, description, rule_tags, ai_tags, final_tags,
                    category, error_type, error_details, correction,
                    ai_prompt, model_output
                ])
        print(f"\n📄 Audit training dataset saved to {args.output}")


if __name__ == "__main__":
    main()