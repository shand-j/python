@echo off
REM Setup script for Vape Product Tagger (Windows)

echo ==========================================
echo Vape Product Tagger - Setup
echo ==========================================
echo.

REM Check Python installation
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%
echo.

REM Create virtual environment
echo Creating virtual environment...
if exist "venv" (
    echo Virtual environment already exists, skipping...
) else (
    python -m venv venv
    echo Virtual environment created
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo Dependencies installed
echo.

REM Create configuration file
echo Setting up configuration...
if exist "config.env" (
    echo config.env already exists, skipping...
) else (
    copy config.env.example config.env
    echo config.env created from example
    echo Please edit config.env to configure your settings
)
echo.

REM Create necessary directories
echo Creating directories...
if not exist "output" mkdir output
if not exist "logs" mkdir logs
if not exist "cache" mkdir cache
if not exist "sample_data" mkdir sample_data
echo Directories created
echo.

echo ==========================================
echo Setup completed successfully!
echo ==========================================
echo.
echo Next steps:
echo 1. Activate the virtual environment:
echo    venv\Scripts\activate.bat
echo.
echo 2. Configure the application:
echo    Edit config.env with your settings
echo.
echo 3. If using Ollama AI, ensure Ollama is running:
echo    ollama serve
echo.
echo 4. Run the application:
echo    python main.py --input your_products.csv
echo.
echo For help:
echo    python main.py --help
echo.
pause
