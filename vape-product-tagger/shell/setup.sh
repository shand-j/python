#!/bin/bash
# Setup script for Vape Product Tagger

set -e

echo "=========================================="
echo "Vape Product Tagger - Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
echo "Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "Dependencies installed"
echo ""

# Create configuration file
echo "Setting up configuration..."
if [ -f "config.env" ]; then
    echo "config.env already exists, skipping..."
else
    cp config.env.example config.env
    echo "config.env created from example"
    echo "Please edit config.env to configure your settings"
fi
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p output logs cache sample_data
echo "Directories created"
echo ""

echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Configure the application:"
echo "   Edit config.env with your settings"
echo ""
echo "3. If using Ollama AI, ensure Ollama is running:"
echo "   ollama serve"
echo ""
echo "4. Run the application:"
echo "   python main.py --input your_products.csv"
echo ""
echo "For help:"
echo "   python main.py --help"
echo ""
