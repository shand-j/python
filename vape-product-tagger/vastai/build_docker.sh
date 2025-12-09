#!/bin/bash
#
# Docker Image Build Script for Vape Product Tagger
# Builds optimized image with pre-loaded models for Vast.ai deployment
#
# Usage:
#   ./vastai/build_docker.sh [OPTIONS]
#
# Options:
#   --push              Push to Docker Hub after build
#   --no-cache          Build without cache
#   --test              Test image locally before pushing
#   --tag VERSION       Custom version tag (default: latest + date)
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
DOCKER_USER="${DOCKER_USER:-shandj}"
IMAGE_NAME="vape-tagger"
VERSION=$(date +%Y%m%d)
PLATFORM="linux/amd64"

# Parse arguments
PUSH=false
NO_CACHE=""
TEST=false
CUSTOM_TAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH=true
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --test)
            TEST=true
            shift
            ;;
        --tag)
            CUSTOM_TAG="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Use custom tag if provided
if [ -n "$CUSTOM_TAG" ]; then
    VERSION="$CUSTOM_TAG"
fi

IMAGE_TAG="${DOCKER_USER}/${IMAGE_NAME}"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Docker Image Build - Vape Product Tagger             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "${CYAN}Image:${NC}     ${IMAGE_TAG}:${VERSION}"
echo -e "${CYAN}Platform:${NC}  ${PLATFORM}"
echo -e "${CYAN}Push:${NC}      ${PUSH}"
echo -e "${CYAN}Cache:${NC}     $([ -z "$NO_CACHE" ] && echo "enabled" || echo "disabled")"
echo ""

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

# Check we're in the right directory
if [ ! -f "vastai/Dockerfile" ]; then
    echo -e "${RED}❌ Must run from vape-product-tagger root directory${NC}"
    exit 1
fi

# Estimate build time and size
echo -e "${YELLOW}⏱  Estimated build time: 15-25 minutes${NC}"
echo -e "${YELLOW}📦 Estimated image size: ~25-30GB (with pre-loaded models)${NC}"
echo ""
read -p "Continue with build? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Build cancelled."
    exit 0
fi

# Start build
echo ""
echo -e "${GREEN}🔨 Building Docker image...${NC}"
echo ""

BUILD_START=$(date +%s)

docker build \
    $NO_CACHE \
    --platform $PLATFORM \
    -f vastai/Dockerfile \
    -t ${IMAGE_TAG}:${VERSION} \
    -t ${IMAGE_TAG}:latest \
    .

BUILD_END=$(date +%s)
BUILD_TIME=$((BUILD_END - BUILD_START))
BUILD_MIN=$((BUILD_TIME / 60))
BUILD_SEC=$((BUILD_TIME % 60))

echo ""
echo -e "${GREEN}✓ Build completed in ${BUILD_MIN}m ${BUILD_SEC}s${NC}"

# Get image size
IMAGE_SIZE=$(docker images ${IMAGE_TAG}:${VERSION} --format "{{.Size}}")
echo -e "${GREEN}✓ Image size: ${IMAGE_SIZE}${NC}"

# Test image if requested
if [ "$TEST" = true ]; then
    echo ""
    echo -e "${CYAN}🧪 Testing image...${NC}"
    
    # Test 1: Verify Ollama is installed
    echo -n "  Testing Ollama installation... "
    if docker run --rm ${IMAGE_TAG}:${VERSION} which ollama > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        exit 1
    fi
    
    # Test 2: Verify Python packages
    echo -n "  Testing Python packages... "
    if docker run --rm ${IMAGE_TAG}:${VERSION} python -c "import pandas, ollama, transformers, peft" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        exit 1
    fi
    
    # Test 3: Check Ollama models are pre-loaded
    echo -n "  Checking pre-loaded models... "
    docker run --rm ${IMAGE_TAG}:${VERSION} bash -c '
        ollama serve > /dev/null 2>&1 &
        sleep 5
        MODELS=$(ollama list 2>/dev/null | grep -E "mistral|gpt-oss|llama3.1" | wc -l)
        if [ "$MODELS" -ge 2 ]; then
            echo "PASS"
        else
            echo "FAIL"
        fi
        pkill ollama
    ' | grep -q "PASS"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ (models may need to be pulled at runtime)${NC}"
    fi
    
    # Test 4: Verify project files
    echo -n "  Checking project files... "
    if docker run --rm ${IMAGE_TAG}:${VERSION} test -f /workspace/vape-product-tagger/scripts/1_main.py; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All tests passed${NC}"
fi

# Push to Docker Hub if requested
if [ "$PUSH" = true ]; then
    echo ""
    echo -e "${CYAN}📤 Pushing to Docker Hub...${NC}"
    
    # Check if logged in
    if ! docker info 2>/dev/null | grep -q "Username"; then
        echo -e "${YELLOW}⚠  Not logged in to Docker Hub${NC}"
        read -p "Login now? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker login
        else
            echo "Push cancelled."
            exit 0
        fi
    fi
    
    echo "  Pushing ${IMAGE_TAG}:${VERSION}..."
    docker push ${IMAGE_TAG}:${VERSION}
    
    echo "  Pushing ${IMAGE_TAG}:latest..."
    docker push ${IMAGE_TAG}:latest
    
    echo -e "${GREEN}✓ Push completed${NC}"
    echo ""
    echo -e "${CYAN}🚀 Image available at:${NC}"
    echo "   docker pull ${IMAGE_TAG}:${VERSION}"
    echo "   docker pull ${IMAGE_TAG}:latest"
fi

# Summary
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     Build Summary                            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Image:${NC}         ${IMAGE_TAG}:${VERSION}"
echo -e "${CYAN}Size:${NC}          ${IMAGE_SIZE}"
echo -e "${CYAN}Build Time:${NC}    ${BUILD_MIN}m ${BUILD_SEC}s"
echo -e "${CYAN}Platform:${NC}      ${PLATFORM}"
echo ""

if [ "$PUSH" = true ]; then
    echo -e "${GREEN}✓ Ready for Vast.ai deployment${NC}"
    echo ""
    echo "Usage on Vast.ai:"
    echo "  vastai create instance ${IMAGE_TAG}:${VERSION} --gpu-ram 24 --disk 60"
else
    echo -e "${YELLOW}ℹ  Image built locally (not pushed)${NC}"
    echo ""
    echo "To push: ./vastai/build_docker.sh --push"
    echo "To test: docker run --rm -it --gpus all ${IMAGE_TAG}:${VERSION} bash"
fi
echo ""

# Save build metadata
BUILD_INFO="vastai/build_info.json"
cat > $BUILD_INFO <<EOF
{
  "image": "${IMAGE_TAG}",
  "version": "${VERSION}",
  "build_time": "${BUILD_MIN}m ${BUILD_SEC}s",
  "size": "${IMAGE_SIZE}",
  "platform": "${PLATFORM}",
  "pushed": ${PUSH},
  "build_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo -e "${CYAN}ℹ  Build info saved to: ${BUILD_INFO}${NC}"
echo ""
