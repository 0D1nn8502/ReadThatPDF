# ReadThatPDF - Intelligent PDF Processing Platform

A comprehensive PDF processing platform that extracts text from PDFs, generates AI-powered insights, and delivers content through scheduled email campaigns.

## 🚀 Features

- **PDF Text Extraction**: Extract text from specific page ranges
- **AI-Powered Insights**: Generate intelligent insights using Groq API
- **Flexible Processing**: Immediate processing, scheduled delivery, or both
- **Email Delivery**: Automated email delivery of processed chunks
- **User Dashboard**: Monitor processing status and view insights
- **Authentication**: Secure user authentication with Clerk
- **Scalable Architecture**: FastAPI backend with Celery workers

## 🏗️ Architecture

### Backend (FastAPI + Celery)
- **FastAPI**: REST API server with comprehensive endpoints
- **Celery**: Distributed task queue for background processing
- **Redis**: Message broker and caching layer
- **AI Integration**: Groq API for insight generation
- **Email System**: SMTP-based email delivery

### Frontend (Next.js)
- **Next.js 15**: Modern React framework with App Router
- **Clerk**: Authentication and user management
- **Tailwind CSS**: Utility-first styling
- **TypeScript**: Type-safe development

## 📋 Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
- Groq API key
- Clerk account for authentication
- SMTP credentials for email delivery

## 🚀 Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ReadThatPDF
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 🛠️ Local Development Setup

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Redis** (required for Celery)
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

5. **Start the FastAPI server (Development)**
   ```bash
   ./dev-start.sh
   ```
   
   Or manually:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Start Celery worker** (in a new terminal)
   ```bash
   celery -A tasks worker --loglevel=info
   ```

7. **Start Celery beat** (in another terminal, for scheduled tasks)
   ```bash
   celery -A tasks beat --loglevel=info
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your values
   ```

4. **Start the development server**
   ```bash
   npm run dev
   ```

## 📚 API Endpoints

### Core Processing
- `POST /process-pdf-text` - Process PDF text with scheduling
- `GET /task-status/{task_id}` - Get task processing status
- `GET /user-insights/{user_id}` - Retrieve user insights
- `GET /user-schedule/{user_id}` - Get user schedule information
- `DELETE /user-schedule/{user_id}` - Cancel user schedule

### Health & Monitoring
- `GET /health` - System health check
- `GET /admin/system-metrics` - System metrics (admin)
- `POST /admin/cleanup-expired` - Cleanup expired data

### Manual Triggers
- `POST /trigger-scheduled-processing/{user_id}` - Manual processing trigger

## 🔧 Configuration

### Environment Variables

#### Required
- `GROQ_API_KEY`: Your Groq API key for AI insights
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`: Clerk publishable key
- `CLERK_SECRET_KEY`: Clerk secret key

#### Email Configuration
- `SMTP_HOST`: SMTP server host (default: smtp.gmail.com)
- `SMTP_PORT`: SMTP server port (default: 587)
- `SMTP_USER`: SMTP username
- `SMTP_PASS`: SMTP password
- `EMAIL_FROM`: From email address

#### Optional
- `REDIS_HOST`: Redis host (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `MAX_CHARS_PER_CHUNK`: Maximum characters per chunk (default: 4800)
- `SEND_EMAIL_RETRY_DELAY`: Email retry delay in seconds (default: 60)

### Processing Modes

1. **Immediate Only**: Process chunks immediately, no scheduling
2. **Schedule Only**: Set up scheduled processing without immediate processing
3. **Immediate + Schedule**: Process some chunks immediately, schedule the rest

### Schedule Types

- **Daily**: Process chunks every day
- **Weekly**: Process chunks once per week
- **Twice Daily**: Process chunks twice per day
- **Every Two Days**: Process chunks every other day
- **Monthly**: Process chunks once per month

## 🎯 Usage Examples

### Basic PDF Processing

```javascript
// Frontend API call
const response = await fetch('/api/process-pdf-text', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: "Your extracted PDF text here...",
    processing_mode: "immediate_and_schedule",
    immediate_chunks_count: 2,
    schedule_type: "daily",
    schedule_time: "09:00",
    user_timezone: "Asia/Kolkata",
    chunks_per_delivery: 2
  })
});
```

### Direct Backend API Call

```bash
curl -X POST "http://localhost:8000/process-pdf-text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your PDF text here...",
    "userId": "user123",
    "email": "user@example.com",
    "processing_mode": "immediate_and_schedule",
    "immediate_chunks_count": 2,
    "schedule_type": "daily",
    "schedule_time": "09:00",
    "user_timezone": "Asia/Kolkata",
    "chunks_per_delivery": 2
  }'
```

## 🔍 Monitoring

### Health Checks
- Frontend: http://localhost:3000/api/health
- Backend: http://localhost:8000/health

### System Metrics
- Backend metrics: http://localhost:8000/admin/system-metrics

### Logs
```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f frontend
```

## 🚨 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Ensure Redis is running: `docker ps | grep redis`
   - Check Redis logs: `docker-compose logs redis`

2. **Redis Schema Conflicts (Development)**
   - The app automatically cleans Redis on startup in development mode
   - Manual cleanup: `redis-cli FLUSHDB`
   - Use the development script: `./backend/dev-start.sh`

2. **Celery Workers Not Processing**
   - Check worker logs: `docker-compose logs celery-worker`
   - Verify Redis connection in worker logs

3. **Email Delivery Issues**
   - Verify SMTP credentials in environment variables
   - Check if Gmail App Passwords are being used (not regular password)

4. **Frontend API Errors**
   - Ensure backend is running and accessible
   - Check CORS configuration in FastAPI

### Debug Mode

Enable debug logging by setting environment variables:
```bash
export CELERY_LOG_LEVEL=DEBUG
export FASTAPI_LOG_LEVEL=DEBUG
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the excellent Python web framework
- [Next.js](https://nextjs.org/) for the React framework
- [Clerk](https://clerk.dev/) for authentication
- [Groq](https://groq.com/) for AI inference
- [Celery](https://celeryproject.org/) for distributed task processing