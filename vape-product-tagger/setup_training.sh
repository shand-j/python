#!/bin/bash
# =============================================================================
# Vast.ai QLoRA Training Setup Script
# =============================================================================
# Sets up the environment for QLoRA fine-tuning on Vast.ai GPU instances.
#
# Usage:
#   chmod +x setup_training.sh
#   ./setup_training.sh
# =============================================================================

set -e

echo "🚀 Setting up QLoRA training environment on Vast.ai..."

# =============================================================================
# 1. System Dependencies
# =============================================================================
echo "📦 Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq git curl wget sqlite3

# =============================================================================
# 2. Python Dependencies
# =============================================================================
echo "🐍 Installing Python dependencies..."

pip install --upgrade pip

# Install from requirements file if available
if [ -f "vastai/requirements-train.txt" ]; then
    pip install -r vastai/requirements-train.txt
else
    # Manual install
    pip install torch>=2.1.0 transformers>=4.36.0 datasets>=2.15.0 accelerate>=0.25.0
    pip install peft>=0.7.0 bitsandbytes>=0.41.0 trl>=0.7.0
    pip install huggingface_hub>=0.19.0 safetensors>=0.4.0
    pip install pandas>=2.0.0 scikit-learn>=1.3.0 tensorboard>=2.15.0
fi

# Optional: Flash Attention 2 (faster training)
pip install flash-attn --no-build-isolation 2>/dev/null || echo "⚠️ flash-attn not installed (optional)"

# =============================================================================
# 3. Directory Setup
# =============================================================================
echo "📂 Setting up directories..."

mkdir -p /workspace/data
mkdir -p /workspace/models
mkdir -p /workspace/output
mkdir -p /workspace/checkpoints

# =============================================================================
# 4. Hugging Face Login
# =============================================================================
echo "🔐 Checking HF Hub authentication..."

if [ -n "$HF_TOKEN" ]; then
    echo "   Logging into Hugging Face Hub..."
    huggingface-cli login --token "$HF_TOKEN" --add-to-git-credential
    echo "   ✅ Logged in to HF Hub"
else
    echo "   ⚠️ HF_TOKEN not set. Set it for gated models (Llama 3.1) and --push-to-hub"
    echo "   Run: export HF_TOKEN=hf_xxx"
fi

# =============================================================================
# 5. GPU Check
# =============================================================================
echo "🖥️ Checking GPU..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
    
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    if [ "$VRAM" -lt 20000 ]; then
        echo "⚠️ Warning: Less than 24GB VRAM detected. QLoRA with Llama 3.1 8B may fail."
    else
        echo "✅ VRAM sufficient for Llama 3.1 8B QLoRA"
    fi
else
    echo "❌ nvidia-smi not found. GPU required for training."
    exit 1
fi

# =============================================================================
# 6. Verify Installation
# =============================================================================
echo "🔍 Verifying installation..."

python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
python3 -c "import transformers; print(f'Transformers: {transformers.__version__}')"
python3 -c "import peft; print(f'PEFT: {peft.__version__}')"
python3 -c "import trl; print(f'TRL: {trl.__version__}')"
python3 -c "import bitsandbytes; print(f'BitsAndBytes: {bitsandbytes.__version__}')"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy training data to /workspace/data/"
echo "  2. Set HF_TOKEN and HF_REPO_ID in environment"
echo "  3. Run: python train_tag_model.py --train --input /workspace/data/training_data.jsonl --push-to-hub"
