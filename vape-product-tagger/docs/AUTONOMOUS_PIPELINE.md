# Autonomous AI Tagging Pipeline

## Overview

The Autonomous AI Tagging Pipeline is a self-improving product tagging system that automatically:
- Tags products using AI cascade (mistral → gpt-oss → llama3.1)
- Validates tags against approved vocabulary
- Reviews and retries low-confidence tags
- Iteratively improves until reaching 90%+ accuracy target
- Exports clean, review-needed, and untagged products to separate CSVs

## Key Features

### 🔄 Self-Improving Loop
- Automatically retries low-confidence products with third opinion recovery
- Tracks accuracy metrics across iterations
- Stops when target accuracy is achieved or max iterations reached

### 📊 Comprehensive Metrics
- Overall accuracy tracking
- Per-category accuracy breakdown
- Confidence score distribution
- Model usage statistics

### 🎯 Quality Gates
- Configurable accuracy target (default: 90%)
- Validation against approved tag vocabulary
- CBD 3-dimension requirement enforcement
- Nicotine strength limits (0-20mg)

### 🚀 Vast.ai Optimized
- One-command deployment script
- Automatic Ollama installation and model pulling
- GPU utilization monitoring
- Remote execution ready

## Quick Start

### Local Development

```bash
# 1. Setup environment
cd vape-product-tagger
pip install -r requirements.txt
cp config.env.example config.env

# 2. Start Ollama
ollama serve &
ollama pull mistral:latest
ollama pull gpt-oss:latest  
ollama pull llama3.1:latest

# 3. Run autonomous pipeline
./shell/run_autonomous_pipeline.sh -i data/products.csv -v

# Or directly with Python
python scripts/autonomous_pipeline.py --input data/products.csv --output output/autonomous --verbose
```

### Vast.ai Deployment

```bash
# 1. SSH into Vast.ai instance
ssh -p <port> root@<vast-ip>

# 2. Clone and deploy
git clone https://github.com/shand-j/python.git
cd python/vape-product-tagger
./vastai/deploy_autonomous.sh

# 3. Upload data (from local machine)
scp -P <port> products.csv root@<vast-ip>:/workspace/python/vape-product-tagger/data/

# 4. Run pipeline (on Vast.ai)
./shell/run_autonomous_pipeline.sh -i data/products.csv -v

# 5. Download results (from local machine)
scp -P <port> -r root@<vast-ip>:/workspace/python/vape-product-tagger/output/autonomous/ ./results/
```

## Command Reference

### Shell Wrapper

```bash
./shell/run_autonomous_pipeline.sh [options]

Options:
  -i, --input FILE          Input CSV file (required)
  -o, --output DIR          Output directory (default: output/autonomous)
  -c, --config FILE         Config file (default: config.env)
  --no-ai                   Disable AI tagging
  -l, --limit N             Process only first N products
  -t, --target ACCURACY     Target accuracy 0.0-1.0 (default: 0.90)
  -m, --max-iterations N    Max improvement iterations (default: 3)
  -v, --verbose             Verbose logging
  -h, --help                Show help
```

### Python Script

```bash
python scripts/autonomous_pipeline.py [options]

Options:
  --input, -i FILE          Input CSV file (required)
  --output, -o DIR          Output directory (default: output/)
  --config, -c FILE         Configuration file path
  --no-ai                   Disable AI tagging
  --limit, -l N             Limit to first N products
  --target, -t FLOAT        Target accuracy (default: 0.90)
  --max-iterations, -m N    Max iterations (default: 3)
  --verbose, -v             Enable verbose logging
```

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Autonomous Pipeline Loop                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Iteration 0: Initial Tagging                │
│  1. Import products from CSV                                    │
│  2. Tag each product (rule-based + AI cascade)                  │
│  3. Validate tags                                               │
│  4. Calculate accuracy metrics                                  │
│  5. Save to audit DB                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
                    Accuracy >= Target?
                         │
              ┌──────────┴──────────┐
              │                     │
             YES                   NO
              │                     │
              │                     ▼
              │    ┌─────────────────────────────────────────────┐
              │    │  Iteration 1-N: Improvement Cycles          │
              │    │  1. Identify low-confidence products        │
              │    │  2. Force third opinion recovery            │
              │    │  3. Re-validate improved tags               │
              │    │  4. Recalculate accuracy                    │
              │    │  5. Update audit DB                         │
              │    └────────────┬────────────────────────────────┘
              │                 │
              │                 ▼
              │            Accuracy >= Target OR
              │            Iterations >= Max?
              │                 │
              └─────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Export Results                             │
