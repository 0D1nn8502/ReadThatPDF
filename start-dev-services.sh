#!/bin/bash

# Start only the backend services needed for development

echo "🚀 Starting Development Services"
echo "================================"

# Check if Redis is already running
if docker ps | grep -q redis-dev; then
    echo "✅ Redis is already running"
else
    echo "🔍 Starting Redis..."
    docker run -d --name redis-dev -p 6379:6379 redis:7-alpine
    echo "✅ Redis started"
fi

echo ""
echo "🎉 Services ready for development!"
echo "=================================="
echo "🔍 Redis:         localhost:6379"
echo ""
echo "📋 Next steps:"
echo "  1. Terminal 1: cd backend && python main.py"
echo "  2. Terminal 2: cd frontend && npm run dev"
echo ""
echo "🛑 To stop services:"
echo "  docker stop redis-dev && docker rm redis-dev"