# main.py - Production FastAPI endpoints
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator 
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from contextlib import asynccontextmanager 

from tasks import (
    redis_client, 
    create_chunks_and_process, 
    generate_insights,
    process_scheduled_chunks,
    cleanup_expired_schedules,
    scheduler_health_check,
    user_scheduler
)
from models import PDFRequest, ProcessingMode, ScheduleType
from scheduling.exceptions import SchedulingException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown"""
    # Startup
    logger.info("Starting PDF Processing API")
    
    # Development mode: Clean Redis on startup to avoid schema conflicts
    import os
    if os.getenv("ENVIRONMENT", "development") == "development":
        try:
            logger.info("Development mode: Cleaning Redis to avoid schema conflicts...")
            redis_client.flushdb()  # Only flush current database, not all databases
            logger.info("Redis database cleaned successfully")
        except Exception as e:
            logger.warning(f"Could not clean Redis database: {e}")
    
    # Test critical services
    try:
        redis_client.ping()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
    
    try:
        health = user_scheduler.health_check()
        logger.info(f"Scheduler health: {health}")
    except Exception as e:
        logger.error(f"Scheduler health check failed: {e}")
    
    # Yield control to the application
    yield
    
    # Shutdown
    logger.info("Shutting down PDF Processing API")
    try:
        # Close Redis connections
        redis_client.close()
        logger.info("Redis connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="PDF Processing API",
    description="API for processing PDF text with AI insights and scheduling",
    version="1.0.0", 
    lifespan=lifespan 
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response Models
class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, str]
    
class ScheduleResponse(BaseModel):
    success: bool
    message: str
    schedule_type: Optional[str] = None
    remaining_chunks: Optional[int] = None
    task_id: Optional[str] = None

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class UserScheduleInfo(BaseModel):
    user_id: str
    schedule_active: bool
    schedule_type: Optional[str] = None
    next_execution: Optional[str] = None
    chunks_remaining: Optional[int] = None
    progress: Optional[Dict[str, Any]] = None


# Main Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check for all services"""
    timestamp = datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
    services = {}
    overall_status = "healthy"
    
    # Test Redis
    try:
        redis_client.ping()
        services["redis"] = "healthy"
    except Exception as e:
        services["redis"] = f"unhealthy: {str(e)}"
        overall_status = "degraded"
    
    # Test Celery workers
    try:
        from tasks import readpdf_app
        stats = readpdf_app.control.inspect().stats()
        if stats:
            services["celery"] = "healthy"
        else:
            services["celery"] = "no_workers"
            overall_status = "degraded"
    except Exception as e:
        services["celery"] = f"unhealthy: {str(e)}"
        overall_status = "degraded"
    
    # Test Scheduler
    try:
        scheduler_health = user_scheduler.health_check()
        services["scheduler"] = scheduler_health.get("scheduler", "unknown")
    except Exception as e:
        services["scheduler"] = f"unhealthy: {str(e)}"
        overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=timestamp,
        services=services
    )

@app.post("/process-pdf-text", response_model=TaskResponse)
async def process_text(request: PDFRequest, raw_request: Request):
    """
    Process PDF text with chunking, immediate processing, and optional scheduling
    """
    try:
        # Log raw request body
        raw_body = await raw_request.body()
        logger.info(f"Raw request body: {raw_body.decode()}")
        
        logger.info(f"Processing request for user {request.userId}")
        
        # Use both methods for debugging
        request_dict = request.model_dump(exclude_unset=False)
        custom_dict = request.to_dict()
        
        logger.info(f"Model dump: {request_dict}")
        logger.info(f"Custom dict: {custom_dict}")
        logger.info(f"Processing mode: {request.processing_mode}")
        logger.info(f"User timezone: {request.user_timezone}")
        
        # Start the main processing task
        task = create_chunks_and_process.delay(request_dict)
        
        return TaskResponse(
            task_id=task.id,
            status="accepted",
            message="PDF processing started successfully"
        )
        
    except Exception as e:
        logger.error(f"Error starting PDF processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start processing: {str(e)}"
        )

@app.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get status of a processing task"""
    try:
        from tasks import readpdf_app
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id, app=readpdf_app)
        
        response = TaskStatusResponse(
            task_id=task_id,
            status=task_result.status
        )
        
        if task_result.status == "PENDING":
            response.progress = {"message": "Task is queued or processing"}
        elif task_result.status == "PROGRESS":
            response.progress = task_result.result
        elif task_result.status == "SUCCESS":
            response.result = task_result.result
        elif task_result.status == "FAILURE":
            response.error = str(task_result.result)
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")

@app.get("/user-insights/{user_id}")
async def get_user_insights(user_id: str):
    """Get generated insights for a user"""
    import json
    
    try:
        insights_data = redis_client.get(f"user_insights:{user_id}")
        
        if not insights_data:
            raise HTTPException(
                status_code=404, 
                detail="No insights found for this user"
            )
        
        insights = json.loads(insights_data)
        
        return {
            "user_id": user_id,
            "insights": insights,
            "retrieved_at": datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid insights data")
    except Exception as e:
        logger.error(f"Error retrieving insights for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve insights")

@app.get("/user-schedule/{user_id}", response_model=UserScheduleInfo)
async def get_user_schedule_info(user_id: str):
    """Get user's current schedule information and progress"""
    try:
        # Get schedule metadata
        schedule_data = user_scheduler.redis_manager.get_json(f"user_schedule:{user_id}")
        
        if not schedule_data:
            return UserScheduleInfo(
                user_id=user_id,
                schedule_active=False
            )
        
        # Get progress data
        progress_data = user_scheduler.redis_manager.get_json(f"user_progress:{user_id}")
        
        # Calculate remaining chunks
        remaining_chunks = None
        if schedule_data.get("remaining_chunks"):
            processed = progress_data.get("processed_count", 0) if progress_data else 0
            remaining_chunks = max(0, schedule_data["remaining_chunks"] - processed)
        
        return UserScheduleInfo(
            user_id=user_id,
            schedule_active=schedule_data.get("status") == "active",
            schedule_type=schedule_data.get("schedule_type"),
            next_execution=schedule_data.get("next_execution"),
            chunks_remaining=remaining_chunks,
            progress=progress_data
        )
        
    except Exception as e:
        logger.error(f"Error getting schedule info for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedule information")

