@echo off
REM OpenClaw Config UI - Start Script for Windows
REM Starts both backend and frontend

echo 🚀 Starting OpenClaw Configuration UI...
echo.

REM Start backend in new window
echo Starting backend server...
start "OpenClaw Backend" cmd /k "cd backend && venv\Scripts\activate.bat && python main.py"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo Starting frontend...
start "OpenClaw Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ✅ Application started!
echo.
echo Backend running on: http://localhost:8000
echo Frontend running on: http://localhost:3000
echo.
echo Open your browser to: http://localhost:3000
echo.
echo Close the terminal windows to stop the servers.
echo.

pause
