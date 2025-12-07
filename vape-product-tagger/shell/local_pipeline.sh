#!/bin/bash
# Local Pipeline Execution Script
# One-command local execution with Ollama checks and automated workflow

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
INPUT_FILE="$1"
OUTPUT_DIR="${2:-output}"
LIMIT="${3:-}"
WORKERS="${4:-4}"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}🚀 Vape Product Tagger - Local Pipeline${NC}"
echo -e "${BLUE}======================================================================${NC}"

# Check if input file provided
if [ -z "$INPUT_FILE" ]; then
    echo -e "${RED}❌ Error: Input file required${NC}"
    echo ""
    echo "Usage: $0 <input_csv> [output_dir] [limit] [workers]"
    echo ""
    echo "Examples:"
    echo "  $0 products.csv"
    echo "  $0 products.csv output 100 4"
    echo "  $0 data/products.csv output/ 50 8"
    exit 1
fi

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}❌ Error: Input file not found: $INPUT_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Input file: $INPUT_FILE"
echo -e "${GREEN}✓${NC} Output directory: $OUTPUT_DIR"

# Check if Ollama is running
echo ""
echo -e "${BLUE}Checking Ollama service...${NC}"
if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Ollama not running${NC}"
    echo -e "${YELLOW}Starting Ollama service...${NC}"
    
    # Try to start Ollama
    if command -v ollama &> /dev/null; then
        ollama serve > /tmp/ollama.log 2>&1 &
        sleep 3
        
        if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Ollama started successfully"
        else
            echo -e "${RED}❌ Failed to start Ollama${NC}"
            echo -e "${YELLOW}Continuing with rule-based tagging only${NC}"
            NO_AI="--no-ai"
        fi
    else
        echo -e "${RED}❌ Ollama not installed${NC}"
        echo -e "${YELLOW}Continuing with rule-based tagging only${NC}"
        NO_AI="--no-ai"
    fi
else
    echo -e "${GREEN}✓${NC} Ollama is running"
    
    # Check if models are available
    echo ""
    echo -e "${BLUE}Checking required models...${NC}"
    
    MODELS=("mistral:latest" "gpt-oss:latest" "llama3.1:latest")
    MISSING_MODELS=()
    
    for model in "${MODELS[@]}"; do
        if ollama list 2>/dev/null | grep -q "$model"; then
            echo -e "${GREEN}✓${NC} $model"
        else
            echo -e "${YELLOW}⚠️${NC}  $model not found"
            MISSING_MODELS+=("$model")
        fi
    done
    
    if [ ${#MISSING_MODELS[@]} -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Missing models: ${MISSING_MODELS[*]}${NC}"
        echo -e "${BLUE}Pull models with:${NC}"
        for model in "${MISSING_MODELS[@]}"; do
            echo "  ollama pull $model"
        done
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Create output directories
echo ""
echo -e "${BLUE}Creating output directories...${NC}"
mkdir -p "$OUTPUT_DIR"
mkdir -p logs
mkdir -p cache
echo -e "${GREEN}✓${NC} Directories created"

# Navigate to project root
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo ""
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source venv/bin/activate
    echo -e "${GREEN}✓${NC} Virtual environment activated"
fi

# Check Python dependencies
echo ""
echo -e "${BLUE}Checking Python dependencies...${NC}"
if ! python -c "import pandas" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  pandas not installed${NC}"
    echo -e "${BLUE}Installing dependencies...${NC}"
    pip install -q -r requirements.txt
fi
echo -e "${GREEN}✓${NC} Dependencies ready"

# Build pipeline command
PIPELINE_CMD="python scripts/run_pipeline.py --input \"$INPUT_FILE\" --output-dir \"$OUTPUT_DIR\" $NO_AI"

if [ -n "$LIMIT" ]; then
    PIPELINE_CMD="$PIPELINE_CMD --limit $LIMIT"
fi

if [ -n "$WORKERS" ] && [ "$WORKERS" -gt 1 ]; then
    PIPELINE_CMD="$PIPELINE_CMD --workers $WORKERS"
fi

# Run pipeline
echo ""
echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}🏷️  Running Tagging Pipeline${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo "Command: $PIPELINE_CMD"
echo ""

# Execute with error handling
if eval "$PIPELINE_CMD"; then
    echo ""
    echo -e "${GREEN}======================================================================${NC}"
    echo -e "${GREEN}✅ Pipeline completed successfully!${NC}"
    echo -e "${GREEN}======================================================================${NC}"
    
    # Show output files
    echo ""
    echo -e "${BLUE}📁 Output files:${NC}"
    ls -lh "$OUTPUT_DIR"/*.csv 2>/dev/null | tail -3 || echo "No CSV files found"
    
    # Check for review file
    REVIEW_FILE=$(ls -t "$OUTPUT_DIR"/*_tagged_review.csv 2>/dev/null | head -1)
    
    if [ -f "$REVIEW_FILE" ]; then
        REVIEW_COUNT=$(tail -n +2 "$REVIEW_FILE" | wc -l)
        
        if [ "$REVIEW_COUNT" -gt 0 ]; then
            echo ""
            echo -e "${YELLOW}======================================================================${NC}"
            echo -e "${YELLOW}⚠️  $REVIEW_COUNT products need manual review${NC}"
            echo -e "${YELLOW}======================================================================${NC}"
            echo ""
            echo -e "${BLUE}Launch review interface?${NC}"
            read -p "(y/n) " -n 1 -r
            echo
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                AUDIT_DB="$OUTPUT_DIR/audit.db"
                if [ -f "$AUDIT_DB" ]; then
                    echo ""
                    python scripts/review_interface.py --audit-db "$AUDIT_DB"
                else
                    echo -e "${YELLOW}Audit database not found, using CSV file${NC}"
                    python scripts/review_interface.py --audit-db "$AUDIT_DB" --review-csv "$REVIEW_FILE"
                fi
            fi
        fi
    fi
    
    echo ""
    echo -e "${BLUE}💡 Next steps:${NC}"
    echo "  1. Review output files in $OUTPUT_DIR/"
    echo "  2. Import *_tagged_clean.csv to Shopify"
    echo "  3. Review *_tagged_review.csv before importing"
    echo ""
    
else
    echo ""
    echo -e "${RED}======================================================================${NC}"
    echo -e "${RED}❌ Pipeline failed${NC}"
    echo -e "${RED}======================================================================${NC}"
    echo ""
    echo "Check logs in logs/ directory for details"
    exit 1
fi

# Cleanup
if [ -f /tmp/ollama.log ]; then
    echo ""
    echo -e "${BLUE}Ollama log:${NC}"
    tail -20 /tmp/ollama.log
fi