│  1. Generate 3-tier CSV export:                                 │
│     - {timestamp}_tagged_clean.csv (ready for Shopify)          │
│     - {timestamp}_tagged_review.csv (needs human review)        │
│     - {timestamp}_untagged.csv (failed tagging)                 │
│  2. Save final metrics to audit DB                              │
│  3. Generate summary report                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Output Structure

```
output/autonomous/
├── audit_iteration_0.db              # Initial tagging audit
├── audit_iteration_1.db              # First improvement audit
├── 20241210_235959_tagged_clean.csv  # Ready for Shopify import
├── 20241210_235959_tagged_review.csv # Needs manual review
└── 20241210_235959_untagged.csv      # Failed tagging

logs/
└── autonomous_pipeline_20241210_235959.log

Each CSV includes:
- All standard Shopify columns (Handle, Title, Body, Tags, etc.)
- Needs Manual Review (YES/NO)
- AI Confidence (0.00-1.00)
- Model Used (mistral/gpt-oss/llama3.1/recovery)
- Failure Reasons (if any)
- Category (detected)
- Rule Based Tags (JSON)
- AI Suggested Tags (JSON)
- Secondary Flavors (JSON)
```

## Configuration

Key settings in `config.env`:

```bash
# AI Cascade Models
PRIMARY_AI_MODEL=mistral:latest
SECONDARY_AI_MODEL=gpt-oss:latest
TERTIARY_AI_MODEL=llama3.1:latest

# Confidence Threshold
AI_CONFIDENCE_THRESHOLD=0.7

# Third Opinion Recovery
ENABLE_THIRD_OPINION=true

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=180
OLLAMA_NUM_PARALLEL=6

# Performance
BATCH_SIZE=8
MAX_WORKERS=6
PARALLEL_PROCESSING=true

# Output
OUTPUT_DIR=./output
LOGS_DIR=./logs
```

## Performance Optimization

### GPU Instances (Vast.ai)
- **Recommended**: RTX 4090, A5000, A6000 (24GB+ VRAM)
- **Expected Rate**: 30-60 products/minute with AI
- **Model Loading**: ~2-3 minutes initial setup

### Parallel Processing
```bash
# In config.env
MAX_WORKERS=8              # More workers = faster (use CPU count)
OLLAMA_NUM_PARALLEL=6      # Concurrent Ollama requests
BATCH_SIZE=8               # Products per batch
```

### Caching
```bash
# Enable caching for repeated products
CACHE_AI_TAGS=true
CACHE_DIR=./cache
```

## Monitoring

### Real-time Progress
```bash
# Watch pipeline logs
tail -f logs/autonomous_pipeline_*.log

# GPU utilization
watch -n 1 nvidia-smi

# Ollama service
tail -f /tmp/ollama.log
```

### Audit Database Queries
```bash
# Check accuracy by category
sqlite3 output/autonomous/audit_iteration_0.db << 'EOF'
SELECT 
  category,
  COUNT(*) as total,
  SUM(CASE WHEN needs_manual_review = 0 AND final_tags != '[]' THEN 1 ELSE 0 END) as clean,
  ROUND(AVG(primary_model_confidence), 2) as avg_confidence
FROM products
GROUP BY category;
EOF

# View low-confidence products
sqlite3 output/autonomous/audit_iteration_0.db << 'EOF'
SELECT handle, title, primary_model_confidence, needs_manual_review
FROM products
WHERE primary_model_confidence < 0.7
LIMIT 10;
EOF
```

## Troubleshooting

