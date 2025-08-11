import pytz
from datetime import datetime
from models import ScheduleType
from .exceptions import InvalidScheduleDataException
import logging

logger = logging.getLogger(__name__)

class ScheduleValidator:
    """Validates schedule data before processing"""
    
    VALID_TIMEZONES = set(pytz.all_timezones)
    MAX_HOURS_INTERVAL = 24
    MIN_HOURS_INTERVAL = 1
    MAX_CHUNKS_PER_DELIVERY = 10
    MIN_CHUNKS_PER_DELIVERY = 1
    
    @classmethod
    def validate_schedule_data(cls, user_data: dict) -> dict:
        """
        Validate and sanitize schedule data.
        Returns cleaned data or raises InvalidScheduleDataException.
        """
        try:
            # Required fields
            if not user_data.get("user_id"):
                raise InvalidScheduleDataException("user_id is required")
            
            if not isinstance(user_data.get("total_chunks"), int) or user_data["total_chunks"] <= 0:
                raise InvalidScheduleDataException("total_chunks must be a positive integer")
            
            # Validate schedule type
            schedule_type = user_data.get("schedule_type")
            if schedule_type and schedule_type not in [e.value for e in ScheduleType]:
                raise InvalidScheduleDataException(f"Invalid schedule_type: {schedule_type}")
            
            # Skip validation if no scheduling
            if schedule_type == ScheduleType.NONE:
                return user_data
            
            # Validate timezone
            user_timezone = user_data.get("user_timezone", "Asia/Kolkata")
            if user_timezone not in cls.VALID_TIMEZONES:
                logger.warning(f"Invalid timezone {user_timezone}, falling back to Asia/Kolkata")
                user_data["user_timezone"] = "Asia/Kolkata"
            
            # Validate schedule time
            schedule_time = user_data.get("schedule_time")
            if schedule_time:
                cls._validate_schedule_time(schedule_time)
            
            # Validate hours interval for EVERY_N_HOURS
            if schedule_type == ScheduleType.EVERY_N_HOURS:
                hours_interval = user_data.get("hours_interval")
                if not hours_interval:
                    raise InvalidScheduleDataException("hours_interval is required for EVERY_N_HOURS schedule")
                
                if not isinstance(hours_interval, int) or not (cls.MIN_HOURS_INTERVAL <= hours_interval <= cls.MAX_HOURS_INTERVAL):
                    raise InvalidScheduleDataException(f"hours_interval must be between {cls.MIN_HOURS_INTERVAL} and {cls.MAX_HOURS_INTERVAL}")
            
            # Validate chunks per delivery
            chunks_per_delivery = user_data.get("chunks_per_delivery", 2)
            if not isinstance(chunks_per_delivery, int) or not (cls.MIN_CHUNKS_PER_DELIVERY <= chunks_per_delivery <= cls.MAX_CHUNKS_PER_DELIVERY):
                logger.warning(f"Invalid chunks_per_delivery {chunks_per_delivery}, setting to 2")
                user_data["chunks_per_delivery"] = 2
            
            # Validate immediate chunks count
            immediate_chunks_count = user_data.get("immediate_chunks_count", 0)
            if not isinstance(immediate_chunks_count, int) or immediate_chunks_count < 0:
                user_data["immediate_chunks_count"] = 0
            elif immediate_chunks_count > user_data["total_chunks"]:
                user_data["immediate_chunks_count"] = user_data["total_chunks"]
            
            return user_data
            
        except Exception as e:
            logger.error(f"Validation failed for user_data: {e}")
            raise InvalidScheduleDataException(str(e))
    
    @classmethod
    def _validate_schedule_time(cls, schedule_time):
        """Validate schedule time format"""
        try:
            if isinstance(schedule_time, str):
                hour, minute = map(int, schedule_time.split(':'))
            elif isinstance(schedule_time, dict):
                hour = schedule_time.get('hour', 9)
                minute = schedule_time.get('minute', 0)
            else:
                raise InvalidScheduleDataException("schedule_time must be string (HH:MM) or dict")
            
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise InvalidScheduleDataException("Invalid time format: hour must be 0-23, minute must be 0-59")
                
        except (ValueError, AttributeError) as e:
            raise InvalidScheduleDataException(f"Invalid schedule_time format: {e}")
