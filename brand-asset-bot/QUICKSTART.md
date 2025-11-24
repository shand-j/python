# Quick Start Guide

Get started with the Brand Asset Bot in 5 minutes!

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

1. Copy configuration files:
   ```bash
   cp config.env.example config.env
   cp brands.txt.example brands.txt
   ```

2. Edit `config.env` and add your OpenAI API key (optional):
   ```env
   OPENAI_API_KEY=your_key_here
   ```

3. Edit `brands.txt` to customize brands (optional - defaults included)

**Note:** The bot works without configuration, but AI features require an OpenAI API key.

## Step 3: Run Your First Brand Asset Discovery

### Basic brand asset discovery:
```bash
python main.py --mode brand-asset --brand SMOK
```

### Full discovery with competitors:
```bash
python main.py --mode brand-asset --brand SMOK --include-competitors
```

### Legacy product scraping:
```bash
python main.py --mode product https://example.com/product-url
```

## Step 4: Find Your Results

After discovery, you'll find:

- **Brand catalog**: `output/brand_assets_BRAND_YYYYMMDD_HHMMSS.json`
- **Downloaded media packs**: `downloads/BRAND/`
- **Extracted assets**: `extracted/BRAND/`
- **Logs**: `logs/brand_asset_bot_YYYYMMDD_HHMMSS.log`

## Common Options

```bash
# Brand asset discovery
python main.py --mode brand-asset --brand BRAND_NAME

# Include competitor sources
python main.py --mode brand-asset --brand BRAND_NAME --include-competitors

# Verbose logging for debugging
python main.py --mode brand-asset --brand BRAND_NAME --verbose

# Legacy product scraping
python main.py --mode product --format json URL

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
