# Quick Start Guide - Vape Product Tagger

Get started with the Vape Product Tagger in 5 minutes!

## Prerequisites

- Python 3.8 or higher installed
- A Shopify product export CSV file
- (Optional) Ollama installed for AI-powered tagging

## Step 1: Setup (2 minutes)

### Automated Setup

**Linux/Mac**:
```bash
cd vape-product-tagger
chmod +x setup.sh
./setup.sh
```

**Windows**:
```bash
cd vape-product-tagger
setup.bat
```

This will:
- Create a virtual environment
- Install all dependencies
- Create configuration file
- Set up necessary directories

## Step 2: Activate Virtual Environment (30 seconds)

**Linux/Mac**:
```bash
source venv/bin/activate
```

**Windows**:
```bash
venv\Scripts\activate.bat
```

## Step 3: Configure (1 minute)

Edit `config.env` with your preferences:

```env
# For AI-powered tagging (optional)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
ENABLE_AI_TAGGING=true

# For rule-based only (faster, no AI required)
ENABLE_AI_TAGGING=false
```

Save the file.

## Step 4: Run (1 minute)

### Basic Usage (Rule-Based Tagging)

```bash
python main.py --input your_products.csv
```

This will:
- Import products from your CSV
- Apply intelligent rule-based tagging
- Export enhanced CSV to `output/` directory

### With AI Enhancement

**First, start Ollama** (in another terminal):
```bash
ollama serve
```

**Then run**:
```bash
python main.py --input your_products.csv
```

### Generate Collections

```bash
python main.py --input your_products.csv --collections
```

This creates:
- Enhanced product CSV in `output/`
- Collections JSON in `output/`

## Step 5: Review Results (30 seconds)

Check the `output/` directory for:
- `shopify_tagged_products_[timestamp].csv` - Import this into Shopify
- `collections_[timestamp].json` - Collection definitions (if using --collections)

Check the `logs/` directory for processing details.

## Quick Examples

### Example 1: Fast Rule-Based Tagging
```bash
python main.py --input products.csv --no-ai
```

### Example 2: AI-Enhanced with Collections
```bash
python main.py --input products.csv --collections --verbose
```

### Example 3: Export to JSON
```bash
python main.py --input products.csv --format json
```

## What Gets Tagged?

The tagger automatically identifies and tags:

### Device Information
- Type: Disposable, Pod System, Mod, etc.
- Form: Pen Style, Box Mod, Compact, etc.

### Flavors
- Main Families: Fruit, Dessert, Menthol, Tobacco, Beverage
- Sub-categories: Berry, Tropical, Custard, Cool, etc.
- Specific flavors: Strawberry, Mango, Vanilla, etc.

### Nicotine
- Strength: 0mg, Low (3-6mg), Medium (9-12mg), High (18mg+)
- Type: Freebase, Salt Nicotine

### Compliance
- Age restrictions (18+)
- Regional compliance (US, EU)
- Nicotine warnings
- Shipping restrictions

## Sample Product Tagging

**Input**: "Tropical Mango Ice Disposable Vape 0mg"

**Output Tags**:
- Disposable, Single Use, Vape
- Fruit, Tropical, Mango
- Ice, Cool, Cooling Effect
- 0mg, Zero Nicotine, No Nicotine
- Compact, Disposable
- 18+, Age Restricted, US Compliant

## Troubleshooting

### "Module not found" error
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate.bat on Windows
```

### "Ollama service not available"
```bash
# Either start Ollama
ollama serve

# Or disable AI tagging
python main.py --input products.csv --no-ai
```

### "Input file not found"
```bash
# Check file path is correct
ls your_products.csv  # Linux/Mac
dir your_products.csv  # Windows
```

## Next Steps

1. **Review Generated Tags**: Open the output CSV and review the Tags column
2. **Customize Taxonomy**: Edit `modules/taxonomy.py` to add your specific keywords
3. **Fine-tune AI**: Adjust `AI_CONFIDENCE_THRESHOLD` in config.env
4. **Import to Shopify**: Use the generated CSV to update your Shopify store
5. **Create Collections**: Use the collections JSON to organize your products

## Getting Help

```bash
# View all command options
python main.py --help

# Run with verbose logging
python main.py --input products.csv --verbose

# Check the logs
cat logs/vape-tagger_*.log
```

## Pro Tips

1. **Start Small**: Test with a subset of products first
2. **Use Caching**: Enable `CACHE_AI_TAGS=true` for faster repeated processing
3. **Parallel Processing**: Enable for large catalogs (1000+ products)
4. **Review Before Import**: Always review tags before importing to Shopify
5. **Customize Taxonomy**: Add your own keywords and categories in `modules/taxonomy.py`

## That's It!

You're now ready to tag your vaping product catalog. For more details, see:
- [README.md](README.md) - Complete documentation
- [TAXONOMY.md](TAXONOMY.md) - Full taxonomy reference
- `config.env.example` - All configuration options
