#!/bin/bash

# Start All Services Script
# This script starts both backend and frontend concurrently

echo "🚀 Starting GenAI Research Tool (Full Stack)"
echo "============================================="
echo ""

# Check if tmux is available
if command -v tmux &> /dev/null; then
    echo "Using tmux for session management..."
    echo ""

    # Create a new tmux session
    tmux new-session -d -s genai-research

    # Split window horizontally
    tmux split-window -h

    # Run backend in left pane
    tmux send-keys -t genai-research:0.0 './start-backend.sh' C-m

    # Run frontend in right pane
    tmux send-keys -t genai-research:0.1 './start-frontend.sh' C-m

    # Attach to the session
    echo "✓ Services started in tmux session 'genai-research'"
    echo ""
    echo "To attach: tmux attach -t genai-research"
    echo "To detach: Press Ctrl+B then D"
    echo "To kill session: tmux kill-session -t genai-research"
    echo ""

    tmux attach -t genai-research
else
    echo "⚠️  tmux not found. Starting services in background..."
    echo ""

    # Start backend in background
    echo "Starting backend..."
    ./start-backend.sh > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "✓ Backend started (PID: $BACKEND_PID)"

    # Wait a bit for backend to initialize
    sleep 3

    # Start frontend in foreground
    echo "Starting frontend..."
    ./start-frontend.sh

    # Cleanup on exit
    echo ""
    echo "Stopping backend..."
    kill $BACKEND_PID
fi
