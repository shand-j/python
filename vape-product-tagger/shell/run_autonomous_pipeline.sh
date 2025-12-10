#!/bin/bash
# Autonomous Pipeline Wrapper for Vast.ai
# ========================================
# Runs the complete autonomous tagging pipeline with optimal settings

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
INPUT_CSV=""
OUTPUT_DIR="output/autonomous"
CONFIG_FILE="config.env"
NO_AI=false
LIMIT=""
TARGET=0.90
MAX_ITERATIONS=3
VERBOSE=false

# Help function
show_help() {
    cat << EOF
Autonomous AI Tagging Pipeline Runner
=====================================

Usage: $0 [options]

Options:
  -i, --input FILE          Input CSV file (required)
  -o, --output DIR          Output directory (default: output/autonomous)
  -c, --config FILE         Config file (default: config.env)
  --no-ai                   Disable AI tagging
  -l, --limit N             Process only first N products
  -t, --target ACCURACY     Target accuracy 0.0-1.0 (default: 0.90)
  -m, --max-iterations N    Max improvement iterations (default: 3)
  -v, --verbose             Verbose logging
  -h, --help                Show this help

Examples:
  # Basic usage
  $0 -i products.csv

  # Custom target and iterations
  $0 -i products.csv -t 0.92 -m 5

  # Test with limited dataset
  $0 -i products.csv -l 100 -v

  # Rule-based only
  $0 -i products.csv --no-ai

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input)
            INPUT_CSV="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --no-ai)
            NO_AI=true
            shift
            ;;
        -l|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -m|--max-iterations)
            MAX_ITERATIONS="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$INPUT_CSV" ]; then
    echo -e "${RED}Error: Input CSV file is required${NC}"
    show_help
    exit 1
fi

if [ ! -f "$INPUT_CSV" ]; then
    echo -e "${RED}Error: Input file not found: $INPUT_CSV${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Autonomous AI Tagging Pipeline${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Ollama is running (if AI enabled)
if [ "$NO_AI" = false ]; then
    echo -e "${YELLOW}Checking Ollama service...${NC}"
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama is running${NC}"
    else
        echo -e "${RED}✗ Ollama is not running${NC}"
        echo -e "${YELLOW}Starting Ollama service...${NC}"
        nohup ollama serve > /dev/null 2>&1 &
        sleep 5
        
        if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Ollama started${NC}"
        else
            echo -e "${RED}✗ Failed to start Ollama${NC}"
            echo -e "${YELLOW}Running with rule-based tagging only${NC}"
            NO_AI=true
        fi
    fi
fi

# Build command
CMD="python $PROJECT_ROOT/scripts/autonomous_pipeline.py"
CMD="$CMD --input $INPUT_CSV"
CMD="$CMD --output $OUTPUT_DIR"

if [ -f "$CONFIG_FILE" ]; then
    CMD="$CMD --config $CONFIG_FILE"
fi

if [ "$NO_AI" = true ]; then
    CMD="$CMD --no-ai"
fi

if [ -n "$LIMIT" ]; then
    CMD="$CMD --limit $LIMIT"
fi

CMD="$CMD --target $TARGET"
CMD="$CMD --max-iterations $MAX_ITERATIONS"

if [ "$VERBOSE" = true ]; then
    CMD="$CMD --verbose"
fi

# Display configuration
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo -e "  Input CSV:       $INPUT_CSV"
echo -e "  Output Dir:      $OUTPUT_DIR"
echo -e "  Config File:     $CONFIG_FILE"
echo -e "  AI Enabled:      $([ "$NO_AI" = true ] && echo "No" || echo "Yes")"
echo -e "  Target Accuracy: ${TARGET} (${TARGET}%)"
echo -e "  Max Iterations:  $MAX_ITERATIONS"
[ -n "$LIMIT" ] && echo -e "  Limit:           $LIMIT products"
[ "$VERBOSE" = true ] && echo -e "  Verbose:         Enabled"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run pipeline
echo -e "${GREEN}Starting pipeline...${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

START_TIME=$(date +%s)

# Execute
eval $CMD
EXIT_CODE=$?

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Pipeline Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Exit Code: $EXIT_CODE"
echo -e "Duration:  ${DURATION}s"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Pipeline completed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Output files:${NC}"
    ls -lh "$OUTPUT_DIR"/*.csv 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    echo ""
    echo -e "${YELLOW}Audit databases:${NC}"
    ls -lh "$OUTPUT_DIR"/*.db 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
else
    echo -e "${RED}❌ Pipeline failed with exit code $EXIT_CODE${NC}"
    echo ""
    echo -e "${YELLOW}Check logs for details:${NC}"
    ls -lht logs/*.log 2>/dev/null | head -3 | awk '{print "  " $9}'
fi

echo ""
exit $EXIT_CODE
