# Product Data Scraper for Shopify

A comprehensive Python application for scraping product data from e-commerce websites, enhancing descriptions with AI, and preparing data for Shopify import.

## Features

### Core Functionality
- **Web Scraping**: Extract product data from various e-commerce website structures
  - Product titles and descriptions
  - Specifications and metadata
  - Navigation and collection data
  - Hidden content accessible via metadata
  
- **Image Processing**
  - Download all product images
  - Resize images to configurable dimensions
  - Maintain image quality and aspect ratio
  - Optimized for web performance

- **AI-Powered Enhancement**
  - GPT integration for description enhancement
  - Intelligent tag generation
  - Content summarization
  - SEO optimization

- **Shopify Export**
  - Complete Shopify product import CSV format
  - JSON export option
  - Data integrity validation

- **Brand Management** ✨ NEW
  - Configure and validate brand information
  - Priority-based brand queuing
  - Website accessibility and SSL validation
  - Brand registry with history tracking
  - See [Brand Management Guide](BRAND_MANAGEMENT.md)

- **Media Pack Discovery** ✨ NEW
  - Discover official media packs from brand websites
  - Automatic detection of press kits and resources
  - File type recognition (archives, documents, images)
  - Access restriction handling
  - Alternative domain discovery
  - See [Media Pack Discovery Guide](MEDIA_PACK_DISCOVERY.md)

- **Media Pack Download & Extraction** ✨ NEW
  - Resumable downloads with progress tracking
  - File integrity verification with checksums
  - Automatic archive extraction (ZIP, TAR.GZ)
  - Smart file categorization and organization
  - Duplicate detection and removal
  - See [Download & Extraction Guide](MEDIA_PACK_DOWNLOAD_EXTRACT.md)

- **Competitor Website Configuration** ✨ NEW
  - Configure major UK vape retailer websites
  - Robots.txt compliance checking
  - Site health monitoring with exponential backoff
  - User agent rotation for respectful scraping
  - Configurable scraping parameters
  - See [Competitor Configuration Guide](COMPETITOR_CONFIGURATION.md)

- **Competitor Product Discovery** ✨ NEW
  - Discover products on competitor websites
  - Automatic category navigation with pagination
  - Brand-specific product filtering
  - Product data extraction (title, price, images, stock)
  - Build comprehensive product inventories
  - See [Product Discovery Guide](PRODUCT_DISCOVERY.md)

- **Competitor Image Extraction** ✨ NEW
  - Extract product images from competitor pages
  - Multi-selector discovery (gallery, thumbnails, zoom, carousel)
  - Image quality analysis with scoring (0-100)
  - Lazy loading and srcset support
  - Placeholder/logo filtering
  - Smart downloading with duplicate detection
  - See [Image Extraction Guide](IMAGE_EXTRACTION.md)

### Advanced Features
- **Error Handling**: Robust error handling with detailed logging
- **Rate Limiting**: Configurable delays between requests
- **User Agent Rotation**: Avoid detection and blocking
- **Proxy Support**: Optional proxy configuration for large-scale scraping
- **Retry Logic**: Automatic retry with exponential backoff
- **OS Agnostic**: Compatible with Windows, Mac, and Linux

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
cd product-scraper
```

2. Create a virtual environment:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the application:
```bash
cp config.env.example config.env
```

Edit `config.env` and add your configuration:
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
IMAGE_MAX_WIDTH=1024
IMAGE_MAX_HEIGHT=1024
```

## Usage

### Product Scraping

Scrape a single product:
```bash
python main.py https://example.com/product-page
```

Scrape multiple products:
```bash
python main.py https://example.com/product1 https://example.com/product2
```

Scrape from a file containing URLs:
```bash
python main.py --file urls.txt
```

### Brand Management

Configure and validate brands:
```bash
# Load brands from file
python brand_manager.py load brands.txt

# Validate all brands
python brand_manager.py validate

# Show processing queue (ordered by priority)
python brand_manager.py queue

# List all brands
python brand_manager.py list

# Add new brand
python brand_manager.py add "SMOK" "smoktech.com" --priority high
```

See [Brand Management Guide](BRAND_MANAGEMENT.md) for complete documentation.

### Media Pack Discovery

Discover official media packs from brand websites:
```bash
# Discover media packs for all brands
python brand_manager.py discover-media --save

# Discover for specific brand
python brand_manager.py discover-media --brand "SMOK" --save

# View discovered media packs
python brand_manager.py media-packs

# Filter by file type
python brand_manager.py media-packs --type archive
```

