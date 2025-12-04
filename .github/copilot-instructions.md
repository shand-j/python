# Python Projects Monorepo - AI Coding Instructions

## Project Overview
This is a Python monorepo focused on e-commerce data processing. The primary project is a comprehensive product scraper in `product-scraper/` that extracts product data from websites and prepares it for Shopify import.

## Architecture Patterns

### Modular Component Design
The product scraper follows a modular pipeline architecture with clear separation of concerns:
- `modules/scraper.py` - Web scraping with retry logic and user agent rotation
- `modules/image_processor.py` - Image downloading, resizing, and optimization
- `modules/gpt_processor.py` - AI-powered description enhancement and tag generation
- `modules/shopify_exporter.py` - Data transformation to Shopify CSV format
- `modules/product_scraper.py` - Main orchestrator coordinating all components

### Configuration Management
Configuration uses environment variables loaded via `python-dotenv`:
- Default config in `config.env.example` 
- Override with custom config files using `--config` flag
- Config class in `modules/config.py` provides typed access to all settings

### Error Handling & Resilience
- Uses `tenacity` for retry logic with exponential backoff on network requests
- Comprehensive logging with `colorlog` for visual debugging
- Graceful degradation when optional features (GPT, images) fail

## Development Workflows

### Environment Setup
Each project uses isolated virtual environments:
```bash
cd product-scraper/
./setup.sh  # Creates venv, installs deps, generates config
source venv/bin/activate
```

### Running & Testing
- `python main.py --help` shows all CLI options with examples
- `python demo.py` runs sample scraping scenarios
- `python test_parsing.py` tests parsing logic on sample HTML

### Adding New Scrapers
When extending scraping capabilities:
1. Add site-specific parsing logic to `WebScraper.extract_product_data()`
2. Use CSS selectors and fallback chains for robustness
3. Follow the metadata extraction pattern (title, description, price, images, breadcrumbs)

## Key Conventions

### Data Flow Pattern
Products flow through a consistent pipeline:
1. URL → Raw HTML (WebScraper)
2. HTML → Structured metadata (WebScraper.extract_product_data)
3. Metadata → Enhanced product object (ProductScraper.scrape_product)
4. Product object → Export format (ShopifyExporter)

### Import Structure
All modules use relative imports from `modules/__init__.py`:
```python
from modules import Config, setup_logger, ProductScraper
```

### File Organization
- `output/` - Generated CSV/JSON exports
- `images/` - Downloaded and processed product images
- `logs/` - Application logs with timestamps
- `urls.txt` - Batch processing input (one URL per line)

## Integration Points

### OpenAI API Integration
GPT processing requires `OPENAI_API_KEY` in config:
- Description enhancement adds marketing copy and formatting
- Tag generation creates relevant product categories
- Gracefully disabled if API key missing

### Shopify CSV Format
Export matches Shopify product import schema:
- Maps enhanced descriptions to Shopify fields
- Handles variant data and image URLs
- Supports both single products and bulk import

### Cross-Platform Compatibility
Setup scripts for both Unix (`setup.sh`) and Windows (`setup.bat`)
- Automatic virtual environment creation
- Dependency installation with error handling
- Config file generation from templates

When working on this codebase, prioritize the modular architecture and robust error handling patterns established in the existing components.

---

## Vape Product Tagger Project

The `vape-product-tagger/` project is an AI-powered product tagging system for Shopify vaping/CBD products with a complete training pipeline.

### Architecture

**Core Components:**
- `main.py` - Main tagger with rule-based + AI tagging via Ollama or HF Hub
- `tag_audit_db.py` - SQLite audit database capturing all tagging decisions
- `tag_auditor.py` - Audit analysis and training data export
- `train_tag_model.py` - QLoRA fine-tuning pipeline for Vast.ai GPU training
- `approved_tags.json` - Controlled vocabulary with range-based validation

**Model Backends:**
- `ollama` (default) - Local inference via Ollama
- `huggingface` - HF Hub models with LoRA adapters

### Training Pipeline (Vast.ai + HF Hub)

**Stack:** PyTorch + Transformers + PEFT (QLoRA) + TRL (SFTTrainer)

**Workflow:**
1. Run tagger with `--audit-db` to capture decisions + AI prompts/outputs
2. Export training data: `python tag_auditor.py --output training.csv`
3. Train on Vast.ai: `python train_tag_model.py --train --push-to-hub`
4. Inference pulls LoRA adapters from HF Hub

**Key Config (config.env):**
```bash
# Model
BASE_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
MODEL_BACKEND=ollama  # or huggingface

# HF Hub
HF_TOKEN=hf_xxx
HF_REPO_ID=username/vape-tagger-lora

# QLoRA
QUANTIZATION_BITS=4
LORA_R=64
LORA_ALPHA=128
```

### Vast.ai Template

Custom training template in `vastai/`:
- `Dockerfile` - PyTorch 2.1 + CUDA 12.1 + training stack
- `template.json` - Vast.ai marketplace config (24GB+ VRAM)

### Data Flow

```
Products CSV → Tagger (rule+AI) → Audit DB → Training Export
                                      ↓
                              Vast.ai QLoRA Training
                                      ↓
                              HF Hub (LoRA adapters)
                                      ↓
                              Production Inference
```

### Key Patterns

- **Range-based validation** for nicotine_strength (0-20mg) and cbd_strength (0-50000mg)
- **Confidence scoring** with varied examples to prevent model always outputting 0.95
- **Category-aware prompting** with domain-specific examples (CBD, e-liquid, pod)
- **80/20 train/val split** stratified by category for optimal accuracy tracking