# Vape Product Tagger Pipeline Documentation

Complete guide to the refactored vape product tagging pipeline with automated AI cascade, validation, and recovery.

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Pipeline Components](#pipeline-components)
- [Local Execution](#local-execution)
- [Configuration](#configuration)
- [Tag Schema](#tag-schema)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

1. **Python 3.8+** installed
2. **Ollama** running locally (`ollama serve`)
3. **Required models** pulled:
   ```bash
   ollama pull mistral:latest
   ollama pull gpt-oss:latest
   ollama pull llama3.1:latest
   ```

### Installation

```bash
cd vape-product-tagger
pip install -r requirements.txt
cp config.env.example config.env
# Edit config.env with your settings
```

### Basic Usage

**Tag products from CSV:**
```bash
python scripts/1_main.py \
  --input products.csv \
  --output output/tagged_products.csv \
  --audit-db output/audit.db
```

**Run integration tests:**
```bash
python tests/test_refactored_tagger.py
```

---

## Architecture Overview

The refactored pipeline implements a **6-step intelligent tagging workflow**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. Category Detection                        │
│  Analyzes product title/description to identify primary        │
│  category (e-liquid, CBD, device, pod, tank, etc.)             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                2. Rule-Based Tagging                            │
│  Applies category-specific tagging methods:                    │
│  • Device: style, power_supply, vaping_style                   │
│  • E-liquid: bottle_size, vg_ratio, flavors, nicotine          │
│  • CBD: strength, form, type (3-dimension validation)          │
│  • Pod: pod_type, capacity                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   3. AI Cascade (Optional)                      │
│  Multi-model fallback with confidence-based cascading:         │
│  1st: mistral:latest (primary)                                 │
│  2nd: gpt-oss:latest (if confidence < 0.7)                     │
│  3rd: llama3.1:latest (last resort)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     4. Tag Validation                           │
│  Validates all tags against approved_tags.json:                │
│  • Checks tag exists in approved vocabulary                    │
│  • Validates applies_to rules (category restrictions)          │
│  • CBD 3-dimension validation (strength + form + type)         │
│  • Nicotine strength max 20mg enforcement                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              5. Third Opinion Recovery (If Failed)              │
│  AI-powered recovery for failed validation:                    │
│  • Category-specific recovery prompts                          │
│  • Analyzes failure reasons and suggests corrections           │
│  • Always flags for manual review (recovery = uncertain)       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    6. Final Output                              │
│  Enhanced product with comprehensive metadata:                 │
│  • final_tags: Validated tags for Shopify                      │
│  • needs_manual_review: Flag for human review                  │
│  • confidence_scores: AI confidence metrics                    │
│  • model_used: Which AI model(s) were used                     │
│  • tag_breakdown: Rule vs AI vs secondary flavors              │
│  • failure_reasons: Validation failure details                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Components

### 1. **ProductTagger** (`modules/product_tagger.py`)

Main orchestrator coordinating all tagging methods.

**Key Methods:**
- `tag_category(product)` - Detect product category
- `tag_device_style(product, category)` - Device style tagging
- `tag_bottle_size(product, category)` - E-liquid bottle sizes
- `tag_nicotine_strength(product, category)` - Nicotine 0-20mg
- `tag_cbd_strength(product, category)` - CBD 0-50000mg
- `tag_flavors(product, category)` - Primary + secondary flavors
- `tag_product(product, use_ai=True)` - **Main entry point**

**Applies To Rules:**
Each tagging method validates that tags only apply to appropriate categories. Example:
- `bottle_size` only for `e-liquid`
- `device_style` only for `device` or `pod_system`
- `cbd_form` only for `CBD`

### 2. **AICascade** (`modules/ai_cascade.py`)

Multi-model AI fallback system.

**Cascade Logic:**
```python
confidence_threshold = 0.7

if primary_model.confidence >= threshold:
    return primary_result
elif secondary_model.confidence >= threshold:
    return secondary_result
else:
    return tertiary_result (flagged for review)
```

**Category-Aware Prompting:**
- **CBD Products**: Enforces 3-dimension requirement (strength, form, type)
- **Nicotine Products**: Warns about 20mg max, includes VG/PG ratio
- **Devices**: Focuses on style, power supply, vaping style

### 3. **TagValidator** (`modules/tag_validator.py`)

Validates tags against `approved_tags.json` schema.

**Validation Rules:**
- Tag must exist in approved vocabulary
- Tag must apply to product category (`applies_to` check)
- CBD products require all 3 dimensions (strength, form, type)
- Nicotine strength max 20mg (illegal if >20mg)
- VG/PG ratio must sum to 100

**Example:**
```python
validator = TagValidator()
is_valid, failures = validator.validate_all_tags(
    tags=['50ml', 'fruity', 'rechargeable'],  # rechargeable invalid for e-liquid
    category='e-liquid'
)
# is_valid = False
# failures = ["Tag 'rechargeable' does not apply to category 'e-liquid'"]
```

### 4. **ThirdOpinionRecovery** (`modules/third_opinion.py`)

AI-powered recovery for failed validation.

**Recovery Process:**
1. Analyzes original product data
2. Reviews suggested tags (rule + AI)
3. Examines validation failures
4. Generates corrected tags using tertiary model
5. **Always** flags for manual review (recovery = uncertain)

**When It Activates:**
- Validation fails (invalid tags or missing CBD dimensions)
- AI cascade returned low confidence
- Category detection unclear

### 5. **ShopifyHandler** (`modules/shopify_handler.py`)

Exports products to Shopify-compatible CSV format.

**3-Tier Export System:**
```python
handler.export_to_csv_three_tier(products, output_dir='output/')
```

Generates 3 files:
1. **`{timestamp}_tagged_clean.csv`** - Ready for Shopify import
   - Successfully tagged
   - Passed validation
   - No manual review needed

2. **`{timestamp}_tagged_review.csv`** - Needs human review
   - Tagged but low confidence
   - Failed validation with recovery
   - Ambiguous categories

3. **`{timestamp}_untagged.csv`** - Failed completely
   - No tags generated
   - Validation failed without recovery
   - Category not detected

**Additional Metadata Columns:**
- `Needs Manual Review` - YES/NO
- `AI Confidence` - 0.00-1.00
- `Model Used` - Which AI model(s) were used
- `Failure Reasons` - Semicolon-separated failures
- `Secondary Flavors` - Opportunistically detected flavors
- `Category` - Detected product category
- `Rule Based Tags` - Tags from rule-based system
- `AI Suggested Tags` - Tags from AI cascade

### 6. **TagAuditDB** (`scripts/tag_audit_db.py`)

SQLite database for tracking all tagging decisions.

**Schema:**
```sql
-- Tracks tagging runs
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT,
    completed_at TEXT,
    config TEXT
);

-- Tracks individual products
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    run_id TEXT,
    handle TEXT,
    title TEXT,
    category TEXT,
    final_tags TEXT,  -- JSON array
    rule_based_tags TEXT,  -- JSON array
    ai_suggested_tags TEXT,  -- JSON array
    secondary_flavor_tags TEXT,  -- JSON array
    needs_manual_review INTEGER,
    ai_confidence REAL,
    model_used TEXT,
    failure_reasons TEXT,  -- JSON array
    processed_at TEXT
);
```

**Usage:**
```python
from scripts.tag_audit_db import TagAuditDB

db = TagAuditDB('output/audit.db')
run_id = db.start_run(config={'use_ai': True})

# Save tagged product
db.save_product_tagging(run_id, enhanced_product)

db.complete_run(run_id)
```

---

## Local Execution

### Step-by-Step Guide

**1. Setup Environment:**
```bash
cd vape-product-tagger
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Configure:**
```bash
cp config.env.example config.env
nano config.env  # Edit configuration
```

Key settings:
```bash
# AI Cascade Models
PRIMARY_AI_MODEL=mistral:latest
SECONDARY_AI_MODEL=gpt-oss:latest
TERTIARY_AI_MODEL=llama3.1:latest

# Confidence threshold for cascade
AI_CONFIDENCE_THRESHOLD=0.7

# Enable third opinion recovery
ENABLE_THIRD_OPINION=true

# Pipeline settings
PIPELINE_MODE=local
AUTO_REVIEW_INTERFACE=false
```

**3. Ensure Ollama is Running:**
```bash
# Start Ollama service
ollama serve

# Pull required models (in separate terminal)
ollama pull mistral:latest
ollama pull gpt-oss:latest
ollama pull llama3.1:latest
```

**4. Run Tagging Pipeline:**
```bash
python scripts/1_main.py \
  --input sample_data/products.csv \
  --output output/tagged_products.csv \
  --audit-db output/audit.db \
  --limit 100
```

**5. Review Output:**
Three CSV files generated:
- `output/{timestamp}_tagged_clean.csv` - Import to Shopify
- `output/{timestamp}_tagged_review.csv` - Review before import
- `output/{timestamp}_untagged.csv` - Manual tagging needed

**6. Check Audit Database:**
```bash
python scripts/tag_audit_db.py output/audit.db --stats
```

Shows:
- Total products processed
- Clean/review/untagged breakdown
- Model usage statistics
- Confidence distribution

---

## Configuration

### Essential Settings

**AI Cascade:**
```bash
PRIMARY_AI_MODEL=mistral:latest     # Fastest, good quality
SECONDARY_AI_MODEL=gpt-oss:latest   # Balanced
TERTIARY_AI_MODEL=llama3.1:latest   # Most capable, slowest
AI_CONFIDENCE_THRESHOLD=0.7         # 0.7-0.8 recommended
ENABLE_THIRD_OPINION=true           # Enable recovery
```

**Performance:**
```bash
BATCH_SIZE=8                # Products per batch
MAX_WORKERS=6               # Parallel workers
PARALLEL_PROCESSING=true    # Enable parallelism
```

**Output:**
```bash
OUTPUT_DIR=./output         # Export directory
LOGS_DIR=./logs             # Log files
CACHE_DIR=./cache           # AI tag cache
```

### Advanced Settings

**Ollama Tuning:**
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=180          # Request timeout (seconds)
OLLAMA_NUM_PARALLEL=6       # Concurrent Ollama requests
OLLAMA_KEEP_ALIVE=5m        # Model warm-up duration
```

**Pipeline Automation:**
```bash
PIPELINE_MODE=local                 # local or vastai
AUTO_REVIEW_INTERFACE=false         # Launch review UI after tagging
TRAINING_DATA_AUTO_EXPORT=true      # Auto-export for fine-tuning
```

---

## Tag Schema

### Approved Tags (`approved_tags.json`)

**Categories:**
```json
["e-liquid", "nicotine_pouches", "disposable", "device", "pod_system", 
 "box_mod", "tank", "coil", "accessory", "pod", "CBD"]
```

**Tag Dimensions with Applies To Rules:**

| Dimension | Applies To | Example Tags |
|-----------|------------|--------------|
| `capacity` | tank, pod | 2ml, 5ml, 10ml |
| `bottle_size` | e-liquid | 10ml, 50ml, shortfill |
| `device_style` | device, pod_system | pen_style, pod_style, compact |
| `nicotine_strength` | e-liquid, disposable, device, pod_system | 0mg, 3mg, 6mg, 12mg, 18mg, 20mg |
| `cbd_strength` | CBD | 0mg-50000mg range |
| `flavour_type` | e-liquid, disposable, nicotine_pouches, pod | fruity, ice, tobacco, desserts/bakery |
| `nicotine_type` | e-liquid, disposable, device, pod_system | nic_salt, freebase_nicotine |
| `vg_ratio` | e-liquid | 50/50, 70/30, 80/20 |
| `cbd_form` | CBD | tincture, oil, gummy, capsule |
| `cbd_type` | CBD | full_spectrum, broad_spectrum, isolate |
| `power_supply` | device, pod_system | rechargeable, removable_battery |
| `vaping_style` | device, pod_system, e-liquid | mouth-to-lung, direct-to-lung |
| `pod_type` | pod | prefilled_pod, replacement_pod |

**CBD 3-Dimension Requirement:**
Every CBD product MUST have:
1. `cbd_strength` (e.g., 1000mg)
2. `cbd_form` (e.g., gummy)
3. `cbd_type` (e.g., full_spectrum)

**Nicotine Limits:**
- Max: 20mg (anything >20mg is illegal and flagged)
- Common values: 0mg, 3mg, 6mg, 12mg, 18mg, 20mg

---

## Troubleshooting

### Common Issues

**1. "requests library not available"**
```bash
pip install requests
```

**2. "Ollama connection refused"**
```bash
# Start Ollama service
ollama serve

# Check if running
curl http://localhost:11434/api/version
```

**3. "Model not found: mistral:latest"**
```bash
# Pull all required models
ollama pull mistral:latest
ollama pull gpt-oss:latest
ollama pull llama3.1:latest
```

**4. "approved_tags.json not found"**
```bash
# Ensure you're in the vape-product-tagger directory
cd vape-product-tagger
ls approved_tags.json  # Should exist
```

**5. Low AI confidence scores**
- Increase `OLLAMA_TIMEOUT` to 300+ seconds
- Use more capable primary model: `PRIMARY_AI_MODEL=llama3.1:latest`
- Lower `AI_CONFIDENCE_THRESHOLD` to 0.6 (be cautious)

**6. High manual review rate**
- Review `failure_reasons` in `*_tagged_review.csv`
- Common causes:
  - CBD products missing 1+ dimensions → Improve descriptions
  - Nicotine >20mg detected → Verify product data accuracy
  - Category not detected → Add clearer category keywords

**7. Performance issues**
- Reduce `MAX_WORKERS` if CPU-bound
- Reduce `BATCH_SIZE` if memory-limited
- Enable caching: `CACHE_AI_TAGS=true`
- Use faster primary model: `PRIMARY_AI_MODEL=mistral:latest`

### Debug Mode

Enable verbose logging:
```bash
# In config.env
LOG_LEVEL=DEBUG
VERBOSE_LOGGING=true
```

Run integration tests:
```bash
python tests/test_refactored_tagger.py
```

Check audit database:
```bash
python scripts/tag_audit_db.py output/audit.db --stats
```

---

## Pipeline Architecture Diagram

```
                    Input CSV
                        │
                        ▼
        ┌───────────────────────────┐
        │   ProductTagger           │
        │   ┌─────────────────────┐ │
        │   │ 1. Category         │ │
        │   │    Detection        │ │
        │   └──────────┬──────────┘ │
        │              ▼            │
        │   ┌─────────────────────┐ │
        │   │ 2. Rule-Based       │ │
        │   │    Tagging          │ │
        │   └──────────┬──────────┘ │
        │              ▼            │
        │   ┌─────────────────────┐ │
        │   │ 3. AI Cascade       │◄├─── Ollama Models
        │   │    (Optional)       │ │
        │   └──────────┬──────────┘ │
        │              ▼            │
        │   ┌─────────────────────┐ │
        │   │ 4. TagValidator     │◄├─── approved_tags.json
        │   └──────────┬──────────┘ │
        │              ▼            │
        │   ┌─────────────────────┐ │
        │   │ 5. Third Opinion    │ │
        │   │    Recovery (If     │ │
        │   │    Failed)          │ │
        │   └──────────┬──────────┘ │
        │              ▼            │
        │   ┌─────────────────────┐ │
        │   │ 6. Final Output     │ │
        │   └──────────┬──────────┘ │
        └──────────────┼────────────┘
                       │
           ┌───────────┼───────────┐
           │           │           │
           ▼           ▼           ▼
      TagAuditDB  ShopifyHandler  Cache
           │           │
           │           ├─── clean.csv
           │           ├─── review.csv
           │           └─── untagged.csv
           │
           └─── audit.db (SQLite)
```

---

## Next Steps

1. **Run Integration Tests**: Verify all components work
   ```bash
   python tests/test_refactored_tagger.py
   ```

2. **Tag Sample Data**: Test with your products
   ```bash
   python scripts/1_main.py --input your_products.csv --output output/
   ```

3. **Review Outputs**: Check the 3-tier CSV files

4. **Adjust Configuration**: Tune based on results

5. **Import to Shopify**: Use `*_tagged_clean.csv`

6. **Manual Review**: Process `*_tagged_review.csv`

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review [Configuration](#configuration) settings
3. Run integration tests for diagnostics
4. Check audit database for detailed failure reasons

---

**Version**: 2.0.0 (Refactored Pipeline)  
**Last Updated**: December 2024