See [Media Pack Discovery Guide](MEDIA_PACK_DISCOVERY.md) for complete documentation.

### Media Pack Download & Extraction

Download and extract media packs:
```bash
# Download media packs for all brands
python brand_manager.py download

# Download for specific brand
python brand_manager.py download --brand "SMOK"

# Download specific URL
python brand_manager.py download --brand "SMOK" --url "https://smoktech.com/media.zip"

# Extract downloaded archives
python brand_manager.py extract

# Extract for specific brand
python brand_manager.py extract --brand "SMOK"

# Extract specific file
python brand_manager.py extract --brand "SMOK" --file "downloads/SMOK/media-packs/pack.zip"
```

See [Download & Extraction Guide](MEDIA_PACK_DOWNLOAD_EXTRACT.md) for complete documentation.

### Competitor Website Configuration

Configure competitor websites for ethical scraping:
```bash
# Load competitor sites from file
python competitor_manager.py load competitor_sites.txt

# Check site health
python competitor_manager.py health

# Check robots.txt compliance
python competitor_manager.py robots --site "Vape UK"

# List all sites
python competitor_manager.py list

# Add new site
python competitor_manager.py add "Site Name" "https://site.com" --priority high

# Analyze site structure
python competitor_manager.py analyze --site "Vape UK"
```

See [Competitor Configuration Guide](COMPETITOR_CONFIGURATION.md) for complete documentation.

### Competitor Product Discovery

Discover and catalog products from competitor websites:
```bash
# Discover products from all active competitor sites
python competitor_manager.py discover --brands brands_registry.json --save

# Discover from specific site with max 20 pages per category
python competitor_manager.py discover --site "Vape UK" --brands brands.txt --max-pages 20 --save

# View all discovered products
python competitor_manager.py products

# Filter by brand
python competitor_manager.py products --brand "SMOK"

# Filter by site and category
python competitor_manager.py products --site "Vape UK" --category "vape-kits"
```

See [Product Discovery Guide](PRODUCT_DISCOVERY.md) for complete documentation.

#### Extract Images from Competitor Products

Extract and download product images with quality analysis:

```bash
# Extract images for a specific brand (analysis only, no download)
python competitor_manager.py extract-images --brand "SMOK"

# Extract and download high-quality images
python competitor_manager.py extract-images --brand "SMOK" --min-quality 70 --save

# Extract from specific site with limits
python competitor_manager.py extract-images \
  --site "Vape UK" \
  --max-products 20 \
  --images-per-product 5 \
  --min-quality 60 \
  --save

# View downloaded images summary
python competitor_manager.py images

# View for specific brand
python competitor_manager.py images --brand "SMOK"
```

See [Image Extraction Guide](IMAGE_EXTRACTION.md) for complete documentation.

### Advanced Usage

Export to JSON instead of CSV:
```bash
python main.py --format json https://example.com/product-page
```

Skip GPT enhancement (faster, no API costs):
```bash
python main.py --no-enhance --no-tags https://example.com/product-page
```

Skip image processing:
```bash
python main.py --no-images https://example.com/product-page
```

Specify custom output file:
```bash
python main.py --output my_products.csv https://example.com/product-page
```

Use custom configuration file:
```bash
python main.py --config custom_config.env https://example.com/product-page
```

Verbose logging:
```bash
python main.py --verbose https://example.com/product-page
```

### URL File Format

Create a text file (e.g., `urls.txt`) with one URL per line:
```
https://example.com/product1
https://example.com/product2
https://example.com/product3
# Lines starting with # are comments and will be ignored
```

## Configuration

### Configuration File Options

| Option | Description | Default |
|--------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT features | Required for AI features |
| `OPENAI_MODEL` | GPT model to use | `gpt-4` |
| `IMAGE_MAX_WIDTH` | Maximum image width in pixels | `1024` |
| `IMAGE_MAX_HEIGHT` | Maximum image height in pixels | `1024` |
| `IMAGE_QUALITY` | JPEG quality (1-100) | `85` |
| `REQUEST_TIMEOUT` | HTTP request timeout in seconds | `30` |
| `REQUEST_DELAY` | Delay between requests in seconds | `2` |
| `MAX_RETRIES` | Maximum retry attempts | `3` |
| `USER_AGENT_ROTATION` | Enable user agent rotation | `true` |
| `USE_PROXY` | Enable proxy usage | `false` |
| `PROXY_URL` | Proxy server URL | Empty |
| `OUTPUT_DIR` | Output directory for CSV/JSON files | `./output` |
| `IMAGES_DIR` | Directory for downloaded images | `./images` |
| `LOGS_DIR` | Directory for log files | `./logs` |
| `OUTPUT_FORMAT` | Default output format | `csv` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Output

