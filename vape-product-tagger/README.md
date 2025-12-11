# Vape Product Tagger

AI-powered product tagging system for Shopify vaping and CBD products. Combines rule-based pattern matching with Ollama AI for accurate, consistent product categorization with a complete fine-tuning pipeline.

## 🚀 New: Autonomous Pipeline

**Self-improving tagging pipeline that achieves 90%+ accuracy automatically!**

```bash
# One command deployment on Vast.ai
./vastai/deploy_autonomous.sh

# Run autonomous pipeline
./shell/run_autonomous_pipeline.sh -i products.csv -v
```

See [AUTONOMOUS_PIPELINE.md](AUTONOMOUS_PIPELINE.md) for complete documentation.

## Features

- **🤖 Autonomous Pipeline**: Self-improving tagging with continuous accuracy monitoring
- **Dual Tagging Engine**: Rule-based + AI-powered tagging with confidence scoring
- **Controlled Vocabulary**: Tags validated against `approved_tags.json`
- **Category-Aware AI**: Different prompts for CBD, e-liquid, pods, devices
- **Audit Database**: SQLite logging of all tagging decisions for analysis
- **Fine-Tuning Pipeline**: QLoRA training on Vast.ai with HF Hub integration
- **Dual Inference Backend**: Ollama (local) or HuggingFace (fine-tuned)
- **3-Tier Output**: Clean, review-needed, and untagged products in separate CSVs

## Supported Product Types

| Category | Tags |
|----------|------|
| **E-Liquid** | nic_salt, freebase_nicotine, shortfill |
| **CBD** | tincture, gummy, capsule, topical, oil, patch, beverage, edible |
| **CBD Spectrum** | full_spectrum, broad_spectrum, isolate, cbg, cbda |
| **Devices** | disposable, pod_system, box_mod, device |
| **Components** | coil, tank, replacement_pod, prefilled_pod |
| **Accessories** | battery, charger, case, mouthpiece |
| **VG/PG Ratios** | 50/50, 70/30, 80/20, 60/40, 100/0 |
| **Nicotine** | 0-20mg (range-based) |
| **CBD Strength** | 0-50000mg (range-based) |
| **Flavors** | fruity, tobacco, menthol, desserts/bakery, beverages |

## Quick Start

### Autonomous Pipeline (Recommended)

Get 90%+ accuracy automatically with self-improving tagging:

```bash
# Setup
cd vape-product-tagger
pip install -r requirements.txt
cp config.env.example config.env

# (Optional) Start Ollama for AI tagging
ollama serve &
ollama pull mistral:latest

# Run autonomous pipeline
./shell/run_autonomous_pipeline.sh -i your_products.csv -v
```

See [QUICKSTART_AUTONOMOUS.md](QUICKSTART_AUTONOMOUS.md) for complete guide.

### Manual Pipeline

For more control over individual steps:

```bash
# Setup
cd vape-product-tagger
./setup.sh
source venv/bin/activate

# Start Ollama (in another terminal)
ollama serve

# Run tagger
python scripts/1_main.py --input input/products.csv --audit-db output/audit.sqlite3
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

## Installation

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) (for AI tagging)

### Setup

```bash
# Automated
./setup.sh  # Linux/Mac
setup.bat   # Windows

# Or manual
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.env.example config.env
```

## Usage

### Basic Tagging

```bash
# AI + rule-based tagging
python main.py --input input/products.csv

# Rule-based only (faster, no Ollama needed)
python main.py --input input/products.csv --no-ai

# With audit database (recommended)
python main.py --input input/products.csv --audit-db output/audit.sqlite3

# Limit for testing
python main.py --input input/products.csv --limit 10 --verbose
```

### Output Files

```
output/
├── controlled_tagged_products.csv      # Tagged products for Shopify
└── controlled_untagged_products.csv    # Products that couldn't be tagged
```

### Command Line Options

```
python main.py --help

Required:
  --input, -i PATH       Input Shopify CSV file

Optional:
  --output, -o PATH      Output CSV file
  --no-ai                Disable AI tagging (rule-based only)
  --limit, -l N          Process only first N products
  --verbose, -v          Enable detailed logging
  --audit-db PATH        SQLite path for audit logging
  --run-id ID            Resume a specific run
  --type, -t TYPE        Override product type (e.g., "CBD products")
  --config, -c PATH      Custom config file path
```

## Configuration

Edit `config.env`:

```env
# AI Model
OLLAMA_MODEL=llama3.1
AI_CONFIDENCE_THRESHOLD=0.7

# Model Backend: ollama (default) or huggingface
MODEL_BACKEND=ollama

# HuggingFace (for fine-tuned models)
HF_TOKEN=hf_xxx
HF_REPO_ID=username/vape-tagger-lora

