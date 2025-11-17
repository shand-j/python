# Python Projects Monorepo

This is a monorepo for Python projects and scripts. Each project is organized in its own directory with its own virtual environment and dependencies.

## Projects

### Product Scraper

A comprehensive product data scraping and processing application for Shopify import.

**Location:** `product-scraper/`

**Features:**
- Web scraping with BeautifulSoup and requests
- Image downloading and resizing
- AI-powered description enhancement (GPT integration)
- Intelligent tag generation
- Shopify CSV export
- JSON export alternative
- Comprehensive error handling and logging

**Quick Start:**
```bash
cd product-scraper
./setup.sh  # or setup.bat on Windows
python main.py --help
```

**Documentation:**
- [README.md](product-scraper/README.md) - Complete user guide
- [QUICKSTART.md](product-scraper/QUICKSTART.md) - Get started in 5 minutes
- [DOCUMENTATION.md](product-scraper/DOCUMENTATION.md) - Technical documentation
- [CONTRIBUTING.md](product-scraper/CONTRIBUTING.md) - Developer guide

## Repository Structure

```
python/
├── .github/              # GitHub configuration
├── product-scraper/      # Product data scraper project
│   ├── modules/          # Core application modules
│   ├── output/           # Generated output files
│   ├── images/           # Downloaded images
│   ├── logs/             # Application logs
│   ├── main.py           # Main entry point
│   ├── demo.py           # Demonstration script
│   ├── requirements.txt  # Python dependencies
│   ├── setup.sh/bat      # Setup scripts
│   └── Documentation files
└── README.md             # This file
```

## General Guidelines

### Virtual Environments

Each project uses its own virtual environment to isolate dependencies:

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### OS Compatibility

All projects are designed to be OS agnostic and work on:
- Windows 10/11
- macOS 10.14+
- Linux (Ubuntu, Debian, CentOS, etc.)

### Python Version

Minimum Python version: 3.8+
Recommended: Python 3.10+

## Adding New Projects

When adding a new project to this monorepo:

1. Create a new directory with a descriptive name
2. Set up a virtual environment within the project directory
3. Create a `requirements.txt` for dependencies
4. Add a README.md with project-specific documentation
5. Include setup scripts (setup.sh, setup.bat) if needed
6. Add appropriate .gitignore rules
7. Update this README with the new project

### Project Template Structure

```
new-project/
├── venv/                 # Virtual environment (gitignored)
├── src/                  # Source code
├── tests/                # Test files
├── requirements.txt      # Dependencies
├── setup.sh/bat          # Setup scripts
├── README.md             # Project documentation
└── .gitignore           # Git ignore rules
```

## Contributing

See individual project CONTRIBUTING.md files for project-specific guidelines.

General contribution guidelines:
- Follow PEP 8 style guidelines
- Add comprehensive documentation
- Include error handling
- Write clear commit messages
- Test thoroughly before submitting

## License

Individual projects may have their own licenses. See project-specific LICENSE files.

## Support

For project-specific issues and questions, refer to the project's README.md file.

For general repository questions, please open an issue.
