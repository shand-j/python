#!/bin/bash
#
# Vast.ai One-Line Setup Script
# ==============================
# Sets up a fresh Vast.ai instance for running the vape product tagger.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/shand-j/python/main/vape-product-tagger/vastai/setup_vast.sh | bash
#
# Or if already cloned:
#   ./vastai/setup_vast.sh
#
# Options (set as environment variables before running):
#   SKIP_OLLAMA=1        Skip Ollama installation
#   SKIP_TRAINING=1      Skip training dependencies
#   SKIP_PROMPTS=1       Skip interactive prompts (use env vars)
#   HF_TOKEN=xxx         HuggingFace token for model access
#   HF_REPO_ID=xxx       HuggingFace repo for LoRA adapters
#   BRANCH=main          Git branch to checkout (default: main)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/shand-j/python.git"
BRANCH="${BRANCH:-main}"
WORKSPACE="/workspace"
PROJECT_DIR="$WORKSPACE/python/vape-product-tagger"
OLLAMA_MODELS=("llama3.1" "llama3.1:8b")

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          Vape Product Tagger - Vast.ai Setup                ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  This script will:                                          ║"
echo "║  1. Install system dependencies                             ║"
echo "║  2. Clone the repository                                    ║"
echo "║  3. Create Python virtual environment                       ║"
echo "║  4. Install Python packages                                 ║"
echo "║  5. Install Ollama and pull models                          ║"
echo "║  6. Configure the environment                               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to print step headers
step() {
    echo -e "\n${GREEN}▶ $1${NC}"
}

# Function to print info
info() {
    echo -e "${YELLOW}  → $1${NC}"
}

# Function to print error
error() {
    echo -e "${RED}✗ Error: $1${NC}"
    exit 1
}

# Function to prompt user
prompt() {
    local var_name="$1"
    local prompt_text="$2"
    local default_value="$3"
    local is_secret="${4:-false}"
    
    # Check if already set via environment
    local current_value="${!var_name}"
    if [ -n "$current_value" ]; then
        if [ "$is_secret" = "true" ]; then
            info "$var_name already set (from environment)"
        else
            info "$var_name=$current_value (from environment)"
        fi
        return
    fi
    
    # Skip prompts if SKIP_PROMPTS is set
    if [ "${SKIP_PROMPTS:-0}" = "1" ]; then
        if [ -n "$default_value" ]; then
            export "$var_name"="$default_value"
        fi
        return
    fi
    
    # Interactive prompt
    if [ -n "$default_value" ]; then
        prompt_text="$prompt_text [$default_value]"
    fi
    
    echo -e -n "${CYAN}  ? $prompt_text: ${NC}"
    
    if [ "$is_secret" = "true" ]; then
        read -s user_input
        echo ""
    else
        read user_input
    fi
    
    if [ -z "$user_input" ] && [ -n "$default_value" ]; then
        user_input="$default_value"
    fi
    
    export "$var_name"="$user_input"
}

# Function to check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# ============================================================
# Step 1: System Dependencies
# ============================================================
step "Installing system dependencies..."

# Update package lists
apt-get update -qq

# Install required packages
apt-get install -y -qq \
    git \
    curl \
    wget \
    sqlite3 \
    build-essential \
    python3-dev \
    python3-venv \
    python3-pip \
    > /dev/null 2>&1

info "System dependencies installed"

# ============================================================
# Step 2: Clone Repository
# ============================================================
step "Cloning repository..."

cd "$WORKSPACE"

if [ -d "python" ]; then
    info "Repository exists, pulling latest changes..."
    cd python
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    info "Cloning from $REPO_URL (branch: $BRANCH)..."
    git clone --branch "$BRANCH" "$REPO_URL"
    cd python
fi

cd vape-product-tagger
info "Repository ready at $PROJECT_DIR"

# ============================================================
# Step 3: Python Virtual Environment
# ============================================================
step "Setting up Python virtual environment..."

if [ -d "venv" ]; then
    info "Virtual environment exists, activating..."
else
    info "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
info "Python $(python3 --version) activated"

# Upgrade pip
pip install --upgrade pip -q

# ============================================================
# Step 4: Install Python Dependencies
# ============================================================
step "Installing Python dependencies..."

# Core dependencies
info "Installing core dependencies..."
pip install -r requirements.txt -q

