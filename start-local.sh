#!/bin/bash

# ReadThatPDF Local Development Setup (without Docker for frontend)

echo "🚀 Starting ReadThatPDF Local Development"
echo "========================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Start backend services with Docker
echo "🐳 Starting backend services..."
docker-compose up -d redis backend celery-worker celery-beat

# Wait for services
echo "⏳ Waiting for backend services..."
sleep 10

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

echo ""
echo "🎉 Backend services are running!"
echo "================================"
echo "🔧 Backend API:   http://localhost:8000"
echo "📚 API Docs:      http://localhost:8000/docs"
echo "🔍 Redis:         localhost:6379"
echo ""
echo "🖥️  To start the frontend:"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "📋 Useful commands:"
echo "  Backend logs:   docker-compose logs -f backend"
echo "  Worker logs:    docker-compose logs -f celery-worker"
echo "  Stop backend:   docker-compose down"