@app.delete("/user-schedule/{user_id}")
async def cancel_user_schedule(user_id: str):
    """Cancel a user's active schedule"""
    try:
        success = user_scheduler.cleanup_user_schedule(user_id)
        
        if success:
            return {"message": f"Schedule cancelled for user {user_id}"}
        else:
            raise HTTPException(
                status_code=404, 
                detail="No active schedule found for user"
            )
            
    except Exception as e:
        logger.error(f"Error cancelling schedule for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel schedule")

@app.post("/trigger-scheduled-processing/{user_id}")
async def trigger_scheduled_processing(user_id: str, chunks_per_delivery: int = Query(default=2, ge=1, le=10)):
    """Manually trigger scheduled processing for a user (for testing)"""
    try:
        # Check if user has data
        user_chunks = user_scheduler.get_user_chunks(user_id)
        if not user_chunks:
            raise HTTPException(
                status_code=404, 
                detail="No chunks found for user"
            )
        
        # Trigger processing
        task = process_scheduled_chunks.delay(
            user_id=user_id,
            chunks_per_delivery=chunks_per_delivery
        )
        
        return TaskResponse(
            task_id=task.id,
            status="triggered",
            message=f"Manual processing triggered for user {user_id}"
        )
        
    except Exception as e:
        logger.error(f"Error triggering processing for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger processing")


# Admin Endpoints
@app.post("/admin/cleanup-expired", dependencies=[])  # Add auth dependency
async def admin_cleanup_expired():
    """Admin endpoint to cleanup expired data"""
    try:
        task = cleanup_expired_schedules.delay()
        
        return TaskResponse(
            task_id=task.id,
            status="started",
            message="Cleanup task started"
        )
        
    except Exception as e:
        logger.error(f"Error starting cleanup task: {e}")
        raise HTTPException(status_code=500, detail="Failed to start cleanup")

@app.get("/admin/scheduler-health")
async def admin_scheduler_health():
    """Admin endpoint for detailed scheduler health"""
    try:
        task = scheduler_health_check.delay()
        
        # For immediate health check, you can also return sync result
        health = user_scheduler.health_check()
        
        return {
            "immediate_health": health,
            "detailed_check_task_id": task.id
        }
        
    except Exception as e:
        logger.error(f"Error getting scheduler health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health status")


@app.get("/admin/system-metrics")
async def admin_system_metrics():
    """Admin endpoint for system metrics"""
    try:
        from tasks import readpdf_app
        
        # Get Celery stats
        inspect = readpdf_app.control.inspect()
        stats = inspect.stats()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        
        # Get Redis info (await the operation)
        redis_info = await redis_client.info()
        
        # Get Redis keys with patterns (await both operations)
        schedule_keys = await redis_client.keys("user_schedule:*")
        progress_keys = await redis_client.keys("user_progress:*")
        
        return {
            "timestamp": datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),
            "celery": {
                "workers": len(stats) if stats else 0,
                "active_tasks": sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0,
                "scheduled_tasks": sum(len(tasks) for tasks in scheduled_tasks.values()) if scheduled_tasks else 0,
            },
            "redis": {
                "connected_clients": redis_info.get("connected_clients", 0),
                "used_memory_human": redis_info.get("used_memory_human", "unknown"),
                "keyspace": redis_info.get("keyspace", {}),
            },
            "scheduler": {
                "active_schedules": len(schedule_keys),
                "active_progress": len(progress_keys),
            }
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system metrics")
    

# Error Handlers
@app.exception_handler(SchedulingException)
async def scheduling_exception_handler(request, exc):
    logger.error(f"Scheduling error: {exc}")
    return HTTPException(status_code=400, detail=str(exc))

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return HTTPException(status_code=500, detail="Internal server error")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,  # Remove in production
        log_level="info"
    )




# Example usage and curl commands:

"""
# 1. Health Check
curl -X GET "http://localhost:8000/health"

# 2. Process PDF text with scheduling
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
    "chunks_per_delivery": 2,
    "user_timezone": "Asia/Kolkata"
  }'

# 3. Check task status
curl -X GET "http://localhost:8000/task-status/your-task-id-here"

# 4. Get user insights
curl -X GET "http://localhost:8000/user-insights/user123"

# 5. Get user schedule info
curl -X GET "http://localhost:8000/user-schedule/user123"

# 6. Cancel user schedule
curl -X DELETE "http://localhost:8000/user-schedule/user123"

# 7. Trigger manual processing
curl -X POST "http://localhost:8000/trigger-scheduled-processing/user123?chunks_per_delivery=3"

# 8. Admin cleanup
curl -X POST "http://localhost:8000/admin/cleanup-expired"

# 9. Admin metrics
curl -X GET "http://localhost:8000/admin/system-metrics"
"""