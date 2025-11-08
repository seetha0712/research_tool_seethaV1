#!/bin/bash

# Start Frontend Script
# This script starts the React development server

echo "🚀 Starting GenAI Research Tool Frontend..."
echo ""

# Navigate to project root
cd "$(dirname "$0")"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Using defaults."
    echo "To customize, copy .env.example to .env"
    echo ""
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
    echo "✓ Dependencies installed"
    echo ""
fi

# Start the development server
echo "🌐 Starting React development server..."
echo "Frontend will be available at http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm start
