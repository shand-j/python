@echo off
REM OpenClaw Config UI Setup Script for Windows
REM Sets up both backend and frontend

echo ======================================
echo OpenClaw Config UI Setup
echo ======================================
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    echo Please install Python 3.8 or higher
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Check Node.js
echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed
    echo Please install Node.js 18 or higher
    exit /b 1
)

for /f %%i in ('node --version') do set NODE_VERSION=%%i
echo Found Node.js %NODE_VERSION%

REM Setup Backend
echo.
echo Setting up Python backend...
cd backend

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

cd ..

REM Setup Frontend
echo.
echo Setting up Next.js frontend...
cd frontend

REM Install dependencies
echo Installing Node.js dependencies...
call npm install

cd ..

echo.
echo ======================================
echo Setup Complete! ✅
echo ======================================
echo.
echo To start the application:
echo.
echo 1. Start the backend (in one terminal):
echo    cd backend
echo    venv\Scripts\activate.bat
echo    python main.py
echo.
echo 2. Start the frontend (in another terminal):
echo    cd frontend
echo    npm run dev
echo.
echo 3. Open your browser to: http://localhost:3000
echo.
echo ======================================

pause