### CSV Output
The application generates a Shopify-compatible CSV file with all required columns:
- Product information (title, description, vendor, type)
- Variants and pricing
- Images with positions
- SEO metadata
- Tags and categories

### JSON Output
Alternative JSON format containing:
- All extracted metadata
- Enhanced descriptions
- Generated tags
- Image paths
- Source URLs

### Directory Structure
```
product-scraper/
├── output/              # CSV/JSON export files
├── images/              # Downloaded and processed images
│   └── Product_Name/    # Images organized by product
└── logs/                # Application logs
```

## Best Practices

### Web Scraping Ethics
- Respect website terms of service
- Use appropriate delays between requests
- Don't overload target servers
- Consider using proxy servers for large-scale scraping
- Check robots.txt before scraping

### Performance Optimization
- Process images only when needed (`--no-images`)
- Skip GPT enhancement for testing (`--no-enhance`)
- Adjust `REQUEST_DELAY` based on target website
- Use proxy rotation for large batches

### Error Handling
- Review log files in `logs/` directory
- Check failed URLs in console output
- Verify configuration before large batches
- Test with single URL first

## Troubleshooting

### Common Issues

**"OPENAI_API_KEY is required"**
- Add your OpenAI API key to `config.env`
- Or use `--no-enhance --no-tags` to skip AI features

**"Connection timeout"**
- Increase `REQUEST_TIMEOUT` in config
- Check your internet connection
- Verify the URL is accessible

**"Failed to download image"**
- Some websites block automated downloads
- Check if proxy is needed
- Verify image URLs are accessible

**"No product data extracted"**
- The website structure may not be supported
- Check logs for detailed error messages
- May need custom extraction rules

## Dependencies

- **requests**: HTTP library for fetching web pages
- **beautifulsoup4**: HTML parsing and extraction
- **lxml**: Fast XML and HTML parser
- **Pillow**: Image processing and resizing
- **openai**: GPT API integration
- **pandas**: Data manipulation and CSV export
- **python-dotenv**: Environment variable management
- **fake-useragent**: User agent rotation
- **tenacity**: Retry logic with exponential backoff
- **colorlog**: Enhanced logging

## Architecture

### Module Structure

```
modules/
├── config.py                   # Configuration management
├── logger.py                   # Logging setup
├── scraper.py                  # Web scraping logic
├── image_processor.py          # Image downloading and resizing
├── gpt_processor.py            # GPT integration
├── shopify_exporter.py         # Shopify CSV export
├── product_scraper.py          # Main orchestrator
├── brand_manager.py            # Brand registry management
├── brand_validator.py          # Brand website validation
├── media_pack_discovery.py     # Media pack discovery
├── media_pack_downloader.py    # Media pack downloads
├── media_pack_extractor.py     # Archive extraction
├── competitor_site_manager.py  # Competitor site management
├── robots_txt_parser.py        # Robots.txt compliance
├── site_health_monitor.py      # Site health monitoring
├── user_agent_rotator.py       # User agent rotation
└── product_discovery.py        # Product discovery on competitor sites
```

### CLI Tools

- **`main.py`** - Original product scraper (12 commands)
- **`brand_manager.py`** - Brand management CLI (12 commands: load, validate, queue, list, add, update, remove, history, discover-media, media-packs, download, extract)
- **`competitor_manager.py`** - Competitor site management CLI (11 commands: load, list, add, update, remove, health, robots, analyze, history, discover, products)

### Processing Pipeline

1. **URL Input** → Load URLs from command line or file
2. **Web Scraping** → Fetch and parse HTML with BeautifulSoup
3. **Data Extraction** → Extract metadata, images, and content
4. **Image Processing** → Download and resize images
5. **AI Enhancement** → Enhance descriptions and generate tags (optional)
6. **Export** → Generate Shopify CSV or JSON output

## License

This project is provided as-is for product data processing and Shopify integration.

## Support

For issues and questions:
1. Check the log files in `logs/` directory
2. Review this README for common solutions
3. Verify your configuration in `config.env`

## Contributing

Contributions are welcome! Areas for enhancement:
- Support for additional e-commerce platforms
- Custom extraction rules per website
- Advanced image recognition
- Multi-language support
- Database storage options
