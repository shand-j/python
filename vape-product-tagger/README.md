# Vape Product Tagger

An intelligent AI-powered product tagging and navigation data pipeline specifically designed for vaping products in Shopify. This tool uses advanced semantic analysis with Ollama AI and comprehensive rule-based tagging to create a multi-dimensional taxonomy for enhanced product discovery and filtering.

## Features

### Intelligent Tagging System
- **Multi-dimensional Taxonomy**: Comprehensive hierarchical tags covering device types, flavors, nicotine levels, and compliance
- **AI-Powered Semantic Analysis**: Local Ollama integration for advanced flavor inference and tag generation
- **Rule-Based Tagging**: Robust keyword-based tagging as primary or fallback mechanism
- **Confidence Scoring**: AI tag generation with configurable confidence thresholds

### Product Taxonomy Coverage

#### Device Classification
- **Device Types**: Disposable, Rechargeable, Pod System, Mod, AIO (All-in-One)
- **Device Forms**: Pen Style, Box Mod, Stick, Compact

#### Flavor Taxonomy
Hierarchical flavor classification with main families and detailed sub-categories:
- **Fruit**: Citrus, Berry, Tropical, Stone Fruit
- **Dessert**: Custard, Bakery, Cream, Pudding
- **Menthol**: Cool, Mint, Arctic, Herbal Mint
- **Tobacco**: Classic, Sweet, Blend, Dark
- **Beverage**: Coffee, Soda, Cocktail, Tea

#### Nicotine Classification
- **Strength Levels**: Zero (0mg), Low (3-6mg), Medium (9-12mg), High (18mg+)
- **Nicotine Types**: Freebase, Salt Nicotine

#### Compliance & Safety
- Age restriction tags (18+, Adult Only)
- Regional compliance indicators (US Compliant, EU Compliant, TPD Compliant)
- Shipping restriction tags
- Nicotine content warnings

### Shopify Integration
- **CSV Import**: Read existing Shopify product exports
- **CSV Export**: Generate Shopify-compatible import files with enhanced tags
- **JSON Export**: Alternative structured data format
- **Dynamic Collection Generation**: Auto-create collections based on tag patterns
  - Flavor-based collections (Fruit Flavors, Dessert Flavors, etc.)
  - Nicotine-based collections (Zero Nicotine, High Strength, etc.)
  - Device-based collections (Disposables, Beginner Kits, etc.)

### Performance & Scalability
- **Batch Processing**: Configurable batch sizes for large catalogs
- **Parallel Processing**: Multi-threaded tag generation
- **AI Tag Caching**: Cache AI-generated tags to reduce API calls
- **Low Computational Overhead**: Optimized for production environments

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Ollama (optional, for AI-powered tagging)

### Quick Start

1. **Clone or navigate to the project directory**:
```bash
cd vape-product-tagger
```

2. **Run the setup script**:

**Linux/Mac**:
```bash
chmod +x setup.sh
./setup.sh
```

**Windows**:
```bash
setup.bat
```

3. **Activate the virtual environment**:

**Linux/Mac**:
```bash
source venv/bin/activate
```

**Windows**:
```bash
venv\Scripts\activate.bat
```

4. **Configure the application**:
```bash
cp config.env.example config.env
# Edit config.env with your settings
```

### Manual Installation

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp config.env.example config.env
```

## Configuration

Edit `config.env` to customize the application:

### Ollama AI Configuration
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_TIMEOUT=60
ENABLE_AI_TAGGING=true
```

### Processing Configuration
```env
BATCH_SIZE=10
PARALLEL_PROCESSING=true
MAX_WORKERS=4
CACHE_AI_TAGS=true
```

### Shopify Configuration
```env
SHOPIFY_VENDOR=Vape Store
SHOPIFY_PRODUCT_TYPE=Vaping Products
AUTO_PUBLISH=false
AUTO_GENERATE_COLLECTIONS=true
```

### Compliance Configuration
```env
ENABLE_COMPLIANCE_TAGS=true
DEFAULT_AGE_RESTRICTION=18+
REGIONAL_COMPLIANCE=US
```

## Usage

### Basic Usage

Tag products from a Shopify CSV export:
```bash
python main.py --input products.csv
```

### Advanced Usage

**Custom configuration**:
```bash
python main.py --input products.csv --config custom_config.env
```

**Export to JSON format**:
```bash
python main.py --input products.csv --format json
```

**Disable AI tagging (rule-based only)**:
```bash
python main.py --input products.csv --no-ai
```

**Generate dynamic collections**:
```bash
python main.py --input products.csv --collections
```

**Control processing**:
```bash
python main.py --input products.csv --batch-size 20 --no-parallel
```

**Verbose logging**:
```bash
python main.py --input products.csv --verbose
```

### Command Line Options

```
Required:
  --input, -i PATH          Input Shopify CSV file path

Optional:
  --config, -c PATH         Configuration file path
  --output, -o PATH         Output file path (auto-generated if not specified)
  --format, -f FORMAT       Output format: csv or json (default: csv)
  --no-ai                   Disable AI-powered tagging
  --collections             Generate dynamic collections
  --batch-size N            Batch size for processing
  --no-parallel             Disable parallel processing
  --verbose, -v             Enable verbose logging
  --quiet, -q               Quiet mode (minimal output)
```

## Ollama Integration

