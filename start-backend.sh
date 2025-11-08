#!/bin/bash

# Start Backend Script
# This script starts the FastAPI backend server

echo "🚀 Starting GenAI Research Tool Backend..."
echo ""

# Navigate to backend directory
cd "$(dirname "$0")/backend"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your API keys:"
    echo "   cp .env.example .env"
    echo ""
    exit 1
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create necessary directories
mkdir -p uploads output static/decks chroma_db
echo "✓ Directories created"
echo ""

# Start the server
echo "🌐 Starting server at http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
