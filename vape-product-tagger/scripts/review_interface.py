#!/usr/bin/env python3
"""
Interactive Review Interface
CLI tool for human review of tagged products
"""
import argparse
import sys
import csv
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.tag_audit_db import TagAuditDB


class ReviewInterface:
    """Interactive CLI for reviewing tagged products"""
    
    def __init__(self, audit_db_path: str, review_csv_path: str = None):
        """
        Initialize review interface
        
        Args:
            audit_db_path: Path to audit database
            review_csv_path: Optional path to review CSV file
        """
        self.audit_db = TagAuditDB(audit_db_path)
        self.review_csv_path = review_csv_path
        self.reviewed_count = 0
        self.approved_count = 0
        self.modified_count = 0
        self.rejected_count = 0
    
    def load_products_for_review(self):
        """Load products that need review"""
        if self.review_csv_path:
            # Load from CSV
            import pandas as pd
            df = pd.read_csv(self.review_csv_path)
            products = df.to_dict('records')
            print(f"📥 Loaded {len(products)} products from CSV")
            return products
        else:
            # Load from audit database
            products = self.audit_db.get_unverified_products()
            print(f"📥 Loaded {len(products)} unverified products from database")
            return products
    
    def display_product(self, product, index, total):
        """Display product details for review"""
        print("\n" + "="*70)
        print(f"Product {index + 1} of {total}")
        print("="*70)
        
        print(f"\n📦 Handle: {product.get('handle', 'N/A')}")
        print(f"📝 Title: {product.get('title', 'N/A')}")
        
        # Description preview
        desc = product.get('description', '')
        if desc:
            preview = desc[:200] + "..." if len(desc) > 200 else desc
            print(f"📄 Description: {preview}")
        
        # Category
        category = product.get('detected_category', product.get('category', 'N/A'))
        print(f"\n🏷️  Category: {category}")
        
        # Tags breakdown
        print("\n🏷️  Tags:")
        
        # Try to parse JSON tags if they're strings
        import json
        
        rule_tags = product.get('rule_tags', [])
        if isinstance(rule_tags, str):
            try:
                rule_tags = json.loads(rule_tags)
            except:
                rule_tags = []
        
        ai_tags = product.get('ai_tags', [])
        if isinstance(ai_tags, str):
            try:
                ai_tags = json.loads(ai_tags)
            except:
                ai_tags = []
        
        final_tags = product.get('final_tags', [])
        if isinstance(final_tags, str):
            try:
                final_tags = json.loads(final_tags)
            except:
                final_tags = []
        
        if rule_tags:
            print(f"  📏 Rule-based: {', '.join(rule_tags)}")
        if ai_tags:
            print(f"  🤖 AI-suggested: {', '.join(ai_tags)}")
        if final_tags:
            print(f"  ✅ Final: {', '.join(final_tags)}")
        
        # AI metadata
        ai_confidence = product.get('ai_confidence', 0.0)
        if ai_confidence:
            print(f"\n🎯 AI Confidence: {ai_confidence:.2f}")
        
        ai_reasoning = product.get('ai_reasoning', '')
        if ai_reasoning:
            print(f"💭 AI Reasoning: {ai_reasoning[:200]}...")
        
        print("\n" + "="*70)
    
    def get_user_action(self):
        """Get user action for current product"""
        print("\nActions:")
        print("  [a] Approve - Accept tags as-is")
        print("  [m] Modify - Edit tags")
        print("  [r] Reject - Mark for retagging")
        print("  [s] Skip - Skip to next")
        print("  [q] Quit - Exit review")
        
        while True:
            choice = input("\nYour choice: ").lower().strip()
            if choice in ['a', 'm', 'r', 's', 'q']:
                return choice
            print("❌ Invalid choice. Please enter a, m, r, s, or q")
    
    def modify_tags(self, current_tags):
        """Allow user to modify tags"""
        print("\nCurrent tags:", ', '.join(current_tags))
        print("Enter new tags (comma-separated), or press Enter to keep current:")
        
        new_tags_input = input("> ").strip()
        
        if not new_tags_input:
            return current_tags
        
        new_tags = [tag.strip() for tag in new_tags_input.split(',') if tag.strip()]
        print(f"✅ Updated to: {', '.join(new_tags)}")
        return new_tags
    
    def review_product(self, product, index, total):
        """Review a single product"""
        self.display_product(product, index, total)
        
        action = self.get_user_action()
        
        handle = product.get('handle')
        
        if action == 'a':
            # Approve
            self.audit_db.mark_verified(handle)
            self.approved_count += 1
            print("✅ Product approved")
            return 'continue'
        
        elif action == 'm':
            # Modify
            import json
            final_tags = product.get('final_tags', [])
            if isinstance(final_tags, str):
                try:
                    final_tags = json.loads(final_tags)
                except:
                    final_tags = []
            
            modified_tags = self.modify_tags(final_tags)
            self.audit_db.update_corrected_tags(handle, modified_tags)
            self.modified_count += 1
            print("✅ Product modified and approved")
            return 'continue'
        
        elif action == 'r':
            # Reject - just don't mark as verified
            self.rejected_count += 1
            print("❌ Product marked for retagging")
            return 'continue'
        
        elif action == 's':
            # Skip
            print("⏭️  Skipped")
            return 'continue'
        
        elif action == 'q':
            # Quit
            return 'quit'
    
    def run(self):
        """Run the interactive review session"""
        print("\n" + "="*70)
        print("🔍 Product Review Interface")
        print("="*70)
        
        products = self.load_products_for_review()
        
        if not products:
            print("\n✅ No products need review!")
            return
        
        total = len(products)
        
        for idx, product in enumerate(products):
            result = self.review_product(product, idx, total)
            
            self.reviewed_count += 1
            
            if result == 'quit':
                print("\n⚠️  Review session ended by user")
                break
        
        # Summary
        print("\n" + "="*70)
        print("📊 Review Summary")
        print("="*70)
        print(f"Total reviewed: {self.reviewed_count}/{total}")
        print(f"✅ Approved: {self.approved_count}")
        print(f"✏️  Modified: {self.modified_count}")
        print(f"❌ Rejected: {self.rejected_count}")
        print(f"⏭️  Skipped: {self.reviewed_count - self.approved_count - self.modified_count - self.rejected_count}")
        
        # Export corrected products
        if self.modified_count > 0:
            print("\n💾 Corrected products have been saved to the audit database")
            print("   These can be exported for training data using prepare_training_data.py")
        
        print("\n✅ Review session complete!")
    
    def close(self):
        """Close database connection"""
        self.audit_db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Interactive review interface for tagged products',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review from audit database
  python scripts/review_interface.py --audit-db output/audit.db

  # Review from CSV file
  python scripts/review_interface.py --audit-db output/audit.db --review-csv output/tagged_review.csv

  # Review only flagged products
  python scripts/review_interface.py --audit-db output/audit.db --flagged-only
        """
    )
    
    parser.add_argument('--audit-db', required=True,
                       help='Path to audit database')
    parser.add_argument('--review-csv',
                       help='Path to review CSV file (optional)')
    parser.add_argument('--flagged-only', action='store_true',
                       help='Only review products flagged for manual review')
    
    args = parser.parse_args()
    
    interface = ReviewInterface(args.audit_db, args.review_csv)
    
    try:
        interface.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Review interrupted by user")
    finally:
        interface.close()


if __name__ == '__main__':
    main()
