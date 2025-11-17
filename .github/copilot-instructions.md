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