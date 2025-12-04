#!/bin/bash
# =============================================================================
# Vast.ai vLLM Full Automation Script
# =============================================================================
# Runs the complete audit, export, training, and evaluation pipeline on
# Vast.ai GPU instances.
#
# Usage:
#   chmod +x run_all_vllm.sh
#   ./run_all_vllm.sh [options]
#
# Options:
#   --skip-setup       Skip environment setup
#   --skip-export      Skip JSONL export
#   --skip-train       Skip training
#   --skip-eval        Skip evaluation
#   --epochs N         Number of training epochs (default: 3)
#   --batch-size N     Training batch size (default: 4)
#   --model NAME       Base model for fine-tuning
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================
DATA_DIR="${DATA_DIR:-/workspace/data}"
MODEL_DIR="${MODEL_DIR:-/workspace/models}"
OUTPUT_DIR="${OUTPUT_DIR:-/workspace/output}"
CHECKPOINT_DIR="${CHECKPOINT_DIR:-/workspace/checkpoints}"

INPUT_CSV="${INPUT_CSV:-$DATA_DIR/audit_training_dataset.csv}"
TRAINING_JSONL="${TRAINING_JSONL:-$DATA_DIR/training_data.jsonl}"
PREDICTIONS_JSONL="${PREDICTIONS_JSONL:-$OUTPUT_DIR/predictions.jsonl}"
EVAL_OUTPUT="${EVAL_OUTPUT:-$OUTPUT_DIR/evaluation_results.csv}"

EPOCHS="${EPOCHS:-3}"
BATCH_SIZE="${BATCH_SIZE:-4}"
MODEL="${MODEL:-meta-llama/Llama-2-7b-chat-hf}"

SKIP_SETUP=false
SKIP_EXPORT=false
SKIP_TRAIN=false
SKIP_EVAL=false

# =============================================================================
# Parse Arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-setup)
            SKIP_SETUP=true
            shift
            ;;
        --skip-export)
            SKIP_EXPORT=true
            shift
            ;;
        --skip-train)
            SKIP_TRAIN=true
            shift
            ;;
        --skip-eval)
            SKIP_EVAL=true
            shift
            ;;
        --epochs)
            EPOCHS="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Logging
# =============================================================================
LOG_FILE="$OUTPUT_DIR/run_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$OUTPUT_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# =============================================================================
# Main Pipeline
# =============================================================================
log "🚀 Starting vLLM Training Pipeline"
log "=" 
log "Configuration:"
log "   Data directory: $DATA_DIR"
log "   Model directory: $MODEL_DIR"
log "   Output directory: $OUTPUT_DIR"
log "   Input CSV: $INPUT_CSV"
log "   Epochs: $EPOCHS"
log "   Batch size: $BATCH_SIZE"
log "   Base model: $MODEL"

# -----------------------------------------------------------------------------
# Step 1: Setup
# -----------------------------------------------------------------------------
if [ "$SKIP_SETUP" = false ]; then
    log ""
    log "📦 Step 1: Environment Setup"
    if [ -f "setup_vllm.sh" ]; then
        ./setup_vllm.sh 2>&1 | tee -a "$LOG_FILE"
    else
        log "⚠️ setup_vllm.sh not found. Skipping setup."
    fi
else
    log "⏭️ Skipping setup (--skip-setup)"
fi

# -----------------------------------------------------------------------------
# Step 2: Export Training Data
# -----------------------------------------------------------------------------
if [ "$SKIP_EXPORT" = false ]; then
    log ""
    log "📂 Step 2: Export Training Data"
    if [ -f "$INPUT_CSV" ]; then
        python train_tag_model.py \
            --input "$INPUT_CSV" \
            --output "$TRAINING_JSONL" \
            2>&1 | tee -a "$LOG_FILE"
    else
        log "❌ Input CSV not found: $INPUT_CSV"
        exit 1
    fi
else
    log "⏭️ Skipping export (--skip-export)"
fi

# -----------------------------------------------------------------------------
# Step 3: Training
# -----------------------------------------------------------------------------
if [ "$SKIP_TRAIN" = false ]; then
    log ""
    log "🎓 Step 3: Training"
    if [ -f "$TRAINING_JSONL" ]; then
        python train_tag_model.py \
            --train \
            --output "$TRAINING_JSONL" \
            --model "$MODEL" \
            --epochs "$EPOCHS" \
            --batch-size "$BATCH_SIZE" \
            --output-dir "$MODEL_DIR" \
            --checkpoint "$CHECKPOINT_DIR/latest" \
            2>&1 | tee -a "$LOG_FILE"
    else
        log "❌ Training JSONL not found: $TRAINING_JSONL"
        exit 1
    fi
else
    log "⏭️ Skipping training (--skip-train)"
fi

# -----------------------------------------------------------------------------
# Step 4: Evaluation
# -----------------------------------------------------------------------------
if [ "$SKIP_EVAL" = false ]; then
    log ""
    log "📊 Step 4: Evaluation"
    if [ -f "$PREDICTIONS_JSONL" ]; then
        python train_tag_model.py \
            --evaluate \
            --predictions "$PREDICTIONS_JSONL" \
            --corrections "$INPUT_CSV" \
            --eval-output "$EVAL_OUTPUT" \
            2>&1 | tee -a "$LOG_FILE"
    else
        log "⚠️ Predictions JSONL not found: $PREDICTIONS_JSONL"
        log "   Run inference first to generate predictions."
    fi
else
    log "⏭️ Skipping evaluation (--skip-eval)"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
log ""
log "✅ Pipeline Complete!"
log "=" 
log "Outputs:"
log "   Training data: $TRAINING_JSONL"
log "   Model output: $MODEL_DIR"
log "   Evaluation results: $EVAL_OUTPUT"
log "   Log file: $LOG_FILE"
