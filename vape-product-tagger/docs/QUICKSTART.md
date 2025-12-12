# Quick Start Guide - Vape Product Tagger

Get started with AI-powered product tagging in 5 minutes!

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) installed (for AI tagging)
- A Shopify product export CSV

## Step 1: Setup (2 minutes)

```bash
cd vape-product-tagger

# Linux/Mac
chmod +x setup.sh && ./setup.sh

# Windows
setup.bat
```

This creates a virtual environment, installs dependencies, and generates `config.env`.

## Step 2: Activate Environment

```bash
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate.bat
```

## Step 3: Start Ollama

In a separate terminal:
```bash
ollama serve
```

Pull a model if you haven't:
```bash
ollama pull llama3.1
```

## Step 4: Run the Tagger

### Basic Usage
```bash
python main.py --input input/your_products.csv
```

### With Audit Database (Recommended)
```bash
python main.py --input input/products.csv --audit-db output/audit.sqlite3
```

### Rule-Based Only (No AI)
```bash
python main.py --input input/products.csv --no-ai
```

### Limit for Testing
```bash
python main.py --input input/products.csv --limit 10 --verbose
```

## Step 5: Review Results

Check `output/` directory:
- `controlled_tagged_products.csv` - Tagged products for Shopify import
- `controlled_untagged_products.csv` - Products that couldn't be tagged

## What Gets Tagged?

### Product Categories
- **E-Liquid**: nic_salt, freebase_nicotine, shortfill
- **CBD**: tincture, gummy, capsule, topical, full_spectrum, broad_spectrum, isolate
- **Devices**: disposable, pod_system, box_mod, coil, tank
- **Accessories**: battery, charger, case

### Automatic Detection
- **VG/PG Ratios**: 50/50, 70/30, 80/20, etc.
- **Nicotine Strength**: 0-20mg range
- **CBD Strength**: 0-50000mg range
- **Flavors**: fruity, tobacco, menthol, desserts/bakery

## Example

**Input**: `"Blue Raspberry 20mg Nic Salt 50VG/50PG 10ml"`

**Output Tags**: `e-liquid, nic_salt, 20mg, 50/50, fruity, 10ml`

## Command Reference

```bash
python main.py --help

# Key options:
--input, -i     Input CSV file (required)
--output, -o    Output CSV file
--no-ai         Disable AI (rule-based only)
--limit, -l     Process only first N products
--verbose, -v   Enable detailed logging
--audit-db      SQLite path for audit logging
--type, -t      Override product type for all products
```

## Troubleshooting

### "Ollama service not available"
```bash
# Start Ollama
ollama serve

# Or run without AI
python main.py --input products.csv --no-ai
```

### "Module not found"
```bash
# Ensure venv is activated
source venv/bin/activate
pip install -r requirements.txt
```

### Low tagging accuracy
1. Check `approved_tags.json` has relevant tags
2. Review audit DB for patterns: `sqlite3 output/audit.sqlite3 "SELECT * FROM products LIMIT 5"`
3. Adjust confidence threshold in config: `AI_CONFIDENCE_THRESHOLD=0.6`

## Next Steps

1. **Review Tags**: Check output CSV before Shopify import
2. **Audit Analysis**: Run `python tag_auditor.py --audit-db output/audit.sqlite3`
3. **Fine-tune Model**: See [Training Pipeline](#training-pipeline-advanced) below
4. **Customize Tags**: Edit `approved_tags.json`

---

# Training Pipeline (Advanced)

Fine-tune a model on your audit data for improved accuracy.

## Prerequisites
- Vast.ai account (GPU instances)
- Hugging Face account (model storage)
- 100+ tagged products in audit DB

## Step 1: Export Training Data

```bash
# Generate training CSV from audit
python tag_auditor.py --audit-db output/audit.sqlite3 --output training_data.csv

# Convert to JSONL for training
python train_tag_model.py --export --input training_data.csv --output training_data.jsonl
```

## Step 2: Train on Vast.ai

1. Rent a 24GB+ VRAM instance (RTX 4090, A5000, A6000)
2. Clone repo and setup:

```bash
git clone https://github.com/shand-j/python.git
cd python/vape-product-tagger

# Set credentials
export HF_TOKEN=hf_your_token
export HF_REPO_ID=your-username/vape-tagger-lora

# Run training
./setup_training.sh
./run_training.sh --push-to-hub
```

## Step 3: Use Fine-Tuned Model

Update `config.env`:
```env
MODEL_BACKEND=huggingface
HF_REPO_ID=your-username/vape-tagger-lora
HF_TOKEN=hf_your_token
```

Run tagger:
```bash
python main.py --input products.csv
```

---

# Full Vast.ai Workflow (Tagger + Audit + Training)

Run the complete pipeline on a Vast.ai GPU instance.

## Quick Setup

```bash
# SSH into Vast.ai instance
ssh -p <port> root@<vast-ip>

# Install Ollama for AI inference
curl -fsSL https://ollama.ai/install.sh | sh
nohup ollama serve > /dev/null 2>&1 &
ollama pull llama3.1

# Clone and setup
git clone https://github.com/shand-j/python.git
cd python/vape-product-tagger
pip install -r requirements.txt
pip install -r vastai/requirements-train.txt
```

## Upload Data (from local machine)
```bash
scp -P <port> your_products.csv root@<vast-ip>:/workspace/data/
```

## Run Full Pipeline

```bash
# 1. Tag products with audit
python main.py --input /workspace/data/products.csv \
  --output /workspace/data/tagged.csv \
  --audit-db /workspace/data/audit.sqlite3

# 2. Export training data
python tag_auditor.py --audit-db /workspace/data/audit.sqlite3 \
  --output /workspace/data/training.csv
python train_tag_model.py --export \
  --input /workspace/data/training.csv \
  --output /workspace/data/training.jsonl

# 3. Train model
huggingface-cli login --token $HF_TOKEN
python train_tag_model.py --train \
  --input /workspace/data/training.jsonl \
  --epochs 3 --push-to-hub
```

## Download Results (from local machine)
```bash
scp -r -P <port> root@<vast-ip>:/workspace/data/ ./vast-output/
```

See [README.md](README.md#running-on-vastai-full-workflow) for detailed instructions.

---

## Getting Help

```bash
# View all options
python main.py --help

# Verbose logging
python main.py --input products.csv --verbose

# Check logs
cat logs/*.log
```

See [README.md](README.md) for complete documentation.
