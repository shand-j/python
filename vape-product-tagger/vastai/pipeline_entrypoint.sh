#!/bin/bash
# Vast.ai Pipeline Entrypoint
# Automated execution script for Vast.ai GPU instances

set -e

echo "========================================================================"
echo "🚀 Vape Product Tagger - Vast.ai Pipeline"
echo "========================================================================"
echo ""

# Environment setup
export DEBIAN_FRONTEND=noninteractive
export WORKSPACE=/workspace
export DATA_DIR=$WORKSPACE/data
export OUTPUT_DIR=$WORKSPACE/output
export REPO_DIR=$WORKSPACE/vape-product-tagger

# Create directories
mkdir -p $DATA_DIR
mkdir -p $OUTPUT_DIR
mkdir -p $WORKSPACE/logs

echo "✓ Workspace directories created"

# Check if repo exists, clone if not
if [ ! -d "$REPO_DIR" ]; then
    echo ""
    echo "📥 Cloning repository..."
    cd $WORKSPACE
    git clone https://github.com/shand-j/python.git temp-repo
    mv temp-repo/vape-product-tagger $REPO_DIR
    rm -rf temp-repo
    echo "✓ Repository cloned"
else
    echo ""
    echo "📥 Updating repository..."
    cd $REPO_DIR
    git pull
    echo "✓ Repository updated"
fi

cd $REPO_DIR

# Setup Python environment
echo ""
echo "🐍 Setting up Python environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

source venv/bin/activate
echo "✓ Virtual environment activated"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Setup Ollama
echo ""
echo "🤖 Setting up Ollama..."

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    echo "✓ Ollama installed"
else
    echo "✓ Ollama already installed"
fi

# Start Ollama service
echo ""
echo "Starting Ollama service..."
ollama serve > $WORKSPACE/logs/ollama.log 2>&1 &
OLLAMA_PID=$!
sleep 5

# Verify Ollama is running
if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "✓ Ollama service started (PID: $OLLAMA_PID)"
else
    echo "❌ Failed to start Ollama service"
    exit 1
fi

# Pull required models
echo ""
echo "📥 Pulling AI models..."

MODELS=("mistral:latest" "gpt-oss:latest" "llama3.1:latest")

for model in "${MODELS[@]}"; do
    echo "  Pulling $model..."
    if ollama pull $model > /dev/null 2>&1; then
        echo "  ✓ $model ready"
    else
        echo "  ⚠️  Failed to pull $model (continuing anyway)"
    fi
done

# Find input CSV
echo ""
echo "🔍 Looking for input data..."

INPUT_FILE=""
if [ -f "$DATA_DIR/products.csv" ]; then
    INPUT_FILE="$DATA_DIR/products.csv"
elif [ -f "$DATA_DIR/input.csv" ]; then
    INPUT_FILE="$DATA_DIR/input.csv"
else
    # Find any CSV in data dir
    INPUT_FILE=$(find $DATA_DIR -name "*.csv" -type f | head -1)
fi

if [ -z "$INPUT_FILE" ]; then
    echo "❌ No input CSV found in $DATA_DIR"
    echo "Please mount a volume with products.csv to /workspace/data"
    exit 1
fi

echo "✓ Input file: $INPUT_FILE"

# Count products
PRODUCT_COUNT=$(tail -n +2 "$INPUT_FILE" | wc -l)
echo "✓ Found $PRODUCT_COUNT products to process"

# Setup configuration
echo ""
echo "⚙️  Configuring pipeline..."

if [ ! -f "config.env" ]; then
    cp config.env.example config.env
    echo "✓ Configuration file created"
fi

# Override config for Vast.ai
cat >> config.env << EOF

# Vast.ai overrides
PIPELINE_MODE=vastai
OUTPUT_DIR=$OUTPUT_DIR
LOGS_DIR=$WORKSPACE/logs
CACHE_DIR=$WORKSPACE/cache
EOF

echo "✓ Configuration updated for Vast.ai"

# Run pipeline
echo ""
echo "========================================================================"
echo "🏷️  Running Tagging Pipeline"
echo "========================================================================"
echo ""

START_TIME=$(date +%s)

