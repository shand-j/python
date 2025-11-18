#!/bin/bash
# Setup script for Product Scraper
# This script sets up the virtual environment and installs dependencies

echo "=========================================="
echo "Product Scraper Setup"
echo "=========================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

if [ ! -d "venv" ]; then
    echo "Error: Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

# Create config file if it doesn't exist
if [ ! -f "config.env" ]; then
    echo ""
    echo "Creating config.env from template..."
    cp config.env.example config.env
    echo "✓ Created config.env"
    echo "  Please edit config.env and add your OpenAI API key"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p output images logs

echo ""
echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit config.env and add your OpenAI API key"
echo "2. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo "3. Run the scraper:"
echo "   python main.py https://example.com/product-page"
echo ""
