#!/bin/bash
# =============================================================================
# Vast.ai vLLM Setup Script
# =============================================================================
# This script sets up the environment for training and evaluation on Vast.ai
# GPU instances using vLLM template.
#
# Usage:
#   chmod +x setup_vllm.sh
#   ./setup_vllm.sh
# =============================================================================

set -e

echo "🚀 Setting up vLLM environment on Vast.ai..."

# =============================================================================
# 1. System Dependencies
# =============================================================================
echo "📦 Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq git curl wget unzip sqlite3

# =============================================================================
# 2. Python Environment
# =============================================================================
echo "🐍 Setting up Python environment..."

# Upgrade pip
pip install --upgrade pip

# Install core dependencies
pip install -q pandas>=2.2.0
pip install -q python-dotenv>=1.0.0
pip install -q colorlog>=6.8.0
pip install -q ollama>=0.2.0
pip install -q requests>=2.31.0

# Install ML/AI dependencies for training
pip install -q torch>=2.0.0
pip install -q transformers>=4.35.0
pip install -q datasets>=2.14.0
pip install -q accelerate>=0.24.0
pip install -q peft>=0.6.0
pip install -q bitsandbytes>=0.41.0
pip install -q trl>=0.7.0

# Install vLLM (if not pre-installed on template)
pip install -q vllm>=0.2.0 || echo "⚠️ vLLM install may require specific CUDA version"

# =============================================================================
# 3. Data Directory Setup
# =============================================================================
echo "📂 Setting up data directories..."

DATA_DIR="${DATA_DIR:-/workspace/data}"
MODEL_DIR="${MODEL_DIR:-/workspace/models}"
OUTPUT_DIR="${OUTPUT_DIR:-/workspace/output}"
CHECKPOINT_DIR="${CHECKPOINT_DIR:-/workspace/checkpoints}"

mkdir -p "$DATA_DIR"
mkdir -p "$MODEL_DIR"
mkdir -p "$OUTPUT_DIR"
mkdir -p "$CHECKPOINT_DIR"

echo "   Data directory: $DATA_DIR"
echo "   Model directory: $MODEL_DIR"
echo "   Output directory: $OUTPUT_DIR"
echo "   Checkpoint directory: $CHECKPOINT_DIR"

# =============================================================================
# 4. Environment Variables
# =============================================================================
echo "🔧 Setting environment variables..."

export DATA_DIR="$DATA_DIR"
export MODEL_DIR="$MODEL_DIR"
export OUTPUT_DIR="$OUTPUT_DIR"
export CHECKPOINT_DIR="$CHECKPOINT_DIR"

# Add to bashrc for persistence
cat >> ~/.bashrc << EOF

# vLLM Training Environment
export DATA_DIR="$DATA_DIR"
export MODEL_DIR="$MODEL_DIR"
export OUTPUT_DIR="$OUTPUT_DIR"
export CHECKPOINT_DIR="$CHECKPOINT_DIR"
EOF

# =============================================================================
# 5. Verify GPU
# =============================================================================
echo "🖥️ Checking GPU availability..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
else
    echo "⚠️ nvidia-smi not found. GPU may not be available."
fi

# =============================================================================
# 6. Summary
# =============================================================================
echo ""
echo "✅ Setup complete!"
echo "=" 
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. Upload your data files to $DATA_DIR:"
echo "   - audit_training_dataset.csv"
echo "   - approved_tags.json"
echo ""
echo "2. Export training data as JSONL:"
echo "   python train_tag_model.py --input $DATA_DIR/audit_training_dataset.csv --output $DATA_DIR/training_data.jsonl"
echo ""
echo "3. Run training:"
echo "   python train_tag_model.py --train --output $DATA_DIR/training_data.jsonl --epochs 3 --batch-size 4 --output-dir $MODEL_DIR"
echo ""
echo "4. Evaluate results:"
echo "   python train_tag_model.py --evaluate --predictions $OUTPUT_DIR/predictions.jsonl --corrections $DATA_DIR/audit_training_dataset.csv"
echo ""
echo "📖 For full automation, run: ./run_all_vllm.sh"
