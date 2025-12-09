#!/bin/bash
#
# Verify Audit Database Schema and Contents
# Quick diagnostic for E2E test database issues
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}Audit Database Verification${NC}"
echo ""

# Check which databases exist
DB_DIR="persistance/e2e_tests"
echo -e "${YELLOW}Checking for audit databases in ${DB_DIR}/${NC}"
echo ""

for db_file in "$DB_DIR"/*.db; do
    if [ -f "$db_file" ]; then
        db_name=$(basename "$db_file")
        file_size=$(ls -lh "$db_file" | awk '{print $5}')
        
        echo -e "${GREEN}Found: ${db_name} (${file_size})${NC}"
        
        # Check tables
        echo -e "${CYAN}  Tables:${NC}"
        tables=$(sqlite3 "$db_file" ".tables" 2>&1)
        if [ -z "$tables" ]; then
            echo -e "${RED}    ⚠ No tables found!${NC}"
        else
            echo "    $tables"
        fi
        
        # Check row counts
        echo -e "${CYAN}  Row counts:${NC}"
        runs=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM runs" 2>/dev/null || echo "0")
        products=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM products" 2>/dev/null || echo "0")
        echo "    runs: $runs"
        echo "    products: $products"
        
        # Show sample data
        if [ "$products" -gt 0 ]; then
            echo -e "${CYAN}  Sample products (first 3):${NC}"
            sqlite3 -header -column "$db_file" "SELECT handle, final_tags, detected_category, ai_confidence FROM products LIMIT 3" 2>/dev/null || echo "    Error querying products"
        fi
        
        echo ""
    fi
done

# Check if any databases found
if ! ls "$DB_DIR"/*.db 1> /dev/null 2>&1; then
    echo -e "${RED}No database files found in ${DB_DIR}/${NC}"
    echo ""
    echo "Run E2E tests first:"
    echo "  ./shell/run_e2e_tests.sh"
fi