### Ollama Connection Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# Restart Ollama
pkill ollama
nohup ollama serve > /tmp/ollama.log 2>&1 &
```

### Low Accuracy
- Check `failure_reasons` in tagged_review.csv
- Review category-specific accuracy in logs
- Adjust `AI_CONFIDENCE_THRESHOLD` in config.env
- Increase `MAX_ITERATIONS` for more improvement cycles

### Performance Issues
- Reduce `MAX_WORKERS` if CPU-bound
- Reduce `BATCH_SIZE` if memory-limited
- Enable caching: `CACHE_AI_TAGS=true`
- Use faster primary model (mistral is fastest)

### Out of Memory
```bash
# In config.env
MAX_WORKERS=4              # Reduce parallelism
BATCH_SIZE=4               # Smaller batches
OLLAMA_NUM_PARALLEL=3      # Fewer concurrent requests
```

## Examples

### Basic Run
```bash
./shell/run_autonomous_pipeline.sh -i data/products.csv
```

### High Accuracy Target
```bash
./shell/run_autonomous_pipeline.sh \
  -i data/products.csv \
  -t 0.95 \
  -m 5 \
  -v
```

### Test Run (Limited)
```bash
./shell/run_autonomous_pipeline.sh \
  -i data/products.csv \
  -l 100 \
  -v
```

### Rule-Based Only
```bash
./shell/run_autonomous_pipeline.sh \
  -i data/products.csv \
  --no-ai
```

### Custom Output Directory
```bash
./shell/run_autonomous_pipeline.sh \
  -i data/products.csv \
  -o /workspace/results/run_$(date +%Y%m%d_%H%M%S)
```

## Integration with Existing Workflows

### After Product Scraping
```bash
# 1. Run product scraper
cd ../product-scraper
python main.py --urls urls.txt --output products.csv

# 2. Run autonomous tagger
cd ../vape-product-tagger
./shell/run_autonomous_pipeline.sh -i ../product-scraper/output/products.csv

# 3. Import clean products to Shopify
# Use output/autonomous/*_tagged_clean.csv
```

### Training Data Export
```bash
# After autonomous pipeline completes
python scripts/prepare_training_data.py \
  --audit-db output/autonomous/audit_iteration_0.db \
  --output training_data.jsonl \
  --min-confidence 0.8
```

### Review Interface
```bash
# For products needing manual review
python scripts/review_interface.py \
  --audit-db output/autonomous/audit_iteration_0.db \
  --csv output/autonomous/*_tagged_review.csv
```

## API / Programmatic Usage

```python
from pathlib import Path
from scripts.autonomous_pipeline import AutonomousPipeline

# Initialize pipeline
pipeline = AutonomousPipeline(
    config_path='config.env',
    verbose=True
)

# Set parameters
pipeline.accuracy_target = 0.92
pipeline.max_iterations = 5

# Initialize components
use_ai = pipeline.initialize(use_ai=True)

# Run autonomous tagging
exit_code = pipeline.run_autonomous(
    input_csv=Path('data/products.csv'),
    output_dir=Path('output/custom'),
    use_ai=use_ai,
    limit=None  # Process all products
)

if exit_code == 0:
    print("✅ Target accuracy achieved!")
else:
    print("⚠️ Target not met, but results available")
```

## Next Steps

1. **Run Initial Test**: Test with 100 products using `-l 100`
2. **Review Output**: Check the 3-tier CSV files
3. **Adjust Config**: Tune performance and accuracy settings
4. **Full Run**: Process complete dataset
5. **Import to Shopify**: Use `*_tagged_clean.csv`
6. **Manual Review**: Process `*_tagged_review.csv` products
7. **Training Export**: Generate training data for model fine-tuning

## Support

For issues or questions:
1. Check logs in `logs/autonomous_pipeline_*.log`
2. Review audit DB with SQLite queries
3. Test with limited dataset (`-l 100`) to isolate issues
4. Enable verbose logging (`-v`)
5. Check Ollama service status

---

**Version**: 1.0.0  
**Last Updated**: December 2024  
**Compatibility**: Python 3.10+, Ollama 0.1.0+
