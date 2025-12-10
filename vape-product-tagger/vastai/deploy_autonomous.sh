#!/bin/bash
# Vast.ai Deployment Script for Autonomous Pipeline
# ==================================================
# Complete setup and execution script for Vast.ai GPU instances

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Vast.ai Autonomous Pipeline Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: System updates and dependencies
echo -e "${YELLOW}[1/8] Installing system dependencies...${NC}"
apt-get update -qq
apt-get install -y -qq bc curl sqlite3 git > /dev/null 2>&1
echo -e "${GREEN}✓ System dependencies installed${NC}"

# Step 2: Check Python
echo -e "${YELLOW}[2/8] Checking Python installation...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi

# Step 3: Install Ollama
echo -e "${YELLOW}[3/8] Installing Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.ai/install.sh | sh > /dev/null 2>&1
    echo -e "${GREEN}✓ Ollama installed${NC}"
else
    echo -e "${GREEN}✓ Ollama already installed${NC}"
fi

# Step 4: Start Ollama service
echo -e "${YELLOW}[4/8] Starting Ollama service...${NC}"
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 5

if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama service running${NC}"
else
    echo -e "${RED}✗ Failed to start Ollama${NC}"
    exit 1
fi

# Step 5: Pull AI models
echo -e "${YELLOW}[5/8] Pulling AI models...${NC}"
MODELS=("mistral:latest" "gpt-oss:latest" "llama3.1:latest")
for model in "${MODELS[@]}"; do
    echo -e "  Pulling $model..."
    if ollama pull "$model" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ $model${NC}"
    else
        echo -e "  ${YELLOW}⚠ Failed to pull $model (continuing)${NC}"
    fi
done

# Step 6: Setup project
echo -e "${YELLOW}[6/8] Setting up project...${NC}"

# Detect if we're in the project directory
if [ -f "approved_tags.json" ] && [ -d "modules" ]; then
    PROJECT_DIR=$(pwd)
    echo -e "${GREEN}✓ Using current directory: $PROJECT_DIR${NC}"
else
    echo -e "${RED}✗ Not in project directory. Please cd to vape-product-tagger/${NC}"
    exit 1
fi

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo -e "  Installing Python dependencies..."
    pip install -q -r requirements.txt
    echo -e "  ${GREEN}✓ Dependencies installed${NC}"
fi

# Create config if not exists
if [ ! -f "config.env" ]; then
    if [ -f "config.env.example" ]; then
        cp config.env.example config.env
        echo -e "  ${GREEN}✓ Created config.env from example${NC}"
    fi
fi

# Step 7: Create directories
echo -e "${YELLOW}[7/8] Creating directories...${NC}"
mkdir -p data output/autonomous logs persistance
echo -e "${GREEN}✓ Directories created${NC}"

# Step 8: System info
echo -e "${YELLOW}[8/8] System Information${NC}"
echo -e "  Python:  $(python3 --version | cut -d' ' -f2)"
echo -e "  Ollama:  $(ollama --version 2>&1 | head -1)"
echo -e "  GPU:     $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo "Not detected")"
echo -e "  CPU:     $(nproc) cores"
echo -e "  Memory:  $(free -h | awk '/^Mem:/ {print $2}')"
echo -e "  Disk:    $(df -h . | awk 'NR==2 {print $4}') available"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Quick Start:${NC}"
echo ""
echo -e "  1. Upload your products CSV:"
echo -e "     ${YELLOW}scp -P <port> products.csv root@<vast-ip>:$PROJECT_DIR/data/${NC}"
echo ""
echo -e "  2. Run autonomous pipeline:"
echo -e "     ${YELLOW}./shell/run_autonomous_pipeline.sh -i data/products.csv -v${NC}"
echo ""
echo -e "  3. Download results:"
echo -e "     ${YELLOW}scp -P <port> -r root@<vast-ip>:$PROJECT_DIR/output/autonomous/ ./${NC}"
echo ""
echo -e "${BLUE}Advanced Options:${NC}"
echo ""
echo -e "  Test with limited dataset:"
echo -e "     ${YELLOW}./shell/run_autonomous_pipeline.sh -i data/products.csv -l 100${NC}"
echo ""
echo -e "  Custom accuracy target:"
echo -e "     ${YELLOW}./shell/run_autonomous_pipeline.sh -i data/products.csv -t 0.92 -m 5${NC}"
echo ""
echo -e "  Rule-based only (no AI):"
echo -e "     ${YELLOW}./shell/run_autonomous_pipeline.sh -i data/products.csv --no-ai${NC}"
echo ""
echo -e "${BLUE}Monitoring:${NC}"
echo ""
echo -e "  Watch progress:"
echo -e "     ${YELLOW}tail -f logs/autonomous_pipeline_*.log${NC}"
echo ""
echo -e "  Check Ollama:"
echo -e "     ${YELLOW}tail -f /tmp/ollama.log${NC}"
echo ""
echo -e "  GPU utilization:"
echo -e "     ${YELLOW}watch -n 1 nvidia-smi${NC}"
echo ""
