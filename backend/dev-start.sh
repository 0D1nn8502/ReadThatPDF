#!/bin/bash

# Development startup script with Redis cleanup

echo "🚀 Starting ReadThatPDF Backend (Development Mode)"
echo "=================================================="

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Please start Redis first."
    echo "   You can start it with: redis-server"
    exit 1
fi

echo "✅ Redis is running"

# Clean Redis database to avoid schema conflicts
echo "🧹 Cleaning Redis database to avoid schema conflicts..."
redis-cli FLUSHDB > /dev/null 2>&1
echo "✅ Redis database cleaned"

# Set development environment
export ENVIRONMENT=development

# Start the FastAPI server
echo "🔧 Starting FastAPI server..."
python main.py