#!/bin/bash

# Tesseracts World Deployment Script
# This script sets up and runs the enhanced decentralized commerce platform

set -e  # Exit on any error

echo "🚀 Starting Tesseracts World Deployment..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python 3.8+ required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version check passed: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Ensure pip is available in the virtual environment
echo "🔧 Ensuring pip is available..."
python3 -m ensurepip --default-pip

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

# Install dependencies
echo "📚 Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Initialize database (will create tables automatically on first run)
echo "🗄️  Database will be initialized automatically on first API start"

# Check if port 8000 is available
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8000 is already in use. Please stop the existing service or choose a different port."
    exit 1
fi

echo "🌐 Starting Tesseracts World API server..."
echo "📖 API documentation will be available at: http://localhost:8000/docs"
echo "🔍 Health check available at: http://localhost:8000/api/v1/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the API server
python src/api/main.py
