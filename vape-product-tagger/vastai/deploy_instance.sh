#!/bin/bash
#
# Vast.ai Instance Deploy Script
# Quick deployment using pre-built Docker image
#
# Usage:
#   ./vastai/deploy_instance.sh [OPTIONS]
#
# Options:
#   --gpu-ram RAM       Minimum GPU RAM in GB (default: 24)
#   --max-price PRICE   Maximum price per hour (default: 0.50)
#   --disk SPACE        Disk space in GB (default: 60)
#   --gpu-name GPU      Specific GPU model (e.g., RTX_4090, A5000)
#   --workers N         Number of parallel workers (default: 4)
#   --dry-run           Show search results without creating instance
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default configuration
GPU_RAM=24
MAX_PRICE=0.50
DISK_SPACE=60
GPU_NAME=""
WORKERS=4
DRY_RUN=false
IMAGE="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime"  # Base image, setup via script

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu-ram)
            GPU_RAM="$2"
            shift 2
            ;;
        --max-price)
            MAX_PRICE="$2"
            shift 2
            ;;
        --disk)
            DISK_SPACE="$2"
            shift 2
            ;;
        --gpu-name)
            GPU_NAME="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Vast.ai Instance Deploy - Vape Product Tagger       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check vastai CLI is installed
if ! command -v vastai &> /dev/null; then
    echo -e "${RED}❌ vastai CLI not found${NC}"
    echo ""
    echo "Install with:"
    echo "  pip install vastai"
    echo ""
    echo "Configure with:"
    echo "  vastai set api-key YOUR_API_KEY"
    exit 1
fi

# Check if logged in
if ! vastai show user &> /dev/null; then
    echo -e "${RED}❌ Not logged in to Vast.ai${NC}"
    echo ""
    echo "Login with:"
    echo "  vastai set api-key YOUR_API_KEY"
    echo ""
    echo "Get your API key from: https://console.vast.ai/account"
    exit 1
fi

# Build search query
SEARCH_QUERY="cuda_vers>=12.0 gpu_ram>=${GPU_RAM} disk_space>=${DISK_SPACE} reliability>0.95"

if [ -n "$GPU_NAME" ]; then
    SEARCH_QUERY="${SEARCH_QUERY} gpu_name=${GPU_NAME}"
fi

echo -e "${CYAN}Search Criteria:${NC}"
echo "  GPU RAM: ${GPU_RAM}GB+"
echo "  Max Price: \$${MAX_PRICE}/hour"
echo "  Disk Space: ${DISK_SPACE}GB+"
if [ -n "$GPU_NAME" ]; then
    echo "  GPU Model: ${GPU_NAME}"
fi
echo "  Workers: ${WORKERS}"
echo ""

# Search for available offers
echo -e "${CYAN}🔍 Searching for available instances...${NC}"
echo ""