# Execute pipeline with error handling
if python scripts/run_pipeline.py \
    --input "$INPUT_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --audit-db "$OUTPUT_DIR/audit.db" \
    --verbose; then
    
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    echo ""
    echo "========================================================================"
    echo "✅ Pipeline completed successfully!"
    echo "========================================================================"
    echo ""
    echo "⏱️  Execution time: ${ELAPSED}s"
    echo "📊 Rate: $(echo "scale=2; $PRODUCT_COUNT / $ELAPSED" | bc) products/s"
    
    # Show output files
    echo ""
    echo "📁 Output files:"
    ls -lh $OUTPUT_DIR/*.csv
    
    # Generate summary
    echo ""
    echo "📈 Generating summary report..."
    
    CLEAN_FILE=$(ls -t $OUTPUT_DIR/*_tagged_clean.csv 2>/dev/null | head -1)
    REVIEW_FILE=$(ls -t $OUTPUT_DIR/*_tagged_review.csv 2>/dev/null | head -1)
    UNTAGGED_FILE=$(ls -t $OUTPUT_DIR/*_untagged.csv 2>/dev/null | head -1)
    
    CLEAN_COUNT=0
    REVIEW_COUNT=0
    UNTAGGED_COUNT=0
    
    if [ -f "$CLEAN_FILE" ]; then
        CLEAN_COUNT=$(tail -n +2 "$CLEAN_FILE" | wc -l)
    fi
    
    if [ -f "$REVIEW_FILE" ]; then
        REVIEW_COUNT=$(tail -n +2 "$REVIEW_FILE" | wc -l)
    fi
    
    if [ -f "$UNTAGGED_FILE" ]; then
        UNTAGGED_COUNT=$(tail -n +2 "$UNTAGGED_FILE" | wc -l)
    fi
    
    echo ""
    echo "Results:"
    echo "  ✅ Clean: $CLEAN_COUNT ($(echo "scale=1; $CLEAN_COUNT * 100 / $PRODUCT_COUNT" | bc)%)"
    echo "  ⚠️  Review: $REVIEW_COUNT ($(echo "scale=1; $REVIEW_COUNT * 100 / $PRODUCT_COUNT" | bc)%)"
    echo "  ❌ Untagged: $UNTAGGED_COUNT ($(echo "scale=1; $UNTAGGED_COUNT * 100 / $PRODUCT_COUNT" | bc)%)"
    
    # Export training data if configured
    if grep -q "TRAINING_DATA_AUTO_EXPORT=true" config.env 2>/dev/null; then
        echo ""
        echo "📚 Exporting training data..."
        python scripts/prepare_training_data.py \
            --audit-db "$OUTPUT_DIR/audit.db" \
            --output "$OUTPUT_DIR/training_data.csv" \
            --min-confidence 0.8 \
            --stratify
        echo "✓ Training data exported"
    fi
    
    # Create completion marker
    touch $OUTPUT_DIR/.pipeline_complete
    echo "$(date)" > $OUTPUT_DIR/.pipeline_complete
    
    # Compress logs
    echo ""
    echo "📦 Compressing logs..."
    tar -czf $OUTPUT_DIR/logs.tar.gz -C $WORKSPACE logs/
    echo "✓ Logs compressed"
    
    echo ""
    echo "✅ All done! Output files available in $OUTPUT_DIR"
    
else
    echo ""
    echo "========================================================================"
    echo "❌ Pipeline failed"
    echo "========================================================================"
    echo ""
    echo "Check logs:"
    echo "  - Pipeline: $WORKSPACE/logs/"
    echo "  - Ollama: $WORKSPACE/logs/ollama.log"
    
    # Still compress logs for debugging
    tar -czf $OUTPUT_DIR/logs_error.tar.gz -C $WORKSPACE logs/ 2>/dev/null || true
    
    exit 1
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."

# Stop Ollama
if [ ! -z "$OLLAMA_PID" ]; then
    kill $OLLAMA_PID 2>/dev/null || true
    echo "✓ Ollama service stopped"
fi

echo ""
echo "🎉 Vast.ai pipeline execution complete!"
echo ""
echo "💡 Download output files from: $OUTPUT_DIR"
echo "   - *_tagged_clean.csv - Ready for Shopify import"
echo "   - *_tagged_review.csv - Needs human review"
echo "   - audit.db - Complete audit database"
echo "   - logs.tar.gz - Execution logs"
