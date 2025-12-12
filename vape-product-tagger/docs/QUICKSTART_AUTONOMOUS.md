# Quick Start: Autonomous AI Tagging Pipeline

This guide gets you running the autonomous tagging pipeline in under 10 minutes.

## What You'll Get

- **Self-improving product tagging** that achieves 90%+ accuracy automatically
- **3-tier output**: Clean products for Shopify, products needing review, and failed products
- **Complete audit trail** in SQLite for analysis and training data export
- **Vast.ai ready** for GPU-accelerated processing

## Prerequisites

- Python 3.10+ 
- Ollama (optional, for AI tagging)
- 5 minutes

## Setup

### Option 1: Local Development

```bash
# Clone and setup
git clone https://github.com/shand-j/python.git
cd python/vape-product-tagger

# Install dependencies
pip install -r requirements.txt

# Create config
cp config.env.example config.env

# (Optional) Start Ollama for AI tagging
ollama serve &
ollama pull mistral:latest
ollama pull gpt-oss:latest
ollama pull llama3.1:latest
```

### Option 2: Vast.ai (Recommended for Production)

```bash
# SSH into your Vast.ai instance
ssh -p <port> root@<vast-ip>

# Clone and auto-deploy
git clone https://github.com/shand-j/python.git
cd python/vape-product-tagger
./vastai/deploy_autonomous.sh

# That's it! Everything is configured automatically.
```

## Your First Run

### Test with Sample Data (Recommended)

```bash
# Create sample CSV
cat > test_products.csv << 'EOF'
Handle,Title,Body (HTML),Vendor,Type,Tags
cbd-1000mg,CBD Gummies 1000mg Full Spectrum,Premium CBD gummies,TestVendor,CBD products,
eliquid-50ml,Strawberry Ice 50ml Shortfill 70/30,Delicious e-liquid,TestVendor,E-Liquid,
disposable-20mg,Blue Razz 600 Puff Disposable 20mg,Disposable vape,TestVendor,Vaping,
pod-system,Compact Pod System Kit,Rechargeable pod system,TestVendor,Vaping,
EOF

# Run autonomous pipeline
./shell/run_autonomous_pipeline.sh -i test_products.csv -v

# Check results
ls -lh output/autonomous/
```

You should see:
- `*_tagged_clean.csv` - 3-4 products ready for Shopify
- `*_tagged_review.csv` - 0-1 products needing review
- `audit_*.db` - Complete audit trail

### Run with Your Products

```bash
# Upload your Shopify export
./shell/run_autonomous_pipeline.sh -i your_products.csv -v

# Or with custom settings
./shell/run_autonomous_pipeline.sh \
  -i your_products.csv \
  -t 0.92 \              # 92% accuracy target
  -m 5 \                 # Max 5 improvement iterations
  -v                     # Verbose logging
```

## Understanding the Output

### Clean Products (`*_tagged_clean.csv`)
✅ Ready to import directly to Shopify
- All tags validated against approved vocabulary
- High confidence (>70%)
- No manual review needed

**Action**: Import to Shopify immediately

### Review Products (`*_tagged_review.csv`)
⚠️ Need human review before import
- Tags present but low confidence OR
- Failed validation with AI recovery OR
- Ambiguous category detection

**Action**: Review manually, correct tags, then import

### Untagged Products (`*_untagged.csv`)
❌ Failed all tagging attempts
- No valid tags could be generated
- Category couldn't be detected
- Product description insufficient

**Action**: Improve product descriptions or add manual tags

## Common Use Cases

### 1. Quick Test (10 products)
```bash
./shell/run_autonomous_pipeline.sh -i products.csv -l 10 -v
```

### 2. High Accuracy Production Run
```bash
./shell/run_autonomous_pipeline.sh \
  -i products.csv \
  -t 0.95 \
  -m 10 \
  -v
```

### 3. Rule-Based Only (No AI, Very Fast)
```bash
./shell/run_autonomous_pipeline.sh -i products.csv --no-ai
```

### 4. Custom Output Location
```bash
./shell/run_autonomous_pipeline.sh \
  -i products.csv \
  -o /workspace/results_$(date +%Y%m%d)
```

## Monitoring Progress

### Real-Time Logs
```bash
# Watch pipeline progress
tail -f logs/autonomous_pipeline_*.log

# Check Ollama (if using AI)
tail -f /tmp/ollama.log

# GPU utilization (Vast.ai)
watch -n 1 nvidia-smi
```

### Audit Database Queries
```bash
# Check accuracy by category
sqlite3 output/autonomous/audit_iteration_0.db << 'EOF'
SELECT 
  category,
  COUNT(*) as total,
  SUM(CASE WHEN needs_manual_review = 0 THEN 1 ELSE 0 END) as clean
FROM products
GROUP BY category;
EOF

# Find low-confidence products
sqlite3 output/autonomous/audit_iteration_0.db << 'EOF'
SELECT handle, title, primary_model_confidence
FROM products
WHERE primary_model_confidence < 0.7
ORDER BY primary_model_confidence
LIMIT 10;
EOF
```

