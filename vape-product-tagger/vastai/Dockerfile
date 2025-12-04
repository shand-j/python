# Vast.ai Training Template for Vape Product Tagger
# QLoRA fine-tuning with Llama 3.1 8B Instruct
#
# Build: docker build -t vape-tagger-train .
# Requires: 24GB+ VRAM GPU instance

FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel

LABEL maintainer="vape-product-tagger"
LABEL description="QLoRA fine-tuning for product tagging with Llama 3.1 8B"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    vim \
    htop \
    nvtop \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create workspace
WORKDIR /workspace

# Install Python dependencies
COPY requirements-train.txt /tmp/requirements-train.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements-train.txt

# Install flash-attention (optional, improves speed)
RUN pip install --no-cache-dir flash-attn --no-build-isolation || echo "flash-attn install failed, continuing without it"

# Create directories
RUN mkdir -p /workspace/data /workspace/models /workspace/output /workspace/checkpoints

# Copy project files (mount at runtime for flexibility)
# COPY . /workspace/vape-product-tagger

# Default command
CMD ["/bin/bash"]