# Training (Vast.ai)
BASE_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
QUANTIZATION_BITS=4
LORA_R=64
LORA_ALPHA=128
```

## Audit & Analysis

### Enable Audit Logging

```bash
python main.py --input products.csv --audit-db output/audit.sqlite3
```

### Analyze Results

```bash
# Export training data from audit
python tag_auditor.py --audit-db output/audit.sqlite3 --output training_data.csv

# View audit summary
python tag_auditor.py --audit-db output/audit.sqlite3 --summary
```

### Query Audit Database

```bash
sqlite3 output/audit.sqlite3

# Recent runs
SELECT run_id, started_at, status FROM runs ORDER BY started_at DESC LIMIT 5;

# Products with AI metadata
SELECT handle, ai_confidence, ai_reasoning FROM products WHERE ai_confidence IS NOT NULL LIMIT 10;
```

## Training Pipeline

Fine-tune a model on your audit data for improved accuracy.

### Prerequisites
- [Vast.ai](https://vast.ai) account (24GB+ VRAM instance)
- [Hugging Face](https://huggingface.co) account
- 100+ tagged products in audit DB

### Workflow

```
Products CSV → Tagger (rule+AI) → Audit DB → Training Export
                                      ↓
                              Vast.ai QLoRA Training
                                      ↓
                              HF Hub (LoRA adapters)
                                      ↓
                              Production Inference
```

---

## Running on Vast.ai (Full Workflow)

Run the complete pipeline (tagging → audit → training) on Vast.ai GPU instances.

### One-Line Setup (Recommended)

SSH into your Vast.ai instance and run:

```bash
curl -fsSL https://raw.githubusercontent.com/shand-j/python/main/vape-product-tagger/vastai/setup_vast.sh | bash
```

This automatically:
- Installs system dependencies (git, sqlite3, etc.)
- Clones the repository
- Creates Python virtual environment
- Installs all Python packages (including training deps)
- Installs Ollama and pulls llama3.1 model
- Configures the environment

**With HuggingFace token:**
```bash
HF_TOKEN=hf_xxx HF_REPO_ID=username/vape-tagger-lora \
  curl -fsSL https://raw.githubusercontent.com/shand-j/python/main/vape-product-tagger/vastai/setup_vast.sh | bash
```

**Options:**
```bash
SKIP_OLLAMA=1      # Skip Ollama installation
SKIP_TRAINING=1    # Skip training dependencies
BRANCH=dev         # Use different git branch
```

After setup, activate and run:
```bash
source /workspace/activate_tagger.sh
python main.py --input /workspace/data/products.csv --audit-db /workspace/data/audit.sqlite3
```

---

### Manual Setup

If you prefer manual setup:

#### Step 1: Rent a Vast.ai Instance

1. Go to [vast.ai/console/create](https://cloud.vast.ai/console/create/)
2. Filter for **24GB+ VRAM** (RTX 4090, A5000, A6000, A100)
3. Select **PyTorch 2.1 + CUDA 12.1** template
4. Recommended specs:
   - GPU: 24GB+ VRAM
   - Disk: 50GB+
   - RAM: 32GB+

#### Step 2: Setup Environment

SSH into your instance and run:

```bash
# Install system dependencies
apt-get update && apt-get install -y git sqlite3

# Clone repository
cd /workspace
git clone https://github.com/shand-j/python.git
cd python/vape-product-tagger

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (includes training + inference)
pip install -r requirements.txt
pip install -r vastai/requirements-train.txt

# Optional: Flash Attention for faster training (takes 15-30 min)
pip install flash-attn --no-build-isolation

# Setup Ollama for AI tagging
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
sleep 5
ollama pull llama3.1
```

#### Step 3: Upload Your Data

```bash
# Create input directory
mkdir -p /workspace/data

# Upload your Shopify export CSV (use scp, rsync, or Vast.ai file browser)
# Example with scp from local machine:
# scp products.csv root@<vast-ip>:/workspace/data/
```

### Step 4: Run Tagger with Audit

```bash
cd /workspace/python/vape-product-tagger

# Run tagger with audit database
python main.py \
  --input /workspace/data/products.csv \
  --output /workspace/data/tagged_products.csv \
  --audit-db /workspace/data/audit.sqlite3 \
  --verbose

# Check results
ls -la /workspace/data/
sqlite3 /workspace/data/audit.sqlite3 "SELECT COUNT(*) FROM products"
```

### Step 5: Analyze Audit & Export Training Data

```bash
# View audit summary
python tag_auditor.py \
  --audit-db /workspace/data/audit.sqlite3 \
  --summary

# Export training data
python tag_auditor.py \
  --audit-db /workspace/data/audit.sqlite3 \
  --output /workspace/data/training_data.csv

# Convert to JSONL for training
python train_tag_model.py \
  --export \
  --input /workspace/data/training_data.csv \
  --output /workspace/data/training_data.jsonl
```

### Step 6: Train Model

```bash
# Set HuggingFace credentials
export HF_TOKEN=hf_your_token
export HF_REPO_ID=your-username/vape-tagger-lora

