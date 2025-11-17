# Product Scraper - Technical Documentation

## Project Overview

The Product Scraper is a comprehensive Python application designed to extract product data from e-commerce websites, enhance descriptions using AI, process images, and export data in Shopify-compatible formats.

## System Requirements

### Minimum Requirements
- Python 3.8+
- 2GB RAM
- 500MB free disk space
- Internet connection

### Recommended Requirements
- Python 3.10+
- 4GB RAM
- 2GB free disk space
- High-speed internet connection

### Supported Operating Systems
- Windows 10/11
- macOS 10.14+
- Linux (Ubuntu 18.04+, Debian 10+, CentOS 7+)

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Main Application                      │
│                          (main.py)                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
┌───────▼──────────┐  ┌────▼────────────┐
│  Configuration   │  │     Logger      │
│   (config.py)    │  │  (logger.py)    │
└──────────────────┘  └─────────────────┘
        │
        │
┌───────▼───────────────────────────────────────────────────┐
│              Product Scraper Orchestrator                  │
│              (product_scraper.py)                          │
└─────┬────────────┬──────────────┬──────────────┬──────────┘
      │            │              │              │
┌─────▼─────┐ ┌───▼────────┐ ┌───▼────────┐ ┌──▼──────────┐
│   Web     │ │   Image    │ │    GPT     │ │  Shopify    │
│  Scraper  │ │ Processor  │ │ Processor  │ │  Exporter   │
│           │ │            │ │            │ │             │
└───────────┘ └────────────┘ └────────────┘ └─────────────┘
```

### Data Flow

```
URL Input
   ↓
Web Scraping (BeautifulSoup + Requests)
   ↓
Metadata Extraction
   ↓
┌──────────────┬──────────────┬──────────────┐
│              │              │              │
Image Download  Description    Tag Generation
& Resizing     Enhancement     (GPT)
(Pillow)       (GPT)
│              │              │
└──────────────┴──────────────┴──────────────┘
                  ↓
            Data Aggregation
                  ↓
         Shopify CSV Export
                  ↓
            Output File
