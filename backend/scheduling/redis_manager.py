from redis import Redis 
import redis 
from redis.connection import ConnectionPool 
import json
import logging
from datetime import timedelta
from typing import Optional, Dict, Any, Union, cast 
from .exceptions import RedisConnectionException

logger = logging.getLogger(__name__)

class RedisManager:
    """Handles Redis operations with connection pooling and retry logic"""
    
    def __init__(self, host='localhost', port=6379, db=0, max_connections=20):
        self.connection_pool : ConnectionPool = redis.ConnectionPool(
            host=host, 
            port=port, 
            db=db, 
            max_connections=max_connections,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            decode_responses = True, 
            socket_timeout=5 
        )
        self.client : Redis = redis.Redis(connection_pool=self.connection_pool)
        self._test_connection()
    
    def _test_connection(self):
        """Test Redis connection on initialization"""
        try:
            self.client.ping()
            logger.info("Redis connection established successfully")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise RedisConnectionException(f"Redis connection failed: {e}")
    
    def setex_json(self, key: str, ttl: timedelta, data: Dict[Any, Any]) -> bool:
        """Set key with JSON data and expiration time"""
        try:
            result = self.client.setex(key, ttl, json.dumps(data, default=str))
            return bool(result) 

        except (redis.RedisError, TypeError, ValueError) as e:
            logger.error(f"Failed to set key {key}: {e}")
            raise RedisConnectionException(f"Failed to set Redis key: {e}")
    
    def get_json(self, key: str) -> Optional[Dict[Any, Any]]:
        """Get JSON data from Redis key"""
        try:
            data = self.client.get(key)
            if data is None:
                return None
            
            # Type cast to handle Redis response types
            data_raw: Union[str, bytes] = cast(Union[str, bytes], data)
            
            # Convert to string for JSON parsing
            if isinstance(data_raw, bytes):
                data_str = data_raw.decode('utf-8')
            else:
                data_str = str(data_raw)
            
            return json.loads(data_str)
        
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get key {key}: {e}")
            raise RedisConnectionException(f"Failed to get Redis key: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete Redis key"""
        try:
            return bool(self.client.delete(key))
        except redis.RedisError as e:
            logger.error(f"Failed to delete key {key}: {e}")
            raise RedisConnectionException(f"Failed to delete Redis key: {e}")
    
    def exists(self, key: str) -> bool:
        """Check if Redis key exists"""
        try:
            return bool(self.client.exists(key))
        except redis.RedisError as e:
            logger.error(f"Failed to check key {key}: {e}")
            return False
    
    def cleanup_expired_keys(self, pattern: str) -> int:
        """Clean up expired keys matching pattern"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys) #type: ignore
            return 0
        except redis.RedisError as e:
            logger.error(f"Failed to cleanup keys with pattern {pattern}: {e}")
            return 0
