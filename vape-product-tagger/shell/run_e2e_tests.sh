#!/bin/bash
# End-to-End Pipeline Testing Script
# Runs comprehensive tests on the vape product tagging pipeline

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Logging function
log_test() {
    local status=$1
    local message=$2
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓ TEST $TESTS_TOTAL: $message${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ TEST $TESTS_TOTAL: $message${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Vape Product Tagger - E2E Testing Suite                 ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Starting at: $(date)${NC}"
echo ""

# Find Python executable
if [ -d "venv/bin" ]; then
    PYTHON="venv/bin/python3"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
else
    PYTHON="/opt/homebrew/bin/python3"
fi

echo -e "${YELLOW}Using Python: $PYTHON${NC}"
$PYTHON --version
echo ""

# Create test directories
TEST_OUTPUT_DIR="output/e2e_tests"
TEST_DB_DIR="persistance/e2e_tests"
TEST_LOG_DIR="logs/e2e_tests"
mkdir -p "$TEST_OUTPUT_DIR" "$TEST_DB_DIR" "$TEST_LOG_DIR" /tmp/tagger_tests

# Cleanup function
cleanup_tests() {
    echo -e "\n${YELLOW}Cleaning up test files...${NC}"
    rm -f /tmp/tagger_tests/*.csv
}
trap cleanup_tests EXIT

echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 1: Prerequisites Check${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Check Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    log_test "PASS" "Ollama service is running"
else
    log_test "FAIL" "Ollama service is NOT running"
    echo -e "${RED}Cannot proceed without Ollama. Start it with: ollama serve${NC}"
    exit 1
fi

# Test 2: Check models
if ollama list | grep -q "llama3.1:latest"; then
    log_test "PASS" "Required model (llama3.1:latest) is available"
else
    log_test "FAIL" "Required model (llama3.1:latest) NOT available"
    exit 1
fi

# Test 3: Check input data
if [ -f "data/input/products.csv" ]; then
    PRODUCT_COUNT=$(wc -l < data/input/products.csv | tr -d ' ')
    log_test "PASS" "Input data exists ($PRODUCT_COUNT lines)"
else
    log_test "FAIL" "Input data NOT found (data/input/products.csv)"
    exit 1
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 2: Small Batch Validation (5 products)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

$PYTHON scripts/1_main.py \
    --input data/input/products.csv \
    --output "$TEST_OUTPUT_DIR/test_5.csv" \
    --audit-db "$TEST_DB_DIR/test_5.db" \
    --workers 1 \
    --limit 5 \
    --verbose > "$TEST_LOG_DIR/test_5.log" 2>&1

# Test 4: Output file created
if [ -f "$TEST_OUTPUT_DIR/test_5.csv" ]; then
    OUTPUT_LINES=$(wc -l < "$TEST_OUTPUT_DIR/test_5.csv" | tr -d ' ')
    if [ "$OUTPUT_LINES" -ge 2 ]; then
        log_test "PASS" "Output CSV created with $OUTPUT_LINES lines (including header)"
    else
        log_test "FAIL" "Output CSV has insufficient data"
    fi
else
    log_test "FAIL" "Output CSV NOT created"
fi

# Test 5: Audit database created
if [ -f "$TEST_DB_DIR/test_5.db" ]; then
    DB_PRODUCTS=$(sqlite3 "$TEST_DB_DIR/test_5.db" "SELECT COUNT(*) FROM products" 2>/dev/null || echo "0")
    if [ "$DB_PRODUCTS" -ge 5 ]; then
        log_test "PASS" "Audit database created with $DB_PRODUCTS products"
    else
        log_test "FAIL" "Audit database has insufficient products ($DB_PRODUCTS)"
    fi
else
    log_test "FAIL" "Audit database NOT created"
fi

# Test 6: AI tagging is active (not skipped)
AI_SKIPPED=$(grep "AI calls skipped:" "$TEST_LOG_DIR/test_5.log" | grep -o "[0-9]*\.[0-9]*%" | head -1 || echo "100.0%")
if [[ "$AI_SKIPPED" =~ ^0\.0 ]]; then
    log_test "PASS" "AI-first workflow confirmed (0% skipped)"
else
    log_test "FAIL" "AI tagging being skipped ($AI_SKIPPED)"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 3: Category-Specific Tests${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 7: CBD products
echo -e "${YELLOW}Testing CBD products...${NC}"
head -1 data/input/products.csv > /tmp/tagger_tests/cbd_test.csv
grep -i "cbd" data/input/products.csv | head -5 >> /tmp/tagger_tests/cbd_test.csv

$PYTHON scripts/1_main.py \
    --input /tmp/tagger_tests/cbd_test.csv \
    --output "$TEST_OUTPUT_DIR/test_cbd.csv" \
    --audit-db "$TEST_DB_DIR/test_cbd.db" \
    --workers 1 \
    --verbose > "$TEST_LOG_DIR/test_cbd.log" 2>&1

CBD_COUNT=$(sqlite3 "$TEST_DB_DIR/test_cbd.db" "SELECT COUNT(*) FROM products WHERE category='CBD'" 2>/dev/null || echo "0")
if [ "$CBD_COUNT" -gt 0 ]; then
    log_test "PASS" "CBD products categorized ($CBD_COUNT products)"
    
    # Check for CBD-specific tags
    CBD_WITH_STRENGTH=$(sqlite3 "$TEST_DB_DIR/test_cbd.db" "SELECT COUNT(*) FROM products WHERE category='CBD' AND final_tags LIKE '%mg%'" 2>/dev/null || echo "0")
    if [ "$CBD_WITH_STRENGTH" -gt 0 ]; then
        log_test "PASS" "CBD strength extraction working ($CBD_WITH_STRENGTH products)"
    else
        log_test "FAIL" "CBD strength extraction NOT working"
    fi
else
    log_test "FAIL" "CBD products NOT categorized"
fi

# Test 8: E-liquids
echo -e "${YELLOW}Testing e-liquid products...${NC}"
head -1 data/input/products.csv > /tmp/tagger_tests/eliquid_test.csv
grep -iE "shortfill|e-liquid" data/input/products.csv | head -5 >> /tmp/tagger_tests/eliquid_test.csv

$PYTHON scripts/1_main.py \
    --input /tmp/tagger_tests/eliquid_test.csv \
    --output "$TEST_OUTPUT_DIR/test_eliquid.csv" \
    --audit-db "$TEST_DB_DIR/test_eliquid.db" \
    --workers 1 \
    --verbose > "$TEST_LOG_DIR/test_eliquid.log" 2>&1

ELIQUID_COUNT=$(sqlite3 "$TEST_DB_DIR/test_eliquid.db" "SELECT COUNT(*) FROM products WHERE category='e-liquid'" 2>/dev/null || echo "0")
if [ "$ELIQUID_COUNT" -gt 0 ]; then
    log_test "PASS" "E-liquid products categorized ($ELIQUID_COUNT products)"
    
    # Check for VG/PG ratios
    VGPG_COUNT=$(sqlite3 "$TEST_DB_DIR/test_eliquid.db" "SELECT COUNT(*) FROM products WHERE category='e-liquid' AND final_tags LIKE '%/%'" 2>/dev/null || echo "0")
    if [ "$VGPG_COUNT" -gt 0 ]; then
        log_test "PASS" "VG/PG ratio detection working ($VGPG_COUNT products)"
    else
        log_test "FAIL" "VG/PG ratio detection NOT working"
    fi
else
    log_test "FAIL" "E-liquid products NOT categorized"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 4: Edge Cases & Error Handling${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 9: Shortfill detection accuracy
echo -e "${YELLOW}Testing shortfill detection...${NC}"
head -1 data/input/products.csv > /tmp/tagger_tests/shortfill_test.csv

# Add a nic shot (should NOT get shortfill tag)
grep "nic.*shot.*10ml" data/input/products.csv | head -1 >> /tmp/tagger_tests/shortfill_test.csv

# Add a real shortfill (should GET shortfill tag)
grep -i "shortfill" data/input/products.csv | grep -iE "50ml|100ml" | head -1 >> /tmp/tagger_tests/shortfill_test.csv

$PYTHON scripts/1_main.py \
    --input /tmp/tagger_tests/shortfill_test.csv \
    --output "$TEST_OUTPUT_DIR/test_shortfill.csv" \
    --audit-db "$TEST_DB_DIR/test_shortfill.db" \
    --workers 1 \
    --verbose > "$TEST_LOG_DIR/test_shortfill.log" 2>&1

# Check that nic shot doesn't have shortfill tag
NICSHOT_SHORTFILL=$(grep -i "nic.*shot" "$TEST_OUTPUT_DIR/test_shortfill.csv" | grep -c "shortfill" || echo "0")
# Check that actual shortfill has shortfill tag
SHORTFILL_TAGGED=$(grep -i "shortfill" "$TEST_OUTPUT_DIR/test_shortfill.csv" | grep -c "shortfill" || echo "0")

if [ "$NICSHOT_SHORTFILL" -eq 0 ] && [ "$SHORTFILL_TAGGED" -gt 0 ]; then
    log_test "PASS" "Shortfill detection accurate (nic shots excluded, shortfills included)"
else
    log_test "FAIL" "Shortfill detection inaccurate"
fi

# Test 10: Missing data handling
echo -e "${YELLOW}Testing minimal data products...${NC}"
head -1 data/input/products.csv > /tmp/tagger_tests/minimal_test.csv
awk -F',' 'NR>1 && length($3) < 100 {print; if(++count==3) exit}' data/input/products.csv >> /tmp/tagger_tests/minimal_test.csv

$PYTHON scripts/1_main.py \
    --input /tmp/tagger_tests/minimal_test.csv \
    --output "$TEST_OUTPUT_DIR/test_minimal.csv" \
    --audit-db "$TEST_DB_DIR/test_minimal.db" \
    --workers 1 \
    --verbose > "$TEST_LOG_DIR/test_minimal.log" 2>&1 || true

# Should not crash, even with minimal data
if [ -f "$TEST_OUTPUT_DIR/test_minimal.csv" ]; then
    log_test "PASS" "Minimal data products handled gracefully"
else
    log_test "FAIL" "Pipeline crashed on minimal data"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 5: Performance & Scalability${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 11: Medium batch (50 products, measure performance)
echo -e "${YELLOW}Testing medium batch (50 products, 2 workers)...${NC}"
START_TIME=$(date +%s)

$PYTHON scripts/1_main.py \
    --input data/input/products.csv \
    --output "$TEST_OUTPUT_DIR/test_50.csv" \
    --audit-db "$TEST_DB_DIR/test_50.db" \
    --workers 2 \
    --limit 50 \
    --verbose > "$TEST_LOG_DIR/test_50.log" 2>&1

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
RATE=$(awk "BEGIN {printf \"%.2f\", 50/$DURATION*60}")

PROCESSED=$(sqlite3 "$TEST_DB_DIR/test_50.db" "SELECT COUNT(*) FROM products" 2>/dev/null || echo "0")
if [ "$PROCESSED" -ge 45 ]; then
    log_test "PASS" "Medium batch processed ($PROCESSED/50 products in ${DURATION}s, ${RATE} products/min)"
else
    log_test "FAIL" "Medium batch incomplete ($PROCESSED/50 products)"
fi

# Check average confidence
AVG_CONFIDENCE=$(sqlite3 "$TEST_DB_DIR/test_50.db" "SELECT ROUND(AVG(primary_model_confidence), 2) FROM products WHERE primary_model_confidence IS NOT NULL" 2>/dev/null || echo "0")
if (( $(echo "$AVG_CONFIDENCE >= 0.70" | bc -l) )); then
    log_test "PASS" "Average confidence acceptable ($AVG_CONFIDENCE)"
else
    log_test "FAIL" "Average confidence too low ($AVG_CONFIDENCE)"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 6: Output Validation${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 12: CSV structure validation
echo -e "${YELLOW}Validating CSV structure...${NC}"
HEADER=$(head -1 "$TEST_OUTPUT_DIR/test_50.csv")
if [[ "$HEADER" == *"Handle"* ]] && [[ "$HEADER" == *"Tags"* ]]; then
    log_test "PASS" "CSV has required columns (Handle, Tags)"
else
    log_test "FAIL" "CSV missing required columns"
fi

# Test 13: Tag format validation
INVALID_TAGS=$(grep -vE '^[^,]+,[^,]*,"[a-zA-Z0-9_ ,/\-]+"$' "$TEST_OUTPUT_DIR/test_50.csv" | tail -n +2 | wc -l | tr -d ' ')
if [ "$INVALID_TAGS" -eq 0 ]; then
    log_test "PASS" "All tags properly formatted"
else
    log_test "FAIL" "Found $INVALID_TAGS rows with invalid tag format"
fi

# Test 14: Database schema validation
TABLES=$(sqlite3 "$TEST_DB_DIR/test_50.db" ".tables" 2>/dev/null)
if [[ "$TABLES" == *"products"* ]] && [[ "$TABLES" == *"runs"* ]]; then
    log_test "PASS" "Audit database has required tables"
else
    log_test "FAIL" "Audit database missing required tables"
fi

# Test 15: Category distribution
echo -e "${YELLOW}Checking category distribution...${NC}"
CATEGORIZED=$(sqlite3 "$TEST_DB_DIR/test_50.db" "SELECT COUNT(*) FROM products WHERE category IS NOT NULL" 2>/dev/null || echo "0")
TOTAL=$(sqlite3 "$TEST_DB_DIR/test_50.db" "SELECT COUNT(*) FROM products" 2>/dev/null || echo "1")
CATEGORIZED_PCT=$(awk "BEGIN {printf \"%.0f\", $CATEGORIZED/$TOTAL*100}")

if [ "$CATEGORIZED_PCT" -ge 80 ]; then
    log_test "PASS" "Good categorization rate (${CATEGORIZED_PCT}%)"
else
    log_test "FAIL" "Low categorization rate (${CATEGORIZED_PCT}%)"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 7: Integration Tests${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 16: Training data export
echo -e "${YELLOW}Testing training data export...${NC}"
if $PYTHON scripts/prepare_training_data.py \
    --audit-db "$TEST_DB_DIR/test_50.db" \
    --output "$TEST_OUTPUT_DIR/training_export.csv" \
    --min-confidence 0.7 > "$TEST_LOG_DIR/training_export.log" 2>&1; then
    
    if [ -f "$TEST_OUTPUT_DIR/training_export_train.csv" ]; then
        TRAIN_ROWS=$(wc -l < "$TEST_OUTPUT_DIR/training_export_train.csv" | tr -d ' ')
        log_test "PASS" "Training data export successful ($TRAIN_ROWS training examples)"
    else
        log_test "FAIL" "Training data export created no output"
    fi
else
    log_test "FAIL" "Training data export script failed"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}TEST SUMMARY${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Total Tests: $TESTS_TOTAL${NC}"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ ALL TESTS PASSED - PIPELINE READY FOR PRODUCTION     ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    EXIT_CODE=0
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ❌ SOME TESTS FAILED - REVIEW LOGS BEFORE PRODUCTION    ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
    EXIT_CODE=1
fi

echo ""
echo -e "${BLUE}Test artifacts:${NC}"
echo "   Outputs: $TEST_OUTPUT_DIR/"
echo "   Databases: $TEST_DB_DIR/"
echo "   Logs: $TEST_LOG_DIR/"
echo ""
echo -e "${BLUE}Completed at: $(date)${NC}"
echo ""

exit $EXIT_CODE
