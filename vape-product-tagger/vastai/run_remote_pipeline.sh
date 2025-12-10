#!/bin/bash
#
# Vast.ai Remote Pipeline Runner
# ==============================
# Runs the complete tagging pipeline on a Vast.ai instance, downloads results,
# and destroys the instance when complete.
#
# Usage:
#   ./vastai/run_remote_pipeline.sh --instance <ID> --input <CSV> [OPTIONS]
#   ./vastai/run_remote_pipeline.sh --deploy --input <CSV> [OPTIONS]
#
# Options:
#   --instance ID       Use existing Vast.ai instance ID
#   --deploy            Deploy a new instance automatically
#   --input FILE        Local CSV file to process (required)
#   --limit N           Only process N products (for testing)
#   --workers N         Number of parallel workers (default: 5)
#   --no-destroy        Keep instance running after completion
#   --output-dir DIR    Local directory for downloaded results (default: ./vast_results)
#   --dry-run           Show what would be done without executing
#
# Examples:
#   # Use existing instance
#   ./vastai/run_remote_pipeline.sh --instance 12345678 --input data/input/products.csv
#
#   # Deploy new instance and run
#   ./vastai/run_remote_pipeline.sh --deploy --input data/input/products.csv --limit 1000
#
#   # Test run without destroying
#   ./vastai/run_remote_pipeline.sh --instance 12345678 --input data/input/test.csv --no-destroy
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Default configuration
INSTANCE_ID=""
DEPLOY_NEW=false
INPUT_FILE=""
LIMIT=""
WORKERS=5
DESTROY_AFTER=true
OUTPUT_DIR="./vast_results"
DRY_RUN=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Remote paths
REMOTE_PROJECT="/workspace/python/vape-product-tagger"
REMOTE_INPUT="/workspace/data/input"
REMOTE_OUTPUT="/workspace/data/output"
REMOTE_DB="/workspace/data/audit.db"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --instance)
            INSTANCE_ID="$2"
            shift 2
            ;;
        --deploy)
            DEPLOY_NEW=true
            shift
            ;;
        --input)
            INPUT_FILE="$2"
            shift 2
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --no-destroy)
            DESTROY_AFTER=false
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            head -40 "$0" | tail -35
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║       Vast.ai Remote Pipeline Runner - Vape Product Tagger      ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Runs tagging → downloads results → destroys instance           ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Validation
if [ -z "$INPUT_FILE" ]; then
    echo -e "${RED}❌ Error: --input is required${NC}"
    echo "Usage: $0 --instance <ID> --input <CSV>"
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}❌ Error: Input file not found: $INPUT_FILE${NC}"
    exit 1
fi

if [ -z "$INSTANCE_ID" ] && [ "$DEPLOY_NEW" = false ]; then
    echo -e "${RED}❌ Error: Either --instance or --deploy is required${NC}"
    exit 1
fi

# Check vastai CLI
if ! command -v vastai &> /dev/null; then
    echo -e "${RED}❌ vastai CLI not found. Install with: pip install vastai${NC}"
    exit 1
fi

# Helper functions
log_step() {
    echo -e "\n${GREEN}▶ $1${NC}"
}

log_info() {
    echo -e "${CYAN}  → $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
}

log_error() {
    echo -e "${RED}  ✗ $1${NC}"
}

log_success() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

