#!/bin/bash

# OpenClaw Config UI - Start Script
# Starts both backend and frontend in parallel

echo "🚀 Starting OpenClaw Configuration UI..."
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting backend server..."
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Application started!"
echo ""
echo "Backend running on: http://localhost:8000"
echo "Frontend running on: http://localhost:3000"
echo ""
echo "Open your browser to: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Wait for processes
wait
