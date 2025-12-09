# Vast.ai Pipeline Template for Vape Product Tagger
# Includes Ollama for AI cascade tagging and QLoRA training support
#
# Build: docker build -f vastai/Dockerfile -t coglabs/vape-tagger:latest .
# Supports: Tagging pipeline + Training (24GB+ VRAM recommended)

FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel

LABEL maintainer="vape-product-tagger"
LABEL description="Complete pipeline for product tagging with AI cascade and training"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=0.0.0.0:11434

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    vim \
    htop \
    nvtop \
    sqlite3 \
    bc \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Create workspace
WORKDIR /workspace

# Copy and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Install training dependencies (for QLoRA fine-tuning) - use specific versions to avoid resolver issues
RUN pip install --no-cache-dir \
    transformers==4.36.0 \
    peft==0.7.1 \
    trl==0.7.4 \
    bitsandbytes==0.41.3 \
    accelerate==0.25.0 \
    datasets==2.15.0 \
    scikit-learn==1.3.2

# Skip flash-attention - it's optional and takes 5+ minutes to build
# Users can install manually if needed: pip install flash-attn --no-build-isolation

# Create directories
RUN mkdir -p \
    /workspace/data \
    /workspace/models \
    /workspace/output \
    /workspace/checkpoints \
    /workspace/logs \
    /workspace/cache

# Pre-pull Ollama models (ENABLED - saves 15+ min on startup)
# This increases image size by ~15GB but reduces instance startup from 20min to 1min
RUN ollama serve & \
    OLLAMA_PID=$! && \
    sleep 10 && \
    echo "Pulling mistral:latest..." && \
    ollama pull mistral:latest && \
    echo "Pulling gpt-oss:latest..." && \
    ollama pull gpt-oss:latest && \
    echo "Pulling llama3.1:latest..." && \
    ollama pull llama3.1:latest && \
    echo "Models cached successfully" && \
    kill "$OLLAMA_PID" && \
    wait "$OLLAMA_PID" 2>/dev/null || true

# Copy project files (done after deps so code changes don't invalidate cache)
COPY . /workspace/vape-product-tagger
WORKDIR /workspace/vape-product-tagger

# Copy entrypoint script
COPY vastai/pipeline_entrypoint.sh /workspace/pipeline_entrypoint.sh
RUN chmod +x /workspace/pipeline_entrypoint.sh

# Expose Ollama port
EXPOSE 11434

# Health check for Ollama
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:11434/api/version || exit 1

# Environment variables
ENV WORKSPACE=/workspace
ENV DATA_DIR=/workspace/data
ENV OUTPUT_DIR=/workspace/output
ENV PYTHONPATH=/workspace/vape-product-tagger:$PYTHONPATH

# Default command - run pipeline entrypoint
CMD ["/workspace/pipeline_entrypoint.sh"]

