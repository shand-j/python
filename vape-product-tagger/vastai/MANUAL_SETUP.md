# Manual Vast.ai Setup Guide

If the automated scripts aren't working, follow this manual process.

## Prerequisites

1. **Create Vast.ai account**: https://console.vast.ai/
2. **Install vastai CLI**:
   ```bash
   pip install vastai
   ```
3. **Get API key**: https://console.vast.ai/account → API Keys
4. **Configure CLI**:
   ```bash
   vastai set api-key YOUR_API_KEY
   ```

## Option 1: Web Interface (Easiest)

### Step 1: Search for GPU
1. Go to: https://console.vast.ai/templates/
2. Click "CREATE TEMPLATE"
3. Paste this config:

```json
{
  "name": "Vape Tagger - Pre-loaded",
  "image": "coglabs/vape-tagger:latest",
  "env": {
    "WORKERS": "4",
    "AI_CONFIDENCE_THRESHOLD": "0.7",
    "OLLAMA_HOST": "0.0.0.0:11434"
  }
}
```

4. Save template
5. Go to: https://console.vast.ai/instances/
6. Click "RENT" → Select your template → Choose GPU with 24GB+ VRAM

### Step 2: Upload Data
```bash
# Get instance ID from web UI
vastai scp <INSTANCE_ID>:/workspace/data/ data/input/products.csv
```

### Step 3: SSH and Run
```bash
vastai ssh <INSTANCE_ID>

# Inside instance:
cd /workspace/vape-product-tagger
source venv/bin/activate
python scripts/1_main.py --input /workspace/data/products.csv --workers 4
```

### Step 4: Download Results
```bash
vastai scp <INSTANCE_ID>:/workspace/output/ ./output/
```

### Step 5: Stop Instance
```bash
vastai stop instance <INSTANCE_ID>
```

---

## Option 2: CLI Manual

### Step 1: Search for Available GPUs
```bash
vastai search offers \
  "cuda_vers>=12.0 gpu_ram>=24 reliability>0.95" \
  --order "dph_base+"
```

Look for RTX 4090, RTX 3090, A5000, or A6000 under $0.50/hr.

### Step 2: Create Instance
```bash
# Replace <OFFER_ID> with the ID from search results
vastai create instance <OFFER_ID> \
  --image coglabs/vape-tagger:latest \
  --disk 60 \
  --env WORKERS=4 \
  --env AI_CONFIDENCE_THRESHOLD=0.7 \
  --env OLLAMA_HOST=0.0.0.0:11434
```

This will output an instance ID like: `Started. {'success': True, 'new_contract': 12345678}`

### Step 3: Wait for Instance to Start
```bash
# Check status
vastai show instance <INSTANCE_ID>
```

Wait until status shows "running" (~30 seconds with pre-built image).

### Step 4: Upload Your Data
```bash
vastai scp <INSTANCE_ID>:/workspace/data/ data/input/products.csv
```

### Step 5: SSH and Run Pipeline
```bash
vastai ssh <INSTANCE_ID>

# Inside the instance:
cd /workspace/vape-product-tagger
source venv/bin/activate

# Run tagging pipeline
python scripts/1_main.py \
  --input /workspace/data/products.csv \
  --output /workspace/output \
  --workers 4 \
  --audit-db

# Monitor progress
tail -f logs/*.log
```

### Step 6: Download Results
```bash
# From your local machine (new terminal):
vastai scp <INSTANCE_ID>:/workspace/output/ ./output/
```

### Step 7: Stop Instance (Important!)
```bash
vastai stop instance <INSTANCE_ID>
```

**⚠️ Don't forget this step or you'll keep paying!**

---

## Option 3: Direct Docker Commands (If SSH'd in)

If you've SSH'd into a Vast.ai instance that doesn't have the image yet:

```bash
# Pull the pre-built image
docker pull coglabs/vape-tagger:latest

# Run the pipeline
docker run --gpus all --rm \
  -v /workspace/data:/workspace/data \
  -v /workspace/output:/workspace/output \
  coglabs/vape-tagger:latest
```

---

## Troubleshooting

### "403: This action requires login"
```bash
vastai set api-key YOUR_API_KEY
```

### "No suitable offers found"
Try lowering requirements:
```bash
vastai search offers "cuda_vers>=12.0 gpu_ram>=16" --order "dph_base+"
```

### "Image not found: coglabs/vape-tagger:latest"
You need to push the Docker image first:
```bash
cd /Users/home/Projects/python/vape-product-tagger
./vastai/build_docker.sh --push
```

### Check vastai CLI is working
```bash
vastai show user
```

Should show your account details.

---

## Cost Estimates

| GPU Model | RAM | Price/hr | 60K products | Build Time |
|-----------|-----|----------|--------------|------------|
| RTX 3090 | 24GB | $0.17-0.25 | ~2-3 hours | ~$0.50-0.75 |
| RTX 4090 | 24GB | $0.30-0.45 | ~1.5-2 hours | ~$0.60-0.90 |
| A5000 | 24GB | $0.35-0.50 | ~2-2.5 hours | ~$0.85-1.25 |
| A100 | 40GB | $0.80-1.20 | ~1-1.5 hours | ~$1.00-1.80 |

**Processing rate**: ~50-100 products/minute with 4 workers

---

## Quick Reference Commands

```bash
# Search GPUs
vastai search offers "cuda_vers>=12.0 gpu_ram>=24" --order "dph_base+"

# Create instance
vastai create instance <OFFER_ID> --image coglabs/vape-tagger:latest --disk 60

# Check status
vastai show instances

# Upload data
vastai scp <INSTANCE_ID>:/workspace/data/ data/input/products.csv

# SSH
vastai ssh <INSTANCE_ID>

# Download results
vastai scp <INSTANCE_ID>:/workspace/output/ ./output/

# Stop instance
vastai stop instance <INSTANCE_ID>

# Check costs
vastai show user
```
