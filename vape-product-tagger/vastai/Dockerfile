# Vast.ai Pipeline Template for Vape Product Tagger
# Includes Ollama for AI cascade tagging and QLoRA training support
#
# Build: docker build -t vape-tagger-pipeline .
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

# Install Python dependencies for pipeline
COPY requirements-train.txt /tmp/requirements-train.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements-train.txt

# Install additional pipeline dependencies
RUN pip install --no-cache-dir \
    pandas>=2.2.0 \
    requests>=2.31.0 \
    python-dotenv>=1.0.0 \
    colorlog>=6.8.0 \
    ollama>=0.2.0

# Install flash-attention (optional, improves training speed)
RUN pip install --no-cache-dir flash-attn --no-build-isolation || \
    echo "flash-attn install failed, continuing without it"

# Create directories
RUN mkdir -p \
    /workspace/data \
    /workspace/models \
    /workspace/output \
    /workspace/checkpoints \
    /workspace/logs \
    /workspace/cache

# Pre-pull Ollama models (optional - can be done at runtime)
# Uncomment to pre-load models (increases image size but faster startup)
# RUN ollama serve & \
#     sleep 5 && \
#     ollama pull mistral:latest && \
#     ollama pull gpt-oss:latest && \
#     ollama pull llama3.1:latest && \
#     pkill ollama

# Copy entrypoint script
COPY pipeline_entrypoint.sh /workspace/pipeline_entrypoint.sh
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