get_ssh_details() {
    local instance_id=$1
    SCP_URL=$(vastai scp-url $instance_id 2>&1)
    SSH_HOST=$(echo "$SCP_URL" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
    SSH_PORT=$(echo "$SCP_URL" | grep -oE ':[0-9]+$' | tr -d ':')
    
    if [ -z "$SSH_HOST" ] || [ -z "$SSH_PORT" ]; then
        log_error "Failed to get SSH details for instance $instance_id"
        return 1
    fi
}

ssh_cmd() {
    ssh -p $SSH_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=30 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 \
        root@${SSH_HOST} "$@"
}

rsync_upload() {
    local src=$1
    local dst=$2
    rsync -avz --progress \
        -e "ssh -p $SSH_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ServerAliveInterval=10 -o ServerAliveCountMax=3" \
        "$src" root@${SSH_HOST}:"$dst"
}

rsync_download() {
    local src=$1
    local dst=$2
    rsync -avz --progress \
        -e "ssh -p $SSH_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ServerAliveInterval=10 -o ServerAliveCountMax=3" \
        root@${SSH_HOST}:"$src" "$dst"
}

wait_for_instance() {
    local instance_id=$1
    local max_wait=300
    local waited=0
    
    log_info "Waiting for instance to be ready..."
    while [ $waited -lt $max_wait ]; do
        # vastai show instance outputs a table - status is in the 3rd column
        STATUS=$(vastai show instance $instance_id 2>/dev/null | tail -1 | awk '{print $3}')
        
        if [ "$STATUS" = "running" ]; then
            log_success "Instance is running"
            sleep 10  # Extra time for SSH to be ready
            return 0
        fi
        
        echo -ne "\r  Waiting... ${waited}s (status: $STATUS)    "
        sleep 10
        waited=$((waited + 10))
    done
    
    log_error "Instance failed to start within ${max_wait}s"
    return 1
}

cleanup_on_error() {
    if [ "$DESTROY_AFTER" = true ] && [ -n "$INSTANCE_ID" ] && [ "$DEPLOYED_NEW" = true ]; then
        log_warn "Error occurred. Destroying instance $INSTANCE_ID..."
        vastai destroy instance $INSTANCE_ID 2>/dev/null || true
    fi
}

trap cleanup_on_error ERR

# ============================================================================
# STEP 1: Deploy or verify instance
# ============================================================================
log_step "Step 1: Instance Setup"

DEPLOYED_NEW=false

if [ "$DEPLOY_NEW" = true ]; then
    log_info "Deploying new Vast.ai instance..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would deploy new instance"
        INSTANCE_ID="DRY_RUN_12345"
    else
        # Use deploy script to create instance
        DEPLOY_OUTPUT=$("$SCRIPT_DIR/deploy_instance.sh" --gpu-ram 24 --max-price 0.40 2>&1)
        INSTANCE_ID=$(echo "$DEPLOY_OUTPUT" | grep -oE 'Instance ID: [0-9]+' | grep -oE '[0-9]+')
        
        if [ -z "$INSTANCE_ID" ]; then
            log_error "Failed to deploy instance"
            echo "$DEPLOY_OUTPUT"
            exit 1
        fi
        
        DEPLOYED_NEW=true
        log_success "Deployed instance: $INSTANCE_ID"
        
        # Wait for instance to be ready
        wait_for_instance $INSTANCE_ID
    fi
else
    log_info "Using existing instance: $INSTANCE_ID"
    
    # Verify instance exists and is running
    if [ "$DRY_RUN" = false ]; then
        # vastai show instance outputs a table - status is in the 3rd column
        STATUS=$(vastai show instance $INSTANCE_ID 2>/dev/null | tail -1 | awk '{print $3}')
        if [ "$STATUS" != "running" ]; then
            log_error "Instance $INSTANCE_ID is not running (status: $STATUS)"
            exit 1
        fi
        log_success "Instance is running (status: $STATUS)"
    fi
fi

# Get SSH details
if [ "$DRY_RUN" = false ]; then
    get_ssh_details $INSTANCE_ID
    log_info "SSH: root@${SSH_HOST}:${SSH_PORT}"
fi

# ============================================================================
# STEP 2: Setup remote environment
# ============================================================================
log_step "Step 2: Remote Environment Setup"

if [ "$DRY_RUN" = true ]; then
    log_info "[DRY RUN] Would run setup script on instance"
else
    # Check if already setup
    SETUP_CHECK=$(ssh_cmd "test -d $REMOTE_PROJECT && echo 'exists' || echo 'missing'" 2>/dev/null)
    
    if [ "$SETUP_CHECK" = "missing" ]; then
        log_info "Running setup script..."
        ssh_cmd "curl -fsSL https://raw.githubusercontent.com/shand-j/python/main/vape-product-tagger/vastai/setup_vast.sh | bash"
        log_success "Setup complete"
    else
        log_info "Environment already setup, pulling latest changes..."
        ssh_cmd "cd /workspace/python && git pull origin main"
        log_success "Updated to latest"
    fi
    
    # Create directories
    ssh_cmd "mkdir -p $REMOTE_INPUT $REMOTE_OUTPUT"
    
    # Ensure Ollama is running and models are pulled
    log_info "Checking Ollama status..."
    
    # Check if Ollama is installed
    OLLAMA_INSTALLED=$(ssh_cmd "command -v ollama && echo 'yes' || echo 'no'" 2>/dev/null)
    if [ "$OLLAMA_INSTALLED" = "no" ]; then
        log_info "Installing Ollama..."
        ssh_cmd "curl -fsSL https://ollama.com/install.sh | sh"
    fi
    
    # Start Ollama server if not running
    OLLAMA_RUNNING=$(ssh_cmd "pgrep -x ollama && echo 'running' || echo 'stopped'" 2>/dev/null)
    if [ "$OLLAMA_RUNNING" = "stopped" ]; then
        log_info "Starting Ollama server..."
        ssh_cmd "nohup ollama serve > /tmp/ollama.log 2>&1 &"
        sleep 5
    else
        log_info "Ollama already running"
    fi
    
    # Pull required models
    log_info "Ensuring models are available..."
    ssh_cmd "ollama pull llama3.1:latest" 2>&1 | tail -3
    ssh_cmd "ollama pull mistral:latest" 2>&1 | tail -3
    
    log_success "Ollama ready with models"
fi

# ============================================================================
# STEP 3: Upload input data
# ============================================================================
log_step "Step 3: Upload Input Data"

INPUT_BASENAME=$(basename "$INPUT_FILE")
REMOTE_INPUT_FILE="$REMOTE_INPUT/$INPUT_BASENAME"

if [ "$DRY_RUN" = true ]; then
    log_info "[DRY RUN] Would upload: $INPUT_FILE → $REMOTE_INPUT_FILE"
else
    log_info "Uploading: $INPUT_FILE (using rsync with compression)"
    rsync_upload "$INPUT_FILE" "$REMOTE_INPUT/"
    
    # Verify upload
    REMOTE_LINES=$(ssh_cmd "wc -l < $REMOTE_INPUT_FILE" 2>/dev/null | tr -d ' ')
    LOCAL_LINES=$(wc -l < "$INPUT_FILE" | tr -d ' ')
    
    if [ "$REMOTE_LINES" != "$LOCAL_LINES" ]; then
        log_warn "Line count mismatch: local=$LOCAL_LINES, remote=$REMOTE_LINES"
    else
        log_success "Uploaded $LOCAL_LINES lines"
    fi
fi

# ============================================================================
# STEP 4: Run tagging pipeline
# ============================================================================
log_step "Step 4: Run Tagging Pipeline"

# Build command
TAGGER_CMD="cd $REMOTE_PROJECT && source venv/bin/activate && python scripts/1_main.py"
TAGGER_CMD="$TAGGER_CMD --input $REMOTE_INPUT_FILE"
TAGGER_CMD="$TAGGER_CMD --output $REMOTE_OUTPUT"
TAGGER_CMD="$TAGGER_CMD --audit-db $REMOTE_DB"
TAGGER_CMD="$TAGGER_CMD --workers $WORKERS"

if [ -n "$LIMIT" ]; then
    TAGGER_CMD="$TAGGER_CMD --limit $LIMIT"
fi

log_info "Command: python scripts/1_main.py --input ... --workers $WORKERS ${LIMIT:+--limit $LIMIT}"

if [ "$DRY_RUN" = true ]; then
    log_info "[DRY RUN] Would run tagging pipeline"
else
    START_TIME=$(date +%s)
    
    log_info "Running tagging pipeline (this may take a while)..."
    echo ""
    
    # Run with live output
    ssh_cmd "$TAGGER_CMD" 2>&1 | while IFS= read -r line; do
        echo -e "  ${CYAN}│${NC} $line"
    done
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    log_success "Tagging complete in ${DURATION}s ($((DURATION/60))m $((DURATION%60))s)"
fi

# ============================================================================
# STEP 5: Run audit report
# ============================================================================
log_step "Step 5: Generate Audit Report"

AUDITOR_CMD="cd $REMOTE_PROJECT && source venv/bin/activate && python scripts/2_tag_auditor.py"
AUDITOR_CMD="$AUDITOR_CMD --db $REMOTE_DB"
AUDITOR_CMD="$AUDITOR_CMD --output $REMOTE_OUTPUT/audit_report.json"
AUDITOR_CMD="$AUDITOR_CMD --export-csv $REMOTE_OUTPUT/audit_summary.csv"

if [ "$DRY_RUN" = true ]; then
    log_info "[DRY RUN] Would generate audit report"
else
    log_info "Generating audit report..."
    ssh_cmd "$AUDITOR_CMD" 2>&1 | while IFS= read -r line; do
        echo -e "  ${CYAN}│${NC} $line"
    done
    log_success "Audit report generated"
fi

# ============================================================================
# STEP 6: Download results
# ============================================================================
log_step "Step 6: Download Results"

# Create local output directory with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOCAL_OUTPUT="$OUTPUT_DIR/$TIMESTAMP"

if [ "$DRY_RUN" = true ]; then
    log_info "[DRY RUN] Would create: $LOCAL_OUTPUT"
    log_info "[DRY RUN] Would download all results"
else
    mkdir -p "$LOCAL_OUTPUT"
    log_info "Output directory: $LOCAL_OUTPUT"
    
    # List remote files
    log_info "Remote output files:"
    ssh_cmd "ls -la $REMOTE_OUTPUT" 2>/dev/null | while IFS= read -r line; do
        echo -e "    $line"
    done
    
    # Download output directory
    log_info "Downloading output files..."
    rsync_download "$REMOTE_OUTPUT/" "$LOCAL_OUTPUT/"
    
    # Download audit database
    log_info "Downloading audit database..."
    rsync_download "$REMOTE_DB" "$LOCAL_OUTPUT/"
    
    # List downloaded files
    echo ""
    log_success "Downloaded files:"
    ls -la "$LOCAL_OUTPUT" | while IFS= read -r line; do
        echo -e "    $line"
    done
fi

# ============================================================================
# STEP 7: Show summary
# ============================================================================
log_step "Step 7: Results Summary"

if [ "$DRY_RUN" = false ]; then
    # Count tagged/untagged if CSVs exist
    TAGGED_FILE=$(ls "$LOCAL_OUTPUT"/*tagged*.csv 2>/dev/null | grep -v untagged | head -1)
    UNTAGGED_FILE=$(ls "$LOCAL_OUTPUT"/*untagged*.csv 2>/dev/null | head -1)
    
    echo ""
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}                        PIPELINE RESULTS                            ${NC}"
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ -n "$TAGGED_FILE" ]; then
        TAGGED_COUNT=$(($(wc -l < "$TAGGED_FILE") - 1))
        echo -e "  ${GREEN}✓ Tagged products:${NC}   $TAGGED_COUNT"
        echo -e "    File: $(basename "$TAGGED_FILE")"
    fi
    
    if [ -n "$UNTAGGED_FILE" ]; then
        UNTAGGED_COUNT=$(($(wc -l < "$UNTAGGED_FILE") - 1))
        echo -e "  ${YELLOW}○ Untagged products:${NC} $UNTAGGED_COUNT"
        echo -e "    File: $(basename "$UNTAGGED_FILE")"
    fi
    
    if [ -f "$LOCAL_OUTPUT/audit.db" ]; then
        DB_SIZE=$(ls -lh "$LOCAL_OUTPUT/audit.db" | awk '{print $5}')
        echo -e "  ${CYAN}◆ Audit database:${NC}    $DB_SIZE"
    fi
    
    if [ -f "$LOCAL_OUTPUT/audit_report.json" ]; then
        echo -e "  ${CYAN}◆ Audit report:${NC}      audit_report.json"
    fi
    
    echo ""
    echo -e "  ${BLUE}Output directory:${NC} $LOCAL_OUTPUT"
    echo ""
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════════════${NC}"
fi

# ============================================================================
# STEP 8: Cleanup (destroy instance)
# ============================================================================
log_step "Step 8: Cleanup"

if [ "$DESTROY_AFTER" = true ]; then
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would destroy instance $INSTANCE_ID"
    else
        log_warn "Destroying instance $INSTANCE_ID..."
        
        # Get final cost ($/hr is in column 11)
        COST=$(vastai show instance $INSTANCE_ID 2>/dev/null | tail -1 | awk '{print $11}' || echo "unknown")
        log_info "Cost rate was: \$$COST/hr"
        
        vastai destroy instance $INSTANCE_ID
        log_success "Instance destroyed"
    fi
else
    log_info "Instance kept running (--no-destroy specified)"
    log_info "To stop later: vastai destroy instance $INSTANCE_ID"
fi

# ============================================================================
# Done
# ============================================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Pipeline Complete! 🎉                         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$DRY_RUN" = false ]; then
    echo -e "Results saved to: ${CYAN}$LOCAL_OUTPUT${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review tagged products: open $LOCAL_OUTPUT/*tagged*.csv"
    echo "  2. Check untagged products: open $LOCAL_OUTPUT/*untagged*.csv"
    echo "  3. Analyze audit data: sqlite3 $LOCAL_OUTPUT/audit.db"
    echo ""
fi
