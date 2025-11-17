# Quick Start Guide

Get started with the Product Scraper in 5 minutes!

## Step 1: Setup Environment

### On Mac/Linux:
```bash
cd product-scraper
./setup.sh
```

### On Windows:
```bash
cd product-scraper
setup.bat
```

Or manually:
```bash
# Create virtual environment
python3 -m venv venv  # or python -m venv venv on Windows

# Activate it
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure (Optional)

If you want to use AI features (description enhancement and tag generation):

1. Copy the example config:
   ```bash
   cp config.env.example config.env
   ```

2. Edit `config.env` and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=your_key_here
   ```

**Note:** The scraper works without an API key, but AI features will be disabled.

## Step 3: Run Your First Scrape

### Quick test (no AI features):
```bash
python main.py --no-enhance --no-tags --no-images https://example.com/product
```

### Full scrape with all features:
```bash
python main.py https://example.com/product-url
```

### Scrape multiple products:
```bash
# Create a file with URLs (one per line)
echo "https://example.com/product1" > my_urls.txt
echo "https://example.com/product2" >> my_urls.txt

# Scrape all URLs
python main.py --file my_urls.txt
```

## Step 4: Find Your Results

After scraping, you'll find:

- **CSV file**: `output/shopify_products_YYYYMMDD_HHMMSS.csv`
- **Images**: `images/Product_Name/`
- **Logs**: `logs/scraper_YYYYMMDD_HHMMSS.log`

## Common Options

```bash
# Export to JSON instead of CSV
python main.py --format json URL

# Skip image download (faster)
python main.py --no-images URL

# Skip AI enhancement (no API costs)
python main.py --no-enhance --no-tags URL

# Verbose logging for debugging
python main.py --verbose URL

# Custom output file
python main.py --output my_products.csv URL
```

## Troubleshooting

### "ModuleNotFoundError"
- Make sure virtual environment is activated: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### "OPENAI_API_KEY is required"
- Either add your API key to `config.env`
- Or run with: `--no-enhance --no-tags`

### "Failed to fetch page"
- Check if the URL is accessible in your browser
- Some sites may block automated requests
- Try adding a delay: edit `REQUEST_DELAY` in `config.env`

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [DOCUMENTATION.md](DOCUMENTATION.md) for technical details
- Customize `config.env` for your needs

## Need Help?

1. Check log files in the `logs/` directory
2. Run with `--verbose` for more details
3. Review the error messages carefully

Happy scraping! 🚀
