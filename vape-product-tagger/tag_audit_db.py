import sqlite3
import json
from pathlib import Path
from datetime import datetime
import uuid
import threading


class TagAuditDB:
    def __init__(self, db_path='output/tag_audit.sqlite3', thread_safe=False):
        self.db_path = db_path
        self.thread_safe = thread_safe
        self._ensure_parent()
        
        if thread_safe:
            # Thread-local storage for connections
            self._local = threading.local()
            self._lock = threading.Lock()
        else:
            self.conn = sqlite3.connect(self.db_path)
        
        self._create_tables()
    
    def _get_connection(self):
        """Get thread-local connection or single connection"""
        if self.thread_safe:
            if not hasattr(self._local, 'conn') or self._local.conn is None:
                self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            return self._local.conn
        return self.conn

    def _ensure_parent(self):
        p = Path(self.db_path)
        if not p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)

    def _create_tables(self):
        conn = self._get_connection()
        cur = conn.cursor()
        # Runs table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT,
            completed_at TEXT,
            is_latest INTEGER DEFAULT 0,
            config TEXT,
            status TEXT DEFAULT 'running'
        )
        ''')
        # Products table with run_id
        cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            handle TEXT,
            title TEXT,
            csv_type TEXT,
            effective_type TEXT,
            description TEXT,
            rule_tags TEXT,
            ai_tags TEXT,
            final_tags TEXT,
            forced_category TEXT,
            device_evidence INTEGER,
            skipped INTEGER,
            skip_reason TEXT,
            processed_at TEXT,
            ai_prompt TEXT,
            ai_model_output TEXT,
            ai_confidence REAL,
            ai_reasoning TEXT,
            human_verified INTEGER DEFAULT 0,
            human_corrected_tags TEXT,
            human_corrected_category TEXT,
            detected_category TEXT,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        )
        ''')
        conn.commit()
        
        # Migrate existing tables - add new columns if they don't exist
        self._migrate_schema()
    
    def _migrate_schema(self):
        """Add new columns to existing tables if they don't exist"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        # Check existing columns in products table
        cur.execute("PRAGMA table_info(products)")
        existing_columns = {row[1] for row in cur.fetchall()}
        
        # New columns to add with their types
        new_columns = [
            ('ai_prompt', 'TEXT'),
            ('ai_model_output', 'TEXT'),
            ('ai_confidence', 'REAL'),
            ('ai_reasoning', 'TEXT'),
            ('human_verified', 'INTEGER DEFAULT 0'),
            ('human_corrected_tags', 'TEXT'),
            ('human_corrected_category', 'TEXT'),
            ('detected_category', 'TEXT'),
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                try:
                    cur.execute(f'ALTER TABLE products ADD COLUMN {col_name} {col_type}')
                    print(f"Added column {col_name} to products table")
                except sqlite3.OperationalError:
                    pass  # Column already exists
        
        conn.commit()

    def start_run(self, config=None):
        """Start a new run, return run_id"""
        run_id = str(uuid.uuid4())
        conn = self._get_connection()
        cur = conn.cursor()
        
        if self.thread_safe:
            with self._lock:
                cur.execute('''
                    INSERT INTO runs (run_id, started_at, config, status)
                    VALUES (?, ?, ?, ?)
                ''', (run_id, datetime.now().isoformat(), json.dumps(config or {}), 'running'))
                conn.commit()
        else:
            cur.execute('''
                INSERT INTO runs (run_id, started_at, config, status)
                VALUES (?, ?, ?, ?)
            ''', (run_id, datetime.now().isoformat(), json.dumps(config or {}), 'running'))
            conn.commit()
        return run_id

    def complete_run(self, run_id):
        """Mark run as completed and set as latest"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        if self.thread_safe:
            with self._lock:
                cur.execute('UPDATE runs SET is_latest = 0 WHERE is_latest = 1')
                cur.execute('''
                    UPDATE runs SET completed_at = ?, is_latest = 1, status = 'completed'
                    WHERE run_id = ?
                ''', (datetime.now().isoformat(), run_id))
                conn.commit()
        else:
            cur.execute('UPDATE runs SET is_latest = 0 WHERE is_latest = 1')
            cur.execute('''
                UPDATE runs SET completed_at = ?, is_latest = 1, status = 'completed'
                WHERE run_id = ?
            ''', (datetime.now().isoformat(), run_id))
            conn.commit()

    def get_latest_run(self):
        """Get the latest run_id"""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute('SELECT run_id FROM runs WHERE is_latest = 1 ORDER BY started_at DESC LIMIT 1')
        row = cur.fetchone()
        return row[0] if row else None

    def get_run_status(self, run_id):
        """Get run status"""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute('SELECT status FROM runs WHERE run_id = ?', (run_id,))
        row = cur.fetchone()
        return row[0] if row else None

    def insert_product(self, run_id, handle, title, csv_type, effective_type, description, rule_tags, ai_tags, final_tags, forced_category, device_evidence, skipped=0, skip_reason=None, ai_prompt=None, ai_model_output=None, ai_confidence=None, ai_reasoning=None, detected_category=None):
        conn = self._get_connection()
        cur = conn.cursor()
        
        data = (
            run_id,
            handle,
            title,
            csv_type,
            effective_type,
            description,
            json.dumps(rule_tags or []),
            json.dumps(ai_tags or []),
            json.dumps(final_tags or []),
            forced_category,
            1 if device_evidence else 0,
            1 if skipped else 0,
            skip_reason,
            datetime.now().isoformat(),
            ai_prompt,
            ai_model_output,
            ai_confidence,
            ai_reasoning,
            detected_category
        )
        
        if self.thread_safe:
            with self._lock:
                cur.execute('''
                    INSERT INTO products (
                        run_id, handle, title, csv_type, effective_type, description,
                        rule_tags, ai_tags, final_tags, forced_category, device_evidence,
                        skipped, skip_reason, processed_at, ai_prompt, ai_model_output,
                        ai_confidence, ai_reasoning, detected_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', data)
                conn.commit()
        else:
            cur.execute('''
                INSERT INTO products (
                    run_id, handle, title, csv_type, effective_type, description,
                    rule_tags, ai_tags, final_tags, forced_category, device_evidence,
                    skipped, skip_reason, processed_at, ai_prompt, ai_model_output,
                    ai_confidence, ai_reasoning, detected_category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            conn.commit()

    def insert_products_batch(self, products_data):
        """Insert multiple products in a single transaction (thread-safe)"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        if self.thread_safe:
            with self._lock:
                for data in products_data:
                    cur.execute('''
                        INSERT INTO products (
                            run_id, handle, title, csv_type, effective_type, description,
                            rule_tags, ai_tags, final_tags, forced_category, device_evidence,
                            skipped, skip_reason, processed_at, ai_prompt, ai_model_output,
                            ai_confidence, ai_reasoning, detected_category
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', data)
                conn.commit()
        else:
            for data in products_data:
                cur.execute('''
                    INSERT INTO products (
                        run_id, handle, title, csv_type, effective_type, description,
                        rule_tags, ai_tags, final_tags, forced_category, device_evidence,
                        skipped, skip_reason, processed_at, ai_prompt, ai_model_output,
                        ai_confidence, ai_reasoning, detected_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', data)
            conn.commit()

    def get_unverified_products(self, limit=None):
        """Get all products that haven't been human verified"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        query = '''
            SELECT handle, title, detected_category, rule_tags, ai_tags, 
                   final_tags, ai_prompt, ai_model_output, ai_confidence
            FROM products 
            WHERE human_verified = 0
            ORDER BY processed_at ASC
        '''
        
        if limit:
            query += f' LIMIT {limit}'
        
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def mark_verified(self, handle):
        """Mark a product as human verified"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        if self.thread_safe:
            with self._lock:
                cur.execute('''
                    UPDATE products 
                    SET human_verified = 1
                    WHERE handle = ?
                ''', (handle,))
                conn.commit()
        else:
            cur.execute('''
                UPDATE products 
                SET human_verified = 1
                WHERE handle = ?
            ''', (handle,))
            conn.commit()

    def update_corrected_tags(self, handle, corrected_tags):
        """Update a product with human-corrected tags"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        corrected_json = json.dumps(corrected_tags)
        
        if self.thread_safe:
            with self._lock:
                cur.execute('''
                    UPDATE products 
                    SET human_corrected_tags = ?, human_verified = 1
                    WHERE handle = ?
                ''', (corrected_json, handle))
                conn.commit()
        else:
            cur.execute('''
                UPDATE products 
                SET human_corrected_tags = ?, human_verified = 1
                WHERE handle = ?
            ''', (corrected_json, handle))
            conn.commit()

    def update_corrected_category(self, handle, corrected_category):
        """Update a product with human-corrected category"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        if self.thread_safe:
            with self._lock:
                cur.execute('''
                    UPDATE products 
                    SET human_corrected_category = ?, human_verified = 1
                    WHERE handle = ?
                ''', (corrected_category, handle))
                conn.commit()
        else:
            cur.execute('''
                UPDATE products 
                SET human_corrected_category = ?, human_verified = 1
                WHERE handle = ?
            ''', (corrected_category, handle))
            conn.commit()

    def get_stats(self):
        """Get statistics about the audit database"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        stats = {}
        
        # Total products
        cur.execute("SELECT COUNT(*) FROM products")
        stats['total'] = cur.fetchone()[0]
        
        # Verified products
        cur.execute("SELECT COUNT(*) FROM products WHERE human_verified = 1")
        stats['verified'] = cur.fetchone()[0]
        
        # Corrected products (tags)
        cur.execute("SELECT COUNT(*) FROM products WHERE human_corrected_tags IS NOT NULL")
        stats['corrected_tags'] = cur.fetchone()[0]
        
        # Corrected products (category)
        cur.execute("SELECT COUNT(*) FROM products WHERE human_corrected_category IS NOT NULL")
        stats['corrected_categories'] = cur.fetchone()[0]
        
        # Unverified products
        stats['unverified'] = stats['total'] - stats['verified']
        
        # By category
        cur.execute('''
            SELECT detected_category, COUNT(*) as count 
            FROM products 
            GROUP BY detected_category 
            ORDER BY count DESC
        ''')
        stats['by_category'] = dict(cur.fetchall())
        
        # Average confidence
        cur.execute("SELECT AVG(ai_confidence) FROM products WHERE ai_confidence IS NOT NULL")
        avg_conf = cur.fetchone()[0]
        stats['avg_confidence'] = round(avg_conf, 3) if avg_conf else 0.0
        
        return stats

    def print_stats(self):
        """Print formatted statistics"""
        stats = self.get_stats()
        
        print(f"\n{'='*50}")
        print(f"  TAG AUDIT DATABASE STATISTICS")
        print(f"{'='*50}")
        print(f"  Total products:       {stats['total']:,}")
        print(f"  Verified:             {stats['verified']:,}")
        print(f"  Corrected (tags):     {stats['corrected_tags']:,}")
        print(f"  Corrected (category): {stats['corrected_categories']:,}")
        print(f"  Unverified:           {stats['unverified']:,}")
        print(f"  Avg AI confidence:    {stats['avg_confidence']:.2%}")
        print(f"{'─'*50}")
        print(f"  By Category:")
        for cat, count in stats.get('by_category', {}).items():
            print(f"    {cat or 'unknown':<20} {count:,}")
        print(f"{'='*50}\n")

    def review_session(self):
        """Interactive session to review and verify tagged products"""
        unverified = self.get_unverified_products()
        
        if not unverified:
            print("\n✅ No unverified products to review!")
            print(f"   Total products in database: {self.get_stats().get('total', 0)}")
            return
        
        print(f"\n{'='*60}")
        print(f"  AUDIT REVIEW SESSION")
        print(f"  {len(unverified)} unverified products to review")
        print(f"{'='*60}\n")
        
        reviewed_count = 0
        corrected_count = 0
        category_corrected = 0
        
        for i, product in enumerate(unverified, 1):
            handle = product['handle']
            title = product['title']
            category = product['detected_category']
            
            # Parse tags from JSON
            try:
                rule_tags = json.loads(product['rule_tags']) if product['rule_tags'] else []
            except:
                rule_tags = []
            
            try:
                ai_tags = json.loads(product['ai_tags']) if product['ai_tags'] else []
            except:
                ai_tags = []
                
            try:
                final_tags = json.loads(product['final_tags']) if product['final_tags'] else []
            except:
                final_tags = []
            
            confidence = product['ai_confidence'] or 0.0
            
            # Display product info
            print(f"\n{'─'*60}")
            print(f"  Product [{i}/{len(unverified)}]")
            print(f"{'─'*60}")
            print(f"  Handle:     {handle}")
            print(f"  Title:      {title}")
            print(f"  Category:   {category}")
            print(f"  Confidence: {confidence:.2f}")
            print()
            print(f"  Rule-based tags ({len(rule_tags)}):")
            for tag in rule_tags[:10]:
                print(f"    • {tag}")
            if len(rule_tags) > 10:
                print(f"    ... and {len(rule_tags) - 10} more")
            print()
            print(f"  AI tags ({len(ai_tags)}):")
            for tag in ai_tags[:10]:
                print(f"    • {tag}")
            if len(ai_tags) > 10:
                print(f"    ... and {len(ai_tags) - 10} more")
            print()
            print(f"  Final tags ({len(final_tags)}):")
            for tag in final_tags[:15]:
                print(f"    • {tag}")
            if len(final_tags) > 15:
                print(f"    ... and {len(final_tags) - 15} more")
            print()
            print(f"{'─'*60}")
            print("  [a] Approve   [c] Correct tags   [g] Change category   [s] Skip   [q] Quit")
            print(f"{'─'*60}")
            
            while True:
                try:
                    choice = input("  Your choice: ").strip().lower()
                except EOFError:
                    print("\n\nNo interactive input available (running in non-interactive mode)")
                    print("Use --export to export data or run in an interactive terminal.")
                    return
                except KeyboardInterrupt:
                    print("\n\nSession interrupted.")
                    break
                
                if choice == 'a':
                    # Approve - mark as verified
                    self.mark_verified(handle)
                    reviewed_count += 1
                    print(f"  ✅ Approved!")
                    break
                    
                elif choice == 'c':
                    # Correct tags
                    print("\n  Enter corrected tags (comma-separated):")
                    print("  Current tags:", ", ".join(final_tags[:10]))
                    try:
                        new_tags_input = input("  New tags: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n  Correction cancelled.")
                        continue
                    
                    if new_tags_input:
                        new_tags = [t.strip() for t in new_tags_input.split(',') if t.strip()]
                        self.update_corrected_tags(handle, new_tags)
                        reviewed_count += 1
                        corrected_count += 1
                        print(f"  ✅ Corrected with {len(new_tags)} tags!")
                    else:
                        print("  ⚠️  No tags entered, skipping correction.")
                        continue
                    break
                
                elif choice == 'g':
                    # Change category
                    print("\n  Enter new category:")
                    print("  Current category:", category)
                    print("  Options: e-liquid, CBD, disposable, pod, coil, accessory, device, nicotine_pouches")
                    try:
                        new_category = input("  New category: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n  Category change cancelled.")
                        continue
                    
                    if new_category:
                        self.update_corrected_category(handle, new_category)
                        reviewed_count += 1
                        category_corrected += 1
                        print(f"  ✅ Category changed to '{new_category}'!")
                    else:
                        print("  ⚠️  No category entered, skipping.")
                        continue
                    break
                    
                elif choice == 's':
                    print(f"  ⏭️  Skipped")
                    break
                    
                elif choice == 'q':
                    print(f"\n{'='*60}")
                    print(f"  SESSION SUMMARY")
                    print(f"{'='*60}")
                    print(f"  Products reviewed:     {reviewed_count}")
                    print(f"  Tags corrected:        {corrected_count}")
                    print(f"  Categories corrected:  {category_corrected}")
                    print(f"  Remaining unverified:  {len(unverified) - i}")
                    print(f"{'='*60}\n")
                    return
                    
                else:
                    print("  ⚠️  Invalid choice. Use [a], [c], [g], [s], or [q]")
        
        print(f"\n{'='*60}")
        print(f"  SESSION COMPLETE")
        print(f"{'='*60}")
        print(f"  Products reviewed:     {reviewed_count}")
        print(f"  Tags corrected:        {corrected_count}")
        print(f"  Categories corrected:  {category_corrected}")
        print(f"{'='*60}\n")

    def export_training_data(self, output_path, verified_only=True):
        """Export data in JSONL format for fine-tuning"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        if verified_only:
            cur.execute('''
                SELECT handle, title, detected_category, ai_prompt, 
                       final_tags, human_corrected_tags, human_corrected_category
                FROM products 
                WHERE human_verified = 1
            ''')
        else:
            cur.execute('''
                SELECT handle, title, detected_category, ai_prompt, 
                       final_tags, human_corrected_tags, human_corrected_category
                FROM products
            ''')
        
        rows = cur.fetchall()
        
        if not rows:
            print(f"⚠️  No {'verified ' if verified_only else ''}products to export!")
            return 0
        
        exported = 0
        with open(output_path, 'w') as f:
            for row in rows:
                handle, title, category, prompt, final_tags_json, corrected_json, corrected_cat = row
                
                # Use corrected tags if available, otherwise final tags
                if corrected_json:
                    try:
                        tags = json.loads(corrected_json)
                    except:
                        tags = []
                elif final_tags_json:
                    try:
                        tags = json.loads(final_tags_json)
                    except:
                        tags = []
                else:
                    continue
                
                # Use corrected category if available
                final_category = corrected_cat if corrected_cat else category
                
                if not tags or not prompt:
                    continue
                
                # Format as training example
                training_example = {
                    "prompt": prompt,
                    "completion": ", ".join(tags),
                    "metadata": {
                        "handle": handle,
                        "category": final_category
                    }
                }
                
                f.write(json.dumps(training_example) + "\n")
                exported += 1
        
        print(f"✅ Exported {exported} training examples to {output_path}")
        return exported

    def clear_database(self):
        """Clear all records from the audit database"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        if self.thread_safe:
            with self._lock:
                cur.execute("DELETE FROM products")
                cur.execute("DELETE FROM runs")
                conn.commit()
        else:
            cur.execute("DELETE FROM products")
            cur.execute("DELETE FROM runs")
            conn.commit()
        
        print("✅ Audit database cleared.")

    def close(self):
        try:
            if self.thread_safe:
                if hasattr(self._local, 'conn') and self._local.conn:
                    self._local.conn.close()
            else:
                self.conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Tag Audit Database Management")
    parser.add_argument("--review", action="store_true", help="Start interactive review session")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--export", type=str, metavar="FILE", help="Export training data to JSONL file")
    parser.add_argument("--export-all", action="store_true", help="Export all products (not just verified)")
    parser.add_argument("--clear", action="store_true", help="Clear all records from database")
    parser.add_argument("--db", type=str, default="output/tag_audit.sqlite3", help="Database file path")
    
    args = parser.parse_args()
    
    db = TagAuditDB(args.db)
    
    if args.stats:
        db.print_stats()
    elif args.review:
        db.review_session()
    elif args.export:
        db.export_training_data(args.export, verified_only=not args.export_all)
    elif args.clear:
        confirm = input("⚠️  This will delete all audit records. Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            db.clear_database()
        else:
            print("Cancelled.")
    else:
        parser.print_help()
        print("\n")
        db.print_stats()
