# Docker Image Quick Start for Vast.ai

## Prerequisites

1. **Push image to Docker Hub** (one-time):
   ```bash
   cd /Users/home/Projects/python/vape-product-tagger
   ./vastai/build_docker.sh --push
   ```

2. **Upload your data to Vast.ai instance**

---

## Option 1: Direct Docker Run (Simplest)

### SSH into Vast.ai instance:
```bash
vastai ssh <instance_id>
```

### Upload your data (from local machine):
```bash
vastai scp <instance_id>:/workspace/data/ data/input/products.csv
```

### Run the pipeline:
```bash
docker run --gpus all --rm \
  -v /workspace/data:/workspace/data \
  -v /workspace/output:/workspace/output \
  coglabs/vape-tagger:latest
```

**Done!** Models are pre-loaded, starts in ~30 seconds.

---

## Option 2: Interactive Session

### Start container with bash:
```bash
docker run --gpus all --rm -it \
  -v /workspace/data:/workspace/data \
  -v /workspace/output:/workspace/output \
  shandj/vape-tagger:20251208 \
  bash
```

### Inside container, run pipeline manually:
```bash
cd /workspace/vape-product-tagger
source venv/bin/activate
python scripts/1_main.py \
  --input /workspace/data/products.csv \
  --output /workspace/output \
  --workers 4 \
  --audit-db
```

---

## Option 3: Custom Configuration

### Run with environment variables:
```bash
docker run --gpus all --rm \
  -v /workspace/data:/workspace/data \
  -v /workspace/output:/workspace/output \
  -e WORKERS=6 \
  -e AI_CONFIDENCE_THRESHOLD=0.8 \
  -e OLLAMA_MODEL=llama3.1:latest \
  shandj/vape-tagger:20251208
```

---

## Option 4: One-Liner from Fresh Instance

**Copy/paste this on a fresh Vast.ai instance:**

```bash
# Create directories and run
mkdir -p /workspace/data /workspace/output && \
docker run --gpus all --rm \
  -v /workspace/data:/workspace/data \
  -v /workspace/output:/workspace/output \
  shandj/vape-tagger:20251208
```

**Before running, upload your data:**
```bash
# From your local machine
vastai scp <instance_id>:/workspace/data/ data/input/products.csv
```

---

## Monitoring Progress

### View logs:
```bash
docker logs -f <container_id>
```

### Check GPU usage:
```bash
nvidia-smi
```

### Download results:
```bash
# From your local machine
vastai scp <instance_id>:/workspace/output/ ./output/
```

---

## Costs Comparison

| Method | Startup Time | Cost @ $0.40/hr (24GB GPU) |
|--------|--------------|----------------------------|
| **Pre-built Docker** | **30-60 sec** | **$0.07-0.13** |
| setup_vast.sh | 15-20 min | $2.00-2.67 |

**Savings: ~$2.50 per instance launch**

---

## Troubleshooting

### Check if image is available:
```bash
docker pull shandj/vape-tagger:20251208
```

### Verify models are pre-loaded:
```bash
docker run --rm shandj/vape-tagger:20251208 \
  bash -c 'ollama serve & sleep 5 && ollama list'
```

### Test without GPU (local):
```bash
docker run --rm -it shandj/vape-tagger:20251208 bash
```

---

## Alternative: Use Vast.ai Template

Create a Vast.ai template JSON:

```json
{
  "name": "Vape Tagger - Pre-loaded",
  "image": "shandj/vape-tagger:20251208",
  "gpu_ram": 24,
  "disk_space": 60,
  "env": {
    "WORKERS": "4",
    "AI_CONFIDENCE_THRESHOLD": "0.7"
  },
  "on_start": "echo 'Ready! Upload data to /workspace/data/products.csv and run the container.'"
}
```

Then create instance:
```bash
vastai create instance --template vape-tagger-template.json
```
