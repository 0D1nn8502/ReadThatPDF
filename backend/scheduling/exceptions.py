class SchedulingException(Exception):
    """Base exception for scheduling operations"""
    pass

class InvalidScheduleDataException(SchedulingException):
    """Raised when schedule data is invalid"""
    pass

class RedisConnectionException(SchedulingException):
    """Raised when Redis operations fail"""
    pass

