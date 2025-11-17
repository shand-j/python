@echo off
REM Setup script for Product Scraper (Windows)
REM This script sets up the virtual environment and installs dependencies

echo ==========================================
echo Product Scraper Setup
echo ==========================================
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv

if not exist "venv\" (
    echo Error: Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

REM Create config file if it doesn't exist
if not exist "config.env" (
    echo.
    echo Creating config.env from template...
    copy config.env.example config.env
    echo √ Created config.env
    echo   Please edit config.env and add your OpenAI API key
)

REM Create necessary directories
echo.
echo Creating directories...
if not exist "output\" mkdir output
if not exist "images\" mkdir images
if not exist "logs\" mkdir logs

echo.
echo ==========================================
echo Setup completed successfully!
echo ==========================================
echo.
echo Next steps:
echo 1. Edit config.env and add your OpenAI API key
echo 2. Activate the virtual environment:
echo    venv\Scripts\activate.bat
echo 3. Run the scraper:
echo    python main.py https://example.com/product-page
echo.
pause
