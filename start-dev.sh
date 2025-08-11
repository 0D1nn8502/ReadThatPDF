#!/bin/bash

# ReadThatPDF Development Startup Script

echo "🚀 Starting ReadThatPDF Development Environment"
echo "=============================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  Port $1 is already in use. Please stop the service using this port."
        return 1
    fi
    return 0
}

# Check required ports
echo "🔍 Checking required ports..."
check_port 3000 || exit 1  # Frontend
check_port 8000 || exit 1  # Backend
check_port 6379 || exit 1  # Redis

echo "✅ All ports are available"

# Start services with Docker Compose
echo "🐳 Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check Redis
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is healthy"
else
    echo "❌ Redis is not responding"
fi

# Check Backend
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend is not responding"
fi

# Check Frontend
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend is not responding"
fi

echo ""
echo "🎉 Development environment is ready!"
echo "=============================================="
echo "📱 Frontend:      http://localhost:3000"
echo "🔧 Backend API:   http://localhost:8000"
echo "📚 API Docs:      http://localhost:8000/docs"
echo "🔍 Redis:         localhost:6379"
echo ""
echo "📋 Useful commands:"
echo "  View logs:      docker-compose logs -f"
echo "  Stop services:  docker-compose down"
echo "  Restart:        docker-compose restart"
echo ""
echo "🐛 Troubleshooting:"
echo "  Check status:   docker-compose ps"
echo "  View backend:   docker-compose logs backend"
echo "  View worker:    docker-compose logs celery-worker"
echo "  View frontend:  docker-compose logs frontend"