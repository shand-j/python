#!/bin/bash
# =============================================================================
# Vast.ai QLoRA Training Pipeline Script
# =============================================================================
# Runs the complete training pipeline: export → train → evaluate → push
#
# Usage:
#   chmod +x run_training.sh
#   ./run_training.sh [options]
#
# Options:
#   --skip-setup       Skip environment setup
#   --skip-export      Skip JSONL export (use existing)
#   --skip-train       Skip training
#   --skip-eval        Skip evaluation
#   --push-to-hub      Push trained model to HF Hub
#   --epochs N         Training epochs (default: 3)
#   --batch-size N     Batch size (default: 4)
# =============================================================================

set -e

# =============================================================================
# Configuration (override with environment variables)
# =============================================================================
WORKSPACE="${WORKSPACE:-/workspace}"
INPUT_CSV="${INPUT_CSV:-$WORKSPACE/data/audit_training_dataset.csv}"
TRAINING_JSONL="${TRAINING_JSONL:-$WORKSPACE/data/training_data.jsonl}"
OUTPUT_DIR="${OUTPUT_DIR:-$WORKSPACE/output}"
MODEL_OUTPUT="${MODEL_OUTPUT:-$WORKSPACE/models/vape-tagger-lora}"

EPOCHS="${EPOCHS:-3}"
BATCH_SIZE="${BATCH_SIZE:-4}"

SKIP_SETUP=false
SKIP_EXPORT=false
SKIP_TRAIN=false
SKIP_EVAL=false
PUSH_TO_HUB=false

# =============================================================================
# Parse Arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-setup) SKIP_SETUP=true; shift ;;
        --skip-export) SKIP_EXPORT=true; shift ;;
        --skip-train) SKIP_TRAIN=true; shift ;;
        --skip-eval) SKIP_EVAL=true; shift ;;
        --push-to-hub) PUSH_TO_HUB=true; shift ;;
        --epochs) EPOCHS="$2"; shift 2 ;;
        --batch-size) BATCH_SIZE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# =============================================================================
# Logging
# =============================================================================
mkdir -p "$OUTPUT_DIR"
LOG_FILE="$OUTPUT_DIR/training_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# =============================================================================
# Pipeline
# =============================================================================
log "🚀 Starting QLoRA Training Pipeline"
log "=================================================="
log "   Input CSV: $INPUT_CSV"
log "   Training JSONL: $TRAINING_JSONL"
log "   Model output: $MODEL_OUTPUT"
log "   Epochs: $EPOCHS, Batch size: $BATCH_SIZE"
log "   Push to Hub: $PUSH_TO_HUB"
log ""

# Step 1: Setup
if [ "$SKIP_SETUP" = false ]; then
    log "📦 Step 1/4: Setting up environment..."
    ./setup_training.sh 2>&1 | tee -a "$LOG_FILE"
else
    log "⏭️  Step 1/4: Skipping setup"
fi

# Step 2: Export
if [ "$SKIP_EXPORT" = false ]; then
    log "📤 Step 2/4: Exporting training data..."
    if [ ! -f "$INPUT_CSV" ]; then
        log "❌ Input CSV not found: $INPUT_CSV"
        exit 1
    fi
    python train_tag_model.py --export --input "$INPUT_CSV" --output "$TRAINING_JSONL" 2>&1 | tee -a "$LOG_FILE"
else
    log "⏭️  Step 2/4: Skipping export"
fi

# Step 3: Train
if [ "$SKIP_TRAIN" = false ]; then
    log "🏋️ Step 3/4: Training model..."
    if [ ! -f "$TRAINING_JSONL" ]; then
        log "❌ Training JSONL not found: $TRAINING_JSONL"
        exit 1
    fi
    
    TRAIN_CMD="python train_tag_model.py --train --input $TRAINING_JSONL --output-dir $MODEL_OUTPUT --epochs $EPOCHS --batch-size $BATCH_SIZE"
    
    if [ "$PUSH_TO_HUB" = true ]; then
        if [ -z "$HF_TOKEN" ] || [ -z "$HF_REPO_ID" ]; then
            log "❌ --push-to-hub requires HF_TOKEN and HF_REPO_ID environment variables"
            exit 1
        fi
        TRAIN_CMD="$TRAIN_CMD --push-to-hub"
    fi
    
    eval "$TRAIN_CMD" 2>&1 | tee -a "$LOG_FILE"
else
    log "⏭️  Step 3/4: Skipping training"
fi

# Step 4: Evaluate
if [ "$SKIP_EVAL" = false ]; then
    log "📊 Step 4/4: Generating predictions and evaluating..."
    
    # Generate predictions on validation set
    PREDICTIONS="$OUTPUT_DIR/predictions.jsonl"
    python train_tag_model.py --generate-predictions \
        --model-path "$MODEL_OUTPUT" \
        --input "$TRAINING_JSONL" \
        --output "$PREDICTIONS" 2>&1 | tee -a "$LOG_FILE"
    
    # Evaluate
    python train_tag_model.py --evaluate \
        --predictions "$PREDICTIONS" \
        --corrections "$INPUT_CSV" \
        --eval-output "$OUTPUT_DIR/evaluation_results.csv" 2>&1 | tee -a "$LOG_FILE"
else
    log "⏭️  Step 4/4: Skipping evaluation"
fi

log ""
log "=================================================="
log "✅ Pipeline complete!"
log "   Model saved to: $MODEL_OUTPUT"
log "   Log file: $LOG_FILE"
if [ "$PUSH_TO_HUB" = true ]; then
    log "   HF Hub: https://huggingface.co/$HF_REPO_ID"
fi