# Login to HF Hub
huggingface-cli login --token $HF_TOKEN

# Run QLoRA training
python train_tag_model.py \
  --train \
  --input /workspace/data/training_data.jsonl \
  --output-dir /workspace/models/vape-tagger-lora \
  --epochs 3 \
  --batch-size 4 \
  --push-to-hub

# Training takes ~30-60 min depending on data size and GPU
```

### Step 7: Evaluate Model

```bash
# Generate predictions on test set
python train_tag_model.py \
  --generate-predictions \
  --model-path /workspace/models/vape-tagger-lora \
  --input /workspace/data/training_data.jsonl \
  --output /workspace/data/predictions.jsonl

# Evaluate accuracy
python train_tag_model.py \
  --evaluate \
  --predictions /workspace/data/predictions.jsonl \
  --corrections /workspace/data/training_data.csv \
  --eval-output /workspace/data/evaluation.csv
```

### Step 8: Use Fine-Tuned Model

After training, use the fine-tuned model for inference:

```bash
# Update config to use HF backend
cat > config.env << EOF
MODEL_BACKEND=huggingface
HF_TOKEN=$HF_TOKEN
HF_REPO_ID=$HF_REPO_ID
BASE_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
EOF

# Run tagger with fine-tuned model
python main.py \
  --input /workspace/data/new_products.csv \
  --output /workspace/data/new_tagged.csv \
  --audit-db /workspace/data/audit.sqlite3
```

### Automated Script

Use the automation scripts for the full pipeline:

```bash
# One-command setup + training
export HF_TOKEN=hf_your_token
export HF_REPO_ID=your-username/vape-tagger-lora
export INPUT_CSV=/workspace/data/products.csv

./setup_training.sh
./run_training.sh --push-to-hub
```

### Download Results

Before terminating your instance, download outputs:

```bash
# From your local machine:
scp -r root@<vast-ip>:/workspace/data/ ./vast-output/
scp -r root@<vast-ip>:/workspace/models/ ./vast-models/
```

---

## Project Structure

```
vape-product-tagger/
├── main.py                    # Main tagger CLI
├── tag_audit_db.py            # SQLite audit database
├── tag_auditor.py             # Audit analysis & export
├── tag_validator.py           # Tag validation utilities
├── train_tag_model.py         # QLoRA training script
├── approved_tags.json         # Controlled vocabulary
├── config.env.example         # Configuration template
├── requirements.txt           # Python dependencies
├── setup.sh / setup.bat       # Setup scripts
├── setup_training.sh          # Vast.ai training setup
├── run_training.sh            # Training automation
├── vastai/                    # Vast.ai template
│   ├── Dockerfile
│   ├── template.json
│   └── requirements-train.txt
├── input/                     # Input CSV files
├── output/                    # Tagged output files
├── logs/                      # Application logs
└── cache/                     # AI tag cache
```

## Customizing Tags

Edit `approved_tags.json` to add/modify tags:

```json
{
  "category": ["e-liquid", "CBD", "device", "accessory"],
  "nicotine_strength": {
    "range": {"min": 0, "max": 20, "unit": "mg"}
  },
  "cbd_strength": {
    "range": {"min": 0, "max": 50000, "unit": "mg"}
  },
  "vg_ratio": {
    "tags": ["50/50", "70/30", "80/20"],
    "applies_to": ["e-liquid"]
  }
}
```

## Troubleshooting

### "Ollama service not available"
```bash
ollama serve  # Start Ollama
# Or use --no-ai for rule-based only
```

### Low tagging accuracy
1. Adjust `AI_CONFIDENCE_THRESHOLD` in config (try 0.6)
2. Review audit DB for patterns
3. Fine-tune model on your data

### "HF model loading failed"
```bash
# Ensure token has access to gated models
huggingface-cli login
# Accept Llama 3.1 license at https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct
```

### Memory issues during training
- Reduce batch size: `--batch-size 2`
- Use 4-bit quantization: `QUANTIZATION_BITS=4`
- Ensure 24GB+ VRAM available

## Architecture

### Tagging Flow

1. **Rule-based extraction**: Pattern matching for VG/PG, nicotine strength, CBD form
2. **Category detection**: Determine product type from handle/title
3. **AI enhancement**: Category-aware prompting with confidence scoring
4. **Tag validation**: Filter against `approved_tags.json`
5. **Deduplication**: One tag per category, most specific wins

### AI Confidence Scoring

The AI returns confidence scores (0.0-1.0):
- **0.95-1.0**: Explicit in title (e.g., "Nic Salt" → nic_salt)
- **0.80-0.94**: Strong evidence from multiple sources
- **0.60-0.79**: Reasonable inference with ambiguity
- **Below 0.60**: Rejected (uses rule-based only)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `python -m pytest test/`
4. Submit a pull request

## License

MIT License - See LICENSE file for details.