```

## Module Documentation

### 1. Configuration Module (config.py)

**Purpose**: Manages application configuration from environment files

**Key Classes**:
- `Config`: Configuration manager

**Key Methods**:
- `__init__(config_file)`: Load configuration
- `validate()`: Validate configuration values
- `_create_directories()`: Create necessary directories

**Configuration Parameters**:
See Configuration section in README.md

### 2. Logger Module (logger.py)

**Purpose**: Provides structured logging for the application

**Key Functions**:
- `setup_logger(name, log_dir, log_level)`: Configure logger with console and file handlers

**Features**:
- Console output with timestamps
- File logging with detailed context
- Configurable log levels
- Automatic log file creation

### 3. Web Scraper Module (scraper.py)

**Purpose**: Handles fetching and parsing web pages

**Key Classes**:
- `WebScraper`: Main scraper class

**Key Methods**:
- `fetch_page(url)`: Fetch web page with retry logic
- `parse_html(html_content)`: Parse HTML using BeautifulSoup
- `extract_metadata(soup, base_url)`: Extract product metadata
- `extract_product_data(url)`: Complete product extraction

**Features**:
- User agent rotation
- Proxy support
- Retry logic with exponential backoff
- Multiple extraction strategies
- Schema.org structured data parsing
- Breadcrumb extraction

### 4. Image Processor Module (image_processor.py)

**Purpose**: Downloads and processes product images

**Key Classes**:
- `ImageProcessor`: Image processing handler

**Key Methods**:
- `download_image(url, output_dir, index)`: Download image
- `resize_image(image_path, max_width, max_height)`: Resize image
- `process_images(image_urls, output_dir)`: Batch process images

**Features**:
- Aspect ratio preservation
- Quality optimization
- Format conversion (RGBA → RGB)
- High-quality Lanczos resampling
- Unique filename generation

### 5. GPT Processor Module (gpt_processor.py)

**Purpose**: AI-powered content enhancement and tag generation

**Key Classes**:
- `GPTProcessor`: GPT integration handler

**Key Methods**:
- `enhance_description(original, product_name, context)`: Enhance descriptions
- `generate_tags(product_name, description, metadata)`: Generate tags
- `generate_summary(description, max_words)`: Create summaries

**Features**:
- OpenAI GPT-4 integration
- Fallback for missing API keys
- Temperature-controlled generation
- Context-aware enhancement

### 6. Shopify Exporter Module (shopify_exporter.py)

**Purpose**: Export data to Shopify CSV format

**Key Classes**:
- `ShopifyExporter`: Export handler

**Key Methods**:
- `export_to_csv(products, output_path)`: Export to CSV
- `export_to_json(products, output_path)`: Export to JSON
- `export(products, format, output_path)`: Unified export

**Features**:
- Complete Shopify CSV schema
- Handle generation from titles
- HTML description formatting
- Multi-image support
- JSON export alternative

### 7. Product Scraper Module (product_scraper.py)

**Purpose**: Main orchestrator coordinating all components

**Key Classes**:
- `ProductScraper`: Main orchestrator

**Key Methods**:
- `scrape_product(url, **options)`: Scrape single product
- `scrape_products(urls, **options)`: Batch scrape
- `export_products(products, format, path)`: Export products
- `scrape_and_export(urls, **options)`: Complete pipeline

**Features**:
- Pipeline orchestration
- Error handling and recovery
- Progress tracking
- Batch processing

## API Integration

### OpenAI GPT API

The application uses OpenAI's GPT API for:
1. Description enhancement
2. Tag generation
3. Content summarization

**API Configuration**:
```python
client = OpenAI(api_key=config.openai_api_key)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    temperature=0.7,
    max_tokens=1000
)
```

**Rate Limits**:
- Respect OpenAI's rate limits
- Implement request delays
- Handle API errors gracefully

## Error Handling

### Error Types

1. **Network Errors**:
   - Connection timeouts
   - HTTP errors (404, 500, etc.)
   - DNS resolution failures

2. **Parsing Errors**:
   - Invalid HTML structure
   - Missing expected elements
   - Encoding issues

3. **Processing Errors**:
   - Image download failures
   - Image resize errors
   - API failures

4. **Configuration Errors**:
   - Missing API keys
   - Invalid configuration values
   - Permission issues

### Error Recovery Strategies

1. **Retry with Exponential Backoff**:
   ```python
   @retry(stop=stop_after_attempt(3), 
          wait=wait_exponential(multiplier=1, min=2, max=10))
   def fetch_page(self, url):
       # Fetch logic
   ```

2. **Graceful Degradation**:
   - Continue without GPT if API key missing
   - Skip problematic images
   - Use fallback extraction methods

3. **Detailed Logging**:
   - Log all errors with context
   - Include stack traces for debugging
   - Track failed URLs

## Performance Optimization

### Best Practices

1. **Request Management**:
   - Implement delays between requests
   - Use session objects for connection pooling
   - Enable compression

2. **Image Processing**:
   - Process images in parallel (future enhancement)
   - Use efficient Pillow operations
   - Optimize quality settings

3. **Memory Management**:
   - Process products in batches
   - Clean up temporary files
   - Stream large files

4. **Caching**:
   - Cache downloaded images
   - Store intermediate results
   - Reuse parsed data

## Testing

### Manual Testing

1. **Single Product Test**:
   ```bash
   python main.py https://example.com/product
   ```

2. **Batch Test**:
   ```bash
   python main.py --file test_urls.txt
   ```

3. **Feature Tests**:
   ```bash
   # Test without GPT
   python main.py --no-enhance --no-tags URL
   
   # Test without images
   python main.py --no-images URL
   ```

### Test Coverage Areas

- URL validation
- HTML parsing
- Image downloading
- Image resizing
- GPT integration
- CSV export format
- Error handling
- Configuration loading

## Security Considerations

### API Key Security
- Never commit API keys to version control
- Use environment variables or config files
- Rotate keys regularly

### Web Scraping Ethics
- Respect robots.txt
- Implement rate limiting
- Use appropriate user agents
- Don't overwhelm target servers

### Data Privacy
- Don't store sensitive user data
- Secure API credentials
- Clean up temporary files

## Deployment

### Production Deployment

1. **Environment Setup**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configuration**:
   - Set production API keys
   - Configure appropriate rate limits
   - Set up logging directory

3. **Monitoring**:
   - Monitor log files
   - Track success/failure rates
   - Monitor API usage

### Docker Deployment (Future)

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## Troubleshooting Guide

### Common Issues and Solutions

1. **Import Errors**:
   - Ensure virtual environment is activated
   - Reinstall dependencies: `pip install -r requirements.txt`

2. **API Errors**:
   - Verify API key in config.env
   - Check API quota and limits
   - Test with `--no-enhance --no-tags`

3. **Image Errors**:
   - Check write permissions
   - Verify disk space
   - Test with `--no-images`

4. **Parsing Errors**:
   - Website structure may have changed
   - Check if website blocks automation
   - Review logs for specific errors

## Future Enhancements

### Planned Features
1. Custom extraction rules per website
2. Database storage option
3. Web UI for management
4. Parallel processing
5. Advanced image recognition
6. Multi-language support
7. Additional export formats
8. Scheduling and automation

## Maintenance

### Regular Tasks
1. Update dependencies monthly
2. Review and rotate API keys
3. Clean up old log files
4. Monitor disk usage
5. Update documentation

### Version Updates
- Follow semantic versioning
- Document breaking changes
- Provide migration guides

## Support and Resources

### Documentation
- README.md - User guide
- DOCUMENTATION.md - Technical details (this file)
- Code comments - Inline documentation

### Logs
- Console output - Real-time progress
- Log files - Detailed debugging info

### Getting Help
1. Check log files in `logs/` directory
2. Review error messages
3. Verify configuration
4. Test with simple URLs first