## Vast.ai Workflow

### Complete Remote Pipeline

```bash
# On local machine: Upload data
scp -P <port> products.csv root@<vast-ip>:/workspace/python/vape-product-tagger/data/

# On Vast.ai: Run pipeline
ssh -p <port> root@<vast-ip>
cd /workspace/python/vape-product-tagger
./shell/run_autonomous_pipeline.sh -i data/products.csv -v

# On local machine: Download results
scp -r -P <port> root@<vast-ip>:/workspace/python/vape-product-tagger/output/autonomous/ ./results/
```

### Automated Vast.ai Script

Save this as `run_on_vast.sh`:
```bash
#!/bin/bash
VAST_PORT=12345
VAST_IP=your.vast.instance.ip
INPUT_CSV=products.csv

# Upload
scp -P $VAST_PORT $INPUT_CSV root@$VAST_IP:/workspace/python/vape-product-tagger/data/

# Run
ssh -p $VAST_PORT root@$VAST_IP << 'ENDSSH'
cd /workspace/python/vape-product-tagger
./shell/run_autonomous_pipeline.sh -i data/products.csv -v
ENDSSH

# Download
mkdir -p results_$(date +%Y%m%d)
scp -r -P $VAST_PORT root@$VAST_IP:/workspace/python/vape-product-tagger/output/autonomous/ ./results_$(date +%Y%m%d)/

echo "✅ Results saved to results_$(date +%Y%m%d)/"
```

## Performance Expectations

### Rule-Based Only (--no-ai)
- **Speed**: 200-500 products/second
- **Accuracy**: 60-70%
- **Use case**: Quick initial pass or very large datasets

### With AI (default)
- **Speed**: 30-60 products/minute (CPU) or 100-200/min (GPU)
- **Accuracy**: 85-95%
- **Use case**: Production tagging for Shopify

### Iterations
- **Iteration 0**: Initial tagging (all products)
- **Iteration 1-N**: Only review products with issues
- **Typical**: 90%+ accuracy achieved by iteration 2

## Troubleshooting

### "Ollama connection refused"
```bash
# Start Ollama
ollama serve &

# Or run without AI
./shell/run_autonomous_pipeline.sh -i products.csv --no-ai
```

### "Low accuracy" (< 90%)
1. Check which categories have issues:
   ```bash
   sqlite3 output/autonomous/audit_*.db \
     "SELECT category, COUNT(*) FROM products GROUP BY category"
   ```
2. Review failure_reasons in `*_tagged_review.csv`
3. Improve product descriptions in source data
4. Adjust config.env settings

### "Out of memory"
```bash
# In config.env
MAX_WORKERS=4
BATCH_SIZE=4
OLLAMA_NUM_PARALLEL=3
```

### "Too slow"
```bash
# Use rule-based only for initial pass
./shell/run_autonomous_pipeline.sh -i products.csv --no-ai

# Then AI tag only review products
./shell/run_autonomous_pipeline.sh -i output/autonomous/*_review.csv
```

## Next Steps

### 1. Import to Shopify
Use `*_tagged_clean.csv` in Shopify admin:
- Products → Import
- Select the clean CSV
- Map columns (auto-detected)
- Import

### 2. Review Interface
Process products needing review:
```bash
python scripts/review_interface.py \
  --audit-db output/autonomous/audit_iteration_0.db \
  --csv output/autonomous/*_tagged_review.csv
```

### 3. Export Training Data
Generate training data for model fine-tuning:
```bash
python scripts/prepare_training_data.py \
  --audit-db output/autonomous/audit_iteration_0.db \
  --output training_data.jsonl \
  --min-confidence 0.8
```

### 4. Fine-Tune Model (Advanced)
See [Training Pipeline](#training-pipeline) in README.md

## Configuration

Key settings in `config.env`:

```bash
# Accuracy target (0.0-1.0)
AI_CONFIDENCE_THRESHOLD=0.7

# Models (fastest → slowest, least → most accurate)
PRIMARY_AI_MODEL=mistral:latest      # Fast, good
SECONDARY_AI_MODEL=gpt-oss:latest    # Medium, better
TERTIARY_AI_MODEL=llama3.1:latest    # Slow, best

# Performance
MAX_WORKERS=6              # Parallel workers
BATCH_SIZE=8               # Products per batch
OLLAMA_NUM_PARALLEL=6      # Concurrent AI requests

# Features
ENABLE_THIRD_OPINION=true  # Recovery for failed tags
```

## Support

- **Documentation**: [AUTONOMOUS_PIPELINE.md](AUTONOMOUS_PIPELINE.md)
- **Issues**: Review audit DB and logs
- **Performance**: See Performance Optimization in docs
- **Test**: Run `python tests/test_autonomous_pipeline.py`

---

**Time to first results**: 2-5 minutes  
**Typical accuracy**: 85-95%  
**Production ready**: Yes ✅