This application uses Ollama for local AI processing, which provides:
- Privacy-focused local inference (no data sent to external APIs)
- Cost-effective (no API costs)
- Fast semantic analysis
- Customizable AI models

### Setting Up Ollama

1. **Install Ollama**:
Visit [ollama.ai](https://ollama.ai) and follow installation instructions for your OS.

2. **Pull a model**:
```bash
ollama pull llama2
# or
ollama pull mistral
```

3. **Start Ollama service**:
```bash
ollama serve
```

4. **Configure in config.env**:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
ENABLE_AI_TAGGING=true
```

### Fallback Mode

If Ollama is not available, the application automatically falls back to rule-based tagging without errors.

## Output

### CSV Output
Shopify-compatible CSV file with:
- All original product data preserved
- Enhanced comprehensive tags
- Ready for direct import into Shopify

### JSON Output
Structured JSON format containing:
- All product metadata
- Complete tag breakdown by category
- Tag hierarchy and relationships
- AI-enhanced insights

### Collections JSON
When using `--collections` flag, generates a JSON file with collection definitions:
```json
[
  {
    "title": "Fruit Flavors",
    "description": "Explore our fruit flavored vaping products",
    "filter_tags": ["Fruit"]
  }
]
```

## Tagging Examples

### Example 1: Disposable Fruit Vape
**Input Product**: "Tropical Mango Ice Disposable Vape (0mg)"

**Generated Tags**:
- Product Type: Disposable, Single Use, Vape
- Device Form: Compact, Disposable
- Flavor: Fruit, Tropical, Mango, Ice, Cool
- Nicotine: 0mg, Zero Nicotine, No Nicotine
- Compliance: 18+, Age Restricted, US Compliant

### Example 2: Rechargeable Pod System
**Input Product**: "Strawberry Cheesecake Pod System 50mg Salt Nicotine"

**Generated Tags**:
- Product Type: Pod System, Pod, Rechargeable
- Flavor: Dessert, Fruit, Berry, Strawberry, Cream, Bakery
- Nicotine: High Strength, Strong, Nicotine Salt, Smooth
- Compliance: 18+, Contains Nicotine, Nicotine Warning

## Project Structure

```
vape-product-tagger/
├── modules/                    # Core application modules
│   ├── __init__.py            # Module exports
│   ├── config.py              # Configuration management
│   ├── logger.py              # Logging setup
│   ├── taxonomy.py            # Vape product taxonomy definitions
│   ├── ollama_processor.py    # Ollama AI integration
│   ├── product_tagger.py      # Main tagging engine
│   └── shopify_handler.py     # Shopify import/export
├── output/                    # Generated CSV/JSON files
├── logs/                      # Application logs
├── cache/                     # AI tag cache
├── sample_data/              # Sample product data
├── main.py                   # Main application entry point
├── demo.py                   # Demonstration script
├── requirements.txt          # Python dependencies
├── config.env.example        # Configuration template
├── setup.sh                  # Setup script (Linux/Mac)
├── setup.bat                 # Setup script (Windows)
├── README.md                 # This file
├── QUICKSTART.md            # Quick start guide
├── TAXONOMY.md              # Complete taxonomy reference
└── .gitignore               # Git ignore rules
```

## Best Practices

### Data Preparation
- Export your Shopify products to CSV format
- Ensure product titles and descriptions are descriptive
- Include nicotine strength in product information
- Maintain consistent naming conventions

### Performance Optimization
- Enable caching for repeated processing: `CACHE_AI_TAGS=true`
- Use parallel processing for large catalogs: `PARALLEL_PROCESSING=true`
- Adjust batch size based on system resources: `BATCH_SIZE=10`
- Use rule-based tagging first, then enable AI for refinement

### AI Model Selection
- **llama2**: Balanced performance and accuracy
- **mistral**: Faster inference, good for large catalogs
- **llama2:13b**: Higher accuracy, slower inference

### Tag Management
- Review AI-generated tags before bulk import
- Use tag breakdown in JSON export for analysis
- Customize taxonomy in `taxonomy.py` for your specific needs
- Generate collections to improve customer navigation

## Troubleshooting

### Common Issues

**"Ollama service not available"**
- Ensure Ollama is installed and running: `ollama serve`
- Check OLLAMA_BASE_URL in config.env
- Application will fall back to rule-based tagging

**"No tags generated"**
- Verify product titles and descriptions are populated
- Check that keywords in taxonomy.py match your product naming
- Enable verbose logging: `--verbose`

**"Import failed"**
- Ensure CSV is valid Shopify export format
- Check for proper UTF-8 encoding
- Verify column headers match Shopify format

**Performance issues with large catalogs**
- Reduce batch size: `--batch-size 5`
- Disable parallel processing temporarily: `--no-parallel`
- Disable AI tagging for initial testing: `--no-ai`

## Contributing

Contributions are welcome! Areas for enhancement:
- Additional flavor categories and sub-categories
- Support for more regional compliance standards
- Enhanced AI prompts for better tag accuracy
- Multi-language product support
- Integration with other e-commerce platforms

## License

This project is provided as-is for vaping product data processing and Shopify integration.

## Support

For issues and questions:
1. Check the log files in `logs/` directory
2. Review this README and QUICKSTART.md
3. Verify your configuration in `config.env`
4. Run with `--verbose` flag for detailed debugging

## Acknowledgments

- Ollama for local AI inference
- Shopify for e-commerce platform
- Python community for excellent libraries
