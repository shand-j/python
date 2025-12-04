import sqlite3
import json
from pathlib import Path
from datetime import datetime
import uuid


class TagAuditDB:
    def __init__(self, db_path='output/tag_audit.sqlite3'):
        self.db_path = db_path
        self._ensure_parent()
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()

    def _ensure_parent(self):
        p = Path(self.db_path)
        if not p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)

    def _create_tables(self):
        cur = self.conn.cursor()
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
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        )
        ''')
        self.conn.commit()
        
        # Migrate existing tables - add new columns if they don't exist
        self._migrate_schema()
    
    def _migrate_schema(self):
        """Add new columns to existing tables if they don't exist"""
        cur = self.conn.cursor()
        
        # Check existing columns in products table
        cur.execute("PRAGMA table_info(products)")
        existing_columns = {row[1] for row in cur.fetchall()}
        
        # New columns to add with their types
        new_columns = [
            ('ai_prompt', 'TEXT'),
            ('ai_model_output', 'TEXT'),
            ('ai_confidence', 'REAL'),
            ('ai_reasoning', 'TEXT'),
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                try:
                    cur.execute(f'ALTER TABLE products ADD COLUMN {col_name} {col_type}')
                    print(f"Added column {col_name} to products table")
                except sqlite3.OperationalError:
                    pass  # Column already exists
        
        self.conn.commit()

    def start_run(self, config=None):
        """Start a new run, return run_id"""
        run_id = str(uuid.uuid4())
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO runs (run_id, started_at, config, status)
            VALUES (?, ?, ?, ?)
        ''', (run_id, datetime.now().isoformat(), json.dumps(config or {}), 'running'))
        self.conn.commit()
        return run_id

    def complete_run(self, run_id):
        """Mark run as completed and set as latest"""
        cur = self.conn.cursor()
        # Unmark previous latest
        cur.execute('UPDATE runs SET is_latest = 0 WHERE is_latest = 1')
        # Mark this run as latest and completed
        cur.execute('''
            UPDATE runs SET completed_at = ?, is_latest = 1, status = 'completed'
            WHERE run_id = ?
        ''', (datetime.now().isoformat(), run_id))
        self.conn.commit()

    def get_latest_run(self):
        """Get the latest run_id"""
        cur = self.conn.cursor()
        cur.execute('SELECT run_id FROM runs WHERE is_latest = 1 ORDER BY started_at DESC LIMIT 1')
        row = cur.fetchone()
        return row[0] if row else None

    def get_run_status(self, run_id):
        """Get run status"""
        cur = self.conn.cursor()
        cur.execute('SELECT status FROM runs WHERE run_id = ?', (run_id,))
        row = cur.fetchone()
        return row[0] if row else None

    def insert_product(self, run_id, handle, title, csv_type, effective_type, description, rule_tags, ai_tags, final_tags, forced_category, device_evidence, skipped=0, skip_reason=None, ai_prompt=None, ai_model_output=None, ai_confidence=None, ai_reasoning=None):
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO products (
                run_id, handle, title, csv_type, effective_type, description,
                rule_tags, ai_tags, final_tags, forced_category, device_evidence,
                skipped, skip_reason, processed_at, ai_prompt, ai_model_output,
                ai_confidence, ai_reasoning
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
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
            ai_reasoning
        ))
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
