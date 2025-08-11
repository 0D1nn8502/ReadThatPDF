import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any
import time

logger = logging.getLogger(__name__)

class SchedulingMetrics:
    """Collects and logs scheduling metrics"""
    
    def __init__(self, redis_manager):
        self.redis_manager = redis_manager
    
    def record_schedule_created(self, user_id: str, schedule_type: str):
        """Record schedule creation event"""
        try:
            metric = {
                "event": "schedule_created",
                "user_id": user_id,
                "schedule_type": schedule_type,
                "timestamp": datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
            }
            
            # Log for external monitoring systems
            logger.info("METRIC", extra=metric)
            
            # Store in Redis for dashboard
            key = f"metrics:schedule_created:{user_id}"
            self.redis_manager.setex_json(key, timedelta(days=7), metric)
            
        except Exception as e:
            logger.error(f"Failed to record schedule creation metric: {e}")
    
    def record_schedule_execution(self, user_id: str, chunks_processed: int, execution_time: float):
        """Record schedule execution metrics"""
        try:
            metric = {
                "event": "schedule_executed",
                "user_id": user_id,
                "chunks_processed": chunks_processed,
                "execution_time_seconds": execution_time,
                "timestamp": datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
            }
            
            logger.info("METRIC", extra=metric)
            
            key = f"metrics:schedule_executed:{user_id}:{int(time.time())}"
            self.redis_manager.setex_json(key, timedelta(days=7), metric)
            
        except Exception as e:
            logger.error(f"Failed to record execution metric: {e}")
    
    def record_error(self, error_type: str, user_id: str, error_details: str):
        """Record error metrics"""
        try:
            metric = {
                "event": "scheduling_error",
                "error_type": error_type,
                "user_id": user_id,
                "error_details": error_details,
                "timestamp": datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
            }
            
            logger.error("SCHEDULING_ERROR", extra=metric)
            
            key = f"metrics:error:{user_id}:{int(time.time())}"
            self.redis_manager.setex_json(key, timedelta(days=7), metric)
            
        except Exception as e:
            logger.error(f"Failed to record error metric: {e}")