# Use table format and parse with awk (more reliable than --raw)
OFFERS_TABLE=$(vastai search offers \
    "${SEARCH_QUERY}" \
    --order "dph_base+" 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to search offers${NC}"
    echo "$OFFERS_TABLE"
    exit 1
fi

# Check if any offers found
if echo "$OFFERS_TABLE" | grep -q "No offers found"; then
    echo -e "${RED}❌ No suitable offers found${NC}"
    echo ""
    echo "Try adjusting search criteria:"
    echo "  ./vastai/deploy_instance.sh --gpu-ram 16 --max-price 0.80"
    exit 1
fi

# Display top offers
echo -e "${GREEN}Top available offers:${NC}"
echo ""
echo "$OFFERS_TABLE" | head -15
echo ""

# Parse first offer from table
# Columns: ID CUDA N Model PCIE cpu_ghz vCPUs RAM Disk $/hr DLP DLP/$ score ...
FIRST_LINE=$(echo "$OFFERS_TABLE" | grep -E "^[0-9]+" | head -1)

if [ -z "$FIRST_LINE" ]; then
    echo -e "${RED}❌ Could not parse offers table${NC}"
    echo "Debug output:"
    echo "$OFFERS_TABLE"
    exit 1
fi

OFFER_ID=$(echo "$FIRST_LINE" | awk '{print $1}')      # Column 1: ID
OFFER_GPU=$(echo "$FIRST_LINE" | awk '{print $4}')     # Column 4: Model (e.g., RTX_3090)
OFFER_PRICE=$(echo "$FIRST_LINE" | awk '{print $10}')  # Column 10: $/hr

# Check price
if [ -z "$OFFER_ID" ]; then
    echo -e "${RED}❌ Could not parse offer ID${NC}"
    exit 1
fi

# Convert price to float for comparison (remove any extra text)
OFFER_PRICE_CLEAN=$(echo "$OFFER_PRICE" | grep -oE '[0-9]+\.[0-9]+' | head -1)

if (( $(echo "$OFFER_PRICE_CLEAN > $MAX_PRICE" | bc -l 2>/dev/null || echo 0) )); then
    echo -e "${YELLOW}⚠  Best offer (\$${OFFER_PRICE_CLEAN}/hr) exceeds max price (\$${MAX_PRICE}/hr)${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

if [ "$DRY_RUN" = true ]; then
    echo -e "${CYAN}ℹ  Dry run mode - no instance created${NC}"
    exit 0
fi

# Create instance
echo ""
echo -e "${GREEN}🚀 Creating instance...${NC}"
echo "  Offer ID: ${OFFER_ID}"
echo "  GPU: ${OFFER_GPU}"
echo "  Price: \$${OFFER_PRICE_CLEAN}/hour"
echo "  Image: ${IMAGE}"
echo ""

INSTANCE_OUTPUT=$(vastai create instance ${OFFER_ID} \
    --image ${IMAGE} \
    --disk ${DISK_SPACE} \
    --env WORKERS=${WORKERS} \
    --env AI_CONFIDENCE_THRESHOLD=0.7 \
    --env OLLAMA_HOST=0.0.0.0:11434 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to create instance${NC}"
    echo "$INSTANCE_OUTPUT"
    exit 1
fi

# Extract instance ID from output (format: "Started. {'success': True, 'new_contract': 12345678}")
INSTANCE_ID=$(echo "$INSTANCE_OUTPUT" | grep -oE "new_contract['\": ]+[0-9]+" | grep -oE "[0-9]+" | head -1)

if [ -z "$INSTANCE_ID" ]; then
    echo -e "${RED}❌ Could not parse instance ID from output:${NC}"
    echo "$INSTANCE_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✓ Instance created: ${INSTANCE_ID}${NC}"
echo ""

# Wait for instance to be ready
echo -e "${CYAN}⏳ Waiting for instance to be ready...${NC}"
sleep 10

# Get instance details
INSTANCE_INFO=$(vastai show instance ${INSTANCE_ID} 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠  Could not fetch instance details yet (might still be starting)${NC}"
    INSTANCE_SSH="(pending)"
else
    # Parse SSH info from table output
    INSTANCE_SSH=$(echo "$INSTANCE_INFO" | grep -oE "ssh://[^[:space:]]*" | head -1 | sed 's/ssh:\/\///')
    if [ -z "$INSTANCE_SSH" ]; then
        INSTANCE_SSH="(use: vastai ssh ${INSTANCE_ID})"
    fi
fi

echo -e "${GREEN}✓ Instance ready!${NC}"
echo ""

# Display connection info
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Instance Information                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Instance ID:${NC}  ${INSTANCE_ID}"
echo -e "${CYAN}SSH Access:${NC}   vastai ssh ${INSTANCE_ID}"
echo -e "${CYAN}SSH Host:${NC}     ${INSTANCE_SSH}"
echo -e "${CYAN}GPU:${NC}          ${OFFER_GPU}"
echo -e "${CYAN}Cost:${NC}         \$${OFFER_PRICE}/hour"
echo ""

# Next steps
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo ""
echo "1. SSH into instance and run setup:"
echo -e "   ${CYAN}vastai ssh ${INSTANCE_ID}${NC}"
echo ""
echo "   Inside instance:"
echo -e "   ${CYAN}curl -fsSL https://raw.githubusercontent.com/shand-j/python/main/vape-product-tagger/vastai/setup_vast.sh | bash${NC}"
echo ""
echo "2. Upload your data (from local machine, new terminal):"
echo -e "   ${CYAN}./vastai/vast_helper.sh upload ${INSTANCE_ID} data/input/products.csv /workspace/data/${NC}"
echo ""
echo "3. Run the pipeline (in SSH session):"
echo -e "   ${CYAN}cd /workspace/python/vape-product-tagger${NC}"
echo -e "   ${CYAN}source venv/bin/activate${NC}"
echo -e "   ${CYAN}python scripts/1_main.py --input /workspace/data/products.csv --workers ${WORKERS} --audit-db${NC}"
echo ""
echo "4. Download results (from local machine):"
echo -e "   ${CYAN}./vastai/vast_helper.sh download ${INSTANCE_ID} /workspace/python/vape-product-tagger/output/ ./output/${NC}"
echo ""
echo "5. Stop instance when done:"
echo -e "   ${CYAN}vastai stop instance ${INSTANCE_ID}${NC}"
echo ""

# Save instance info
INSTANCE_FILE="vastai/current_instance.json"
cat > $INSTANCE_FILE <<EOF
{
  "instance_id": "${INSTANCE_ID}",
  "ssh": "${INSTANCE_SSH}",
  "gpu": "${OFFER_GPU}",
  "price": ${OFFER_PRICE_CLEAN},
  "workers": ${WORKERS},
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo -e "${CYAN}ℹ  Instance info saved to: ${INSTANCE_FILE}${NC}"
echo ""
