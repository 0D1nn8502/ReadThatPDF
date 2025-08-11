from celery.schedules import crontab
from datetime import datetime, timedelta, time
import time 
from zoneinfo import ZoneInfo
import logging
from models import Chunk, ScheduleType
from .validators import ScheduleValidator
from .redis_manager import RedisManager
from .metrics import SchedulingMetrics
from .exceptions import SchedulingException, InvalidScheduleDataException, RedisConnectionException

logger = logging.getLogger(__name__)

class UserScheduler:
    """Production-ready scheduler with validation, metrics, and error handling"""
    
    def __init__(self, celery_app, redis_config=None):
        self.celery_app = celery_app
        
        # Initialize Redis manager with error handling
        redis_config = redis_config or {}
        try:
            self.redis_manager = RedisManager(**redis_config)
        except Exception as e:
            logger.error(f"Redis schema conflict detected: {e}")
            logger.info("Attempting to clean Redis and retry...")
            try:
                # Try to clean and reconnect
                import redis
                temp_client = redis.Redis(**redis_config)
                temp_client.flushdb()
                temp_client.close()
                self.redis_manager = RedisManager(**redis_config)
                logger.info("Redis cleaned and reconnected successfully")
            except Exception as retry_error:
                logger.error(f"Failed to recover from Redis error: {retry_error}")
                raise
        
        # Initialize metrics
        self.metrics = SchedulingMetrics(self.redis_manager)
        
        logger.info("UserScheduler initialized successfully")
    
    def setup_user_schedule(self, user_data: dict) -> dict:
        """
        Set up scheduled processing for user chunks.
        Returns dict with success status and details.
        """
        start_time = time.time()
        user_id = user_data.get("user_id", "unknown")
        
        try:
            # Validate input data
            validated_data = ScheduleValidator.validate_schedule_data(user_data)
            
            schedule_type = validated_data.get("schedule_type")
            
            # Skip scheduling if NONE
            if schedule_type == ScheduleType.NONE:
                logger.info(f"No scheduling requested for user {user_id}")
                return {"success": True, "message": "No scheduling required"}
            
            # Check if there are chunks to schedule
            immediate_chunks_count = validated_data.get("immediate_chunks_count", 0)
            total_chunks = validated_data["total_chunks"]
            remaining_chunks = total_chunks - immediate_chunks_count
            
            if remaining_chunks <= 0:
                logger.info(f"No chunks left to schedule for user {user_id}")
                return {"success": True, "message": "All chunks processed immediately"}
            
            # Create schedule
            success = self._create_schedule(validated_data)
            
            if success:
                # Record metrics
                self.metrics.record_schedule_created(user_id, schedule_type)  
                
                execution_time = time.time() - start_time
                logger.info(f"Schedule created successfully for user {user_id} in {execution_time:.2f}s")
                
                return {
                    "success": True, 
                    "message": f"Schedule created for {remaining_chunks} chunks",
                    "schedule_type": schedule_type,
                    "remaining_chunks": remaining_chunks
                }
            else:
                return {"success": False, "message": "Failed to create schedule"}
                
        except InvalidScheduleDataException as e:
            self.metrics.record_error("validation_error", user_id, str(e))
            logger.warning(f"Validation failed for user {user_id}: {e}")
            return {"success": False, "message": f"Invalid schedule data: {e}"}
            
        except RedisConnectionException as e:
            self.metrics.record_error("redis_error", user_id, str(e))
            logger.error(f"Redis error for user {user_id}: {e}")
            return {"success": False, "message": "Database connection failed"}
            
        except Exception as e:
            self.metrics.record_error("system_error", user_id, str(e))
            logger.error(f"Unexpected error setting up schedule for user {user_id}: {e}", exc_info=True)
            return {"success": False, "message": "Internal system error"}
    
    def _create_schedule(self, user_data: dict) -> bool:
        """Create the actual Celery Beat schedule"""
        try:
            user_id = user_data["user_id"]
            schedule_type = user_data["schedule_type"]
            schedule_time = user_data["schedule_time"]
            chunks_per_delivery = user_data.get("chunks_per_delivery", 2)
            immediate_chunks_count = user_data.get("immediate_chunks_count", 0)
            
            # Parse schedule time
            hour, minute = self._parse_schedule_time(schedule_time)
            
            # Create crontab schedule
            schedule = self._create_crontab_schedule(schedule_type, hour, minute, user_data)
            if not schedule:
                logger.error(f"Failed to create crontab schedule for user {user_id}")
                return False
            
            # Set up Celery Beat schedule
            task_name = f"process_user_chunks_{user_id}"
            self._add_to_beat_schedule(
                task_name, schedule, user_id, chunks_per_delivery, immediate_chunks_count
            )
            
            # Store schedule metadata
            self._store_schedule_metadata(user_data, task_name)
            
            logger.info(f"Created {schedule_type} schedule for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating schedule: {e}", exc_info=True)
            return False
    
    def cleanup_user_schedule(self, user_id: str) -> bool:
        """Remove user's schedule and clean up resources"""
        try:
            # Get schedule metadata
            schedule_data = self.redis_manager.get_json(f"user_schedule:{user_id}")
            if schedule_data:
                task_name = schedule_data.get("task_name")
                
                # Remove from beat schedule
                if task_name and task_name in self.celery_app.conf.beat_schedule:
                    del self.celery_app.conf.beat_schedule[task_name]
                    logger.info(f"Removed beat schedule {task_name}")
                
                # Update metadata status
                schedule_data["status"] = "completed"
                schedule_data["completed_at"] = datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
                
                self.redis_manager.setex_json(
                    f"user_schedule:{user_id}",
                    timedelta(days=7),
                    schedule_data
                )
            
            # Clean up progress data
            self.redis_manager.delete(f"user_progress:{user_id}")
            
            logger.info(f"Cleaned up schedule for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up schedule for user {user_id}: {e}")
            return False
    
    def get_user_processing_state(self, user_id: str, start_index: int = 0) -> dict:
        """Get current processing state for a user with error handling"""
        try:
            progress_data = self.redis_manager.get_json(f"user_progress:{user_id}")
            
            if progress_data:
                return {
                    "current_index": progress_data.get("current_index", start_index),
                    "processed_count": progress_data.get("processed_count", 0)
                }
            else:
                return {
                    "current_index": start_index,
                    "processed_count": 0
                }
        except Exception as e:
            logger.error(f"Error getting processing state for user {user_id}: {e}")
            return {"current_index": start_index, "processed_count": 0}
    
    def update_user_progress(self, user_id: str, new_index: int, processed_count: int, task_id: str) -> bool:
        """Update user's processing progress with error handling"""
        try:
            new_progress = {
                "current_index": new_index,
                "processed_count": processed_count,
                "last_processed_at": datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),
                "last_task_id": task_id
            }
            
            self.redis_manager.setex_json(
                f"user_progress:{user_id}",
                timedelta(days=30),
                new_progress
            )
            
            logger.debug(f"Updated progress for user {user_id}: {processed_count} chunks processed")
            return True
            
        except Exception as e:
            logger.error(f"Error updating progress for user {user_id}: {e}")
            return False
    
    def get_user_chunks(self, user_id: str):
        """Retrieve user chunks from Redis with error handling"""
        try:
            user_data = self.redis_manager.get_json(f"user_chunks:{user_id}")
            if not user_data:
                return None
            
            return [Chunk(**chunk_data) for chunk_data in user_data["chunks"]]
            
        except Exception as e:
            logger.error(f"Error getting chunks for user {user_id}: {e}")
            return None
    
    def health_check(self) -> dict:
        """Perform health check on scheduler components"""
        health = {
            "scheduler": "healthy",
            "redis": "unknown",
            "celery": "unknown",
            "timestamp": datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
        }
        
        try:
            # Test Redis connection
            self.redis_manager.client.ping()
            health["redis"] = "healthy"
        except Exception as e:
            health["redis"] = f"unhealthy: {e}"
        
        try:
            # Test Celery connection
            stats = self.celery_app.control.inspect().stats()
            health["celery"] = "healthy" if stats else "no_workers"
        except Exception as e:
            health["celery"] = f"unhealthy: {e}"
        
        return health
    
    def cleanup_expired_data(self) -> dict:
        """Clean up expired data and orphaned schedules"""
        try:
            # Clean up old metrics
            metrics_cleaned = self.redis_manager.cleanup_expired_keys("metrics:*")
            
            # Clean up old progress data  
            progress_cleaned = self.redis_manager.cleanup_expired_keys("user_progress:*")
            
            logger.info(f"Cleanup completed: {metrics_cleaned} metrics, {progress_cleaned} progress records")
            
            return {
                "success": True,
                "metrics_cleaned": metrics_cleaned,
                "progress_cleaned": progress_cleaned
            }
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {"success": False, "error": str(e)}
    
    # Helper methods (same as before but with better error handling)
    def _parse_schedule_time(self, schedule_time):
        """Parse schedule time - validation already done"""
        if isinstance(schedule_time, str):
            hour, minute = map(int, schedule_time.split(':'))
        else:
            hour, minute = schedule_time.get('hour', 9), schedule_time.get('minute', 0)
        return hour, minute
    
    def _create_crontab_schedule(self, schedule_type, hour, minute, user_data):
        """Create crontab schedule"""
        if schedule_type == ScheduleType.DAILY:
            return crontab(hour=hour, minute=minute)
        elif schedule_type == ScheduleType.EVERY_N_HOURS:
            hours_interval = user_data["hours_interval"]
            return crontab(minute=minute, hour=f"*/{hours_interval}")
        return None
    
    def _add_to_beat_schedule(self, task_name, schedule, user_id, chunks_per_delivery, start_index):
        """Add task to Celery Beat schedule"""
        if task_name in self.celery_app.conf.beat_schedule:
            del self.celery_app.conf.beat_schedule[task_name]
        
        self.celery_app.conf.beat_schedule[task_name] = {
            'task': 'server.process_scheduled_chunks',
            'schedule': schedule,
            'args': (user_id,),
            'kwargs': {
                'chunks_per_delivery': chunks_per_delivery,
                'start_index': start_index
            },
            'options': {
                'expires': 60 * 60 * 24 * 30
            }
        }
    
    def _store_schedule_metadata(self, user_data, task_name):
        """Store schedule metadata"""
        user_id = user_data["user_id"]
        schedule_type = user_data["schedule_type"]
        hour, minute = self._parse_schedule_time(user_data["schedule_time"])
        
        schedule_metadata = {
            "user_id": user_id,
            "task_name": task_name,
            "schedule_type": schedule_type,
            "schedule_time": f"{hour:02d}:{minute:02d}",
            "timezone": user_data.get("user_timezone", "Asia/Kolkata"),
            "chunks_per_delivery": user_data.get("chunks_per_delivery", 2),
            "start_index": user_data.get("immediate_chunks_count", 0),
            "remaining_chunks": user_data["total_chunks"] - user_data.get("immediate_chunks_count", 0),
            "created_at": datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),
            "status": "active",
            "hours_interval": user_data.get("hours_interval")  # For EVERY_N_HOURS
        }
        
        self.redis_manager.setex_json(
            f"user_schedule:{user_id}",
            timedelta(days=30),
            schedule_metadata
        )