# Training dependencies (optional)
if [ "${SKIP_TRAINING:-0}" != "1" ]; then
    info "Installing training dependencies..."
    pip install -r vastai/requirements-train.txt -q
    
    # Flash attention (optional, may fail on some systems)
    info "Attempting Flash Attention install (may take 10-30 min)..."
    pip install flash-attn --no-build-isolation -q 2>/dev/null || {
        echo -e "${YELLOW}  → Flash Attention install failed (optional, continuing...)${NC}"
    }
else
    info "Skipping training dependencies (SKIP_TRAINING=1)"
fi

info "Python dependencies installed"

# ============================================================
# Step 5: Install Ollama
# ============================================================
if [ "${SKIP_OLLAMA:-0}" != "1" ]; then
    step "Installing Ollama..."
    
    if command_exists ollama; then
        info "Ollama already installed"
    else
        info "Downloading and installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    # Start Ollama server in background
    info "Starting Ollama server..."
    pkill ollama 2>/dev/null || true
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    
    # Wait for Ollama to be ready
    info "Waiting for Ollama to start..."
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # Verify Ollama is running
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        error "Ollama failed to start. Check /tmp/ollama.log"
    fi
    
    info "Ollama server running"
    
    # Pull models
    step "Pulling Ollama models..."
    for model in "${OLLAMA_MODELS[@]}"; do
        info "Pulling $model..."
        ollama pull "$model" || echo -e "${YELLOW}  → Failed to pull $model (continuing...)${NC}"
    done
    
    info "Ollama models ready"
else
    info "Skipping Ollama installation (SKIP_OLLAMA=1)"
fi

# ============================================================
# Step 6: Configure Environment
# ============================================================
step "Configuring environment..."

# Create config.env if it doesn't exist
if [ ! -f "config.env" ]; then
    info "Creating config.env from template..."
    cp config.env.example config.env
    
    # Prompt for HuggingFace credentials
    echo -e "\n${CYAN}  Configure HuggingFace (optional - press Enter to skip):${NC}"
    prompt "HF_TOKEN" "HuggingFace API token" "" "true"
    prompt "HF_REPO_ID" "HuggingFace repo for LoRA adapters" "your-username/vape-tagger-lora"
    
    # Update config.env with provided values
    if [ -n "$HF_TOKEN" ]; then
        sed -i "s/^HF_TOKEN=.*/HF_TOKEN=$HF_TOKEN/" config.env
        info "HuggingFace token configured"
        
        # Login to HuggingFace
        info "Logging into HuggingFace Hub..."
        pip install huggingface_hub -q 2>/dev/null
        huggingface-cli login --token "$HF_TOKEN" --add-to-git-credential 2>/dev/null || true
    fi
    
    if [ -n "$HF_REPO_ID" ] && [ "$HF_REPO_ID" != "your-username/vape-tagger-lora" ]; then
        sed -i "s|^HF_REPO_ID=.*|HF_REPO_ID=$HF_REPO_ID|" config.env
        info "HuggingFace repo ID configured: $HF_REPO_ID"
    fi
else
    info "config.env already exists"
fi

# Create data directory
mkdir -p "$WORKSPACE/data"
info "Data directory created at $WORKSPACE/data"

# ============================================================
# Step 7: GPU Check
# ============================================================
step "Checking GPU..."

if command_exists nvidia-smi; then
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
    info "GPU detected and ready"
else
    echo -e "${YELLOW}  → No GPU detected (CPU mode)${NC}"
fi

# ============================================================
# Complete!
# ============================================================
echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete! ✓                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "To start using the tagger:\n"
echo -e "  ${BLUE}cd $PROJECT_DIR${NC}"
echo -e "  ${BLUE}source venv/bin/activate${NC}"
echo -e ""
echo -e "Run the tagger:"
echo -e "  ${BLUE}python main.py --input /workspace/data/products.csv --audit-db /workspace/data/audit.sqlite3${NC}"
echo -e ""
echo -e "Check Ollama status:"
echo -e "  ${BLUE}curl http://localhost:11434/api/tags${NC}"
echo -e ""
echo -e "View logs:"
echo -e "  ${BLUE}tail -f /tmp/ollama.log${NC}"
echo -e ""

# Create a convenience alias file
cat > "$WORKSPACE/activate_tagger.sh" << 'EOF'
#!/bin/bash
cd /workspace/python/vape-product-tagger
source venv/bin/activate
echo "Tagger environment activated. Run: python main.py --help"
EOF
chmod +x "$WORKSPACE/activate_tagger.sh"

echo -e "Quick activate: ${BLUE}source /workspace/activate_tagger.sh${NC}"
echo ""
