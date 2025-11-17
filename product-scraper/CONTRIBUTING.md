# Contributing to Product Scraper

Thank you for considering contributing to the Product Scraper! This document provides guidelines for extending and improving the application.

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Mac/Linux
   # or
   venv\Scripts\activate.bat  # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create your config file:
   ```bash
   cp config.env.example config.env
   # Edit config.env with your settings
   ```

## Project Structure

```
product-scraper/
├── modules/              # Core application modules
│   ├── config.py        # Configuration management
│   ├── logger.py        # Logging utilities
│   ├── scraper.py       # Web scraping logic
│   ├── image_processor.py   # Image handling
│   ├── gpt_processor.py     # AI integration
│   ├── shopify_exporter.py  # Export functionality
│   └── product_scraper.py   # Main orchestrator
├── main.py              # CLI entry point
├── demo.py              # Demonstration script
└── tests/               # Test files (future)
```

## Code Style

- Follow PEP 8 style guidelines
- Use descriptive variable and function names
- Add docstrings to all classes and functions
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

### Example Function

```python
def process_product_data(url, config):
    """
    Process product data from a given URL
    
    Args:
        url: Product page URL to scrape
        config: Configuration object
    
    Returns:
        dict: Processed product data
    
    Raises:
        ValueError: If URL is invalid
        RequestException: If page fetch fails
    """
    # Implementation here
    pass
```

## Adding New Features

### 1. Adding a New Export Format

To add support for a new export format (e.g., XML):

1. Add export method to `ShopifyExporter` class:
   ```python
   def export_to_xml(self, products, output_path=None):
       """Export products to XML format"""
       # Implementation
   ```

2. Update the `export()` method to handle the new format:
   ```python
   def export(self, products, format='csv', output_path=None):
       if format.lower() == 'xml':
           return self.export_to_xml(products, output_path)
       # ... existing code
   ```

3. Update CLI options in `main.py`:
   ```python
   parser.add_argument(
       '--format',
       choices=['csv', 'json', 'xml'],
       default='csv',
       help='Output format'
   )
   ```

### 2. Adding Custom Extraction Rules

To add website-specific extraction logic:

1. Create a new method in `WebScraper` class:
   ```python
   def _extract_custom_site(self, soup, base_url):
       """Extract data from a specific website"""
       # Custom extraction logic
       return metadata
   ```

2. Update `extract_product_data()` to detect and use custom rules:
   ```python
   def extract_product_data(self, url):
       # Detect website
       if 'customsite.com' in url:
           return self._extract_custom_site(soup, url)
       # Default extraction
   ```

### 3. Adding New Image Processing Features

To add image filters or transformations:

1. Add method to `ImageProcessor` class:
   ```python
   def apply_watermark(self, image_path, watermark_text):
       """Apply watermark to image"""
       # Implementation
   ```

2. Optionally add config options:
   ```python
   # In config.py
   self.watermark_enabled = os.getenv('WATERMARK_ENABLED', 'false').lower() == 'true'
   self.watermark_text = os.getenv('WATERMARK_TEXT', '')
   ```

### 4. Adding New GPT Features

To add new AI-powered features:

1. Add method to `GPTProcessor` class:
   ```python
   def generate_product_benefits(self, description):
       """Generate list of product benefits"""
       # Implementation with GPT API call
   ```

2. Ensure fallback behavior for when API key is missing

## Testing

### Manual Testing

Run the demo script to verify basic functionality:
```bash
python demo.py
```

Test with a real URL (without AI features):
```bash
python main.py --no-enhance --no-tags --no-images https://example.com/product
```

### Adding Tests (Future)

When adding tests, use this structure:
```
tests/
├── test_config.py
├── test_scraper.py
├── test_image_processor.py
└── test_exporter.py
```

Example test:
```python
import unittest
from modules import Config

class TestConfig(unittest.TestCase):
    def test_default_values(self):
        config = Config()
        self.assertEqual(config.image_max_width, 1024)
```

## Error Handling

Always handle errors gracefully:

```python
try:
    # Risky operation
    result = fetch_data(url)
except RequestException as e:
    logger.error(f"Failed to fetch {url}: {e}")
    return None
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

## Logging

Use appropriate log levels:

- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages for recoverable issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical issues requiring immediate attention

Example:
```python
logger.debug(f"Processing URL: {url}")
logger.info("Product scraped successfully")
logger.warning("Some images failed to download")
logger.error(f"Failed to parse HTML: {e}")
```

## Configuration

When adding new config options:

1. Add to `config.env.example`:
   ```env
   # New Feature Configuration
   NEW_FEATURE_ENABLED=true
   NEW_FEATURE_VALUE=100
   ```

2. Load in `Config` class:
   ```python
   self.new_feature_enabled = os.getenv('NEW_FEATURE_ENABLED', 'true').lower() == 'true'
   self.new_feature_value = int(os.getenv('NEW_FEATURE_VALUE', 100))
   ```

3. Update README.md with new configuration options

## Documentation

When adding features, update:

1. **README.md**: User-facing documentation
2. **DOCUMENTATION.md**: Technical documentation
3. **Docstrings**: In-code documentation
4. **QUICKSTART.md**: If it affects quick start process

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Test thoroughly
4. Update documentation
5. Commit with clear messages
6. Push and create pull request

### Commit Message Format

```
feat: Add XML export support

- Implement export_to_xml method
- Update CLI to accept xml format
- Add tests for XML export
```

Prefixes:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

## Common Development Tasks

### Testing a Single Module

```python
# Test scraper module
cd product-scraper
source venv/bin/activate
python -c "from modules import WebScraper, Config, setup_logger; ..."
```

### Debugging

1. Enable verbose logging: `--verbose`
2. Check log files in `logs/` directory
3. Add print statements or use Python debugger:
   ```python
   import pdb; pdb.set_trace()
   ```

### Performance Profiling

```python
import cProfile
import pstats

cProfile.run('main()', 'profile_stats')
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative')
stats.print_stats(20)
```

## Future Enhancement Ideas

- [ ] Multi-threaded image processing
- [ ] Database storage option (SQLite/PostgreSQL)
- [ ] Web UI for management
- [ ] REST API endpoints
- [ ] Docker containerization
- [ ] Custom extraction rule DSL
- [ ] Advanced image recognition (product detection)
- [ ] Multi-language support
- [ ] Scheduled scraping
- [ ] Rate limiting per domain
- [ ] Session persistence for large batches

## Questions or Issues?

- Check existing documentation
- Review log files
- Test with demo script
- Create an issue with detailed information

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

Thank you for contributing! 🎉
