"""
Unified Cache System for Vape Product Tagger

Provides a single SQLite database for caching AI-generated tags with:
- Product caching by content hash
- Tag frequency analytics
- Similar product discovery
- Tag reuse recommendations
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime


class UnifiedCache:
    """
    Unified cache system using SQLite for efficient tag storage and retrieval
    """
    
    def __init__(self, cache_file: Path, logger):
        """
        Initialize unified cache
        
        Args:
            cache_file: Path to SQLite cache file
            logger: Logger instance
        """
        self.cache_file = cache_file
        self.logger = logger
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        try:
            with sqlite3.connect(self.cache_file) as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_hash TEXT UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        tags JSON NOT NULL,
                        ai_tags JSON NOT NULL,
                        rule_tags JSON NOT NULL,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tag TEXT UNIQUE NOT NULL,
                        frequency INTEGER DEFAULT 1,
                        first_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_content_hash ON products(content_hash);
                    CREATE INDEX IF NOT EXISTS idx_tag ON tags(tag);
                    CREATE INDEX IF NOT EXISTS idx_frequency ON tags(frequency DESC);
                """)
            self.logger.debug("Cache database initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize cache database: {e}")
    
    def _get_content_hash(self, product_data: Dict) -> str:
        """
        Generate content hash for product data
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            str: SHA256 hash for stable caching
        """
        # Create stable string from title and description
        content = f"{product_data.get('title', '')}|{product_data.get('description', '')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]  # Use first 16 chars
    
    def get_cached_tags(self, product_data: Dict) -> Optional[Dict]:
        """
        Retrieve cached tags for product
        
        Args:
            product_data: Product information dictionary
        
        Returns:
            Optional[Dict]: Cached tag data or None
        """
        content_hash = self._get_content_hash(product_data)
        
        try:
            with sqlite3.connect(self.cache_file) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT ai_tags, rule_tags FROM products WHERE content_hash = ?",
                    (content_hash,)
                )
                
                result = cursor.fetchone()
                if result:
                    self.logger.debug(f"Cache hit for product: {product_data.get('title', 'Unknown')}")
                    return {
                        'ai_tags': json.loads(result['ai_tags']),
                        'rule_tags': json.loads(result['rule_tags'])
                    }
                    
        except Exception as e:
            self.logger.warning(f"Failed to retrieve cached tags: {e}")
        
        return None
    
    def save_tags(self, product_data: Dict, ai_tags: List[str], rule_tags: List[str]):
        """
        Save product tags to cache and update tag frequency
        
        Args:
            product_data: Product information dictionary
            ai_tags: AI-generated tags
            rule_tags: Rule-based tags
        """
        content_hash = self._get_content_hash(product_data)
        all_tags = set(ai_tags + rule_tags)
        
        try:
            with sqlite3.connect(self.cache_file) as conn:
                cursor = conn.cursor()
                
                # Save product cache
                cursor.execute("""
                    INSERT OR REPLACE INTO products 
                    (content_hash, title, description, tags, ai_tags, rule_tags, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    content_hash,
                    product_data.get('title', ''),
                    product_data.get('description', ''),
                    json.dumps(list(all_tags)),
                    json.dumps(ai_tags),
                    json.dumps(rule_tags)
                ))
                
                # Update tag frequencies
                for tag in all_tags:
                    cursor.execute("""
                        INSERT INTO tags (tag, frequency, first_used, last_used)
                        VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT(tag) DO UPDATE SET
                            frequency = frequency + 1,
                            last_used = CURRENT_TIMESTAMP
                    """, (tag,))
                
                conn.commit()
                self.logger.debug(f"Cached tags for product: {product_data.get('title', 'Unknown')}")
                
        except Exception as e:
            self.logger.error(f"Failed to save tags to cache: {e}")
    
    def get_popular_tags(self, limit: int = 50) -> List[Dict]:
        """
        Get most frequently used tags for analytics
        
        Args:
            limit: Maximum number of tags to return
        
        Returns:
            List of tag dictionaries with frequency data
        """
        try:
            with sqlite3.connect(self.cache_file) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT tag, frequency, first_used, last_used
                    FROM tags
                    ORDER BY frequency DESC, last_used DESC
                    LIMIT ?
                """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get popular tags: {e}")
            return []
    
    def find_similar_products(self, product_data: Dict, limit: int = 5) -> List[Dict]:
        """
        Find similar cached products based on shared tags
        
        Args:
            product_data: Product to find similar items for
            limit: Maximum number of similar products
        
        Returns:
            List of similar products with shared tag counts
        """
        content_hash = self._get_content_hash(product_data)
        
        try:
            with sqlite3.connect(self.cache_file) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # This is a simplified similarity - could be enhanced with more sophisticated matching
                cursor.execute("""
                    SELECT title, description, tags, cached_at
                    FROM products
                    WHERE content_hash != ? AND (
                        title LIKE ? OR 
                        description LIKE ? OR
                        json_extract(tags, '$') LIKE ?
                    )
                    ORDER BY cached_at DESC
                    LIMIT ?
                """, (
                    content_hash,
                    f"%{product_data.get('title', '').split()[0]}%",
                    f"%{product_data.get('description', '').split()[0]}%",
                    f"%{product_data.get('title', '').split()[0]}%",
                    limit
                ))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to find similar products: {e}")
            return []
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics for monitoring
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            with sqlite3.connect(self.cache_file) as conn:
                cursor = conn.cursor()
                
                # Get basic counts
                cursor.execute("SELECT COUNT(*) FROM products")
                product_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM tags")
                unique_tags = cursor.fetchone()[0]
                
                cursor.execute("SELECT SUM(frequency) FROM tags")
                total_tag_uses = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT MAX(cached_at) FROM products")
                last_cached = cursor.fetchone()[0]
                
                return {
                    'cached_products': product_count,
                    'unique_tags': unique_tags,
                    'total_tag_uses': total_tag_uses,
                    'last_cached': last_cached,
                    'cache_file_size': self.cache_file.stat().st_size if self.cache_file.exists() else 0
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def cleanup_old_entries(self, days_old: int = 30):
        """
        Clean up cache entries older than specified days
        
        Args:
            days_old: Remove entries older than this many days
        """
        try:
            with sqlite3.connect(self.cache_file) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM products 
                    WHERE cached_at < datetime('now', '-' || ? || ' days')
                """, (days_old,))
                
                deleted_products = cursor.rowcount
                
                # Clean up unused tags
                cursor.execute("""
                    DELETE FROM tags 
                    WHERE tag NOT IN (
                        SELECT DISTINCT json_each.value
                        FROM products, json_each(products.tags)
                    )
                """)
                
                deleted_tags = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"Cache cleanup: removed {deleted_products} products and {deleted_tags} unused tags")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup cache: {e}")